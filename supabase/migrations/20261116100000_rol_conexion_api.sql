-- Rol de conexion del backend (ADR-007): sin privilegios propios; cada transaccion asume
-- `authenticated` (o `anon`) con `set local role`. La contrasena no va aqui: en local la fija
-- supabase/seed.sql; en otros entornos, el despliegue (alter role ... password).
create role bugalu_api login noinherit nosuperuser nocreatedb nocreaterole nobypassrls;

grant anon, authenticated to bugalu_api;
