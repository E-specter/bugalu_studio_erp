-- RF-18, retoques de la auditoria A (ronda 3): tope de la decision parcial en lo solicitado, plazo de pago de una
-- reprogramacion sin costo desde la foto de parametros y fin_buffer recalculado al mover una reserva.

-- 1. fin_buffer tambien al actualizar inicio o fin (RN-02); la reprogramacion por funcion fija el mismo valor.
create or replace function public.preparar_reserva()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.fin_buffer := new.fin + interval '30 minutes';
  if tg_op = 'INSERT' and new.estado <> 'cancelada' then
    perform public.caducar_reservas(new.id_sala, new.inicio, new.fin_buffer);
  end if;
  return new;
end;
$$;
create trigger reserva_recalcular_buffer before update of inicio, fin on public.reserva
  for each row when (old.inicio is distinct from new.inicio or old.fin is distinct from new.fin)
  execute function public.preparar_reserva();

-- 2. Reprogramar (misma funcion que en la ronda 2): la diferencia a favor vuelve primero a sus creditos de origen (tipo y vencimiento); solo el resto es
-- credito `reprogramacion`. Una pre_reservada que vuelve tras una cancelacion del estudio recibe un plazo de pago como
-- el de una reserva nueva con el inicio nuevo (RN-18).
create or replace function public.reprogramar_reserva(
  p_id uuid, p_nuevo_inicio timestamptz, p_nivel_esperado integer, p_total_esperado numeric, p_id_franja uuid,
  p_precio jsonb, p_total_nuevo numeric, p_especialistas jsonb default '[]')
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
  v record;
  v_fin timestamptz;
  v_detalle text;
  v_estado text;
  v_devuelto numeric;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into v from public.calcular_reprogramacion(p_id, p_nuevo_inicio, p_total_nuevo);
  v_detalle := jsonb_build_object('nivel', v.nivel, 'penalizacion', v.penalizacion::text, 'saldo', v.saldo::text,
    'credito', v.credito::text, 'reprogramaciones_restantes', v.reprogramaciones_restantes)::text;
  if p_nivel_esperado is distinct from v.nivel then
    raise exception 'nivel_cambiado' using errcode = 'P0001', detail = v_detalle;
  end if;
  if p_total_esperado is distinct from v.total_nuevo and not (v.estudio and p_total_esperado is null) then
    raise exception 'precio_cambiado' using errcode = 'P0001', detail = v_detalle;
  end if;
  v_fin := p_nuevo_inicio + (r.fin - r.inicio);
  perform public.caducar_reservas(r.id_sala, p_nuevo_inicio, v_fin + interval '30 minutes'); -- como al insertar
  if v.estudio then
    -- Vuelve al estado de antes de cancelar: confirmada si el adelanto esta pagado, si no pre_reservada.
    v_estado := case when exists (select 1 from public.cuota q where q.id_reserva = r.id and q.hito = 'al_reservar'
                                  and q.estado = 'pagada') then 'confirmada' else 'pre_reservada' end;
    update public.reserva
    set estado = v_estado,
        motivo_cancelacion = null, inicio = p_nuevo_inicio, fin = v_fin, fin_buffer = v_fin + interval '30 minutes',
        id_franja = p_id_franja, eleccion_estudio = 'reprogramada',
        vence_pago = case when v_estado = 'pre_reservada' then
          least(p_nuevo_inicio, greatest(
            p_nuevo_inicio - make_interval(days => (select valor from public.parametro where clave = 'dias_limite_pago')::int),
            now() + make_interval(hours => (r.parametros_aplicados ->> 'horas_limite_pago')::int)))
          else vence_pago end
    where id = r.id;
    update public.cuota set estado = 'pendiente' where id_reserva = r.id and estado = 'anulada';
  else
    update public.reserva
    set inicio = p_nuevo_inicio, fin = v_fin, fin_buffer = v_fin + interval '30 minutes', id_franja = p_id_franja,
        precio = p_precio, total = v.total_nuevo
    where id = r.id;
    -- La cuota de saldo pasa a lo ya aplicado mas el saldo nuevo (0.00 si hay credito); el adelanto no cambia.
    update public.cuota q
    set monto = q.pagado + v.saldo, estado = case when v.saldo = 0 then 'pagada' else 'pendiente' end
    where q.id_reserva = r.id and q.hito = 'al_terminar';
    update public.reserva_especialista re
    set monto_fijo = (x.value ->> 'monto_fijo')::numeric, monto_variable = (x.value ->> 'monto_variable')::numeric,
        unidad = x.value ->> 'unidad'
    from jsonb_array_elements(p_especialistas) x
    where re.id_reserva = r.id and re.id_especialista = (x.value ->> 'id')::uuid;
    if v.credito > 0 then
      v_devuelto := public.devolver_credito_aplicado(r.id, v.credito);
      if v.credito > v_devuelto then
        perform public.generar_credito(r.id_cliente, r.id, 'reprogramacion', v.credito - v_devuelto,
          (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
      end if;
    end if;
  end if;
  insert into public.reprogramacion (id_reserva, anterior_inicio, nuevo_inicio, nivel, penalizacion, total_anterior,
                                     total_nuevo, id_autor)
  values (r.id, r.inicio, p_nuevo_inicio, v.nivel, v.penalizacion, r.total, v.total_nuevo, v_uid);
  insert into public.notificacion (tipo, destinatario, datos)
  select 'reserva_reprogramada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', p_nuevo_inicio, 'fin', v_fin,
                            'anterior_inicio', r.inicio, 'nivel', v.nivel, 'penalizacion', v.penalizacion,
                            'saldo', v.saldo, 'credito', v.credito, 'sin_costo', v.estudio)
  from auth.users u where u.id = r.id_cliente;
  if v.estudio and v_uid = r.id_cliente then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'eleccion_estudio_resuelta', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre, 'opcion', 'reprogramar',
                              'inicio', p_nuevo_inicio, 'fin', v_fin)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  end if;
