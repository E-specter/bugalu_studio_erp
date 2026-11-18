-- RF-16, auditoria A (ronda 1): subidas pendientes en Storage, clave de envio con los mismos datos, fecha original acotada,
-- correlativo sin huecos, anio de presentacion, lectura por columnas del cliente y estado real en el reintento.

-- 1. Subidas pendientes: `anon` solo puede subir a una ruta que la base genero al registrar la hoja (aleatoria, 10 minutos,
-- un solo objeto). Tras subir, `confirmar_adjunto` crea el adjunto. Nada de esto lo lee `anon` ni `authenticated`.
create table public.subida_reclamacion (
  ruta text primary key,
  id_hoja uuid not null references public.hoja_reclamacion (id) on delete cascade,
  n smallint not null check (n between 1 and 3),
  nombre text not null check (char_length(nombre) between 1 and 200),
  tipo text not null check (tipo in ('application/pdf', 'image/jpeg', 'image/png')),
  tamano integer not null check (tamano between 1 and 5242880),
  caduca_en timestamptz not null default now() + interval '10 minutes',
  unique (id_hoja, n)
);
alter table public.subida_reclamacion enable row level security;
revoke all on public.subida_reclamacion from public, anon, authenticated;

-- La politica de Storage la evalua el rol que sube (`anon`): la funcion lee la tabla por el.
create function public.subida_reclamacion_vigente(p_ruta text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.subida_reclamacion s where s.ruta = p_ruta and s.caduca_en > now())
     and not exists (select 1 from storage.objects o where o.bucket_id = 'reclamaciones' and o.name = p_ruta)
$$;
revoke all on function public.subida_reclamacion_vigente(text) from public;
grant execute on function public.subida_reclamacion_vigente(text) to anon, authenticated;

drop policy reclamaciones_inserta on storage.objects;
create policy reclamaciones_inserta on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'reclamaciones' and public.subida_reclamacion_vigente(name));

-- El objeto debe existir (lo subio Storage con la politica de arriba). Conserva nombre, tipo y tamano declarados.
create function public.confirmar_adjunto(p_ruta text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  s public.subida_reclamacion;
begin
  select * into s from public.subida_reclamacion where ruta = p_ruta for update;
  if not found or not exists (select 1 from storage.objects o where o.bucket_id = 'reclamaciones' and o.name = p_ruta) then
    raise exception 'subida_no_encontrada' using errcode = 'P0002';
  end if;
  insert into public.adjunto_reclamacion (id_hoja, n, nombre, tipo, tamano, ruta)
  values (s.id_hoja, s.n, s.nombre, s.tipo, s.tamano, s.ruta);
  delete from public.subida_reclamacion where ruta = p_ruta;
end;
$$;
revoke all on function public.confirmar_adjunto(text) from public;
grant execute on function public.confirmar_adjunto(text) to anon, authenticated;

-- Limpieza diaria (13:30 UTC): una hora de margen sobre la caducidad por si una confirmacion esta en curso.
create function public.limpiar_subidas_reclamacion()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_borradas integer;
begin
  delete from public.subida_reclamacion where caduca_en < now() - interval '1 hour';
  get diagnostics v_borradas = row_count;
  return v_borradas;
end;
$$;
revoke all on function public.limpiar_subidas_reclamacion() from public, anon, authenticated;
select cron.schedule('limpiar_subidas_reclamacion', '30 13 * * *', 'select public.limpiar_subidas_reclamacion()');

-- 2. Correlativo sin huecos: una fila contador que se incrementa en la misma transaccion del alta (si se deshace, no se
-- consume el numero; las altas se serializan en esa fila). Reemplaza a la secuencia, que dejaba huecos.
create table public.contador_reclamacion (
  id boolean primary key default true check (id),
  ultimo bigint not null
);
insert into public.contador_reclamacion (ultimo) select coalesce(max(correlativo), 0) from public.hoja_reclamacion;
alter table public.contador_reclamacion enable row level security;
revoke all on public.contador_reclamacion from public, anon, authenticated;
alter table public.hoja_reclamacion alter column correlativo drop default;
drop sequence public.hoja_reclamacion_correlativo;

-- 3. El anio del numero es el de presentacion en Lima: la fecha original en las transcritas.
create function public.anio_presentacion(p_fecha timestamptz)
returns smallint
language sql
immutable
set search_path = ''
as $$
  select extract(year from p_fecha at time zone 'America/Lima')::smallint
$$;
revoke all on function public.anio_presentacion(timestamptz) from public, anon, authenticated;

-- 4. Fecha original: no futura ni anterior a 90 dias (un anio absurdo dejaba plazos de cientos de miles de dias).
create or replace function public.hoja_reclamacion_preparar()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.creada_en := now();
  if new.fecha_original is not null
     and (new.fecha_original > now() or new.fecha_original < now() - interval '90 days') then
    raise exception 'fecha_original_invalida';
  end if;
  new.anio := public.anio_presentacion(coalesce(new.fecha_original, new.creada_en));
  new.vence_respuesta := public.sumar_dias_habiles(coalesce(new.fecha_original, new.creada_en), 15);
  update public.contador_reclamacion set ultimo = ultimo + 1 returning ultimo into new.correlativo;
  return new;
end;
$$;

-- 5. El cliente lee sus hojas por columnas, sin las marcas del Administrador (`revisar_spam`, `respondida_por`); el
-- Administrador las recibe por `marcas_de_hojas`, que no devuelve nada a nadie mas.
revoke select on public.hoja_reclamacion from authenticated;
grant select (id, correlativo, anio, numero, creada_en, vence_respuesta, origen, fecha_original, numero_hoja_fisica,
  id_cuenta, nombre, tipo_documento, documento, domicilio, telefono, correo, es_menor, rep_nombre, rep_domicilio,
  rep_telefono, rep_correo, bien_tipo, monto, descripcion, tipo, detalle, pedido, medio_respuesta, respuesta_texto,
  respuesta_referencia_carta, respuesta_enviada_en, respondida_en) on public.hoja_reclamacion to authenticated;

create function public.marcas_de_hojas()
returns table (id uuid, revisar_spam boolean, respondida_por uuid)
language sql
stable
security definer
set search_path = ''
as $$
  select h.id, h.revisar_spam, h.respondida_por from public.hoja_reclamacion h where public.es_administrador()
$$;
revoke all on function public.marcas_de_hojas() from public, anon;
grant execute on function public.marcas_de_hojas() to authenticated;

-- 6. Los avisos listan los adjuntos declarados (aun no confirmados al registrar la hoja).
create or replace function public.datos_hoja_para_correo(p_id uuid)
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
    'adjuntos', coalesce((select jsonb_agg(a.nombre order by a.n) from public.subida_reclamacion a where a.id_hoja = h.id), '[]'),
    'detalle', h.detalle, 'pedido', h.pedido, 'con_cuenta', h.id_cuenta is not null)
  from public.hoja_reclamacion h where h.id = p_id;
