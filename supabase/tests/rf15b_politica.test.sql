begin;
create extension if not exists pgtap with schema extensions;
select plan(92);

-- RF-15 etapa B (backend B2): politica de RF-18 para asesorias (CA-10, CA-11), barreras del profesional por SQL (CA-16),
-- horario_con_asesorias y profesional_con_asesorias. La sala sigue igual (rf18_*.test.sql).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{"nombre":"Admin"}'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p1@t.pe', '{"nombre":"Pablo Uno"}'),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p2@t.pe', '{"nombre":"Paula Dos"}'),
  ('00000000-0000-0000-0000-0000000000b3', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p3@t.pe', '{"nombre":"Pedro Tres"}'),
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe', '{"nombre":"Clara Cliente"}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c2@t.pe', '{"nombre":"Carlos Cliente"}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 's1@t.pe', '{"nombre":"Sergio Personal"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'profesional' where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-0000000000b3');
select public.crear_perfil_profesional(id) from public.usuario where rol = 'profesional';
insert into public.especialidad_asesoria (id, nombre) values ('ee000000-0000-0000-0000-000000000001', 'Mezcla');
insert into public.perfil_especialidad (id_profesional, id_especialidad)
  select id, 'ee000000-0000-0000-0000-000000000001' from public.perfil_profesional where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
insert into public.precio_asesoria (id_profesional, minutos, precio)
  select id, m, 50 * m / 30 from public.perfil_profesional, (values (30), (60)) v(m) where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
update public.perfil_profesional set activo = true where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');

create temp table h as select date_trunc('hour', now()) as h0;
grant select on h to authenticated;
create temp table t (k text primary key, id uuid not null);
grant all on t to authenticated;
create temp table d (k text primary key, txt text);
grant all on d to authenticated;

-- Horarios: uno grande a futuro, y tramos pasados para las asesorias que ya empezaron o terminaron.
insert into public.horario_profesional (id, id_profesional, inicio, fin)
select ('b0000000-0000-0000-0000-' || p.n)::uuid, p.id, (select h0 from h) + p.d1, (select h0 from h) + p.d2
from (values
  ('0000000000b1'::text, '00000000-0000-0000-0000-0000000000b1'::uuid, interval '1 hour', interval '200 days'),
  ('0000000000b2', '00000000-0000-0000-0000-0000000000b2', interval '1 hour', interval '200 days'),
  ('0000000000b3', '00000000-0000-0000-0000-0000000000b1', interval '-70 hours', interval '-50 hours'),
  ('0000000000b4', '00000000-0000-0000-0000-0000000000b1', interval '-4 hours', interval '-1 hour'),
  ('0000000000b5', '00000000-0000-0000-0000-0000000000b2', interval '-2 hours', interval '1 hour'),
  ('0000000000b6', '00000000-0000-0000-0000-0000000000b2', interval '300 days', interval '301 days'),
  ('0000000000b7', '00000000-0000-0000-0000-0000000000b2', interval '302 days', interval '303 days')
) as p(n, id, d1, d2);

-- Ayuda de prueba: una asesoria con su fila 1:1 y su cuota unica (pagada si hay pagado).
create function pg_temp.mk(p_id text, p_cli text, p_prof text, p_ini interval, p_min integer, p_estado text, p_pagado numeric,
                           p_vence interval default interval '300 days')
returns void language plpgsql as $f$
declare
  v_total numeric := case p_min when 30 then 50 else 90 end;
  v_id uuid := ('aa000000-0000-0000-0000-' || p_id)::uuid;
  v_ini timestamptz := (select h0 from h) + p_ini;
begin
  insert into public.reserva (id, tipo, id_cliente, id_profesional, inicio, fin, total, estado, vence_pago)
  values (v_id, 'asesoria', ('00000000-0000-0000-0000-0000000000' || p_cli)::uuid,
          ('00000000-0000-0000-0000-0000000000' || p_prof)::uuid, v_ini, v_ini + p_min * interval '1 minute', v_total,
          p_estado, now() + p_vence);
  insert into public.asesoria (id_reserva, modalidad) values (v_id, 'virtual');
  insert into public.cuota (id_reserva, hito, monto, estado, pagado)
  values (v_id, 'al_reservar', v_total, case when p_pagado > 0 then 'pagada' else 'pendiente' end, p_pagado);
