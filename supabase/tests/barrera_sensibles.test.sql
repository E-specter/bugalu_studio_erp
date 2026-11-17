begin;
create extension if not exists pgtap with schema extensions;
select plan(50);

-- RF-20 CA-04..CA-08: la barrera vive tambien en la base. Un administrador por SQL (con sus claims) no cambia un campo
-- sensible ni falsifica el registro; solo crear_confirmacion + aplicar_cambio_confirmado escriben esos campos.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ae', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ae@t.pe', '{}');
update public.usuario set rol = 'administrador', nombre = 'Ana Admin' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ae';

-- Estado inicial conocido (otras pruebas de la base pueden haber dejado otros valores; todo se revierte al final).
update public.configuracion_impuestos set porcentaje_igv = 18, precios_incluyen_igv = true;
update public.servicio set tarifa_hora = 40, monto_fijo = 0 where nombre = 'Ensayo';
update public.especialista set monto_fijo = 50, monto_variable = 40, unidad = 'hora' where nombre = 'Ejecutante';
update public.recargo set porcentaje = 25, desde = '20:00', hasta = '06:00' where tipo = 'noche';
update public.recargo set porcentaje = 30 where tipo = 'feriado';
update public.parametro set valor = 48 where clave = 'horas_nivel_1';

select has_function('public', 'crear_confirmacion', array['text', 'text', 'uuid', 'text', 'jsonb', 'integer'], 'existe crear_confirmacion');
select has_function('public', 'aplicar_cambio_confirmado', array['uuid'], 'existe aplicar_cambio_confirmado');
select has_function('public', 'actualizar_parametro', array['text', 'integer'], 'existe actualizar_parametro');
select hasnt_function('public', 'registrar_cambios', array['uuid'], 'ya no hay una funcion que registre sin aplicar');

-- Administrador A, directo por SQL.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.configuracion_impuestos set porcentaje_igv = 5$$, '42501', null, 'el administrador no cambia el IGV por SQL');
select throws_ok($$update public.configuracion_impuestos set precios_incluyen_igv = false$$, '42501', null, 'ni si los precios incluyen IGV');
select throws_ok($$update public.servicio set tarifa_hora = 1 where nombre = 'Ensayo'$$, '42501', null, 'ni la tarifa del servicio');
select throws_ok($$update public.servicio set monto_fijo = 1 where nombre = 'Ensayo'$$, '42501', null, 'ni el monto fijo del servicio');
select throws_ok($$update public.especialista set monto_fijo = 1 where nombre = 'Ejecutante'$$, '42501', null, 'ni el monto fijo del especialista');
select throws_ok($$update public.especialista set monto_variable = 1 where nombre = 'Ejecutante'$$, '42501', null, 'ni el monto variable');
select throws_ok($$update public.especialista set unidad = 'hora' where nombre = 'Ejecutante'$$, '42501', null, 'ni la unidad');
select throws_ok($$update public.recargo set porcentaje = 1 where tipo = 'noche'$$, '42501', null, 'ni el porcentaje de un recargo');
select throws_ok($$update public.recargo set desde = '19:00' where tipo = 'noche'$$, '42501', null, 'ni la ventana de la noche');
select throws_ok($$insert into public.recargo (tipo, porcentaje) values ('feriado', 1) on conflict (tipo) do update set porcentaje = 1$$, '42501', null, 'ni con upsert');
select throws_ok($$update public.parametro set valor = 99 where clave = 'horas_nivel_1'$$, '42501', null, 'ni un parametro sensible');
select throws_ok($$update public.parametro set valor = 99 where clave = 'anticipacion_minima_horas'$$, '42501', null, 'parametro solo por actualizar_parametro');
select throws_ok($$insert into public.confirmacion_cambio (hash_token, id_autor, recurso, nombre_recurso, cambios, expira_en)
  values ('hash-falsa', '00000000-0000-0000-0000-0000000000ad', 'impuestos', 'Impuestos', '{"porcentaje_igv": {"anterior": "1.00", "nuevo": "2.00"}}', now() + interval '10 minutes')$$,
  '42501', null, 'el administrador no inserta una confirmacion inventada');
select lives_ok($$update public.servicio set activo = activo where nombre = 'Ensayo'$$, 'los campos no sensibles de servicio siguen editables');
select lives_ok($$update public.especialista set activo = activo where nombre = 'Ejecutante'$$, 'los de especialista tambien');
reset role;
select is((select porcentaje_igv::text from public.configuracion_impuestos), '18.00', 'el IGV sigue intacto');
select is((select tarifa_hora::text from public.servicio where nombre = 'Ensayo'), '40.00', 'la tarifa sigue intacta');
select is((select valor from public.parametro where clave = 'horas_nivel_1'), 48, 'el parametro sigue intacto');
select is((select count(*)::int from public.confirmacion_cambio), 0, 'no quedo ninguna confirmacion inventada');

