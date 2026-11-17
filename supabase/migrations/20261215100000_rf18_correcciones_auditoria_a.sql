-- RF-18, correcciones de la auditoria A (ronda 1). Se parte de las versiones vigentes (parte B para calcular_cancelacion y
-- aplicar_inasistencia). Orden de bloqueo sin cambios: cuotas de la reserva -> reserva -> creditos.

-- 1. Cada aplicacion de credito recuerda cuanto ya volvio a su credito de origen (no se devuelve dos veces).
alter table public.aplicacion_credito
  add column devuelto numeric(10, 2) not null default 0 check (devuelto >= 0 and devuelto <= monto);

drop trigger aplicacion_credito_inmutable on public.aplicacion_credito;
create function public.aplicacion_credito_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' and to_jsonb(new) - 'devuelto' = to_jsonb(old) - 'devuelto' and new.devuelto >= old.devuelto then
    return new; -- solo crece lo devuelto
  end if;
  if tg_op = 'DELETE' and pg_trigger_depth() > 1 then
    return old; -- en cascada desde la reserva
  end if;
  raise exception 'Un registro de % no se edita ni se borra.', tg_table_name;
end;
$$;
create trigger aplicacion_credito_inmutable before update or delete on public.aplicacion_credito
  for each row execute function public.aplicacion_credito_inmutable();

-- 2. Capturas que detienen el plazo y la caducidad (RN-18): solo las que estan en validacion o aprobadas. El credito
-- aplicado cuenta como pago para cancelar (tiene_pagos), pero no mantiene viva una pre-reserva vencida. Una cuota
-- `pagada` tambien cuenta: solo se llega a ella con una captura aprobada o con el credito que ya confirma la reserva.
create function public.tiene_capturas(p_id_reserva uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (select 1 from public.cuota where id_reserva = p_id_reserva and estado = 'pagada')
      or exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                 where c.id_reserva = p_id_reserva and p.estado in ('pendiente_validacion', 'aprobado'));
$$;
revoke all on function public.tiene_capturas(uuid) from public, anon, authenticated;

-- 3. Devuelve a sus creditos de origen (con su tipo y vencimiento) lo aplicado a las cuotas de la reserva, hasta
-- `p_tope` (null: todo lo pendiente de devolver). Lo ultimo aplicado vuelve primero. Un credito ya vencido (o vencido por
-- el cron) se reactiva por 7 dias hasta el fin del dia en Lima; con `p_dias_min` el vencimiento es el mayor entre el suyo
-- y el fin del dia en Lima a esos dias (cancelacion del estudio: no es culpa del cliente). Devuelve lo devuelto.
create function public.devolver_credito_aplicado(p_id_reserva uuid, p_tope numeric default null, p_dias_min integer default null)
returns numeric
language plpgsql
security definer
set search_path = ''
as $$
declare
  a record;
  v_resto numeric := coalesce(p_tope, 99999999.99);
  v_toma numeric;
  v_total numeric := 0;
begin
  perform 1 from public.credito k
  where k.id in (select x.id_credito from public.aplicacion_credito x join public.cuota c on c.id = x.id_cuota
                 where c.id_reserva = p_id_reserva and x.monto > x.devuelto)
  order by k.id
  for update;
  for a in
    select x.id, x.id_credito, x.monto - x.devuelto as pendiente
    from public.aplicacion_credito x join public.cuota c on c.id = x.id_cuota
    where c.id_reserva = p_id_reserva and x.monto > x.devuelto
    order by x.aplicada_en desc, x.id desc
    for update of x
  loop
    exit when v_resto <= 0;
    v_toma := least(a.pendiente, v_resto);
    update public.credito
    set saldo = saldo + v_toma, estado = 'vigente',
        vence = case when p_dias_min is not null then greatest(vence, public.fin_de_dia_lima(now(), p_dias_min))
                     when vence <= now() or estado = 'vencido' then public.fin_de_dia_lima(now(), 7) else vence end
    where id = a.id_credito;
    update public.aplicacion_credito set devuelto = devuelto + v_toma where id = a.id;
    v_resto := v_resto - v_toma;
    v_total := v_total + v_toma;
  end loop;
  return v_total;
