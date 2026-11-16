-- RF-06 (auditoria A, ronda 2): avanzar_reservas ve el pago de saldo que se esta confirmando.
-- En una sola sentencia sql, el aviso `reserva_finalizada_saldo` leia los pagos con la instantanea anterior a esperar el
-- bloqueo de la reserva que toma validar_pago_nuevo, y avisaba del saldo aunque el cliente acabara de pagar. Como
-- caducar_reservas: primero se bloquean las candidatas (en orden de id, espera al pago sin confirmar) y luego el update
-- y los avisos van en otra sentencia, cuya instantanea ya incluye ese pago. Orden de bloqueo: solo reservas.
create or replace function public.avanzar_reservas()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_avanzadas integer;
begin
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
  return v_avanzadas;
end;
$$;

-- shortcut: validar_pago_nuevo mantiene bloqueadas la cuota y la reserva mientras el backend sube la captura a
-- Storage (hasta TIMEOUT_SEGUNDOS = 10 s): cron, cancelaciones y reservas de esa sala esperan ese tiempo como maximo.
-- Mejorar si la carga crece (subir primero y confirmar despues, o reservar el pago en un estado intermedio).
comment on function public.validar_pago_nuevo() is
  'shortcut: bloquea cuota y reserva durante la subida a Storage (hasta 10 s de espera para cron, cancelaciones y '
  'reservas de esa sala); mejorar si la carga crece.';
