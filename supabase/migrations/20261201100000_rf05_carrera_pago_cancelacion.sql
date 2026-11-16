-- RF-05 (auditoria A, ronda 1): registrar un pago ya no se cruza con cancelar o caducar la reserva (RN-18, RN-20).
-- Orden de bloqueo unico: cuota -> reserva (como aprobar_pago y rechazar_pago); cancelar_reserva, caducar_reservas y
-- avanzar_reservas solo bloquean reservas, asi que no hay interbloqueo.

-- Antes de insertar un pago: bloquea tambien la reserva (cancelar y caducar esperan al commit del pago y lo ven) y
-- rechaza una pre_reservada con el plazo vencido aunque el cron aun no la haya caducado.
create or replace function public.validar_pago_nuevo()
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
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente is distinct from (select auth.uid()) or new.id_cliente <> r.id_cliente then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'pago_en_validacion' using errcode = 'P0001';
  end if;
  if r.estado = 'cancelada' or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada')) then
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

-- Primero bloquea las candidatas (espera a un pago sin confirmar) y despues actualiza en una sentencia nueva, cuya
-- instantanea ya ve ese pago: en una sola sentencia sql la caducidad usaba la instantanea anterior a la espera.
create or replace function public.caducar_reservas(
  p_id_sala uuid default null, p_desde timestamptz default null, p_hasta timestamptz default null)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_caducadas integer;
begin
  perform 1 from public.reserva r
  where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_pagos(r.id)
    and (p_id_sala is null
         or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)))
  order by r.id
  for update;
  with caducadas as (
    update public.reserva r
    set estado = 'cancelada', motivo_cancelacion = 'caducada'
    where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_pagos(r.id)
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
  select count(*)::int into v_caducadas from caducadas;
  return v_caducadas;
end;
$$;