end;
$$;
revoke all on function public.devolver_credito_aplicado(uuid, numeric, integer) from public, anon, authenticated;

-- 4. Caducidad: solo las capturas la detienen; el credito aplicado vuelve a sus creditos de origen.
create or replace function public.caducar_reservas(
  p_id_sala uuid default null, p_desde timestamptz default null, p_hasta timestamptz default null)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_caducadas integer;
  v_ids uuid[];
begin
  perform 1 from public.reserva r
  where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_capturas(r.id)
    and (p_id_sala is null
         or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)))
  order by r.id
  for update;
  with caducadas as (
    update public.reserva r
    set estado = 'cancelada', motivo_cancelacion = 'caducada'
    where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_capturas(r.id)
      and (p_id_sala is null
           or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)))
    returning r.id, r.id_cliente, r.folio, r.inicio, r.fin
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_caducada', u.email,
           jsonb_build_object('id_reserva', c.id, 'folio', c.folio, 'inicio', c.inicio, 'fin', c.fin)
    from caducadas c join auth.users u on u.id = c.id_cliente
    returning 1
  )
  select count(*)::int, coalesce(array_agg(id), '{}') into v_caducadas, v_ids from caducadas;
  perform public.devolver_credito_aplicado(x) from unnest(v_ids) x;
  return v_caducadas;
end;
$$;

-- El tramo de una pre_reservada vencida sin capturas cuenta como libre (la caducara el cron).
create or replace function public.ocupacion_sala(p_id_sala uuid, p_desde timestamptz, p_hasta timestamptz)
returns table (inicio timestamptz, fin_buffer timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin_buffer
  from public.reserva r
  where r.id_sala = p_id_sala
    and r.estado <> 'cancelada'
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_capturas(r.id))
    and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;

create or replace function public.ocupacion_sala_excluyendo(p_id_sala uuid, p_desde timestamptz, p_hasta timestamptz, p_excluir uuid)
returns table (inicio timestamptz, fin_buffer timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin_buffer
  from public.reserva r
  where r.id_sala = p_id_sala
    and r.id <> p_excluir
    and r.estado <> 'cancelada'
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_capturas(r.id))
    and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;

-- Rechazar una captura amplia el plazo mientras no haya otra captura en validacion o aprobada (el credito no cuenta).
create or replace function public.rechazar_pago(p_id uuid, p_motivo text)
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
  if r.estado = 'pre_reservada' and not public.tiene_capturas(r.id) then
    update public.reserva
    set vence_pago = greatest(coalesce(vence_pago, now()),
      least(inicio, now() + make_interval(hours => (r.parametros_aplicados ->> 'horas_limite_pago')::int)))
    where id = r.id;
  end if;
  if r.estado in ('cancelada', 'no_asistio') then
    update public.cuota set estado = 'anulada' where id = c.id and estado = 'pendiente'; -- ya no se puede pagar
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_rechazado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'motivo', v_motivo)
  from auth.users u where u.id = p.id_cliente;
end;
$$;

-- 5. Aprobar: la cuota pasa a pagada solo cuando lo aplicado cubre su monto, y solo entonces confirma la reserva.
create or replace function public.aprobar_pago(p_id uuid)
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
  update public.cuota
  set pagado = pagado + p.monto, estado = case when pagado + p.monto >= monto then 'pagada' else estado end
  where id = p.id_cuota returning * into c;
  select * into r from public.reserva where id = c.id_reserva for update;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' and c.estado = 'pagada' then
    update public.reserva set estado = 'confirmada' where id = r.id;
    v_confirma := true;
  end if;
  if r.estado in ('cancelada', 'no_asistio') and r.aviso_en is not null then
    perform public.aplicar_pago_tardio(r.id, p.monto); -- sigue el nivel con que se cancelo (ADR-015)
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_aprobado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'reserva_confirmada', v_confirma)
  from auth.users u where u.id = p.id_cliente;
