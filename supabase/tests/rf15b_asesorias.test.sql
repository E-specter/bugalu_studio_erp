begin;
create extension if not exists pgtap with schema extensions;
select plan(61);

-- RF-15 etapa B (backend B1): la asesoria es una fila de `reserva` con tipo 'asesoria' mas la fila 1:1 de `asesoria`.
-- CA-06 a CA-09, CA-16.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{"nombre":"Admin"}'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p1@t.pe', '{"nombre":"Pablo Uno"}'),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p2@t.pe', '{"nombre":"Paula Dos"}'),
  ('00000000-0000-0000-0000-0000000000b3', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p3@t.pe', '{"nombre":"Pedro Tres"}'),
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe', '{"nombre":"Clara Cliente"}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c2@t.pe', '{"nombre":"Carlos Cliente"}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 's1@t.pe', '{"nombre":"Sergio Personal"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'profesional' where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-0000000000b3');
select public.crear_perfil_profesional(id) from public.usuario where rol = 'profesional';
insert into public.especialidad_asesoria (id, nombre) values ('ee000000-0000-0000-0000-000000000001', 'Mezcla');
insert into public.perfil_especialidad (id_profesional, id_especialidad)
  select id, 'ee000000-0000-0000-0000-000000000001' from public.perfil_profesional where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
insert into public.precio_asesoria (id_profesional, minutos, precio)
  select id, m, 50 * m / 30 from public.perfil_profesional, (values (30), (60)) v(m) where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
update public.perfil_profesional set activo = true where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
insert into public.horario_profesional (id_profesional, inicio, fin)
  select id, '2099-03-01 09:00-05', '2099-03-01 13:00-05' from public.perfil_profesional;
insert into public.horario_profesional (id_profesional, inicio, fin) values
  ('00000000-0000-0000-0000-0000000000b1', '2020-01-01 09:00-05', '2020-01-01 13:00-05');

-- Una reserva de sala sigue igual: tipo 'sala', folio R-, margen de 30 min.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select 'aa000000-0000-0000-0000-00000000005a', '00000000-0000-0000-0000-0000000000c1', sa.id, se.id,
       '2099-03-01 10:00-05', '2099-03-01 11:00-05', 100, '2099-01-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo' limit 1;
select is((select tipo from public.reserva where id = 'aa000000-0000-0000-0000-00000000005a'), 'sala', 'una reserva de sala nace con tipo sala');
select matches((select folio from public.reserva where id = 'aa000000-0000-0000-0000-00000000005a'), '^R-\d{4}-\d{5}$', 'y con folio R-');
select is((select fin_buffer - fin from public.reserva where id = 'aa000000-0000-0000-0000-00000000005a'), interval '30 minutes', 'y conserva el margen de 30 minutos');

-- Coherencia del tipo y estados (en la base, no solo en la API).
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, id_sala, inicio, fin, total, vence_pago)
  select 'asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', id, '2099-03-01 12:30-05', '2099-03-01 13:00-05', 50, '2099-01-01' from public.sala_tecnica limit 1$$,
  '23514', null, 'una asesoria no lleva sala');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago, estado)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 12:30-05', '2099-03-01 13:00-05', 50, '2099-01-01', 'en_curso')$$,
  '23514', null, 'una asesoria no pasa por en_curso');
select throws_ok($$update public.reserva set estado = 'realizada' where id = 'aa000000-0000-0000-0000-00000000005a'$$, '23514', null, 'realizada es solo de asesorias');

create temp table t (k text primary key, id uuid not null);
grant all on t to authenticated;

