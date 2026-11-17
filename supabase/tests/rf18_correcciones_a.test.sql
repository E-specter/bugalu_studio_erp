begin;
create extension if not exists pgtap with schema extensions;
select plan(72);

-- RF-18, correcciones de la auditoria A (ronda 1): el credito aplicado no detiene la caducidad, avanzar_reservas sin
-- carrera, el credito aplicado vuelve a su origen al cancelar, barrera de salida de cancelada/no_asistio/anulada,
-- aviso al confirmar con credito, cuota pagada solo si lo aplicado la cubre y creada_en de las reservas existentes.
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
-- La captura de una cuota la registra el cliente (el disparador comprueba identidad y plazo).
create function public.t_captura(p_n int, p_monto numeric, p_op text) returns void language plpgsql as $$
begin
  set local role authenticated;
  perform set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
  insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  values (public.t_id('cccccccc', p_n), auth.uid(), 'yape', p_monto, p_op, auth.uid() || '/a.png', 'image/png');
  reset role;
end $$;

select public.t_reserva(0, -500, 'cancelada', 1000, 'cliente');

-- 1. El credito aplicado no detiene el plazo de pago ni la caducidad.
-- n1: credito parcial (30) con el plazo vencido; n2 igual con el credito de origen ya vencido; n3 con 30 de credito y el
-- resto (70) en validacion.
select public.t_reserva(1, 300, 'pre_reservada', -1);
select public.t_reserva(2, 310, 'pre_reservada', -1);
select public.t_reserva(3, 320, 'pre_reservada', 10);
select public.t_credito(1, 100, 30, 'nivel_2');
select public.t_credito(2, 100, 30, 'nivel_2', now() - interval '1 day', 'vencido');
select public.t_credito(3, 100, 30, 'nivel_1');
select public.t_captura(3, 70, 'OP-3');
update public.reserva set vence_pago = now() - interval '1 hour' where id = public.t_id('bbbbbbbb', 3);

select lives_ok($$select public.caducar_reservas()$$, 'caducar_reservas() corre');
select is((select estado || '/' || motivo_cancelacion from public.reserva where id = public.t_id('bbbbbbbb', 1)), 'cancelada/caducada',
  'credito parcial con el plazo vencido: la pre-reserva caduca');
select results_eq($$select saldo, estado, vence from public.credito where id = public.t_id('eeeeeeee', 1)$$,
  $$values (100.00::numeric, 'vigente', '2031-01-01 12:00-05'::timestamptz)$$, 'el credito aplicado vuelve a su origen con su vencimiento');
select results_eq($$select saldo, estado, vence from public.credito where id = public.t_id('eeeeeeee', 2)$$,
  $$values (100.00::numeric, 'vigente', public.fin_de_dia_lima(now(), 7))$$, 'si el origen ya vencio: 7 dias desde la caducidad, fin del dia en Lima');
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 3)), 'pre_reservada', 'la captura en validacion si detiene la caducidad');
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 3)), 70.00::numeric, 'y no devuelve el credito mientras la reserva sigue viva');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.rechazar_pago((select id from public.comprobante_pago where numero_operacion = 'OP-3'), 'No coincide')$$, 'rechaza la captura del resto');
reset role;
select ok((select vence_pago > now() from public.reserva where id = public.t_id('bbbbbbbb', 3)), 'rechazar con credito parcial amplia el plazo (RN-18)');

-- n4: unico pago = credito, plazo vencido y fin pasado: avanzar_reservas no la deja en no_asistio.
select public.t_reserva(4, -3, 'pre_reservada', -5);
select public.t_credito(4, 100, 30, 'nivel_1');
select lives_ok($$select public.avanzar_reservas()$$, 'avanzar_reservas() corre');
select isnt((select estado from public.reserva where id = public.t_id('bbbbbbbb', 4)), 'no_asistio', 'un unico pago en credito nunca es no_asistio');
select is((select retenido from public.reserva where id = public.t_id('bbbbbbbb', 4)), null, 'no se retiene nada');
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 4)), 100.00::numeric, 'el credito vuelve al cliente');

