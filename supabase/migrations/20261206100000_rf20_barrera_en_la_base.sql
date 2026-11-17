-- RF-20 (correccion de la auditoria A): la barrera de los campos sensibles vive tambien en la base.
-- Un administrador con sus claims ya no puede cambiar por SQL un campo sensible ni inventar una confirmacion o una
-- fila del registro: esas escrituras pasan por funciones security definer (solo Administrador) que el backend llama
-- dentro del flujo de vista previa y confirmacion.

-- 1. Privilegios: se quita el update directo de los campos sensibles (los demas siguen como hoy).
revoke update on public.configuracion_impuestos from authenticated;
revoke update on public.recargo from authenticated;
revoke update on public.parametro from authenticated;
revoke update on public.servicio from authenticated;
grant update (nombre, categoria, ocupa_sala, activo) on public.servicio to authenticated;
revoke update on public.especialista from authenticated;
grant update (nombre, activo) on public.especialista to authenticated;

-- La confirmacion ya no se inserta directo: la crea crear_confirmacion.
drop policy confirmacion_cambio_propia_alta on public.confirmacion_cambio;
revoke insert on public.confirmacion_cambio from authenticated;

-- registrar_cambios dejaba escribir el registro con una confirmacion inventada: lo reemplaza aplicar_cambio_confirmado.
drop function public.registrar_cambios(uuid);

-- 2. Parametros sensibles (ADR-015): todos menos los de anticipacion.
create function public.es_parametro_sensible(p_clave text)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select p_clave in ('dias_limite_pago', 'horas_limite_pago', 'porcentaje_adelanto', 'horas_nivel_1', 'horas_nivel_2',
    'porcentaje_penalizacion_nivel_2', 'minutos_tolerancia_inasistencia', 'dias_vigencia_credito',
    'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2');
$$;
revoke all on function public.es_parametro_sensible(text) from public, anon, authenticated;

-- Escritura de un parametro sin barrera: solo los no sensibles, o uno sensible con su mismo valor (no-op).
create function public.actualizar_parametro(p_clave text, p_valor integer)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  if public.es_parametro_sensible(p_clave)
     and p_valor is distinct from (select valor from public.parametro where clave = p_clave) then
    raise exception 'Un parametro sensible solo cambia con vista previa y confirmacion.' using errcode = '42501';
  end if;
  update public.parametro set valor = p_valor where clave = p_clave and valor <> p_valor;
end;
$$;

-- 3. Confirmacion: lo que el administrador vio en la vista previa (el token llega ya hasheado).
create function public.crear_confirmacion(
  p_hash text, p_recurso text, p_id_recurso uuid, p_nombre text, p_cambios jsonb, p_minutos integer
)
returns timestamptz
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_expira timestamptz;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  if p_minutos not between 1 and 60 then
    raise exception 'Vigencia invalida.' using errcode = '22023';
  end if;
  insert into public.confirmacion_cambio (hash_token, id_autor, recurso, id_recurso, nombre_recurso, cambios, expira_en)
    values (p_hash, auth.uid(), p_recurso, p_id_recurso, p_nombre, p_cambios, now() + make_interval(mins => p_minutos))
    returning expira_en into v_expira;
  return v_expira;
end;
$$;

