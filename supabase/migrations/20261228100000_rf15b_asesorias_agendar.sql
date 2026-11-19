-- RF-15 etapa B (backend B1): la asesoria es una fila de `reserva` con tipo 'asesoria' mas la tabla 1:1 `asesoria`
-- (decision 1). Reutiliza cuotas, pagos, creditos y caducidad. Aqui: agendar, doble agendamiento, pago y caducidad,
-- lugar o enlace y correos. La politica de RF-18 para asesorias (cancelar, reprogramar, inasistencia) es la etapa B2.

-- 1. `reserva` suma tipo y profesional; la sala y el servicio pasan a ser solo de sala.
alter table public.reserva
  add column tipo text not null default 'sala' check (tipo in ('sala', 'asesoria')),
  add column id_profesional uuid references public.perfil_profesional (id);
alter table public.reserva alter column id_sala drop not null, alter column id_servicio drop not null;
alter table public.reserva add constraint reserva_tipo_coherente check (
  (tipo = 'sala' and id_sala is not null and id_servicio is not null and id_profesional is null)
  or (tipo = 'asesoria' and id_profesional is not null and id_sala is null and id_servicio is null
      and id_franja is null));
-- `realizada` es solo de asesorias; la asesoria no pasa por en_curso ni finalizada.
alter table public.reserva drop constraint reserva_estado_check;
alter table public.reserva add constraint reserva_estado_check check (estado in
  ('pre_reservada', 'confirmada', 'en_curso', 'finalizada', 'realizada', 'cancelada', 'no_asistio'));
alter table public.reserva add constraint reserva_estado_por_tipo check (
  (tipo = 'sala' and estado <> 'realizada')
  or (tipo = 'asesoria' and estado in ('pre_reservada', 'confirmada', 'realizada', 'cancelada', 'no_asistio')));

-- CA-07: dos asesorias no cancelas del mismo profesional no se solapan, sin margen entre ellas.
alter table public.reserva add exclude using gist (id_profesional with =, tstzrange(inicio, fin) with &&)
  where (estado <> 'cancelada');

-- 2. Folio: `R-AAAA-NNNNN` en sala, `A-AAAA-NNNNN` en asesoria (secuencia propia, sin saltos en las R-).
create sequence public.asesoria_folio_seq;
alter table public.reserva alter column folio drop default;

-- La base caduca las pre-reservas vencidas sin capturas que estorban a una nueva: por sala o por profesional.
drop function public.caducar_reservas(uuid, timestamptz, timestamptz);
create function public.caducar_reservas(
  p_id_sala uuid default null, p_desde timestamptz default null, p_hasta timestamptz default null,
  p_id_profesional uuid default null)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_caducadas integer;
  v_ids uuid[];
begin
  perform 1 from public.reserva r
  where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_capturas(r.id)
    and ((p_id_sala is null and p_id_profesional is null)
         or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta))
         or (r.id_profesional = p_id_profesional and tstzrange(r.inicio, r.fin) && tstzrange(p_desde, p_hasta)))
  order by r.id
  for update;
  with caducadas as (
    update public.reserva r
    set estado = 'cancelada', motivo_cancelacion = 'caducada'
    where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_capturas(r.id)
      and ((p_id_sala is null and p_id_profesional is null)
           or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta))
           or (r.id_profesional = p_id_profesional and tstzrange(r.inicio, r.fin) && tstzrange(p_desde, p_hasta)))
    returning r.id, r.id_cliente, r.folio, r.inicio, r.fin
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_caducada', u.email,
           jsonb_build_object('id_reserva', c.id, 'folio', c.folio, 'inicio', c.inicio, 'fin', c.fin)
    from caducadas c join auth.users u on u.id = c.id_cliente
    returning 1
  )
  select count(*)::int, coalesce(array_agg(id), '{}') into v_caducadas, v_ids from caducadas;
  perform public.devolver_credito_aplicado(x) from unnest(v_ids) x;
  return v_caducadas;
end;
$$;
revoke all on function public.caducar_reservas(uuid, timestamptz, timestamptz, uuid) from public, anon, authenticated;
grant execute on function public.caducar_reservas(uuid, timestamptz, timestamptz, uuid) to service_role;

create or replace function public.preparar_reserva()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.fin_buffer := case when new.tipo = 'asesoria' then new.fin else new.fin + interval '30 minutes' end;
  if tg_op = 'INSERT' then
    if new.folio is null then
      new.folio := case when new.tipo = 'asesoria'
        then 'A-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('public.asesoria_folio_seq')::text, 5, '0')
        else 'R-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('public.reserva_folio_seq')::text, 5, '0') end;
    end if;
    if new.estado <> 'cancelada' then
      if new.tipo = 'asesoria' then
        perform public.caducar_reservas(null, new.inicio, new.fin, new.id_profesional);
      else
        perform public.caducar_reservas(new.id_sala, new.inicio, new.fin_buffer);
      end if;
    end if;
  end if;
  return new;
