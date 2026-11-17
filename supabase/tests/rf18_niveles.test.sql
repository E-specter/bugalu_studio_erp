begin;
create extension if not exists pgtap with schema extensions;
select plan(35);

-- RF-18 (parte A): niveles de cancelacion, penalizacion, foto de parametros y vista previa (CA-02).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'pe@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

-- Foto de parametros: los cinco nuevos viajan en parametros_vigentes() y en cada reserva.
select ok(public.parametros_vigentes() ?& array['porcentaje_penalizacion_nivel_2', 'minutos_tolerancia_inasistencia',
  'dias_vigencia_credito', 'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2'], 'parametros_vigentes trae los 5 parametros nuevos');

-- Nivel con limites exactos (anticipacion = inicio - aviso), plazos 48 y 24 horas.
create temp table p as select '{"horas_nivel_1": 48, "horas_nivel_2": 24}'::jsonb as v;
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-08 10:00-05', (select v from p)), 2::smallint, '48 h exactas: nivel 2');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-08 09:59:59-05', (select v from p)), 1::smallint, '48 h y 1 s: nivel 1');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-08 10:00:01-05', (select v from p)), 2::smallint, '47 h 59 min 59 s: nivel 2');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-09 10:00-05', (select v from p)), 3::smallint, '24 h exactas: nivel 3');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-09 09:59:59-05', (select v from p)), 2::smallint, '24 h y 1 s: nivel 2');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-10 09:00-05', (select v from p)), 3::smallint, '1 h: nivel 3');
select is(public.nivel_cancelacion('2027-06-10 10:00-05', '2027-06-08 10:00-05', '{"horas_nivel_1": 72, "horas_nivel_2": 36}'), 2::smallint,
  'con otros plazos guardados (72 y 36 h), 48 h es nivel 2');

-- Penalizacion de nivel 2: redondeo al centimo, mitad hacia arriba.
select is(public.penalizacion_nivel_2(200, '{"porcentaje_penalizacion_nivel_2": 25}'), 50.00::numeric, '25 % de 200 = 50.00');
select is(public.penalizacion_nivel_2(0.10, '{"porcentaje_penalizacion_nivel_2": 25}'), 0.03::numeric, '0.025 se redondea hacia arriba: 0.03');
select is(public.penalizacion_nivel_2(33.33, '{"porcentaje_penalizacion_nivel_2": 25}'), 8.33::numeric, '8.3325 -> 8.33');

-- Reservas (tramos de la misma sala, lejos de los limites): +73 h nivel 1, +31 h nivel 2, +11 h nivel 3.
-- r1..r3 con adelanto pagado 100 de 200; r4 sin pagos; r5 de c2.
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select d.id, d.cliente, sa.id, se.id, date_trunc('hour', now()) + d.horas * interval '1 hour',
  date_trunc('hour', now()) + d.horas * interval '1 hour' + interval '1 hour', 200, d.estado, '2099-01-01'
from public.sala_tecnica sa, public.servicio se,
  (values
    ('bbbbbbbb-0000-0000-0000-000000000001'::uuid, '00000000-0000-0000-0000-0000000000c1'::uuid, 73, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-0000000000c1', 31, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000003', '00000000-0000-0000-0000-0000000000c1', 11, 'confirmada'),
    ('bbbbbbbb-0000-0000-0000-000000000004', '00000000-0000-0000-0000-0000000000c1', 100, 'pre_reservada'),
    ('bbbbbbbb-0000-0000-0000-000000000005', '00000000-0000-0000-0000-0000000000c2', 150, 'confirmada')
  ) as d(id, cliente, horas, estado)
where se.nombre = 'Ensayo';
insert into public.cuota (id_reserva, hito, monto, estado, pagado)
select id, 'al_reservar', 100, case when right(id::text, 1) = '4' then 'pendiente' else 'pagada' end,
  case when right(id::text, 1) = '4' then 0 else 100 end from public.reserva;
insert into public.cuota (id_reserva, hito, monto, estado) select id, 'al_terminar', 100, 'pendiente' from public.reserva;

update public.reserva set creada_en = now() - interval '30 days';
select ok((select parametros_aplicados ?& array['porcentaje_penalizacion_nivel_2', 'minutos_tolerancia_inasistencia',
  'dias_vigencia_credito', 'reprogramaciones_nivel_1', 'reprogramaciones_nivel_2'] from public.reserva where id = 'bbbbbbbb-0000-0000-0000-000000000001'),
  'cada reserva nueva guarda los 5 parametros nuevos');
select throws_ok($$insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, parametros_aplicados)
  select '00000000-0000-0000-0000-0000000000c1', sa.id, se.id, '2027-09-01 10:00-05', '2027-09-01 11:00-05', 10,
    public.parametros_vigentes() - 'dias_vigencia_credito' from public.sala_tecnica sa, public.servicio se where se.nombre = 'Ensayo'$$,
  '23514', null, 'la foto de parametros sin los nuevos no vale');

