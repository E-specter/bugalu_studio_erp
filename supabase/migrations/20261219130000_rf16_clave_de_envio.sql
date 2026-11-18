-- RF-16 (precision 11): clave de envio. Un reintento con la misma clave en las ultimas 24 h devuelve la hoja ya
-- registrada sin crear otra ni reenviar correos, tambien en concurrencia (se serializa por clave).
alter table public.hoja_reclamacion add column clave_envio uuid;
create index hoja_reclamacion_clave_idx on public.hoja_reclamacion (clave_envio, creada_en) where clave_envio is not null;

-- `crear_hoja` lee la clave de `p_datos` (misma firma): solo la pasa `registrar_hoja`.
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

  insert into public.adjunto_reclamacion (id_hoja, n, nombre, tipo, tamano, ruta)
  select p_id, a.n::smallint, a.e ->> 'nombre', a.e ->> 'tipo', (a.e ->> 'tamano')::integer,
         p_id || '/' || a.n || '.' || case a.e ->> 'tipo'
           when 'application/pdf' then 'pdf' when 'image/jpeg' then 'jpg' when 'image/png' then 'png' end
  from jsonb_array_elements(coalesce(p_adjuntos, '[]'::jsonb)) with ordinality as a (e, n);

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

-- La hoja ya registrada, para devolverla en el reintento (anon no puede leerla).
create function public.hoja_registrada_json(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'id', h.id, 'numero', h.numero, 'creada_en', h.creada_en, 'vence_respuesta', h.vence_respuesta,
    'dias', public.dias_habiles_restantes(h.vence_respuesta),
    'nombre', h.nombre, 'tipo_documento', h.tipo_documento, 'documento', h.documento, 'domicilio', h.domicilio,
    'telefono', h.telefono, 'correo', h.correo, 'es_menor', h.es_menor,
    'rep_nombre', h.rep_nombre, 'rep_domicilio', h.rep_domicilio, 'rep_telefono', h.rep_telefono, 'rep_correo', h.rep_correo,
    'bien_tipo', h.bien_tipo, 'monto', h.monto, 'descripcion', h.descripcion, 'tipo', h.tipo,
    'detalle', h.detalle, 'pedido', h.pedido, 'medio_respuesta', h.medio_respuesta,
    'adjuntos', coalesce((select jsonb_agg(jsonb_build_object('n', a.n, 'nombre', a.nombre, 'tipo', a.tipo,
                 'tamano', a.tamano, 'ruta', a.ruta) order by a.n)
               from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'))
  from public.hoja_reclamacion h where h.id = p_id;
$$;
revoke all on function public.hoja_registrada_json(uuid) from public, anon, authenticated;

drop function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean);
create function public.registrar_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_ip text, p_spam boolean, p_clave uuid default null)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer, r_repetida boolean, r_existente jsonb)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_hash text := encode(sha256(convert_to(coalesce(p_ip, ''), 'utf8')), 'hex');
  v_previa uuid;
begin
  if p_clave is not null then
    perform pg_advisory_xact_lock(hashtextextended('clave_reclamacion:' || p_clave::text, 0));
    select h.id into v_previa from public.hoja_reclamacion h
      where h.clave_envio = p_clave and h.creada_en > now() - interval '24 hours'
      order by h.creada_en limit 1;
    if v_previa is not null then
      return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta),
                          true, public.hoja_registrada_json(h.id)
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
  return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta), false, null::jsonb
                 from public.hoja_reclamacion h where h.id = p_id;
end;
$$;
revoke all on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean, uuid) from public;
grant execute on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean, uuid) to anon, authenticated;
