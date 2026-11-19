-- RF-15 etapa B (backend B6): correos al profesional al cancelar o reprogramar una asesoria confirmada (CA-14), los
-- avisos al cliente con los datos de la asesoria (profesional, modalidad, lugar o enlace) y la nota obligatoria en
-- la cancelacion del estudio de una asesoria (CA-11), tambien sin pagos. `cancelar_reserva` y `reprogramar_reserva`
-- parten de su ULTIMA definicion vigente (20261229100000); la sala no cambia: `datos_asesoria_aviso` es null para ella.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in (
  'reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
  'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
  'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
  'devolucion_decidida', 'devolucion_realizada', 'reserva_reprogramada', 'eleccion_estudio_resuelta',
  'reclamacion_registrada', 'reclamacion_recibida', 'reclamacion_respondida', 'reclamaciones_por_vencer',
  'asesoria_confirmada_profesional', 'asesoria_encuentro_cambiado',
  'asesoria_cancelada_profesional', 'asesoria_reprogramada_profesional'));

-- Lo que los avisos de una asesoria dicen de ella; null si la reserva es de sala. Interna (solo la usan las
-- funciones security definer de abajo).
create function public.datos_asesoria_aviso(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object('profesional', coalesce(pp.nombre_artistico, pu.nombre), 'modalidad', a.modalidad,
                            'lugar', a.lugar, 'enlace', a.enlace)
  from public.reserva r
  join public.asesoria a on a.id_reserva = r.id
  left join public.usuario pu on pu.id = r.id_profesional
  left join public.perfil_profesional pp on pp.id = r.id_profesional
  where r.id = p_id;
$$;
revoke all on function public.datos_asesoria_aviso(uuid) from public, anon, authenticated;

-- Cancelar (parte de 20261229): nota siempre en la cancelacion del estudio de una asesoria.
create or replace function public.cancelar_reserva(
  p_id uuid, p_nota text default null, p_nivel_esperado integer default null, p_por text default null,
  p_aviso_en timestamptz default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_dueno boolean;
  v_admin boolean;
  v_directo boolean; -- el cliente cancela por si mismo
  v_por text;
  v_nota text := nullif(btrim(p_nota), '');
  v_aviso timestamptz;
  v_tiene boolean;
  v_vista record;
  v_nivel smallint;
  v_dias integer;
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
  v_dueno := r.id_cliente = v_uid;
  v_admin := public.es_administrador();
  if not v_dueno and not v_admin then
    if r.tipo = 'sala' and public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p_por is not null and p_por not in ('cliente', 'estudio') then
    raise exception 'por_invalido' using errcode = '22023';
  end if;
  v_directo := v_dueno and p_aviso_en is null and coalesce(p_por, 'cliente') = 'cliente';
  if not v_directo and not v_admin then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  v_por := case when v_directo then 'cliente' else coalesce(p_por, 'estudio') end;
  if r.estado not in ('pre_reservada', 'confirmada')
     or (r.inicio <= now() and not (r.tipo = 'asesoria' and v_por = 'estudio')) then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if char_length(v_nota) > 300 or v_nota ~ '[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]' then
    raise exception 'nota_invalida' using errcode = '22023';
  end if;
  if v_por = 'cliente' and not v_directo then
    perform public.validar_aviso(p_aviso_en, r.creada_en);
    v_aviso := p_aviso_en;
  else
    v_aviso := now();
  end if;
  v_tiene := public.tiene_pagos(r.id);
  if not v_directo and v_nota is null and (v_tiene or v_por = 'cliente' or r.tipo = 'asesoria') then
    raise exception 'nota_requerida' using errcode = 'P0001';
  end if;
  select * into v_vista from public.calcular_cancelacion(r.id, v_aviso);
  if v_directo and v_tiene and p_nivel_esperado is distinct from v_vista.nivel then
    raise exception 'nivel_cambiado' using errcode = 'P0001', detail = jsonb_build_object(
      'nivel', v_vista.nivel, 'anticipacion_horas', v_vista.anticipacion_horas, 'pagado', v_vista.pagado::text,
      'en_validacion', v_vista.en_validacion::text, 'retenido', v_vista.retenido::text, 'credito', v_vista.credito::text,
      'credito_vence', v_vista.credito_vence, 'puede_reprogramar', v_vista.puede_reprogramar,
      'reprogramaciones_restantes', v_vista.reprogramaciones_restantes)::text;
  end if;
  -- Por el estudio no hay nivel ni retencion: el cliente elige despues (CA-13).
  v_nivel := case when v_por = 'estudio' then null else v_vista.nivel end;
  update public.reserva
  set estado = 'cancelada', motivo_cancelacion = case when v_por = 'estudio' then 'administrador' else 'cliente' end,
      nota_cancelacion = v_nota, nivel_cancelacion = v_nivel, aviso_en = v_aviso, cancelacion_por = v_por,
      id_cancelador = v_uid, pagado_cancelacion = v_vista.pagado,
      retenido = case when v_por = 'estudio' then 0 else v_vista.retenido end,
      credito_generado = case when v_por = 'estudio' then 0 else v_vista.credito end,
      eleccion_estudio = case when v_por = 'estudio' and v_tiene then 'pendiente' end
  where id = r.id;
  if v_tiene then
    update public.cuota q set estado = 'anulada'
    where q.id_reserva = r.id and q.estado = 'pendiente'
      and not exists (select 1 from public.comprobante_pago p where p.id_cuota = q.id and p.estado = 'pendiente_validacion');
  end if;
  v_dias := (r.parametros_aplicados ->> 'dias_vigencia_credito')::int;
  if v_por = 'cliente' and v_vista.credito > 0 then
    v_devuelto := public.devolver_credito_aplicado(r.id, v_vista.credito);
    if v_vista.credito > v_devuelto then
      perform public.generar_credito(r.id_cliente, r.id, 'nivel_' || v_nivel, v_vista.credito - v_devuelto, v_dias);
    end if;
  end if;
  if v_directo then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_cliente', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre,
                              'inicio', r.inicio, 'fin', r.fin)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  elsif v_por = 'estudio' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_estudio', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'nota', v_nota)
           || coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
    from auth.users u where u.id = r.id_cliente;
  end if;
  if v_por = 'cliente' and v_tiene then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_con_pagos', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                              'nivel', v_nivel, 'pagado', v_vista.pagado, 'retenido', v_vista.retenido,
                              'credito', v_vista.credito, 'credito_vence', v_vista.credito_vence)
           || coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
    from auth.users u where u.id = r.id_cliente;
  end if;
  -- El profesional se entera de la cancelacion de una asesoria confirmada, pida quien la pida; nunca el dinero.
  if r.tipo = 'asesoria' and r.estado = 'confirmada' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'asesoria_cancelada_profesional', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                              'cliente', cl.nombre, 'por', v_por) || coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
    from auth.users u
    left join public.usuario cl on cl.id = r.id_cliente
    where u.id = r.id_profesional;
  end if;
