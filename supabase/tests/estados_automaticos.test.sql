begin;
create extension if not exists pgtap with schema extensions;
select plan(22);

-- RF-06: avanzar_reservas() (RN-23): confirmada -> en_curso -> finalizada con el reloj, aviso de saldo una sola vez.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Tiempos simulados: las reservas se insertan ya vencidas con la conexion de administracion.
-- r1 confirmada ya terminada con saldo pendiente; r2 confirmada en su hora (inicio pasado, fin futuro);
-- r3 pre_reservada pasada (no avanza); r4 en_curso ya terminada con saldo pagado; r5 confirmada futura;
-- r6 cancelada pasada.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
select d.id, '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, d.inicio, d.fin, 80, d.estado, d.motivo, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid, '2020-01-01 10:00-05'::timestamptz, '2020-01-01 11:00-05'::timestamptz, 'confirmada', null),
    ('aaaaaaaa-0000-0000-0000-000000000002', date_trunc('hour', now()) - interval '1 hour', date_trunc('hour', now()) + interval '7 hours', 'confirmada', null),
    ('aaaaaaaa-0000-0000-0000-000000000003', '2020-01-03 10:00-05', '2020-01-03 11:00-05', 'pre_reservada', null),
    ('aaaaaaaa-0000-0000-0000-000000000004', '2020-01-04 10:00-05', '2020-01-04 11:00-05', 'en_curso', null),
    ('aaaaaaaa-0000-0000-0000-000000000005', '2099-01-05 10:00-05', '2099-01-05 11:00-05', 'confirmada', null),
    ('aaaaaaaa-0000-0000-0000-000000000006', '2020-01-06 10:00-05', '2020-01-06 11:00-05', 'cancelada', 'cliente')
  ) as d(id, inicio, fin, estado, motivo)
where se.nombre = 'Ensayo';
insert into public.cuota (id_reserva, hito, monto, estado)
select id, 'al_terminar', 40, case when id = 'aaaaaaaa-0000-0000-0000-000000000004' then 'pagada' else 'pendiente' end
from public.reserva where id in ('aaaaaaaa-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000004',
  'aaaaaaaa-0000-0000-0000-000000000005');

select has_function('public', 'avanzar_reservas', 'existe avanzar_reservas');
select is((select schedule from cron.job where jobname = 'avanzar_reservas'), '* * * * *', 'se programa cada minuto en pg_cron');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.avanzar_reservas()$$, '42501', null, 'ni el administrador la ejecuta');
reset role;
set local role anon;
select throws_ok($$select public.avanzar_reservas()$$, '42501', null, 'anon no la ejecuta');
reset role;

select is(public.avanzar_reservas(), 3, 'avanza 3 reservas: r1, r2 y r4');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000001'), 'finalizada', 'confirmada ya terminada pasa directo a finalizada');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000002'), 'en_curso', 'confirmada en su hora pasa a en_curso');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000003'), 'pre_reservada', 'la pre_reservada no avanza');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000004'), 'finalizada', 'en_curso terminada pasa a finalizada');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000005'), 'confirmada', 'la confirmada futura no cambia');
select is((select estado from public.reserva where id = 'aaaaaaaa-0000-0000-0000-000000000006'), 'cancelada', 'la cancelada no cambia');

select is((select count(*)::int from public.notificacion where tipo = 'reserva_finalizada_saldo'), 1, 'un aviso de saldo: solo r1 (r4 ya pagada)');
select is((select destinatario from public.notificacion where tipo = 'reserva_finalizada_saldo'), 'cli@t.pe', 'va al correo del cliente');
select ok((select datos ->> 'id_reserva' = 'aaaaaaaa-0000-0000-0000-000000000001' and datos ? 'folio' and (datos ->> 'saldo')::numeric = 40
  from public.notificacion where tipo = 'reserva_finalizada_saldo'), 'lleva reserva, folio y saldo');

select is(public.avanzar_reservas(), 0, 'segunda corrida: nada que avanzar');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_finalizada_saldo'), 1, 'segunda corrida: sin avisos duplicados');

-- Una reserva en_curso cuyo fin llega despues termina y avisa una vez.
update public.reserva set inicio = date_trunc('hour', now()) - interval '3 hours', fin = date_trunc('hour', now()) - interval '2 hours'
  where id = 'aaaaaaaa-0000-0000-0000-000000000002';
insert into public.cuota (id_reserva, hito, monto) values ('aaaaaaaa-0000-0000-0000-000000000002', 'al_terminar', 25);
select is(public.avanzar_reservas(), 1, 'al llegar su fin, la en_curso pasa a finalizada');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_finalizada_saldo'), 2, 'y avisa su saldo');
select is(public.avanzar_reservas(), 0, 'idempotente otra vez');

-- Con un pago en validacion el cliente ya pago y espera: no se le avisa del saldo. Con el pago rechazado, si.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select d.id, '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, d.inicio, d.fin, 80, 'confirmada', '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('aaaaaaaa-0000-0000-0000-000000000007'::uuid, '2020-01-07 10:00-05'::timestamptz, '2020-01-07 11:00-05'::timestamptz),
    ('aaaaaaaa-0000-0000-0000-000000000008', '2020-01-08 10:00-05', '2020-01-08 11:00-05')
  ) as d(id, inicio, fin)
where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto)
values ('cccccccc-0000-0000-0000-000000000007', 'aaaaaaaa-0000-0000-0000-000000000007', 'al_terminar', 30),
       ('cccccccc-0000-0000-0000-000000000008', 'aaaaaaaa-0000-0000-0000-000000000008', 'al_terminar', 35);
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
values ('cccccccc-0000-0000-0000-000000000007', '00000000-0000-0000-0000-0000000000c1', 'yape', 30, '12345678', 'r/7', 'image/png'),
       ('cccccccc-0000-0000-0000-000000000008', '00000000-0000-0000-0000-0000000000c1', 'yape', 35, '87654321', 'r/8', 'image/png');
select set_config('request.jwt.claims', '', true);
update public.comprobante_pago set estado = 'rechazado', motivo_rechazo = 'Monto errado', validado_en = now()
  where id_cuota = 'cccccccc-0000-0000-0000-000000000008';
select is(public.avanzar_reservas(), 2, 'finalizan la del pago en validacion y la del pago rechazado');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_finalizada_saldo'
  and datos ->> 'id_reserva' = 'aaaaaaaa-0000-0000-0000-000000000007'), 0, 'con pago en validacion no se avisa del saldo');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_finalizada_saldo'
  and datos ->> 'id_reserva' = 'aaaaaaaa-0000-0000-0000-000000000008'), 1, 'con el pago rechazado si se avisa');

select * from finish();
rollback;
