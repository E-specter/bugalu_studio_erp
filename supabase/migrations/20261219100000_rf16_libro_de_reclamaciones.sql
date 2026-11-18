-- RF-16: Libro de Reclamaciones virtual (Ley 29571, D.S. 011-2011-PCM y modificatorias).
-- Hojas con correlativo propio que nunca se reinicia, plazo de 15 dias habiles (sin los feriados del catalogo) al
-- final del dia en Lima, alta publica (`anon`) solo por funcion, respuesta unica, hojas y adjuntos inmutables,
-- limite de 5 hojas por hora por IP, avisos por correo y cron diario de plazos. El backend es el unico camino a los datos.

-- 1. Avisos nuevos.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
   'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
   'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
   'devolucion_decidida', 'devolucion_realizada', 'reserva_reprogramada', 'eleccion_estudio_resuelta',
   'reclamacion_registrada', 'reclamacion_recibida', 'reclamacion_respondida', 'reclamaciones_por_vencer'));

-- 2. Hojas. El numero es el correlativo (secuencia propia, nunca se reinicia) con 9 cifras y el anio de presentacion.
create sequence public.hoja_reclamacion_correlativo;

create table public.hoja_reclamacion (
  id uuid primary key default gen_random_uuid(),
  correlativo bigint not null unique default nextval('public.hoja_reclamacion_correlativo'),
  anio smallint not null,
  numero text generated always as (lpad(correlativo::text, 9, '0') || '-' || anio::text) stored,
  creada_en timestamptz not null default now(),
  vence_respuesta timestamptz not null,
  origen text not null default 'web' check (origen in ('web', 'libro_fisico')),
  fecha_original timestamptz,
  numero_hoja_fisica text check (char_length(numero_hoja_fisica) between 1 and 50),
  id_cuenta uuid references public.usuario (id) on delete set null,
  revisar_spam boolean not null default false,
  -- 1) consumidor
  nombre text not null check (char_length(nombre) between 1 and 200),
  tipo_documento text not null check (tipo_documento in ('dni', 'ce', 'pasaporte')),
  documento text not null,
  domicilio text not null check (char_length(domicilio) between 1 and 200),
  telefono text check (char_length(telefono) between 1 and 20),
  correo text not null check (char_length(correo) <= 254 and correo ~ '^[^@[:space:]]+@[^@[:space:]]+$'),
  es_menor boolean not null default false,
  rep_nombre text check (char_length(rep_nombre) between 1 and 200),
  rep_domicilio text check (char_length(rep_domicilio) between 1 and 200),
  rep_telefono text check (char_length(rep_telefono) between 1 and 20),
  rep_correo text check (char_length(rep_correo) <= 254 and rep_correo ~ '^[^@[:space:]]+@[^@[:space:]]+$'),
  -- 2) bien contratado
  bien_tipo text not null check (bien_tipo in ('producto', 'servicio')),
  monto numeric(8, 2) check (monto between 0.01 and 999999.99),
  descripcion text check (char_length(descripcion) between 1 and 1000),
  -- 3) detalle y pedido
  tipo text check (tipo in ('reclamo', 'queja')),
  detalle text not null check (char_length(detalle) between 10 and 3000),
  pedido text not null check (char_length(pedido) between 10 and 3000),
  medio_respuesta text not null check (medio_respuesta in ('correo', 'carta')),
  -- respuesta (una sola vez, por `responder_hoja`)
  respuesta_texto text check (char_length(respuesta_texto) between 10 and 5000),
  respuesta_referencia_carta text check (char_length(respuesta_referencia_carta) between 1 and 200),
  respuesta_enviada_en timestamptz,
  respondida_en timestamptz,
  respondida_por uuid references public.usuario (id) on delete set null,
  constraint hoja_documento_formato check (
    (tipo_documento = 'dni' and documento ~ '^[0-9]{8}$')
    or (tipo_documento in ('ce', 'pasaporte') and documento ~ '^[A-Z0-9]{6,12}$')),
  constraint hoja_representante_coherente check (
    (es_menor and rep_nombre is not null and rep_domicilio is not null and rep_correo is not null)
    or (not es_menor and rep_nombre is null and rep_domicilio is null and rep_telefono is null and rep_correo is null)),
  constraint hoja_origen_coherente check (
    (origen = 'web' and fecha_original is null and numero_hoja_fisica is null)
    or (origen = 'libro_fisico' and fecha_original is not null and numero_hoja_fisica is not null)),
  constraint hoja_tipo_obligatorio_en_web check (origen = 'libro_fisico' or tipo is not null),
  constraint hoja_respuesta_completa check (
    (respuesta_texto is null) = (respondida_en is null) and (respuesta_texto is null) = (respuesta_enviada_en is null)
    and (respuesta_texto is not null or (respuesta_referencia_carta is null and respondida_por is null))),
  constraint hoja_respuesta_por_carta check (
    medio_respuesta = 'correo' or respuesta_texto is null or respuesta_referencia_carta is not null)
);
create index hoja_reclamacion_cuenta_idx on public.hoja_reclamacion (id_cuenta, creada_en desc) where id_cuenta is not null;
create index hoja_reclamacion_pendiente_idx on public.hoja_reclamacion (vence_respuesta) where respuesta_texto is null;