end $f$;

select pg_temp.mk('000000000001', 'c1', 'b1', interval '100 days', 30, 'confirmada', 50);  -- n1: nivel 1
select pg_temp.mk('000000000002', 'c1', 'b1', interval '30 hours', 30, 'confirmada', 50);  -- n2: nivel 2
select pg_temp.mk('000000000003', 'c1', 'b1', interval '5 hours', 30, 'confirmada', 50);   -- n3: nivel 3
select pg_temp.mk('000000000004', 'c2', 'b2', interval '0 hours', 60, 'confirmada', 90);   -- n4: ya empezo
select pg_temp.mk('000000000005', 'c1', 'b1', interval '-3 hours', 30, 'confirmada', 50);  -- n5: ya termino
select pg_temp.mk('000000000006', 'c1', 'b1', interval '-2 hours', 30, 'confirmada', 50);  -- n6: ya termino
select pg_temp.mk('000000000007', 'c1', 'b1', interval '-90 minutes', 30, 'pre_reservada', 50);  -- n7: pago en validacion, fin pasado
select pg_temp.mk('000000000008', 'c1', 'b1', interval '4 hours', 30, 'confirmada', 50);   -- n8: futura
select pg_temp.mk('000000000010', 'c1', 'b1', interval '-60 hours', 30, 'confirmada', 50); -- n10: fin hace mas de 48 h
select pg_temp.mk('000000000011', 'c1', 'b1', interval '-4 hours', 30, 'realizada', 50);   -- n11: realizada hace poco
select pg_temp.mk('000000000012', 'c1', 'b1', interval '-210 minutes', 30, 'realizada', 50);  -- n12: realizada hace poco
select pg_temp.mk('000000000020', 'c1', 'b1', interval '110 days', 30, 'confirmada', 50); -- r1: reprogramar nivel 1
select pg_temp.mk('000000000021', 'c1', 'b1', interval '36 hours', 30, 'confirmada', 50);  -- r2: reprogramar nivel 2
select pg_temp.mk('000000000030', 'c2', 'b2', interval '302 days', 30, 'confirmada', 50);  -- viva dentro de un bloque de b2
select pg_temp.mk('000000000031', 'c2', 'b2', interval '300 days', 30, 'pre_reservada', 0, interval '-1 hour'); -- vencida sin pagos
insert into public.cuota (id_reserva, hito, monto) select id, 'al_terminar', 12.50 from public.reserva
  where id in ('aa000000-0000-0000-0000-000000000010', 'aa000000-0000-0000-0000-000000000011', 'aa000000-0000-0000-0000-000000000012');
-- Una reserva de sala con un credito de nivel 1 (para ver que la sala conserva la devolucion).
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago)
select 'aa000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-0000000000c1', sa.id, se.id,
       '2099-03-01 10:00-05', '2099-03-01 11:00-05', 100, '2099-01-01'
from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo' limit 1;
insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence) values
  ('ec000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000c1', 'aa000000-0000-0000-0000-000000000011', 'nivel_1', 40, 40, now() + interval '10 days'),
  ('ec000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-0000000000c1', 'aa000000-0000-0000-0000-000000000011', 'excepcion', 10, 10, now() + interval '10 days'),
  ('ec000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-0000000000c1', 'aa000000-0000-0000-0000-000000000009', 'nivel_1', 20, 20, now() + interval '10 days'),
  ('ec000000-0000-0000-0000-00000000000d', '00000000-0000-0000-0000-0000000000c1', 'aa000000-0000-0000-0000-000000000009', 'nivel_2', 100, 100, now() + interval '10 days');

