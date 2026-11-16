begin;
create extension if not exists pgtap with schema extensions;
select plan(79);

-- RF-05: comprobante_pago, aprobar_pago, rechazar_pago, instruccion_pago, avisos, tiene_pagos y storage `comprobantes`.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- r1 (c1, pre_reservada con plazo a 10 min), r2 (c1, cancelada), r3 (c2, pre_reservada).
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
select d.id, d.id_cliente, sa.id, se.id, d.inicio, d.inicio + interval '1 hour', 50, d.estado, d.motivo, d.vence
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-000000000001'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, '2027-06-01 10:00-05'::timestamptz, 'pre_reservada', null, now() + interval '10 minutes'),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', '2027-06-02 10:00-05', 'cancelada', 'cliente', now() + interval '10 minutes'),
    ('bbbbbbbb-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c2', '2027-06-03 10:00-05', 'pre_reservada', null, now() + interval '10 minutes')
  ) as d(id, id_cliente, inicio, estado, motivo, vence)
where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto) values
  ('cccccccc-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001', 'al_reservar', 25),
  ('cccccccc-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000001', 'al_terminar', 25),
  ('cccccccc-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000002', 'al_reservar', 25),
  ('cccccccc-0000-0000-0000-000000000004', 'bbbbbbbb-0000-0000-0000-000000000003', 'al_reservar', 25);

select has_table('public', 'comprobante_pago', 'existe comprobante_pago');
select has_table('public', 'instruccion_pago', 'existe instruccion_pago');
select has_function('public', 'aprobar_pago', array['uuid'], 'existe aprobar_pago');
select has_function('public', 'rechazar_pago', array['uuid', 'text'], 'existe rechazar_pago');
select is((select count(*)::int from public.instruccion_pago), 4, 'cuatro metodos de pago');
select is((select count(*)::int from public.instruccion_pago where metodo in ('transferencia', 'yape', 'plin', 'tarjeta')), 4, 'los cuatro metodos esperados');

-- Estado conocido: transferencia y yape activos; plin y tarjeta inactivos.
update public.instruccion_pago set texto = case when metodo in ('transferencia', 'yape') then 'Cuenta de prueba' else '' end,
  activo = metodo in ('transferencia', 'yape');

-- anon: nada
set local role anon;
select throws_ok($$select * from public.comprobante_pago$$, '42501', null, 'anon no lee comprobantes');
select throws_ok($$select public.aprobar_pago(gen_random_uuid())$$, '42501', null, 'anon no aprueba');
select throws_ok($$select public.rechazar_pago(gen_random_uuid(), 'x')$$, '42501', null, 'anon no rechaza');
select throws_ok($$select * from public.instruccion_pago$$, '42501', null, 'anon no lee instrucciones');
reset role;

-- c1 registra pagos
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
-- Restricciones y metodo (antes del primer pago: el trigger revisa la cuota primero)
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'plin', 25, 'OP-3', auth.uid() || '/a3.png', 'image/png')$$,
  'P0001', 'metodo_no_disponible', 'un metodo inactivo no se usa');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 0, 'OP-3', auth.uid() || '/a3.png', 'image/png')$$,
  '23514', null, 'monto > 0');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, E'OP\n3', auth.uid() || '/a3.png', 'image/png')$$,
  '23514', null, 'numero de operacion sin caracteres de control');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, '   ', auth.uid() || '/a3.png', 'image/png')$$,
  '23514', null, 'numero de operacion no vacio');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-3', auth.uid() || '/a3.gif', 'image/gif')$$,
  '23514', null, 'tipo de captura admitido');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-3', 'otra/a3.png', 'image/png')$$,
  '42501', null, 'la captura va en la carpeta del dueno');
select lives_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-1', auth.uid() || '/a1.png', 'image/png')$$,
  'c1 registra su pago');
select is((select estado from public.comprobante_pago where id = 'aaaaaaaa-0000-0000-0000-000000000001'), 'pendiente_validacion', 'nace pendiente_validacion');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'transferencia', 25, 'OP-2', auth.uid() || '/a2.png', 'image/png')$$,
  'P0001', 'pago_en_validacion', 'una cuota no admite otro pago en validacion');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000004', auth.uid(), 'yape', 25, 'OP-3', auth.uid() || '/a3.png', 'image/png')$$,
  '42501', null, 'c1 no paga la cuota de c2');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c2', 'yape', 25, 'OP-3', '00000000-0000-0000-0000-0000000000c2/a3.png', 'image/png')$$,
  '42501', null, 'c1 no registra a nombre de otro');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura, estado)
  values ('cccccccc-0000-0000-0000-000000000002', auth.uid(), 'yape', 25, 'OP-3', auth.uid() || '/a3.png', 'image/png', 'aprobado')$$,
  '42501', null, 'c1 no fija el estado');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000002', auth.uid(), 'yape', 25, 'OP-3', auth.uid() || '/a3.png', 'image/png')$$,
  'P0001', 'cuota_no_pagable', 'al_terminar no se paga con la reserva pre_reservada');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000003', auth.uid(), 'yape', 25, 'OP-3', auth.uid() || '/a3.png', 'image/png')$$,
  'P0001', 'cuota_no_pagable', 'una reserva cancelada no se paga');
