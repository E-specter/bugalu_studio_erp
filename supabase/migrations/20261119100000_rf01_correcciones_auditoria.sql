-- RF-01 / auditoria: carrera del ultimo administrador y verificacion del correo al cambiarlo.

-- 1. Serializa los cambios de rol y borrados de usuario: sin esto, dos transacciones cruzadas
-- (A quita a B, B quita a A) no ven el cambio no confirmado de la otra y dejan 0 administradores.
-- La constante 20261119 es la clave del bloqueo (fecha de esta migracion); el bloqueo se libera al
-- confirmar o revertir, y la cuenta se hace despues de obtenerlo (READ COMMITTED ve lo ya confirmado).
create or replace function public.impedir_sin_administrador()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.rol = 'administrador' then
    perform pg_advisory_xact_lock(20261119);
    if not exists (select 1 from public.usuario where rol = 'administrador') then
      raise exception 'no puede quedar el sistema sin administradores' using errcode = 'BG001';
    end if;
  end if;
  return null;
end;
$$;

-- 2. Un correo nuevo no hereda la verificacion del anterior (aunque double_confirm_changes se desactive).
create function public.reiniciar_verificacion_correo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.usuario set correo_verificado_en = null where id = new.id;
  return null;
end;
$$;

revoke all on function public.reiniciar_verificacion_correo() from public, anon, authenticated;

create trigger usuario_reinicia_verificacion_al_cambiar_correo
  after update of email on auth.users
  for each row when (old.email is distinct from new.email)
  execute function public.reiniciar_verificacion_correo();