-- (a) Barreras del profesional por SQL: no lee `reserva` ni `asesoria`; la vista no le da las columnas de dinero.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select is((select count(*)::int from public.reserva), 0, 'el profesional no lee reserva por SQL (ni precio ni total ni retenido)');
select is((select count(*)::int from public.asesoria), 0, 'ni la fila de asesoria');
select is((select count(*)::int from public.cuota), 0, 'ni cuotas');
select is((select count(*)::int from public.asesoria_vista), 12, 'su vista trae sus asesorias');
select is((select count(*)::int from public.asesoria_vista where total is not null or pagado_cancelacion is not null
  or retenido is not null or credito_generado is not null or nota_cancelacion is not null or detalle is not null), 0,
  'y sin las columnas de dinero ni la nota de cancelacion');
select ok((select bool_and(precio is not null and parametros_aplicados is not null and id_cliente is not null) from public.asesoria_vista),
  'si el precio publicado y la politica que ya muestra la API');
update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where tipo = 'asesoria';
reset role;
select is((select count(*)::int from public.reserva where tipo = 'asesoria' and estado = 'cancelada'), 0, 'no cambia ninguna asesoria (las filas quedan intactas)');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select total from public.asesoria_vista where id = 'aa000000-0000-0000-0000-000000000001'), 50.00::numeric, 'el cliente ve el total de la suya en la vista');
select is((select count(*)::int from public.asesoria_vista), 12, 'y todas las suyas');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.asesoria_vista), 3, 'otro cliente solo ve las suyas');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select is((select count(*)::int from public.asesoria_vista), 0, 'el personal no ve asesorias');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.asesoria_vista where total is not null and id::text like 'aa000000%'), 15, 'el administrador ve todas con su dinero');
reset role;
set local role anon;
select set_config('request.jwt.claims', '', true);
select throws_ok($$select 1 from public.asesoria_vista$$, '42501', null, 'anon no lee la vista');
reset role;

-- horario_con_asesorias: retirar un bloque con asesorias vivas dentro (la base lo decide, tras bloquear el perfil).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.retirar_horario('b0000000-0000-0000-0000-0000000000b1')$$, 'BG005', 'horario_con_asesorias', 'un bloque con asesorias vivas no se retira');
do $$ declare v_d text; begin
  begin
    perform public.retirar_horario('b0000000-0000-0000-0000-0000000000b1');
  exception when others then
    get stacked diagnostics v_d = pg_exception_detail;
    insert into d values ('retiro', v_d);
  end;
end $$;
reset role;
select is((select jsonb_array_length(txt::jsonb) from d where k = 'retiro'), 6, 'el detalle lista las asesorias vivas del bloque');
select is((select (txt::jsonb -> 0) ?& array['id', 'folio', 'inicio'] from d where k = 'retiro'), true, 'con id, folio e inicio');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select lives_ok($$select public.retirar_horario('b0000000-0000-0000-0000-0000000000b6')$$, 'una pre-reservada vencida sin pagos no cuenta como viva');
select throws_ok($$select public.retirar_horario('b0000000-0000-0000-0000-0000000000b7')$$, 'BG005', 'horario_con_asesorias', 'una confirmada en otro bloque si');
select throws_ok($$select public.retirar_horario('b0000000-0000-0000-0000-0000000000b4')$$, '42501', null, 'el bloque de otro profesional no se toca');
reset role;
select is((select count(*)::int from public.horario_profesional where id in ('b0000000-0000-0000-0000-0000000000b1', 'b0000000-0000-0000-0000-0000000000b7')), 2, 'los bloques con asesorias siguen ahi');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$select public.retirar_horario('b0000000-0000-0000-0000-0000000000b4')$$, 'un tramo pasado, con asesorias ya dadas, se retira');
reset role;

-- profesional_con_asesorias: quitarle el rol con asesorias vivas.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b2', 'cliente', null)$$, 'BG004', 'profesional_con_asesorias', 'no se quita el rol con asesorias vivas');
reset role;
select is((select rol from public.usuario where id = '00000000-0000-0000-0000-0000000000b2'), 'profesional', 'la fila no cambio con el rechazo');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b3', 'cliente', null)$$, 'sin asesorias vivas si');
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b2', 'administrador', null)$$, 'pasar a administrador conserva el perfil: no es quitarlo');
select lives_ok($$select public.asignar_rol('00000000-0000-0000-0000-0000000000b2', 'profesional', null)$$, 'y volver a profesional');
reset role;