-- 2. avanzar_reservas vuelve a comprobar el estado tras bloquear. Carrera simulada: al marcar la primera, un disparador
-- confirma la segunda, que el cursor de la seleccion aun ve como pre_reservada.
select public.t_reserva(5, 5, 'pre_reservada', 10);
select public.t_reserva(6, 8, 'pre_reservada', 10);
select public.t_captura(5, 100, 'OP-5');
select public.t_captura(6, 100, 'OP-6');
update public.reserva
set inicio = date_trunc('hour', now()) - interval '3 hours', fin = date_trunc('hour', now()) - interval '2 hours',
    fin_buffer = date_trunc('hour', now()) - interval '90 minutes', vence_pago = now() - interval '1 hour'
where id in (public.t_id('bbbbbbbb', 5), public.t_id('bbbbbbbb', 6));
create function public.t_carrera() returns trigger language plpgsql as $$
begin
  update public.reserva set estado = 'confirmada' where id = public.t_id('bbbbbbbb', 6) and estado = 'pre_reservada';
  return null;
end $$;
create trigger t_carrera after insert on public.notificacion for each row when (new.tipo = 'inasistencia_marcada')
  execute function public.t_carrera();
select lives_ok($$select public.avanzar_reservas()$$, 'avanzar_reservas() con la carrera');
drop trigger t_carrera on public.notificacion;
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 5)), 'no_asistio', 'la que sigue pre_reservada pasa a no_asistio');
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 6)), 'finalizada', 'la confirmada entre la seleccion y el bloqueo sigue su ruta a finalizada');
select is((select count(*)::int from public.notificacion where tipo = 'inasistencia_marcada'), 1, 'solo se avisa la inasistencia realmente marcada');

-- 3. Cancelar o aplicar la excepcion: el credito aplicado vuelve a su origen; solo el resto es credito nuevo.
-- Total 200, adelanto 100; +73 h = nivel 1, +31 h = nivel 2 (penalizacion 50), +11 h = nivel 3.
select public.t_reserva(10, 73, 'confirmada');
select public.t_credito(10, 100, 100, 'nivel_2');
select public.t_reserva(11, 73, 'confirmada');
select public.t_credito(11, 40, 40, 'reprogramacion');
select public.t_efectivo(11, 60);
select public.t_reserva(12, 31, 'confirmada');
select public.t_credito(12, 80, 80, 'nivel_1');
select public.t_efectivo(12, 20);
select public.t_reserva(13, 31, 'confirmada');
select public.t_credito(13, 100, 100, 'nivel_2');
select public.t_reserva(14, 11, 'confirmada');
select public.t_credito(14, 50, 50, 'reprogramacion');
select public.t_efectivo(14, 50);
select public.t_reserva(15, 11, 'confirmada');
select public.t_credito(15, 100, 100, 'nivel_2');
select public.t_reserva(16, 73, 'confirmada');
select public.t_credito(16, 100, 100, 'nivel_1', now() - interval '1 day');
select public.t_reserva(20, 100, 'confirmada');
select public.t_efectivo(20, 100);
update public.cuota set estado = 'pagada' where hito = 'al_reservar' and pagado >= monto and id_reserva in
  (select id from public.reserva where estado = 'confirmada');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 10), null, 1)$$, 'S1: nivel 1 con todo en credito');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 11), null, 1)$$, 'S2: nivel 1 con credito parcial');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 12), null, 2)$$, 'S3: nivel 2 con credito parcial');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 13), null, 2)$$, 'S4: nivel 2 con todo en credito');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 14), null, 3)$$, 'S5: nivel 3 con credito parcial');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 15), null, 3)$$, 'S6: nivel 3 con todo en credito');
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 16), null, 1)$$, 'S7: nivel 1, credito de origen vencido');
reset role;

