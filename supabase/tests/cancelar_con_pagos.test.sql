begin;
create extension if not exists pgtap with schema extensions;
select plan(32);

-- RF-06: cancelar_reserva(id, nota) (D-11 v1), avisos de cancelacion, nota_cancelacion y hay_pago_por_validar.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad2@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id in ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-0000000000a2');
update public.usuario set nombre = 'Ana Cliente' where id = '00000000-0000-0000-0000-0000000000c1';

-- Una reserva por dia (2027-06-0N): 1 y 2 de c1 con pagos, 3 y 4 sin pagos, 5 confirmada con pagos, 6 sin pagos;
-- 7 de c2 sin cuota pagada (tendra un pago en validacion).
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select d.id, d.cliente, sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 50, d.estado, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-000000000001'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, '2027-06-01 10:00-05'::timestamptz, 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', '2027-06-02 10:00-05', 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', '2027-06-03 10:00-05', 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c1', '2027-06-04 10:00-05', 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c1', '2027-06-05 10:00-05', 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000006', '00000000-0000-0000-0000-0000000000c1', '2027-06-06 10:00-05', 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000007', '00000000-0000-0000-0000-0000000000c2', '2027-06-07 10:00-05', 'pre_reservada')
  ) as d(id, cliente, inicio, estado)
where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto, estado)
select ('cccccccc-0000-0000-0000-00000000000' || right(id::text, 1))::uuid, id, 'al_reservar', 25,
  case when right(id::text, 1) in ('1', '2', '5') then 'pagada' else 'pendiente' end
from public.reserva;
update public.instruccion_pago set texto = 'Cuenta de prueba', activo = true where metodo = 'yape';

select has_function('public', 'cancelar_reserva', array['uuid', 'text'], 'cancelar_reserva(id, nota)');
select has_function('public', 'hay_pago_por_validar', array['uuid'], 'existe hay_pago_por_validar');
select has_column('public', 'reserva', 'nota_cancelacion', 'reserva.nota_cancelacion');
select throws_ok($$update public.reserva set nota_cancelacion = repeat('x', 301)$$, '23514', null, 'la nota admite 300 caracteres como maximo');
select throws_ok($$update public.reserva set nota_cancelacion = E'a\u0007b'$$, '23514', null, 'la nota no admite controles');

-- c1 (dueno) con pagos: tiene_pagos, tambien con nota
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000001', 'quiero mi dinero')$$, 'P0001', 'tiene_pagos', 'el dueno con pagos recibe tiene_pagos aun con nota');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000001')$$, 'P0001', 'tiene_pagos', 'y sin nota');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000003')$$, 'el dueno cancela sin pagos y sin nota');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000004', '  Me surgio un viaje  ')$$, 'el dueno cancela sin pagos con nota opcional');
reset role;
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'pre_reservada', 'la del dueno con pagos sigue pre_reservada');
select is((select nota_cancelacion from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000004'), 'Me surgio un viaje', 'la nota se guarda recortada');
select is((select nota_cancelacion from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000003'), null, 'sin nota queda null');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_cliente'), 4, 'dos cancelaciones del cliente por dos administradores');
select is((select count(distinct destinatario)::int from public.notificacion where tipo = 'reserva_cancelada_cliente' and destinatario in ('ad@t.pe', 'ad2@t.pe')), 2, 'avisa a cada administrador');
select ok((select datos ->> 'folio' is not null and datos ->> 'cliente' = 'Ana Cliente' and datos ? 'inicio'
  from public.notificacion where tipo = 'reserva_cancelada_cliente' limit 1), 'el aviso a administradores lleva folio, cliente e inicio');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_estudio'), 0, 'cuando cancela el cliente no hay aviso del estudio');

-- personal: no cancela
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', 'x')$$, '42501', null, 'el personal no cancela');

-- administrador
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002')$$, 'P0001', 'nota_requerida', 'con pagos exige nota');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', '   ')$$, 'P0001', 'nota_requerida', 'la nota en blanco no vale');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', repeat('x', 301))$$, '22023', 'nota_invalida', 'mas de 300 caracteres: nota_invalida');
select throws_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', E'a\u0007b')$$, '22023', 'nota_invalida', 'con controles: nota_invalida');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000002', 'Reembolso de S/ 25 por yape')$$, 'con pagos y nota, cancela');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000006')$$, 'sin pagos la nota es opcional');
select lives_ok($$select public.cancelar_reserva('bbbbbbbb-0000-0000-0000-000000000005', 'Averia en la sala')$$, 'una confirmada con pagos tambien, con nota');
reset role;
select is((select estado || '/' || motivo_cancelacion || '/' || nota_cancelacion from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000002'), 'cancelada/administrador/Reembolso de S/ 25 por yape', 'queda cancelada con su nota');
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_estudio' and destinatario = 'cli@t.pe'), 3, 'avisa al cliente por cada cancelacion del estudio');
select is((select datos ->> 'nota' from public.notificacion where tipo = 'reserva_cancelada_estudio' and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000002'), 'Reembolso de S/ 25 por yape', 'el aviso al cliente lleva la nota');

-- hay_pago_por_validar: el personal solo sabe si lo hay, sin ver el comprobante
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000007', auth.uid(), 'yape', 25, 'OP-0001', auth.uid() || '/a1.png', 'image/png');
select is(public.hay_pago_por_validar('bbbbbbbb-0000-0000-0000-000000000007'), false, 'un cliente no usa la funcion (siempre false)');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.comprobante_pago), 0, 'el personal sigue sin ver comprobantes');
select is(public.hay_pago_por_validar('bbbbbbbb-0000-0000-0000-000000000007'), true, 'el personal sabe que hay un pago por validar');
select is(public.hay_pago_por_validar('bbbbbbbb-0000-0000-0000-000000000003'), false, 'y que otra reserva no lo tiene');
reset role;
set local role anon;
select throws_ok($$select public.hay_pago_por_validar(gen_random_uuid())$$, '42501', null, 'anon no la ejecuta');
reset role;

select * from finish();
rollback;