select is((select count(*)::int from public.comprobante_pago), 1, 'c1 solo ve el suyo');
select throws_ok($$update public.comprobante_pago set estado = 'aprobado'$$, '42501', null, 'c1 no actualiza');
select throws_ok($$delete from public.comprobante_pago$$, '42501', null, 'c1 no borra');
select is((select count(*)::int from public.instruccion_pago), 2, 'c1 ve solo las instrucciones activas');
update public.instruccion_pago set texto = 'x';
reset role;
select is((select count(*)::int from public.instruccion_pago where texto = 'x'), 0, 'c1 no edita instrucciones (la RLS no deja filas)');

-- c2: operacion repetida (normalizada) con el mismo metodo, y no ve el pago ajeno
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000004', auth.uid(), 'yape', 25, ' op-1 ', auth.uid() || '/b1.png', 'image/png')$$,
  'P0001', 'operacion_duplicada', 'operacion repetida con el mismo metodo');
select lives_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-000000000002', 'cccccccc-0000-0000-0000-000000000004', auth.uid(), 'transferencia', 25, 'OP-1', auth.uid() || '/b1.pdf', 'application/pdf')$$,
  'la misma operacion con otro metodo si');
select is((select count(*)::int from public.comprobante_pago), 1, 'c2 solo ve el suyo');
reset role;

-- Un pago registrado detiene la caducidad y mantiene la ocupacion
update public.reserva set vence_pago = now() - interval '1 minute' where id = 'bbbbbbbb-0000-0000-0000-000000000001';
select is(public.tiene_pagos('bbbbbbbb-0000-0000-0000-000000000001'), true, 'tiene_pagos cuenta el pago en validacion');
select public.caducar_reservas();
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'pre_reservada', 'caducar_reservas respeta el pago en validacion');
select is((select count(*)::int from public.ocupacion_sala((select id_sala from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), '2027-06-01 00:00-05', '2027-06-02 00:00-05')), 1, 'ocupacion_sala no libera el tramo');
update public.reserva set vence_pago = now() + interval '10 minutes' where id = 'bbbbbbbb-0000-0000-0000-000000000001';

-- Aviso al registrarse: un pago_registrado por administrador
select is((select count(*)::int from public.notificacion where tipo = 'pago_registrado' and datos ->> 'id_pago' = 'aaaaaaaa-0000-0000-0000-000000000001'),
  (select count(*)::int from public.usuario where rol = 'administrador'), 'un pago_registrado por administrador');
select is((select count(*)::int from public.notificacion where tipo = 'pago_registrado' and destinatario = 'ad@t.pe' and datos ->> 'folio' is not null), 2, 'el aviso al administrador lleva folio (dos pagos)');

-- Validacion: solo administrador
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000001')$$, '42501', null, 'el cliente no aprueba');
select throws_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', 'x')$$, '42501', null, 'el cliente no rechaza');
reset role;
select is((select estado from public.comprobante_pago where id = 'aaaaaaaa-0000-0000-0000-000000000001'), 'pendiente_validacion', 'el pago sigue intacto');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.comprobante_pago), 2, 'el administrador lee todos');
select throws_ok($$select public.aprobar_pago(gen_random_uuid())$$, 'P0002', null, 'aprobar inexistente: P0002');
select throws_ok($$select public.rechazar_pago(gen_random_uuid(), 'x')$$, 'P0002', null, 'rechazar inexistente: P0002');
select throws_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', '  ')$$, '22023', 'motivo_invalido', 'rechazar sin motivo');
select throws_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', repeat('x', 301))$$, '22023', 'motivo_invalido', 'rechazar con motivo largo');
select lives_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', 'el monto no coincide')$$, 'el administrador rechaza');
select throws_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', 'otra vez')$$, 'P0001', 'pago_ya_validado', 'rechazar dos veces');
select throws_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000001')$$, 'P0001', 'pago_ya_validado', 'aprobar uno ya rechazado');
reset role;

select is((select estado || '|' || motivo_rechazo from public.comprobante_pago where id = 'aaaaaaaa-0000-0000-0000-000000000001'), 'rechazado|el monto no coincide', 'queda rechazado con motivo');
select is((select validado_en is not null and id_validador = '00000000-0000-0000-0000-0000000000ad' from public.comprobante_pago where id = 'aaaaaaaa-0000-0000-0000-000000000001'), true, 'queda quien y cuando valido');
select is((select estado from public.cuota where id = 'cccccccc-0000-0000-0000-000000000001'), 'pendiente', 'la cuota sigue pendiente');
select is((select vence_pago > now() + interval '50 minutes' from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), true, 'rechazo sin otro pago: nuevo plazo de la hora');
select is((select count(*)::int from public.notificacion where tipo = 'pago_rechazado' and destinatario = 'cli@t.pe'
  and datos ->> 'motivo' = 'el monto no coincide' and datos ->> 'folio' is not null and datos ->> 'monto' is not null and datos ->> 'hito' = 'al_reservar'), 1, 'aviso de rechazo al cliente');
