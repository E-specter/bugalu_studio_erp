-- RF-20 CA-11/CA-12: parametros de danos (anexo de condiciones de uso).
-- Decision de almacenamiento: `parametro.valor` es integer > 0 y la tarifa tiene que poder valer 0.00 y llevar dos
-- decimales. En vez de forzar centimos (el registro mostraria "2500") o ensanchar `valor` (lo leen ::int muchas
-- funciones), la tarifa vive en una fila unica `configuracion_danos`, igual que `configuracion_impuestos`: numeric exacto,
-- texto canonico 25.00 en el registro y el mismo camino de escritura. El tope (entero) es una clave mas de `parametro`.

create table public.configuracion_danos (
  id boolean primary key default true check (id),
  tarifa_hora_gestion numeric(6, 2) not null default 0.00 check (tarifa_hora_gestion between 0 and 9999.99)
);
insert into public.configuracion_danos default values;

alter table public.configuracion_danos enable row level security;
revoke all on public.configuracion_danos from anon, authenticated;
grant select on public.configuracion_danos to authenticated;
create policy configuracion_danos_admin_lee on public.configuracion_danos
  for select to authenticated using (public.es_administrador());
-- Sin insert/update/delete para nadie: solo aplicar_cambio_confirmado (security definer) la escribe.

alter table public.parametro drop constraint parametro_clave_check;
alter table public.parametro add constraint parametro_clave_check check (clave in (
  'dias_limite_pago', 'horas_limite_pago', 'anticipacion_minima_horas', 'anticipacion_maxima_semanas',
  'porcentaje_adelanto', 'horas_nivel_1', 'horas_nivel_2', 'porcentaje_penalizacion_nivel_2',
  'minutos_tolerancia_inasistencia', 'dias_vigencia_credito', 'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2',
  'tope_horas_sesiones_perdidas'
));
alter table public.parametro add constraint parametro_tope_check
  check (clave <> 'tope_horas_sesiones_perdidas' or valor <= 200);
insert into public.parametro (clave, valor) values ('tope_horas_sesiones_perdidas', 8) on conflict (clave) do nothing;

create or replace function public.es_parametro_sensible(p_clave text)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select p_clave in ('dias_limite_pago', 'horas_limite_pago', 'porcentaje_adelanto', 'horas_nivel_1', 'horas_nivel_2',
    'porcentaje_penalizacion_nivel_2', 'minutos_tolerancia_inasistencia', 'dias_vigencia_credito',
    'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2', 'tarifa_hora_gestion', 'tope_horas_sesiones_perdidas');
$$;
revoke all on function public.es_parametro_sensible(text) from public, anon, authenticated;

-- Lectura publica (CA-12): las condiciones de uso muestran los dos valores a cualquier visitante.
create function public.parametros_danos()
returns table (tarifa_hora_gestion numeric, tope_horas_sesiones_perdidas integer)
language sql
stable
security definer
set search_path = ''
as $$
  select (select c.tarifa_hora_gestion from public.configuracion_danos c),
         (select p.valor from public.parametro p where p.clave = 'tope_horas_sesiones_perdidas');
$$;
revoke all on function public.parametros_danos() from public;
grant execute on function public.parametros_danos() to anon, authenticated;

-- El bloqueo de `parametros` cubre tambien la tarifa.
create or replace function public.bloquear_recurso_sensible(p_recurso text, p_id uuid)
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
    perform 1 from public.configuracion_danos for update;
  elsif p_recurso = 'profesional' then
    perform 1 from public.perfil_profesional where id = p_id for update;
  else
    raise exception 'Recurso desconocido.' using errcode = '22023';
  end if;
end;
$$;

-- aplicar_cambio_confirmado: igual que en rf15a_profesionales, con la tarifa (configuracion_danos, numeric) y los
-- rangos de los dos parametros nuevos (BG010 antes de escribir).
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
  v_minutos integer;
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
    if v.recurso = 'profesional' then
      if c.key not in ('precio_30', 'precio_60') or v.id_recurso is null then
        raise exception 'Campo no aplicable: %.', c.key using errcode = '22023';
      end if;
      v_minutos := substr(c.key, 8)::integer;
      perform 1 from public.perfil_profesional where id = v.id_recurso for update;
      if not found then
        raise exception 'El recurso ya no existe.' using errcode = 'P0002';
      end if;
      select coalesce(to_char(precio, 'FM999999990.00'), 'no_ofrece') into v_real
        from public.precio_asesoria where id_profesional = v.id_recurso and minutos = v_minutos;
      v_real := coalesce(v_real, 'no_ofrece');
      if v_real is distinct from c.value ->> 'anterior' then
        raise exception 'El valor cambio desde la vista previa.' using errcode = '40001';
      end if;
      if c.value ->> 'nuevo' = 'no_ofrece' then
        delete from public.precio_asesoria where id_profesional = v.id_recurso and minutos = v_minutos;
        v_nuevo := 'no_ofrece';
      else
        if (c.value ->> 'nuevo')::numeric not between 0.01 and 99999999.99 then
          raise exception 'Valor fuera de rango en %.', c.key using errcode = 'BG010';
        end if;
        insert into public.precio_asesoria (id_profesional, minutos, precio)
          values (v.id_recurso, v_minutos, (c.value ->> 'nuevo')::numeric)
          on conflict (id_profesional, minutos) do update set precio = excluded.precio;
        v_nuevo := to_char((c.value ->> 'nuevo')::numeric, 'FM999999990.00');
      end if;
      insert into public.registro_cambio (id_autor, autor_nombre, recurso, id_recurso, nombre_recurso, campo, anterior, nuevo)
        values (v.id_autor,
                coalesce((select nullif(u.nombre, '') from public.usuario u where u.id = v.id_autor), 'Administrador'),
                v.recurso, v.id_recurso, v.nombre_recurso, c.key, v_real, v_nuevo);
      continue;
    end if;
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
      if c.key = 'tarifa_hora_gestion' then  -- decimal: vive en configuracion_danos (RF-20 CA-11)
        v_tabla := 'configuracion_danos'; v_col := c.key; v_donde := 'true';
      else
        v_tabla := 'parametro'; v_col := 'valor'; v_donde := format('clave = %L', c.key);
      end if;
    else
      raise exception 'Campo no aplicable: %.', c.key using errcode = '22023';
    end if;
    -- Rangos del valor nuevo (los mismos que la API): se rechaza antes de escribir.
    if (c.key = 'porcentaje_igv' and (c.value ->> 'nuevo')::numeric not between 0 and 99.99)
       or (c.key in ('porcentaje_adelanto', 'porcentaje_penalizacion_nivel_2') and (c.value ->> 'nuevo')::integer not between 0 and 100)
       or (c.key = 'tarifa_hora_gestion' and (c.value ->> 'nuevo')::numeric not between 0 and 9999.99)
       or (c.key = 'tope_horas_sesiones_perdidas' and (c.value ->> 'nuevo')::integer not between 1 and 200)
       or (v_tabla = 'recargo' and v_col = 'porcentaje' and (c.value ->> 'nuevo')::numeric not between 0 and 300) then
      raise exception 'Valor fuera de rango en %.', c.key using errcode = 'BG010';
    end if;
    v_tipo := case
      when v_col in ('porcentaje_igv', 'tarifa_hora', 'monto_fijo', 'monto_variable', 'porcentaje', 'tarifa_hora_gestion') then 'numeric'
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
