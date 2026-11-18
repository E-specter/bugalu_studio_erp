-- La politica de borrado de `anon` evalua subida_reclamacion_huerfana con los privilegios de quien consulta Storage
-- (PostgreSQL comprueba el execute del rol que ejecuta la consulta, aunque la funcion sea security definer): `anon` lo
-- conserva. La funcion solo dice si una ruta ya es huerfana. Authenticated y service_role siguen sin ella.
grant execute on function public.subida_reclamacion_huerfana(text) to anon;
