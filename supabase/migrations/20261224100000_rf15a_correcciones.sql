-- RF-15 etapa A, correcciones de la auditoria (ronda 1): el profesional no es cliente de sala ni de pagos,
-- el perfil solo se publica si el usuario conserva el rol y la foto tiene rutas fijas por perfil.

-- B1. Solo el rol `profesional` (un administrador con perfil sigue siendo administrador).
create function public.es_profesional()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.usuario where id = (select auth.uid()) and rol = 'profesional');
$$;
revoke all on function public.es_profesional() from public, anon;
grant execute on function public.es_profesional() to authenticated;

drop policy reserva_cliente_inserta on public.reserva;
create policy reserva_cliente_inserta on public.reserva for insert to authenticated
  with check (id_cliente = (select auth.uid()) and estado = 'pre_reservada' and motivo_cancelacion is null
    and vence_pago is not null and total >= 0 and not public.es_profesional());

drop policy comprobante_pago_inserta on public.comprobante_pago;
create policy comprobante_pago_inserta on public.comprobante_pago for insert to authenticated
  with check (id_cliente = (select auth.uid()) and estado = 'pendiente_validacion' and not public.es_profesional()
    and ruta_captura like (select auth.uid())::text || '/%'
    and exists (select 1 from public.cuota c join public.reserva r on r.id = c.id_reserva
                where c.id = id_cuota and r.id_cliente = (select auth.uid())));

-- Usar credito: si cubre el adelanto y confirma la reserva, el mismo aviso que una aprobacion.
create or replace function public.aplicar_credito(p_id_cuota uuid, p_monto numeric, p_id_credito uuid default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  k record;
  v_resto numeric;
  v_toma numeric;
begin
  if v_uid is null or public.es_profesional() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into c from public.cuota where id = p_id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente <> v_uid then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if c.estado = 'anulada' or r.estado in ('cancelada', 'no_asistio') or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada'))
     or exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'no_pagable' using errcode = 'P0001';
  end if;
  if p_monto is null or p_monto <= 0 or p_monto <> round(p_monto, 2) or p_monto > c.monto - c.pagado then
    raise exception 'monto_invalido' using errcode = '22023';
  end if;
  if p_id_credito is not null
     and not exists (select 1 from public.credito where id = p_id_credito and id_cliente = v_uid) then
    raise exception 'credito_no_encontrado' using errcode = 'P0002';
  end if;
  v_resto := p_monto;
  for k in
    select * from public.credito cr
    where cr.id_cliente = v_uid and cr.estado = 'vigente' and cr.saldo > 0 and cr.vence > now() and not cr.congelado
      and (p_id_credito is null or cr.id = p_id_credito)
    order by cr.vence, cr.id
    for update
  loop
    v_toma := least(k.saldo, v_resto);
    update public.credito
    set saldo = saldo - v_toma, estado = case when saldo - v_toma = 0 then 'agotado' else estado end
    where id = k.id;
    insert into public.aplicacion_credito (id_credito, id_cuota, monto, id_usuario) values (k.id, c.id, v_toma, v_uid);
    v_resto := v_resto - v_toma;
    exit when v_resto = 0;
  end loop;
  if v_resto > 0 then
    raise exception 'credito_insuficiente' using errcode = 'P0001';
  end if;
  update public.cuota
  set pagado = pagado + p_monto, estado = case when pagado + p_monto >= monto then 'pagada' else estado end
  where id = c.id;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' and c.pagado + p_monto >= c.monto then
    update public.reserva set estado = 'confirmada' where id = r.id;
    insert into public.notificacion (tipo, destinatario, datos)
    select 'pago_aprobado', u.email,
           jsonb_build_object('id_pago', null, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                              'monto', p_monto, 'reserva_confirmada', true)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;

-- No bloqueante 1: publicado y activo exigen que el usuario siga siendo profesional o administrador.
create or replace function public.perfil_publicado(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.perfil_profesional p
    join public.usuario u on u.id = p.id and u.rol in ('profesional', 'administrador')
    where p.id = p_id and p.activo
      and exists (select 1 from public.perfil_especialidad pe
                  join public.especialidad_asesoria e on e.id = pe.id_especialidad
                  where pe.id_profesional = p.id and e.activa)
      and exists (select 1 from public.precio_asesoria pr where pr.id_profesional = p.id)
  );
$$;

create or replace function public.cambiar_estado_profesional(p_id uuid, p_activo boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_rol text;
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador cambia el estado' using errcode = '42501';
  end if;
  select u.rol into v_rol from public.perfil_profesional p join public.usuario u on u.id = p.id where p.id = p_id;
  if not found then
    raise exception 'el perfil no existe' using errcode = 'P0002';
  end if;
  if p_activo and v_rol not in ('profesional', 'administrador') then
    raise exception 'rol_no_admitido' using errcode = 'P0001';
  end if;
  update public.perfil_profesional set activo = p_activo where id = p_id;
end;
$$;

-- No bloqueante 3: la API sube con la sesion del usuario, asi que Storage solo admite dos rutas por perfil,
-- `<perfil>/foto-1` y `<perfil>/foto-2` (la API alterna para no pisar la foto vigente antes del commit).
create function public.gestiona_foto_de_perfil(p_nombre text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select case when p_nombre ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/foto-[12]$'
              then public.gestiona_carpeta_de_perfil(split_part(p_nombre, '/', 1)) else false end;
$$;
revoke all on function public.gestiona_foto_de_perfil(text) from public, anon;
grant execute on function public.gestiona_foto_de_perfil(text) to authenticated;
drop policy profesionales_inserta on storage.objects;
create policy profesionales_inserta on storage.objects for insert to authenticated
  with check (bucket_id = 'profesionales' and public.gestiona_foto_de_perfil(name));
create policy profesionales_sobrescribe on storage.objects for update to authenticated
  using (bucket_id = 'profesionales' and public.gestiona_foto_de_perfil(name))
  with check (bucket_id = 'profesionales' and public.gestiona_foto_de_perfil(name));
