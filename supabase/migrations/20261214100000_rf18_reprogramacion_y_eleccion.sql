-- RF-18 (parte B, ADR-015): reprogramar con la politica de niveles (CA-08 a CA-10) y la eleccion del cliente tras una
-- cancelacion del estudio (CA-13). El precio nuevo lo calcula el motor del catalogo en el backend; aqui se calculan
-- el nivel, la penalizacion, el saldo y el credito, y se protege todo. Orden de bloqueo (como la parte A):
-- sala (advisory, backend) -> cuotas de la reserva -> reserva -> creditos.

-- 1. Avisos nuevos.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
   'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
   'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
   'devolucion_decidida', 'devolucion_realizada', 'reserva_reprogramada', 'eleccion_estudio_resuelta'));

-- 2. Apoyos puros o de lectura.
-- Final del dia habil `p_dias` despues (lunes a viernes, sin los feriados registrados), en Lima.
create function public.sumar_dias_habiles(p_desde timestamptz, p_dias integer)
returns timestamptz
language plpgsql
stable
set search_path = ''
as $$
declare
  v_dia date := (p_desde at time zone 'America/Lima')::date;
  v_cuenta integer := 0;
begin
  while v_cuenta < p_dias loop
    v_dia := v_dia + 1;
    if extract(isodow from v_dia) < 6 and not exists (select 1 from public.feriado where fecha = v_dia) then
      v_cuenta := v_cuenta + 1;
    end if;
  end loop;
  return ((v_dia + 1)::timestamp at time zone 'America/Lima') - interval '1 microsecond';
end;
$$;
revoke all on function public.sumar_dias_habiles(timestamptz, integer) from public, anon, authenticated;

-- Lo pagado que sigue siendo del cliente: lo aplicado a las cuotas menos lo que ya se retuvo como penalizacion de
-- nivel 2 al reprogramar y lo que ya paso a credito de reprogramacion (para no cobrarlo ni acreditarlo dos veces).
create function public.pagado_neto(p_id_reserva uuid)
returns numeric
language sql
stable
security definer
set search_path = ''
as $$
  select greatest(
    coalesce((select sum(c.pagado) from public.cuota c where c.id_reserva = p_id_reserva), 0)
    - coalesce((select sum(g.penalizacion) from public.reprogramacion g where g.id_reserva = p_id_reserva), 0)
    - coalesce((select sum(k.monto) from public.credito k where k.id_reserva = p_id_reserva and k.tipo = 'reprogramacion'), 0),
    0);
$$;
revoke all on function public.pagado_neto(uuid) from public, anon, authenticated;

-- Ocupacion sin una reserva: al reprogramar, el tramo puede solaparse con el propio horario.
create function public.ocupacion_sala_excluyendo(p_id_sala uuid, p_desde timestamptz, p_hasta timestamptz, p_excluir uuid)
returns table (inicio timestamptz, fin_buffer timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin_buffer
  from public.reserva r
  where r.id_sala = p_id_sala
    and r.id <> p_excluir
    and r.estado <> 'cancelada'
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_pagos(r.id))
    and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;
revoke all on function public.ocupacion_sala_excluyendo(uuid, timestamptz, timestamptz, uuid) from public, anon;
grant execute on function public.ocupacion_sala_excluyendo(uuid, timestamptz, timestamptz, uuid) to authenticated;

