-- RF-01 / ADR-008: verificacion del correo propia, asignacion de rol por el administrador y lectura de correos.

-- 1. Verificacion del correo: solo la escribe marcar_correo_verificado() (sin grant de update a authenticated).
alter table public.usuario add column correo_verificado_en timestamptz;

-- Verificado = la sesion viene de un enlace de correo de un solo uso (otp/magiclink) o de Google (oauth).
-- SQLSTATE propio BG002: el backend lo traduce a 409 verificacion_no_valida.
create function public.marcar_correo_verificado()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1
    from jsonb_array_elements(coalesce(auth.jwt() -> 'amr', '[]'::jsonb)) as metodo
    where metodo ->> 'method' in ('otp', 'magiclink', 'oauth')
  ) then
    raise exception 'la sesion no viene de un enlace de correo ni de Google' using errcode = 'BG002';
  end if;
  update public.usuario set correo_verificado_en = coalesce(correo_verificado_en, now())
  where id = (select auth.uid());
  return found;
end;
$$;

revoke all on function public.marcar_correo_verificado() from public, anon;
grant execute on function public.marcar_correo_verificado() to authenticated;

-- Supabase confirma al registrar: el correo confirmado es el verificado por el flujo propio.
create or replace function public.correo_confirmado()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(
    (select correo_verificado_en is not null from public.usuario where id = (select auth.uid())),
    false
  );
$$;

-- 2. Asignar rol y especialidad (los unicos campos que el usuario no edita). Respeta el trigger BG001.
-- Se eligio funcion y no grant de columna: el administrador no recibe update directo sobre rol,
-- y la comprobacion es_administrador() queda dentro de la propia funcion.
create function public.asignar_rol(id_usuario uuid, rol text, especialidad text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador asigna roles' using errcode = '42501';
  end if;
  update public.usuario as u set rol = asignar_rol.rol, especialidad = asignar_rol.especialidad
  where u.id = asignar_rol.id_usuario;
  if not found then
    raise exception 'el usuario no existe' using errcode = 'P0002';
  end if;
end;
$$;

revoke all on function public.asignar_rol(uuid, text, text) from public, anon;
grant execute on function public.asignar_rol(uuid, text, text) to authenticated;

-- 3. El correo vive en auth.users: cada usuario lee el suyo y el administrador el de cualquiera.
create function public.correo_de_usuario(id_usuario uuid)
returns text
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if id_usuario is distinct from (select auth.uid()) and not public.es_administrador() then
    raise exception 'sin permiso para leer ese correo' using errcode = '42501';
  end if;
  return (select email::text from auth.users where id = id_usuario);
end;
$$;

revoke all on function public.correo_de_usuario(uuid) from public, anon;
grant execute on function public.correo_de_usuario(uuid) to authenticated;