-- S1: nivel 1, todo credito nivel_2: vuelve como nivel_2, sin ganar 30 dias ni convertirse en nivel_1.
select results_eq($$select saldo, estado, tipo, vence from public.credito where id = public.t_id('eeeeeeee', 10)$$,
  $$values (100.00::numeric, 'vigente', 'nivel_2', '2031-01-01 12:00-05'::timestamptz)$$, 'S1: vuelve a su origen con su tipo y vencimiento');
select is((select count(*)::int from public.credito where id_reserva = public.t_id('bbbbbbbb', 10)), 0, 'S1: no nace un credito nivel_1');
select is((select credito_generado from public.reserva where id = public.t_id('bbbbbbbb', 10)), 100.00::numeric, 'S1: el credito de la reserva sigue siendo lo pagado');
-- S2: nivel 1, 40 de credito de reprogramacion + 60 de efectivo.
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 11)), 40.00::numeric, 'S2: la parte aplicada vuelve a su origen');
select results_eq($$select tipo, monto from public.credito where id_reserva = public.t_id('bbbbbbbb', 11)$$,
  $$values ('nivel_1', 60.00::numeric)$$, 'S2: solo el efectivo es credito nuevo de nivel 1');
select is((select credito_generado from public.reserva where id = public.t_id('bbbbbbbb', 11)), 100.00::numeric, 'S2: retenido + credito = pagado');
-- S3: nivel 2, 80 de credito + 20 de efectivo; retenido 50 (sale primero del efectivo): credito 50, todo del origen.
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 12)), 50.00::numeric, 'S3: vuelve lo que no se retuvo del credito');
select is((select count(*)::int from public.credito where id_reserva = public.t_id('bbbbbbbb', 12)), 0, 'S3: sin credito nuevo');
select results_eq($$select retenido, credito_generado from public.reserva where id = public.t_id('bbbbbbbb', 12)$$,
  $$values (50.00::numeric, 50.00::numeric)$$, 'S3: retenido + credito = pagado neto');
-- S4: nivel 2, todo credito.
select results_eq($$select saldo, vence from public.credito where id = public.t_id('eeeeeeee', 13)$$,
  $$values (50.00::numeric, '2031-01-01 12:00-05'::timestamptz)$$, 'S4: vuelve 50 con su vencimiento');
select is((select count(*)::int from public.credito where id_reserva = public.t_id('bbbbbbbb', 13)), 0, 'S4: sin credito nuevo');
-- S5: nivel 3 retiene todo; la excepcion devuelve a su origen lo que era credito y el resto es credito de excepcion.
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 14)), 0.00::numeric, 'S5: en nivel 3 nada vuelve');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_excepcion(public.t_id('bbbbbbbb', 14), 'Motivo de la excepcion')$$, 'S5: aplica la excepcion');
select lives_ok($$select public.aplicar_excepcion(public.t_id('bbbbbbbb', 15), 'Motivo de la excepcion')$$, 'S6: aplica la excepcion');
reset role;
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 14)), 50.00::numeric, 'S5: la parte aplicada vuelve a su origen');
select results_eq($$select tipo, monto from public.credito where id_reserva = public.t_id('bbbbbbbb', 14)$$,
  $$values ('excepcion', 50.00::numeric)$$, 'S5: el resto es credito de excepcion');
-- S6: todo credito: la excepcion lo devuelve entero a su origen.
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 15)), 100.00::numeric, 'S6: vuelve entero');
select is((select count(*)::int from public.credito where id_reserva = public.t_id('bbbbbbbb', 15)), 0, 'S6: sin credito de excepcion');
-- S7: origen vencido: 7 dias desde ahora, fin del dia en Lima.
select results_eq($$select saldo, estado, vence from public.credito where id = public.t_id('eeeeeeee', 16)$$,
  $$values (100.00::numeric, 'vigente', public.fin_de_dia_lima(now(), 7))$$, 'S7: origen vencido: 7 dias desde la cancelacion');

