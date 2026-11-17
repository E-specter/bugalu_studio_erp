begin;
create extension if not exists pgtap with schema extensions;
select plan(95);

-- RF-18 (parte B): reprogramar con la politica de niveles (CA-08 a CA-10) y la eleccion tras una cancelacion del estudio (CA-13).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Total 200, adelanto pagado 100 y saldo 100 pendiente. Horas desde ahora (la misma sala, sin solapes):
-- r1 +73 (nivel 1), r2 +31 (nivel 2), r3 +11 (nivel 3), r4 de c2 +150, r5/r6/r7 +120/+130/+140 (cancelan por el estudio),
-- r8 de c2 +300 (ocupa el tramo), r10 +40 (nivel 2, ya reprogramo una vez en nivel 2), r11 +90 (nivel 1, ya reprogramo dos veces),
-- r12 +160 (se mueve 30 min), r13 +170 sin pagos pre_reservada.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago, creada_en)
select d.id, d.cliente, sa.id, se.id, date_trunc('hour', now()) + d.horas * interval '1 hour',
  date_trunc('hour', now()) + d.horas * interval '1 hour' + interval '1 hour', 200, d.estado, '2099-01-01', now() - interval '30 days'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('cccccccc-0000-0000-0000-000000000001'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, 73, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', 31, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', 11, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c2', 150, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c1', 120, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000006', '00000000-0000-0000-0000-0000000000c1', 130, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000007', '00000000-0000-0000-0000-0000000000c1', 140, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000008', '00000000-0000-0000-0000-0000000000c2', 300, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000010', '00000000-0000-0000-0000-0000000000c1', 40, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000c1', 90, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000012', '00000000-0000-0000-0000-0000000000c1', 160, 'confirmada'),
    ('cccccccc-0000-0000-0000-000000000013', '00000000-0000-0000-0000-0000000000c1', 170, 'pre_reservada')
  ) as d(id, cliente, horas, estado)
where se.nombre = 'Ensayo' and sa.nombre = 'Sala principal';
insert into public.cuota (id_reserva, hito, monto, estado, pagado)
select id, 'al_reservar', 100, case when right(id::text, 2) = '13' then 'pendiente' else 'pagada' end,
  case when right(id::text, 2) = '13' then 0 else 100 end from public.reserva;
insert into public.cuota (id_reserva, hito, monto, estado) select id, 'al_terminar', 100, 'pendiente' from public.reserva;
insert into public.reprogramacion (id_reserva, anterior_inicio, nuevo_inicio, nivel, total_anterior, total_nuevo)
values ('cccccccc-0000-0000-0000-000000000010', now(), now(), 2, 200, 200),
  ('cccccccc-0000-0000-0000-000000000011', now(), now(), 1, 200, 200),
  ('cccccccc-0000-0000-0000-000000000011', now(), now(), 1, 200, 200);

-- Ayuda de prueba: el mensaje y el detalle del error al reprogramar.
create function public.t_repro(p_id uuid, p_horas integer, p_nivel integer, p_esperado numeric, p_total numeric) returns text
language plpgsql as $$
declare v_det text; v_msg text;
begin
  perform public.reprogramar_reserva(p_id, date_trunc('hour', now()) + p_horas * interval '1 hour', p_nivel, p_esperado, null,
    jsonb_build_object('total', p_total::text), p_total);
  return 'sin error';
exception when others then
  get stacked diagnostics v_det = pg_exception_detail, v_msg = message_text;
  return v_msg || '|' || coalesce(v_det, '');
end;
$$;

-- Funciones puras de apoyo.
select is(public.sumar_dias_habiles('2027-03-05 10:00-05', 7), '2027-03-16 23:59:59.999999-05'::timestamptz, '7 dias habiles desde un viernes: el martes 16, al final del dia en Lima');
insert into public.feriado (fecha, nombre) values ('2027-03-10', 'Prueba');
select is(public.sumar_dias_habiles('2027-03-05 10:00-05', 7), '2027-03-17 23:59:59.999999-05'::timestamptz, 'un feriado registrado no cuenta');
select is(public.sumar_dias_habiles('2027-03-06 10:00-05', 1), '2027-03-08 23:59:59.999999-05'::timestamptz, 'desde un sabado, el primer dia habil es el lunes');
select is(public.pagado_neto('cccccccc-0000-0000-0000-000000000001'), 100.00::numeric, 'pagado neto sin reprogramaciones: lo aplicado a las cuotas');
select is((select count(*)::int from public.ocupacion_sala((select id_sala from public.reserva where id = 'cccccccc-0000-0000-0000-000000000012'),
  date_trunc('hour', now()) + interval '160 hours', date_trunc('hour', now()) + interval '162 hours')), 1, 'la ocupacion normal ve la reserva');