end;
$$;

-- Barrera al agendar (CA-05, CA-06): perfil publicado, duracion con precio y bloque publicado que la contiene.
-- Bloquea el perfil igual que retirar_horario: agendar y retirar un horario a la vez se serializan.
create function public.validar_asesoria_nueva()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform 1 from public.perfil_profesional where id = new.id_profesional for update;
  if not public.perfil_publicado(new.id_profesional) then
    raise exception 'profesional_no_publicado' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.precio_asesoria p
                 where p.id_profesional = new.id_profesional and p.minutos * interval '1 minute' = new.fin - new.inicio) then
    raise exception 'duracion_no_ofrecida' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.horario_profesional h
                 where h.id_profesional = new.id_profesional and h.inicio <= new.inicio and h.fin >= new.fin) then
    raise exception 'fuera_de_horario' using errcode = 'P0001';
  end if;
  return new;
end;
$$;
revoke all on function public.validar_asesoria_nueva() from public, anon, authenticated;
-- Antes que `reserva_preparar` (orden alfabetico): el bloqueo del perfil precede a la caducidad y a la exclusion.
create trigger reserva_asesoria_valida before insert on public.reserva
  for each row when (new.tipo = 'asesoria') execute function public.validar_asesoria_nueva();

-- 3. RLS de `reserva`: el personal no ve asesorias (el administrador si); el profesional ve las suyas.
drop policy reserva_lee on public.reserva;
create policy reserva_lee on public.reserva for select to authenticated using (
  id_cliente = (select auth.uid())
  or (public.es_personal() and (tipo = 'sala' or public.es_administrador()))
  or (tipo = 'asesoria' and id_profesional = (select auth.uid()))
);
grant insert (tipo, id_profesional) on public.reserva to authenticated;
-- Las cuotas y las reprogramaciones cuelgan de la visibilidad de la reserva: el profesional no las ve (CA-16).
drop policy cuota_lee on public.cuota;
create policy cuota_lee on public.cuota for select to authenticated
  using (not public.es_profesional() and exists (select 1 from public.reserva r where r.id = cuota.id_reserva));
drop policy reprogramacion_lee on public.reprogramacion;
create policy reprogramacion_lee on public.reprogramacion for select to authenticated
  using (not public.es_profesional() and exists (select 1 from public.reserva r where r.id = reprogramacion.id_reserva));

-- 4. Tabla 1:1 `asesoria`: modalidad, lugar o enlace, notas internas y cierre. El estado, el precio y las notas
-- solo cambian por funciones; el cliente no lee las notas (sin privilegio de columna).
create table public.asesoria (
  id_reserva uuid primary key references public.reserva (id) on delete cascade,
  modalidad text not null check (modalidad in ('presencial', 'virtual')),
  lugar text check (lugar is null or char_length(lugar) between 1 and 300),
  enlace text check (enlace is null or enlace ~ '^https://meet\.google\.com/[A-Za-z0-9/_?=&.%-]{1,200}$'),
  notas text check (notas is null or char_length(notas) <= 5000),
  realizada_en timestamptz
);
alter table public.asesoria enable row level security;
revoke all on public.asesoria from anon, authenticated;
grant select (id_reserva, modalidad, lugar, enlace, realizada_en) on public.asesoria to authenticated;
grant insert (id_reserva, modalidad) on public.asesoria to authenticated;
create policy asesoria_lee on public.asesoria for select to authenticated
  using (exists (select 1 from public.reserva r where r.id = asesoria.id_reserva));
create policy asesoria_inserta on public.asesoria for insert to authenticated
  with check (exists (select 1 from public.reserva r
                      where r.id = asesoria.id_reserva and r.id_cliente = (select auth.uid()) and r.tipo = 'asesoria'));

-- Notas internas: solo su profesional y el administrador (nunca el cliente).
create function public.notas_de_asesoria(p_id uuid)
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select a.notas from public.asesoria a join public.reserva r on r.id = a.id_reserva
  where a.id_reserva = p_id and (r.id_profesional = (select auth.uid()) or public.es_administrador());
$$;
revoke all on function public.notas_de_asesoria(uuid) from public, anon;
grant execute on function public.notas_de_asesoria(uuid) to authenticated;