-- CA-06: el cliente agenda (reserva + asesoria + cuota unica) con folio A-.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$with i as (insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 10:00-05', '2099-03-01 10:30-05', 50, '2099-02-01') returning id) insert into t select 'a1', id from i$$, 'el cliente agenda una asesoria');
select lives_ok($$insert into public.asesoria (id_reserva, modalidad) values ((select id from t where k = 'a1'), 'virtual')$$, 'y su fila de asesoria');
select matches((select folio from public.reserva where id = (select id from t where k = 'a1')), '^A-\d{4}-\d{5}$', 'folio A-AAAA-NNNNN');
select ok((select fin_buffer = fin and id_sala is null and id_servicio is null and estado = 'pre_reservada' and tipo = 'asesoria' from public.reserva where id = (select id from t where k = 'a1')), 'sin margen, sin sala ni servicio, pre_reservada');

-- CA-07: exclusion por profesional en las no canceladas, sin margen entre asesorias.
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 10:00-05', '2099-03-01 10:30-05', 50, '2099-02-01')$$, '23P01', null, 'el mismo horario con el mismo profesional se rechaza');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 10:00-05', '2099-03-01 11:00-05', 90, '2099-02-01')$$, '23P01', null, 'un solape parcial tambien');
select lives_ok($$with i as (insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 10:30-05', '2099-03-01 11:00-05', 50, '2099-02-01') returning id) insert into t select 'a2', id from i$$, 'justo despues cabe: no hay margen entre asesorias');
select lives_ok($$insert into public.asesoria (id_reserva, modalidad) values ((select id from t where k = 'a2'), 'presencial')$$, 'su fila de asesoria');
select lives_ok($$with i as (insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b2', '2099-03-01 10:00-05', '2099-03-01 10:30-05', 50, '2099-02-01') returning id) insert into t select 'b1', id from i$$, 'a la misma hora con otro profesional si');
select lives_ok($$insert into public.asesoria (id_reserva, modalidad) values ((select id from t where k = 'b1'), 'virtual')$$, 'su fila de asesoria');
select lives_ok($$insert into public.cuota (id_reserva, hito, monto) values ((select id from t where k = 'a2'), 'al_reservar', 50)$$, 'una cuota unica al reservar');

-- Barreras de la base al agendar: horario publicado, duracion ofrecida, perfil publicado.
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 14:00-05', '2099-03-01 14:30-05', 50, '2099-02-01')$$, 'P0001', 'fuera_de_horario', 'fuera de los bloques publicados');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 11:00-05', '2099-03-01 12:30-05', 50, '2099-02-01')$$, 'P0001', 'duracion_no_ofrecida', 'solo 30 o 60 minutos');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b3', '2099-03-01 11:00-05', '2099-03-01 11:30-05', 50, '2099-02-01')$$, 'P0001', 'profesional_no_publicado', 'un perfil que no esta publicado no agenda');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 11:00-05', '2099-03-01 11:30-05', 50, '2099-02-01')$$, '42501', null, 'nadie agenda a nombre de otro');

-- Estados solo por funciones: el cliente no confirma su asesoria.
update public.reserva set estado = 'confirmada' where id = (select id from t where k = 'a2');
select is((select estado from public.reserva where id = (select id from t where k = 'a2')), 'pre_reservada', 'el cliente no cambia el estado (la fila queda intacta)');
select throws_ok($$select notas from public.asesoria$$, '42501', null, 'las notas internas no se leen con el rol del cliente');
select throws_ok($$update public.asesoria set lugar = 'mi casa' where id_reserva = (select id from t where k = 'a2')$$, '42501', null, 'el cliente no edita el encuentro');

-- RLS: cada quien ve lo suyo.
select is((select count(*)::int from public.reserva where tipo = 'asesoria'), 3, 'el cliente ve sus asesorias');
select is((select count(*)::int from public.asesoria), 3, 'y sus filas de asesoria');
select is((select count(*)::int from public.cuota), 1, 'y su cuota');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva where tipo = 'asesoria'), 0, 'otro cliente no ve ninguna');
select is((select count(*)::int from public.asesoria) + (select count(*)::int from public.cuota), 0, 'ni sus filas ni sus cuotas');
select throws_ok($$insert into public.asesoria (id_reserva, modalidad) values ((select id from t where k = 'a1'), 'virtual')$$, '42501', null, 'ni agrega filas a una asesoria ajena');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select is((select string_agg(id_profesional::text, ',') from public.reserva where tipo = 'asesoria'), '00000000-0000-0000-0000-0000000000b2', 'el profesional ve solo las suyas');
select is((select count(*)::int from public.reserva where tipo = 'sala'), 0, 'y ninguna reserva de sala');
select is((select count(*)::int from public.cuota), 0, 'no ve cuotas');
select throws_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 12:00-05', '2099-03-01 12:30-05', 50, '2099-02-01')$$, '42501', null, 'el profesional no agenda');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva where tipo = 'asesoria'), 0, 'el personal no ve asesorias');
select is((select count(*)::int from public.reserva where id = 'aa000000-0000-0000-0000-00000000005a'), 1, 'pero si las reservas de sala');
select is((select count(*)::int from public.cuota where id_reserva in (select id from t)), 0, 'ni cuotas de asesoria');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva where tipo = 'asesoria'), 3, 'el administrador las ve todas');
reset role;
set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select 1 from public.reserva$$, '42501', null, 'anon no lee reservas');
select throws_ok($$select 1 from public.asesoria$$, '42501', null, 'ni asesorias');
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b1', '2099-03-01 00:00-05', '2099-03-02 00:00-05')), 2, 'anon ve los tramos ocupados del profesional');
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b1', '2099-03-01 00:00-05', '2099-03-02 00:00-05') where propia), 0, 'sin decir de quien');
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b3', '2099-03-01 00:00-05', '2099-03-02 00:00-05')), 0, 'un perfil no publicado no muestra nada');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b1', '2099-03-01 00:00-05', '2099-03-02 00:00-05') where propia), 2, 'el cliente reconoce las suyas con propia');

