-- RF-01 / ADR-008: perfil ampliado, solicitudes de acceso interno, ultimo administrador y correo confirmado.

-- 1. usuario: telefono y nombre artistico (rol y especialidad siguen sin privilegio de update)
alter table public.usuario
  add column telefono text check (telefono ~ '^\+?[0-9]{9,15}$'),
  add column nombre_artistico text;

grant update (telefono, nombre_artistico) on public.usuario to authenticated;

-- El alta toma nombre, telefono (si es valido) y nombre artistico de los metadatos; nunca rol ni especialidad.
create or replace function public.crear_perfil_usuario()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.usuario (id, nombre, telefono, nombre_artistico)
  values (
    new.id,
    nullif(new.raw_user_meta_data ->> 'nombre', ''),
    case when new.raw_user_meta_data ->> 'telefono' ~ '^\+?[0-9]{9,15}$' then new.raw_user_meta_data ->> 'telefono' end,
    nullif(new.raw_user_meta_data ->> 'nombre_artistico', '')
  );
  return new;
end;
$$;

-- 2. solicitud_acceso
create table public.solicitud_acceso (
  id uuid primary key default gen_random_uuid(),
  id_usuario uuid not null references public.usuario (id) on delete cascade,
  especialidad text not null check (btrim(especialidad) <> ''),
  mensaje text,
  estado text not null default 'pendiente' check (estado in ('pendiente', 'aprobada', 'rechazada')),
  motivo text,
  id_revisor uuid references public.usuario (id),
  creada_en timestamptz not null default now(),
  revisada_en timestamptz
);

create unique index solicitud_acceso_una_pendiente on public.solicitud_acceso (id_usuario) where estado = 'pendiente';

alter table public.solicitud_acceso enable row level security;

-- El dueño solo inserta id_usuario, especialidad y mensaje (privilegio de columna) y la politica exige estado pendiente.
-- El administrador actualiza solo los campos de revision. Nadie borra por la API.
revoke all on public.solicitud_acceso from anon, authenticated;
grant select on public.solicitud_acceso to authenticated;
grant insert (id_usuario, especialidad, mensaje, estado, motivo, id_revisor) on public.solicitud_acceso to authenticated;
grant update (estado, motivo, id_revisor, revisada_en) on public.solicitud_acceso to authenticated;

create policy solicitud_lee_propia on public.solicitud_acceso
  for select to authenticated using (id_usuario = (select auth.uid()));

create policy solicitud_admin_lee_todas on public.solicitud_acceso
  for select to authenticated using (public.es_administrador());

create policy solicitud_crea_propia on public.solicitud_acceso
  for insert to authenticated
  with check (id_usuario = (select auth.uid()) and estado = 'pendiente' and motivo is null and id_revisor is null);

create policy solicitud_admin_revisa on public.solicitud_acceso
  for update to authenticated
  using (public.es_administrador())
  with check (public.es_administrador());

-- 3. Nunca queda la tabla sin administrador (SQLSTATE propio BG001; el backend lo traduce a 409)
create function public.impedir_sin_administrador()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.rol = 'administrador'
     and not exists (select 1 from public.usuario where rol = 'administrador') then
    raise exception 'no puede quedar el sistema sin administradores' using errcode = 'BG001';
  end if;
  return null;
end;
$$;

revoke all on function public.impedir_sin_administrador() from public, anon, authenticated;

create trigger usuario_conserva_administrador
  after update of rol or delete on public.usuario
  for each row execute function public.impedir_sin_administrador();

-- 4. Correo confirmado del usuario autenticado
create function public.correo_confirmado()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(
    (select email_confirmed_at is not null from auth.users where id = (select auth.uid())),
    false
  );
$$;

revoke all on function public.correo_confirmado() from public, anon;
grant execute on function public.correo_confirmado() to authenticated;
