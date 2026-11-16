-- RF-03: lecturas que el backend necesita y la RLS no permite directamente (ADR-009).

-- Anticipacion de reserva (RN-17): la ventana reservable es publica; el resto de `parametro` sigue solo para el administrador.
create function public.limites_reserva()
returns table (minima_horas integer, maxima_semanas integer)
language sql
stable
security definer
set search_path = ''
as $$
  select
    (select valor from public.parametro where clave = 'anticipacion_minima_horas'),
    (select valor from public.parametro where clave = 'anticipacion_maxima_semanas');
$$;
revoke all on function public.limites_reserva() from public;
grant execute on function public.limites_reserva() to anon, authenticated;

-- Nombre de los clientes de una reserva (RN-19): solo personal o administrador; para cualquier otro, sin filas.
create function public.nombres_de_clientes(p_ids uuid[])
returns table (id uuid, nombre text)
language sql
stable
security definer
set search_path = ''
as $$
  select u.id, u.nombre
  from public.usuario u
  where public.es_personal() and u.id = any(p_ids);
$$;
revoke all on function public.nombres_de_clientes(uuid[]) from public, anon;
grant execute on function public.nombres_de_clientes(uuid[]) to authenticated;
