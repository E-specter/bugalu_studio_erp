begin;
create extension if not exists pgtap with schema extensions;
select plan(63);

-- RF-15 etapa C (backend C1): cerrar la asesoria (CA-12), notas y constancia (CA-13), recordatorio de 24 h (CA-14) y el
-- aviso de reprogramacion al profesional (pendiente de B6).
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{"nombre":"Admin"}'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p1@t.pe', '{"nombre":"Pablo Uno"}'),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'p2@t.pe', '{"nombre":"Paula Dos"}'),
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe', '{"nombre":"Clara Cliente"}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c2@t.pe', '{"nombre":"Carlos Cliente"}'),
  ('00000000-0000-0000-0000-0000000000e1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 's1@t.pe', '{"nombre":"Sergio Personal"}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'personal' where id = '00000000-0000-0000-0000-0000000000e1';
update public.usuario set rol = 'profesional' where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
update public.usuario set nombre_artistico = 'Clara MC' where id = '00000000-0000-0000-0000-0000000000c1';
select public.crear_perfil_profesional(id) from public.usuario where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
insert into public.especialidad_asesoria (id, nombre) values ('ee000000-0000-0000-0000-000000000001', 'Mezcla'), ('ee000000-0000-0000-0000-000000000002', 'Composicion');
insert into public.perfil_especialidad (id_profesional, id_especialidad)
  values ('00000000-0000-0000-0000-0000000000b1', 'ee000000-0000-0000-0000-000000000001'),
         ('00000000-0000-0000-0000-0000000000b1', 'ee000000-0000-0000-0000-000000000002'),
         ('00000000-0000-0000-0000-0000000000b2', 'ee000000-0000-0000-0000-000000000001');
insert into public.precio_asesoria (id_profesional, minutos, precio)
  select id, m, 50 * m / 30 from public.perfil_profesional, (values (30), (60)) v(m)
  where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
update public.perfil_profesional set activo = true where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');
update public.perfil_profesional set nombre_artistico = 'Pablo Beats' where id = '00000000-0000-0000-0000-0000000000b1';

create temp table h as select date_trunc('hour', now()) as h0;
grant select on h to authenticated;
insert into public.horario_profesional (id_profesional, inicio, fin)
select id, (select h0 from h) - interval '200 hours', (select h0 from h) + interval '200 days'
from public.perfil_profesional where id in ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000b2');

create function pg_temp.mk(p_id text, p_cli text, p_prof text, p_ini interval, p_min integer, p_estado text)
returns void language plpgsql as $f$
declare
  v_id uuid := ('aa000000-0000-0000-0000-' || p_id)::uuid;
  v_ini timestamptz := (select h0 from h) + p_ini;
begin
  insert into public.reserva (id, tipo, id_cliente, id_profesional, inicio, fin, total, estado, motivo_cancelacion, vence_pago)
  values (v_id, 'asesoria', ('00000000-0000-0000-0000-0000000000' || p_cli)::uuid,
          ('00000000-0000-0000-0000-0000000000' || p_prof)::uuid, v_ini, v_ini + p_min * interval '1 minute', 50,
          p_estado, case when p_estado = 'cancelada' then 'cliente' end, now() + interval '300 days');
  insert into public.asesoria (id_reserva, modalidad, enlace) values (v_id, 'virtual', 'https://meet.google.com/abc-defg-hij');
  insert into public.cuota (id_reserva, hito, monto, estado, pagado)
  values (v_id, 'al_reservar', 50, 'pagada', 50);
end $f$;

select pg_temp.mk('000000000001', 'c1', 'b1', interval '5 hours', 30, 'confirmada');      -- a1: aun no empieza
select pg_temp.mk('000000000002', 'c1', 'b1', interval '-3 hours', 30, 'confirmada');     -- a2: ya empezo y termino
select pg_temp.mk('000000000003', 'c2', 'b2', interval '-2 hours', 30, 'confirmada');     -- a3: la cierra el administrador
select pg_temp.mk('000000000004', 'c1', 'b1', interval '-60 hours', 30, 'confirmada');    -- a4: sin limite posterior
select pg_temp.mk('000000000005', 'c1', 'b1', interval '-8 hours', 30, 'pre_reservada');  -- a5: sin pagar
select pg_temp.mk('000000000006', 'c1', 'b1', interval '-20 hours', 30, 'cancelada');     -- a6
select pg_temp.mk('000000000007', 'c1', 'b1', interval '-6 hours', 30, 'confirmada');     -- a7: no asistio
select pg_temp.mk('000000000009', 'c2', 'b2', interval '2 hours', 30, 'pre_reservada');    -- a9: tolerancia

-- CA-12: Realizada.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000001')$$, 'P0001', 'antes_del_inicio', 'antes del inicio: antes_del_inicio');
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000005')$$, 'P0001', 'no_aplicable', 'una pre_reservada no se marca realizada');
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000006')$$, 'P0001', 'no_aplicable', 'una cancelada tampoco');
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000003')$$, 'P0002', null, 'la asesoria de otro profesional no existe: 404');
select lives_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000002')$$, 'su profesional la marca realizada desde el inicio');
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000002')$$, 'P0001', 'no_aplicable', 'ya cerrada: no_aplicable');
select lives_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000004')$$, 'sin limite posterior: 60 h despues');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000007')$$, '42501', null, 'el cliente no la cierra: 403');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000007')$$, 'P0002', null, 'el personal no ve asesorias: 404');
reset role;
set local role anon;
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000007')$$, '42501', null, 'anon no la cierra');
reset role;
select is((select estado from public.reserva where id = 'aa000000-0000-0000-0000-000000000007'), 'confirmada', 'los intentos ajenos dejan la fila intacta');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000003')$$, 'el administrador tambien');
reset role;
select is((select estado || ':' || (realizada_en is not null)::text from public.reserva r join public.asesoria a on a.id_reserva = r.id
           where r.id = 'aa000000-0000-0000-0000-000000000002'), 'realizada:true', 'estado realizada y realizada_en');