select is(public.tiene_pagos('bbbbbbbb-0000-0000-0000-000000000001'), false, 'un pago rechazado no cuenta en tiene_pagos');

-- Rechazado: la misma operacion se puede repetir y la cuota admite otro pago
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-000000000003', 'cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-1', auth.uid() || '/a4.jpg', 'image/jpeg')$$,
  'tras el rechazo se repite la operacion');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000003')$$, 'el administrador aprueba');
select throws_ok($$select public.aprobar_pago('aaaaaaaa-0000-0000-0000-000000000003')$$, 'P0001', 'pago_ya_validado', 'aprobar dos veces');
select throws_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000003', 'tarde')$$, 'P0001', 'pago_ya_validado', 'una aprobacion no se deshace');
reset role;
select is((select estado from public.cuota where id = 'cccccccc-0000-0000-0000-000000000001'), 'pagada', 'la cuota queda pagada');
select is((select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'), 'confirmada', 'la reserva queda confirmada');
select is((select count(*)::int from public.notificacion where tipo = 'pago_aprobado' and destinatario = 'cli@t.pe'
  and datos ->> 'folio' is not null and datos ->> 'monto' is not null and (datos ->> 'reserva_confirmada')::boolean), 1, 'aviso de aprobacion al cliente');

-- Con la reserva confirmada: la cuota pagada no admite pago y la al_terminar si
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-9', auth.uid() || '/a5.png', 'image/png')$$,
  'P0001', 'cuota_pagada', 'una cuota pagada no admite pago');
select lives_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-000000000004', 'cccccccc-0000-0000-0000-000000000002', auth.uid(), 'transferencia', 25, 'OP-10', auth.uid() || '/a6.png', 'image/png')$$,
  'al_terminar se paga con la reserva confirmada');
reset role;
select is((select count(*)::int from pg_indexes where tablename = 'comprobante_pago' and indexdef ilike '%unique%'), 3, 'indices unicos: pk, un pendiente por cuota y operacion');

-- instruccion_pago: el administrador edita
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.instruccion_pago), 4, 'el administrador ve las cuatro');
select lives_ok($$update public.instruccion_pago set texto = 'Plin 999', activo = true where metodo = 'plin'$$, 'el administrador edita');
select throws_ok($$update public.instruccion_pago set activo = true, texto = '' where metodo = 'tarjeta'$$, '23514', null, 'no se activa un metodo sin texto');
select throws_ok($$update public.instruccion_pago set texto = repeat('x', 1001) where metodo = 'tarjeta'$$, '23514', null, 'texto hasta 1000');
reset role;

-- Storage: bucket y politicas
select is((select file_size_limit from storage.buckets where id = 'comprobantes'), 5242880::bigint, 'bucket limitado a 5 MB');
select is((select allowed_mime_types from storage.buckets where id = 'comprobantes'), array['image/jpeg', 'image/png', 'application/pdf'], 'bucket limitado a jpg, png y pdf');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('comprobantes', '00000000-0000-0000-0000-0000000000c1/p.png', auth.uid()::text)$$, 'c1 sube a su carpeta');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('comprobantes', '00000000-0000-0000-0000-0000000000c2/p.png', auth.uid()::text)$$, '42501', null, 'c1 no sube a la carpeta de otro');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('comprobantes', 'p.png', auth.uid()::text)$$, '42501', null, 'c1 no sube a la raiz');
select is((select count(*)::int from storage.objects where bucket_id = 'comprobantes'), 1, 'c1 lee lo suyo');
update storage.objects set name = '00000000-0000-0000-0000-0000000000c1/q.png' where bucket_id = 'comprobantes';
reset role;
select is((select name from storage.objects where bucket_id = 'comprobantes'), '00000000-0000-0000-0000-0000000000c1/p.png', 'nadie actualiza ni borra (el objeto sigue igual; el borrado directo lo bloquea ademas storage.protect_delete)');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from storage.objects where bucket_id = 'comprobantes'), 0, 'c2 no ve lo de c1');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from storage.objects where bucket_id = 'comprobantes'), 1, 'el administrador lee todo');
select throws_ok($$insert into storage.objects (bucket_id, name, owner_id) values ('comprobantes', '00000000-0000-0000-0000-0000000000c1/z.png', auth.uid()::text)$$, '42501', null, 'el administrador no sube a carpeta ajena');
reset role;
set local role anon;
select is((select count(*)::int from storage.objects where bucket_id = 'comprobantes'), 0, 'anon no lee');
reset role;

select * from finish();
rollback;
