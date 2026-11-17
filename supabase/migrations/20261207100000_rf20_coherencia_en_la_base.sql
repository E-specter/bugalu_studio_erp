-- RF-20 (auditoria A, ronda 2): la coherencia de los campos sensibles tambien se exige en la base.

-- 1. Una noche sin duracion no existe (ni por una carrera de dos confirmaciones).
alter table public.recargo add constraint recargo_noche_con_duracion_check check (tipo <> 'noche' or desde <> hasta);

-- 2. actualizar_parametro: una clave inexistente falla (P0002) en vez de ignorarse.
create or replace function public.actualizar_parametro(p_clave text, p_valor integer)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actual integer;
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  select valor into v_actual from public.parametro where clave = p_clave;
  if not found then
    raise exception 'El parametro % no existe.', p_clave using errcode = 'P0002';
  end if;
  if public.es_parametro_sensible(p_clave) and p_valor is distinct from v_actual then
    raise exception 'Un parametro sensible solo cambia con vista previa y confirmacion.' using errcode = '42501';
  end if;
  update public.parametro set valor = p_valor where clave = p_clave and valor <> p_valor;
end;
$$;

-- 3. aplicar_cambio_confirmado rechaza (BG010) lo incoherente: porcentajes e IGV fuera de rango antes de escribir,
-- y los plazos (nivel 1 > nivel 2) sobre el resultado. La noche sin duracion la frena el check de `recargo` (23514).
create or replace function public.aplicar_cambio_confirmado(p_id uuid)
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
    -- Rangos del valor nuevo (los mismos que la API): se rechaza antes de escribir.
    if (c.key = 'porcentaje_igv' and (c.value ->> 'nuevo')::numeric not between 0 and 99.99)
       or (c.key in ('porcentaje_adelanto', 'porcentaje_penalizacion_nivel_2') and (c.value ->> 'nuevo')::integer not between 0 and 100)
       or (v_tabla = 'recargo' and v_col = 'porcentaje' and (c.value ->> 'nuevo')::numeric not between 0 and 300) then
      raise exception 'Valor fuera de rango en %.', c.key using errcode = 'BG010';
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
  -- Coherencia del resultado completo (si falla, todo lo anterior se revierte con la transaccion del llamador).
  if v.recurso = 'parametros'
     and (select valor from public.parametro where clave = 'horas_nivel_1')
         <= (select valor from public.parametro where clave = 'horas_nivel_2') then
    raise exception 'Las horas del nivel 1 deben ser mayores que las del nivel 2.' using errcode = 'BG010';
  end if;
end;
$$;