-- Vista previa (CA-02): total 200, adelanto pagado 100.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select nivel, pagado, en_validacion, retenido, credito from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')$$,
  $$values (1::smallint, 100.00::numeric, 0.00::numeric, 0.00::numeric, 100.00::numeric)$$, 'nivel 1: retiene 0.00, credito 100.00');
select results_eq($$select nivel, retenido, credito from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000002')$$,
  $$values (2::smallint, 50.00::numeric, 50.00::numeric)$$, 'nivel 2: retiene 50.00, credito 50.00');
select results_eq($$select nivel, retenido, credito from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000003')$$,
  $$values (3::smallint, 100.00::numeric, 0.00::numeric)$$, 'nivel 3: retiene 100.00, credito 0.00');
select ok((select credito_vence = (date_trunc('day', (now() at time zone 'America/Lima') + interval '31 days') at time zone 'America/Lima') - interval '1 microsecond'
  from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')), 'el credito vence al final del dia 30 en Lima');
select is((select credito_vence from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000003')), null, 'sin credito no hay vencimiento');
select results_eq($$select nivel, pagado, retenido, credito from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000004')$$,
  $$values (null::smallint, 0.00::numeric, 0.00::numeric, 0.00::numeric)$$, 'sin pagos: nivel null y todo en cero');
select ok((select anticipacion_horas between 72 and 73 from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')), 'anticipacion en horas');
reset role;

-- La vista usa la foto de la reserva aunque cambien los parametros vigentes.
update public.parametro set valor = 100 where clave = 'horas_nivel_1';
update public.parametro set valor = 99 where clave = 'horas_nivel_2';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select nivel from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')), 1::smallint, 'los plazos guardados mandan sobre los vigentes');

-- Un pago en validacion se informa aparte y no cuenta como pagado.
reset role;
update public.instruccion_pago set texto = 'x', activo = true where metodo = 'yape';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
insert into public.comprobante_pago (id, id_cuota, id_cliente, metodo, monto, numero_operacion, ruta_captura, tipo_captura)
select 'aaaaaaaa-0000-0000-0000-000000000001', c.id, '00000000-0000-0000-0000-0000000000c1', 'yape', 100, 'OP-1',
  '00000000-0000-0000-0000-0000000000c1/a.png', 'image/png'
from public.cuota c where c.id_reserva = 'bbbbbbbb-0000-0000-0000-000000000001' and c.hito = 'al_terminar';
reset role;
select results_eq($$select pagado, en_validacion, nivel from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000004')$$,
  $$values (0.00::numeric, 0.00::numeric, null::smallint)$$, 'otra reserva sin pagos no se ve afectada');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select pagado, en_validacion, nivel from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')$$,
  $$values (100.00::numeric, 100.00::numeric, 1::smallint)$$, 'el pago en validacion aparece en en_validacion y no en pagado');

-- aviso_en: solo el administrador lo pasa (mismas reglas que al cancelar).
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001', now() - interval '3 days')$$, '42501', null, 'el cliente no pasa aviso_en');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select nivel from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000003', now() - interval '100 hours')), 1::smallint, 'el administrador simula con aviso_en: 100 h antes es nivel 1');
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001', now() + interval '1 hour')$$, 'P0001', 'aviso_invalido', 'aviso_en futuro: aviso_invalido');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);

-- Quien puede ver la vista previa.
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000005')$$, 'P0002', null, 'otro cliente: no existe para el (404)');
select throws_ok($$select * from public.vista_cancelacion(gen_random_uuid())$$, 'P0002', null, 'inexistente: P0002');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')$$, '42501', null, 'el personal no ve la vista de cancelacion');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select nivel from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000005')), 1::smallint, 'el administrador la ve de cualquier reserva');
reset role;
set local role anon;
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')$$, '42501', null, 'anon no la ejecuta');
reset role;

-- Estados que no se cancelan.
update public.reserva set estado = 'en_curso' where id = 'bbbbbbbb-0000-0000-0000-000000000003';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select * from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000003')$$, 'P0001', 'no_cancelable', 'en_curso: no_cancelable');
reset role;

-- Reprogramaciones restantes (la tabla de historial existe vacia): limite 2 en total, 1 en nivel 2.
select has_table('public', 'reprogramacion', 'existe el historial de reprogramaciones');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select results_eq($$select puede_reprogramar, reprogramaciones_restantes from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000001')$$,
  $$values (true, 2)$$, 'nivel 1 confirmada: puede reprogramar, 2 restantes');
select results_eq($$select puede_reprogramar, reprogramaciones_restantes from public.vista_cancelacion('bbbbbbbb-0000-0000-0000-000000000002')$$,
  $$values (true, 1)$$, 'nivel 2: 1 restante');
reset role;

select * from finish();
rollback;