create table public.adjunto_reclamacion (
  id uuid primary key default gen_random_uuid(),
  id_hoja uuid not null references public.hoja_reclamacion (id),
  n smallint not null check (n between 1 and 3),
  nombre text not null check (char_length(nombre) between 1 and 200),
  tipo text not null check (tipo in ('application/pdf', 'image/jpeg', 'image/png')),
  tamano integer not null check (tamano between 1 and 5242880),
  ruta text not null unique,
  unique (id_hoja, n)
);

-- Limite por IP: solo el hash (la IP en claro no se guarda) y la hora de cada hoja registrada.
create table public.intento_reclamacion (
  ip_hash text not null,
  creado_en timestamptz not null default now()
);
create index intento_reclamacion_idx on public.intento_reclamacion (ip_hash, creado_en);

-- 3. Fecha, anio, plazo y fecha original: siempre los calcula la base.
create function public.hoja_reclamacion_preparar()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.creada_en := now();
  new.anio := extract(year from now() at time zone 'America/Lima')::int;
  if new.fecha_original is not null and new.fecha_original > now() then
    raise exception 'fecha_original_invalida';
  end if;
  new.vence_respuesta := public.sumar_dias_habiles(coalesce(new.fecha_original, new.creada_en), 15);
  return new;
end;
$$;
revoke all on function public.hoja_reclamacion_preparar() from public, anon, authenticated;
create trigger hoja_reclamacion_preparar before insert on public.hoja_reclamacion
  for each row execute function public.hoja_reclamacion_preparar();

-- 4. Inmutabilidad (ni el propietario de la tabla): solo se cierra la respuesta una vez (la hace `responder_hoja`) y
-- la baja de una cuenta suelta `id_cuenta` y `respondida_por` (la hoja se conserva).
create function public.hoja_reclamacion_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  -- `numero` es generada: en un BEFORE UPDATE aun no esta calculada, por eso se excluye de la comparacion.
  if tg_op = 'UPDATE' then
    if old.respuesta_texto is null and new.respuesta_texto is not null
       and to_jsonb(new) - array['numero', 'respuesta_texto', 'respuesta_referencia_carta', 'respuesta_enviada_en', 'respondida_en', 'respondida_por']
         = to_jsonb(old) - array['numero', 'respuesta_texto', 'respuesta_referencia_carta', 'respuesta_enviada_en', 'respondida_en', 'respondida_por'] then
      return new;
    end if;
    if new.id_cuenta is not distinct from old.id_cuenta or new.id_cuenta is null then
      if (new.respondida_por is null or new.respondida_por is not distinct from old.respondida_por)
         and to_jsonb(new) - array['numero', 'id_cuenta', 'respondida_por'] = to_jsonb(old) - array['numero', 'id_cuenta', 'respondida_por'] then
        return new;
      end if;
    end if;
  end if;
  raise exception 'hoja_inmutable';
end;
$$;
create trigger hoja_reclamacion_sin_edicion before update or delete on public.hoja_reclamacion
  for each row execute function public.hoja_reclamacion_inmutable();
