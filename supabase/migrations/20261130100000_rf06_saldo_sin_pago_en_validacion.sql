-- RF-06: no se avisa del saldo si la cuota `al_terminar` ya tiene un pago en validacion (el cliente pago y espera).
create or replace function public.avanzar_reservas()
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
      and not exists (select 1 from public.comprobante_pago p
                      where p.id_cuota = c.id and p.estado = 'pendiente_validacion')
    returning 1
  )
  select count(*)::int from avanzadas;
$$;