$$;

create or replace function public.crear_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_origen text, p_fecha_original timestamptz, p_numero_hoja_fisica text,
  p_cuenta uuid, p_spam boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.hoja_reclamacion (id, origen, fecha_original, numero_hoja_fisica, id_cuenta, revisar_spam,
    clave_envio, nombre, tipo_documento, documento, domicilio, telefono, correo, es_menor,
    rep_nombre, rep_domicilio, rep_telefono, rep_correo, bien_tipo, monto, descripcion,
    tipo, detalle, pedido, medio_respuesta)
  values (p_id, p_origen, p_fecha_original, p_numero_hoja_fisica,
    (select u.id from public.usuario u where u.id = p_cuenta), p_spam,
    (p_datos ->> 'clave_envio')::uuid,
    p_datos ->> 'nombre', p_datos ->> 'tipo_documento', p_datos ->> 'documento', p_datos ->> 'domicilio',
    p_datos ->> 'telefono', p_datos ->> 'correo', coalesce((p_datos ->> 'es_menor')::boolean, false),
    p_datos ->> 'rep_nombre', p_datos ->> 'rep_domicilio', p_datos ->> 'rep_telefono', p_datos ->> 'rep_correo',
    p_datos ->> 'bien_tipo', (p_datos ->> 'monto')::numeric, p_datos ->> 'descripcion',
    p_datos ->> 'tipo', p_datos ->> 'detalle', p_datos ->> 'pedido', p_datos ->> 'medio_respuesta');

  -- Una subida pendiente por adjunto: la ruta es `<hoja>/<uuid aleatorio>.<ext>` y la genera la base.
  insert into public.subida_reclamacion (ruta, id_hoja, n, nombre, tipo, tamano)
  select p_id::text || '/' || gen_random_uuid()::text || '.' || case a.e ->> 'tipo'
           when 'application/pdf' then 'pdf' when 'image/jpeg' then 'jpg' when 'image/png' then 'png' end,
         p_id, a.n::smallint, a.e ->> 'nombre', a.e ->> 'tipo', (a.e ->> 'tamano')::integer
  from jsonb_array_elements(coalesce(p_adjuntos, '[]'::jsonb)) with ordinality as a (e, n);

  insert into public.notificacion (tipo, destinatario, datos)
  select 'reclamacion_registrada', h.correo, public.datos_hoja_para_correo(h.id)
  from public.hoja_reclamacion h where h.id = p_id;
  if p_origen = 'web' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reclamacion_recibida', u.email,
           jsonb_build_object('id', h.id, 'numero', h.numero, 'tipo', h.tipo, 'nombre', h.nombre, 'creada_en', h.creada_en,
             'vence_respuesta', h.vence_respuesta, 'medio_respuesta', h.medio_respuesta,
             'adjuntos', (select count(*) from public.subida_reclamacion a where a.id_hoja = h.id))
    from public.hoja_reclamacion h
    cross join (select au.email from public.usuario a join auth.users au on au.id = a.id where a.rol = 'administrador') u
    where h.id = p_id;
  end if;
end;
$$;