-- La parte A cancela y marca la inasistencia con lo pagado; ahora con el pagado neto (identico sin reprogramaciones).
create or replace function public.calcular_cancelacion(p_id_reserva uuid, p_aviso timestamptz)
returns table (nivel smallint, anticipacion_horas numeric, pagado numeric, en_validacion numeric, retenido numeric,
               credito numeric, credito_vence timestamptz, puede_reprogramar boolean, reprogramaciones_restantes integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_hechas integer;
  v_hechas_2 integer;
begin
  select * into r from public.reserva where id = p_id_reserva;
  pagado := public.pagado_neto(r.id);
  en_validacion := coalesce((select sum(p.monto) from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                             where c.id_reserva = r.id and p.estado = 'pendiente_validacion'), 0);
  anticipacion_horas := round(extract(epoch from (r.inicio - p_aviso)) / 3600, 2);
  if public.tiene_pagos(r.id) then
    nivel := public.nivel_cancelacion(r.inicio, p_aviso, r.parametros_aplicados);
    retenido := case nivel when 1 then 0 when 2 then least(pagado, public.penalizacion_nivel_2(r.total, r.parametros_aplicados))
                else pagado end;
  else
    nivel := null;
    retenido := 0;
  end if;
  credito := pagado - retenido;
  credito_vence := case when credito > 0
    then public.fin_de_dia_lima(now(), (r.parametros_aplicados ->> 'dias_vigencia_credito')::int) end;
  select count(*) filter (where g.nivel is not null), count(*) filter (where g.nivel = 2) into v_hechas, v_hechas_2
    from public.reprogramacion g where g.id_reserva = r.id;
  reprogramaciones_restantes := case
    when r.estado <> 'confirmada' or nivel is null or nivel = 3 then 0
    when nivel = 1 then greatest((r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int - v_hechas, 0)
    else greatest(least((r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int - v_hechas,
                        (r.parametros_aplicados ->> 'reprogramaciones_nivel_2')::int - v_hechas_2), 0)
  end;
  puede_reprogramar := reprogramaciones_restantes > 0;
  return next;
end;
$$;

create or replace function public.aplicar_inasistencia(p_id uuid, p_id_autor uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_pagado numeric;
begin
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found or r.estado not in ('pre_reservada', 'confirmada', 'en_curso') then
    return;
  end if;
  v_pagado := public.pagado_neto(r.id);
  update public.reserva
  set estado = 'no_asistio', aviso_en = now(), cancelacion_por = 'inasistencia', nivel_cancelacion = null,
      id_cancelador = p_id_autor, pagado_cancelacion = v_pagado, retenido = v_pagado, credito_generado = 0
  where id = r.id;
  update public.cuota q set estado = 'anulada'
  where q.id_reserva = r.id and q.estado = 'pendiente'
    and not exists (select 1 from public.comprobante_pago p where p.id_cuota = q.id and p.estado = 'pendiente_validacion');
  insert into public.notificacion (tipo, destinatario, datos)
  select 'inasistencia_marcada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'retenido', v_pagado)
  from auth.users u where u.id = r.id_cliente;
end;
$$;

-- 3. Quien puede reprogramar y si la reserva se deja: el dueno siempre; el administrador solo cuando la reserva espera
-- la eleccion tras una cancelacion del estudio. P0002 si no es suya (404), 42501 al personal y al administrador fuera de
-- ese caso, P0001 reprogramacion_no_permitida o limite_reprogramaciones.
create function public.exigir_reprogramable(r public.reserva)
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
revoke all on function public.exigir_reprogramable(public.reserva) from public, anon, authenticated;

-- Lo que el backend necesita para validar el horario nuevo y cotizar: la misma sala, servicio, duracion y especialistas.
create function public.contexto_reprogramacion(p_id uuid)
returns table (id_sala uuid, id_servicio uuid, inicio timestamptz, fin timestamptz, estudio boolean, precio jsonb,
               total numeric, id_especialistas uuid[], parametros_aplicados jsonb)
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
              where re.id_reserva = r.id), '{}'::uuid[]), r.parametros_aplicados;
end;
$$;
revoke all on function public.contexto_reprogramacion(uuid) from public, anon;
grant execute on function public.contexto_reprogramacion(uuid) to authenticated;

-- 4. Calculo comun de la vista previa y de la reprogramacion (CA-09, CA-10). Tras una cancelacion del estudio no hay
-- nivel ni penalizacion y el precio es el de la reserva (se ignora `p_total_nuevo`); no cuenta para los limites.
create function public.calcular_reprogramacion(p_id uuid, p_nuevo_inicio timestamptz, p_total_nuevo numeric)
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
  if not estudio and (p_total_nuevo is null or p_total_nuevo < 0) then
    raise exception 'total_invalido' using errcode = '22023';
  end if;
  v_pagado := public.pagado_neto(r.id);
  total_nuevo := case when estudio then r.total else p_total_nuevo end;
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
revoke all on function public.calcular_reprogramacion(uuid, timestamptz, numeric) from public, anon, authenticated;

create function public.vista_reprogramacion(p_id uuid, p_nuevo_inicio timestamptz, p_total_nuevo numeric)
returns table (nivel smallint, penalizacion numeric, saldo numeric, credito numeric, reprogramaciones_restantes integer)
language sql
stable
security definer
set search_path = ''
as $$
  select c.nivel, c.penalizacion, c.saldo, c.credito, c.reprogramaciones_restantes
  from public.calcular_reprogramacion(p_id, p_nuevo_inicio, p_total_nuevo) c;
$$;
revoke all on function public.vista_reprogramacion(uuid, timestamptz, numeric) from public, anon;
grant execute on function public.vista_reprogramacion(uuid, timestamptz, numeric) to authenticated;

-- 5. Reprogramar. El backend valida franja, anticipacion, cierres y tramo libre, y pasa el precio recalculado; aqui se
-- comprueban nivel y total esperados, se mueve la reserva y se ajustan cuotas, credito, historial y avisos. Un tramo
-- ocupado lo detiene la exclusion de `reserva` (23P01).
create function public.reprogramar_reserva(
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
    update public.reserva
    set estado = case when exists (select 1 from public.cuota q where q.id_reserva = r.id and q.hito = 'al_reservar'
                                   and q.estado = 'pagada') then 'confirmada' else 'pre_reservada' end,
        motivo_cancelacion = null, inicio = p_nuevo_inicio, fin = v_fin, fin_buffer = v_fin + interval '30 minutes',
        id_franja = p_id_franja, eleccion_estudio = 'reprogramada'
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
      perform public.generar_credito(r.id_cliente, r.id, 'reprogramacion', v.credito,
        (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
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
revoke all on function public.reprogramar_reserva(uuid, timestamptz, integer, numeric, uuid, jsonb, numeric, jsonb) from public, anon;
grant execute on function public.reprogramar_reserva(uuid, timestamptz, integer, numeric, uuid, jsonb, numeric, jsonb) to authenticated;

-- 6. Eleccion tras una cancelacion del estudio: la devolucion integra de lo pagado (CA-13). Se registra aprobada y total,
-- con plazo de 7 dias habiles; el administrador la marca realizada como cualquier otra. Una sola vez.
create function public.elegir_estudio_devolucion(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  r public.reserva%rowtype;
  v_pagado numeric;
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
  v_limite := public.sumar_dias_habiles(now(), 7);
  insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado, estado, monto_aprobado, decidida_en, limite)
  values (r.id, r.id_cliente, 'estudio', 'Devolución íntegra por cancelación del estudio', v_pagado, 'aprobada', v_pagado,
          now(), v_limite);
  update public.reserva set eleccion_estudio = 'devolucion' where id = r.id;
  if v_uid = r.id_cliente then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'eleccion_estudio_resuelta', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre, 'opcion', 'devolucion',
                              'monto', v_pagado, 'limite', v_limite)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  end if;
end;
$$;
revoke all on function public.elegir_estudio_devolucion(uuid) from public, anon;
grant execute on function public.elegir_estudio_devolucion(uuid) to authenticated;
