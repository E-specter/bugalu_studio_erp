begin;
create extension if not exists pgtap with schema extensions;
select plan(13);

-- RF-18, retoques de la auditoria A (ronda 3): tope de la decision parcial, plazo de pago desde la foto de parametros,
-- fin_buffer al mover una reserva y la cadena diferencia devuelta -> inasistencia -> excepcion.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

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
create function public.t_credito(p_n int, p_monto numeric, p_aplicado numeric, p_tipo text)
returns void language plpgsql as $$
begin
  insert into public.credito (id, id_cliente, id_reserva, tipo, monto, saldo, vence, estado)
  values (public.t_id('eeeeeeee', p_n), '00000000-0000-0000-0000-0000000000c1', public.t_id('bbbbbbbb', 0), p_tipo, p_monto,
    p_monto - p_aplicado, '2031-01-01 12:00-05', case when p_monto = p_aplicado then 'agotado' else 'vigente' end);
  if p_aplicado > 0 then
    insert into public.aplicacion_credito (id_credito, id_cuota, monto, id_usuario)
    values (public.t_id('eeeeeeee', p_n), public.t_id('cccccccc', p_n), p_aplicado, '00000000-0000-0000-0000-0000000000c1');
    update public.cuota set pagado = pagado + p_aplicado where id = public.t_id('cccccccc', p_n);
  end if;
end $$;
create function public.t_pagada(p_n int) returns void language sql as $$
  update public.cuota set estado = 'pagada' where id = public.t_id('cccccccc', p_n) and pagado >= monto $$;
create function public.t_como(p_quien text) returns void language plpgsql as $$
begin
  set local role authenticated;
  perform set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000' || p_quien || '","role":"authenticated"}', true);
end $$;

select public.t_reserva(0, -500, 'cancelada', 1000, 'cliente');

-- 1. Decision parcial: el tope es lo solicitado (70), no el saldo del credito (100 tras caducar la pre_reservada).
select public.t_reserva(30, 300, 'pre_reservada', -1);
select public.t_credito(30, 100, 30, 'nivel_1');
select public.t_como('c1');
select public.solicitar_devolucion(public.t_id('eeeeeeee', 30), 'Quiero mi dinero de vuelta');
reset role;
select public.caducar_reservas();
select public.t_como('ad');
select throws_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = public.t_id('eeeeeeee', 30)), 'parcial', 80, 'Motivo de la parcial')$$,
  '22023', 'monto_invalido', 'parcial: por encima de lo solicitado (aunque haya saldo) es monto_invalido');
select lives_ok($$select public.decidir_devolucion((select id from public.devolucion where id_credito = public.t_id('eeeeeeee', 30)), 'parcial', 70, 'Motivo de la parcial')$$,
  'parcial: lo solicitado exacto se aprueba');
reset role;
select is((select monto_aprobado from public.devolucion where id_credito = public.t_id('eeeeeeee', 30)), 70.00::numeric, 'aprobada por 70');

-- 2. R3: horas_limite_pago sale de la foto de la reserva (500 h), no del valor vigente.
select public.t_reserva(20, 300, 'pre_reservada', -1);
select public.t_credito(20, 100, 30, 'nivel_1');
update public.reserva set parametros_aplicados = coalesce(parametros_aplicados, '{}'::jsonb) || '{"horas_limite_pago": 500}'
  where id = public.t_id('bbbbbbbb', 20);
select public.t_como('ad');
select public.cancelar_reserva(public.t_id('bbbbbbbb', 20), 'Averia de la sala', null, 'estudio');
reset role;
select public.t_como('c1');
select public.reprogramar_reserva(public.t_id('bbbbbbbb', 20), date_trunc('hour', now()) + interval '400 hours', null, null, null, '{}', null);
reset role;
select is((select vence_pago from public.reserva where id = public.t_id('bbbbbbbb', 20)), date_trunc('hour', now()) + interval '400 hours',
  'R3: con 500 h en la foto, el plazo se topa en el inicio');

-- 3. fin_buffer sigue a inicio y fin tambien al actualizar (RN-02).
select public.t_reserva(50, 300, 'confirmada');
update public.reserva set inicio = date_trunc('hour', now()) + interval '700 hours', fin = date_trunc('hour', now()) + interval '702 hours'
  where id = public.t_id('bbbbbbbb', 50);
select is((select fin_buffer from public.reserva where id = public.t_id('bbbbbbbb', 50)), date_trunc('hour', now()) + interval '702 hours 30 minutes',
  'update de inicio y fin: fin_buffer = fin + 30 min');
update public.reserva set inicio = inicio + interval '1 hour' where id = public.t_id('bbbbbbbb', 50);
select is((select fin_buffer - fin from public.reserva where id = public.t_id('bbbbbbbb', 50)), interval '30 minutes', 'cambiar solo inicio lo deja en fin + 30 min');

-- 4. Cadena: reprogramar con diferencia a favor (vuelve al origen) -> mover a la ventana de inasistencia -> marcar -> excepcion.
select public.t_reserva(1, 100, 'confirmada');
select public.t_credito(1, 100, 100, 'nivel_2');
select public.t_pagada(1);
select public.t_como('c1');
select public.reprogramar_reserva(public.t_id('bbbbbbbb', 1), date_trunc('hour', now()) + interval '120 hours', 1, 80, null, '{}', 80);
reset role;
update public.reserva set inicio = date_bin('30 minutes', now(), timestamptz '2000-01-01') - interval '1 hour', fin = date_bin('30 minutes', now(), timestamptz '2000-01-01') + interval '1 hour', vence_pago = null where id = public.t_id('bbbbbbbb', 1);
select is((select fin_buffer from public.reserva where id = public.t_id('bbbbbbbb', 1)), (select fin + interval '30 minutes' from public.reserva where id = public.t_id('bbbbbbbb', 1)),
  'mover la reserva recalcula fin_buffer');
select public.t_como('ad');
select lives_ok($$select public.marcar_inasistencia(public.t_id('bbbbbbbb', 1))$$, 'se marca la inasistencia dentro de la ventana');
select lives_ok($$select public.aplicar_excepcion(public.t_id('bbbbbbbb', 1), 'Fuerza mayor: hospitalizacion')$$, 'se aplica la excepcion');
reset role;
select is((select coalesce((select sum(penalizacion) from public.reprogramacion where id_reserva = r.id), 0)
  + coalesce((select sum(a.devuelto) from public.aplicacion_credito a join public.cuota c on c.id = a.id_cuota where c.id_reserva = r.id), 0)
  + coalesce((select sum(k.monto) from public.credito k where k.id_reserva = r.id), 0)
  + coalesce(r.retenido, 0)
  + coalesce((select sum(d.monto_aprobado) from public.devolucion d where d.id_reserva = r.id), 0)
  from public.reserva r where r.id = public.t_id('bbbbbbbb', 1)),
  (select sum(pagado) from public.cuota where id_reserva = public.t_id('bbbbbbbb', 1)),
  'penalizacion + devuelto + creditos + retenido + devoluciones = lo pagado');
select is((select saldo from public.credito where id = public.t_id('eeeeeeee', 1)), 100.00::numeric, 'el origen recupera todo lo aplicado');
select is((select count(*)::int from public.reserva where id = public.t_id('bbbbbbbb', 1) and estado = 'no_asistio' and excepcion_en is not null), 1,
  'queda no_asistio con la excepcion aplicada');
select is((select sum(a.devuelto) from public.aplicacion_credito a where a.id_credito = public.t_id('eeeeeeee', 1)), 100.00::numeric,
  'todo lo aplicado figura como devuelto');

select * from finish();
rollback;
