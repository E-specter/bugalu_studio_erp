-- RF-15 etapa A: rol `profesional`, especialidades, perfil publico, precios (cambio sensible de RF-20), horarios y foto.
-- Un usuario tiene un solo rol; el perfil cuelga de un usuario con rol profesional o administrador (decision 8).
-- Las asesorias (reserva con tipo) llegan en la etapa B: los puntos marcados con `etapa B` quedan preparados.

-- 1. El rol. es_personal() y es_administrador() enumeran sus roles: el profesional no entra en ninguna.
alter table public.usuario drop constraint usuario_rol_check;
alter table public.usuario add constraint usuario_rol_check
  check (rol in ('cliente', 'personal', 'administrador', 'profesional'));

-- Administrador, o el propio usuario si tiene rol de profesional o de administrador.
create function public.gestiona_perfil(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.es_administrador() or (
    p_id = (select auth.uid())
    and exists (select 1 from public.usuario where id = p_id and rol in ('profesional', 'administrador'))
  );
$$;
revoke all on function public.gestiona_perfil(uuid) from public, anon;
grant execute on function public.gestiona_perfil(uuid) to authenticated;

-- 2. Especialidades (CA-02): se crean, renombran y desactivan; nunca se borran. La clave ignora mayusculas y tildes.
create table public.especialidad_asesoria (
  id uuid primary key default gen_random_uuid(),
  nombre text not null check (nombre = btrim(nombre) and char_length(nombre) between 2 and 60),
  nombre_clave text generated always as (
    lower(translate(nombre, 'áéíóúüÁÉÍÓÚÜ', 'aeiouuAEIOUU'))) stored unique,
  activa boolean not null default true,
  creada_en timestamptz not null default now()
);
alter table public.especialidad_asesoria enable row level security;
revoke all on public.especialidad_asesoria from anon, authenticated;
grant select on public.especialidad_asesoria to anon, authenticated;
grant insert (nombre), update (nombre, activa) on public.especialidad_asesoria to authenticated;
create policy especialidad_lectura_publica on public.especialidad_asesoria for select to anon using (activa);
create policy especialidad_lectura on public.especialidad_asesoria for select to authenticated
  using (activa or public.es_administrador());
create policy especialidad_alta on public.especialidad_asesoria for insert to authenticated
  with check (public.es_administrador());
create policy especialidad_cambio on public.especialidad_asesoria for update to authenticated
  using (public.es_administrador()) with check (public.es_administrador());

-- 3. Perfil (CA-03). `activo` y los precios solo cambian por funciones.
create table public.perfil_profesional (
  id uuid primary key references public.usuario (id) on delete cascade,
  nombre_artistico text check (nombre_artistico is null or char_length(nombre_artistico) between 1 and 80),
  presentacion text check (presentacion is null or char_length(presentacion) <= 600),
  redes jsonb not null default '[]' check (jsonb_typeof(redes) = 'array' and jsonb_array_length(redes) <= 5),
  foto_ruta text,
  activo boolean not null default false,
  creado_en timestamptz not null default now()
);
create table public.perfil_especialidad (
  id_profesional uuid not null references public.perfil_profesional (id) on delete cascade,
  id_especialidad uuid not null references public.especialidad_asesoria (id),
  primary key (id_profesional, id_especialidad)
);
-- Precio de 30 o 60 min en soles, IGV incluido; sin fila = no ofrece esa duracion.
create table public.precio_asesoria (
  id_profesional uuid not null references public.perfil_profesional (id) on delete cascade,
  minutos integer not null check (minutos in (30, 60)),
  precio numeric(10, 2) not null check (precio > 0),
  primary key (id_profesional, minutos)
);

-- Publicado = activo, con al menos una especialidad activa y un precio.
create function public.perfil_publicado(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.perfil_profesional p
    where p.id = p_id and p.activo
      and exists (select 1 from public.perfil_especialidad pe
                  join public.especialidad_asesoria e on e.id = pe.id_especialidad
                  where pe.id_profesional = p.id and e.activa)
      and exists (select 1 from public.precio_asesoria pr where pr.id_profesional = p.id)
  );
$$;
create function public.puede_ver_perfil(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.perfil_publicado(p_id) or public.gestiona_perfil(p_id);
$$;
-- Nombre completo (RF-01) de un perfil que quien llama puede ver; la cuenta (`usuario`) sigue cerrada.
create function public.nombre_profesional(p_id uuid)
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select u.nombre from public.usuario u where u.id = p_id and public.puede_ver_perfil(p_id);
$$;
revoke all on function public.perfil_publicado(uuid) from public;
revoke all on function public.puede_ver_perfil(uuid) from public;
revoke all on function public.nombre_profesional(uuid) from public;
grant execute on function public.perfil_publicado(uuid) to anon, authenticated;
grant execute on function public.puede_ver_perfil(uuid) to anon, authenticated;
grant execute on function public.nombre_profesional(uuid) to anon, authenticated;

alter table public.perfil_profesional enable row level security;
alter table public.perfil_especialidad enable row level security;
alter table public.precio_asesoria enable row level security;
revoke all on public.perfil_profesional, public.perfil_especialidad, public.precio_asesoria from anon, authenticated;
grant select on public.perfil_profesional, public.perfil_especialidad, public.precio_asesoria to anon, authenticated;
grant update (nombre_artistico, presentacion, redes, foto_ruta) on public.perfil_profesional to authenticated;
create policy perfil_lectura on public.perfil_profesional for select to anon, authenticated
  using (public.puede_ver_perfil(id));
create policy perfil_cambio on public.perfil_profesional for update to authenticated
  using (public.gestiona_perfil(id)) with check (public.gestiona_perfil(id));
create policy perfil_especialidad_lectura on public.perfil_especialidad for select to anon, authenticated
  using (public.puede_ver_perfil(id_profesional));
create policy precio_lectura on public.precio_asesoria for select to anon, authenticated
  using (public.puede_ver_perfil(id_profesional));

-- Alta del perfil (inactivo). Interna: la llama asignar_rol, nadie mas.
create function public.crear_perfil_profesional(p_id uuid)
returns void
language sql
security definer
set search_path = ''
as $$
  insert into public.perfil_profesional (id) values (p_id) on conflict (id) do nothing;
$$;
revoke all on function public.crear_perfil_profesional(uuid) from public, anon, authenticated;

-- Rol profesional: nace su perfil. Quien deja de serlo (ni profesional ni administrador) queda inactivo, sin borrar nada.
-- shortcut: la regla 409 `profesional_con_asesorias` (quitar el rol con asesorias vivas) llega en la etapa B,
-- cuando exista `asesoria`; hasta entonces no hay asesorias que proteger.
create or replace function public.asignar_rol(id_usuario uuid, rol text, especialidad text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador asigna roles' using errcode = '42501';
  end if;
  update public.usuario as u set rol = asignar_rol.rol, especialidad = asignar_rol.especialidad
  where u.id = asignar_rol.id_usuario;
  if not found then
    raise exception 'el usuario no existe' using errcode = 'P0002';
  end if;
  if asignar_rol.rol = 'profesional' then
    perform public.crear_perfil_profesional(id_usuario);
  elsif asignar_rol.rol <> 'administrador' then
    update public.perfil_profesional set activo = false where id = id_usuario and activo;
  end if;
end;
$$;

-- Especialidades del perfil: 1 a 5, distintas y activas; reemplaza el conjunto entero.
create function public.reemplazar_especialidades(p_id uuid, p_ids uuid[])
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ids uuid[];
begin
  if not public.gestiona_perfil(p_id) then
    raise exception 'sin permiso sobre este perfil' using errcode = '42501';
  end if;
  perform 1 from public.perfil_profesional where id = p_id for update;
  if not found then
    raise exception 'el perfil no existe' using errcode = 'P0002';
  end if;
  select array_agg(distinct x) into v_ids from unnest(p_ids) as x;
  if coalesce(array_length(v_ids, 1), 0) not between 1 and 5
     or (select count(*) from public.especialidad_asesoria e where e.id = any(v_ids) and e.activa) <> array_length(v_ids, 1) then
    raise exception 'de 1 a 5 especialidades activas' using errcode = '22023';
  end if;
  delete from public.perfil_especialidad where id_profesional = p_id;
  insert into public.perfil_especialidad (id_profesional, id_especialidad) select p_id, unnest(v_ids);
end;
$$;

-- Estado del perfil: solo el administrador.
create function public.cambiar_estado_profesional(p_id uuid, p_activo boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador cambia el estado' using errcode = '42501';
  end if;
  update public.perfil_profesional set activo = p_activo where id = p_id;
  if not found then
    raise exception 'el perfil no existe' using errcode = 'P0002';
  end if;
end;
$$;
revoke all on function public.reemplazar_especialidades(uuid, uuid[]) from public, anon;
revoke all on function public.cambiar_estado_profesional(uuid, boolean) from public, anon;
grant execute on function public.reemplazar_especialidades(uuid, uuid[]) to authenticated;
grant execute on function public.cambiar_estado_profesional(uuid, boolean) to authenticated;

-- 4. Horarios (CA-05): bloques [inicio, fin) futuros, en multiplos de 30 min, sin solaparse (lo garantiza la exclusion).
create table public.horario_profesional (
  id uuid primary key default gen_random_uuid(),
  id_profesional uuid not null references public.perfil_profesional (id) on delete cascade,
  inicio timestamptz not null,
  fin timestamptz not null,
  id_publicador uuid references public.usuario (id) on delete set null,
  check (fin > inicio),
  check (mod(extract(epoch from inicio), 1800) = 0 and mod(extract(epoch from fin), 1800) = 0),
  exclude using gist (id_profesional with =, tstzrange(inicio, fin) with &&)
);
alter table public.horario_profesional enable row level security;
revoke all on public.horario_profesional from anon, authenticated;
grant select on public.horario_profesional to anon, authenticated;
grant insert (id_profesional, inicio, fin, id_publicador) on public.horario_profesional to authenticated;
create policy horario_lectura on public.horario_profesional for select to anon, authenticated
  using (public.puede_ver_perfil(id_profesional));
create policy horario_alta on public.horario_profesional for insert to authenticated
  with check (public.gestiona_perfil(id_profesional) and inicio > now()
              and id_publicador is not distinct from (select auth.uid()));

-- Retirar un bloque: unica via de borrado.
-- shortcut: la regla 409 `horario_con_asesorias` (asesorias vivas dentro del bloque) llega en la etapa B; aqui es el
-- punto donde se comprueba, junto al bloqueo del perfil que serializa con el agendamiento.
create function public.retirar_horario(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_perfil uuid;
begin
  select id_profesional into v_perfil from public.horario_profesional where id = p_id;
  if not found then
    raise exception 'el horario no existe' using errcode = 'P0002';
  end if;
  if not public.gestiona_perfil(v_perfil) then
    raise exception 'sin permiso sobre este horario' using errcode = '42501';
  end if;
  perform 1 from public.perfil_profesional where id = v_perfil for update;
  delete from public.horario_profesional where id = p_id;
  if not found then
    raise exception 'el horario no existe' using errcode = 'P0002';
  end if;
end;
$$;
revoke all on function public.retirar_horario(uuid) from public, anon;
grant execute on function public.retirar_horario(uuid) to authenticated;

-- 5. Precios por el flujo sensible de RF-20: el recurso `profesional` con los campos `precio_30` y `precio_60`
-- (texto canonico `50.00`, o `no_ofrece`). Solo aplicar_cambio_confirmado los escribe.
alter table public.confirmacion_cambio drop constraint confirmacion_cambio_recurso_check;
alter table public.confirmacion_cambio add constraint confirmacion_cambio_recurso_check
  check (recurso in ('impuestos', 'servicio', 'especialista', 'recargos', 'parametros', 'profesional'));
alter table public.registro_cambio drop constraint registro_cambio_recurso_check;
alter table public.registro_cambio add constraint registro_cambio_recurso_check
  check (recurso in ('impuestos', 'servicio', 'especialista', 'recargos', 'parametros', 'profesional'));

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
  elsif p_recurso = 'profesional' then
    perform 1 from public.perfil_profesional where id = p_id for update;
  else
    raise exception 'Recurso desconocido.' using errcode = '22023';
  end if;
end;
$$;

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

-- 6. Foto (CA-03): bucket publico, JPG, PNG o WebP de hasta 2 MB; cada perfil escribe solo en `<id del perfil>/`.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('profesionales', 'profesionales', true, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update set public = true, file_size_limit = 2097152,
  allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp'];

create function public.gestiona_carpeta_de_perfil(p_carpeta text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select case when p_carpeta ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
              then public.gestiona_perfil(p_carpeta::uuid) else false end;
$$;
revoke all on function public.gestiona_carpeta_de_perfil(text) from public, anon;
grant execute on function public.gestiona_carpeta_de_perfil(text) to authenticated;
create policy profesionales_inserta on storage.objects for insert to authenticated
  with check (bucket_id = 'profesionales' and public.gestiona_carpeta_de_perfil((storage.foldername(name))[1]));
create policy profesionales_borra on storage.objects for delete to authenticated
  using (bucket_id = 'profesionales' and public.gestiona_carpeta_de_perfil((storage.foldername(name))[1]));

-- 7. Perfil de un administrador (decision 8): solo el administrador; el rol debe ser profesional o administrador.
create function public.crear_perfil_de_usuario(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_rol text;
begin
  if not public.es_administrador() then
    raise exception 'solo un administrador crea perfiles' using errcode = '42501';
  end if;
  select rol into v_rol from public.usuario where id = p_id;
  if not found then
    raise exception 'el usuario no existe' using errcode = 'P0002';
  end if;
  if v_rol not in ('profesional', 'administrador') then
    raise exception 'rol_no_admitido' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.perfil_profesional where id = p_id) then
    raise exception 'perfil_existente' using errcode = 'P0001';
  end if;
  perform public.crear_perfil_profesional(p_id);
end;
$$;
revoke all on function public.crear_perfil_de_usuario(uuid) from public, anon;
grant execute on function public.crear_perfil_de_usuario(uuid) to authenticated;
-- Storage exige poder ver el objeto para borrarlo; la lectura publica del bucket no pasa por esta politica.
create policy profesionales_lee on storage.objects for select to authenticated
  using (bucket_id = 'profesionales' and public.gestiona_carpeta_de_perfil((storage.foldername(name))[1]));
