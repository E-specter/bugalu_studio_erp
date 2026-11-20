-- RF-15 etapa C (backend C1): recordatorio de 24 h (CA-14) a toda asesoria `confirmada` (cliente y profesional) y a toda
-- reserva de sala `confirmada` (cliente), una vez por horario. `recordatorio_inicio` guarda el `inicio` ya atendido:
-- una reprogramacion lo cambia y vuelve a tocar; una confirmacion con menos de 24 h lo da por atendido (no se envia).
alter table public.reserva add column recordatorio_inicio timestamptz;

create function public.marcar_recordatorio_al_confirmar()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.inicio - now() < interval '24 hours' then
    new.recordatorio_inicio := new.inicio;
  end if;
  return new;
end;
$$;
create trigger reserva_recordatorio_confirmada before update of estado on public.reserva
  for each row when (old.estado is distinct from 'confirmada' and new.estado = 'confirmada')
  execute function public.marcar_recordatorio_al_confirmar();

-- El UPDATE bloquea cada fila: dos corridas a la vez no la toman dos veces (la segunda vuelve a evaluar el filtro).
create function public.enviar_recordatorios()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_enviados integer;
begin
  with tocadas as (
    update public.reserva r set recordatorio_inicio = r.inicio
    where r.estado = 'confirmada' and r.inicio > now() and r.inicio <= now() + interval '24 hours'
      and r.recordatorio_inicio is distinct from r.inicio
    returning r.id, r.folio, r.tipo, r.inicio, r.fin, r.id_cliente, r.id_profesional, r.id_sala, r.id_servicio,
              (r.parametros_aplicados ->> 'minutos_tolerancia_inasistencia')::int as tolerancia
  ), de_asesoria as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'recordatorio_asesoria', u.email,
           jsonb_build_object('id_reserva', t.id, 'folio', t.folio, 'inicio', t.inicio, 'fin', t.fin, 'para', d.para,
                              'profesional', coalesce(pp.nombre_artistico, pu.nombre), 'cliente', cu.nombre,
                              'duracion', (extract(epoch from t.fin - t.inicio) / 60)::int, 'modalidad', a.modalidad,
                              'lugar', a.lugar, 'enlace', a.enlace, 'tolerancia', t.tolerancia)
    from tocadas t
    join public.asesoria a on a.id_reserva = t.id
    cross join lateral (values ('cliente', t.id_cliente), ('profesional', t.id_profesional)) d(para, id_usuario)
    join auth.users u on u.id = d.id_usuario
    left join public.usuario cu on cu.id = t.id_cliente
    left join public.usuario pu on pu.id = t.id_profesional
    left join public.perfil_profesional pp on pp.id = t.id_profesional
    where t.tipo = 'asesoria'
    returning 1
  ), de_sala as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'recordatorio_reserva', u.email,
           jsonb_strip_nulls(jsonb_build_object(
             'id_reserva', t.id, 'folio', t.folio, 'inicio', t.inicio, 'fin', t.fin, 'servicio', s.nombre,
             'sala', sa.nombre, 'tolerancia', t.tolerancia,
             'saldo', (select c.monto - c.pagado from public.cuota c
                       where c.id_reserva = t.id and c.hito = 'al_terminar' and c.estado = 'pendiente')))
    from tocadas t
    join auth.users u on u.id = t.id_cliente
    left join public.servicio s on s.id = t.id_servicio
    left join public.sala_tecnica sa on sa.id = t.id_sala
    where t.tipo = 'sala'
    returning 1
  )
  select (select count(*) from de_asesoria) + (select count(*) from de_sala) into v_enviados;
  return v_enviados;
end;
$$;
revoke all on function public.enviar_recordatorios() from public, anon, authenticated;
select cron.schedule('enviar_recordatorios', '*/5 * * * *', 'select public.enviar_recordatorios()');
