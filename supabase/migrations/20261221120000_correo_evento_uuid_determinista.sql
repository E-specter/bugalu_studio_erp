-- La conversion a uuid de id_reserva se evalua siempre sobre los avisos pedidos (el planificador podia saltarsela si
-- `reserva` estaba vacia): un id invalido falla de forma determinista y la bandeja lo degrada a "sin evento".
create or replace function public.datos_reserva_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, inicio timestamptz, fin timestamptz, servicio text, sala text, tiene_evento boolean)
language sql
stable
security definer
set search_path = ''
as $$
  with n as materialized (
    select x.id, x.creada_en, (x.datos ->> 'id_reserva')::uuid as id_reserva
    from public.notificacion x where x.id = any (p_ids)
  )
  select n.id, r.inicio, r.fin, s.nombre, sa.nombre,
         exists (
           select 1 from public.notificacion p
           where p.tipo = 'pago_aprobado' and p.id <> n.id
             and (p.datos ->> 'id_reserva')::uuid = n.id_reserva
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         )
  from n
  join public.reserva r on r.id = n.id_reserva
  join public.servicio s on s.id = r.id_servicio
  join public.sala_tecnica sa on sa.id = r.id_sala;
$$;
