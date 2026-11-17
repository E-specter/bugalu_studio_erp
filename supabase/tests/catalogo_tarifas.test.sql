begin;
create extension if not exists pgtap with schema extensions;
select plan(51);

select has_table('public', t, 'existe ' || t)
from unnest(array['sala_tecnica','servicio','especialista','servicio_especialista','recargo','feriado','parametro']) as t;

-- Usuarios: CLI cliente, ADM administrador
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
insert into public.feriado (fecha, nombre) values ('2026-12-25', 'Navidad');

-- Restricciones de negocio
select throws_ok($$insert into public.servicio (nombre, categoria, ocupa_sala, tarifa_hora) values ('X','otra',true,1)$$, '23514', null, 'categoria fuera de la lista');
select throws_ok($$insert into public.servicio (nombre, categoria, ocupa_sala, tarifa_hora) values ('X','ensayo',true,-1)$$, '23514', null, 'tarifa negativa');
select throws_ok($$insert into public.especialista (nombre, monto_fijo, monto_variable, unidad) values ('X',0,0,'dia')$$, '23514', null, 'unidad invalida');
select throws_ok($$insert into public.especialista (nombre, monto_fijo, monto_variable, unidad) values ('X',-1,0,'hora')$$, '23514', null, 'monto fijo negativo');
select throws_ok($$update public.recargo set porcentaje = 301 where tipo = 'feriado'$$, '23514', null, 'porcentaje sobre 300');
select throws_ok($$update public.recargo set desde = null where tipo = 'noche'$$, '23514', null, 'la noche exige desde y hasta');
select throws_ok($$update public.recargo set desde = '08:00', hasta = '09:00' where tipo = 'feriado'$$, '23514', null, 'desde y hasta solo para noche');
select throws_ok($$insert into public.recargo (tipo, porcentaje, desde, hasta) values ('noche', 10, '21:00', '05:00')$$, '23505', null, 'un recargo por tipo');
select throws_ok($$insert into public.parametro (clave, valor) values ('otra', 1)$$, '23514', null, 'clave de parametro desconocida');
select throws_ok($$update public.parametro set valor = 0 where clave = 'dias_limite_pago'$$, '23514', null, 'valor de parametro positivo');

-- Datos iniciales
select is((select count(*)::int from public.sala_tecnica where nombre = 'Sala principal' and sede = 'La Molina' and activa), 1, 'sala inicial');
select is((select count(*)::int from public.servicio), 7, 'siete servicios');
select is((select count(*)::int from public.servicio where categoria = 'posproduccion' and not ocupa_sala), 2, 'mezcla y masterizacion no ocupan sala');
select is((select count(*)::int from public.servicio where categoria <> 'posproduccion' and ocupa_sala), 5, 'el resto ocupa sala');
select is((select count(*)::int from public.especialista), 4, 'cuatro especialistas');
select is((select count(*)::int from public.servicio_especialista se join public.especialista e on e.id = se.id_especialista
  where e.nombre = 'Ingeniero de sonido'), 4, 'ingeniero por defecto en grabacion y live');
select is((select count(*)::int from public.recargo), 3, 'tres recargos');
select is((select string_agg(clave || '=' || valor, ',' order by clave) from public.parametro),
  'anticipacion_maxima_semanas=8,anticipacion_minima_horas=2,dias_limite_pago=3,dias_vigencia_credito=30,horas_limite_pago=1,horas_nivel_1=48,horas_nivel_2=24,minutos_tolerancia_inasistencia=15,porcentaje_adelanto=50,porcentaje_penalizacion_nivel_2=25,reprogramaciones_nivel_1=2,reprogramaciones_nivel_2=1', 'parametros iniciales');

-- anon: lee lo publico, no parametro, no escribe
set local role anon;
select is((select count(*)::int from public.servicio), 7, 'anon lee servicios');
select is((select count(*)::int from public.recargo), 3, 'anon lee recargos');
select is((select count(*)::int from public.feriado), 1, 'anon lee feriados');
select throws_ok($$select * from public.parametro$$, '42501', null, 'anon no lee parametro');
select throws_ok($$insert into public.servicio (nombre, categoria, ocupa_sala, tarifa_hora) values ('X','ensayo',true,1)$$, '42501', null, 'anon no inserta');

-- cliente: lee lo publico, no parametro, no escribe, filas intactas
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.sala_tecnica), 1, 'cliente lee la sala');
select is((select count(*)::int from public.especialista), 4, 'cliente lee especialistas');
select is((select count(*)::int from public.parametro), 0, 'cliente no ve parametro');
select throws_ok($$update public.servicio set tarifa_hora = 1 where nombre = 'Ensayo'$$, '42501', null, 'cliente no actualiza la tarifa');
select throws_ok($$update public.parametro set valor = 99$$, '42501', null, 'cliente no actualiza parametro');
select throws_ok($$update public.recargo set porcentaje = 1$$, '42501', null, 'cliente no actualiza recargo');
select lives_ok($$delete from public.feriado$$, 'cliente delete de feriado no afecta filas');
select throws_ok($$insert into public.servicio (nombre, categoria, ocupa_sala, tarifa_hora) values ('X','ensayo',true,1)$$, '42501', null, 'cliente no inserta servicio');
select throws_ok($$insert into public.feriado (fecha, nombre) values ('2026-12-26','X')$$, '42501', null, 'cliente no inserta feriado');
select throws_ok($$delete from public.servicio$$, '42501', null, 'cliente no borra servicios');
reset role;
select isnt((select tarifa_hora from public.servicio where nombre = 'Ensayo'), 1.00, 'tarifa intacta tras el cliente');
select is((select count(*)::int from public.parametro where valor = 99), 0, 'parametro intacto tras el cliente');
select is((select count(*)::int from public.recargo where porcentaje = 1), 0, 'recargo intacto tras el cliente');
select is((select count(*)::int from public.feriado), 1, 'feriado intacto tras el cliente');

-- administrador
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.parametro), 12, 'admin lee parametro');
select throws_ok($$update public.servicio set tarifa_hora = 99.00 where nombre = 'Ensayo'$$, '42501', null, 'admin no actualiza la tarifa directo (barrera RF-20)');
select lives_ok($$update public.servicio set activo = true where nombre = 'Ensayo'$$, 'admin actualiza campos no sensibles');
select lives_ok($$select public.actualizar_parametro('anticipacion_minima_horas', 5)$$, 'admin actualiza un parametro no sensible');
select lives_ok($$insert into public.feriado (fecha, nombre) values ('2026-12-26','X')$$, 'admin inserta feriado');
select lives_ok($$delete from public.feriado where fecha = '2026-12-26'$$, 'admin borra feriado');
select throws_ok($$delete from public.servicio$$, '42501', null, 'admin no borra servicios');

select * from finish();
rollback;
