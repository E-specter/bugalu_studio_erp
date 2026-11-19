-- Lecturas de la asesoria que la RLS cerrada de `usuario` no permite: el profesional de la cita (para su cliente y
-- el administrador) y el contacto del cliente (solo su profesional y el administrador, CA-16).
create function public.profesional_de_asesorias(p_ids uuid[])
returns table (id_reserva uuid, id uuid, nombre text, nombre_artistico text)
language sql
stable
security definer
set search_path = ''
as $$
  select r.id, u.id, u.nombre, pp.nombre_artistico
  from public.reserva r
  join public.usuario u on u.id = r.id_profesional
  left join public.perfil_profesional pp on pp.id = u.id
  where r.tipo = 'asesoria' and r.id = any (p_ids)
    and (r.id_cliente = (select auth.uid()) or r.id_profesional = (select auth.uid()) or public.es_administrador());
$$;
create function public.contacto_de_asesorias(p_ids uuid[])
returns table (id_reserva uuid, id uuid, nombre text, nombre_artistico text, telefono text, correo text)
language sql
stable
security definer
set search_path = ''
as $$
  select r.id, u.id, u.nombre, u.nombre_artistico, u.telefono, a.email::text
  from public.reserva r
  join public.usuario u on u.id = r.id_cliente
  join auth.users a on a.id = u.id
  where r.tipo = 'asesoria' and r.id = any (p_ids)
    and (r.id_profesional = (select auth.uid()) or public.es_administrador());
$$;
revoke all on function public.profesional_de_asesorias(uuid[]), public.contacto_de_asesorias(uuid[]) from public, anon;
grant execute on function public.profesional_de_asesorias(uuid[]), public.contacto_de_asesorias(uuid[]) to authenticated;

-- Precisiones de la etapa B: cambiar de modalidad borra el dato de la otra (lo hace el backend al llamar a
-- cambiar_encuentro); lugar y enlace pueden quedar vacios ("por confirmar").
