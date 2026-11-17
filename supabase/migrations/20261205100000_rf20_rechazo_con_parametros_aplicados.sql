-- RF-20 CA-07 (correccion de la auditoria A): al rechazar un pago, el plazo se extiende con las horas de pago que
-- la reserva guardo al crearse (`parametros_aplicados`), no con el parametro vigente.
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
  if r.estado = 'pre_reservada' and not public.tiene_pagos(r.id) then
    update public.reserva
    set vence_pago = greatest(coalesce(vence_pago, now()),
      least(inicio, now() + make_interval(hours => (r.parametros_aplicados ->> 'horas_limite_pago')::int)))
    where id = r.id;
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_rechazado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'motivo', v_motivo)
  from auth.users u where u.id = p.id_cliente;
end;
$$;
