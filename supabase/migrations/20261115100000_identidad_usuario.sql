-- RF-01: perfil de usuario ligado a auth.users (ADR-005, ADR-006).
create table public.usuario (
  id uuid primary key references auth.users (id) on delete cascade,
  nombre text,
  rol text not null default 'cliente' check (rol in ('cliente', 'personal', 'administrador')),
  especialidad text,
  creado_en timestamptz not null default now()
);

alter table public.usuario enable row level security;

-- Privilegios: solo lectura y edicion de nombre/especialidad. Sin insert ni delete por la API,
-- y sin update sobre rol ni id (impide la escalada de rol por privilegio de columna).
revoke all on public.usuario from anon, authenticated;
grant select on public.usuario to authenticated;
grant update (nombre, especialidad) on public.usuario to authenticated;

create function public.es_administrador()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.usuario
    where id = (select auth.uid()) and rol = 'administrador'
  );
$$;

revoke all on function public.es_administrador() from public, anon;
grant execute on function public.es_administrador() to authenticated;

create policy usuario_lee_propio on public.usuario
  for select to authenticated using (id = (select auth.uid()));

create policy usuario_admin_lee_todos on public.usuario
  for select to authenticated using (public.es_administrador());

create policy usuario_actualiza_propio on public.usuario
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- Alta en auth.users -> perfil con rol cliente.
create function public.crear_perfil_usuario()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.usuario (id, nombre)
  values (new.id, nullif(new.raw_user_meta_data ->> 'nombre', ''));
  return new;
end;
$$;

revoke all on function public.crear_perfil_usuario() from public, anon, authenticated;

create trigger al_crear_usuario
  after insert on auth.users
  for each row execute function public.crear_perfil_usuario();
