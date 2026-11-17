begin;
create extension if not exists pgtap with schema extensions;
select plan(41);

-- RF-18, correcciones de la auditoria A (ronda 2): eleccion tras el estudio con una captura en validacion (y pago tardio
-- sumado a la devolucion), la diferencia de una reprogramacion vuelve a sus creditos de origen, vence_pago al reprogramar
-- sin costo y decision total de una devolucion con el credito congelado que recibio credito devuelto.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.instruccion_pago set texto = 'x', activo = true where metodo = 'yape';

-- Ayudas de prueba. Reserva n: id bbbbbbbb-...-0n, sala propia, cuota de adelanto cccccccc-...-0n (100) y de saldo
-- dddddddd-...-0n (100); credito n: eeeeeeee-...-0n, de origen la reserva 0 (cancelada).
create function public.t_id(p text, p_n int) returns uuid language sql immutable as $$
  select (p || '-0000-0000-0000-0000000000' || lpad(p_n::text, 2, '0'))::uuid $$;
create function public.t_reserva(p_n int, p_horas int, p_estado text, p_vence_horas int default 1000, p_motivo text default null)
returns void language plpgsql as $$
begin
  insert into public.sala_tecnica (id, nombre, sede) values (public.t_id('5a5a5a5a', p_n), 'Sala t' || p_n, 'Sede t');
  insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago, creada_en)
  select public.t_id('bbbbbbbb', p_n), '00000000-0000-0000-0000-0000000000c1', public.t_id('5a5a5a5a', p_n), se.id,
    date_trunc('hour', now()) + p_horas * interval '1 hour', date_trunc('hour', now()) + p_horas * interval '1 hour' + interval '1 hour',
    200, p_estado, p_motivo, now() + p_vence_horas * interval '1 hour', now() - interval '30 days'
  from public.servicio se where se.nombre = 'Ensayo';
  insert into public.cuota (id, id_reserva, hito, monto) values
    (public.t_id('cccccccc', p_n), public.t_id('bbbbbbbb', p_n), 'al_reservar', 100),
    (public.t_id('dddddddd', p_n), public.t_id('bbbbbbbb', p_n), 'al_terminar', 100);
end $$;
create function public.t_credito(p_n int, p_monto numeric, p_aplicado numeric, p_tipo text,
  p_vence timestamptz default '2031-01-01 12:00-05', p_estado text default null)
returns void language plpgsql as $$
begin
  insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence, estado)
  values (public.t_id('eeeeeeee', p_n), '00000000-0000-0000-0000-0000000000c1', public.t_id('bbbbbbbb', 0), p_tipo, p_monto,
    p_monto - p_aplicado, p_vence, coalesce(p_estado, case when p_monto = p_aplicado then 'agotado' else 'vigente' end));
  if p_aplicado > 0 then
    insert into public.aplicacion_credito (id_credito, id_cuota, monto, id_usuario)
    values (public.t_id('eeeeeeee', p_n), public.t_id('cccccccc', p_n), p_aplicado, '00000000-0000-0000-0000-0000000000c1');
    update public.cuota set pagado = pagado + p_aplicado where id = public.t_id('cccccccc', p_n);
  end if;
end $$;
create function public.t_efectivo(p_n int, p_monto numeric) returns void language sql as $$
  update public.cuota set pagado = pagado + p_monto where id = public.t_id('cccccccc', p_n) $$;
create function public.t_pagada(p_n int) returns void language sql as $$
  update public.cuota set estado = 'pagada' where id = public.t_id('cccccccc', p_n) and pagado >= monto $$;
-- La captura de una cuota la registra el cliente (el disparador comprueba identidad y plazo); `p_saldo`: la del saldo.
create function public.t_captura(p_n int, p_monto numeric, p_op text, p_saldo boolean default false) returns void language plpgsql as $$
begin
  set local role authenticated;
  perform set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
  insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values (public.t_id(case when p_saldo then 'dddddddd' else 'cccccccc' end, p_n), auth.uid(), 'yape', p_monto, p_op, auth.uid() || '/a.png', 'image/png');
  reset role;
end $$;
create function public.t_como(p_quien text) returns void language plpgsql as $$
begin
  set local role authenticated;
  perform set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000' || p_quien || '","role":"authenticated"}', true);
end $$;

select public.t_reserva(0, -500, 'cancelada', 1000, 'cliente');