select is((select count(*)::int from public.ocupacion_sala_excluyendo((select id_sala from public.reserva where id = 'cccccccc-0000-0000-0000-000000000012'),
  date_trunc('hour', now()) + interval '160 hours', date_trunc('hour', now()) + interval '162 hours', 'cccccccc-0000-0000-0000-000000000012')), 0, 'excluyendo la propia reserva, el tramo queda libre');

-- Vista previa (CA-10): sin cambiar nada. Ejemplos exactos de CA-09.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select nivel, penalizacion, saldo, credito, reprogramaciones_restantes
  from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000002', date_trunc('hour', now()) + interval '210 hours', 240)$$,
  $$values (2::smallint, 50.00::numeric, 190.00::numeric, 0.00::numeric, 0)$$, 'nivel 2: total 200, pagado 100, nuevo 240: penalizacion 50, saldo 190');
select results_eq($$select nivel, penalizacion, saldo, credito, reprogramaciones_restantes
  from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001', date_trunc('hour', now()) + interval '200 hours', 80)$$,
  $$values (1::smallint, 0.00::numeric, 0.00::numeric, 20.00::numeric, 1)$$, 'nivel 1: pagado 100, nuevo 80: saldo 0 y credito 20; queda 1');
select results_eq($$select nivel, penalizacion, saldo, credito from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001',
  date_trunc('hour', now()) + interval '200 hours', 250)$$, $$values (1::smallint, 0.00::numeric, 150.00::numeric, 0.00::numeric)$$,
  'nivel 1 con un precio mayor: la diferencia va al saldo');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000003', now() + interval '200 hours', 200)$$,
  'P0001', 'reprogramacion_no_permitida', 'nivel 3: no se reprograma');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000013', now() + interval '200 hours', 200)$$,
  'P0001', 'reprogramacion_no_permitida', 'una pre_reservada no se reprograma');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000010', now() + interval '200 hours', 200)$$,
  'P0001', 'limite_reprogramaciones', 'nivel 2 con una en nivel 2 ya hecha: limite');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000011', now() + interval '200 hours', 200)$$,
  'P0001', 'limite_reprogramaciones', 'dos reprogramaciones hechas: limite total');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000004', now() + interval '200 hours', 200)$$,
  'P0002', null, 'la reserva de otro cliente no existe para el');
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001', now() - interval '1 hour', 200)$$,
  '22023', 'inicio_invalido', 'el nuevo inicio debe ser futuro');
select is((select count(*)::int from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000001'), 0, 'la vista previa no escribe el historial');
reset role;
select is((select total from public.reserva where id = 'cccccccc-0000-0000-0000-000000000001'), 200.00::numeric, 'la vista previa no cambia la reserva');

-- Quien no puede.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001', now() + interval '200 hours', 200)$$,
  '42501', null, 'el personal no reprograma');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001', now() + interval '200 hours', 200)$$,
  '42501', null, 'el administrador solo reprograma tras una cancelacion del estudio');
reset role;
set local role anon;
select throws_ok($$select * from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000001', now() + interval '200 hours', 200)$$,
  '42501', null, 'anon no ejecuta');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000001', now() + interval '200 hours', 1, 80, null, '{}', 80)$$,
  '42501', null, 'anon no reprograma');
reset role;

