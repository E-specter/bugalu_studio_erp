begin;
create extension if not exists pgtap with schema extensions;
select plan(85);

-- RF-15 etapa A: rol profesional, especialidades, perfiles, precios, horarios y foto (CA-01 a CA-05, CA-16 en lo de A).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{"nombre":"Admin"}'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p1@t.pe', '{"nombre":"Pablo Uno"}'),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p2@t.pe', '{"nombre":"Paula Dos"}'),
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe', '{"nombre":"Clara Cliente"}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 's1@t.pe', '{"nombre":"Sergio Personal"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';

-- Datos de otras areas, para comprobar que el profesional no ve nada de ellas.
insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2099-03-01 10:00-05', '2099-03-01 11:00-05', 100, '2099-01-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo' limit 1;
insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence)
select '00000000-0000-0000-0000-0000000000c1', r.id, 'nivel_1', 10, 10, now() + interval '5 days' from public.reserva r
where r.id_cliente = '00000000-0000-0000-0000-0000000000c1';
insert into public.registro_cambio (id_autor, autor_nombre, recurso, nombre_recurso, campo, anterior, nuevo)
values ('00000000-0000-0000-0000-0000000000ad', 'Admin', 'impuestos', 'Impuestos', 'porcentaje_igv', '18.00', '18.00');
insert into public.especialidad_asesoria (id, nombre) values
  ('ee000000-0000-0000-0000-000000000001', 'Ingenieria de mezcla'),
  ('ee000000-0000-0000-0000-000000000002', 'Produccion'),
  ('ee000000-0000-0000-0000-000000000003', 'Coros'),
  ('ee000000-0000-0000-0000-000000000004', 'Guitarra'),
  ('ee000000-0000-0000-0000-000000000005', 'Bajo'),
  ('ee000000-0000-0000-0000-000000000006', 'Bateria'),
  ('ee000000-0000-0000-0000-000000000007', 'Antigua');
update public.especialidad_asesoria set activa = false where id = 'ee000000-0000-0000-0000-000000000007';

