begin;
create extension if not exists pgtap with schema extensions;
select plan(33);

-- RF-20 (1/2): configuracion_impuestos, parametros de ADR-015 y reserva.parametros_aplicados.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Configuracion de impuestos: una fila con 18 % incluido.
select has_table('public', 'configuracion_impuestos', 'existe configuracion_impuestos');
select is((select count(*)::int from public.configuracion_impuestos), 1, 'una sola fila');
select is((select porcentaje_igv::text from public.configuracion_impuestos), '18.00', 'IGV inicial 18.00');
select is((select precios_incluyen_igv from public.configuracion_impuestos), true, 'precios incluyen IGV por defecto');
select throws_ok($$insert into public.configuracion_impuestos (id, porcentaje_igv, precios_incluyen_igv) values (false, 10, true)$$, '23514', null, 'no se crea una segunda fila');
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = 100$$, '22003', null, 'porcentaje de 100 o mas no vale');
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = -1$$, '23514', null, 'porcentaje negativo no vale');

-- anon lee, no escribe
set local role anon;
select is((select porcentaje_igv::text from public.configuracion_impuestos), '18.00', 'anon lee el IGV');
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = 5$$, '42501', null, 'anon no cambia el IGV');
reset role;

-- cliente lee, no escribe (la fila queda intacta)
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select porcentaje_igv::text from public.configuracion_impuestos), '18.00', 'el cliente lee el IGV');
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = 5, precios_incluyen_igv = false$$, '42501', null, 'el cliente no escribe el IGV');
reset role;
select is((select porcentaje_igv::text || precios_incluyen_igv::text from public.configuracion_impuestos), '18.00true', 'la escritura del cliente no cambia nada');

-- administrador actualiza, no inserta ni borra
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = 10.50, precios_incluyen_igv = false$$, '42501', null, 'el administrador no actualiza directo (barrera RF-20)');
select throws_ok($$delete from public.configuracion_impuestos$$, '42501', null, 'nadie borra la configuracion');
select throws_ok($$insert into public.configuracion_impuestos (porcentaje_igv, precios_incluyen_igv) values (1, true)$$, '42501', null, 'nadie inserta otra fila');
reset role;
select is((select porcentaje_igv::text || precios_incluyen_igv::text from public.configuracion_impuestos), '18.00true', 'el IGV sigue intacto');
update public.configuracion_impuestos set porcentaje_igv = 10.50, precios_incluyen_igv = false;  -- estado para lo que sigue

-- Parametros de ADR-015
select is(
  (select jsonb_object_agg(clave, valor) from public.parametro where clave in (
    'porcentaje_adelanto', 'horas_nivel_1', 'horas_nivel_2', 'porcentaje_penalizacion_nivel_2',
    'minutos_tolerancia_inasistencia', 'dias_vigencia_credito', 'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2')),
  '{"horas_nivel_1": 48, "horas_nivel_2": 24, "dias_vigencia_credito": 30, "porcentaje_adelanto": 50,
    "reprogramaciones_nivel_1": 2, "reprogramaciones_nivel_2": 1, "porcentaje_penalizacion_nivel_2": 25,
    "minutos_tolerancia_inasistencia": 15}'::jsonb,
  'parametros de ADR-015 con sus valores iniciales');
select throws_ok($$update public.parametro set valor = 101 where clave = 'porcentaje_adelanto'$$, '23514', null, 'adelanto de mas de 100');
select throws_ok($$update public.parametro set valor = 101 where clave = 'porcentaje_penalizacion_nivel_2'$$, '23514', null, 'penalizacion de mas de 100');
select throws_ok($$update public.parametro set valor = 0 where clave = 'horas_nivel_1'$$, '23514', null, 'horas en cero');
select throws_ok($$insert into public.parametro (clave, valor) values ('inventado', 1)$$, '23514', null, 'clave fuera de la lista');
select lives_ok($$update public.parametro set valor = 100 where clave = 'porcentaje_adelanto'$$, 'adelanto de 100 vale');
update public.parametro set valor = 50 where clave = 'porcentaje_adelanto';

-- parametros_vigentes(): lo que se guarda en la reserva
select has_function('public', 'parametros_vigentes', 'existe parametros_vigentes');
select is(
  public.parametros_vigentes(),
  '{"porcentaje_igv": "10.50", "precios_incluyen_igv": false, "horas_limite_pago": 1, "horas_nivel_1": 48,
    "horas_nivel_2": 24, "porcentaje_adelanto": 50, "porcentaje_penalizacion_nivel_2": 25,
    "minutos_tolerancia_inasistencia": 15, "dias_vigencia_credito": 30, "reprogramaciones_nivel_1": 2,
    "reprogramaciones_nivel_2": 1}'::jsonb,
  'parametros_vigentes junta IGV y parametros (RF-18 suma los de cancelacion)');
set local role anon;
select is((select public.parametros_vigentes()->>'porcentaje_adelanto'), '50', 'anon ejecuta parametros_vigentes (la simulacion es publica)');
reset role;

-- reserva.parametros_aplicados: no nulo, por defecto los vigentes
select col_not_null('public', 'reserva', 'parametros_aplicados', 'parametros_aplicados no admite nulos');
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select 'bbbbbbbb-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', sa.id, se.id,
  '2027-06-01 10:00-05', '2027-06-01 11:00-05', 50, now() + interval '1 hour'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo';
select is((select parametros_aplicados->>'porcentaje_igv' from public.reserva), '10.50', 'una reserva sin indicarlos guarda los vigentes');
update public.configuracion_impuestos set porcentaje_igv = 18, precios_incluyen_igv = true;
select is((select parametros_aplicados->>'porcentaje_igv' from public.reserva), '10.50', 'cambiar el IGV no altera la reserva guardada');

-- el cliente puede guardarlos al reservar (los calcula el backend) pero no editarlos despues
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago, parametros_aplicados)
  select auth.uid(), sa.id, se.id, '2027-06-02 10:00-05', '2027-06-02 11:00-05', 50, now() + interval '1 hour', public.parametros_vigentes()
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'el cliente inserta con parametros_aplicados');
select throws_ok($$update public.reserva set parametros_aplicados = '{}'$$, '42501', null, 'el cliente no edita parametros_aplicados');
reset role;
select is((select count(*)::int from public.reserva where parametros_aplicados = '{}'::jsonb), 0, 'ninguna reserva quedo con parametros vacios');
select col_has_check('public', 'reserva', 'parametros_aplicados', 'parametros_aplicados con check de forma');
select throws_ok($$update public.reserva set parametros_aplicados = '{}'$$, '23514', null, 'parametros_aplicados vacio no vale');

select * from finish();
rollback;