end;
$$;

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
  if v_uid is null then
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

-- 6. Cancelar y excepcion: lo que procede de credito aplicado vuelve a sus creditos de origen (sin escalar de tipo ni
-- ganar dias); solo el resto es credito nuevo. La retencion sale primero de lo pagado en efectivo, asi que de lo
-- generado vuelve a su origen hasta lo aplicado pendiente; el invariante retenido + devuelto + nuevo = pagado neto.
create or replace function public.cancelar_reserva(
  p_id uuid, p_nota text default null, p_nivel_esperado integer default null, p_por text default null,
  p_aviso_en timestamptz default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_dueno boolean;
  v_admin boolean;
  v_directo boolean; -- el cliente cancela por si mismo
  v_por text;
  v_nota text := nullif(btrim(p_nota), '');
  v_aviso timestamptz;
  v_tiene boolean;
  v_vista record;
  v_nivel smallint;
  v_dias integer;
  v_devuelto numeric;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_dueno := r.id_cliente = v_uid;
  v_admin := public.es_administrador();
  if not v_dueno and not v_admin then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p_por is not null and p_por not in ('cliente', 'estudio') then
    raise exception 'por_invalido' using errcode = '22023';
  end if;
  v_directo := v_dueno and p_aviso_en is null and coalesce(p_por, 'cliente') = 'cliente';
  if not v_directo and not v_admin then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  v_por := case when v_directo then 'cliente' else coalesce(p_por, 'estudio') end;
  if r.estado not in ('pre_reservada', 'confirmada') or r.inicio <= now() then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if char_length(v_nota) > 300 or v_nota ~ '[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]' then
    raise exception 'nota_invalida' using errcode = '22023';
  end if;
  if v_por = 'cliente' and not v_directo then
    perform public.validar_aviso(p_aviso_en, r.creada_en);
    v_aviso := p_aviso_en;
  else
    v_aviso := now();
  end if;
  v_tiene := public.tiene_pagos(r.id);
  if not v_directo and v_nota is null and (v_tiene or v_por = 'cliente') then
    raise exception 'nota_requerida' using errcode = 'P0001';
  end if;
  select * into v_vista from public.calcular_cancelacion(r.id, v_aviso);
  if v_directo and v_tiene and p_nivel_esperado is distinct from v_vista.nivel then
    raise exception 'nivel_cambiado' using errcode = 'P0001', detail = jsonb_build_object(
      'nivel', v_vista.nivel, 'anticipacion_horas', v_vista.anticipacion_horas, 'pagado', v_vista.pagado::text,
      'en_validacion', v_vista.en_validacion::text, 'retenido', v_vista.retenido::text, 'credito', v_vista.credito::text,
      'credito_vence', v_vista.credito_vence, 'puede_reprogramar', v_vista.puede_reprogramar,
      'reprogramaciones_restantes', v_vista.reprogramaciones_restantes)::text;
  end if;
  -- Por el estudio no hay nivel ni retencion: el cliente elige despues (CA-13).
  v_nivel := case when v_por = 'estudio' then null else v_vista.nivel end;
  update public.reserva
  set estado = 'cancelada', motivo_cancelacion = case when v_por = 'estudio' then 'administrador' else 'cliente' end,
      nota_cancelacion = v_nota, nivel_cancelacion = v_nivel, aviso_en = v_aviso, cancelacion_por = v_por,
      id_cancelador = v_uid, pagado_cancelacion = v_vista.pagado,
      retenido = case when v_por = 'estudio' then 0 else v_vista.retenido end,
      credito_generado = case when v_por = 'estudio' then 0 else v_vista.credito end,
      eleccion_estudio = case when v_por = 'estudio' and v_tiene then 'pendiente' end
  where id = r.id;
  if v_tiene then
    update public.cuota q set estado = 'anulada'
    where q.id_reserva = r.id and q.estado = 'pendiente'
      and not exists (select 1 from public.comprobante_pago p where p.id_cuota = q.id and p.estado = 'pendiente_validacion');
  end if;
  v_dias := (r.parametros_aplicados ->> 'dias_vigencia_credito')::int;
  if v_por = 'cliente' and v_vista.credito > 0 then
    v_devuelto := public.devolver_credito_aplicado(r.id, v_vista.credito);
    if v_vista.credito > v_devuelto then
      perform public.generar_credito(r.id_cliente, r.id, 'nivel_' || v_nivel, v_vista.credito - v_devuelto, v_dias);
    end if;
  end if;
  if v_directo then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_cliente', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre,
                              'inicio', r.inicio, 'fin', r.fin)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  elsif v_por = 'estudio' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_estudio', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'nota', v_nota)
    from auth.users u where u.id = r.id_cliente;
  end if;
  if v_por = 'cliente' and v_tiene then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_con_pagos', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                              'nivel', v_nivel, 'pagado', v_vista.pagado, 'retenido', v_vista.retenido,
                              'credito', v_vista.credito, 'credito_vence', v_vista.credito_vence)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;