-- CA-01: el rol existe y asignarlo crea el perfil inactivo.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b1', 'profesional', null)$$, 'el administrador asigna el rol profesional');
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b2', 'profesional', null)$$, 'y a otra cuenta');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000c1', 'jefe', null)$$, '23514', null, 'un rol fuera del catalogo sigue rechazado');
select is((select count(*)::int from public.perfil_profesional where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2') and not activo), 2, 'nacen los dos perfiles, inactivos');
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b1', 'profesional', null)$$, 'asignarlo de nuevo no duplica ni falla');
select is((select count(*)::int from public.perfil_profesional), 2, 'sigue habiendo dos perfiles');

-- CA-02: especialidades.
select lives_ok($$insert into public.especialidad_asesoria (nombre) values ('Mastering')$$, 'el administrador crea una especialidad');
select throws_ok($$insert into public.especialidad_asesoria (nombre) values ('INGENIERÍA DE MEZCLA')$$, '23505', null, 'duplicada sin distinguir mayusculas ni tildes');
select throws_ok($$insert into public.especialidad_asesoria (nombre) values ('X')$$, '23514', null, 'menos de 2 caracteres');
select throws_ok($$insert into public.especialidad_asesoria (nombre) values (repeat('x', 61))$$, '23514', null, 'mas de 60 caracteres');
select throws_ok($$delete from public.especialidad_asesoria where nombre = 'Mastering'$$, '42501', null, 'no se borran');
select lives_ok($$update public.especialidad_asesoria set activa = false where nombre = 'Mastering'$$, 'se desactivan');

-- Perfil: el profesional edita lo suyo, no `activo`, no precios, no lo ajeno.
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$update public.perfil_profesional set presentacion = 'Hola', nombre_artistico = 'Pab', redes = '[{"red":"instagram","valor":"@pab"}]' where id = '00000000-0000-0000-0000-0000000000b1'$$, 'el profesional edita su perfil');
select is((select presentacion from public.perfil_profesional where id = '00000000-0000-0000-0000-0000000000b1'), 'Hola', 'y quedo guardado');
select throws_ok($$update public.perfil_profesional set activo = true where id = '00000000-0000-0000-0000-0000000000b1'$$, '42501', null, 'no se activa solo');
select throws_ok($$update public.perfil_profesional set presentacion = repeat('x', 601) where id = '00000000-0000-0000-0000-0000000000b1'$$, '23514', null, 'presentacion hasta 600');
select throws_ok($$update public.perfil_profesional set nombre_artistico = repeat('x', 81) where id = '00000000-0000-0000-0000-0000000000b1'$$, '23514', null, 'nombre artistico hasta 80');
select throws_ok($$update public.perfil_profesional set redes = '[1,2,3,4,5,6]' where id = '00000000-0000-0000-0000-0000000000b1'$$, '23514', null, 'redes hasta 5');
select lives_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b1', array['ee000000-0000-0000-0000-000000000001', 'ee000000-0000-0000-0000-000000000002']::uuid[])$$, 'elige sus especialidades');
select throws_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b1', array[]::uuid[])$$, '22023', null, 'al menos una');
select throws_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b1', array['ee000000-0000-0000-0000-000000000001','ee000000-0000-0000-0000-000000000002','ee000000-0000-0000-0000-000000000003','ee000000-0000-0000-0000-000000000004','ee000000-0000-0000-0000-000000000005','ee000000-0000-0000-0000-000000000006']::uuid[])$$, '22023', null, 'como maximo cinco');
select throws_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b1', array['ee000000-0000-0000-0000-000000000007']::uuid[])$$, '22023', null, 'una desactivada no se elige');
select is((select count(*)::int from public.perfil_especialidad where id_profesional = '00000000-0000-0000-0000-0000000000b1'), 2, 'las rechazadas no tocaron las elegidas');
select throws_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b2', array['ee000000-0000-0000-0000-000000000001']::uuid[])$$, '42501', null, 'no cambia las especialidades de otro');
select throws_ok($$insert into public.precio_asesoria (id_profesional, minutos, precio) values ('00000000-0000-0000-0000-0000000000b1', 30, 10)$$, '42501', null, 'no escribe precios');
select throws_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b1', true)$$, '42501', null, 'no cambia su estado');
select throws_ok($$select public.crear_confirmacion('h', 'profesional', '00000000-0000-0000-0000-0000000000b1', 'x', '{"precio_30":{"anterior":"no_ofrece","nuevo":"1.00"}}'::jsonb, 10)$$, '42501', null, 'no crea confirmaciones de cambio sensible');
update public.perfil_profesional set presentacion = 'Hackeada' where id = '00000000-0000-0000-0000-0000000000b2';
reset role;
select is((select presentacion from public.perfil_profesional where id = '00000000-0000-0000-0000-0000000000b2'), null, 'el perfil ajeno queda intacto');

-- Precios por el flujo sensible, y publicacion (CA-03, CA-04).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.crear_confirmacion('h1', 'profesional', '00000000-0000-0000-0000-0000000000b1', 'Pablo Uno',
  '{"precio_30":{"anterior":"no_ofrece","nuevo":"50.00"},"precio_60":{"anterior":"no_ofrece","nuevo":"90.00"}}'::jsonb, 10)$$, 'el administrador crea la confirmacion de los precios');