-- CA-08: caducidad. Una pre_reservada vencida y sin capturas libera el horario al agendar otra.
reset role;
insert into public.reserva (id, tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
values ('aa000000-0000-0000-0000-0000000000a3', 'asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 12:00-05', '2099-03-01 12:30-05', 50, now() - interval '1 hour');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select lives_ok($$with i as (insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 12:00-05', '2099-03-01 12:30-05', 50, '2099-02-01') returning id) insert into t select 'a4', id from i$$, 'agendar sobre una vencida: la base la caduca y el horario se libera');
reset role;
select is((select estado || '/' || motivo_cancelacion from public.reserva where id = 'aa000000-0000-0000-0000-0000000000a3'), 'cancelada/caducada', 'la vencida quedo cancelada por caducada');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_caducada' and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-0000000000a3'), 1, 'y su cliente recibio el aviso');
-- Una cancelada no bloquea el horario.
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = (select id from t where k = 'a4');
select lives_ok($$insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago)
  values ('asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2099-03-01 12:00-05', '2099-03-01 12:30-05', 50, '2099-02-01')$$, 'una cancelada no bloquea el horario');

-- CA-09: lugar o enlace por funcion, solo su profesional o el administrador, mientras viva y antes de su fin.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$select public.cambiar_encuentro((select id from t where k = 'a2'), 'presencial', 'Av. Siempre Viva 123', null)$$, 'su profesional registra el lugar');
reset role;
select is((select lugar from public.asesoria where id_reserva = (select id from t where k = 'a2')), 'Av. Siempre Viva 123', 'queda guardado');
select is((select count(*)::int from public.notificacion where tipo = 'asesoria_encuentro_cambiado' and datos ->> 'id_reserva' = (select id::text from t where k = 'a2') and destinatario in ('p1@t.pe', 'c1@t.pe')), 2, 'avisa al cliente y al profesional');
select is((select ubicacion from public.datos_reserva_para_correo(array[(select id from public.notificacion where tipo = 'asesoria_encuentro_cambiado' and destinatario = 'c1@t.pe')])), 'Av. Siempre Viva 123', 'el evento de calendario recibe el lugar');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.cambiar_encuentro((select id from t where k = 'a2'), 'presencial', 'Otro lugar', null)$$, '42501', null, 'el cliente no lo edita: se lo pide al profesional');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select throws_ok($$select public.cambiar_encuentro((select id from t where k = 'a2'), 'presencial', 'Otro lugar', null)$$, 'P0002', null, 'otro profesional no ve la asesoria');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.cambiar_encuentro((select id from t where k = 'a2'), 'virtual', null, 'http://evil.example/x')$$, '23514', null, 'el enlace es de Meet con https');
select lives_ok($$select public.cambiar_encuentro((select id from t where k = 'a2'), 'virtual', null, 'https://meet.google.com/abc-defg-hij')$$, 'el administrador pone el enlace');
select throws_ok($$select public.cambiar_encuentro((select id from t where k = 'a4'), 'virtual', null, 'https://meet.google.com/abc-defg-hij')$$, 'P0001', 'no_editable', 'una cancelada no se edita');
reset role;
insert into public.reserva (id, tipo, id_cliente, id_profesional, inicio, fin, total, vence_pago, estado)
values ('aa000000-0000-0000-0000-0000000000a5', 'asesoria', '00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b1', '2020-01-01 10:00-05', '2020-01-01 10:30-05', 50, '2019-12-01', 'confirmada');
insert into public.asesoria (id_reserva, modalidad) values ('aa000000-0000-0000-0000-0000000000a5', 'virtual');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.cambiar_encuentro('aa000000-0000-0000-0000-0000000000a5', 'virtual', null, 'https://meet.google.com/abc-defg-hij')$$, 'P0001', 'no_editable', 'tampoco despues de su fin');
reset role;

-- avanzar_reservas no mueve una asesoria confirmada (la cierra su profesional).
select public.avanzar_reservas();
select is((select estado from public.reserva where id = 'aa000000-0000-0000-0000-0000000000a5'), 'confirmada', 'una asesoria confirmada no avanza sola');

-- Al confirmarse la asesoria, su profesional recibe el aviso con el evento.
update public.reserva set estado = 'confirmada' where id = (select id from t where k = 'a2');
select is((select count(*)::int from public.notificacion where tipo = 'asesoria_confirmada_profesional' and destinatario = 'p1@t.pe' and datos ->> 'id_reserva' = (select id::text from t where k = 'a2')), 1, 'confirmar avisa al profesional');

-- El aviso de creacion (datos para pagar) tambien existe para la asesoria.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select public.encolar_aviso_reserva((select id from t where k = 'a1'));
reset role;
select is((select datos ->> 'servicio' from public.notificacion where tipo = 'reserva_creada' and datos ->> 'id_reserva' = (select id::text from t where k = 'a1')), 'Asesoría artística', 'el aviso de creacion nombra la asesoria');

select * from finish();
rollback;