-- Reprogramar: las barreras de nivel y de precio esperados, y el otro cliente.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select matches(public.t_repro('cccccccc-0000-0000-0000-000000000001', 200, 2, 80, 80), '^nivel_cambiado\|.*"nivel": 1', 'otro nivel: nivel_cambiado con la vista nueva');
select matches(public.t_repro('cccccccc-0000-0000-0000-000000000001', 200, 1, 90, 80), '^precio_cambiado\|.*"credito": "?20', 'otro precio: precio_cambiado con la vista nueva');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000001', date_trunc('hour', now()) + interval '200 hours', null, 80, null, '{}', 80)$$,
  'P0001', 'nivel_cambiado', 'sin nivel esperado: nivel_cambiado');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000004', date_trunc('hour', now()) + interval '200 hours', 1, 80, null, '{}', 80)$$,
  'P0002', null, 'otro cliente no reprograma (404)');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000003', date_trunc('hour', now()) + interval '200 hours', 3, 200, null, '{}', 200)$$,
  'P0001', 'reprogramacion_no_permitida', 'nivel 3: no se reprograma');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000011', date_trunc('hour', now()) + interval '200 hours', 1, 200, null, '{}', 200)$$,
  'P0001', 'limite_reprogramaciones', 'limite total');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000001', date_trunc('hour', now()) + interval '300 hours', 1, 80, null, '{}', 80)$$,
  '23P01', null, 'un tramo ocupado por otra reserva: la exclusion de la base');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000001', now() + interval '200 hours' + interval '7 minutes', 1, 80, null, '{}', 80)$$,
  '23514', null, 'un inicio que no es media hora exacta: la base lo rechaza');
reset role;
select results_eq($$select inicio, total, estado from public.reserva where id = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$select date_trunc('hour', now()) + interval '73 hours', 200.00::numeric, 'confirmada'::text$$, 'los rechazos no cambian la reserva');
select is((select count(*)::int from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000001'), 0, 'ni el historial');

-- Nivel 1 con precio menor (CA-09): saldo 0, credito de reprogramacion 20.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000001', date_trunc('hour', now()) + interval '200 hours', 1, 80, null,
  '{"total": "80.00"}', 80, '[]')$$, 'reprograma en nivel 1 a un precio menor');
reset role;
select results_eq($$select inicio, fin, fin_buffer, total, estado, precio ->> 'total' from public.reserva where id = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$select date_trunc('hour', now()) + interval '200 hours', date_trunc('hour', now()) + interval '201 hours',
    date_trunc('hour', now()) + interval '201 hours 30 minutes', 80.00::numeric, 'confirmada'::text, '80.00'::text$$,
  'cambian el horario (con su buffer), el total y el precio; sigue confirmada');
select results_eq($$select hito, monto, estado, pagado from public.cuota where id_reserva = 'cccccccc-0000-0000-0000-000000000001' order by hito$$,
  $$values ('al_reservar'::text, 100.00::numeric, 'pagada'::text, 100.00::numeric), ('al_terminar', 0.00, 'pagada', 0.00)$$, 'la cuota de saldo queda en 0.00');
select results_eq($$select tipo, monto, saldo, estado, id_cliente from public.credito where id_reserva = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$values ('reprogramacion'::text, 20.00::numeric, 20.00::numeric, 'vigente'::text, '00000000-0000-0000-0000-0000000000c1'::uuid)$$, 'la diferencia pasa a credito de reprogramacion');
select results_eq($$select nivel, penalizacion, total_anterior, total_nuevo, id_autor, nuevo_inicio - anterior_inicio
  from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000001'$$,
  $$values (1::smallint, 0.00::numeric, 200.00::numeric, 80.00::numeric, '00000000-0000-0000-0000-0000000000c1'::uuid, interval '127 hours')$$, 'queda en el historial');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_reprogramada' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000001'
  and destinatario = 'cli@t.pe'), 1, 'aviso al cliente');
select is(public.pagado_neto('cccccccc-0000-0000-0000-000000000001'), 80.00::numeric, 'el pagado neto descuenta lo que ya paso a credito');
select is((select hechas from (select count(*)::int as hechas from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000001') x), 1, 'una hecha');
-- Lo que ya paso a credito no se acredita dos veces al cancelar despues (nivel 1: pagado neto 80).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select pagado, retenido, credito, reprogramaciones_restantes from public.vista_cancelacion('cccccccc-0000-0000-0000-000000000001')$$,
  $$values (80.00::numeric, 0.00::numeric, 80.00::numeric, 1)$$, 'cancelar despues: el credito ya generado no se vuelve a acreditar');
reset role;

-- Nivel 2 con precio mayor (CA-09): penalizacion 50 y saldo 190; el aviso lo dice.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000002', date_trunc('hour', now()) + interval '210 hours', 2, 240, null,
  '{"total": "240.00"}', 240, '[]')$$, 'reprograma en nivel 2 a un precio mayor');