-- 1. Con una captura en validacion no se elige tras una cancelacion del estudio (R4 del auditor: credito 40 + efectivo 60
-- en el adelanto, captura de 50 en el saldo).
select public.t_reserva(10, 300, 'confirmada');
select public.t_credito(10, 40, 40, 'nivel_1');
select public.t_efectivo(10, 60);
select public.t_pagada(10);
select public.t_captura(10, 50, 'OP-10', true);
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 10), 'Averia de la sala', null, 'estudio');
reset role;
select public.t_como('c1');
select throws_ok($$select public.elegir_estudio_devolucion(public.t_id('bbbbbbbb', 10))$$, 'P0001', 'eleccion_no_disponible',
  'devolucion: con una captura en validacion no se elige');
select throws_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 10), date_trunc('hour', now()) + interval '500 hours', null, null, null, '{}', null)$$,
  'P0001', 'eleccion_no_disponible', 'reprogramar sin costo: con una captura en validacion no se elige');
select throws_ok($$select * from public.vista_reprogramacion(public.t_id('bbbbbbbb', 10), date_trunc('hour', now()) + interval '500 hours', null)$$,
  'P0001', 'eleccion_no_disponible', 'la vista previa tampoco');
reset role;
select is((select eleccion_estudio from public.reserva where id = public.t_id('bbbbbbbb', 10)), 'pendiente', 'la eleccion sigue pendiente');
select public.t_como('ad');
select lives_ok($$select public.aprobar_pago((select p.id from public.comprobante_pago p where p.numero_operacion = 'OP-10'))$$, 'se aprueba la captura');
reset role;
select public.t_como('c1');
select lives_ok($$select public.elegir_estudio_devolucion(public.t_id('bbbbbbbb', 10))$$, 'validada la captura, elige la devolucion');
reset role;
select is((select sum(monto_aprobado) from public.devolucion where id_reserva = public.t_id('bbbbbbbb', 10) and tipo = 'estudio'), 110.00::numeric,
  'devolucion en dinero: 60 de efectivo + 50 de la captura');
select results_eq($$select saldo, estado from public.credito where id = public.t_id('eeeeeeee', 10)$$,
  $$values (40.00::numeric, 'vigente')$$, 'el credito aplicado vuelve a su origen');
select is((select r.retenido + coalesce((select sum(a.devuelto) from public.aplicacion_credito a join public.cuota c on c.id = a.id_cuota
    where c.id_reserva = r.id), 0) + coalesce((select sum(k.monto) from public.credito k where k.id_reserva = r.id), 0)
    + coalesce((select sum(d.monto_aprobado) from public.devolucion d where d.id_reserva = r.id), 0)
  from public.reserva r where r.id = public.t_id('bbbbbbbb', 10)),
  (select sum(pagado) from public.cuota where id_reserva = public.t_id('bbbbbbbb', 10)),
  'R4: retenido + devuelto + credito + devolucion = lo pagado');

-- Defensa: un pago tardio aprobado tras una eleccion `devolucion` ya registrada se suma a la devolucion (n11: ya habia una
-- de 100; n12: no habia ninguna, todo era credito).
select public.t_reserva(11, 310, 'confirmada');
select public.t_efectivo(11, 100);
select public.t_pagada(11);
select public.t_captura(11, 50, 'OP-11', true);
select public.t_reserva(12, 320, 'confirmada');
select public.t_credito(12, 100, 100, 'nivel_1');
select public.t_pagada(12);
select public.t_captura(12, 50, 'OP-12', true);
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 11), 'Averia de la sala', null, 'estudio');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 12), 'Averia de la sala', null, 'estudio');
reset role;
update public.reserva set eleccion_estudio = 'devolucion' where id in (public.t_id('bbbbbbbb', 11), public.t_id('bbbbbbbb', 12));
insert into public.devolucion (id_reserva, id_cliente, tipo, motivo, monto_solicitado, estado, monto_aprobado, decidida_en, limite)
values (public.t_id('bbbbbbbb', 11), '00000000-0000-0000-0000-0000000000c1', 'estudio', 'Devolucion integral', 100, 'aprobada', 100, now(), now());
select public.t_como('ad');
select lives_ok($$select public.aprobar_pago((select p.id from public.comprobante_pago p where p.numero_operacion = 'OP-11'))$$, 'se aprueba el pago tardio de n11');
select lives_ok($$select public.aprobar_pago((select p.id from public.comprobante_pago p where p.numero_operacion = 'OP-12'))$$, 'se aprueba el pago tardio de n12');
reset role;
select is((select sum(monto_aprobado) from public.devolucion where id_reserva = public.t_id('bbbbbbbb', 11)), 150.00::numeric,
  'n11: el pago tardio se suma a lo devuelto');
