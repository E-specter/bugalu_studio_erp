begin;
create extension if not exists pgtap with schema extensions;
select plan(32);

-- RF-20 CA-11/CA-12: parametros de danos. La tarifa (decimal) vive en configuracion_danos; el tope (entero 1-200) en parametro.
-- Ambos son sensibles: solo cambian por crear_confirmacion + aplicar_cambio_confirmado. parametros_danos() es publica.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador', nombre = 'Ana Admin' where id = '00000000-0000-0000-0000-0000000000ad';

-- Estado inicial conocido (todo se revierte al final).
update public.configuracion_danos set tarifa_hora_gestion = 0;
update public.parametro set valor = 8 where clave = 'tope_horas_sesiones_perdidas';

select has_table('public', 'configuracion_danos', 'existe configuracion_danos');
select col_default_is('public', 'configuracion_danos', 'tarifa_hora_gestion', '0.00', 'la tarifa inicial es 0.00 (por fijar)');
select is((select count(*)::int from public.configuracion_danos), 1, 'una sola fila');
select ok(public.es_parametro_sensible('tope_horas_sesiones_perdidas'), 'el tope es sensible');
select ok(public.es_parametro_sensible('tarifa_hora_gestion'), 'la tarifa es sensible');

-- Rangos en la base (como superusuario: lo que ninguna ruta debe poder saltar).
select throws_ok($$update public.configuracion_danos set tarifa_hora_gestion = -0.01$$, '23514', null, 'tarifa negativa');
select throws_ok($$update public.configuracion_danos set tarifa_hora_gestion = 10000$$, '22003', null, 'tarifa sobre 9999.99');
select lives_ok($$update public.configuracion_danos set tarifa_hora_gestion = 9999.99$$, 'tarifa 9999.99 cabe');
update public.configuracion_danos set tarifa_hora_gestion = 0;
select throws_ok($$update public.parametro set valor = 0 where clave = 'tope_horas_sesiones_perdidas'$$, '23514', null, 'tope 0');
select throws_ok($$update public.parametro set valor = 201 where clave = 'tope_horas_sesiones_perdidas'$$, '23514', null, 'tope 201');

-- Lectura publica: parametros_danos() sirve a anon y a cualquier sesion.
set local role anon;
select is((select tarifa_hora_gestion::text || '/' || tope_horas_sesiones_perdidas::text from public.parametros_danos()), '0.00/8', 'anon lee los dos valores');
select throws_ok($$select * from public.configuracion_danos$$, '42501', null, 'anon no lee la tabla directamente');
select throws_ok($$update public.configuracion_danos set tarifa_hora_gestion = 1$$, '42501', null, 'anon no escribe la tarifa');
select throws_ok($$update public.parametro set valor = 9 where clave = 'tope_horas_sesiones_perdidas'$$, '42501', null, 'anon no escribe el tope');
reset role;

-- Cliente: lee por la funcion, no escribe ni por SQL ni por los caminos del flujo.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select tope_horas_sesiones_perdidas from public.parametros_danos()), 8, 'el cliente lee por la funcion');
select is((select count(*)::int from public.configuracion_danos), 0, 'el cliente no ve la tabla (RLS)');
select throws_ok($$update public.configuracion_danos set tarifa_hora_gestion = 1$$, '42501', null, 'el cliente no escribe la tarifa');
select throws_ok($$insert into public.configuracion_danos (id, tarifa_hora_gestion) values (false, 1)$$, '42501', null, 'el cliente no inserta');
select throws_ok($$delete from public.configuracion_danos$$, '42501', null, 'el cliente no borra');
select throws_ok($$select public.actualizar_parametro('tope_horas_sesiones_perdidas', 9)$$, '42501', null, 'el cliente no usa actualizar_parametro');
select throws_ok($$select public.crear_confirmacion('h', 'parametros', null, 'Parametros', '{}', 10)$$, '42501', null, 'el cliente no crea confirmaciones');
reset role;
select is((select tarifa_hora_gestion::text from public.configuracion_danos), '0.00', 'la tarifa sigue intacta');
select is((select valor from public.parametro where clave = 'tope_horas_sesiones_perdidas'), 8, 'el tope sigue intacto');

-- Administrador: ni por SQL cambia la tarifa o el tope; el mismo valor no falla.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.configuracion_danos set tarifa_hora_gestion = 25$$, '42501', null, 'el administrador no cambia la tarifa por SQL');
select throws_ok($$select public.actualizar_parametro('tope_horas_sesiones_perdidas', 9)$$, '42501', null, 'ni el tope por actualizar_parametro');
select lives_ok($$select public.actualizar_parametro('tope_horas_sesiones_perdidas', 8)$$, 'el mismo valor del tope es un no-op');

-- Flujo con barrera: aplica y registra con el texto canonico.
select public.crear_confirmacion('hd-1', 'parametros', null, 'Parametros',
  '{"tarifa_hora_gestion": {"anterior": "0.00", "nuevo": "25.5"}, "tope_horas_sesiones_perdidas": {"anterior": "8", "nuevo": "12"}}', 10);
select lives_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hd-1'))$$, 'el flujo aplica tarifa y tope');
select is((select tarifa_hora_gestion::text || '/' || tope_horas_sesiones_perdidas::text from public.parametros_danos()), '25.50/12', 'valores nuevos');
select is((select string_agg(campo || ':' || anterior || '>' || nuevo, ',' order by campo) from public.registro_cambio where id_autor = '00000000-0000-0000-0000-0000000000ad' and campo in ('tarifa_hora_gestion', 'tope_horas_sesiones_perdidas')),
  'tarifa_hora_gestion:0.00>25.50,tope_horas_sesiones_perdidas:8>12', 'el registro guarda anterior y nuevo en texto');

-- Fuera de rango o con un anterior falso: no se aplica nada.
select public.crear_confirmacion('hd-2', 'parametros', null, 'Parametros', '{"tarifa_hora_gestion": {"anterior": "25.50", "nuevo": "10000"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hd-2'))$$, 'BG010', null, 'tarifa fuera de rango');
select public.crear_confirmacion('hd-3', 'parametros', null, 'Parametros', '{"tope_horas_sesiones_perdidas": {"anterior": "12", "nuevo": "201"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hd-3'))$$, 'BG010', null, 'tope fuera de rango');
select public.crear_confirmacion('hd-4', 'parametros', null, 'Parametros', '{"tarifa_hora_gestion": {"anterior": "1.00", "nuevo": "30"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hd-4'))$$, '40001', null, 'anterior falso: el valor cambio');
reset role;

select * from finish();
rollback;