end;
$$;

-- Reprogramar (parte de 20261217). Asesoria: el perfil del profesional se bloquea primero (como agendar y retirar un
-- horario, asi se serializan), el horario nuevo debe caber en un bloque suyo (`fuera_de_horario`), no lleva franja ni
-- margen, el solape lo detiene la exclusion por profesional (23P01) y la penalizacion de nivel 2 es una cuota `al_terminar`.
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
  v_prof uuid;
  v_margen interval;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select id_profesional into v_prof from public.reserva where id = p_id and tipo = 'asesoria';
  if v_prof is not null then
    perform 1 from public.perfil_profesional where id = v_prof for update;
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
  v_margen := case when r.tipo = 'asesoria' then interval '0' else interval '30 minutes' end;
  if r.tipo = 'asesoria' then
    if not exists (select 1 from public.horario_profesional h
                   where h.id_profesional = r.id_profesional and h.inicio <= p_nuevo_inicio and h.fin >= v_fin) then
      raise exception 'fuera_de_horario' using errcode = 'P0001';
    end if;
    perform public.caducar_reservas(null, p_nuevo_inicio, v_fin, r.id_profesional); -- como al insertar
  else
    perform public.caducar_reservas(r.id_sala, p_nuevo_inicio, v_fin + v_margen);
  end if;
  if v.estudio then
    -- Vuelve al estado de antes de cancelar: confirmada si el adelanto esta pagado, si no pre_reservada.
    v_estado := case when exists (select 1 from public.cuota q where q.id_reserva = r.id and q.hito = 'al_reservar'
                                  and q.estado = 'pagada') then 'confirmada' else 'pre_reservada' end;
    update public.reserva
    set estado = v_estado,
        motivo_cancelacion = null, inicio = p_nuevo_inicio, fin = v_fin, fin_buffer = v_fin + v_margen,
        id_franja = case when r.tipo = 'sala' then p_id_franja end, eleccion_estudio = 'reprogramada',
        vence_pago = case when v_estado = 'pre_reservada' then
          least(p_nuevo_inicio, greatest(
            p_nuevo_inicio - make_interval(days => (select valor from public.parametro where clave = 'dias_limite_pago')::int),
            now() + make_interval(hours => (r.parametros_aplicados ->> 'horas_limite_pago')::int)))
          else vence_pago end
    where id = r.id;
    update public.cuota set estado = 'pendiente' where id_reserva = r.id and estado = 'anulada';
  else
    update public.reserva
    set inicio = p_nuevo_inicio, fin = v_fin, fin_buffer = v_fin + v_margen,
        id_franja = case when r.tipo = 'sala' then p_id_franja end,
        precio = case when r.tipo = 'sala' then p_precio else precio end, total = v.total_nuevo
    where id = r.id;
    -- La cuota de saldo pasa a lo ya aplicado mas el saldo nuevo (0.00 si hay credito); el adelanto no cambia.
    update public.cuota q
    set monto = q.pagado + v.saldo, estado = case when v.saldo = 0 then 'pagada' else 'pendiente' end
    where q.id_reserva = r.id and q.hito = 'al_terminar';
    -- Una asesoria solo tiene el adelanto: la penalizacion de nivel 2 nace como su cuota `al_terminar`.
    if r.tipo = 'asesoria' and v.saldo > 0
       and not exists (select 1 from public.cuota q where q.id_reserva = r.id and q.hito = 'al_terminar') then
      insert into public.cuota (id_reserva, hito, monto) values (r.id, 'al_terminar', v.saldo);
    end if;
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
                            'saldo', v.saldo, 'credito', v.credito, 'sin_costo', v.estudio) || coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
  from auth.users u where u.id = r.id_cliente;
  -- El profesional se entera si la asesoria queda confirmada en el horario nuevo (sin dinero).
  if r.tipo = 'asesoria' and coalesce(v_estado, r.estado) = 'confirmada' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'asesoria_reprogramada_profesional', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', p_nuevo_inicio, 'fin', v_fin,
                              'anterior_inicio', r.inicio, 'cliente', cl.nombre) || coalesce(public.datos_asesoria_aviso(r.id), '{}'::jsonb)
    from auth.users u
    left join public.usuario cl on cl.id = r.id_cliente
    where u.id = r.id_profesional;
  end if;
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
