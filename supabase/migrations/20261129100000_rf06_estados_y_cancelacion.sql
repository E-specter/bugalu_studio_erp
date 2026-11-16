-- RF-06: estados automaticos de la reserva (RN-23), cancelacion con pagos y nota (D-11 v1, ADR-010),
-- avisos de finalizacion y cancelacion, y "pago por validar" visible para el personal.

-- Avisos nuevos.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
   'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio'));

-- Nota del Administrador sobre el reembolso: hasta 300 caracteres, sin controles (se permiten salto y tabulador).
alter table public.reserva add column nota_cancelacion text
  check (char_length(nota_cancelacion) between 1 and 300 and nota_cancelacion !~ '[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]');

-- RN-23: confirmada -> en_curso al llegar `inicio`; confirmada|en_curso -> finalizada al llegar `fin`.
-- La pre_reservada no avanza. Al finalizar con la cuota `al_terminar` pendiente se encola el aviso de saldo
-- (una sola vez: una reserva finaliza una sola vez). Devuelve cuantas reservas avanzo.
create function public.avanzar_reservas()
returns integer
language sql
security definer
set search_path = ''
as $$
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
    returning 1
  )
  select count(*)::int from avanzadas;
$$;
revoke all on function public.avanzar_reservas() from public, anon, authenticated;

select cron.schedule('avanzar_reservas', '* * * * *', 'select public.avanzar_reservas()');

-- Cancelar (RN-20, D-11 v1). El dueno con pagos recibe `tiene_pagos`; el administrador con pagos debe dar nota
-- (P0001 `nota_requerida`); la nota se recorta y admite 1-300 caracteres sin controles (22023 `nota_invalida`).
-- Avisa a los administradores si cancela el cliente y al cliente (con la nota) si cancela el administrador.
drop function public.cancelar_reserva(uuid);
create function public.cancelar_reserva(p_id uuid, p_nota text default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_dueno boolean;
  v_nota text := nullif(btrim(p_nota), '');
begin
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_dueno := r.id_cliente = v_uid;
  if v_uid is null or (not v_dueno and not public.es_administrador()) then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada') then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if char_length(v_nota) > 300 or v_nota ~ '[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]' then
    raise exception 'nota_invalida' using errcode = '22023';
  end if;
  if public.tiene_pagos(r.id) then
    if v_dueno then
      raise exception 'tiene_pagos' using errcode = 'P0001';
    elsif v_nota is null then
      raise exception 'nota_requerida' using errcode = 'P0001';
    end if;
  end if;
  update public.reserva
  set estado = 'cancelada', motivo_cancelacion = case when v_dueno then 'cliente' else 'administrador' end,
      nota_cancelacion = v_nota
  where id = p_id;
  if v_dueno then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_cliente', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre,
                              'inicio', r.inicio, 'fin', r.fin)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  else
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_estudio', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'nota', v_nota)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;
revoke all on function public.cancelar_reserva(uuid, text) from public, anon;
grant execute on function public.cancelar_reserva(uuid, text) to authenticated;

-- El personal no ve comprobantes (RLS), pero la agenda marca "pago por validar": esta funcion devuelve solo
-- ese dato, y unicamente a personal y administrador (a los demas, siempre false).
create function public.hay_pago_por_validar(p_id_reserva uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.es_personal() and exists (
    select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
    where c.id_reserva = p_id_reserva and p.estado = 'pendiente_validacion');
$$;
revoke all on function public.hay_pago_por_validar(uuid) from public, anon;
grant execute on function public.hay_pago_por_validar(uuid) to authenticated;
