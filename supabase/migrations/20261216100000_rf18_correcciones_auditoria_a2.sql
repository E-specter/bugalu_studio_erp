-- RF-18, correcciones de la auditoria A (ronda 2). Se parte de las versiones vigentes (214 y 215). Orden de bloqueo sin
-- cambios: sala (advisory, backend) -> cuotas de la reserva -> reserva -> creditos.

-- 1. Lo pagado que sigue siendo del cliente descuenta tambien lo que ya volvio a un credito de origen (reprogramar con
-- diferencia a favor), para no devolverlo ni acreditarlo dos veces.
create or replace function public.pagado_neto(p_id_reserva uuid)
returns numeric
language sql
stable
security definer
set search_path = ''
as $$
  select greatest(
    coalesce((select sum(c.pagado) from public.cuota c where c.id_reserva = p_id_reserva), 0)
    - coalesce((select sum(g.penalizacion) from public.reprogramacion g where g.id_reserva = p_id_reserva), 0)
    - coalesce((select sum(k.monto) from public.credito k where k.id_reserva = p_id_reserva and k.tipo = 'reprogramacion'), 0)
    - coalesce((select sum(x.devuelto) from public.aplicacion_credito x join public.cuota c on c.id = x.id_cuota
                where c.id_reserva = p_id_reserva), 0),
    0);
$$;

-- 2. Con una captura en validacion no se elige tras una cancelacion del estudio: se espera a que se valide (detail
-- `en_validacion`). Vale para reprogramar sin costo y para su vista previa.
create or replace function public.exigir_reprogramable(r public.reserva)
returns table (e_estudio boolean, e_nivel smallint, e_hechas integer, e_hechas_2 integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  e_estudio := r.estado = 'cancelada' and r.eleccion_estudio = 'pendiente';
  if r.id_cliente <> v_uid and not (e_estudio and public.es_administrador()) then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if e_estudio and exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                           where c.id_reserva = r.id and p.estado = 'pendiente_validacion') then
    raise exception 'eleccion_no_disponible' using errcode = 'P0001', detail = 'en_validacion';
  end if;
  select count(*) filter (where g.nivel is not null), count(*) filter (where g.nivel = 2) into e_hechas, e_hechas_2
    from public.reprogramacion g where g.id_reserva = r.id;
  e_nivel := null;
  if not e_estudio then
    if r.estado <> 'confirmada' or r.inicio <= now() then
      raise exception 'reprogramacion_no_permitida' using errcode = 'P0001';
    end if;
    e_nivel := public.nivel_cancelacion(r.inicio, now(), r.parametros_aplicados);
    if e_nivel = 3 then
      raise exception 'reprogramacion_no_permitida' using errcode = 'P0001';
    end if;
    if e_hechas >= (r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int
       or (e_nivel = 2 and e_hechas_2 >= (r.parametros_aplicados ->> 'reprogramaciones_nivel_2')::int) then
      raise exception 'limite_reprogramaciones' using errcode = 'P0001';
    end if;
    -- Un pago en validacion apunta al monto actual de la cuota: se espera a que se valide.
    if exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
               where c.id_reserva = r.id and p.estado = 'pendiente_validacion') then
      raise exception 'reprogramacion_no_permitida' using errcode = 'P0001';
    end if;
  end if;
  return next;
end;
$$;

create or replace function public.elegir_estudio_devolucion(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
  v_pagado numeric;
  v_credito numeric;
  v_dinero numeric;
  v_limite timestamptz;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.id_cliente <> v_uid and not public.es_administrador() then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_pagado := public.pagado_neto(r.id);
  if r.estado <> 'cancelada' or r.eleccion_estudio is distinct from 'pendiente' or v_pagado <= 0 then
    raise exception 'eleccion_no_disponible' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
             where c.id_reserva = r.id and p.estado = 'pendiente_validacion') then
    raise exception 'eleccion_no_disponible' using errcode = 'P0001', detail = 'en_validacion';
  end if;
  v_credito := public.devolver_credito_aplicado(r.id, v_pagado, (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  v_dinero := v_pagado - v_credito;
  v_limite := public.sumar_dias_habiles(now(), 7);
  if v_dinero > 0 then
    insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado, estado, monto_aprobado, decidida_en, limite)
    values (r.id, r.id_cliente, 'estudio', 'Devolución íntegra por cancelación del estudio', v_dinero, 'aprobada', v_dinero,
            now(), v_limite);
  end if;
  update public.reserva set eleccion_estudio = 'devolucion' where id = r.id;
  if v_uid = r.id_cliente then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'eleccion_estudio_resuelta', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre, 'opcion', 'devolucion',
                              'monto', v_dinero, 'limite', v_limite)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  end if;
end;
$$;

-- Defensa: un pago aprobado despues de una eleccion `devolucion` se devuelve tambien (devolucion nueva, aprobada y total,
-- con su plazo; la ya hecha es inmutable). Con otra eleccion pendiente, la eleccion futura lo incluye.
create or replace function public.aplicar_pago_tardio(p_id_reserva uuid, p_monto numeric)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_nivel smallint;
  v_pagado numeric;
  v_ret numeric;
  v_delta_ret numeric;
begin
  select * into r from public.reserva where id = p_id_reserva;
  v_pagado := coalesce(r.pagado_cancelacion, 0) + p_monto;
  v_nivel := case when r.excepcion_en is not null then 1 when r.cancelacion_por = 'inasistencia' then 3
                  when r.cancelacion_por = 'estudio' then null else r.nivel_cancelacion end;
  if v_nivel is null then
    update public.reserva set pagado_cancelacion = v_pagado where id = r.id;
    if r.eleccion_estudio = 'devolucion' and p_monto > 0 then
      insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado, estado, monto_aprobado, decidida_en, limite)
      values (r.id, r.id_cliente, 'estudio', 'Devolución de un pago validado tras la cancelación del estudio', p_monto,
              'aprobada', p_monto, now(), public.sumar_dias_habiles(now(), 7));
    end if;
    return;
  end if;
  v_ret := case v_nivel when 1 then coalesce(r.retenido, 0)
                        when 2 then least(v_pagado, public.penalizacion_nivel_2(r.total, r.parametros_aplicados))
                        else coalesce(r.retenido, 0) + p_monto end;
  v_delta_ret := v_ret - coalesce(r.retenido, 0);
  update public.reserva
  set pagado_cancelacion = v_pagado, retenido = v_ret, credito_generado = coalesce(credito_generado, 0) + (p_monto - v_delta_ret)
  where id = r.id;
  if p_monto - v_delta_ret > 0 then
    perform public.generar_credito(r.id_cliente, r.id, case when r.excepcion_en is not null then 'excepcion' else 'nivel_' || v_nivel end,
      p_monto - v_delta_ret, (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  end if;
end;
$$;

-- 3 y 4. Reprogramar: la diferencia a favor vuelve primero a sus creditos de origen (tipo y vencimiento); solo el resto es
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
            now() + make_interval(hours => (select valor from public.parametro where clave = 'horas_limite_pago')::int)))
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

-- 5. La decision total aprueba lo solicitado: el credito congelado pudo recibir credito devuelto mientras tanto, y lo que
-- sobra sigue como credito vigente.
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
  if p_decision = 'parcial' and (p_monto is null or p_monto < 0.01 or p_monto > k.saldo or p_monto <> round(p_monto, 2)) then
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