-- 7. La hoja ya registrada (reintento): ahora con su estado y su respuesta reales.
create or replace function public.hoja_registrada_json(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'id', h.id, 'numero', h.numero, 'creada_en', h.creada_en, 'vence_respuesta', h.vence_respuesta,
    'dias', case when h.respuesta_texto is null then public.dias_habiles_restantes(h.vence_respuesta) end,
    'id_cuenta', h.id_cuenta,
    'nombre', h.nombre, 'tipo_documento', h.tipo_documento, 'documento', h.documento, 'domicilio', h.domicilio,
    'telefono', h.telefono, 'correo', h.correo, 'es_menor', h.es_menor,
    'rep_nombre', h.rep_nombre, 'rep_domicilio', h.rep_domicilio, 'rep_telefono', h.rep_telefono, 'rep_correo', h.rep_correo,
    'bien_tipo', h.bien_tipo, 'monto', h.monto, 'descripcion', h.descripcion, 'tipo', h.tipo,
    'detalle', h.detalle, 'pedido', h.pedido, 'medio_respuesta', h.medio_respuesta,
    'respuesta_texto', h.respuesta_texto, 'respuesta_referencia_carta', h.respuesta_referencia_carta,
    'respuesta_enviada_en', h.respuesta_enviada_en,
    'adjuntos', coalesce((select jsonb_agg(jsonb_build_object('n', a.n, 'nombre', a.nombre, 'tipo', a.tipo,
                 'tamano', a.tamano, 'ruta', a.ruta) order by a.n)
               from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'))
  from public.hoja_reclamacion h where h.id = p_id;
$$;

-- 8. Altas: devuelven tambien las rutas de subida. La clave de envio solo es un reintento si coinciden documento,
-- correo, detalle y pedido; con otros datos se ignora y se registra una hoja nueva.
drop function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean, uuid);
drop function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text);

create function public.registrar_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_ip text, p_spam boolean, p_clave uuid default null)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer, r_repetida boolean,
               r_existente jsonb, r_subidas jsonb)
language plpgsql
security definer
set search_path = ''
as $$
declare
  -- shortcut: SHA-256 de la IP sin sal. El espacio IPv4 es enumerable: el hash solo evita guardar la IP en claro, no la
  -- anonimiza. Vale porque la fila dura una hora (se borra al alta y en el cron diario). Si la retencion pasa de unos
  -- dias o el dato se usa para otra cosa, cambiar a HMAC con una clave del servidor.
  v_hash text := encode(sha256(convert_to(coalesce(p_ip, ''), 'utf8')), 'hex');
  v_previa uuid;
begin
  if p_clave is not null then
    perform pg_advisory_xact_lock(hashtextextended('clave_reclamacion:' || p_clave::text, 0));
    select h.id into v_previa from public.hoja_reclamacion h
      where h.clave_envio = p_clave and h.creada_en > now() - interval '24 hours'
        and h.documento = p_datos ->> 'documento' and h.correo = p_datos ->> 'correo'
        and h.detalle = p_datos ->> 'detalle' and h.pedido = p_datos ->> 'pedido'
      order by h.creada_en limit 1;
    if v_previa is not null then
      return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta),
                          true, public.hoja_registrada_json(h.id), '[]'::jsonb
                     from public.hoja_reclamacion h where h.id = v_previa;
      return;
    end if;
  end if;
  perform pg_advisory_xact_lock(hashtextextended('reclamacion:' || v_hash, 0));
  delete from public.intento_reclamacion where ip_hash = v_hash and creado_en < now() - interval '1 hour';
  if (select count(*) from public.intento_reclamacion where ip_hash = v_hash) >= 5 then
    raise exception 'demasiadas_solicitudes';
  end if;
  insert into public.intento_reclamacion (ip_hash) values (v_hash);
  perform public.crear_hoja(p_id, p_datos || jsonb_build_object('clave_envio', p_clave), p_adjuntos, 'web', null, null,
                            (select auth.uid()), coalesce(p_spam, false));
  return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta), false,
                      null::jsonb,
                      coalesce((select jsonb_agg(jsonb_build_object('n', s.n, 'ruta', s.ruta) order by s.n)
                                from public.subida_reclamacion s where s.id_hoja = h.id), '[]')
                 from public.hoja_reclamacion h where h.id = p_id;
end;
$$;
revoke all on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean, uuid) from public;
grant execute on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean, uuid) to anon, authenticated;

create function public.transcribir_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_fecha_original timestamptz, p_numero_hoja_fisica text)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer, r_subidas jsonb)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform public.crear_hoja(p_id, p_datos, p_adjuntos, 'libro_fisico', p_fecha_original, p_numero_hoja_fisica, null, false);
  return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta),
                      coalesce((select jsonb_agg(jsonb_build_object('n', s.n, 'ruta', s.ruta) order by s.n)
                                from public.subida_reclamacion s where s.id_hoja = h.id), '[]')
                 from public.hoja_reclamacion h where h.id = p_id;
end;
$$;
revoke all on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) from public, anon;
grant execute on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) to authenticated;
