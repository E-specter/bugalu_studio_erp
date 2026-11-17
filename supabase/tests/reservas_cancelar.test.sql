begin;
create extension if not exists pgtap with schema extensions;
select plan(34);

-- RF-04: cancelar_reserva (RN-20), existe_reserva, plazos_pago y encolar_aviso_reserva.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Una reserva por dia: d01 libre de pagos (c1), d02 con cuota pagada (c1), d03 cancelada (c1), d04 finalizada (c1),
-- d05 de c2, d06 para el administrador (c1), d07 en curso (c1).
insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
select u.id, sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 50, d.estado, d.motivo, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('00000000-0000-0000-0000-0000000000c1'::uuid, '2027-05-01 10:00-05'::timestamptz, 'pre_reservada', null),
    ('00000000-0000-0000-0000-0000000000c1', '2027-05-02 10:00-05', 'pre_reservada', null),
    ('00000000-0000-0000-0000-0000000000c1', '2027-05-03 10:00-05', 'cancelada', 'cliente'),
    ('00000000-0000-0000-0000-0000000000c1', '2027-05-04 10:00-05', 'finalizada', null),
    ('00000000-0000-0000-0000-0000000000c2', '2027-05-05 10:00-05', 'pre_reservada', null),
    ('00000000-0000-0000-0000-0000000000c1', '2027-05-06 10:00-05', 'pre_reservada', null),
    ('00000000-0000-0000-0000-0000000000c1', '2027-05-07 10:00-05', 'en_curso', null)) as d(id_cliente, inicio, estado, motivo)
  join public.usuario u on u.id = d.id_cliente
where se.nombre = 'Ensayo';
insert into public.cuota (id_reserva, hito, monto, estado)
select id, 'al_reservar', 25, 'pagada' from public.reserva where inicio = '2027-05-02 10:00-05';

select has_function('public', 'cancelar_reserva', array['uuid', 'text', 'integer', 'text', 'timestamp with time zone'], 'existe cancelar_reserva');
select has_function('public', 'existe_reserva', array['uuid'], 'existe existe_reserva');
select has_function('public', 'plazos_pago', 'existe plazos_pago');
select has_function('public', 'encolar_aviso_reserva', array['uuid'], 'existe encolar_aviso_reserva');

-- anon: sin acceso a ninguna
set local role anon;
select throws_ok($$select public.cancelar_reserva(gen_random_uuid())$$, '42501', null, 'anon no cancela');
select throws_ok($$select public.existe_reserva(gen_random_uuid())$$, '42501', null, 'anon no consulta existe_reserva');
select throws_ok($$select * from public.plazos_pago()$$, '42501', null, 'anon no lee plazos_pago');
select throws_ok($$select public.encolar_aviso_reserva(gen_random_uuid())$$, '42501', null, 'anon no encola avisos');
reset role;

-- c1 (dueno)
create temp table antes as
  select id, inicio, fin, total, folio, id_cliente, vence_pago, md5(precio::text) as precio
  from public.reserva where id_cliente = '00000000-0000-0000-0000-0000000000c1' and inicio = '2027-05-01 10:00-05';
grant select on antes to authenticated;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-01 10:00-05'))$$, 'c1 cancela la suya sin pagos');
select is((select estado || '/' || motivo_cancelacion from public.reserva where inicio = '2027-05-01 10:00-05'), 'cancelada/cliente', 'queda cancelada con motivo cliente');
select is((select count(*)::int from public.reserva r join antes a using (id, inicio, fin, total, folio, id_cliente, vence_pago) where md5(r.precio::text) = a.precio), 1,
  'la cancelacion solo cambia estado y motivo');
select lives_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
  select auth.uid(), sa.id, se.id, '2027-05-01 10:00-05', '2027-05-01 11:00-05', 1, '2099-01-01'
  from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$, 'el tramo cancelado queda libre');
select throws_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-02 10:00-05'))$$, 'P0001', 'nivel_cambiado', 'con pagos sin nivel esperado: nivel_cambiado (RF-18)');
select throws_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-03 10:00-05'))$$, 'P0001', 'no_cancelable', 'ya cancelada: no_cancelable');
select throws_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-04 10:00-05'))$$, 'P0001', 'no_cancelable', 'finalizada: no_cancelable');
select throws_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-07 10:00-05'))$$, 'P0001', 'no_cancelable', 'en curso: no_cancelable');
select throws_ok($$select public.cancelar_reserva(gen_random_uuid())$$, 'P0002', null, 'inexistente: P0002');
reset role;
select is((select estado from public.reserva where inicio = '2027-05-02 10:00-05'), 'pre_reservada', 'la que tiene pagos sigue igual');

-- c1 no cancela la de c2 (se pasa el id como literal desde la conexion administradora)
select set_config('prueba.id_c2', (select id::text from public.reserva where inicio = '2027-05-05 10:00-05'), true);
select set_config('prueba.id_ad', (select id::text from public.reserva where inicio = '2027-05-06 10:00-05'), true);
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva(current_setting('prueba.id_c2')::uuid)$$, 'P0002', null, 'c1 no cancela la de c2: para el no existe (404)');
select is(public.existe_reserva(current_setting('prueba.id_c2')::uuid), true, 'existe_reserva ve la ajena sin darla');
select is(public.existe_reserva(gen_random_uuid()), false, 'existe_reserva falso si no existe');
select is((select dias from public.plazos_pago()), 3, 'plazos_pago: dias');
select is((select horas from public.plazos_pago()), 1, 'plazos_pago: horas');
select throws_ok($$select public.encolar_aviso_reserva(current_setting('prueba.id_c2')::uuid)$$, '42501', null, 'c1 no encola el aviso de la de c2');
select lives_ok($$select public.encolar_aviso_reserva(current_setting('prueba.id_ad')::uuid)$$, 'c1 encola el aviso de la suya');
select lives_ok($$select public.encolar_aviso_reserva(current_setting('prueba.id_ad')::uuid)$$, 'repetirlo no falla');
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'reserva_creada'), 1, 'un solo aviso por reserva');
select is((select destinatario from public.notificacion where tipo = 'reserva_creada'), 'cli@t.pe', 'el aviso va al correo del dueno');
select ok((select datos ? 'folio' and datos ? 'vence_pago' and datos ? 'inicio' from public.notificacion where tipo = 'reserva_creada'), 'el aviso lleva folio, inicio y fecha limite');
select is((select estado from public.reserva where inicio = '2027-05-05 10:00-05'), 'pre_reservada', 'la de c2 sigue intacta');

-- personal: no cancela; el administrador si (motivo administrador), pero tampoco con pagos
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva(current_setting('prueba.id_ad')::uuid)$$, '42501', null, 'el personal no cancela');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva(current_setting('prueba.id_ad')::uuid)$$, 'el administrador cancela la de otro');
select throws_ok($$select public.cancelar_reserva((select id from public.reserva where inicio = '2027-05-02 10:00-05'))$$, 'P0001', 'nota_requerida', 'el administrador con pagos necesita nota (D-11 v1)');
reset role;
select is((select estado || '/' || motivo_cancelacion from public.reserva where inicio = '2027-05-06 10:00-05'), 'cancelada/administrador', 'motivo administrador');

select * from finish();
rollback;