select is((select count(*)::int from public.devolucion where id_reserva = public.t_id('bbbbbbbb', 12) and tipo = 'estudio'
  and estado = 'aprobada' and monto_aprobado = 50), 1, 'n12: sin devolucion previa, se crea una aprobada de 50');
select is((select count(*)::int from public.credito where id_reserva in (public.t_id('bbbbbbbb', 11), public.t_id('bbbbbbbb', 12))), 0,
  'el pago tardio no genera credito');
select is((select pagado_cancelacion from public.reserva where id = public.t_id('bbbbbbbb', 11)), 150.00::numeric, 'pagado_cancelacion al dia');

-- 2. La diferencia a favor de una reprogramacion vuelve primero a sus creditos de origen (tipo y vencimiento).
select public.t_reserva(1, 100, 'confirmada');
select public.t_credito(1, 100, 100, 'nivel_2', now() + interval '2 days');
select public.t_pagada(1);
select public.t_reserva(2, 100, 'confirmada');
select public.t_credito(2, 100, 100, 'nivel_1', now() + interval '2 days');
select public.t_pagada(2);
select public.t_reserva(3, 100, 'confirmada'); -- 30 de credito + 70 de efectivo; el total baja a 50
select public.t_credito(3, 100, 30, 'nivel_1', now() + interval '2 days');
select public.t_efectivo(3, 70);
select public.t_pagada(3);
select public.t_como('c1');
select lives_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 1), date_trunc('hour', now()) + interval '120 hours', 1, 80, null, '{}', 80)$$, 'R1: reprograma a 80');
select lives_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 2), date_trunc('hour', now()) + interval '120 hours', 1, 80, null, '{}', 80)$$, 'R1b: reprograma a 80');
select lives_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 3), date_trunc('hour', now()) + interval '120 hours', 1, 50, null, '{}', 50)$$, 'R1c: reprograma a 50');
reset role;
select results_eq($$select tipo, saldo, estado, vence < now() + interval '3 days' from public.credito where id = public.t_id('eeeeeeee', 1)$$,
  $$values ('nivel_2', 20.00::numeric, 'vigente', true)$$, 'R1: los 20 vuelven al credito nivel_2 con su vencimiento (2 dias, no 30)');
select results_eq($$select tipo, saldo, estado from public.credito where id = public.t_id('eeeeeeee', 2)$$,
  $$values ('nivel_1', 20.00::numeric, 'vigente')$$, 'R1b: el credito nivel_1 sigue siendo nivel_1');
select is((select count(*)::int from public.credito where id_reserva in (public.t_id('bbbbbbbb', 1), public.t_id('bbbbbbbb', 2))), 0,
  'sin credito de reprogramacion cuando todo vuelve al origen');
select results_eq($$select k.tipo, k.monto, k.saldo from public.credito k where k.id_reserva = public.t_id('bbbbbbbb', 3)$$,
  $$values ('reprogramacion', 20.00::numeric, 20.00::numeric)$$, 'R1c: de los 50 de diferencia, 30 vuelven al origen y 20 son credito de reprogramacion');
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 3)), 100.00::numeric, 'R1c: el credito de origen recupera sus 30');
select is(public.pagado_neto(public.t_id('bbbbbbbb', 1)), 80.00::numeric, 'lo pagado neto tras reprogramar es el precio nuevo');

-- R2: la cadena credito aplicado -> reprogramar en nivel 2 -> cancelar en nivel 3 -> excepcion suma lo pagado.
select public.t_reserva(4, 40, 'confirmada');
select public.t_credito(4, 40, 40, 'nivel_1');
select public.t_efectivo(4, 60);
select public.t_pagada(4);
select public.t_como('c1');
select public.reprogramar_reserva(public.t_id('bbbbbbbb', 4), date_trunc('hour', now()) + interval '20 hours', 2, 200, null, '{}', 200);
select public.cancelar_reserva(public.t_id('bbbbbbbb', 4), null, 3);
reset role;
select public.t_como('ad');
select public.aplicar_excepcion(public.t_id('bbbbbbbb', 4), 'Motivo de la excepcion largo');
reset role;
select is((select (select sum(penalizacion) from public.reprogramacion where id_reserva = public.t_id('bbbbbbbb', 4))
  + (select sum(devuelto) from public.aplicacion_credito a join public.cuota c on c.id = a.id_cuota where c.id_reserva = public.t_id('bbbbbbbb', 4))
  + coalesce((select sum(monto) from public.credito where id_reserva = public.t_id('bbbbbbbb', 4)), 0)
  + (select retenido from public.reserva where id = public.t_id('bbbbbbbb', 4))), 100.00::numeric,
  'R2: penalizacion + devuelto + credito nuevo + retenido = lo pagado');

