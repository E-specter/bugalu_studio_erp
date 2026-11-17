-- RF-20 (1/2): configuracion de impuestos (ADR-013), parametros de cancelacion y adelanto (ADR-015)
-- y parametros aplicados por reserva (CA-07).

-- Configuracion de impuestos: una sola fila (numeric(4, 2) ya limita a 99.99). Lectura publica; solo el administrador la actualiza (el flujo
-- con barreras de RF-20 llega despues). Nadie inserta ni borra.
create table public.configuracion_impuestos (
  id boolean primary key default true check (id),
  porcentaje_igv numeric(4, 2) not null default 18.00 check (porcentaje_igv >= 0),
  precios_incluyen_igv boolean not null default true
);
insert into public.configuracion_impuestos default values;

alter table public.configuracion_impuestos enable row level security;
revoke all on public.configuracion_impuestos from anon, authenticated;
grant select on public.configuracion_impuestos to anon, authenticated;
grant update (porcentaje_igv, precios_incluyen_igv) on public.configuracion_impuestos to authenticated;
create policy configuracion_impuestos_lectura_publica on public.configuracion_impuestos
  for select to anon, authenticated using (true);
create policy configuracion_impuestos_admin_actualiza on public.configuracion_impuestos
  for update to authenticated using (public.es_administrador()) with check (public.es_administrador());

-- Parametros de ADR-015: lista cerrada ampliada y rangos de los porcentajes.
alter table public.parametro drop constraint parametro_clave_check;
alter table public.parametro add constraint parametro_clave_check check (clave in (
  'dias_limite_pago', 'horas_limite_pago', 'anticipacion_minima_horas', 'anticipacion_maxima_semanas',
  'porcentaje_adelanto', 'horas_nivel_1', 'horas_nivel_2', 'porcentaje_penalizacion_nivel_2',
  'minutos_tolerancia_inasistencia', 'dias_vigencia_credito', 'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2'
));
alter table public.parametro add constraint parametro_porcentaje_check
  check (clave not in ('porcentaje_adelanto', 'porcentaje_penalizacion_nivel_2') or valor <= 100);

insert into public.parametro (clave, valor) values
  ('porcentaje_adelanto', 50),
  ('horas_nivel_1', 48),
  ('horas_nivel_2', 24),
  ('porcentaje_penalizacion_nivel_2', 25),
  ('minutos_tolerancia_inasistencia', 15),
  ('dias_vigencia_credito', 30),
  ('reprogramaciones_nivel_1', 2),
  ('reprogramaciones_nivel_2', 1)
on conflict (clave) do nothing;

-- IGV y parametros vigentes ahora mismo: lo que cada reserva guarda al crearse. `parametro` solo lo lee el
-- administrador, por eso la funcion es security definer. La simulacion publica tambien la usa: nada de esto es secreto
-- (el adelanto y el IGV ya se ven en el precio; los plazos son politica publica).
create function public.parametros_vigentes()
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'porcentaje_igv', (select to_char(porcentaje_igv, 'FM990.00') from public.configuracion_impuestos),
    'precios_incluyen_igv', (select precios_incluyen_igv from public.configuracion_impuestos),
    'horas_limite_pago', (select valor from public.parametro where clave = 'horas_limite_pago'),
    'horas_nivel_1', (select valor from public.parametro where clave = 'horas_nivel_1'),
    'horas_nivel_2', (select valor from public.parametro where clave = 'horas_nivel_2'),
    'porcentaje_adelanto', (select valor from public.parametro where clave = 'porcentaje_adelanto'));
$$;
revoke all on function public.parametros_vigentes() from public;
grant execute on function public.parametros_vigentes() to anon, authenticated;

-- reserva.parametros_aplicados: las reservas anteriores a RF-20 se completan con IGV 18 % incluido y los
-- parametros vigentes (decision 1 de RF-20); las nuevas toman los vigentes si no se indican.
alter table public.reserva add column parametros_aplicados jsonb;
update public.reserva
  set parametros_aplicados = public.parametros_vigentes()
    || '{"porcentaje_igv": "18.00", "precios_incluyen_igv": true}'::jsonb;
alter table public.reserva
  alter column parametros_aplicados set not null,
  alter column parametros_aplicados set default public.parametros_vigentes(),
  add constraint reserva_parametros_aplicados_check check (
    parametros_aplicados ?& array['porcentaje_igv', 'precios_incluyen_igv', 'horas_limite_pago',
      'horas_nivel_1', 'horas_nivel_2', 'porcentaje_adelanto']);

-- El backend los calcula al reservar y los pasa en el insert; el cliente no los edita despues.
grant insert (parametros_aplicados) on public.reserva to authenticated;