-- Disponibilidad: ocupacion sin una asesoria (reprogramar puede solaparse con la propia).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b1', (select h0 from h) + interval '29 hours', (select h0 from h) + interval '31 hours')), 1, 'la asesoria ocupa su tramo');
select is((select count(*)::int from public.ocupacion_profesional('00000000-0000-0000-0000-0000000000b1', (select h0 from h) + interval '29 hours', (select h0 from h) + interval '31 hours', 'aa000000-0000-0000-0000-000000000002')), 0, 'y excluyendola queda libre');
reset role;

-- (b) avanzar_reservas: una pre_reservada con capturas que llega a su fin pasa sola a no_asistio (CA-12); confirmada no.
select public.avanzar_reservas();
select is((select estado from public.reserva where id = 'aa000000-0000-0000-0000-000000000007'), 'no_asistio', 'una pre-reservada con pago en validacion y fin pasado pasa a no_asistio');
select is((select estado from public.reserva where id = 'aa000000-0000-0000-0000-000000000005'), 'confirmada', 'una confirmada sin cerrar no avanza');

-- CA-10: cancelar. Lo ajeno no existe (404) y el personal no ve asesorias; el cliente no cancela tras el inicio.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000001', null, 1)$$, 'P0002', null, 'el personal no ve la asesoria: 404');
select throws_ok($$select * from public.vista_cancelacion('aa000000-0000-0000-0000-000000000001')$$, 'P0002', null, 'ni su vista previa');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000001', null, 1)$$, 'P0002', null, 'su profesional no la cancela como cliente');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000001', null, 1)$$, 'P0002', null, 'otro cliente: 404');
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000004', null, 1)$$, 'P0001', 'no_cancelable', 'el cliente no cancela una asesoria que ya empezo');
reset role;
select is((select estado from public.reserva where id = 'aa000000-0000-0000-0000-000000000001'), 'confirmada', 'la fila ajena sigue intacta');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select nivel::int from public.vista_cancelacion('aa000000-0000-0000-0000-000000000002')), 2, 'la vista previa usa los plazos guardados (nivel 2)');
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000001', null, 2)$$, 'P0001', 'nivel_cambiado', 'nivel_esperado distinto: nivel_cambiado');
select lives_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000001', null, 1)$$, 'nivel 1: cancela');
select lives_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000002', null, 2)$$, 'nivel 2: cancela');
select lives_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000003', null, 3)$$, 'nivel 3: cancela');
reset role;
select is((select credito_generado from public.reserva where id = 'aa000000-0000-0000-0000-000000000001'), 50.00::numeric, 'nivel 1: todo pasa a credito');
select is((select tipo || ':' || saldo::text from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000001'), 'nivel_1:50.00', 'credito de nivel 1 nacido de la asesoria');
select is((select retenido::text || '/' || credito_generado::text from public.reserva where id = 'aa000000-0000-0000-0000-000000000002'), '12.50/37.50', 'nivel 2: retiene el 25 % y acredita el resto');
select is((select retenido::text || '/' || credito_generado::text from public.reserva where id = 'aa000000-0000-0000-0000-000000000003'), '50.00/0.00', 'nivel 3: retiene todo');

-- Excepcion (administrador): lo retenido pasa a credito de excepcion.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_excepcion('aa000000-0000-0000-0000-000000000003', 'El cliente tuvo una emergencia medica')$$, 'el administrador aplica la excepcion a una asesoria');
reset role;
select is((select tipo || ':' || saldo::text from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000003'), 'excepcion:50.00', 'credito de excepcion de la asesoria');

-- Sin devolucion en dinero: un credito de nivel 1 o de excepcion nacido de una asesoria no se devuelve.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.solicitar_devolucion((select id from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000001'), 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_no_permitida', 'nivel 1 de asesoria: sin devolucion');
select throws_ok($$select public.solicitar_devolucion((select id from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000003'), 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_no_permitida', 'excepcion de asesoria: sin devolucion');
select throws_ok($$select public.solicitar_devolucion('ec000000-0000-0000-0000-00000000000b', 'Quiero mi dinero de vuelta')$$, 'P0001', 'devolucion_no_permitida', 'excepcion insertada de asesoria: tampoco');
select lives_ok($$select public.solicitar_devolucion('ec000000-0000-0000-0000-00000000000c', 'Quiero mi dinero de vuelta')$$, 'el de nivel 1 de una sala conserva la devolucion');
reset role;
select is((select count(*)::int from public.devolucion where id_cliente = '00000000-0000-0000-0000-0000000000c1'), 1, 'solo la de la sala quedo registrada');

-- Inasistencia: su profesional o el administrador, desde inicio + tolerancia, sin limite posterior.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'P0002', null, 'el personal no ve la asesoria: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, '42501', null, 'el cliente no marca su propia inasistencia: 403');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'P0002', null, 'otro cliente: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'P0002', null, 'otro profesional: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000008')$$, 'P0001', 'tolerancia_no_cumplida', 'antes de inicio + tolerancia');
select lives_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'su profesional la marca, aunque ya haya terminado');
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'P0001', 'no_aplicable', 'ya cerrada: no_aplicable');
reset role;
select is((select estado || ':' || retenido::text || ':' || credito_generado::text from public.reserva where id = 'aa000000-0000-0000-0000-000000000005'), 'no_asistio:50.00:0.00', 'no_asistio: sin devolucion, todo retenido');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000006')$$, 'el administrador tambien');
select lives_ok($$select public.aplicar_excepcion('aa000000-0000-0000-0000-000000000006', 'Fallo la conexion del profesional')$$, 'y "tratar como nivel 1" sigue disponible en no_asistio');
reset role;
select is((select tipo from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000006'), 'excepcion', 'con credito de excepcion');

-- CA-11: cancelacion del estudio, tambien tras el inicio; el cliente elige devolucion integra.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000004', 'No vino el profesional', null, 'estudio')$$, '42501', null, 'el cliente no cancela por el estudio');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000004', null, null, 'estudio')$$, 'P0001', 'nota_requerida', 'la nota es obligatoria');
select lives_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000004', 'No vino el profesional', null, 'estudio')$$, 'el administrador cancela por el estudio una asesoria ya empezada');
select throws_ok($$select public.cancelar_reserva('aa000000-0000-0000-0000-000000000004', 'Otra vez', null, 'estudio')$$, 'P0001', 'no_cancelable', 'ya cancelada');
reset role;
select is((select estado || ':' || eleccion_estudio || ':' || retenido::text from public.reserva where id = 'aa000000-0000-0000-0000-000000000004'), 'cancelada:pendiente:0.00', 'queda esperando la eleccion del cliente, sin retencion');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.elegir_estudio_devolucion('aa000000-0000-0000-0000-000000000004')$$, 'P0002', null, 'otro cliente no elige por ella: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.elegir_estudio_devolucion('aa000000-0000-0000-0000-000000000004')$$, 'P0002', null, 'el personal no ve la asesoria: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select lives_ok($$select public.elegir_estudio_devolucion('aa000000-0000-0000-0000-000000000004')$$, 'el cliente elige la devolucion integra');
reset role;
select is((select tipo || ':' || monto_aprobado::text || ':' || estado from public.devolucion where id_reserva = 'aa000000-0000-0000-0000-000000000004'), 'estudio:90.00:aprobada', 'devolucion total del estudio (la unica que admite una asesoria)');

-- CA-10 (b): reprogramar con el mismo profesional, misma duracion, dentro de sus horarios, conservando el precio.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select * from public.contexto_reprogramacion('aa000000-0000-0000-0000-000000000020')$$, 'P0002', null, 'el personal no ve la asesoria: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select * from public.contexto_reprogramacion('aa000000-0000-0000-0000-000000000020')$$, 'P0002', null, 'su profesional no la reprograma como cliente');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select tipo || ':' || id_profesional::text || ':' || coalesce(id_sala::text, 'sin_sala') from public.contexto_reprogramacion('aa000000-0000-0000-0000-000000000020')),
  'asesoria:00000000-0000-0000-0000-0000000000b1:sin_sala', 'el contexto trae el tipo y el profesional');
select throws_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000020', (select h0 from h) + interval '111 days', 2, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000020'), 50)$$, 'P0001', 'nivel_cambiado', 'nivel esperado distinto: nivel_cambiado');
select throws_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000020', (select h0 from h) + interval '300 days', 1, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000020'), 50)$$, 'P0001', 'fuera_de_horario', 'fuera de los horarios del profesional');
select lives_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000020', (select h0 from h) + interval '111 days', 1, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000020'), 50)$$, 'nivel 1: reprograma');
select lives_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000021', (select h0 from h) + interval '112 days', 2, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000021'), 50)$$, 'nivel 2: reprograma');
select throws_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000020', (select h0 from h) + interval '112 days', 1, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000020'), 50)$$, '23P01', null, 'el horario ocupado lo detiene la exclusion por profesional');
reset role;
select is((select inicio = (select h0 from h) + interval '111 days' and fin = inicio + interval '30 minutes' and fin_buffer = fin and id_franja is null and total = 50 and id_sala is null
  from public.reserva where id = 'aa000000-0000-0000-0000-000000000020'), true, 'mismo profesional y duracion, sin franja ni margen, mismo precio');
