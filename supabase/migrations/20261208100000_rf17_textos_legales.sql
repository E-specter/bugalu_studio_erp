-- RF-17 (etapa A): textos legales versionados e inmutables y aceptaciones inmutables (CA-01 a CA-03, CA-14).
-- Sin IP ni navegador en las aceptaciones (decision 6).

-- Un texto por (tipo, version). `autorizacion_menor` queda reservado para la etapa B (la API no lo publica aun).
create table public.texto_legal (
  id uuid primary key default gen_random_uuid(),
  tipo text not null check (tipo in
    ('terminos_uso', 'politica_privacidad', 'condiciones_contratacion', 'declaracion_agrupacion', 'autorizacion_menor')),
  version text not null check (version ~ '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'),
  tipo_cambio text not null check (tipo_cambio in ('mayor', 'menor', 'parche')),
  contenido text not null check (btrim(contenido) <> ''),
  -- {contexto: resumen para pantalla}, sin datos de una reserva concreta.
  resumenes jsonb not null default '{}' check (
    jsonb_typeof(resumenes) = 'object'
    and resumenes - array['registro', 'reserva', 'asesoria', 'pago', 'menor', 'promociones', 'usos_promocionales'] = '{}'::jsonb),
  resumen_cambios text check (resumen_cambios is null or length(resumen_cambios) <= 500),
  vigente_desde timestamptz not null,
  publicado_en timestamptz not null default now(),
  id_autor uuid references public.usuario (id) on delete set null,
  unique (tipo, version)
);

alter table public.texto_legal enable row level security;
revoke all on public.texto_legal from anon, authenticated;
grant select on public.texto_legal to anon, authenticated;
create policy texto_legal_lectura on public.texto_legal for select to anon, authenticated using (true);

-- Inmutable tras publicar: solo se retira una programada (retirar_texto_legal), tampoco el propietario edita o vacia.
create function public.texto_legal_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' and old.vigente_desde > now() then
    return old;
  end if;
  raise exception 'Una version publicada no se edita ni se borra.';
end;
$$;
create trigger texto_legal_sin_edicion before update or delete on public.texto_legal
  for each row execute function public.texto_legal_inmutable();
create trigger texto_legal_sin_vaciado before truncate on public.texto_legal
  for each statement execute function public.texto_legal_inmutable();

-- Vigente de cada tipo: la mayor version con `vigente_desde` ya cumplido.
create function public.textos_vigentes()
returns setof public.texto_legal
language sql
stable
set search_path = ''
as $$
  select distinct on (t.tipo) t.*
    from public.texto_legal t
   where t.vigente_desde <= now()
   order by t.tipo, string_to_array(t.version, '.')::int[] desc;
$$;

-- Unica via de publicacion. Las reglas de version y de aviso (CA-02) las valida el backend; aqui quedan la
-- unicidad, una sola programada por texto (409 version_programada) y el aviso a los clientes. Sin
-- `p_vigente_desde` rige al publicarse, con el reloj de la base.
create function public.publicar_texto_legal(
  p_tipo text, p_version text, p_tipo_cambio text, p_contenido text, p_resumenes jsonb,
  p_resumen_cambios text, p_vigente_desde timestamptz)
returns public.texto_legal
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.texto_legal;
  hay_previas boolean;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  perform pg_advisory_xact_lock(20261208, hashtext(p_tipo));
  if exists (select 1 from public.texto_legal where tipo = p_tipo and vigente_desde > now()) then
    raise exception 'version_programada';
  end if;
  hay_previas := exists (select 1 from public.texto_legal where tipo = p_tipo);
  insert into public.texto_legal (tipo, version, tipo_cambio, contenido, resumenes, resumen_cambios, vigente_desde, id_autor)
    values (p_tipo, p_version, p_tipo_cambio, p_contenido, coalesce(p_resumenes, '{}'), p_resumen_cambios, coalesce(p_vigente_desde, now()), auth.uid())
    returning * into v;
  if hay_previas and p_tipo_cambio in ('mayor', 'menor') then
    insert into public.notificacion (tipo, destinatario, datos)
      select 'texto_legal_nuevo', a.email,
             jsonb_build_object('tipo', v.tipo, 'version', v.version, 'tipo_cambio', v.tipo_cambio,
                                'vigente_desde', v.vigente_desde, 'resumen_cambios', v.resumen_cambios)
        from public.usuario u join auth.users a on a.id = u.id
       where u.rol = 'cliente' and a.email is not null;
  end if;
  return v;
end;
$$;

-- Retira una version programada (aun no vigente) y anula sus avisos sin enviar.
create function public.retirar_texto_legal(p_tipo text, p_version text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.texto_legal;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  perform pg_advisory_xact_lock(20261208, hashtext(p_tipo));
  select * into v from public.texto_legal where tipo = p_tipo and version = p_version for update;
  if not found then
    raise exception 'La version no existe.' using errcode = 'P0002';
  end if;
  if v.vigente_desde <= now() then
    raise exception 'version_vigente';
  end if;
  delete from public.texto_legal where id = v.id;
  delete from public.notificacion
   where tipo = 'texto_legal_nuevo' and enviada_en is null
     and datos ->> 'tipo' = p_tipo and datos ->> 'version' = p_version;
end;
$$;

-- Aviso de una version nueva de los textos.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
   'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo'));

