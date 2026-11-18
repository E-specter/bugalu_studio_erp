-- Auditoria A de RF-16, ronda 3: privilegios de las funciones de hoja, IPv4 mapeada y id_reserva invalido.

-- Privilegios: solo la API llama estas funciones. La politica de borrado las evalua con security definer.
revoke all on function public.avisar_hoja(uuid) from public, anon, authenticated, service_role;
grant execute on function public.avisar_hoja(uuid) to bugalu_api;
revoke all on function public.subida_reclamacion_huerfana(text) from public, anon, authenticated, service_role;
grant execute on function public.subida_reclamacion_huerfana(text) to bugalu_api;

-- Limite por IP: una IPv4 mapeada en IPv6 (::ffff:a.b.c.d) vale como la IPv4 embebida, no como un /64 comun a todas.
create or replace function public.ip_para_limite(p_ip text)
returns text
language plpgsql
immutable
set search_path = ''
as $$
declare
  v inet;
begin
  if p_ip like '%:%' then
    v := p_ip::inet;
    if v << '::ffff:0:0/96'::inet then
      return host('0.0.0.0'::inet + (v - '::ffff:0:0'::inet));
    end if;
    return network(set_masklen(v, 64))::text;
  end if;
  return coalesce(p_ip, '');
exception when others then
  return coalesce(p_ip, '');
end;
$$;

-- Un id_reserva que no sea uuid no tumba la consulta del lote: ese aviso queda sin fila y los demas conservan su evento.
create function public.uuid_o_nulo(p_texto text)
returns uuid
language sql
immutable
set search_path = ''
as $$
  select case when p_texto ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then p_texto::uuid end
$$;
revoke all on function public.uuid_o_nulo(text) from public, anon, authenticated, service_role;

create or replace function public.datos_reserva_para_correo(p_ids uuid[])
returns table (id_notificacion uuid, inicio timestamptz, fin timestamptz, servicio text, sala text, tiene_evento boolean)
language sql
stable
security definer
set search_path = ''
as $$
  select n.id, r.inicio, r.fin, s.nombre, sa.nombre,
         exists (
           select 1 from public.notificacion p
           where p.tipo = 'pago_aprobado' and p.id <> n.id
             and public.uuid_o_nulo(p.datos ->> 'id_reserva') = r.id
             and p.datos ->> 'reserva_confirmada' = 'true'
             and p.creada_en <= n.creada_en
         )
  from public.notificacion n
  join public.reserva r on r.id = public.uuid_o_nulo(n.datos ->> 'id_reserva')
  join public.servicio s on s.id = r.id_servicio
  join public.sala_tecnica sa on sa.id = r.id_sala
  where n.id = any (p_ids);
$$;
