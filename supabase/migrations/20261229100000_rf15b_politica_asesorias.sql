-- RF-15 etapa B (backend B2): la politica de RF-18 para asesorias (CA-10, CA-11), las barreras de lectura del profesional
-- (CA-16), 409 horario_con_asesorias y profesional_con_asesorias. Cada funcion parte de su ULTIMA definicion vigente:
--   cancelar_reserva 20261215, vista_cancelacion 20261213, marcar_inasistencia 20261213, exigir_reprogramable 20261216,
--   contexto_reprogramacion y calcular_reprogramacion 20261214, reprogramar_reserva 20261217,
--   elegir_estudio_devolucion 20261216, aplicar_credito 20261224, validar_pago_nuevo y solicitar_devolucion 20261213,
--   retirar_horario 20261223, asignar_rol 20261225, ocupacion_profesional 20261228100000.
-- La sala no cambia: toda rama nueva pregunta por `tipo`.

-- 1. El profesional no lee `reserva` por SQL: sus asesorias le llegan por una vista que no trae el dinero ni la
-- cancelacion (CA-16). Antes lo veia por la politica `reserva_lee` (B1); ahora solo el cliente, el personal (sala) y el
-- administrador. `asesoria` (1:1) cuelga de esa visibilidad, asi que tampoco la lee directo.
drop policy reserva_lee on public.reserva;
create policy reserva_lee on public.reserva for select to authenticated using (
  id_cliente = (select auth.uid())
  or (public.es_personal() and (tipo = 'sala' or public.es_administrador()))
);

-- La vista corre con los permisos de su duena (sin RLS) y filtra ella misma: el cliente, su profesional y el administrador.
-- Para el profesional van nulos `total`, `detalle`, la cancelacion y sus montos; quedan el precio publicado (lo ve en el
-- directorio) y la politica guardada, que la API ya le muestra.
create view public.asesoria_vista as
select r.id, r.folio, r.estado, r.motivo_cancelacion, r.inicio, r.fin, r.vence_pago, r.id_cliente, r.id_profesional,
       r.creada_en, r.precio, r.parametros_aplicados, r.eleccion_estudio,
       a.modalidad, a.lugar, a.enlace, a.realizada_en,
       d.dinero as con_dinero,
       case when d.dinero then r.total end as total,
       case when d.dinero then r.detalle end as detalle,
       case when d.dinero then r.nota_cancelacion end as nota_cancelacion,
       case when d.dinero then r.nivel_cancelacion end as nivel_cancelacion,
       case when d.dinero then r.aviso_en end as aviso_en,
       case when d.dinero then r.cancelacion_por end as cancelacion_por,
       case when d.dinero then r.id_cancelador end as id_cancelador,
       case when d.dinero then r.pagado_cancelacion end as pagado_cancelacion,
       case when d.dinero then r.retenido end as retenido,
       case when d.dinero then r.credito_generado end as credito_generado,
       case when d.dinero then r.excepcion_motivo end as excepcion_motivo,
       case when d.dinero then r.excepcion_por end as excepcion_por,
       case when d.dinero then r.excepcion_en end as excepcion_en
from public.reserva r
join public.asesoria a on a.id_reserva = r.id
cross join lateral (select r.id_cliente = (select auth.uid()) or public.es_administrador() as dinero) d
where r.tipo = 'asesoria'
  and (d.dinero or r.id_profesional = (select auth.uid()));
revoke all on public.asesoria_vista from public, anon, authenticated;
grant select on public.asesoria_vista to authenticated;

-- El tipo de una reserva visible para quien llama (cliente, su profesional, el administrador; el personal solo la
-- de sala): las rutas de RF-18 deciden con ella entre la sala y la asesoria. Otro caso: null.
create function public.tipo_de_reserva(p_id uuid)
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select r.tipo from public.reserva r
  where r.id = p_id and (select auth.uid()) is not null
    and (r.id_cliente = (select auth.uid()) or r.id_profesional = (select auth.uid()) or public.es_administrador()
         or (r.tipo = 'sala' and public.es_personal()));
$$;
revoke all on function public.tipo_de_reserva(uuid) from public, anon;
grant execute on function public.tipo_de_reserva(uuid) to authenticated;