reset role;
select results_eq($$select hito, monto, estado, pagado from public.cuota where id_reserva = 'cccccccc-0000-0000-0000-000000000002' order by hito$$,
  $$values ('al_reservar'::text, 100.00::numeric, 'pagada'::text, 100.00::numeric), ('al_terminar', 190.00, 'pendiente', 0.00)$$, 'saldo = 240 + 50 - 100 = 190');
select results_eq($$select nivel, penalizacion, total_anterior, total_nuevo from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000002'$$,
  $$values (2::smallint, 50.00::numeric, 200.00::numeric, 240.00::numeric)$$, 'la penalizacion de nivel 2 queda registrada');
select is((select count(*)::int from public.credito where id_reserva = 'cccccccc-0000-0000-0000-000000000002'), 0, 'sin credito');
select is((select (datos ->> 'penalizacion')::numeric from public.notificacion where tipo = 'reserva_reprogramada' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000002'),
  50.00::numeric, 'el aviso lleva la penalizacion');
-- Segunda reprogramacion (ahora en nivel 1, mismo precio): la penalizacion retenida no se cobra dos veces.
select is(public.pagado_neto('cccccccc-0000-0000-0000-000000000002'), 50.00::numeric, 'pagado neto: 100 aplicados menos la penalizacion retenida');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select nivel, penalizacion, saldo, credito, reprogramaciones_restantes
  from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000002', date_trunc('hour', now()) + interval '220 hours', 240)$$,
  $$values (1::smallint, 0.00::numeric, 190.00::numeric, 0.00::numeric, 0)$$, 'segunda: el mismo saldo de 190, sin cobrar la penalizacion de nuevo; no quedan mas');
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000002', date_trunc('hour', now()) + interval '220 hours', 1, 240, null,
  '{"total": "240.00"}', 240, '[]')$$, 'segunda reprogramacion (en nivel 1)');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000002', date_trunc('hour', now()) + interval '230 hours', 1, 240, null,
  '{"total": "240.00"}', 240, '[]')$$, 'P0001', 'limite_reprogramaciones', 'una tercera supera el limite de 2');
reset role;
select results_eq($$select monto, estado from public.cuota where id_reserva = 'cccccccc-0000-0000-0000-000000000002' and hito = 'al_terminar'$$,
  $$values (190.00::numeric, 'pendiente'::text)$$, 'la cuota de saldo sigue en 190');

-- Moverse 30 minutos: el tramo se solapa con el propio y es valido.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000012', date_trunc('hour', now()) + interval '160 hours 30 minutes', 1, 200, null,
  '{"total": "200.00"}', 200, '[]')$$, 'moverse 30 minutos, solapandose con el propio horario');
reset role;
select is((select inicio from public.reserva where id = 'cccccccc-0000-0000-0000-000000000012'), date_trunc('hour', now()) + interval '160 hours 30 minutes', 'queda en el nuevo horario');
select results_eq($$select monto, estado from public.cuota where id_reserva = 'cccccccc-0000-0000-0000-000000000012' and hito = 'al_terminar'$$,
  $$values (100.00::numeric, 'pendiente'::text)$$, 'mismo precio: la cuota de saldo intacta');

