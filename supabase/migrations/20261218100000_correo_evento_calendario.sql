-- ADR-016: los correos de reserva confirmada, reprogramada y cancelada llevan un evento de calendario (.ics).
-- La bandeja (rol `bugalu_api`) necesita de la reserva el horario, el servicio y la sala, y saber si la reserva
-- ya tenia evento antes del aviso. Una funcion de solo lectura evita darle a `bugalu_api` lectura sobre `reserva`.
--
-- "Tiene evento": existe un `pago_aprobado` de la misma reserva con `reserva_confirmada` anterior o simultaneo al aviso.
-- Cubre sin columnas nuevas: la pre-reserva cancelada o reprogramada no recibe evento; la cancelada por el estudio y
-- luego reprogramada sin costo recibe CANCEL y despues un REQUEST que la devuelve al calendario.
create function public.datos_reserva_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, inicio timestamptz, fin timestamptz, servicio text, sala text, tiene_evento boolean)
language sql
stable
security definer
set search_path = ''
as $$
  select n.id, r.inicio, r.fin, s.nombre, sa.nombre,
         exists (
           select 1 from public.notificacion p
           where p.tipo = 'pago_aprobado' and p.id <> n.id
             and p.datos ->> 'id_reserva' = n.datos ->> 'id_reserva'
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         )
  from public.notificacion n
  join public.reserva r on r.id::text = n.datos ->> 'id_reserva'
  join public.servicio s on s.id = r.id_servicio
  join public.sala_tecnica sa on sa.id = r.id_sala
  where n.id = any (p_ids);
$$;
revoke all on function public.datos_reserva_para_correo(uuid[]) from public, anon, authenticated;
grant execute on function public.datos_reserva_para_correo(uuid[]) to bugalu_api;