end;
$$;

-- 3. La decision parcial tiene como tope lo solicitado (y el saldo del credito): nunca mas de lo que pidio el cliente.
create or replace function public.decidir_devolucion(p_id uuid, p_decision text, p_monto numeric default null, p_motivo text default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_motivo text := nullif(btrim(p_motivo), '');
  d public.devolucion%rowtype;
  k public.credito%rowtype;
  v_monto numeric;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if p_decision is null or p_decision not in ('total', 'parcial', 'rechazo') then
    raise exception 'decision_invalida' using errcode = '22023';
  end if;
  select * into d from public.devolucion where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if d.estado <> 'pendiente' then
    raise exception 'devolucion_decidida' using errcode = 'P0001';
  end if;
  select * into k from public.credito where id = d.id_credito for update;
  if p_decision = 'parcial' and (p_monto is null or p_monto < 0.01 or p_monto > least(k.saldo, d.monto_solicitado) or p_monto <> round(p_monto, 2)) then
    raise exception 'monto_invalido' using errcode = '22023';
  end if;
  if (p_decision <> 'total' and (v_motivo is null or char_length(v_motivo) not between 10 and 500))
     or char_length(v_motivo) > 500 then
    raise exception 'motivo_requerido' using errcode = '22023';
  end if;
  v_monto := case p_decision when 'total' then least(d.monto_solicitado, k.saldo) when 'parcial' then p_monto end;
  update public.devolucion
  set estado = case when p_decision = 'rechazo' then 'rechazada' else 'aprobada' end, monto_aprobado = v_monto,
      motivo_decision = v_motivo, decidida_en = now(), id_decisor = v_uid
  where id = d.id;
  update public.credito
  set saldo = saldo - coalesce(v_monto, 0), congelado = false,
      estado = case when saldo - coalesce(v_monto, 0) = 0 then 'agotado' else estado end,
      vence = case when vence <= now() then public.fin_de_dia_lima(now(), 7) else vence end
  where id = k.id;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'devolucion_decidida', u.email,
         jsonb_build_object('id_devolucion', d.id, 'decision', p_decision, 'monto_aprobado', v_monto, 'motivo', v_motivo,
                            'folio_origen', (select folio from public.reserva where id = d.id_reserva))
  from auth.users u where u.id = d.id_cliente;
end;
$$;