-- CA-09: modalidad, lugar o enlace. Solo su profesional o el administrador, en pre_reservada o confirmada y antes
-- de su fin. Cada cambio avisa al cliente y al profesional (con el .ics actualizado, lo arma el backend).
create function public.cambiar_encuentro(p_id uuid, p_modalidad text, p_lugar text, p_enlace text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
  a public.asesoria%rowtype;
  v_profesional text;
  v_cliente text;
begin
  select * into r from public.reserva where id = p_id and tipo = 'asesoria' for update;
  if not found or v_uid is null
     or not (r.id_cliente = v_uid or r.id_profesional = v_uid or public.es_administrador()) then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if not (r.id_profesional = v_uid or public.es_administrador()) then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada') or r.fin <= now() then
    raise exception 'no_editable' using errcode = 'P0001';
  end if;
  select * into a from public.asesoria where id_reserva = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if (a.modalidad, a.lugar, a.enlace) is not distinct from (p_modalidad, p_lugar, p_enlace) then
    return;
  end if;
  update public.asesoria set modalidad = p_modalidad, lugar = p_lugar, enlace = p_enlace where id_reserva = p_id;
  select coalesce(pp.nombre_artistico, pu.nombre) into v_profesional
    from public.usuario pu left join public.perfil_profesional pp on pp.id = pu.id where pu.id = r.id_profesional;
  select nombre into v_cliente from public.usuario where id = r.id_cliente;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'asesoria_encuentro_cambiado', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                            'modalidad', p_modalidad, 'lugar', p_lugar, 'enlace', p_enlace,
                            'profesional', v_profesional, 'cliente', v_cliente)
  from auth.users u where u.id in (r.id_cliente, r.id_profesional);
end;
$$;
revoke all on function public.cambiar_encuentro(uuid, text, text, text) from public, anon;
grant execute on function public.cambiar_encuentro(uuid, text, text, text) to authenticated;

-- Disponibilidad (CA-05): tramos ocupados del profesional, sin decir de quien; `propia` para el cliente.
-- No cuentan las canceladas ni las pre-reservadas vencidas sin capturas (el horario ya esta libre).
create function public.ocupacion_profesional(p_id uuid, p_desde timestamptz, p_hasta timestamptz)
returns table (inicio timestamptz, fin timestamptz, propia boolean)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin, coalesce(r.id_cliente = (select auth.uid()), false)
  from public.reserva r
  where r.id_profesional = p_id and public.puede_ver_perfil(p_id)
    and r.estado <> 'cancelada'
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_capturas(r.id))
    and tstzrange(r.inicio, r.fin) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;
revoke all on function public.ocupacion_profesional(uuid, timestamptz, timestamptz) from public;
grant execute on function public.ocupacion_profesional(uuid, timestamptz, timestamptz) to anon, authenticated;

-- 5. `avanzar_reservas` no toca la asesoria `confirmada`: la cierra su profesional (Realizada o No asistio).
-- La pre-reservada con pago en validacion que llega a su fin si pasa a no asistio (RF-18, CA-12).
create or replace function public.avanzar_reservas()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_avanzadas integer;
  v_sin_asistir integer := 0;
  v_id uuid;
