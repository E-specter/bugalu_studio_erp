-- Corrige 20261228100000: `datos_reserva_para_correo` debe partir de la version vigente (RF-16, 20261222110000), que
-- tolera un id_reserva invalido con `uuid_o_nulo`: ese aviso queda sin fila y los demas conservan su evento.
-- Conserva `ubicacion` (asesorias) y los permisos: solo `bugalu_api`.
create or replace function public.datos_reserva_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, inicio timestamptz, fin timestamptz, servicio text, sala text,
               tiene_evento boolean, ubicacion text)
language sql
stable
security definer
set search_path = ''
as $$
  select n.id, r.inicio, r.fin,
         case when r.tipo = 'asesoria'
              then 'Asesoría artística con ' || coalesce(pp.nombre_artistico, pu.nombre, 'tu profesional')
              else s.nombre end,
         case when r.tipo = 'asesoria' then case a.modalidad when 'virtual' then 'Videollamada' else 'Presencial' end
              else sa.nombre end,
         exists (
           select 1 from public.notificacion p
           where p.tipo = 'pago_aprobado' and p.id <> n.id
             and public.uuid_o_nulo(p.datos ->> 'id_reserva') = r.id
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         ),
         case when r.tipo = 'asesoria'
              then coalesce(case when a.modalidad = 'virtual' then a.enlace else a.lugar end, 'Por confirmar') end
  from public.notificacion n
  join public.reserva r on r.id = public.uuid_o_nulo(n.datos ->> 'id_reserva')
  left join public.servicio s on s.id = r.id_servicio
  left join public.sala_tecnica sa on sa.id = r.id_sala
  left join public.asesoria a on a.id_reserva = r.id
  left join public.perfil_profesional pp on pp.id = r.id_profesional
  left join public.usuario pu on pu.id = r.id_profesional
  where n.id = any (p_ids);
$$;