create or replace function public.aplicar_excepcion(p_id uuid, p_motivo text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
  v_devuelto numeric;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 10 and 500 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.excepcion_en is not null then
    raise exception 'excepcion_ya_aplicada' using errcode = 'P0001';
  end if;
  if not ((r.estado = 'cancelada' and r.cancelacion_por = 'cliente' and r.nivel_cancelacion in (2, 3))
          or r.estado = 'no_asistio') or coalesce(r.retenido, 0) <= 0 then
    raise exception 'excepcion_no_aplicable' using errcode = 'P0001';
  end if;
  v_devuelto := public.devolver_credito_aplicado(r.id, r.retenido);
  if r.retenido > v_devuelto then
    perform public.generar_credito(r.id_cliente, r.id, 'excepcion', r.retenido - v_devuelto,
      (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  end if;
  update public.reserva
  set credito_generado = coalesce(credito_generado, 0) + retenido, retenido = 0, excepcion_motivo = v_motivo,
      excepcion_por = v_uid, excepcion_en = now()
  where id = r.id;
end;
$$;

-- 7. avanzar_reservas: primero caduca (un credito aplicado no la mantiene viva), y solo marca no_asistio a las que siguen
-- pre_reservada tras bloquear sus filas; el contador cuenta las cambiadas.
create or replace function public.avanzar_reservas()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_avanzadas integer;
  v_sin_asistir integer := 0;
  v_id uuid;
begin
  perform public.caducar_reservas();
  for v_id in
    select r.id from public.reserva r
    where r.estado = 'pre_reservada' and r.fin <= now() and public.tiene_capturas(r.id) order by r.id
  loop
    perform 1 from public.cuota where id_reserva = v_id order by id for update;
    perform 1 from public.reserva where id = v_id and estado = 'pre_reservada' for update; -- tras la espera, vuelve a mirar
    if found then
      perform public.aplicar_inasistencia(v_id, null);
      v_sin_asistir := v_sin_asistir + 1;
    end if;
  end loop;
  perform 1 from public.reserva r
  where (r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now())
  order by r.id
  for update;
  with avanzadas as (
    update public.reserva r
    set estado = case when r.fin <= now() then 'finalizada' else 'en_curso' end
    where (r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now())
    returning r.id, r.id_cliente, r.folio, r.estado, r.inicio, r.fin
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_finalizada_saldo', u.email,
           jsonb_build_object('id_reserva', a.id, 'folio', a.folio, 'inicio', a.inicio, 'fin', a.fin, 'saldo', c.monto)
    from avanzadas a
    join public.cuota c on c.id_reserva = a.id and c.hito = 'al_terminar' and c.estado = 'pendiente'
    join auth.users u on u.id = a.id_cliente
    where a.estado = 'finalizada'
      and not exists (select 1 from public.comprobante_pago p
                      where p.id_cuota = c.id and p.estado = 'pendiente_validacion')
    returning 1
  )
  select count(*)::int into v_avanzadas from avanzadas;
  return v_avanzadas + v_sin_asistir;
end;
$$;

-- 8. Barrera: con rol de API nadie saca una reserva de cancelada/no_asistio ni una cuota de anulada (solo las funciones).
create or replace function public.reserva_barrera()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.excepcion_en is not null and new.excepcion_en is null then
    raise exception 'La excepcion aplicada no se quita.';
  end if;
  if current_user in ('authenticated', 'anon') then
    if old.estado in ('cancelada', 'no_asistio') and new.estado <> old.estado then
      raise exception 'Una reserva cancelada o con inasistencia no se reactiva por update.' using errcode = '42501';
    end if;
    if new.estado = 'no_asistio' and old.estado <> 'no_asistio' then
      raise exception 'La inasistencia se marca con marcar_inasistencia.' using errcode = '42501';
    end if;
    if new.estado = 'cancelada' and old.estado <> 'cancelada'
       and (exists (select 1 from public.cuota where id_reserva = old.id and (estado = 'pagada' or pagado > 0))
            or exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                       where c.id_reserva = old.id and p.estado in ('pendiente_validacion', 'aprobado'))) then
      raise exception 'Una reserva con pagos se cancela con cancelar_reserva.' using errcode = '42501';
    end if;
  end if;
  return new;
end;
$$;

create function public.cuota_barrera()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if current_user in ('authenticated', 'anon') and old.estado = 'anulada' and new.estado <> 'anulada' then
    raise exception 'Una cuota anulada no se reactiva por update.' using errcode = '42501';
  end if;
  return new;
end;
$$;
create trigger cuota_barrera before update on public.cuota
  for each row execute function public.cuota_barrera();

-- 9. creada_en de las reservas anteriores a RF-18 (quedaron con la fecha de la migracion): el de su aviso
-- `reserva_creada` si existe y es anterior. Idempotente; devuelve cuantas cambio.
create function public.rellenar_creada_en()
returns integer
language sql
security definer
set search_path = ''
as $$
  with avisos as (
    select (n.datos ->> 'id_reserva')::uuid as id, min(n.creada_en) as en
    from public.notificacion n where n.tipo = 'reserva_creada' and n.datos ? 'id_reserva' group by 1
  ), cambiadas as (
    update public.reserva r set creada_en = a.en from avisos a where a.id = r.id and a.en < r.creada_en returning 1
  )
  select count(*)::int from cambiadas;
$$;
revoke all on function public.rellenar_creada_en() from public, anon, authenticated;
select public.rellenar_creada_en();

-- 10. Devolucion integra tras la cancelacion del estudio: en dinero solo lo pagado con capturas; lo pagado con credito
-- vuelve a sus creditos de origen con el vencimiento ampliado (el mayor entre el suyo y la vigencia desde hoy). Si no
-- hubo capturas no se crea devolucion en dinero y la eleccion igual queda `devolucion` (el cliente no queda sin nada).
create or replace function public.elegir_estudio_devolucion(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
  v_pagado numeric;
  v_credito numeric;
  v_dinero numeric;
  v_limite timestamptz;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.id_cliente <> v_uid and not public.es_administrador() then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_pagado := public.pagado_neto(r.id);
  if r.estado <> 'cancelada' or r.eleccion_estudio is distinct from 'pendiente' or v_pagado <= 0 then
    raise exception 'eleccion_no_disponible' using errcode = 'P0001';
  end if;
  v_credito := public.devolver_credito_aplicado(r.id, v_pagado, (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  v_dinero := v_pagado - v_credito;
  v_limite := public.sumar_dias_habiles(now(), 7);
  if v_dinero > 0 then
    insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado, estado, monto_aprobado, decidida_en, limite)
    values (r.id, r.id_cliente, 'estudio', 'Devolución íntegra por cancelación del estudio', v_dinero, 'aprobada', v_dinero,
            now(), v_limite);
  end if;
  update public.reserva set eleccion_estudio = 'devolucion' where id = r.id;
  if v_uid = r.id_cliente then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'eleccion_estudio_resuelta', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre, 'opcion', 'devolucion',
                              'monto', v_dinero, 'limite', v_limite)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  end if;
end;
$$;
