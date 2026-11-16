-- RF-05: comprobantes de pago, datos para pagar, validacion del administrador, avisos y storage `comprobantes` (ADR-010).

-- Datos para pagar (RN-22): un texto por metodo, editable por el administrador.
create table public.instruccion_pago (
  metodo text primary key check (metodo in ('transferencia', 'yape', 'plin', 'tarjeta')),
  texto text not null default '' check (char_length(texto) <= 1000),
  activo boolean not null default false,
  check (not activo or btrim(texto) <> '')
);
insert into public.instruccion_pago (metodo) values ('transferencia'), ('yape'), ('plin'), ('tarjeta');

create table public.comprobante_pago (
  id uuid primary key default gen_random_uuid(),
  id_cuota uuid not null references public.cuota (id),
  id_cliente uuid not null references public.usuario (id),
  metodo text not null references public.instruccion_pago (metodo),
  monto numeric(10, 2) not null check (monto > 0),
  numero_operacion text not null
    check (char_length(btrim(numero_operacion)) between 1 and 64 and numero_operacion !~ '[[:cntrl:]]'),
  ruta_captura text not null,
  tipo_captura text not null check (tipo_captura in ('image/jpeg', 'image/png', 'application/pdf')),
  estado text not null default 'pendiente_validacion'
    check (estado in ('pendiente_validacion', 'aprobado', 'rechazado')),
  motivo_rechazo text check (char_length(btrim(motivo_rechazo)) between 1 and 300),
  registrado_en timestamptz not null default now(),
  validado_en timestamptz,
  id_validador uuid references public.usuario (id) on delete set null,
  check ((estado = 'rechazado') = (motivo_rechazo is not null)),
  check ((estado = 'pendiente_validacion') = (validado_en is null))
);
-- Un pago en validacion por cuota; una operacion (normalizada) por metodo salvo rechazados.
create unique index comprobante_pago_pendiente_uq on public.comprobante_pago (id_cuota)
  where estado = 'pendiente_validacion';
create unique index comprobante_pago_operacion_uq
  on public.comprobante_pago (metodo, lower(btrim(numero_operacion))) where estado <> 'rechazado';
create index comprobante_pago_cliente_idx on public.comprobante_pago (id_cliente);
create index comprobante_pago_estado_idx on public.comprobante_pago (estado, registrado_en);

-- tiene_pagos (RN-18) cuenta tambien los comprobantes en validacion o aprobados: detiene la caducidad
-- y ocupacion_sala no libera el tramo (ambas ya la usan).
create or replace function public.tiene_pagos(p_id_reserva uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (select 1 from public.cuota where id_reserva = p_id_reserva and estado = 'pagada')
      or exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                 where c.id_reserva = p_id_reserva and p.estado in ('pendiente_validacion', 'aprobado'));
$$;

-- Avisos de pago.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado'));

-- Reglas de pagabilidad (antes de insertar). Errores P0001 con mensaje: cuota_pagada, pago_en_validacion,
-- cuota_no_pagable, metodo_no_disponible, operacion_duplicada; 42501 si la cuota no es del usuario; P0002 si no existe.
-- Bloquea la cuota para serializar registros simultaneos (los indices unicos son la ultima barrera, 23505).
create function public.validar_pago_nuevo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  c public.cuota%rowtype;
  r public.reserva%rowtype;
begin
  select * into c from public.cuota where id = new.id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva;
  if r.id_cliente is distinct from (select auth.uid()) or new.id_cliente <> r.id_cliente then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'pago_en_validacion' using errcode = 'P0001';
  end if;
  if r.estado = 'cancelada' or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada')) then
    raise exception 'cuota_no_pagable' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.instruccion_pago where metodo = new.metodo and activo) then
    raise exception 'metodo_no_disponible' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago
             where metodo = new.metodo and estado <> 'rechazado'
               and lower(btrim(numero_operacion)) = lower(btrim(new.numero_operacion))) then
    raise exception 'operacion_duplicada' using errcode = 'P0001';
  end if;
  return new;
end;
$$;
revoke all on function public.validar_pago_nuevo() from public, anon, authenticated;
create trigger comprobante_pago_validar before insert on public.comprobante_pago
  for each row execute function public.validar_pago_nuevo();

-- Despues de insertar: aviso `pago_registrado` a cada administrador.
create function public.avisar_pago_registrado()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_registrado', u.email,
         jsonb_build_object('id_pago', new.id, 'id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre,
                            'hito', c.hito, 'monto', new.monto, 'monto_cuota', c.monto, 'metodo', new.metodo,
                            'numero_operacion', new.numero_operacion)
  from public.cuota c
  join public.reserva r on r.id = c.id_reserva
  left join public.usuario cl on cl.id = new.id_cliente
  cross join (select au.email from public.usuario a join auth.users au on au.id = a.id
              where a.rol = 'administrador') u
  where c.id = new.id_cuota;
  return null;