select is((select count(*)::int from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000020'), 1, 'nivel 1: sin cuota nueva');
select is((select nivel::int from public.reprogramacion where id_reserva = 'aa000000-0000-0000-0000-000000000020'), 1, 'queda en el historial');
select is((select hito || ':' || monto::text || ':' || estado || ':' || pagado::text from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000021' and hito = 'al_terminar'),
  'al_terminar:12.50:pendiente:0.00', 'nivel 2: cuota al_terminar del 25 %');
select is((select penalizacion from public.reprogramacion where id_reserva = 'aa000000-0000-0000-0000-000000000021'), 12.50::numeric, 'con su penalizacion en el historial');
select is((select count(*)::int from public.credito where id_reserva = 'aa000000-0000-0000-0000-000000000021'), 0, 'y sin credito');

-- La penalizacion se paga con credito (o captura) hasta 48 h despues del fin; un credito sirve en sala o asesoria.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.aplicar_credito((select id from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000021' and hito = 'al_terminar'), 12.50, 'ec000000-0000-0000-0000-00000000000d')$$, 'la cuota de la penalizacion se paga con credito');
select throws_ok($$select public.aplicar_credito((select id from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000010' and hito = 'al_terminar'), 12.50, 'ec000000-0000-0000-0000-00000000000d')$$, 'P0001', 'no_pagable', 'pasadas 48 h del fin: no_pagable');
select lives_ok($$select public.aplicar_credito((select id from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000011' and hito = 'al_terminar'), 12.50, 'ec000000-0000-0000-0000-00000000000d')$$, 'una realizada dentro de las 48 h si');
reset role;
select is((select estado from public.cuota where id_reserva = 'aa000000-0000-0000-0000-000000000021' and hito = 'al_terminar'), 'pagada', 'la cuota queda pagada');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  select id, auth.uid(), 'yape', 12.50, 'OP-A-1', auth.uid() || '/a1.png', 'image/png' from public.cuota
  where id_reserva = 'aa000000-0000-0000-0000-000000000010' and hito = 'al_terminar'$$, 'P0001', 'cuota_no_pagable', 'una captura pasadas 48 h del fin tampoco');
select lives_ok($$insert into public.comprobante_pago (id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
  select id, auth.uid(), 'yape', 12.50, 'OP-A-2', auth.uid() || '/a2.png', 'image/png' from public.cuota
  where id_reserva = 'aa000000-0000-0000-0000-000000000012' and hito = 'al_terminar'$$, 'ni una captura de una realizada dentro de las 48 h');
reset role;

select * from finish();
rollback;
