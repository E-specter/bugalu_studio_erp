-- TAREA-RF16-8: retoques de la auditoria A de RF-16 (ronda 2) y de los correos (CORREO-3).
-- create or replace sobre 20261220100000_rf16_correcciones_auditoria_a.

-- Correos 7: la bandeja es la unica que ejecuta la consulta de reservas (service_role heredaba el execute por defecto).
revoke execute on function public.datos_reserva_para_correo(uuid[]) from service_role;

-- Correos 13: id_reserva se compara como uuid (la tabla `reserva` tiene indice por `id`, no por su texto). Un valor que
-- no sea uuid falla con 22P02: la bandeja lo degrada a "sin evento".
create or replace function public.datos_reserva_para_correo(p_ids uuid[])
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
             and (p.datos ->> 'id_reserva')::uuid = r.id
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         )
  from public.notificacion n
  join public.reserva r on r.id = (n.datos ->> 'id_reserva')::uuid
  join public.servicio s on s.id = r.id_servicio
  join public.sala_tecnica sa on sa.id = r.id_sala
  where n.id = any (p_ids);
$$;

-- RF-16 1: limite por IP. IPv6 se agrupa por prefijo /64 (una red domestica entrega miles de direcciones); IPv4, por
-- direccion. Un texto que no sea IP se usa tal cual.
create function public.ip_para_limite(p_ip text)
returns text
language plpgsql
immutable
set search_path = ''
as $$
begin
  if p_ip like '%:%' then
    return network(set_masklen(p_ip::inet, 64))::text;
  end if;
  return coalesce(p_ip, '');
exception when others then
  return coalesce(p_ip, '');
end;
$$;
revoke all on function public.ip_para_limite(text) from public, anon, authenticated;

-- RF-16 2 y 4: huella del contenido (jsonb tiene texto canonico) y adjuntos declarados, para el reintento.
alter table public.hoja_reclamacion add column huella_datos text;
alter table public.hoja_reclamacion add column adjuntos_declarados smallint not null default 0;

-- RF-16 3: un aviso puede esperar a que termine la subida de los adjuntos. Si la API cae a medias, sale solo, a los
-- cinco minutos, con lo que se haya guardado hasta entonces.
alter table public.notificacion add column enviar_desde timestamptz not null default now();

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
    'adjuntos', coalesce((select jsonb_agg(a.nombre order by a.n) from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'),
    'adjuntos_no_guardados', h.adjuntos_declarados - (select count(*) from public.adjunto_reclamacion a where a.id_hoja = h.id),
    'detalle', h.detalle, 'pedido', h.pedido, 'con_cuenta', h.id_cuenta is not null)
  from public.hoja_reclamacion h where h.id = p_id;
$$;

create function public.datos_hoja_recibida(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object('id', h.id, 'numero', h.numero, 'tipo', h.tipo, 'nombre', h.nombre, 'creada_en', h.creada_en,
    'vence_respuesta', h.vence_respuesta, 'medio_respuesta', h.medio_respuesta,
    'adjuntos', (select count(*) from public.adjunto_reclamacion a where a.id_hoja = h.id),
    'adjuntos_no_guardados', h.adjuntos_declarados - (select count(*) from public.adjunto_reclamacion a where a.id_hoja = h.id))
  from public.hoja_reclamacion h where h.id = p_id;
$$;
revoke all on function public.datos_hoja_recibida(uuid) from public, anon, authenticated;

create or replace function public.crear_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_origen text, p_fecha_original timestamptz, p_numero_hoja_fisica text,
  p_cuenta uuid, p_spam boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_declarados smallint := jsonb_array_length(coalesce(p_adjuntos, '[]'::jsonb));
  v_envio timestamptz := case when v_declarados > 0 then now() + interval '5 minutes' else now() end;
begin
  insert into public.hoja_reclamacion (id, origen, fecha_original, numero_hoja_fisica, id_cuenta, revisar_spam,
    clave_envio, huella_datos, adjuntos_declarados, nombre, tipo_documento, documento, domicilio, telefono, correo, es_menor,
    rep_nombre, rep_domicilio, rep_telefono, rep_correo, bien_tipo, monto, descripcion,
    tipo, detalle, pedido, medio_respuesta)
  values (p_id, p_origen, p_fecha_original, p_numero_hoja_fisica,
    (select u.id from public.usuario u where u.id = p_cuenta), p_spam,
    (p_datos ->> 'clave_envio')::uuid,
    encode(sha256(convert_to((p_datos - 'clave_envio')::text, 'utf8')), 'hex'), v_declarados,
    p_datos ->> 'nombre', p_datos ->> 'tipo_documento', p_datos ->> 'documento', p_datos ->> 'domicilio',
    p_datos ->> 'telefono', p_datos ->> 'correo', coalesce((p_datos ->> 'es_menor')::boolean, false),
    p_datos ->> 'rep_nombre', p_datos ->> 'rep_domicilio', p_datos ->> 'rep_telefono', p_datos ->> 'rep_correo',
    p_datos ->> 'bien_tipo', (p_datos ->> 'monto')::numeric, p_datos ->> 'descripcion',
    p_datos ->> 'tipo', p_datos ->> 'detalle', p_datos ->> 'pedido', p_datos ->> 'medio_respuesta');

  insert into public.subida_reclamacion (ruta, id_hoja, n, nombre, tipo, tamano)
  select p_id::text || '/' || gen_random_uuid()::text || '.' || case a.e ->> 'tipo'
           when 'application/pdf' then 'pdf' when 'image/jpeg' then 'jpg' when 'image/png' then 'png' end,
         p_id, a.n::smallint, a.e ->> 'nombre', a.e ->> 'tipo', (a.e ->> 'tamano')::integer
  from jsonb_array_elements(coalesce(p_adjuntos, '[]'::jsonb)) with ordinality as a (e, n);

  insert into public.notificacion (tipo, destinatario, datos, enviar_desde)
  select 'reclamacion_registrada', h.correo, public.datos_hoja_para_correo(h.id), v_envio
  from public.hoja_reclamacion h where h.id = p_id;
  if p_origen = 'web' then
    insert into public.notificacion (tipo, destinatario, datos, enviar_desde)
    select 'reclamacion_recibida', u.email, public.datos_hoja_recibida(h.id), v_envio
    from public.hoja_reclamacion h
    cross join (select au.email from public.usuario a join auth.users au on au.id = a.id where a.rol = 'administrador') u
    where h.id = p_id;
  end if;
end;
$$;

-- La API la llama al terminar las subidas: los avisos de la hoja que aun no salieron pasan a listar los adjuntos
-- confirmados y salen ya. Solo refresca datos de esa hoja (hay que conocer su id); no revela nada.
create function public.avisar_hoja(p_id uuid)
returns void
language sql
security definer
set search_path = ''
as $$
  update public.notificacion n
     set datos = case n.tipo when 'reclamacion_registrada' then public.datos_hoja_para_correo(p_id)
                             else public.datos_hoja_recibida(p_id) end,
         enviar_desde = now()
   where n.enviada_en is null and n.tipo in ('reclamacion_registrada', 'reclamacion_recibida')
     and n.datos ->> 'id' = p_id::text;
$$;
revoke all on function public.avisar_hoja(uuid) from public;
grant execute on function public.avisar_hoja(uuid) to anon, authenticated;

-- RF-16 4: el reintento informa que adjuntos declarados no se guardaron.
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
               from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'),
    'adjuntos_no_guardados', coalesce((select jsonb_agg(g order by g) from generate_series(1, h.adjuntos_declarados) g
               where not exists (select 1 from public.adjunto_reclamacion a where a.id_hoja = h.id and a.n = g)), '[]'))
  from public.hoja_reclamacion h where h.id = p_id;
$$;

-- RF-16 1 y 2: el limite usa la IP agrupada; la clave de envio exige el mismo contenido completo.
create or replace function public.registrar_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_ip text, p_spam boolean, p_clave uuid default null)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer, r_repetida boolean,
               r_existente jsonb, r_subidas jsonb)
