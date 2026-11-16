-- RF-04: cancelar una reserva (RN-20), plazos de pago, existencia de una reserva ajena y aviso de reserva creada.

-- El cliente cancela la suya sin pagos; el administrador cualquiera, tambien sin pagos mientras D-11 siga abierta.
-- Errores: P0002 no existe, 42501 ajena, P0001 con mensaje `no_cancelable` o `tiene_pagos`.
create function public.cancelar_reserva(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
begin
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if v_uid is null or (r.id_cliente <> v_uid and not public.es_administrador()) then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada') then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if public.tiene_pagos(r.id) then
    raise exception 'tiene_pagos' using errcode = 'P0001';
  end if;
  update public.reserva
  set estado = 'cancelada',
      motivo_cancelacion = case when r.id_cliente = v_uid then 'cliente' else 'administrador' end
  where id = p_id;
end;
$$;
revoke all on function public.cancelar_reserva(uuid) from public, anon;
grant execute on function public.cancelar_reserva(uuid) to authenticated;

-- Distingue 403 de 404: la RLS oculta las ajenas, pero el backend debe saber si existen (no devuelve datos).
create function public.existe_reserva(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.reserva where id = p_id);
$$;
revoke all on function public.existe_reserva(uuid) from public, anon;
grant execute on function public.existe_reserva(uuid) to authenticated;

-- Plazos de pago (RN-18) para fijar `vence_pago`: `parametro` solo lo lee el administrador.
create function public.plazos_pago()
returns table (dias integer, horas integer)
language sql
stable
security definer
set search_path = ''
as $$
  select
    (select valor from public.parametro where clave = 'dias_limite_pago'),
    (select valor from public.parametro where clave = 'horas_limite_pago');
$$;
revoke all on function public.plazos_pago() from public, anon;
grant execute on function public.plazos_pago() to authenticated;

-- Encola el correo de reserva creada (RN-21) al correo del dueño; una sola vez por reserva.
create function public.encolar_aviso_reserva(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_dueno uuid;
begin
  select id_cliente into v_dueno from public.reserva where id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if v_dueno <> (select auth.uid()) and not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'reserva_creada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                            'vence_pago', r.vence_pago, 'servicio', s.nombre, 'total', r.total)
  from public.reserva r
  join auth.users u on u.id = r.id_cliente
  join public.servicio s on s.id = r.id_servicio
  where r.id = p_id
    and not exists (select 1 from public.notificacion n
                    where n.tipo = 'reserva_creada' and n.datos ->> 'id_reserva' = r.id::text);
end;
$$;
revoke all on function public.encolar_aviso_reserva(uuid) from public, anon;
grant execute on function public.encolar_aviso_reserva(uuid) to authenticated;
