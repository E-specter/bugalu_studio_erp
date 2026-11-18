-- RF-15 etapa A, retoques de la auditoria (ronda 2): quien tiene operaciones de cliente vivas no pasa a `profesional`
-- (no podria pagar, cancelar ni pedir la devolucion) y la foto vigente no se sobrescribe directo en Storage.

-- Interna: la llama asignar_rol (security definer); nadie mas.
create function public.operaciones_vivas_de_cliente(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'reservas_vivas', (select count(*) from public.reserva where id_cliente = p_id and estado in ('pre_reservada', 'confirmada')),
    'creditos_vigentes', (select count(*) from public.credito where id_cliente = p_id and estado = 'vigente' and vence > now()),
    'pagos_en_validacion', (select count(*) from public.comprobante_pago where id_cliente = p_id and estado = 'pendiente_validacion'),
    'devoluciones_pendientes', (select count(*) from public.devolucion where id_cliente = p_id and estado = 'pendiente'));
$$;
revoke all on function public.operaciones_vivas_de_cliente(uuid) from public, anon, authenticated;

-- BG003: cliente_con_operaciones. `detail` lleva los conteos (jsonb) para que la API diga que queda.
-- Ya profesional no se revisa (reasignarlo es idempotente). El `for update` de la fila de usuario espera a quien
-- inserte una reserva o un pago suyo (la clave foranea toma un bloqueo compartido sobre esa fila).
create or replace function public.asignar_rol(id_usuario uuid, rol text, especialidad text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_rol text;
  v_operaciones jsonb;
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador asigna roles' using errcode = '42501';
  end if;
  select u.rol into v_rol from public.usuario as u where u.id = asignar_rol.id_usuario for update;
  if not found then
    raise exception 'el usuario no existe' using errcode = 'P0002';
  end if;
  if asignar_rol.rol = 'profesional' and v_rol is distinct from 'profesional' then
    v_operaciones := public.operaciones_vivas_de_cliente(id_usuario);
    if exists (select 1 from jsonb_each(v_operaciones) where value <> '0'::jsonb) then
      raise exception 'cliente_con_operaciones' using errcode = 'BG003', detail = v_operaciones::text;
    end if;
  end if;
  update public.usuario as u set rol = asignar_rol.rol, especialidad = asignar_rol.especialidad
  where u.id = asignar_rol.id_usuario;
  if asignar_rol.rol = 'profesional' then
    perform public.crear_perfil_profesional(id_usuario);
  elsif asignar_rol.rol <> 'administrador' then
    update public.perfil_profesional set activo = false where id = id_usuario and activo;
  end if;
end;
$$;

-- Con `x-upsert` la subida directa actualiza el objeto: la ruta de la foto vigente queda fuera. La API escribe
-- siempre en la ruta libre (alterna foto-1 y foto-2), asi que no pierde nada.
create function public.es_foto_vigente(p_nombre text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.perfil_profesional where foto_ruta = p_nombre);
$$;
revoke all on function public.es_foto_vigente(text) from public, anon;
grant execute on function public.es_foto_vigente(text) to authenticated;
drop policy profesionales_sobrescribe on storage.objects;
create policy profesionales_sobrescribe on storage.objects for update to authenticated
  using (bucket_id = 'profesionales' and public.gestiona_foto_de_perfil(name) and not public.es_foto_vigente(name))
  with check (bucket_id = 'profesionales' and public.gestiona_foto_de_perfil(name) and not public.es_foto_vigente(name));
