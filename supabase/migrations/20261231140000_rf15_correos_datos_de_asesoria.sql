-- RF-15: los avisos al cliente de una asesoria (creacion, pago aprobado o rechazado, inasistencia) se encolan sin
-- profesional, modalidad, lugar ni enlace, y la creacion sin la cuota a pagar. En vez de redefinir las funciones que los
-- insertan, el envio los completa al leer: esta funcion devuelve, por notificacion de una asesoria, esos datos (los
-- vigentes) mas el horario y la cuota `al_reservar`. Los datos del aviso mandan sobre estos; la sala no devuelve filas.
create function public.datos_asesoria_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, datos jsonb)
language sql
stable
security definer
set search_path = ''
as $$
  select n.id,
         coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
         || jsonb_build_object('inicio', r.inicio, 'fin', r.fin, 'id_cuota', c.id)
  from public.notificacion n
  join public.reserva r on r.id = public.uuid_o_nulo(n.datos ->> 'id_reserva') and r.tipo = 'asesoria'
  left join lateral (select id from public.cuota where id_reserva = r.id and hito = 'al_reservar'
                     order by id limit 1) c on true
  where n.id = any (p_ids);
$$;

revoke all on function public.datos_asesoria_para_correo(uuid[]) from public, anon, authenticated, service_role;
grant execute on function public.datos_asesoria_para_correo(uuid[]) to bugalu_api;