-- Aceptacion: solo insert por funciones; solo se actualiza `retirada_en` de un consentimiento opcional.
-- `aceptante` ({nombre, documento}) solo si acepta un tutor (etapa B).
create table public.aceptacion (
  id uuid primary key default gen_random_uuid(),
  id_usuario uuid not null references public.usuario (id) on delete cascade,
  tipo text not null,
  version text not null,
  contexto text not null check (contexto in
    ('registro', 'reserva', 'asesoria', 'pago', 'menor', 'promociones', 'usos_promocionales')),
  id_operacion uuid,
  aceptada_en timestamptz not null default now(),
  retirada_en timestamptz,
  aceptante jsonb check (aceptante is null or jsonb_typeof(aceptante) = 'object'),
  foreign key (tipo, version) references public.texto_legal (tipo, version) on delete restrict,
  check (retirada_en is null or contexto in ('promociones', 'usos_promocionales')),
  check (id_operacion is null or contexto in ('reserva', 'asesoria', 'pago'))
);
create index aceptacion_usuario_idx on public.aceptacion (id_usuario, aceptada_en desc);
create unique index aceptacion_registro_unica on public.aceptacion (id_usuario, tipo, version)
  where contexto = 'registro';

alter table public.aceptacion enable row level security;
revoke all on public.aceptacion from anon, authenticated;
grant select on public.aceptacion to authenticated;
create policy aceptacion_lectura on public.aceptacion for select to authenticated
  using (id_usuario = (select auth.uid()) or public.es_administrador());

create function public.aceptacion_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' and old.retirada_en is null and new.retirada_en is not null
     and to_jsonb(new) - 'retirada_en' = to_jsonb(old) - 'retirada_en' then
    return new;  -- el retiro de un consentimiento opcional (la restriccion limita el contexto)
  end if;
  if tg_op = 'DELETE' and pg_trigger_depth() > 1 then
    return old;  -- en cascada desde la baja de la cuenta (supresion), nunca una sentencia directa
  end if;
  raise exception 'Una aceptacion no se edita ni se borra.';
end;
$$;
create trigger aceptacion_sin_edicion before update or delete on public.aceptacion
  for each row execute function public.aceptacion_inmutable();
create trigger aceptacion_sin_vaciado before truncate on public.aceptacion
  for each statement execute function public.aceptacion_inmutable();

-- Insercion interna para las funciones de reserva, asesoria, pago y consentimientos: no es llamable desde la API.
create function public.insertar_aceptacion(
  p_id_usuario uuid, p_tipo text, p_version text, p_contexto text, p_id_operacion uuid, p_aceptante jsonb)
returns public.aceptacion
language sql
security definer
set search_path = ''
as $$
  insert into public.aceptacion (id_usuario, tipo, version, contexto, id_operacion, aceptante)
  values (p_id_usuario, p_tipo, p_version, p_contexto, p_id_operacion, p_aceptante)
  returning *;
$$;

-- Aceptacion del registro (CA-04): terminos y declaracion se aceptan, la politica registra la version mostrada.
-- Solo la vigente (P0001 texto_desactualizado); repetir no duplica.
create function public.aceptar_textos(p_contexto text, p_textos jsonb)
returns setof public.aceptacion
language plpgsql
security definer
set search_path = ''
as $$
declare
  t record;
begin
  if auth.uid() is null then
    raise exception 'Sin sesion.' using errcode = '42501';
  end if;
  if p_contexto <> 'registro' then
    raise exception 'Contexto no admitido.' using errcode = '22023';
  end if;
  for t in select e ->> 'tipo' as tipo, e ->> 'version' as version from jsonb_array_elements(p_textos) e loop
    if t.tipo is null or t.tipo not in ('terminos_uso', 'politica_privacidad', 'declaracion_agrupacion') then
      raise exception 'Texto no admitido en el registro.' using errcode = '22023';
    end if;
    if not exists (select 1 from public.textos_vigentes() v where v.tipo = t.tipo and v.version = t.version) then
      raise exception 'texto_desactualizado';
    end if;
    insert into public.aceptacion (id_usuario, tipo, version, contexto)
      values (auth.uid(), t.tipo, t.version, 'registro')
      on conflict (id_usuario, tipo, version) where contexto = 'registro' do nothing;
  end loop;
  return query
    select a.* from public.aceptacion a
     where a.id_usuario = auth.uid() and a.contexto = 'registro'
       and (a.tipo, a.version) in (select e ->> 'tipo', e ->> 'version' from jsonb_array_elements(p_textos) e)
     order by a.tipo;
end;
$$;

revoke all on function public.textos_vigentes() from public, anon;
revoke all on function public.publicar_texto_legal(text, text, text, text, jsonb, text, timestamptz) from public, anon;
revoke all on function public.retirar_texto_legal(text, text) from public, anon;
revoke all on function public.insertar_aceptacion(uuid, text, text, text, uuid, jsonb) from public, anon, authenticated;
revoke all on function public.aceptar_textos(text, jsonb) from public, anon;
grant execute on function public.textos_vigentes() to anon, authenticated;
grant execute on function public.publicar_texto_legal(text, text, text, text, jsonb, text, timestamptz) to authenticated;
grant execute on function public.retirar_texto_legal(text, text) to authenticated;
grant execute on function public.aceptar_textos(text, jsonb) to authenticated;
