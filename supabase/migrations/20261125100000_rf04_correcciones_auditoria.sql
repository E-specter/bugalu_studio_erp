-- Correcciones de la auditoria A de RF-02/03/04 (TAREA-RF04-9).

-- B1: retirar una franja con reservas canceladas o vencidas no debe fallar; la reserva conserva su tramo.
alter table public.reserva drop constraint reserva_id_franja_fkey;
alter table public.reserva
  add constraint reserva_id_franja_fkey foreign key (id_franja) references public.franja_sala (id)
  on delete set null;

-- Defensa en profundidad. El backend inserta reserva, cuotas y especialistas con la identidad del cliente,
-- asi que se conserva el insert directo pero acotado: la cuota nace siempre `pendiente` (sin `estado`) y la
-- reserva exige plazo de pago.
revoke insert on public.cuota from authenticated;
grant insert (id_reserva, hito, monto) on public.cuota to authenticated;

drop policy reserva_cliente_inserta on public.reserva;
create policy reserva_cliente_inserta on public.reserva for insert to authenticated
  with check (id_cliente = (select auth.uid()) and estado = 'pre_reservada' and motivo_cancelacion is null
    and vence_pago is not null and total >= 0);

-- Sin `sub` el dueno es null y `<>` no rechazaba: `is distinct from` si.
create or replace function public.encolar_aviso_reserva(p_id uuid)
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
  if v_dueno is distinct from (select auth.uid()) and not public.es_administrador() then
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