create trigger hoja_reclamacion_sin_vaciado before truncate on public.hoja_reclamacion
  for each statement execute function public.hoja_reclamacion_inmutable();

create function public.adjunto_reclamacion_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'adjunto_inmutable';
end;
$$;
create trigger adjunto_reclamacion_sin_edicion before update or delete on public.adjunto_reclamacion
  for each row execute function public.adjunto_reclamacion_inmutable();
create trigger adjunto_reclamacion_sin_vaciado before truncate on public.adjunto_reclamacion
  for each statement execute function public.adjunto_reclamacion_inmutable();

-- 5. RLS y privilegios: anon no lee ni escribe tablas; el cliente lee las suyas; el administrador lee todo.
alter table public.hoja_reclamacion enable row level security;
alter table public.adjunto_reclamacion enable row level security;
alter table public.intento_reclamacion enable row level security;
revoke all on public.hoja_reclamacion, public.adjunto_reclamacion, public.intento_reclamacion from public, anon, authenticated;
grant select on public.hoja_reclamacion, public.adjunto_reclamacion to authenticated;
create policy hoja_reclamacion_lee on public.hoja_reclamacion for select to authenticated
  using (id_cuenta = (select auth.uid()) or public.es_administrador());
create policy adjunto_reclamacion_lee on public.adjunto_reclamacion for select to authenticated
  using (exists (select 1 from public.hoja_reclamacion h where h.id = id_hoja));

-- 6. Dias habiles hasta el plazo: 0 el dia del vencimiento, negativo (-1 o menos) si ya vencio.
create function public.dias_habiles_restantes(p_vence timestamptz)
returns integer
language sql
stable
set search_path = ''
as $$
  with f as (select (now() at time zone 'America/Lima')::date as hoy, (p_vence at time zone 'America/Lima')::date as dia)
  select case when p_vence < now()
    then -greatest(1, (select count(*)::int from f, generate_series(f.dia + 1, f.hoy, interval '1 day') d
                       where extract(isodow from d) < 6 and not exists (select 1 from public.feriado x where x.fecha = d::date)))
    else (select count(*)::int from f, generate_series(f.hoy + 1, f.dia, interval '1 day') d
          where extract(isodow from d) < 6 and not exists (select 1 from public.feriado x where x.fecha = d::date))
  end;
$$;
revoke all on function public.dias_habiles_restantes(timestamptz) from public, anon;
grant execute on function public.dias_habiles_restantes(timestamptz) to authenticated;