begin
  perform public.caducar_reservas();
  for v_id in
    select r.id from public.reserva r
    where r.estado = 'pre_reservada' and r.fin <= now() and public.tiene_capturas(r.id) order by r.id
  loop
    perform 1 from public.cuota where id_reserva = v_id order by id for update;
    perform 1 from public.reserva where id = v_id and estado = 'pre_reservada' for update; -- tras la espera, vuelve a mirar
    if found then
      perform public.aplicar_inasistencia(v_id, null);
      v_sin_asistir := v_sin_asistir + 1;
    end if;
  end loop;
  perform 1 from public.reserva r
  where r.tipo = 'sala' and ((r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now()))
  order by r.id
  for update;
  with avanzadas as (
    update public.reserva r
    set estado = case when r.fin <= now() then 'finalizada' else 'en_curso' end
    where r.tipo = 'sala' and ((r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now()))
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
  return v_avanzadas + v_sin_asistir;
end;
$$;

-- 6. Condiciones: la aceptacion `asesoria` se guarda en la misma transaccion que el agendamiento.
create or replace function public.aceptar_condiciones(p_contexto text, p_id_operacion uuid, p_version text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.texto_legal;
begin
  if auth.uid() is null then
    raise exception 'Sin sesion.' using errcode = '42501';
  end if;
  if p_contexto not in ('reserva', 'asesoria', 'pago') or (p_contexto in ('reserva', 'asesoria') and p_version is null) then
    raise exception 'Contexto no admitido.' using errcode = '22023';
  end if;
  select * into v from public.textos_vigentes() t where t.tipo = 'condiciones_contratacion';
  if not found then
    if p_contexto = 'pago' then
      return;
    end if;
    raise exception 'texto_desactualizado';
  end if;
  if p_version is not null and p_version <> v.version then
    raise exception 'texto_desactualizado';
  end if;
  if p_contexto in ('reserva', 'asesoria') then
    if not exists (select 1 from public.reserva
                   where id = p_id_operacion and id_cliente = auth.uid()
                     and tipo = case p_contexto when 'asesoria' then 'asesoria' else 'sala' end) then
      raise exception 'La reserva no es tuya.' using errcode = '42501';
    end if;
  elsif not exists (select 1 from public.comprobante_pago where id = p_id_operacion and id_cliente = auth.uid()) then
    raise exception 'El pago no es tuyo.' using errcode = '42501';
  end if;
  perform public.insertar_aceptacion(auth.uid(), v.tipo, v.version, p_contexto, p_id_operacion, null);
end;
$$;

-- 7. Correos. El aviso de creacion (datos para pagar) sirve a la asesoria; el de confirmacion al profesional y el
-- de cambio de lugar o enlace son tipos nuevos. El pago aprobado del cliente ya existe.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in (
  'reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
  'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
  'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
  'devolucion_decidida', 'devolucion_realizada', 'reserva_reprogramada', 'eleccion_estudio_resuelta',
  'reclamacion_registrada', 'reclamacion_recibida', 'reclamacion_respondida', 'reclamaciones_por_vencer',
  'asesoria_confirmada_profesional', 'asesoria_encuentro_cambiado'));

create or replace function public.encolar_aviso_reserva(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_dueno uuid;
begin
  select id_cliente into v_dueno from public.reserva where id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if v_dueno is distinct from (select auth.uid()) and not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'reserva_creada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                            'vence_pago', r.vence_pago, 'servicio', coalesce(s.nombre, 'Asesoría artística'),
                            'total', r.total)
  from public.reserva r
  join auth.users u on u.id = r.id_cliente
  left join public.servicio s on s.id = r.id_servicio
  where r.id = p_id
    and not exists (select 1 from public.notificacion n
                    where n.tipo = 'reserva_creada' and n.datos ->> 'id_reserva' = r.id::text);
end;
$$;

-- Al confirmarse (pago aprobado o credito) la asesoria avisa a su profesional, con el evento de calendario.
create function public.avisar_asesoria_confirmada()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.notificacion (tipo, destinatario, datos)
  select 'asesoria_confirmada_profesional', u.email,
         jsonb_build_object('id_reserva', new.id, 'folio', new.folio, 'inicio', new.inicio, 'fin', new.fin,
                            'cliente', c.nombre, 'modalidad', a.modalidad, 'lugar', a.lugar, 'enlace', a.enlace,
                            'reserva_confirmada', true)
  from auth.users u
  left join public.usuario c on c.id = new.id_cliente
  left join public.asesoria a on a.id_reserva = new.id
  where u.id = new.id_profesional;
  return null;
end;
$$;
revoke all on function public.avisar_asesoria_confirmada() from public, anon, authenticated;
create trigger reserva_asesoria_confirmada after update of estado on public.reserva
  for each row when (new.tipo = 'asesoria' and old.estado = 'pre_reservada' and new.estado = 'confirmada')
  execute function public.avisar_asesoria_confirmada();

-- El evento de calendario de una asesoria: titulo con el profesional, `ubicacion` con el lugar o el enlace.
drop function public.datos_reserva_para_correo(uuid[]);
create function public.datos_reserva_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, inicio timestamptz, fin timestamptz, servicio text, sala text,
               tiene_evento boolean, ubicacion text)
language sql
stable
security definer
set search_path = ''
as $$
  with n as materialized (
    select x.id, x.creada_en, (x.datos ->> 'id_reserva')::uuid as id_reserva
    from public.notificacion x where x.id = any (p_ids)
  )
  select n.id, r.inicio, r.fin,
         case when r.tipo = 'asesoria'
              then 'Asesoría artística con ' || coalesce(pp.nombre_artistico, pu.nombre, 'tu profesional')
              else s.nombre end,
         case when r.tipo = 'asesoria' then case a.modalidad when 'virtual' then 'Videollamada' else 'Presencial' end
              else sa.nombre end,
         exists (
           select 1 from public.notificacion p
           where p.tipo = 'pago_aprobado' and p.id <> n.id
             and (p.datos ->> 'id_reserva')::uuid = n.id_reserva
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         ),
         case when r.tipo = 'asesoria'
              then coalesce(case when a.modalidad = 'virtual' then a.enlace else a.lugar end, 'Por confirmar') end
  from n
  join public.reserva r on r.id = n.id_reserva
  left join public.servicio s on s.id = r.id_servicio
  left join public.sala_tecnica sa on sa.id = r.id_sala
  left join public.asesoria a on a.id_reserva = r.id
  left join public.perfil_profesional pp on pp.id = r.id_profesional
  left join public.usuario pu on pu.id = r.id_profesional;
$$;
revoke all on function public.datos_reserva_para_correo(uuid[]) from public, anon, authenticated;
grant execute on function public.datos_reserva_para_correo(uuid[]) to bugalu_api;
