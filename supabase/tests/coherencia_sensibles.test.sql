begin;
create extension if not exists pgtap with schema extensions;
select plan(12);

-- RF-20 (auditoria A, ronda 2): la coherencia de los campos sensibles vive tambien en la base.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.configuracion_impuestos set porcentaje_igv = 18;
update public.recargo set porcentaje = 25, desde = '20:00', hasta = '06:00' where tipo = 'noche';
update public.parametro set valor = 48 where clave = 'horas_nivel_1';
update public.parametro set valor = 24 where clave = 'horas_nivel_2';
update public.parametro set valor = 50 where clave = 'porcentaje_adelanto';
create temp table registro_previo as select count(*)::int as n from public.registro_cambio;
grant select on registro_previo to authenticated;

-- Una noche sin duracion no existe, ni por SQL directo.
select throws_ok($$update public.recargo set desde = '06:00', hasta = '06:00' where tipo = 'noche'$$, '23514', null, 'la noche no puede tener desde = hasta');
select is((select to_char(desde, 'HH24:MI') || '-' || to_char(hasta, 'HH24:MI') from public.recargo where tipo = 'noche'), '20:00-06:00', 'la noche sigue intacta');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);

-- Confirmaciones con un anterior verdadero y un nuevo incoherente: la base no las aplica (BG010).
select public.crear_confirmacion('c1', 'parametros', null, 'Parametros', '{"horas_nivel_1": {"anterior": "48", "nuevo": "20"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'c1'))$$, 'BG010', null, 'horas_nivel_1 <= horas_nivel_2 no se aplica');
select public.crear_confirmacion('c2', 'parametros', null, 'Parametros', '{"horas_nivel_2": {"anterior": "24", "nuevo": "48"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'c2'))$$, 'BG010', null, 'horas_nivel_2 = horas_nivel_1 no se aplica');
select public.crear_confirmacion('c3', 'parametros', null, 'Parametros', '{"porcentaje_adelanto": {"anterior": "50", "nuevo": "150"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'c3'))$$, 'BG010', null, 'un porcentaje sobre 100 no se aplica');
select public.crear_confirmacion('c4', 'impuestos', null, 'Impuestos', '{"porcentaje_igv": {"anterior": "18.00", "nuevo": "100.00"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'c4'))$$, 'BG010', null, 'un IGV fuera de 0-99.99 no se aplica');
select public.crear_confirmacion('c5', 'recargos', null, 'Recargos', '{"noche.desde": {"anterior": "20:00", "nuevo": "06:00"}}', 10);
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'c5'))$$, '23514', null, 'una noche sin duracion no se aplica (check de recargo)');
reset role;
select is((select valor from public.parametro where clave = 'horas_nivel_1'), 48, 'horas_nivel_1 intacto');
select is((select count(*)::int from public.registro_cambio), (select n from registro_previo), 'el registro no recibio nada');
select is((select count(*)::int from public.confirmacion_cambio where usada_en is not null), 0, 'ninguna confirmacion quedo consumida');

-- actualizar_parametro con una clave inexistente falla.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.actualizar_parametro('no_existe', 5)$$, 'P0002', null, 'una clave inexistente no se ignora');
select lives_ok($$select public.actualizar_parametro('anticipacion_minima_horas', 6)$$, 'una clave real sigue funcionando');
reset role;

select * from finish();
rollback;
