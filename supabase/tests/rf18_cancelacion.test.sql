begin;
create extension if not exists pgtap with schema extensions;
select plan(62);

-- RF-18 (parte A): cancelar con pagos por nivel (CA-01, CA-03, CA-04) y pagos en validacion despues de cancelar.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.instruccion_pago set texto = 'x', activo = true where metodo = 'yape';

-- Total 200, adelanto pagado 100 y saldo 100 pendiente; +73 h = nivel 1, +31 h = nivel 2, +11 h = nivel 3.
-- r1 n1, r2 n2, r3 n3, r4 sin pagos, r5 de c2, r6 admin en nombre del cliente, r7 estudio con pagos,
-- r8 n1 / r9 n3 / r10 n2 con un pago en validacion, r11 n1 con pago en validacion que se rechaza.
insert into public.sala_tecnica (id, nombre, sede)
select ('5a5a5a5a-0000-0000-0000-0000000000' || lpad(n::text, 2, '0'))::uuid, 'Sala t' || n, 'Sede t' from generate_series(6, 11) n;
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago, creada_en)
select d.id, d.cliente, case when right(d.id::text, 2)::int between 6 and 11 then ('5a5a5a5a-0000-0000-0000-0000000000' || lpad(right(d.id::text, 2)::int::text, 2, '0'))::uuid else sa.id end, se.id, date_trunc('hour', now()) + d.horas * interval '1 hour',
  date_trunc('hour', now()) + d.horas * interval '1 hour' + interval '1 hour', 200, d.estado, '2099-01-01', now() - interval '30 days'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-000000000001'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, 73, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', 31, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', 11, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c1', 100, 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c2', 150, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000006', '00000000-0000-0000-0000-0000000000c1', 31, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000007', '00000000-0000-0000-0000-0000000000c1', 73, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000008', '00000000-0000-0000-0000-0000000000c1', 73, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000009', '00000000-0000-0000-0000-0000000000c1', 11, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000010', '00000000-0000-0000-0000-0000000000c1', 31, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000011', '00000000-0000-0000-0000-0000000000c1', 73, 'confirmada')
  ) as d(id, cliente, horas, estado)
where se.nombre = 'Ensayo' and sa.nombre = 'Sala principal';
insert into public.cuota (id_reserva, hito, monto, estado, pagado)
select id, 'al_reservar', 100, case when id = 'bbbbbbbb-0000-0000-0000-000000000004' then 'pendiente' else 'pagada' end,
  case when id = 'bbbbbbbb-0000-0000-0000-000000000004' then 0 else 100 end from public.reserva;
insert into public.cuota (id_reserva, hito, monto, estado) select id, 'al_terminar', 100, 'pendiente' from public.reserva;

-- Ayuda de prueba: el detalle del error al cancelar.
create function public.t_detalle(p_id uuid, p_nivel integer) returns text
language plpgsql as $$
declare v_det text; v_msg text;
begin
  perform public.cancelar_reserva(p_id, null, p_nivel);
  return 'sin error';
exception when others then
  get stacked diagnostics v_det = pg_exception_detail, v_msg = message_text;
  return v_msg || '|' || coalesce(v_det, '');
end;
$$;

-- Pagos en validacion sobre la cuota de saldo de r8..r11 (los registra el cliente).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
select ('aaaaaaaa-0000-0000-0000-0000000000' || right(c.id_reserva::text, 2))::uuid, c.id, auth.uid(), 'yape', 100,
  'OP-' || right(c.id_reserva::text, 2), auth.uid() || '/a.png', 'image/png'
from public.cuota c where c.hito = 'al_terminar'
  and right(c.id_reserva::text, 2) in ('08', '09', '10', '11');

-- Con pagos el cliente debe dar el nivel esperado; sin el, o con otro, 409 con la vista previa en el detalle.
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000001')$$, 'P0001', 'nivel_cambiado', 'con pagos y sin nivel_esperado: nivel_cambiado');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000001', null, 2)$$, 'P0001', 'nivel_cambiado', 'con otro nivel: nivel_cambiado');
select matches(public.t_detalle('bbbbbbbb-0000-0000-0000-000000000001', 3), '^nivel_cambiado\|.*"nivel": 1.*"credito": "?100', 'el detalle lleva la nueva vista previa');
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'confirmada', 'el nivel cambiado no cambia nada');
select is((select count(*)::int from public.credito), 0, 'ni genera credito');