-- 4. Barrera: nadie con rol de API saca una reserva de cancelada/no_asistio ni una cuota de anulada; las funciones si.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$update public.reserva set estado = 'confirmada', motivo_cancelacion = null where id = public.t_id('bbbbbbbb', 10)$$, '42501', null, 'el administrador no revive una cancelada por update');
select throws_ok($$update public.reserva set estado = 'confirmada' where id = public.t_id('bbbbbbbb', 5)$$, '42501', null, 'ni una no_asistio');
select throws_ok($$update public.cuota set estado = 'pendiente' where id = public.t_id('dddddddd', 10)$$, '42501', null, 'ni una cuota anulada');
reset role;
set local role anon;
select throws_ok($$update public.reserva set estado = 'confirmada', motivo_cancelacion = null where id = public.t_id('bbbbbbbb', 10)$$, '42501', null, 'anon tampoco');
reset role;
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 10)), 'cancelada', 'la reserva sigue cancelada');
select is((select estado from public.cuota where id = public.t_id('dddddddd', 10)), 'anulada', 'la cuota sigue anulada');
-- Las funciones si: el estudio cancela y el cliente reprograma (reactiva la reserva y las cuotas).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.cancelar_reserva(public.t_id('bbbbbbbb', 20), 'Mantenimiento de la sala', null, 'estudio')$$, 'el estudio cancela');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva(public.t_id('bbbbbbbb', 20), date_trunc('hour', now()) + interval '200 hours', null, null, null, '{}', 200)$$,
  'tras la cancelacion del estudio la funcion reactiva la reserva');
reset role;
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 20)), 'confirmada', 'la reserva vuelve a confirmada');

-- 6. creada_en de las reservas existentes: el de su aviso reserva_creada si existe y es anterior.
select public.t_reserva(50, 500, 'pre_reservada');
select public.t_reserva(51, 510, 'pre_reservada');
select public.t_reserva(52, 520, 'pre_reservada');
update public.reserva set creada_en = now() where id in (public.t_id('bbbbbbbb', 50), public.t_id('bbbbbbbb', 51), public.t_id('bbbbbbbb', 52));
insert into public.notificacion (tipo, destinatario, datos, creada_en) values
  ('reserva_creada', 'cli@t.pe', jsonb_build_object('id_reserva', public.t_id('bbbbbbbb', 50)), now() - interval '5 days'),
  ('reserva_creada', 'cli@t.pe', jsonb_build_object('id_reserva', public.t_id('bbbbbbbb', 51)), now() + interval '1 day');
select lives_ok($$select public.rellenar_creada_en()$$, 'rellena creada_en');
select lives_ok($$select public.rellenar_creada_en()$$, 'es idempotente');
select is((select creada_en from public.reserva where id = public.t_id('bbbbbbbb', 50)), now() - interval '5 days', 'toma el momento de su aviso');
select is((select creada_en from public.reserva where id = public.t_id('bbbbbbbb', 51)), now(), 'un aviso posterior no la cambia');

-- 7. Confirmar con credito avisa igual que una aprobacion.
select public.t_reserva(30, 400, 'pre_reservada');
select public.t_reserva(31, 410, 'pre_reservada');
select public.t_credito(30, 100, 0, 'nivel_1');
select public.t_credito(31, 100, 0, 'nivel_1');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_credito(public.t_id('cccccccc', 30), 100, public.t_id('eeeeeeee', 30))$$, 'el credito cubre el adelanto');
select lives_ok($$select public.aplicar_credito(public.t_id('cccccccc', 31), 40, public.t_id('eeeeeeee', 31))$$, 'un credito parcial no confirma');
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'pago_aprobado' and destinatario = 'cli@t.pe'
  and datos ->> 'id_reserva' = public.t_id('bbbbbbbb', 30)::text and (datos ->> 'reserva_confirmada')::boolean
  and (datos ->> 'monto')::numeric = 100 and datos ->> 'hito' = 'al_reservar'), 1, 'confirmar con credito encola pago_aprobado con la reserva confirmada');