end;
$$;
revoke all on function public.avisar_pago_registrado() from public, anon, authenticated;
create trigger comprobante_pago_avisar after insert on public.comprobante_pago
  for each row execute function public.avisar_pago_registrado();

-- Aprobar (RN-04): solo administrador. Errores: 42501, P0002 no existe, P0001 `pago_ya_validado`.
create function public.aprobar_pago(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  p public.comprobante_pago%rowtype;
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_confirma boolean := false;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into p from public.comprobante_pago where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p.estado <> 'pendiente_validacion' then
    raise exception 'pago_ya_validado' using errcode = 'P0001';
  end if;
  update public.comprobante_pago set estado = 'aprobado', validado_en = now(), id_validador = v_uid where id = p_id;
  update public.cuota set estado = 'pagada' where id = p.id_cuota returning * into c;
  select * into r from public.reserva where id = c.id_reserva for update;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' then
    update public.reserva set estado = 'confirmada' where id = r.id;
    v_confirma := true;
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_aprobado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'reserva_confirmada', v_confirma)
  from auth.users u where u.id = p.id_cliente;
end;
$$;
revoke all on function public.aprobar_pago(uuid) from public, anon;
grant execute on function public.aprobar_pago(uuid) to authenticated;

-- Rechazar (RN-04, RN-18): motivo de 1 a 300 caracteres (22023 `motivo_invalido`). Sin otro pago vigente en la reserva,
-- el plazo pasa a max(actual, min(inicio, ahora + horas_limite_pago)).
create function public.rechazar_pago(p_id uuid, p_motivo text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  p public.comprobante_pago%rowtype;
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 1 and 300 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  select * into p from public.comprobante_pago where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p.estado <> 'pendiente_validacion' then
    raise exception 'pago_ya_validado' using errcode = 'P0001';
  end if;
  update public.comprobante_pago
  set estado = 'rechazado', motivo_rechazo = v_motivo, validado_en = now(), id_validador = v_uid
  where id = p_id;
  select * into c from public.cuota where id = p.id_cuota;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.estado = 'pre_reservada' and not public.tiene_pagos(r.id) then
    update public.reserva
    set vence_pago = greatest(coalesce(vence_pago, now()),
      least(inicio, now() + make_interval(hours => (select valor from public.parametro where clave = 'horas_limite_pago'))))
    where id = r.id;
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_rechazado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'motivo', v_motivo)
  from auth.users u where u.id = p.id_cliente;
end;
$$;
revoke all on function public.rechazar_pago(uuid, text) from public, anon;
grant execute on function public.rechazar_pago(uuid, text) to authenticated;

-- RLS y privilegios
alter table public.comprobante_pago enable row level security;
alter table public.instruccion_pago enable row level security;
revoke all on public.comprobante_pago, public.instruccion_pago from anon, authenticated;

-- El dueno lee los suyos y registra solo `pendiente_validacion` (sin privilegio sobre estado, motivo ni validador);
-- el administrador lee todos; nadie actualiza ni borra directo.
grant select on public.comprobante_pago to authenticated;
grant insert (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  on public.comprobante_pago to authenticated;
create policy comprobante_pago_lee on public.comprobante_pago for select to authenticated
  using (id_cliente = (select auth.uid()) or public.es_administrador());
create policy comprobante_pago_inserta on public.comprobante_pago for insert to authenticated
  with check (id_cliente = (select auth.uid()) and estado = 'pendiente_validacion'
    and ruta_captura like (select auth.uid())::text || '/%'
    and exists (select 1 from public.cuota c join public.reserva r on r.id = c.id_reserva
                where c.id = id_cuota and r.id_cliente = (select auth.uid())));

grant select on public.instruccion_pago to authenticated;
grant update (texto, activo) on public.instruccion_pago to authenticated;
create policy instruccion_pago_lee on public.instruccion_pago for select to authenticated
  using (activo or public.es_administrador());
create policy instruccion_pago_admin_actualiza on public.instruccion_pago for update to authenticated
  using (public.es_administrador()) with check (public.es_administrador());

-- Storage `comprobantes` (ADR-003): 5 MB y tipos en el bucket; el dueno sube y lee en `<uid>/`, el administrador lee todo.
update storage.buckets
set file_size_limit = 5242880, allowed_mime_types = array['image/jpeg', 'image/png', 'application/pdf']
where id = 'comprobantes';
create policy comprobantes_inserta on storage.objects for insert to authenticated
  with check (bucket_id = 'comprobantes' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy comprobantes_lee on storage.objects for select to authenticated
  using (bucket_id = 'comprobantes'
    and ((storage.foldername(name))[1] = (select auth.uid())::text or public.es_administrador()));