-- Nivel 1.
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000001', 'No puedo asistir', 1)$$, 'nivel 1 con el nivel esperado');
-- Nivel 2 y 3.
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', null, 2)$$, 'nivel 2');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000003', null, 3)$$, 'nivel 3');
-- Sin pagos: como hoy (CA-01), sin nivel esperado.
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000004')$$, 'sin pagos: cancela gratis sin nivel esperado');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000005', null, 1)$$, 'P0002', null, 'otro cliente: no existe para el (404)');
-- Un cliente no se fija el aviso ni cancela "por el estudio".
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000008', null, 1, 'cliente', now() - interval '3 days')$$, '42501', null, 'el cliente no fija aviso_en');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000008', null, 1, 'estudio')$$, '42501', null, 'el cliente no cancela por el estudio');
reset role;

select results_eq($$select estado, motivo_cancelacion, nivel_cancelacion, pagado_cancelacion, retenido, credito_generado, cancelacion_por
  from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'$$,
  $$values ('cancelada', 'cliente', 1::smallint, 100.00::numeric, 0.00::numeric, 100.00::numeric, 'cliente')$$, 'nivel 1: cancelada, retiene 0, credito 100');
select ok((select aviso_en between now() - interval '1 minute' and now() + interval '1 minute' and id_cancelador = '00000000-0000-0000-0000-0000000000c1'
  from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'guarda el momento del aviso y quien cancelo');
select results_eq($$select retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000002'$$,
  $$values (50.00::numeric, 50.00::numeric)$$, 'nivel 2: retiene 50, credito 50');
select results_eq($$select retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000003'$$,
  $$values (100.00::numeric, 0.00::numeric)$$, 'nivel 3: retiene 100, credito 0');
select results_eq($$select tipo, monto, saldo, estado, id_cliente from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000001'$$,
  $$values ('nivel_1', 100.00::numeric, 100.00::numeric, 'vigente', '00000000-0000-0000-0000-0000000000c1'::uuid)$$, 'credito de nivel 1 vigente para el cliente');
select is((select tipo from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000002'), 'nivel_2', 'credito de nivel 2');
select is((select count(*)::int from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000003'), 0, 'nivel 3: sin credito');
select ok((select vence = (date_trunc('day', (now() at time zone 'America/Lima') + interval '31 days') at time zone 'America/Lima') - interval '1 microsecond'
  from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000001'), 'vence al final del dia 30 en Lima');
select is((select estado from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000001' and hito = 'al_terminar'), 'anulada', 'la cuota de saldo queda anulada');
select is((select estado || pagado::text from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000001' and hito = 'al_reservar'), 'pagada100.00', 'la cuota pagada queda como estaba');
select is((select count(*)::int from public.ocupacion_sala((select id_sala from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'),
  (select inicio from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'),
  (select fin from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'))), 0, 'el tramo queda libre');
select results_eq($$select nivel_cancelacion, credito_generado, (select count(*)::int from public.cuota q where q.id_reserva = r.id and q.estado = 'pendiente')
  from public.reserva r where id = 'bbbbbbbb-0000-0000-0000-000000000004'$$,
  $$values (null::smallint, 0.00::numeric, 2)$$, 'sin pagos: sin nivel y las cuotas siguen como hoy');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_con_pagos' and destinatario = 'cli@t.pe'), 3, 'avisa al cliente de las tres cancelaciones con pagos');
select ok((select datos ->> 'nivel' = '1' and (datos ->> 'retenido')::numeric = 0 and (datos ->> 'credito')::numeric = 100
  and datos ? 'credito_vence' and datos ? 'folio' from public.notificacion where tipo = 'reserva_cancelada_con_pagos'
  and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000001'), 'el aviso lleva nivel, retenido, credito y vencimiento');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_cliente' and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000004'), 1, 'los administradores siguen recibiendo el aviso del cliente');

-- Personal y anon: no cancelan.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000008', 'x')$$, '42501', null, 'el personal no cancela');
reset role;
set local role anon;
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000008')$$, '42501', null, 'anon no cancela');
reset role;
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000008'), 'confirmada', 'la reserva intacta tras los intentos ajenos');

-- Administrador: por el estudio (CA-13, solo deja la eleccion pendiente) y en nombre del cliente (CA-04).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000007', null, null, 'estudio')$$, 'P0001', 'nota_requerida', 'por el estudio con pagos: nota obligatoria');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000007', 'Averia en la sala', null, 'estudio')$$, 'cancela por el estudio');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', 'Pidio por WhatsApp', null, 'cliente')$$, 'P0001', 'aviso_invalido', 'en nombre del cliente sin aviso_en: aviso_invalido');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', 'x', null, 'cliente', now() + interval '1 hour')$$, 'P0001', 'aviso_invalido', 'aviso_en futuro: aviso_invalido');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', 'x', null, 'cliente', now() - interval '31 days')$$, 'P0001', 'aviso_invalido', 'aviso_en anterior a la creacion: aviso_invalido');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', null, null, 'cliente', now() - interval '1 day')$$, 'P0001', 'nota_requerida', 'en nombre del cliente la nota es obligatoria');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', 'x', null, 'otro')$$, '22023', null, 'por desconocido: 22023');
-- r6 empieza en 31 h; con el aviso hace 250 h la anticipacion es de 281 h y el nivel es 1.
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006', 'Pidio por WhatsApp', null, 'cliente', now() - interval '250 hours')$$, 'en nombre del cliente con aviso_en valido');
reset role;
select results_eq($$select motivo_cancelacion, nivel_cancelacion, cancelacion_por, id_cancelador, eleccion_estudio, credito_generado
  from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000007'$$,
  $$values ('administrador', null::smallint, 'estudio', '00000000-0000-0000-0000-0000000000ad'::uuid, 'pendiente', 0.00::numeric)$$, 'por el estudio: sin nivel, eleccion pendiente');
select is((select count(*)::int from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000007'), 0, 'por el estudio no hay credito hasta que el cliente elija');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_estudio' and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000007'), 1, 'por el estudio: aviso de siempre al cliente');
select results_eq($$select motivo_cancelacion, nivel_cancelacion, cancelacion_por, id_cancelador, credito_generado, (aviso_en = now() - interval '250 hours')
  from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000006'$$,
  $$values ('cliente', 1::smallint, 'cliente', '00000000-0000-0000-0000-0000000000ad'::uuid, 100.00::numeric, true)$$, 'en nombre del cliente: nivel por aviso_en y queda quien la hizo');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_con_pagos' and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000006'), 1, 'avisa al cliente');

-- Barrera: un administrador no cancela con pagos por UPDATE directo (sin nivel ni credito).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$, '42501', null, 'no se cancela con pagos por update directo');
select throws_ok($$update public.reserva set nivel_cancelacion = 1 where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$, '42501', null, 'nadie fija el nivel desde fuera');
select throws_ok($$update public.reserva set retenido = 0 where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$, '42501', null, 'nadie fija lo retenido desde fuera');
select throws_ok($$update public.reserva set estado = 'no_asistio' where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$, '42501', null, 'no_asistio solo lo pone la funcion');
reset role;

-- Cancelar con un pago en validacion (r8 n1, r9 n3, r10 n2, r11 n1): la cuota con pago pendiente no se anula.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000008', null, 1)$$, 'r8 nivel 1 con un pago en validacion');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000009', null, 3)$$, 'r9 nivel 3');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000010', null, 2)$$, 'r10 nivel 2');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000011', null, 1)$$, 'r11 nivel 1');
reset role;
select is((select estado from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000008' and hito = 'al_terminar'), 'pendiente', 'la cuota con pago en validacion sigue pendiente');
select results_eq($$select pagado_cancelacion, retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$,
  $$values (100.00::numeric, 0.00::numeric, 100.00::numeric)$$, 'lo que esta en validacion no cuenta todavia');

-- El administrador aprueba despues: el pago sigue el nivel con que se cancelo.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000008')$$, 'aprueba el pago de r8');
select lives_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000009')$$, 'aprueba el pago de r9');
select lives_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000010')$$, 'aprueba el pago de r10');
select lives_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000011', 'no coincide')$$, 'rechaza el pago de r11');
reset role;
select results_eq($$select pagado_cancelacion, retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000008'$$,
  $$values (200.00::numeric, 0.00::numeric, 200.00::numeric)$$, 'nivel 1: lo aprobado despues aumenta el credito');
select is((select sum(monto) from public.credito where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000008'), 200.00::numeric, 'y existe como credito');
select results_eq($$select pagado_cancelacion, retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000009'$$,
  $$values (200.00::numeric, 200.00::numeric, 0.00::numeric)$$, 'nivel 3: lo aprobado despues se retiene');
select results_eq($$select pagado_cancelacion, retenido, credito_generado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000010'$$,
  $$values (200.00::numeric, 50.00::numeric, 150.00::numeric)$$, 'nivel 2: la penalizacion es la misma y el resto es credito');
select is((select estado from public.cuota where id_reserva = 'bbbbbbbb-0000-0000-0000-000000000011' and hito = 'al_terminar'), 'anulada', 'un pago rechazado despues de cancelar anula la cuota');

select * from finish();
rollback;