-- Bloquea la fila del recurso sensible (el backend ya no tiene `for update` directo sobre estas tablas).
create function public.bloquear_recurso_sensible(p_recurso text, p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  if p_recurso = 'impuestos' then
    perform 1 from public.configuracion_impuestos for update;
  elsif p_recurso = 'servicio' then
    perform 1 from public.servicio where id = p_id for update;
  elsif p_recurso = 'especialista' then
    perform 1 from public.especialista where id = p_id for update;
  elsif p_recurso = 'recargos' then
    perform 1 from public.recargo order by tipo for update;
  elsif p_recurso = 'parametros' then
    perform 1 from public.parametro order by clave for update;
  else
    raise exception 'Recurso desconocido.' using errcode = '22023';
  end if;
end;
$$;

-- Unica via de escritura de los campos sensibles y del registro: consume la confirmacion propia (un solo uso,
-- vigente), comprueba que el `anterior` de cada campo sea el valor real, lo aplica y deja una fila por campo.
create function public.aplicar_cambio_confirmado(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.confirmacion_cambio%rowtype;
  c record;
  v_tabla text;
  v_col text;
  v_donde text;
  v_tipo text;
  v_leer text;
  v_real text;
  v_nuevo text;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  update public.confirmacion_cambio set usada_en = now()
    where id = p_id and id_autor = auth.uid() and usada_en is null and expira_en > now()
    returning * into v;
  if not found then
    raise exception 'Confirmacion no valida.' using errcode = '55000';
  end if;
  for c in select key, value from jsonb_each(v.cambios) loop
    if v.recurso = 'impuestos' and c.key in ('porcentaje_igv', 'precios_incluyen_igv') then
      v_tabla := 'configuracion_impuestos'; v_col := c.key; v_donde := 'true';
    elsif v.recurso = 'servicio' and c.key in ('tarifa_hora', 'monto_fijo') and v.id_recurso is not null then
      v_tabla := 'servicio'; v_col := c.key; v_donde := format('id = %L', v.id_recurso);
    elsif v.recurso = 'especialista' and c.key in ('monto_fijo', 'monto_variable', 'unidad') and v.id_recurso is not null then
      v_tabla := 'especialista'; v_col := c.key; v_donde := format('id = %L', v.id_recurso);
    elsif v.recurso = 'recargos' and c.key in ('noche.porcentaje', 'noche.desde', 'noche.hasta',
        'fin_de_semana.porcentaje', 'feriado.porcentaje') then
      v_tabla := 'recargo'; v_col := split_part(c.key, '.', 2); v_donde := format('tipo = %L', split_part(c.key, '.', 1));
    elsif v.recurso = 'parametros' and public.es_parametro_sensible(c.key) then
      v_tabla := 'parametro'; v_col := 'valor'; v_donde := format('clave = %L', c.key);
    else
      raise exception 'Campo no aplicable: %.', c.key using errcode = '22023';
    end if;
    v_tipo := case
      when v_col in ('porcentaje_igv', 'tarifa_hora', 'monto_fijo', 'monto_variable', 'porcentaje') then 'numeric'
      when v_col = 'precios_incluyen_igv' then 'boolean'
      when v_col in ('desde', 'hasta') then 'time'
      when v_col = 'valor' then 'integer'
      else 'text' end;
    -- Mismo texto canonico que el backend: decimales con 2 cifras, horas HH:MM, booleanos true/false.
    v_leer := case v_tipo
      when 'numeric' then format('to_char(%I, ''FM999999990.00'')', v_col)
      when 'time' then format('to_char(%I, ''HH24:MI'')', v_col)
      else format('%I::text', v_col) end;
    execute format('select %s from public.%I where %s for update', v_leer, v_tabla, v_donde) into v_real;
    if not found then
      raise exception 'El recurso ya no existe.' using errcode = 'P0002';
    end if;
    if v_real is distinct from c.value ->> 'anterior' then
      raise exception 'El valor cambio desde la vista previa.' using errcode = '40001';
    end if;
    execute format('update public.%I set %I = $1::%s where %s', v_tabla, v_col, v_tipo, v_donde)
      using c.value ->> 'nuevo';
    execute format('select %s from public.%I where %s', v_leer, v_tabla, v_donde) into v_nuevo;
    insert into public.registro_cambio (id_autor, autor_nombre, recurso, id_recurso, nombre_recurso, campo, anterior, nuevo)
      values (v.id_autor,
              coalesce((select nullif(u.nombre, '') from public.usuario u where u.id = v.id_autor), 'Administrador'),
              v.recurso, v.id_recurso, v.nombre_recurso, c.key, v_real, v_nuevo);
  end loop;
end;
$$;

revoke all on function public.actualizar_parametro(text, integer) from public, anon;
revoke all on function public.crear_confirmacion(text, text, uuid, text, jsonb, integer) from public, anon;
revoke all on function public.bloquear_recurso_sensible(text, uuid) from public, anon;
revoke all on function public.aplicar_cambio_confirmado(uuid) from public, anon;
grant execute on function public.actualizar_parametro(text, integer) to authenticated;
grant execute on function public.crear_confirmacion(text, text, uuid, text, jsonb, integer) to authenticated;
grant execute on function public.bloquear_recurso_sensible(text, uuid) to authenticated;
grant execute on function public.aplicar_cambio_confirmado(uuid) to authenticated;
