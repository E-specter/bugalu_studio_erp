-- RF-15 etapa C (backend C1): cerrar la asesoria (CA-12), notas y constancia (CA-13). Funciones nuevas: no
-- redefinen ninguna. `marcar_inasistencia` (20261229100000) ya cumple CA-12 con la tolerancia: se prueba, no se toca.

-- 1. Tipos de correo nuevos: la constancia al cliente y los dos recordatorios (migracion 20261231120000).
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in (
  'reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
  'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
  'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
  'devolucion_decidida', 'devolucion_realizada', 'reserva_reprogramada', 'eleccion_estudio_resuelta',
  'reclamacion_registrada', 'reclamacion_recibida', 'reclamacion_respondida', 'reclamaciones_por_vencer',
  'asesoria_confirmada_profesional', 'asesoria_encuentro_cambiado',
  'asesoria_cancelada_profesional', 'asesoria_reprogramada_profesional',
  'asesoria_realizada', 'recordatorio_asesoria', 'recordatorio_reserva'));

-- 2. La constancia es una instantanea inmutable: se escribe una vez, al marcar Realizada, y ningun usuario la lee por
-- la tabla (sin privilegio de columna): solo por `constancia_de_asesoria`.
alter table public.asesoria add column constancia jsonb;
create function public.constancia_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.constancia is not null and new.constancia is distinct from old.constancia then
    raise exception 'constancia_inmutable' using errcode = 'P0001';
  end if;
  return new;
end;
$$;
create trigger asesoria_constancia_inmutable before update of constancia on public.asesoria
  for each row execute function public.constancia_inmutable();

-- 3. Realizada (CA-12): su profesional o el administrador, desde el inicio, solo una `confirmada`, sin limite posterior.
-- Su cliente recibe 403; lo ajeno no existe (404), como `marcar_inasistencia`.
create function public.marcar_asesoria_realizada(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into r from public.reserva where id = p_id and tipo = 'asesoria';
  if not found or not (r.id_profesional = v_uid or public.es_administrador()) then
    if found and r.id_cliente = v_uid then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = p_id for update; -- tras la espera, vuelve a mirar el estado
  if r.estado <> 'confirmada' then
    raise exception 'no_aplicable' using errcode = 'P0001';
  end if;
  if now() < r.inicio then
    raise exception 'antes_del_inicio' using errcode = 'P0001';
  end if;
  update public.reserva set estado = 'realizada' where id = p_id;
  update public.asesoria a
  set realizada_en = now(),
      constancia = jsonb_build_object(
        'folio', r.folio,
        'cliente', jsonb_build_object('nombre', c.nombre, 'nombre_artistico', c.nombre_artistico),
        'profesional', jsonb_build_object(
          'nombre', pu.nombre, 'nombre_artistico', pp.nombre_artistico,
          'especialidades', (select coalesce(jsonb_agg(e.nombre order by e.nombre), '[]'::jsonb)
                             from public.perfil_especialidad pe
                             join public.especialidad_asesoria e on e.id = pe.id_especialidad
                             where pe.id_profesional = r.id_profesional)),
        'inicio', r.inicio, 'fin', r.fin, 'duracion', (extract(epoch from r.fin - r.inicio) / 60)::int,
        'modalidad', a.modalidad, 'emitida_en', now())
  from public.usuario c, public.usuario pu
  left join public.perfil_profesional pp on pp.id = pu.id
  where a.id_reserva = p_id and c.id = r.id_cliente and pu.id = r.id_profesional;
  -- El correo lleva el enlace a la constancia, nunca las notas.
  insert into public.notificacion (tipo, destinatario, datos)
  select 'asesoria_realizada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                            'profesional', coalesce(pp.nombre_artistico, pu.nombre),
                            'duracion', (extract(epoch from r.fin - r.inicio) / 60)::int, 'modalidad', a.modalidad)
  from auth.users u
  join public.asesoria a on a.id_reserva = r.id
  left join public.usuario pu on pu.id = r.id_profesional
  left join public.perfil_profesional pp on pp.id = r.id_profesional
  where u.id = r.id_cliente;
end;
$$;
revoke all on function public.marcar_asesoria_realizada(uuid) from public, anon;
grant execute on function public.marcar_asesoria_realizada(uuid) to authenticated;

-- 4. Notas internas (CA-13): su profesional o el administrador, en todo estado salvo `cancelada` (precision B7);
-- hasta 5000 caracteres; en blanco las borra. El cliente nunca las lee (`notas_de_asesoria`, sin privilegio de columna).
create function public.guardar_notas_asesoria(p_id uuid, p_texto text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into r from public.reserva where id = p_id and tipo = 'asesoria';
  if not found or not (r.id_profesional = v_uid or public.es_administrador()) then
    if found and r.id_cliente = v_uid then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if char_length(coalesce(p_texto, '')) > 5000 then
    raise exception 'texto_invalido' using errcode = '22023';
  end if;
  select * into r from public.reserva where id = p_id for update;
  if r.estado = 'cancelada' then
    raise exception 'no_editable' using errcode = 'P0001';
  end if;
  update public.asesoria set notas = case when btrim(coalesce(p_texto, '')) = '' then null else p_texto end
  where id_reserva = p_id;
end;
$$;
revoke all on function public.guardar_notas_asesoria(uuid, text) from public, anon;
grant execute on function public.guardar_notas_asesoria(uuid, text) to authenticated;

-- 5. Constancia (CA-13): su dueno, su profesional o el administrador; sin Realizada, 409.
create function public.constancia_de_asesoria(p_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_constancia jsonb;
begin
  select a.constancia into v_constancia
  from public.asesoria a join public.reserva r on r.id = a.id_reserva
  where a.id_reserva = p_id and v_uid is not null
    and (r.id_cliente = v_uid or r.id_profesional = v_uid or public.es_administrador());
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if v_constancia is null then
    raise exception 'constancia_no_disponible' using errcode = 'P0001';
  end if;
  return v_constancia;
end;
$$;
revoke all on function public.constancia_de_asesoria(uuid) from public, anon;
grant execute on function public.constancia_de_asesoria(uuid) to authenticated;