-- Historial inmutable y RLS.
select throws_ok($$update public.reprogramacion set penalizacion = 0 where id_reserva = 'cccccccc-0000-0000-0000-000000000002'$$, 'P0001', null, 'el historial no se edita');
select throws_ok($$delete from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000002'$$, 'P0001', null, 'ni se borra');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.reprogramacion), 0, 'otro cliente no ve el historial ajeno');
select throws_ok($$insert into public.reprogramacion (id_reserva, anterior_inicio, nuevo_inicio, total_anterior, total_nuevo)
  values ('cccccccc-0000-0000-0000-000000000004', now(), now(), 1, 1)$$, '42501', null, 'nadie inserta el historial por fuera de la funcion');
reset role;

-- Cancelacion del estudio (CA-13): reprogramar sin costo.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva('cccccccc-0000-0000-0000-000000000005', 'Averia en la sala', null, 'estudio')$$, 'el administrador cancela r5 por el estudio');
select lives_ok($$select public.cancelar_reserva('cccccccc-0000-0000-0000-000000000006', 'Averia en la sala', null, 'estudio')$$, 'y r6');
select lives_ok($$select public.cancelar_reserva('cccccccc-0000-0000-0000-000000000007', 'Averia en la sala', null, 'estudio')$$, 'y r7');
reset role;
select is((select count(*)::int from public.reserva where eleccion_estudio = 'pendiente' and id::text like 'cccccccc%'), 3, 'tres cancelaciones del estudio con eleccion pendiente');
select is((select q.estado from public.cuota q where q.id_reserva = 'cccccccc-0000-0000-0000-000000000005' and q.hito = 'al_terminar'), 'anulada', 'la cuota de saldo quedo anulada');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select nivel, penalizacion, saldo, credito, reprogramaciones_restantes
  from public.vista_reprogramacion('cccccccc-0000-0000-0000-000000000005', date_trunc('hour', now()) + interval '230 hours', 999)$$,
  $$values (null::smallint, 0.00::numeric, 100.00::numeric, 0.00::numeric, 2)$$, 'tras el estudio: sin nivel ni penalizacion, mismo precio (ignora el recalculado), no cuenta para los limites');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000005', date_trunc('hour', now()) + interval '230 hours', 1, 200, null, '{}', 200)$$,
  'P0001', 'nivel_cambiado', 'tras el estudio el nivel esperado es null');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000005', date_trunc('hour', now()) + interval '300 hours', null, null, null, '{}', 999)$$,
  '23P01', null, 'tras el estudio tambien se respeta el tramo libre');
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000005', date_trunc('hour', now()) + interval '230 hours', null, null, null,
  '{"total": "999"}', 999, '[]')$$, 'reprograma sin costo (sin total esperado)');
reset role;
select results_eq($$select estado, motivo_cancelacion, eleccion_estudio, total, inicio from public.reserva where id = 'cccccccc-0000-0000-0000-000000000005'$$,
  $$select 'confirmada'::text, null::text, 'reprogramada'::text, 200.00::numeric, date_trunc('hour', now()) + interval '230 hours'$$,
  'vuelve a confirmada en el nuevo horario con el mismo total');
select results_eq($$select hito, monto, estado, pagado from public.cuota where id_reserva = 'cccccccc-0000-0000-0000-000000000005' order by hito$$,
  $$values ('al_reservar'::text, 100.00::numeric, 'pagada'::text, 100.00::numeric), ('al_terminar', 100.00, 'pendiente', 0.00)$$, 'la cuota de saldo vuelve a pendiente');
select results_eq($$select nivel, penalizacion, total_anterior, total_nuevo, id_autor from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000005'$$,
  $$values (null::smallint, 0.00::numeric, 200.00::numeric, 200.00::numeric, '00000000-0000-0000-0000-0000000000c1'::uuid)$$, 'historial sin nivel');
select is((select precio ->> 'total' from public.reserva where id = 'cccccccc-0000-0000-0000-000000000005'), null, 'el precio guardado no se recalcula (queda el de la reserva)');
select is((select count(*)::int from public.credito where id_reserva = 'cccccccc-0000-0000-0000-000000000005'), 0, 'sin credito');
select is((select count(*)::int from public.notificacion where tipo = 'eleccion_estudio_resuelta' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000005'
  and destinatario = 'ad@t.pe'), 1, 'aviso a los administradores: el cliente eligio');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_reprogramada' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000005'), 1, 'aviso de reprogramacion al cliente');
-- Elegida una vez, no hay otra.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000005')$$, 'P0001', 'eleccion_no_disponible', 'ya reprogramo: no elige la devolucion');

-- El administrador reprograma por el cliente tras la cancelacion del estudio; el personal y otro cliente no.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000007', date_trunc('hour', now()) + interval '240 hours', null, null, null, '{}', 200)$$,
  'P0002', null, 'otro cliente: 404 tambien tras el estudio');
