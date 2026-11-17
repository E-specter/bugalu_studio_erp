begin;
create extension if not exists pgtap with schema extensions;
select plan(3);

-- RF-20 CA-07: el plazo que se extiende al rechazar un pago es el guardado en la reserva, no el parametro vigente.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.instruccion_pago set texto = 'Cuenta de prueba', activo = true where metodo = 'yape';

insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago, parametros_aplicados)
select 'bbbbbbbb-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', sa.id, se.id,
  '2027-06-01 10:00-05', '2027-06-01 11:00-05', 50, 'pre_reservada', now() + interval '10 minutes',
  public.parametros_vigentes() || '{"horas_limite_pago": 1}'::jsonb
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo';
insert into public.cuota (id, id_reserva, hito, monto)
values ('cccccccc-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001', 'al_reservar', 25);

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
values ('aaaaaaaa-0000-0000-0000-000000000001', 'cccccccc-0000-0000-0000-000000000001', auth.uid(), 'yape', 25, 'OP-1', auth.uid() || '/a1.png', 'image/png');
reset role;

-- El administrador sube despues el parametro vigente a 24 h: la reserva siguio con su hora.
update public.parametro set valor = 24 where clave = 'horas_limite_pago';
update public.reserva set vence_pago = now() - interval '1 minute' where id = 'bbbbbbbb-0000-0000-0000-000000000001';

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.rechazar_pago('aaaaaaaa-0000-0000-0000-000000000001', 'el monto no coincide')$$, 'el administrador rechaza');
reset role;
select ok((select vence_pago > now() + interval '50 minutes' from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'),
  'la extension es de 1 h: el plazo ya no baja de ahora + 1 h');
select ok((select vence_pago < now() + interval '2 hours' from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'),
  'la extension no usa las 24 h del parametro vigente');

select * from finish();
rollback;