-- 7. Datos de la hoja para sus correos (la bandeja solo lee `notificacion`).
create function public.datos_hoja_para_correo(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'id', h.id, 'numero', h.numero, 'creada_en', h.creada_en, 'vence_respuesta', h.vence_respuesta, 'tipo', h.tipo,
    'nombre', h.nombre, 'tipo_documento', h.tipo_documento, 'documento', h.documento, 'domicilio', h.domicilio,
    'telefono', h.telefono, 'correo', h.correo, 'es_menor', h.es_menor,
    'representante', case when h.es_menor then jsonb_build_object(
      'nombre', h.rep_nombre, 'domicilio', h.rep_domicilio, 'telefono', h.rep_telefono, 'correo', h.rep_correo) end,
    'bien_tipo', h.bien_tipo, 'monto', h.monto, 'descripcion', h.descripcion, 'medio_respuesta', h.medio_respuesta,
    'adjuntos', coalesce((select jsonb_agg(a.nombre order by a.n) from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'),
    'detalle', h.detalle, 'pedido', h.pedido, 'con_cuenta', h.id_cuenta is not null)
  from public.hoja_reclamacion h where h.id = p_id;
$$;
revoke all on function public.datos_hoja_para_correo(uuid) from public, anon, authenticated;

-- 8. Alta comun (interna): inserta la hoja y sus adjuntos y avisa. `p_datos` trae los campos planos de la hoja.
create function public.crear_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_origen text, p_fecha_original timestamptz, p_numero_hoja_fisica text,
  p_cuenta uuid, p_spam boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.hoja_reclamacion (id, origen, fecha_original, numero_hoja_fisica, id_cuenta, revisar_spam,
    nombre, tipo_documento, documento, domicilio, telefono, correo, es_menor,
    rep_nombre, rep_domicilio, rep_telefono, rep_correo, bien_tipo, monto, descripcion,
    tipo, detalle, pedido, medio_respuesta)
  values (p_id, p_origen, p_fecha_original, p_numero_hoja_fisica,
    (select u.id from public.usuario u where u.id = p_cuenta), p_spam,
    p_datos ->> 'nombre', p_datos ->> 'tipo_documento', p_datos ->> 'documento', p_datos ->> 'domicilio',
    p_datos ->> 'telefono', p_datos ->> 'correo', coalesce((p_datos ->> 'es_menor')::boolean, false),
    p_datos ->> 'rep_nombre', p_datos ->> 'rep_domicilio', p_datos ->> 'rep_telefono', p_datos ->> 'rep_correo',
    p_datos ->> 'bien_tipo', (p_datos ->> 'monto')::numeric, p_datos ->> 'descripcion',
    p_datos ->> 'tipo', p_datos ->> 'detalle', p_datos ->> 'pedido', p_datos ->> 'medio_respuesta');

  insert into public.adjunto_reclamacion (id_hoja, n, nombre, tipo, tamano, ruta)
  select p_id, a.n::smallint, a.e ->> 'nombre', a.e ->> 'tipo', (a.e ->> 'tamano')::integer,
         p_id || '/' || a.n || '.' || case a.e ->> 'tipo'
           when 'application/pdf' then 'pdf' when 'image/jpeg' then 'jpg' when 'image/png' then 'png' end
  from jsonb_array_elements(coalesce(p_adjuntos, '[]'::jsonb)) with ordinality as a (e, n);

  -- Copia de la hoja al consumidor (web y transcrita) y aviso al administrador (solo web: la transcrita la registro el).
  insert into public.notificacion (tipo, destinatario, datos)
  select 'reclamacion_registrada', h.correo, public.datos_hoja_para_correo(h.id)
  from public.hoja_reclamacion h where h.id = p_id;
  if p_origen = 'web' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reclamacion_recibida', u.email,
           jsonb_build_object('id', h.id, 'numero', h.numero, 'tipo', h.tipo, 'nombre', h.nombre, 'creada_en', h.creada_en,
             'vence_respuesta', h.vence_respuesta, 'medio_respuesta', h.medio_respuesta,
             'adjuntos', (select count(*) from public.adjunto_reclamacion a where a.id_hoja = h.id))
    from public.hoja_reclamacion h
    cross join (select au.email from public.usuario a join auth.users au on au.id = a.id where a.rol = 'administrador') u
    where h.id = p_id;
  end if;
end;
$$;
revoke all on function public.crear_hoja(uuid, jsonb, jsonb, text, timestamptz, text, uuid, boolean) from public, anon, authenticated;

-- Alta publica: con sesion o sin ella. Limite de 5 hojas por hora por IP (se serializa por IP).
create function public.registrar_hoja(p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_ip text, p_spam boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_hash text := encode(sha256(convert_to(coalesce(p_ip, ''), 'utf8')), 'hex');
begin
  perform pg_advisory_xact_lock(hashtextextended('reclamacion:' || v_hash, 0));
  delete from public.intento_reclamacion where ip_hash = v_hash and creado_en < now() - interval '1 hour';
  if (select count(*) from public.intento_reclamacion where ip_hash = v_hash) >= 5 then
    raise exception 'demasiadas_solicitudes';
  end if;
  insert into public.intento_reclamacion (ip_hash) values (v_hash);
  perform public.crear_hoja(p_id, p_datos, p_adjuntos, 'web', null, null, (select auth.uid()), coalesce(p_spam, false));
end;
$$;
revoke all on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean) from public;
grant execute on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean) to anon, authenticated;

-- Transcripcion del libro fisico de respaldo (solo administrador).
create function public.transcribir_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_fecha_original timestamptz, p_numero_hoja_fisica text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform public.crear_hoja(p_id, p_datos, p_adjuntos, 'libro_fisico', p_fecha_original, p_numero_hoja_fisica, null, false);
end;
$$;
revoke all on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) from public, anon;
grant execute on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) to authenticated;