select throws_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000007')$$, 'P0002', null, 'otro cliente no elige');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000007', date_trunc('hour', now()) + interval '240 hours', null, null, null, '{}', 200)$$,
  '42501', null, 'el personal no reprograma tras el estudio');
select throws_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000007')$$, '42501', null, 'el personal no elige');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000007', date_trunc('hour', now()) + interval '240 hours', null, null, null, '{}', 200)$$,
  'el administrador reprograma por el cliente');
reset role;
select results_eq($$select estado, eleccion_estudio, inicio from public.reserva where id = 'cccccccc-0000-0000-0000-000000000007'$$,
  $$select 'confirmada'::text, 'reprogramada'::text, date_trunc('hour', now()) + interval '240 hours'$$, 'queda reprogramada');
select results_eq($$select id_autor from public.reprogramacion where id_reserva = 'cccccccc-0000-0000-0000-000000000007'$$,
  $$values ('00000000-0000-0000-0000-0000000000ad'::uuid)$$, 'el historial dice que lo hizo el administrador');
select is((select count(*)::int from public.notificacion where tipo = 'eleccion_estudio_resuelta' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000007'), 0,
  'si elige el propio administrador, no se avisa a los administradores');

-- Devolucion integra (CA-13).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000003')$$, 'P0001', 'eleccion_no_disponible', 'sin eleccion pendiente: no disponible');
select lives_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000006')$$, 'el cliente elige la devolucion integra');
select throws_ok($$select public.elegir_estudio_devolucion('cccccccc-0000-0000-0000-000000000006')$$, 'P0001', 'eleccion_no_disponible', 'elegir dos veces: no disponible');
select throws_ok($$select public.reprogramar_reserva('cccccccc-0000-0000-0000-000000000006', date_trunc('hour', now()) + interval '250 hours', null, null, null, '{}', 200)$$,
  'P0001', 'reprogramacion_no_permitida', 'tras elegir la devolucion ya no se reprograma');
reset role;
select results_eq($$select tipo, estado, monto_solicitado, monto_aprobado, id_credito, id_cliente, decidida_en is not null, id_decisor
  from public.devolucion where id_reserva = 'cccccccc-0000-0000-0000-000000000006'$$,
  $$values ('estudio'::text, 'aprobada'::text, 100.00::numeric, 100.00::numeric, null::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, true, null::uuid)$$,
  'devolucion del estudio: aprobada, total, lo pagado');
select ok((select limite = public.sumar_dias_habiles(solicitada_en, 7) from public.devolucion where id_reserva = 'cccccccc-0000-0000-0000-000000000006'), 'con plazo de 7 dias habiles');
select is((select eleccion_estudio from public.reserva where id = 'cccccccc-0000-0000-0000-000000000006'), 'devolucion', 'la reserva guarda la eleccion');
select is((select estado from public.reserva where id = 'cccccccc-0000-0000-0000-000000000006'), 'cancelada', 'sigue cancelada');
select is((select count(*)::int from public.notificacion where tipo = 'eleccion_estudio_resuelta' and datos ->> 'id_reserva' = 'cccccccc-0000-0000-0000-000000000006'
  and destinatario = 'ad@t.pe' and datos ->> 'opcion' = 'devolucion'), 1, 'aviso a los administradores');
select is((select count(*)::int from public.credito where id_reserva = 'cccccccc-0000-0000-0000-000000000006'), 0, 'la devolucion del estudio no pasa por credito');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.marcar_devolucion_realizada((select id from public.devolucion where id_reserva = 'cccccccc-0000-0000-0000-000000000006'), 'Yape 123')$$,
  'el administrador la marca realizada como cualquier otra');
reset role;
-- Contexto para el backend: lo que se conserva al reprogramar.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select estudio, total, id_especialistas, fin - inicio from public.contexto_reprogramacion('cccccccc-0000-0000-0000-000000000012')$$,
  $$values (false, 200.00::numeric, '{}'::uuid[], interval '1 hour')$$, 'el contexto trae la duracion, el precio y los especialistas');
select throws_ok($$select * from public.contexto_reprogramacion('cccccccc-0000-0000-0000-000000000004')$$, 'P0002', null, 'el contexto de otro cliente no existe');
reset role;
select * from finish();
rollback;
