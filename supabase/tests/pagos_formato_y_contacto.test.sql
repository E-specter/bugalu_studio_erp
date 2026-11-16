begin;
create extension if not exists pgtap with schema extensions;
select plan(15);

-- RF-05 (3a): formato de numero_operacion, contacto_estudio y aprobar sobre una reserva cancelada.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'd1@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.instruccion_pago set texto = 'Cuenta de prueba', activo = true where metodo = 'yape';

insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select 'bbbbbbbb-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-0000000000d1', sa.id, se.id,
  '2027-07-01 10:00-05', '2027-07-01 11:00-05', 50, 'pre_reservada', now() + interval '10 minutes'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto)
values ('cccccccc-0000-0000-0000-0000000000d1', 'bbbbbbbb-0000-0000-0000-0000000000d1', 'al_reservar', 50);

-- contacto_estudio (estado conocido: vacio, como nace)
update public.contacto_estudio set texto = '';
select is((select count(*)::int from public.contacto_estudio), 1, 'una fila de contacto');
select is((select texto from public.contacto_estudio), '', 'baseline vacio');
select throws_ok($$insert into public.contacto_estudio (id, texto) values (false, 'x')$$, null, null, 'no se agrega otra fila');

set local role anon;
select throws_ok($$select * from public.contacto_estudio$$, '42501', null, 'anon no lee el contacto');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select lives_ok($$select * from public.contacto_estudio$$, 'un cliente lee el contacto');
update public.contacto_estudio set texto = 'hackeado';
reset role;
select is((select texto from public.contacto_estudio), '', 'un cliente no cambia el contacto');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
update public.contacto_estudio set texto = 'Escribenos al 999 999 999';
select is((select texto from public.contacto_estudio), 'Escribenos al 999 999 999', 'el administrador lo actualiza');
select throws_ok($$update public.contacto_estudio set texto = repeat('x', 501)$$, '23514', null, 'maximo 500');
reset role;

-- numero_operacion: 4 a 40 letras, cifras o guiones
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000d1","role":"authenticated"}', true);
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-0000000000d1', auth.uid(), 'yape', 50, 'AB1', auth.uid() || '/a.png', 'image/png')$$,
  '23514', null, 'menos de 4 caracteres');
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('cccccccc-0000-0000-0000-0000000000d1', auth.uid(), 'yape', 50, 'AB 12', auth.uid() || '/a.png', 'image/png')$$,
  '23514', null, 'sin espacios ni simbolos');
select lives_ok($$insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values ('aaaaaaaa-0000-0000-0000-0000000000d1', 'cccccccc-0000-0000-0000-0000000000d1', auth.uid(), 'yape', 50, 'AB-12', auth.uid() || '/a.png', 'image/png')$$,
  'un numero valido entra');
reset role;

-- Aprobar con la reserva cancelada: cuota pagada, reserva intacta.
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'administrador'
where id = 'bbbbbbbb-0000-0000-0000-0000000000d1';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select public.aprobar_pago('aaaaaaaa-0000-0000-0000-0000000000d1');
reset role;
select is((select estado || '/' || (select estado from public.reserva where id = 'bbbbbbbb-0000-0000-0000-0000000000d1')
  from public.cuota where id = 'cccccccc-0000-0000-0000-0000000000d1'), 'pagada/cancelada',
  'aprobar sobre reserva cancelada paga la cuota y no reabre la reserva');

-- existe_pago distingue 403 de 404: un cliente ajeno ve que existe, pero no lo lee.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is(public.existe_pago('aaaaaaaa-0000-0000-0000-0000000000d1'), true, 'existe_pago ve un pago');
select is(public.existe_pago(gen_random_uuid()), false, 'existe_pago no inventa pagos');
reset role;
set local role anon;
select throws_ok($$select public.existe_pago(gen_random_uuid())$$, '42501', null, 'anon no usa existe_pago');
reset role;

select * from finish();
rollback;