-- 9. Respuesta unica del administrador. El medio es el que pidio el consumidor; con carta, referencia y fecha de envio.
create function public.responder_hoja(p_id uuid, p_texto text, p_referencia text, p_enviada_en timestamptz)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  h public.hoja_reclamacion;
begin
  if not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into h from public.hoja_reclamacion where id = p_id for update;
  if not found then
    raise exception 'no_encontrado' using errcode = 'P0002';
  end if;
  if h.respuesta_texto is not null then
    raise exception 'ya_respondida';
  end if;
  update public.hoja_reclamacion
     set respuesta_texto = p_texto,
         respuesta_referencia_carta = case when h.medio_respuesta = 'carta' then p_referencia end,
         respuesta_enviada_en = case when h.medio_respuesta = 'carta' then p_enviada_en else now() end,
         respondida_en = now(),
         respondida_por = (select auth.uid())
   where id = p_id;
  if h.medio_respuesta = 'correo' then
    insert into public.notificacion (tipo, destinatario, datos)
    values ('reclamacion_respondida', h.correo,
            jsonb_build_object('id', h.id, 'numero', h.numero, 'tipo', h.tipo, 'creada_en', h.creada_en,
              'texto', p_texto, 'enviada_en', now(), 'con_cuenta', h.id_cuenta is not null));
  end if;
end;
$$;
revoke all on function public.responder_hoja(uuid, text, text, timestamptz) from public, anon;
grant execute on function public.responder_hoja(uuid, text, text, timestamptz) to authenticated;

-- 10. Cron de dias habiles (08:00 de Lima = 13:00 UTC): un aviso por administrador con las hojas pendientes que vencen
-- en 5 dias habiles o menos y las vencidas (vencidas primero, luego por plazo). Sin hojas, sin aviso. Devuelve los avisos.
create function public.avisar_plazos_reclamaciones()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_hojas jsonb;
  v_avisos integer;
begin
  delete from public.intento_reclamacion where creado_en < now() - interval '1 day';
  if exists (select 1 from public.feriado where fecha = (now() at time zone 'America/Lima')::date) then
    return 0;
  end if;
  select jsonb_agg(jsonb_build_object('id', x.id, 'numero', x.numero, 'tipo', x.tipo,
                                      'vence_respuesta', x.vence_respuesta, 'dias', x.dias)
                   order by (x.dias < 0) desc, x.vence_respuesta)
    into v_hojas
    from (select h.id, h.numero, h.tipo, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta) as dias
            from public.hoja_reclamacion h where h.respuesta_texto is null) x
   where x.dias <= 5;
  if v_hojas is null then
    return 0;
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'reclamaciones_por_vencer', au.email, jsonb_build_object('hojas', v_hojas)
    from public.usuario a join auth.users au on au.id = a.id where a.rol = 'administrador';
  get diagnostics v_avisos = row_count;
  return v_avisos;
end;
$$;
revoke all on function public.avisar_plazos_reclamaciones() from public, anon, authenticated;
select cron.schedule('avisar_plazos_reclamaciones', '0 13 * * 1-5', 'select public.avisar_plazos_reclamaciones()');

-- 11. Storage `reclamaciones` (ADR-003): privado, 5 MB y PDF/JPG/PNG en el bucket. El alta es publica pero solo en
-- `<id de hoja>/<1-3>.<ext>`; solo el administrador lee (y firma URLs).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('reclamaciones', 'reclamaciones', false, 5242880, array['application/pdf', 'image/jpeg', 'image/png'])
on conflict (id) do update set public = false, file_size_limit = 5242880,
  allowed_mime_types = array['application/pdf', 'image/jpeg', 'image/png'];
create policy reclamaciones_inserta on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'reclamaciones'
    and name ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[1-3]\.(pdf|jpg|png)$');
create policy reclamaciones_lee on storage.objects for select to authenticated
  using (bucket_id = 'reclamaciones' and public.es_administrador());
