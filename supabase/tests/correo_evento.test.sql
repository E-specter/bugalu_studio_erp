begin;
create extension if not exists pgtap with schema extensions;
select plan(12);

-- ADR-016: la bandeja de correos lee de la reserva lo que el evento de calendario necesita
-- (horario, servicio, sala) y si la reserva ya tenia evento antes del aviso.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

create function public.t_id(p text, p_n int) returns uuid language sql immutable as $$
  select (p || '-0000-0000-0000-0000000000' || lpad(p_n::text, 2, '0'))::uuid $$;
create function public.t_reserva(p_n int, p_horas int, p_estado text, p_motivo text default null)
returns void language plpgsql as $$
begin
  insert into public.sala_tecnica (id, nombre, sede) values (public.t_id('5a5a5a5a', p_n), 'Sala t' || p_n, 'Sede t');
  insert into public.reserva (id, id_cliente, id_sala, id_servicio, inicio, fin, total, estado, motivo_cancelacion, vence_pago, creada_en)
  select public.t_id('bbbbbbbb', p_n), '00000000-0000-0000-0000-0000000000c1', public.t_id('5a5a5a5a', p_n), se.id,
    date_trunc('hour', now()) + p_horas * interval '1 hour', date_trunc('hour', now()) + p_horas * interval '1 hour' + interval '1 hour',
    200, p_estado, p_motivo, now() + interval '1000 hours', now() - interval '30 days'
  from public.servicio se where se.nombre = 'Ensayo';
  insert into public.cuota (id, id_reserva, hito, monto) values
    (public.t_id('cccccccc', p_n), public.t_id('bbbbbbbb', p_n), 'al_reservar', 100),
    (public.t_id('dddddddd', p_n), public.t_id('bbbbbbbb', p_n), 'al_terminar', 100);
end $$;
create function public.t_credito(p_n int)
returns void language sql as $$
  insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence, estado)
  values (public.t_id('eeeeeeee', p_n), '00000000-0000-0000-0000-0000000000c1', public.t_id('bbbbbbbb', 0), 'nivel_1', 100, 100,
    '2031-01-01 12:00-05', 'vigente') $$;
create function public.t_como(p_quien text) returns void language plpgsql as $$
begin
  set local role authenticated;
  perform set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000' || p_quien || '","role":"authenticated"}', true);
end $$;
create function public.t_datos(p_n int, p_tipo text)
returns table (inicio timestamptz, fin timestamptz, servicio text, sala text, tiene_evento boolean) language sql as $$
  select d.inicio, d.fin, d.servicio, d.sala, d.tiene_evento
  from public.notificacion n
  join public.datos_reserva_para_correo(array(select id from public.notificacion)) d on d.id_notificacion = n.id
  where n.tipo = p_tipo and n.datos ->> 'id_reserva' = public.t_id('bbbbbbbb', p_n)::text $$;

select public.t_reserva(0, -500, 'cancelada', 'cliente');

-- 1. Solo la bandeja (bugalu_api) puede llamarla.
select ok(has_function_privilege('bugalu_api', 'public.datos_reserva_para_correo(uuid[])', 'execute'), 'bugalu_api la ejecuta');
select ok(not has_function_privilege('anon', 'public.datos_reserva_para_correo(uuid[])', 'execute'), 'anon no');
select ok(not has_function_privilege('authenticated', 'public.datos_reserva_para_correo(uuid[])', 'execute'), 'authenticated no');

-- 2. Reserva confirmada solo con credito y cancelada por el cliente: el aviso de cancelacion tiene evento.
select public.t_reserva(30, 300, 'pre_reservada');
select public.t_credito(30);
select public.t_como('c1');
select public.aplicar_credito(public.t_id('cccccccc', 30), 100, public.t_id('eeeeeeee', 30));
select public.cancelar_reserva(public.t_id('bbbbbbbb', 30), null, 1);
reset role;
select is((select count(*)::int from public.notificacion where tipo = 'reserva_cancelada_con_pagos' and datos ->> 'id_reserva' = public.t_id('bbbbbbbb', 30)::text), 1,
  'el credito aplicado cuenta como pago: la cancelacion encola reserva_cancelada_con_pagos');
select results_eq($$select servicio, sala, tiene_evento from public.t_datos(30, 'reserva_cancelada_con_pagos')$$,
  $$values ('Ensayo', 'Sala t30', true)$$, 'con credito: servicio, sala y tiene_evento');
select is((select inicio from public.t_datos(30, 'reserva_cancelada_con_pagos')), (select inicio from public.reserva where id = public.t_id('bbbbbbbb', 30)),
  'trae el inicio de la reserva');
select is((select count(*)::int from public.t_datos(30, 'pago_aprobado')), 1, 'el pago_aprobado de la confirmacion tambien se devuelve');

-- 3. Pre-reserva sin confirmar cancelada por el estudio: no tiene evento.
select public.t_reserva(31, 310, 'pre_reservada');
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 31), 'Averia', null, 'estudio');
reset role;
select is((select tiene_evento from public.t_datos(31, 'reserva_cancelada_estudio')), false, 'sin confirmacion previa no hay evento');

-- 4. Confirmada con credito y cancelada por el estudio: tiene evento.
select public.t_reserva(32, 320, 'pre_reservada');
select public.t_credito(32);
select public.t_como('c1');
select public.aplicar_credito(public.t_id('cccccccc', 32), 100, public.t_id('eeeeeeee', 32));
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 32), 'Averia', null, 'estudio');
reset role;
select is((select tiene_evento from public.t_datos(32, 'reserva_cancelada_estudio')), true, 'confirmada y cancelada por el estudio: tiene evento');

-- 5. Un aviso solo cuenta confirmaciones anteriores o simultaneas: una posterior no cuenta.
select public.t_reserva(33, 330, 'pre_reservada');
insert into public.notificacion (id, tipo, destinatario, datos, creada_en) values
  (public.t_id('aaaaaaaa', 1), 'reserva_cancelada_estudio', 'cli@t.pe', jsonb_build_object('id_reserva', public.t_id('bbbbbbbb', 33)), now() - interval '2 hours'),
  (public.t_id('aaaaaaaa', 2), 'pago_aprobado', 'cli@t.pe', jsonb_build_object('id_reserva', public.t_id('bbbbbbbb', 33), 'reserva_confirmada', true), now() - interval '1 hour'),
  (public.t_id('aaaaaaaa', 3), 'reserva_reprogramada', 'cli@t.pe', jsonb_build_object('id_reserva', public.t_id('bbbbbbbb', 33)), now());
select is((select tiene_evento from public.datos_reserva_para_correo(array[public.t_id('aaaaaaaa', 1)])), false, 'una confirmacion posterior no cuenta');
select is((select tiene_evento from public.datos_reserva_para_correo(array[public.t_id('aaaaaaaa', 3)])), true, 'una anterior si (reprogramar tras cancelar)');

-- 6. Ids sin notificacion o sin reserva no devuelven filas.
select is((select count(*)::int from public.datos_reserva_para_correo(array[gen_random_uuid()])), 0, 'id desconocido: sin filas');
select * from finish();
rollback;
