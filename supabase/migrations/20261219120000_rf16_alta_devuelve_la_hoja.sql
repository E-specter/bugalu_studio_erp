-- RF-16: el alta devuelve lo que la respuesta 201 necesita (numero, fecha, plazo y dias habiles restantes), porque
-- `anon` no puede releer la hoja que acaba de registrar.
drop function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean);
drop function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text);

create function public.registrar_hoja(p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_ip text, p_spam boolean)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer)
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
  return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta)
                 from public.hoja_reclamacion h where h.id = p_id;
end;
$$;
revoke all on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean) from public;
grant execute on function public.registrar_hoja(uuid, jsonb, jsonb, text, boolean) to anon, authenticated;

create function public.transcribir_hoja(
  p_id uuid, p_datos jsonb, p_adjuntos jsonb, p_fecha_original timestamptz, p_numero_hoja_fisica text)
returns table (r_numero text, r_creada_en timestamptz, r_vence timestamptz, r_dias integer)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform public.crear_hoja(p_id, p_datos, p_adjuntos, 'libro_fisico', p_fecha_original, p_numero_hoja_fisica, null, false);
  return query select h.numero, h.creada_en, h.vence_respuesta, public.dias_habiles_restantes(h.vence_respuesta)
                 from public.hoja_reclamacion h where h.id = p_id;
end;
$$;
revoke all on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) from public, anon;
grant execute on function public.transcribir_hoja(uuid, jsonb, jsonb, timestamptz, text) to authenticated;
