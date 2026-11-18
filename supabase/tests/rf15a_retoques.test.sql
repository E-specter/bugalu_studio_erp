begin;
create extension if not exists pgtap with schema extensions;
select plan(16);

-- Retoques de la auditoria de RF-15 etapa A (ronda 2): asignar_rol a `profesional` solo si el usuario no deja
-- operaciones de cliente vivas (reservas vivas, creditos vigentes, pagos en validacion, devoluciones pendientes).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
select ('00000000-0000-0000-0000-0000000000' || n)::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
       n || '@t.pe', '{"nombre":"Usuario"}'
from unnest(array['ad', 'e0', 'd1', 'd2', 'd3', 'd4', 'd5']) as n;
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';

-- Una reserva por usuario d1..d5 (dia distinto); d2 confirmada; d3, d4 y d5 canceladas para dejar solo su otra operacion.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select ('00000000-0000-0000-0000-0000000001' || n)::uuid, ('00000000-0000-0000-0000-0000000000' || n)::uuid, sa.id, se.id,
       ('2099-03-0' || row_number() over () || ' 10:00-05')::timestamptz, ('2099-03-0' || row_number() over () || ' 11:00-05')::timestamptz,
       100, '2099-02-01'
from unnest(array['d1', 'd2', 'd3', 'd4', 'd5']) as n, public.sala_tecnica sa, public.servicio se
where se.nombre = 'Ensayo' and sa.id = (select id from public.sala_tecnica limit 1);
insert into public.cuota (id, id_reserva, hito, monto)
values ('00000000-0000-0000-0000-0000000002d4', '00000000-0000-0000-0000-0000000001d4', 'al_reservar', 50);
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d4"}', true);
insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
values ('00000000-0000-0000-0000-0000000002d4', '00000000-0000-0000-0000-0000000000d4', 'yape', 50, 'OP-1234',
        '00000000-0000-0000-0000-0000000000d4/x.png', 'image/png');
select set_config('request.jwt.claims', '', true);
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence)
values ('00000000-0000-0000-0000-0000000003d3', '00000000-0000-0000-0000-0000000000d3',
        '00000000-0000-0000-0000-0000000001d3', 'nivel_1', 10, 10, now() + interval '5 days');
insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado)
values ('00000000-0000-0000-0000-0000000001d5', '00000000-0000-0000-0000-0000000000d5', 'estudio', 'Quiero mi dinero', 10);
update public.reserva set estado = 'confirmada' where id = '00000000-0000-0000-0000-0000000001d2';
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente'
where id in ('00000000-0000-0000-0000-0000000001d3', '00000000-0000-0000-0000-0000000001d4', '00000000-0000-0000-0000-0000000001d5');

-- Cada usuario cuenta solo su operacion.
select is(public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d1'),
  '{"reservas_vivas":1,"creditos_vigentes":0,"pagos_en_validacion":0,"devoluciones_pendientes":0}'::jsonb, 'd1: una reserva pre_reservada');
select is((public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d2') ->> 'reservas_vivas')::int, 1, 'd2: una reserva confirmada');
select is((public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d3') ->> 'creditos_vigentes')::int, 1, 'd3: un credito vigente');
select is((public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d4') ->> 'pagos_en_validacion')::int, 1, 'd4: un pago en validacion');
select is((public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d5') ->> 'devoluciones_pendientes')::int, 1, 'd5: una devolucion pendiente');
select is((select count(*)::int from jsonb_each(public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000e0')) where value <> '0'),
  0, 'e0: sin operaciones');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d1', 'profesional', null)$$, 'BG003', null, 'reserva viva: 409 en la base');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d2', 'profesional', null)$$, 'BG003', null, 'reserva confirmada: bloquea');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d3', 'profesional', null)$$, 'BG003', null, 'credito vigente: bloquea');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d4', 'profesional', null)$$, 'BG003', null, 'pago en validacion: bloquea');
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d5', 'profesional', null)$$, 'BG003', null, 'devolucion pendiente: bloquea');
reset role;
select is((select count(*)::int from public.usuario where id::text like '00000000-0000-0000-0000-0000000000d%' and rol = 'cliente'), 5, 'ninguno cambio de rol');
select is((select count(*)::int from public.perfil_profesional where id::text like '00000000-0000-0000-0000-0000000000d%'), 0, 'ni nacio un perfil');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000e0', 'profesional', null)$$, 'sin operaciones, pasa a profesional');
select throws_ok($$select public.operaciones_vivas_de_cliente('00000000-0000-0000-0000-0000000000d1')$$, '42501', null, 'la funcion interna no se llama desde la API');
reset role;
-- Una vez profesional, reasignarlo no revisa operaciones (ya no hay nada que quitar).
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = '00000000-0000-0000-0000-0000000001d1';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000d1', 'profesional', null)$$, 'cancelada la reserva, d1 pasa a profesional');

select * from finish();
rollback;
