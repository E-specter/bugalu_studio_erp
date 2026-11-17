-- RF-20 (2/2): confirmaciones de cambios sensibles (token de un solo uso) y registro de cambios (CA-05, CA-06, CA-08).

-- Confirmacion: lo que el administrador vio en la vista previa. El token nunca se guarda en claro (solo su hash).
-- `cambios` = {campo: {"anterior": texto, "nuevo": texto}}.
create table public.confirmacion_cambio (
  id uuid primary key default gen_random_uuid(),
  hash_token text not null unique,
  id_autor uuid not null references public.usuario (id) on delete cascade,
  recurso text not null check (recurso in ('impuestos', 'servicio', 'especialista', 'recargos', 'parametros')),
  id_recurso uuid,
  nombre_recurso text not null,
  cambios jsonb not null,
  creada_en timestamptz not null default now(),
  expira_en timestamptz not null,
  usada_en timestamptz,
  check (expira_en > creada_en)
);

alter table public.confirmacion_cambio enable row level security;
revoke all on public.confirmacion_cambio from anon, authenticated;
grant select, insert on public.confirmacion_cambio to authenticated;
create policy confirmacion_cambio_propia_lectura on public.confirmacion_cambio
  for select to authenticated using (id_autor = auth.uid() and public.es_administrador());
create policy confirmacion_cambio_propia_alta on public.confirmacion_cambio
  for insert to authenticated with check (id_autor = auth.uid() and public.es_administrador() and usada_en is null);

-- Registro de cambios: una fila por campo. Sin FK al autor: el registro sobrevive a la baja del usuario.
create table public.registro_cambio (
  id uuid primary key default gen_random_uuid(),
  cambiado_en timestamptz not null default now(),
  id_autor uuid not null,
  autor_nombre text not null,
  recurso text not null check (recurso in ('impuestos', 'servicio', 'especialista', 'recargos', 'parametros')),
  id_recurso uuid,
  nombre_recurso text not null,
  campo text not null,
  anterior text not null,
  nuevo text not null
);
create index registro_cambio_cambiado_en_idx on public.registro_cambio (cambiado_en desc);

alter table public.registro_cambio enable row level security;
revoke all on public.registro_cambio from anon, authenticated;
grant select on public.registro_cambio to authenticated;
create policy registro_cambio_lectura_administrador on public.registro_cambio
  for select to authenticated using (public.es_administrador());

-- Nadie edita, borra ni vacia el registro: tampoco el propietario de la tabla (CA-08).
create function public.registro_cambio_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  raise exception 'El registro de cambios no se edita ni se borra.';
end;
$$;
create trigger registro_cambio_sin_edicion before update or delete on public.registro_cambio
  for each row execute function public.registro_cambio_inmutable();
create trigger registro_cambio_sin_vaciado before truncate on public.registro_cambio
  for each statement execute function public.registro_cambio_inmutable();

-- Busca y bloquea la confirmacion por el hash de su token. Cualquier administrador la ve (el backend responde 403 si
-- no es suya); `vigente` = sin usar y sin vencer.
create function public.confirmacion_para_aplicar(p_hash text)
returns table (
  id uuid, id_autor uuid, recurso text, id_recurso uuid, nombre_recurso text, cambios jsonb, vigente boolean
)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  return query
    select c.id, c.id_autor, c.recurso, c.id_recurso, c.nombre_recurso, c.cambios,
           (c.usada_en is null and c.expira_en > now())
      from public.confirmacion_cambio c where c.hash_token = p_hash for update;
end;
$$;

-- Unica via de escritura del registro: consume la confirmacion propia (un solo uso, vigente) y deja una fila por campo.
create function public.registrar_cambios(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.confirmacion_cambio%rowtype;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  update public.confirmacion_cambio set usada_en = now()
    where id = p_id and id_autor = auth.uid() and usada_en is null and expira_en > now()
    returning * into v;
  if not found then
    raise exception 'Confirmacion no valida.' using errcode = '55000';
  end if;
  insert into public.registro_cambio (id_autor, autor_nombre, recurso, id_recurso, nombre_recurso, campo, anterior, nuevo)
    select v.id_autor,
           coalesce((select nullif(u.nombre, '') from public.usuario u where u.id = v.id_autor), 'Administrador'),
           v.recurso, v.id_recurso, v.nombre_recurso, c.key, c.value ->> 'anterior', c.value ->> 'nuevo'
      from jsonb_each(v.cambios) c;
end;
$$;

revoke all on function public.confirmacion_para_aplicar(text) from public, anon;
revoke all on function public.registrar_cambios(uuid) from public, anon;
grant execute on function public.confirmacion_para_aplicar(text) to authenticated;
grant execute on function public.registrar_cambios(uuid) to authenticated;
