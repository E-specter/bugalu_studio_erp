-- RF-02 / RF-03: sala, catalogo de servicios, especialistas, recargos, feriados y parametros (ADR-006, ADR-009).
create table public.sala_tecnica (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  sede text not null,
  activa boolean not null default true,
  unique (nombre, sede)
);

create table public.servicio (
  id uuid primary key default gen_random_uuid(),
  nombre text not null unique,
  categoria text not null check (categoria in ('grabacion', 'ensayo', 'live', 'posproduccion')),
  ocupa_sala boolean not null,
  tarifa_hora numeric(10, 2) not null check (tarifa_hora >= 0),
  activo boolean not null default true
);

create table public.especialista (
  id uuid primary key default gen_random_uuid(),
  nombre text not null unique,
  monto_fijo numeric(10, 2) not null check (monto_fijo >= 0),
  monto_variable numeric(10, 2) not null check (monto_variable >= 0),
  unidad text not null check (unidad in ('hora', 'lapso_30')),
  activo boolean not null default true
);

create table public.servicio_especialista (
  id_servicio uuid not null references public.servicio (id) on delete cascade,
  id_especialista uuid not null references public.especialista (id) on delete cascade,
  primary key (id_servicio, id_especialista)
);

create table public.recargo (
  tipo text primary key check (tipo in ('noche', 'fin_de_semana', 'feriado')),
  porcentaje numeric(5, 2) not null check (porcentaje between 0 and 300),
  desde time,
  hasta time,
  -- Solo la noche tiene ventana horaria (puede cruzar la medianoche: desde > hasta).
  check ((tipo = 'noche') = (desde is not null and hasta is not null)),
  check (tipo = 'noche' or (desde is null and hasta is null))
);

create table public.feriado (
  fecha date primary key,
  nombre text not null
);

create table public.parametro (
  clave text primary key check (clave in (
    'dias_limite_pago', 'horas_limite_pago', 'anticipacion_minima_horas', 'anticipacion_maxima_semanas'
  )),
  valor integer not null check (valor > 0)
);

-- RLS y privilegios: lectura publica, escritura solo del administrador, sin borrados (salvo feriados).
-- parametro solo lo ve y escribe el administrador.
do $$
declare
  t text;
begin
  foreach t in array array['sala_tecnica', 'servicio', 'especialista', 'servicio_especialista', 'recargo', 'feriado', 'parametro'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
    execute format('grant insert on public.%I to authenticated', t);
    if t = 'parametro' then
      execute 'grant select on public.parametro to authenticated';
      execute 'create policy parametro_admin_lee on public.parametro for select to authenticated using (public.es_administrador())';
    else
      execute format('grant select on public.%I to anon, authenticated', t);
      execute format('create policy %I on public.%I for select to anon, authenticated using (true)', t || '_lectura_publica', t);
    end if;
    execute format('create policy %I on public.%I for insert to authenticated with check (public.es_administrador())', t || '_admin_inserta', t);
    if t <> 'servicio_especialista' then
      execute format('grant update on public.%I to authenticated', t);
      execute format(
        'create policy %I on public.%I for update to authenticated using (public.es_administrador()) with check (public.es_administrador())',
        t || '_admin_actualiza', t);
    end if;
  end loop;
end $$;

grant delete on public.feriado to authenticated;
create policy feriado_admin_borra on public.feriado for delete to authenticated using (public.es_administrador());

-- Datos iniciales (idempotentes). PROVISIONAL: los montos de tarifa y especialistas y los porcentajes de recargo
-- son valores de ejemplo; los define el estudio con el Administrador (ADR-009) y se ajustan por la API.
insert into public.sala_tecnica (nombre, sede) values ('Sala principal', 'La Molina') on conflict do nothing;

insert into public.servicio (nombre, categoria, ocupa_sala, tarifa_hora) values
  ('Grabación de voces', 'grabacion', true, 80),
  ('Grabación de instrumentos', 'grabacion', true, 90),
  ('Grabación de banda en vivo', 'grabacion', true, 120),
  ('Ensayo', 'ensayo', true, 40),
  ('Live session', 'live', true, 150),
  ('Mezcla', 'posproduccion', false, 0),
  ('Masterización', 'posproduccion', false, 0)
on conflict (nombre) do nothing;

insert into public.especialista (nombre, monto_fijo, monto_variable, unidad) values
  ('Ingeniero de sonido', 30, 25, 'lapso_30'),
  ('Ejecutante', 50, 40, 'hora'),
  ('Especialista audiovisual', 60, 50, 'hora'),
  ('Productor o arreglista', 80, 60, 'hora')
on conflict (nombre) do nothing;

insert into public.servicio_especialista (id_servicio, id_especialista)
select s.id, e.id
from public.servicio s, public.especialista e
where e.nombre = 'Ingeniero de sonido' and s.categoria in ('grabacion', 'live')
on conflict do nothing;

insert into public.recargo (tipo, porcentaje, desde, hasta) values
  ('noche', 25, '20:00', '06:00'),
  ('fin_de_semana', 20, null, null),
  ('feriado', 30, null, null)
on conflict (tipo) do nothing;

insert into public.parametro (clave, valor) values
  ('dias_limite_pago', 3),
  ('horas_limite_pago', 1),
  ('anticipacion_minima_horas', 2),
  ('anticipacion_maxima_semanas', 8)
on conflict (clave) do nothing;