select is((select count(*)::int from public.notificacion where tipo = 'asesoria_realizada' and destinatario = 'c1@t.pe'
           and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000002'), 1, 'correo de la constancia al cliente');
select ok((select not (datos::text ilike '%notas%') from public.notificacion where tipo = 'asesoria_realizada'
           and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000002'), 'el correo no lleva notas');

-- CA-12: No asistio (existente) en una pre_reservada o confirmada, sin limite posterior.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000009')$$, 'P0002', null, 'la de otro profesional: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2","role":"authenticated"}', true);
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000009')$$, 'P0001', 'tolerancia_no_cumplida', 'antes de la tolerancia');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000007')$$, 'confirmada, 6 h despues: no asistio');
select lives_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000005')$$, 'pre_reservada, 8 h despues: no asistio');
select throws_ok($$select public.marcar_asesoria_realizada('aa000000-0000-0000-0000-000000000007')$$, 'P0001', 'no_aplicable', 'una no asistio no pasa a realizada');
select throws_ok($$select public.marcar_inasistencia('aa000000-0000-0000-0000-000000000002')$$, 'P0001', 'no_aplicable', 'una realizada no pasa a no asistio');
reset role;

-- CA-13: notas internas.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select lives_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000001', 'Quiere mezclar su EP')$$, 'su profesional guarda notas (confirmada)');
select is(public.notas_de_asesoria('aa000000-0000-0000-0000-000000000001'), 'Quiere mezclar su EP', 'y las lee');
select lives_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000002', 'Cotizar masterizacion')$$, 'tambien en una realizada');
select throws_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000006', 'x')$$, 'P0001', 'no_editable', 'cancelada: no_editable');
select throws_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000001', repeat('x', 5001))$$, '22023', 'texto_invalido', 'mas de 5000 caracteres: invalido');
select lives_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000001', repeat('x', 5000))$$, '5000 caracteres si');
select throws_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000003', 'ajena')$$, 'P0002', null, 'asesoria de otro profesional: 404');
select lives_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000001', '  ')$$, 'texto en blanco borra las notas');
reset role;
select is((select notas is null from public.asesoria where id_reserva = 'aa000000-0000-0000-0000-000000000001'), true, 'queda null');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select throws_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000002', 'del cliente')$$, '42501', null, 'el cliente no escribe notas: 403');
select is(public.notas_de_asesoria('aa000000-0000-0000-0000-000000000002'), null, 'el cliente no las lee por la funcion');
select throws_ok($$select notas from public.asesoria$$, '42501', null, 'ni por la tabla');
reset role;
select is((select notas from public.asesoria where id_reserva = 'aa000000-0000-0000-0000-000000000002'), 'Cotizar masterizacion', 'las notas siguen intactas');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select lives_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000002', 'Nota del administrador')$$, 'el administrador escribe');
reset role;
set local role anon;
select throws_ok($$select public.guardar_notas_asesoria('aa000000-0000-0000-0000-000000000002', 'anon')$$, '42501', null, 'anon no escribe');
reset role;

-- CA-13: constancia (inmutable, solo dueno, su profesional o administrador).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002') ->> 'folio'),
          (select folio from public.reserva where id = 'aa000000-0000-0000-0000-000000000002'), 'el dueno la lee');
select is((select jsonb_object_keys_ordenadas from (select string_agg(k, ',' order by k) as jsonb_object_keys_ordenadas
           from jsonb_object_keys(public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002')) k) x),
          'cliente,duracion,emitida_en,fin,folio,inicio,modalidad,profesional', 'los campos del contrato');
select is((public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002') -> 'cliente')::text, '{"nombre": "Clara Cliente", "nombre_artistico": "Clara MC"}', 'solo nombre y nombre artistico del titular');
select is((public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002') -> 'profesional' -> 'especialidades')::text, '["Composicion", "Mezcla"]', 'con las especialidades del profesional');
select is((public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002') ->> 'duracion')::int, 30, 'duracion en minutos');
select throws_ok($$select public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000007')$$, 'P0001', 'constancia_no_disponible', 'una no asistio: constancia_no_disponible');
select throws_ok($$select public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000003')$$, 'P0002', null, 'la de otro cliente: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b1","role":"authenticated"}', true);
select ok(public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002') is not null, 'su profesional la lee');
select throws_ok($$select public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000003')$$, 'P0002', null, 'profesional ajeno: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000e1","role":"authenticated"}', true);
select throws_ok($$select public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000002')$$, 'P0002', null, 'el personal: 404');
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select ok(public.constancia_de_asesoria('aa000000-0000-0000-0000-000000000003') is not null, 'el administrador la lee');
reset role;
update public.usuario set nombre = 'Otro Nombre' where id = '00000000-0000-0000-0000-0000000000c1';
select is((select constancia -> 'cliente' ->> 'nombre' from public.asesoria where id_reserva = 'aa000000-0000-0000-0000-000000000002'), 'Clara Cliente', 'inmutable: un cambio posterior del nombre no la toca');
select throws_ok($$update public.asesoria set constancia = '{}' where id_reserva = 'aa000000-0000-0000-0000-000000000002'$$, 'P0001', 'constancia_inmutable', 'no se reescribe ni como superusuario');
select is((select count(*)::int from information_schema.column_privileges where table_name = 'asesoria' and column_name = 'constancia'
           and grantee in ('authenticated', 'anon')), 0, 'sin privilegio de columna para los usuarios');

-- CA-14: recordatorio de 24 h, una vez por horario.
insert into public.sala_tecnica (id, nombre, sede) values ('5a5a5a5a-0000-0000-0000-000000000001', 'Sala t', 'Sede t');
insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, vence_pago)
select 'bbbbbbbb-0000-0000-0000-000000000001', '00000000-0000-0000-0000-0000000000c1', '5a5a5a5a-0000-0000-0000-000000000001', se.id,
       (select h0 from h) + interval '20 hours', (select h0 from h) + interval '22 hours', 200, 'confirmada', '2099-01-01'
from public.servicio se where se.nombre = 'Ensayo';
select pg_temp.mk('000000000011', 'c1', 'b1', interval '20 hours', 30, 'confirmada');   -- r1: entra al recordatorio
select pg_temp.mk('000000000012', 'c2', 'b2', interval '30 hours', 30, 'confirmada');   -- r2: falta mas de 24 h
select pg_temp.mk('000000000013', 'c2', 'b2', interval '10 hours', 30, 'pre_reservada'); -- r3: sin confirmar
select pg_temp.mk('000000000014', 'c1', 'b1', interval '22 hours', 30, 'pre_reservada'); -- r4: se confirma con menos de 24 h
update public.reserva set estado = 'confirmada' where id = 'aa000000-0000-0000-0000-000000000014';
select ok(public.enviar_recordatorios() >= 3, 'la corrida envia (asesoria: cliente y profesional; sala: cliente)');
select is((select string_agg(destinatario, ',' order by destinatario) from public.notificacion where tipo = 'recordatorio_asesoria'
           and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000011'), 'c1@t.pe,p1@t.pe', 'asesoria: cliente y profesional');
select is((select datos ->> 'para' from public.notificacion where tipo = 'recordatorio_asesoria' and destinatario = 'p1@t.pe'
           and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000011'), 'profesional', 'marcado para quien es');
select ok((select not (datos ? 'total' or datos ? 'precio' or datos ? 'notas' or datos ? 'saldo') from public.notificacion
           where tipo = 'recordatorio_asesoria' and destinatario = 'p1@t.pe' and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000011'), 'al profesional, ni dinero ni notas');
select is((select count(*)::int from public.notificacion where tipo = 'recordatorio_reserva' and destinatario = 'c1@t.pe'
           and datos ->> 'id_reserva' = 'bbbbbbbb-0000-0000-0000-000000000001'), 1, 'sala confirmada: al cliente');
select is((select count(*)::int from public.notificacion where tipo like 'recordatorio_%'
           and datos ->> 'id_reserva' in ('aa000000-0000-0000-0000-000000000012', 'aa000000-0000-0000-0000-000000000013', 'aa000000-0000-0000-0000-000000000014')), 0,
          'ni a mas de 24 h, ni a una sin confirmar, ni a una confirmada con menos de 24 h');
select is(public.enviar_recordatorios(), 0, 'una segunda corrida no duplica');
update public.reserva set inicio = inicio + interval '1 hour', fin = fin + interval '1 hour' where id = 'aa000000-0000-0000-0000-000000000011';
select ok(public.enviar_recordatorios() >= 2, 'tras reprogramar vuelve a tocar');
select is((select count(*)::int from public.notificacion where tipo = 'recordatorio_asesoria' and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000011'), 4,
          'uno por horario y destinatario');
select is(public.enviar_recordatorios(), 0, 'y de nuevo una sola vez');

-- Pendiente de B6: el aviso de reprogramacion al profesional.
select pg_temp.mk('000000000021', 'c1', 'b1', interval '36 hours', 30, 'confirmada');
select pg_temp.mk('000000000022', 'c1', 'b1', interval '40 hours', 30, 'pre_reservada');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.reprogramar_reserva('aa000000-0000-0000-0000-000000000021', (select h0 from h) + interval '100 hours', 2, 50, null,
  (select precio from public.reserva where id = 'aa000000-0000-0000-0000-000000000021'), 50)$$, 'el cliente reprograma una confirmada');
reset role;
select is((select datos ->> 'cliente' || ':' || (datos ? 'anterior_inicio')::text || ':' || (datos ? 'total')::text from public.notificacion
           where tipo = 'asesoria_reprogramada_profesional' and destinatario = 'p1@t.pe'
             and datos ->> 'id_reserva' = 'aa000000-0000-0000-0000-000000000021'), 'Otro Nombre:true:false', 'el profesional recibe el aviso: quien, fecha anterior y nada de dinero');
select is((select count(*)::int from public.notificacion where tipo = 'asesoria_reprogramada_profesional' and destinatario = 'c1@t.pe'), 0, 'el cliente no recibe el del profesional');

select * from finish();
rollback;