select is((select count(*)::int from public.notificacion where tipo = 'pago_aprobado' and datos ->> 'id_reserva' = public.t_id('bbbbbbbb', 31)::text), 0,
  'sin confirmar no hay aviso');

-- 8. La cuota pasa a pagada solo cuando lo aplicado cubre su monto.
select public.t_reserva(40, 420, 'pre_reservada', 10);
select public.t_captura(40, 60, 'OP-40a');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aprobar_pago((select id from public.comprobante_pago where numero_operacion = 'OP-40a'))$$, 'aprueba una captura menor que la cuota');
reset role;
select results_eq($$select estado, pagado from public.cuota where id = public.t_id('cccccccc', 40)$$,
  $$values ('pendiente', 60.00::numeric)$$, 'la cuota sigue pendiente con 60 aplicados');
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 40)), 'pre_reservada', 'y la reserva no se confirma');
select public.t_captura(40, 40, 'OP-40b');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aprobar_pago((select id from public.comprobante_pago where numero_operacion = 'OP-40b'))$$, 'aprueba el resto');
reset role;
select results_eq($$select estado, pagado from public.cuota where id = public.t_id('cccccccc', 40)$$,
  $$values ('pagada', 100.00::numeric)$$, 'con el resto la cuota queda pagada');
select is((select estado from public.reserva where id = public.t_id('bbbbbbbb', 40)), 'confirmada', 'y la reserva se confirma');

-- 10. Devolucion integra tras la cancelacion del estudio: en dinero solo lo pagado con capturas; lo pagado con credito
-- vuelve a sus creditos de origen con el vencimiento ampliado (el mayor entre el suyo y 30 dias desde la eleccion).
-- n60: 40 de credito nivel_2 + 60 de captura; n61: todo en credito.
select public.t_reserva(60, 600, 'confirmada');
select public.t_credito(60, 40, 40, 'nivel_2', now() + interval '2 days');
select public.t_efectivo(60, 60);
select public.t_reserva(61, 610, 'confirmada');
select public.t_credito(61, 100, 100, 'nivel_2', now() + interval '2 days');
update public.cuota set estado = 'pagada' where hito = 'al_reservar' and pagado >= monto
  and id_reserva in (public.t_id('bbbbbbbb', 60), public.t_id('bbbbbbbb', 61));
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select public.cancelar_reserva(public.t_id('bbbbbbbb', 60), 'Averia de la sala', null, 'estudio');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 61), 'Averia de la sala', null, 'estudio');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.elegir_estudio_devolucion(public.t_id('bbbbbbbb', 60))$$, 'elige la devolucion integra (credito + captura)');
select lives_ok($$select public.elegir_estudio_devolucion(public.t_id('bbbbbbbb', 61))$$, 'elige la devolucion integra (todo credito)');
reset role;
select results_eq($$select monto_solicitado, monto_aprobado from public.devolucion where id_reserva = public.t_id('bbbbbbbb', 60) and tipo = 'estudio'$$,
  $$values (60.00::numeric, 60.00::numeric)$$, 'la devolucion en dinero es solo lo pagado con capturas');
select results_eq($$select saldo, estado, vence from public.credito where id = public.t_id('eeeeeeee', 60)$$,
  $$values (40.00::numeric, 'vigente', public.fin_de_dia_lima(now(), 30))$$, 'el credito vuelve a su origen con el vencimiento ampliado');
select is((select eleccion_estudio from public.reserva where id = public.t_id('bbbbbbbb', 60)), 'devolucion', 'la eleccion queda registrada');
select is((select count(*)::int from public.devolucion where id_reserva = public.t_id('bbbbbbbb', 61)), 0, 'sin capturas no hay devolucion en dinero');
select results_eq($$select r.eleccion_estudio, k.saldo from public.reserva r, public.credito k
  where r.id = public.t_id('bbbbbbbb', 61) and k.id = public.t_id('eeeeeeee', 61)$$,
  $$values ('devolucion', 100.00::numeric)$$, 'pero la eleccion se registra y el credito vuelve entero');

select * from finish();
rollback;