select lives_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'h1'))$$, 'el administrador aplica los precios confirmados');
select is((select string_agg(minutos || '=' || precio, ',' order by minutos) from public.precio_asesoria where id_profesional = '00000000-0000-0000-0000-0000000000b1'), '30=50.00,60=90.00', 'quedan los dos precios');
select is((select count(*)::int from public.registro_cambio where id_recurso = '00000000-0000-0000-0000-0000000000b1' and campo in ('precio_30', 'precio_60') and anterior = 'no_ofrece'), 2, 'el registro de cambios guarda cada campo');
select lives_ok($$select public.crear_confirmacion('h2', 'profesional', '00000000-0000-0000-0000-0000000000b1', 'Pablo Uno', '{"precio_30":{"anterior":"45.00","nuevo":"40.00"}}'::jsonb, 10)$$, 'confirmacion h2');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'h2'))$$, '40001', null, 'un anterior que no es el real se rechaza');
select lives_ok($$select public.crear_confirmacion('h3', 'profesional', '00000000-0000-0000-0000-0000000000b1', 'Pablo Uno', '{"precio_60":{"anterior":"90.00","nuevo":"no_ofrece"}}'::jsonb, 10)$$, 'confirmacion h3');
select lives_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'h3'))$$, 'null = no ofrece: se quita el precio');
select is((select count(*)::int from public.precio_asesoria where id_profesional = '00000000-0000-0000-0000-0000000000b1'), 1, 'solo queda el de 30');
select lives_ok($$select public.crear_confirmacion('h4', 'profesional', '00000000-0000-0000-0000-0000000000b1', 'Pablo Uno', '{"precio_30":{"anterior":"50.00","nuevo":"0.00"}}'::jsonb, 10)$$, 'confirmacion h4');
select throws_ok($$select public.aplicar_cambio_confirmado((select id from public.confirmacion_cambio where hash_token = 'h4'))$$, 'BG010', null, 'un precio de cero se rechaza');

select throws_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000ff', true)$$, 'P0002', null, 'perfil inexistente');
reset role;
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*)::int from public.perfil_profesional), 0, 'anon no ve un perfil inactivo');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b1', true)$$, 'el administrador activa el perfil');
reset role;
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*)::int from public.perfil_profesional), 1, 'anon ve el perfil publicado (activo, especialidad y precio)');
select is((select count(*)::int from public.precio_asesoria), 1, 'anon ve sus precios');
select is((select count(*)::int from public.perfil_especialidad), 2, 'anon ve sus especialidades');
select is((select count(*)::int from public.especialidad_asesoria where not activa), 0, 'anon no ve especialidades desactivadas');
select is(public.nombre_profesional('00000000-0000-0000-0000-0000000000b1'), 'Pablo Uno', 'anon lee el nombre de un perfil publicado');
select is(public.nombre_profesional('00000000-0000-0000-0000-0000000000b2'), null, 'pero no el de uno que no lo esta');
select throws_ok($$update public.perfil_profesional set presentacion = 'x'$$, '42501', null, 'anon no escribe perfiles');
select throws_ok($$select public.cambiar_estado_profesional('00000000-0000-0000-0000-0000000000b1', false)$$, '42501', null, 'anon no cambia estados');
reset role;
-- Sin especialidad activa deja de ser publico.
update public.especialidad_asesoria set activa = false where id in ('ee000000-0000-0000-0000-000000000001', 'ee000000-0000-0000-0000-000000000002');
set local role anon;
select is((select count(*)::int from public.perfil_profesional), 0, 'sin especialidades activas deja de ser publico');
reset role;
update public.especialidad_asesoria set activa = true where id in ('ee000000-0000-0000-0000-000000000001', 'ee000000-0000-0000-0000-000000000002');

-- Quien no es el dueno ni administrador: cliente y otro profesional ven solo lo publicado.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.perfil_profesional), 1, 'el cliente ve solo el publicado');
select throws_ok($$select public.reemplazar_especialidades('00000000-0000-0000-0000-0000000000b1', array['ee000000-0000-0000-0000-000000000001']::uuid[])$$, '42501', null, 'el cliente no cambia especialidades');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin) values ('00000000-0000-0000-0000-0000000000b1', now() + interval '2 days', now() + interval '3 days')$$, '42501', null, 'el cliente no publica horarios');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select is((select count(*)::int from public.perfil_profesional), 2, 'P2 ve el publicado y el propio');