-- actualizar_parametro: libre para lo no sensible o sin cambio de valor; el cliente no.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.actualizar_parametro('anticipacion_minima_horas', 5)$$, '42501', null, 'el cliente no usa actualizar_parametro');
select throws_ok($$select public.crear_confirmacion('h', 'impuestos', null, 'Impuestos', '{}', 10)$$, '42501', null, 'el cliente no crea confirmaciones');
select throws_ok($$select public.aplicar_cambio_confirmado(gen_random_uuid())$$, '42501', null, 'el cliente no aplica cambios');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.actualizar_parametro('horas_nivel_1', 99)$$, '42501', null, 'un sensible con otro valor no pasa por actualizar_parametro');
select lives_ok($$select public.actualizar_parametro('horas_nivel_1', 48)$$, 'un sensible con el mismo valor es un no-op');
select lives_ok($$select public.actualizar_parametro('anticipacion_minima_horas', 5)$$, 'un no sensible si cambia');
reset role;
select is((select valor from public.parametro where clave = 'horas_nivel_1'), 48, 'horas_nivel_1 no cambio');
select is((select valor from public.parametro where clave = 'anticipacion_minima_horas'), 5, 'anticipacion_minima_horas si');

-- El flujo: crear_confirmacion + aplicar_cambio_confirmado aplica y registra el valor REAL anterior.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.crear_confirmacion('hash-1', 'impuestos', null, 'Impuestos',
  '{"porcentaje_igv": {"anterior": "18.00", "nuevo": "10.00"}, "precios_incluyen_igv": {"anterior": "true", "nuevo": "false"}}', 10)$$,
  'A crea su confirmacion');
select lives_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hash-1'))$$, 'A aplica su confirmacion');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hash-1'))$$, '55000', null, 'un token se usa una sola vez');
reset role;
select is((select porcentaje_igv::text || precios_incluyen_igv::text from public.configuracion_impuestos), '10.00false', 'el cambio se aplico');
select is((select count(*)::int from public.registro_cambio where recurso = 'impuestos' and id_autor = '00000000-0000-0000-0000-0000000000ad'), 2, 'una fila por campo');
select is((select autor_nombre || ':' || campo || ':' || anterior || ':' || nuevo from public.registro_cambio where campo = 'porcentaje_igv' and id_autor = '00000000-0000-0000-0000-0000000000ad'), 'Ana Admin:porcentaje_igv:18.00:10.00', 'la fila guarda autor, campo, anterior y nuevo');

-- Falsificar el "anterior": la base compara con el valor real y no aplica ni registra nada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.crear_confirmacion('hash-2', 'servicio', (select id from public.servicio where nombre = 'Ensayo'), 'Ensayo',
  '{"tarifa_hora": {"anterior": "1.00", "nuevo": "55.00"}}', 10)$$, 'A crea una confirmacion con un anterior falso');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hash-2'))$$, '40001', null, 'no se aplica: el anterior no es el real');
select lives_ok($$select public.crear_confirmacion('hash-3', 'servicio', (select id from public.servicio where nombre = 'Ensayo'), 'Ensayo',
  '{"nombre": {"anterior": "Ensayo", "nuevo": "Otro"}}', 10)$$, 'A crea una confirmacion con un campo no sensible');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hash-3'))$$, '22023', null, 'un campo fuera de la lista no se aplica');
reset role;
select is((select tarifa_hora::text from public.servicio where nombre = 'Ensayo'), '40.00', 'la tarifa sigue intacta');
select is((select count(*)::int from public.registro_cambio where recurso = 'servicio' and id_autor = '00000000-0000-0000-0000-0000000000ad'), 0, 'el registro no recibio nada');

-- Cada recurso se aplica con el valor real; otro administrador no usa la confirmacion ajena.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select public.crear_confirmacion('hash-4', 'servicio', (select id from public.servicio where nombre = 'Ensayo'), 'Ensayo',
  '{"tarifa_hora": {"anterior": "40.00", "nuevo": "55.50"}, "monto_fijo": {"anterior": "0.00", "nuevo": "3.00"}}', 10);
select public.crear_confirmacion('hash-5', 'especialista', (select id from public.especialista where nombre = 'Ejecutante'), 'Ejecutante',
  '{"unidad": {"anterior": "hora", "nuevo": "lapso_30"}, "monto_variable": {"anterior": "40.00", "nuevo": "41.00"}}', 10);
select public.crear_confirmacion('hash-6', 'recargos', null, 'Recargos',
  '{"noche.desde": {"anterior": "20:00", "nuevo": "21:30"}, "feriado.porcentaje": {"anterior": "30.00", "nuevo": "35.00"}}', 10);
select public.crear_confirmacion('hash-7', 'parametros', null, 'Parametros',
  '{"horas_nivel_1": {"anterior": "48", "nuevo": "72"}}', 10);
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ae","role":"authenticated"}', true);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'hash-4'))$$, '55000', null, 'B no aplica la confirmacion de A');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_cambio_confirmado(id) from public.confirmacion_cambio where hash_token in ('hash-4', 'hash-5', 'hash-6', 'hash-7')$$, 'A aplica servicio, especialista, recargos y parametros');
reset role;
select is((select tarifa_hora::text || '/' || monto_fijo::text from public.servicio where nombre = 'Ensayo'), '55.50/3.00', 'servicio aplicado');
select is((select unidad || '/' || monto_variable::text from public.especialista where nombre = 'Ejecutante'), 'lapso_30/41.00', 'especialista aplicado');
select is((select to_char(desde, 'HH24:MI') || '/' || porcentaje::text from public.recargo where tipo = 'noche'), '21:30/25.00', 'noche: solo cambio desde');
select is((select porcentaje::text from public.recargo where tipo = 'feriado'), '35.00', 'feriado aplicado');
select is((select valor from public.parametro where clave = 'horas_nivel_1'), 72, 'parametro aplicado');

select * from finish();
rollback;