-- 3. R3: reprogramar sin costo una pre_reservada tras una cancelacion del estudio recalcula vence_pago.
select public.t_reserva(20, 300, 'pre_reservada', -1);
select public.t_credito(20, 100, 30, 'nivel_1');
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 20), 'Averia de la sala', null, 'estudio');
reset role;
select public.t_como('c1');
select lives_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 20), date_trunc('hour', now()) + interval '400 hours', null, null, null, '{}', null)$$,
  'R3: reprograma sin costo');
reset role;
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 20)), 'pre_reservada', 'vuelve a pre_reservada');
select ok((select vence_pago > now() from public.reserva where id = public.t_id('bbbbbbbb', 20)), 'con un plazo nuevo (RN-18)');
select ok((select vence_pago = r.inicio - (select valor from public.parametro where clave = 'dias_limite_pago') * interval '1 day'
  from public.reserva r where r.id = public.t_id('bbbbbbbb', 20)), 'lo mas tarde entre inicio - dias y ahora + horas (RN-18)');
select lives_ok($$select public.caducar_reservas()$$, 'caducar_reservas() corre');
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 20)), 'pre_reservada', 'R3: no la caduca al momento');

-- 4. La decision total aprueba lo solicitado aunque el credito congelado haya recibido credito devuelto.
select public.t_reserva(30, 300, 'pre_reservada', -1);
select public.t_credito(30, 100, 30, 'nivel_1');
select public.t_como('c1');
select lives_ok($$select public.solicitar_devolucion(public.t_id('eeeeeeee', 30), 'Quiero mi dinero de vuelta')$$, 'solicita la devolucion de 70');
reset role;
select public.caducar_reservas();
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 30)), 100.00::numeric, 'mientras esta pendiente el credito recibe 30 devueltos');
select public.t_como('ad');
select lives_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = public.t_id('eeeeeeee', 30)), 'total', null, null)$$, 'decide total');
reset role;
select results_eq($$select monto_solicitado, monto_aprobado from public.devolucion where id_credito = public.t_id('eeeeeeee', 30)$$,
  $$values (70.00::numeric, 70.00::numeric)$$, 'aprueba lo solicitado, no el saldo del momento');
select results_eq($$select saldo, estado, congelado from public.credito where id = public.t_id('eeeeeeee', 30)$$,
  $$values (30.00::numeric, 'vigente', false)$$, 'lo que sobra sigue como credito vigente');

-- 5. El administrador autenticado no cambia por update directo lo que solo mueven las funciones (n10: reserva con pagos).
select public.t_reserva(40, 300, 'confirmada');
select public.t_efectivo(40, 100);
select public.t_como('ad');
select throws_ok($$update public.reserva set retenido = 999 where id = public.t_id('bbbbbbbb', 40)$$, '42501', null, 'el administrador no cambia reserva.retenido');
select throws_ok($$update public.reserva set credito_generado = 999 where id = public.t_id('bbbbbbbb', 40)$$, '42501', null, 'ni reserva.credito_generado');
select throws_ok($$update public.reserva set pagado_cancelacion = 999 where id = public.t_id('bbbbbbbb', 40)$$, '42501', null, 'ni reserva.pagado_cancelacion');
select throws_ok($$update public.cuota set pagado = 999 where id = public.t_id('cccccccc', 40)$$, '42501', null, 'ni cuota.pagado');
reset role;
select results_eq($$select r.retenido, r.credito_generado, r.pagado_cancelacion, (select pagado from public.cuota where id = public.t_id('cccccccc', 40))
  from public.reserva r where r.id = public.t_id('bbbbbbbb', 40)$$, $$values (null::numeric, null::numeric, null::numeric, 100.00::numeric)$$, 'las filas quedan intactas');

select * from finish();
rollback;