-- CA-05: horarios.
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2099-02-01 10:00-05', '2099-02-01 12:00-05', '00000000-0000-0000-0000-0000000000b1')$$, 'el profesional publica un bloque futuro');
select lives_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2099-02-01 12:00-05', '2099-02-01 13:00-05', '00000000-0000-0000-0000-0000000000b1')$$, 'un bloque contiguo no se solapa');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2099-02-01 11:30-05', '2099-02-01 12:30-05', '00000000-0000-0000-0000-0000000000b1')$$, '23P01', null, 'un solape lo rechaza la base');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2099-02-02 10:10-05', '2099-02-02 11:00-05', '00000000-0000-0000-0000-0000000000b1')$$, '23514', null, 'multiplos de 30 minutos');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2099-02-02 10:00-05', '2099-02-02 10:00-05', '00000000-0000-0000-0000-0000000000b1')$$, '23514', null, 'fin posterior al inicio');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b1', '2020-02-02 10:00-05', '2020-02-02 11:00-05', '00000000-0000-0000-0000-0000000000b1')$$, '42501', null, 'no se publica en el pasado');
select throws_ok($$insert into public.horario_profesional (id_profesional, inicio, fin, id_publicador) values ('00000000-0000-0000-0000-0000000000b2', '2099-02-05 10:00-05', '2099-02-05 11:00-05', '00000000-0000-0000-0000-0000000000b1')$$, '42501', null, 'no publica horarios de otro profesional');
select is((select count(*)::int from public.horario_profesional), 2, 'solo quedaron los dos bloques validos');
reset role;
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*)::int from public.horario_profesional), 2, 'anon ve los horarios del perfil publicado');
select throws_ok($$select public.retirar_horario((select id from public.horario_profesional limit 1))$$, '42501', null, 'anon no retira horarios');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select throws_ok($$select public.retirar_horario((select id from public.horario_profesional limit 1))$$, '42501', null, 'otro profesional no retira horarios ajenos');
reset role;
select is((select count(*)::int from public.horario_profesional), 2, 'los horarios ajenos quedan intactos');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$select public.retirar_horario((select id from public.horario_profesional order by inicio limit 1))$$, 'el profesional retira un bloque suyo');
select is((select count(*)::int from public.horario_profesional), 1, 'y desaparece');
select throws_ok($$select public.retirar_horario('00000000-0000-0000-0000-0000000000ff')$$, 'P0002', null, 'bloque inexistente');

-- CA-01 y CA-16: el profesional no recibe acceso de personal ni de administrador en el resto del sistema.
select is((select count(*)::int from public.reserva), 0, 'no ve reservas');
select is((select count(*)::int from public.credito), 0, 'no ve creditos');
select is((select count(*)::int from public.registro_cambio), 0, 'no ve el registro de cambios');
select is((select count(*)::int from public.usuario), 1, 'solo ve su propia cuenta');
select is((select count(*)::int from public.hoja_reclamacion), 0, 'no ve reclamaciones');
select is((select count(*)::int from public.comprobante_pago), 0, 'no ve pagos');
select ok(not public.es_personal() and not public.es_administrador(), 'no es personal ni administrador');
select throws_ok($$insert into public.franja_sala (id_sala, inicio, fin) select id, '2099-05-01 10:00-05', '2099-05-01 12:00-05' from public.sala_tecnica limit 1$$, '42501', null, 'no publica franjas de sala');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b1', 'administrador', null)$$, '42501', null, 'no se asigna roles');
select throws_ok($$update public.parametro set valor = valor + 1 where clave = 'anticipacion_minima_horas'$$, '42501', null, 'no cambia parametros');
reset role;

-- Perfil de un administrador (decision 8).
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.crear_perfil_de_usuario('00000000-0000-0000-0000-0000000000ad')$$, '42501', null, 'un cliente no crea perfiles');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.crear_perfil_de_usuario('00000000-0000-0000-0000-0000000000ad')$$, 'el administrador crea el perfil de un administrador');
select throws_ok($$select public.crear_perfil_de_usuario('00000000-0000-0000-0000-0000000000ad')$$, 'P0001', 'perfil_existente', 'una sola vez');
select throws_ok($$select public.crear_perfil_de_usuario('00000000-0000-0000-0000-0000000000c1')$$, 'P0001', 'rol_no_admitido', 'no para un cliente');
select throws_ok($$select public.crear_perfil_de_usuario('00000000-0000-0000-0000-0000000000ff')$$, 'P0002', null, 'usuario inexistente');

select * from finish();
rollback;