language plpgsql
security definer
set search_path = ''
as $$
declare
  -- shortcut: SHA-256 de la IP (o de su /64) sin sal. El espacio IPv4 es enumerable: el hash solo evita guardar la IP en
  -- claro, no la anonimiza. Vale porque la fila dura una hora (se borra al alta y en el cron diario). Si la retencion
  -- pasa de unos dias o el dato se usa para otra cosa, cambiar a HMAC con una clave del servidor.
  v_hash text := encode(sha256(convert_to(public.ip_para_limite(p_ip), 'utf8')), 'hex');
  v_huella text := encode(sha256(convert_to((p_datos - 'clave_envio')::text, 'utf8')), 'hex');
  v_previa uuid;
begin
  if p_clave is not null then
    perform pg_advisory_xact_lock(hashtextextended('clave_reclamacion:' || p_clave::text, 0));
    select h.id into v_previa from public.hoja_reclamacion h
      where h.clave_envio = p_clave and h.creada_en > now() - interval '24 hours' and h.huella_datos = v_huella
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

-- RF-16 5: huerfanos. Si la subida termino y la confirmacion fallo, el objeto queda en Storage. Pasada la hora de margen
-- sobre la caducidad, la API lista las rutas, las borra por la API de Storage (como `anon`, solo estas rutas) y la
-- limpieza diaria quita despues la fila. Storage no deja borrar con SQL (storage.protect_delete).
create function public.rutas_huerfanas_reclamacion()
returns setof text
language sql
stable
security definer
set search_path = ''
as $$
  select s.ruta from public.subida_reclamacion s
  where s.caduca_en < now() - interval '1 hour'
    and exists (select 1 from storage.objects o where o.bucket_id = 'reclamaciones' and o.name = s.ruta)
$$;
revoke all on function public.rutas_huerfanas_reclamacion() from public, anon, authenticated;
grant execute on function public.rutas_huerfanas_reclamacion() to bugalu_api;

create function public.subida_reclamacion_huerfana(p_ruta text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.subida_reclamacion s where s.ruta = p_ruta and s.caduca_en < now() - interval '1 hour')
$$;
revoke all on function public.subida_reclamacion_huerfana(text) from public;
grant execute on function public.subida_reclamacion_huerfana(text) to anon, authenticated;

create policy reclamaciones_borra_huerfana on storage.objects for delete to anon
  using (bucket_id = 'reclamaciones' and public.subida_reclamacion_huerfana(name));

create or replace function public.limpiar_subidas_reclamacion()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_borradas integer;
begin
  -- Con el objeto aun en Storage, la fila se queda: la API la necesita para limpiarlo.
  delete from public.subida_reclamacion s
   where s.caduca_en < now() - interval '1 hour'
     and not exists (select 1 from storage.objects o where o.bucket_id = 'reclamaciones' and o.name = s.ruta);
  get diagnostics v_borradas = row_count;
  return v_borradas;
end;
$$;