-- 2. Cancelar (parte de 20261215): el personal no ve asesorias (404); el estudio cancela una asesoria tambien tras su
-- inicio mientras no este cerrada (CA-11); el cliente, solo hasta el inicio.
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
  if not v_directo and v_nota is null and (v_tiene or v_por = 'cliente') then
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
    from auth.users u where u.id = r.id_cliente;
  end if;
  if v_por = 'cliente' and v_tiene then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_con_pagos', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                              'nivel', v_nivel, 'pagado', v_vista.pagado, 'retenido', v_vista.retenido,
                              'credito', v_vista.credito, 'credito_vence', v_vista.credito_vence)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;

-- Vista previa de cancelar (parte de 20261213): el personal no ve asesorias.
create or replace function public.vista_cancelacion(p_id uuid, p_aviso_en timestamptz default null)
returns table (nivel smallint, anticipacion_horas numeric, pagado numeric, en_validacion numeric, retenido numeric,
               credito numeric, credito_vence timestamptz, puede_reprogramar boolean, reprogramaciones_restantes integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_admin boolean;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into r from public.reserva where id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_admin := public.es_administrador();
  if r.id_cliente <> v_uid and not v_admin then
    if r.tipo = 'sala' and public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p_aviso_en is not null and not v_admin then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada') or r.inicio <= now() then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if p_aviso_en is not null then
    perform public.validar_aviso(p_aviso_en, r.creada_en);
  end if;
  return query select * from public.calcular_cancelacion(r.id, coalesce(p_aviso_en, now()));
end;
$$;

-- 3. Inasistencia (parte de 20261213). Sala: el personal, desde inicio + tolerancia hasta el fin. Asesoria: su
-- profesional o el administrador (no el personal), desde inicio + tolerancia y sin limite posterior (CA-12). Lo ajeno
-- no existe (404); su cliente recibe 403.
create or replace function public.marcar_inasistencia(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_existe boolean;
  v_tolerancia integer;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into r from public.reserva where id = p_id;
  v_existe := found;
  if v_existe and r.tipo = 'asesoria' then
    if not (r.id_profesional = v_uid or public.es_administrador()) then
      if r.id_cliente = v_uid then
        raise exception 'sin_permiso' using errcode = '42501';
      end if;
      raise exception 'no_encontrada' using errcode = 'P0002';
    end if;
  elsif not public.es_personal() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada', 'en_curso') then
    raise exception 'no_aplicable' using errcode = 'P0001';
  end if;
  v_tolerancia := (r.parametros_aplicados ->> 'minutos_tolerancia_inasistencia')::int;
  if r.tipo = 'asesoria' then
    if now() < r.inicio + make_interval(mins => v_tolerancia) then
      raise exception 'tolerancia_no_cumplida' using errcode = 'P0001';
    end if;
  else
    case public.ventana_inasistencia(r.inicio, r.fin, v_tolerancia, now())
      when 'antes' then raise exception 'tolerancia_no_cumplida' using errcode = 'P0001';
      when 'despues' then raise exception 'no_aplicable' using errcode = 'P0001';
      else null;
    end case;
  end if;
  perform public.aplicar_inasistencia(r.id, v_uid);
end;
$$;

-- 4. Reprogramar. Quien puede (parte de 20261216): el personal no ve asesorias.
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
    if r.tipo = 'sala' and public.es_personal() then
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

-- Lo que el backend necesita para validar el horario nuevo y cotizar (parte de 20261214): suma el tipo y el profesional.
drop function public.contexto_reprogramacion(uuid);
create function public.contexto_reprogramacion(p_id uuid)
returns table (id_sala uuid, id_servicio uuid, inicio timestamptz, fin timestamptz, estudio boolean, precio jsonb,
               total numeric, id_especialistas uuid[], parametros_aplicados jsonb, tipo text, id_profesional uuid)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  e record;
begin
  select * into r from public.reserva x where x.id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into e from public.exigir_reprogramable(r);
  return query select r.id_sala, r.id_servicio, r.inicio, r.fin, e.e_estudio, r.precio, r.total,
    coalesce((select array_agg(re.id_especialista order by re.id_especialista) from public.reserva_especialista re
              where re.id_reserva = r.id), '{}'::uuid[]), r.parametros_aplicados, r.tipo, r.id_profesional;
end;
$$;
revoke all on function public.contexto_reprogramacion(uuid) from public, anon;
grant execute on function public.contexto_reprogramacion(uuid) to authenticated;

-- Calculo comun (parte de 20261214): una asesoria conserva siempre su precio agendado (decision 3), venga lo que venga.
create or replace function public.calcular_reprogramacion(p_id uuid, p_nuevo_inicio timestamptz, p_total_nuevo numeric)
returns table (estudio boolean, nivel smallint, penalizacion numeric, total_nuevo numeric, saldo numeric, credito numeric,
               reprogramaciones_restantes integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  e record;
  v_pagado numeric;
  v_limite_1 integer;
  v_limite_2 integer;
begin
  select * into r from public.reserva x where x.id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into e from public.exigir_reprogramable(r);
  if p_nuevo_inicio is null or p_nuevo_inicio <= now() or p_nuevo_inicio = r.inicio then
    raise exception 'inicio_invalido' using errcode = '22023';
  end if;
  estudio := e.e_estudio;
  nivel := e.e_nivel;
  if not estudio and r.tipo = 'sala' and (p_total_nuevo is null or p_total_nuevo < 0) then
    raise exception 'total_invalido' using errcode = '22023';
  end if;
  v_pagado := public.pagado_neto(r.id);
  total_nuevo := case when estudio or r.tipo = 'asesoria' then r.total else p_total_nuevo end;
  penalizacion := case when nivel = 2 then public.penalizacion_nivel_2(r.total, r.parametros_aplicados) else 0 end;
  saldo := greatest(total_nuevo + penalizacion - v_pagado, 0);
  credito := greatest(v_pagado - total_nuevo - penalizacion, 0);
  v_limite_1 := (r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int;
  v_limite_2 := (r.parametros_aplicados ->> 'reprogramaciones_nivel_2')::int;
  reprogramaciones_restantes := case
    when estudio then greatest(v_limite_1 - e.e_hechas, 0)
    when nivel = 1 then greatest(v_limite_1 - (e.e_hechas + 1), 0)
    else greatest(least(v_limite_1 - (e.e_hechas + 1), v_limite_2 - (e.e_hechas_2 + 1)), 0)
  end;
  return next;
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

-- 5. Eleccion tras la cancelacion del estudio (parte de 20261216): el personal no ve asesorias.
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
    if r.tipo = 'sala' and public.es_personal() then
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

-- 6. Pagar la penalizacion de una asesoria: la cuota `al_terminar` se paga hasta 48 h despues del fin, tambien con la
-- asesoria `realizada` (captura, parte de 20261213, y credito, parte de 20261224). Un credito sirve en sala o asesoria.
create or replace function public.validar_pago_nuevo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  c public.cuota%rowtype;
  r public.reserva%rowtype;
begin
  select * into c from public.cuota where id = new.id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente is distinct from (select auth.uid()) or new.id_cliente <> r.id_cliente then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'pago_en_validacion' using errcode = 'P0001';
  end if;
  if c.estado = 'anulada' or r.estado in ('cancelada', 'no_asistio') or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada', 'realizada'))
     or (c.hito = 'al_terminar' and r.tipo = 'asesoria' and now() > r.fin + interval '48 hours') then
    raise exception 'cuota_no_pagable' using errcode = 'P0001';
  end if;
  if c.pagado > 0 and new.monto <> c.monto - c.pagado then
    raise exception 'monto_invalido' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.instruccion_pago where metodo = new.metodo and activo) then
    raise exception 'metodo_no_disponible' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago
             where metodo = new.metodo and estado <> 'rechazado'
               and lower(btrim(numero_operacion)) = lower(btrim(new.numero_operacion))) then
    raise exception 'operacion_duplicada' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

create or replace function public.aplicar_credito(p_id_cuota uuid, p_monto numeric, p_id_credito uuid default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  k record;
  v_resto numeric;
  v_toma numeric;
begin
  if v_uid is null or public.es_profesional() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into c from public.cuota where id = p_id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente <> v_uid then
    if r.tipo = 'sala' and public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if c.estado = 'anulada' or r.estado in ('cancelada', 'no_asistio') or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada', 'realizada'))
     or (c.hito = 'al_terminar' and r.tipo = 'asesoria' and now() > r.fin + interval '48 hours')
     or exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'no_pagable' using errcode = 'P0001';
  end if;
  if p_monto is null or p_monto <= 0 or p_monto <> round(p_monto, 2) or p_monto > c.monto - c.pagado then
    raise exception 'monto_invalido' using errcode = '22023';
  end if;
  if p_id_credito is not null
     and not exists (select 1 from public.credito where id = p_id_credito and id_cliente = v_uid) then
    raise exception 'credito_no_encontrado' using errcode = 'P0002';
  end if;
  v_resto := p_monto;
  for k in
    select * from public.credito cr
    where cr.id_cliente = v_uid and cr.estado = 'vigente' and cr.saldo > 0 and cr.vence > now() and not cr.congelado
      and (p_id_credito is null or cr.id = p_id_credito)
    order by cr.vence, cr.id
    for update
  loop
    v_toma := least(k.saldo, v_resto);
    update public.credito
    set saldo = saldo - v_toma, estado = case when saldo - v_toma = 0 then 'agotado' else estado end
    where id = k.id;
    insert into public.aplicacion_credito (id_credito, id_cuota, monto, id_usuario) values (k.id, c.id, v_toma, v_uid);
    v_resto := v_resto - v_toma;
    exit when v_resto = 0;
  end loop;
  if v_resto > 0 then
    raise exception 'credito_insuficiente' using errcode = 'P0001';
  end if;
  update public.cuota
  set pagado = pagado + p_monto, estado = case when pagado + p_monto >= monto then 'pagada' else estado end
  where id = c.id;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' and c.pagado + p_monto >= c.monto then
    update public.reserva set estado = 'confirmada' where id = r.id;
    insert into public.notificacion (tipo, destinatario, datos)
    select 'pago_aprobado', u.email,
           jsonb_build_object('id_pago', null, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                              'monto', p_monto, 'reserva_confirmada', true)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;

-- 7. Sin devolucion en dinero (ADR-015): un credito de nivel 1 o de excepcion nacido de una asesoria no se devuelve
-- (parte de 20261213). La devolucion integra de la cancelacion del estudio si existe.
create or replace function public.solicitar_devolucion(p_id_credito uuid, p_motivo text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
  k public.credito%rowtype;
  v_id uuid;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 10 and 500 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  select * into k from public.credito where id = p_id_credito for update;
  if not found or k.id_cliente <> v_uid then
    if found and public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if k.tipo in ('nivel_2', 'reprogramacion')
     or exists (select 1 from public.reserva o where o.id = k.id_reserva and o.tipo = 'asesoria') then
    raise exception 'devolucion_no_permitida' using errcode = 'P0001';
  end if;
  if k.congelado then
    raise exception 'devolucion_pendiente' using errcode = 'P0001';
  end if;
  if k.estado <> 'vigente' or k.vence <= now() or k.saldo <= 0 then
    raise exception 'credito_no_vigente' using errcode = 'P0001';
  end if;
  insert into public.devolucion (id_credito, id_reserva, id_cliente, tipo, motivo, monto_solicitado)
  values (k.id, k.id_reserva, v_uid, 'nivel_1', v_motivo, k.saldo)
  returning id into v_id;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'devolucion_solicitada', au.email,
         jsonb_build_object('id_devolucion', v_id, 'id_credito', k.id, 'cliente', cl.nombre, 'saldo', k.saldo,
                            'motivo', v_motivo, 'folio_origen', (select folio from public.reserva where id = k.id_reserva))
  from public.usuario a
  join auth.users au on au.id = a.id
  left join public.usuario cl on cl.id = v_uid
  where a.rol = 'administrador';
  return v_id;
end;
$$;

-- 8. Asesorias vivas de un profesional: pre_reservada o confirmada, sin contar la pre-reservada vencida sin capturas
-- (la caducara el cron; su horario ya esta libre). Lista `{id, folio, inicio}` o null. Interna.
create function public.asesorias_vivas(p_id_profesional uuid, p_desde timestamptz, p_hasta timestamptz)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_agg(jsonb_build_object('id', x.id, 'folio', x.folio, 'inicio', x.inicio) order by x.inicio, x.id)
  from (
    select r.id, r.folio, r.inicio from public.reserva r
    where r.tipo = 'asesoria' and r.id_profesional = p_id_profesional and r.estado in ('pre_reservada', 'confirmada')
      and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_capturas(r.id))
      and (p_desde is null or tstzrange(r.inicio, r.fin) && tstzrange(p_desde, p_hasta))
    order by r.inicio, r.id
    limit 50
  ) x;
$$;
revoke all on function public.asesorias_vivas(uuid, timestamptz, timestamptz) from public, anon, authenticated;

-- 409 horario_con_asesorias (parte de 20261223): se comprueba tras bloquear el perfil, igual que el agendamiento.
create or replace function public.retirar_horario(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_perfil uuid;
  v_h public.horario_profesional%rowtype;
  v_vivas jsonb;
begin
  select id_profesional into v_perfil from public.horario_profesional where id = p_id;
  if not found then
    raise exception 'el horario no existe' using errcode = 'P0002';
  end if;
  if not public.gestiona_perfil(v_perfil) then
    raise exception 'sin permiso sobre este horario' using errcode = '42501';
  end if;
  perform 1 from public.perfil_profesional where id = v_perfil for update;
  select * into v_h from public.horario_profesional where id = p_id;
  if not found then
    raise exception 'el horario no existe' using errcode = 'P0002';
  end if;
  -- Solo cuenta lo que falta por dar: retirar un tramo pasado no cambia ninguna cita pendiente.
  if v_h.fin > now() then
    v_vivas := public.asesorias_vivas(v_perfil, greatest(v_h.inicio, now()), v_h.fin);
    if v_vivas is not null then
      raise exception 'horario_con_asesorias' using errcode = 'BG005', detail = v_vivas::text;
    end if;
  end if;
  delete from public.horario_profesional where id = p_id;
  if not found then
    raise exception 'el horario no existe' using errcode = 'P0002';
  end if;
end;
$$;

-- 409 profesional_con_asesorias (parte de 20261225): quien deja de ser profesional o administrador con asesorias
-- vivas no cambia de rol. El perfil se bloquea antes de contar: un agendamiento a la vez espera aqui.
create or replace function public.asignar_rol(id_usuario uuid, rol text, especialidad text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_rol text;
  v_operaciones jsonb;
  v_vivas jsonb;
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
  if v_rol in ('profesional', 'administrador') and asignar_rol.rol not in ('profesional', 'administrador') then
    perform 1 from public.perfil_profesional where id = id_usuario for update;
    v_vivas := public.asesorias_vivas(id_usuario, null, null);
    if v_vivas is not null then
      raise exception 'profesional_con_asesorias' using errcode = 'BG004', detail = v_vivas::text;
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

-- 9. Disponibilidad con `excluir_asesoria` (reprogramar: el tramo propio no cuenta como ocupado). Misma funcion de
-- 20261228100000 con un cuarto parametro opcional.
drop function public.ocupacion_profesional(uuid, timestamptz, timestamptz);
create function public.ocupacion_profesional(
  p_id uuid, p_desde timestamptz, p_hasta timestamptz, p_excluir uuid default null)
returns table (inicio timestamptz, fin timestamptz, propia boolean)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin, coalesce(r.id_cliente = (select auth.uid()), false)
  from public.reserva r
  where r.id_profesional = p_id and public.puede_ver_perfil(p_id)
    and r.estado <> 'cancelada'
    and (p_excluir is null or r.id <> p_excluir)
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_capturas(r.id))
    and tstzrange(r.inicio, r.fin) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;
revoke all on function public.ocupacion_profesional(uuid, timestamptz, timestamptz, uuid) from public;
grant execute on function public.ocupacion_profesional(uuid, timestamptz, timestamptz, uuid) to anon, authenticated;
