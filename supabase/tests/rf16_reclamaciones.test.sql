begin;
create extension if not exists pgtap with schema extensions;
select plan(153);

-- RF-16: Libro de Reclamaciones virtual. Hojas con correlativo propio, plazo en dias habiles, alta publica (anon),
-- respuesta unica, inmutabilidad, adjuntos, limite por IP, avisos y storage `reclamaciones`.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli1@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'cli2@t.pe', '{}'),
  ('00000000-0000-0000-0000-0000000000ad', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'ad@t.pe', '{}');
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';

create function public.zz_datos(p jsonb default '{}') returns jsonb language sql as $$
  select jsonb_build_object('nombre', 'Ana Prueba', 'tipo_documento', 'dni', 'documento', '12345678',
    'domicilio', 'Av. Lima 123', 'telefono', '987654321', 'correo', 'ana@t.pe', 'es_menor', false,
    'bien_tipo', 'servicio', 'tipo', 'reclamo', 'detalle', 'El servicio no fue el pactado.',
    'pedido', 'Quiero la devolucion.', 'medio_respuesta', 'correo') || p
$$;
grant execute on function public.zz_datos(jsonb) to anon, authenticated;

select has_table('public', 'hoja_reclamacion', 'existe hoja_reclamacion');
select has_table('public', 'adjunto_reclamacion', 'existe adjunto_reclamacion');
select has_table('public', 'contador_reclamacion', 'existe el contador del correlativo');
select has_table('public', 'subida_reclamacion', 'existe subida_reclamacion');
select has_function('public', 'confirmar_adjunto', array['text'], 'existe confirmar_adjunto');
select has_function('public', 'registrar_hoja', array['uuid', 'jsonb', 'jsonb', 'text', 'boolean', 'uuid'], 'existe registrar_hoja');
select has_function('public', 'transcribir_hoja', array['uuid', 'jsonb', 'jsonb', 'timestamptz', 'text'], 'existe transcribir_hoja');
select has_function('public', 'responder_hoja', array['uuid', 'text', 'text', 'timestamptz'], 'existe responder_hoja');
select has_function('public', 'dias_habiles_restantes', array['timestamptz'], 'existe dias_habiles_restantes');
select has_function('public', 'avisar_plazos_reclamaciones', 'existe avisar_plazos_reclamaciones');

-- Estado conocido: un solo administrador, sin hojas ni avisos previos (se deshace con el rollback).
alter table public.hoja_reclamacion disable trigger user;
alter table public.adjunto_reclamacion disable trigger user;
delete from public.adjunto_reclamacion;
delete from public.hoja_reclamacion;
delete from public.intento_reclamacion;
delete from public.notificacion;
alter table public.hoja_reclamacion enable trigger user;
alter table public.adjunto_reclamacion enable trigger user;
delete from public.feriado;

-- anon registra (sin cuenta) con un adjunto y el campo trampa
set local role anon;
select lives_ok($$select public.registrar_hoja('11111111-0000-0000-0000-000000000001', public.zz_datos(),
  '[{"nombre": "foto.pdf", "tipo": "application/pdf", "tamano": 1234}]', '1.1.1.1', false)$$,
  'anon registra una hoja');
select lives_ok($$select public.registrar_hoja('11111111-0000-0000-0000-000000000002', public.zz_datos(), '[]', '1.1.1.1', true)$$,
  'anon registra otra hoja con el campo trampa');
select throws_ok($$select * from public.hoja_reclamacion$$, '42501', null, 'anon no lee hojas');
select throws_ok($$select * from public.adjunto_reclamacion$$, '42501', null, 'anon no lee adjuntos');
select throws_ok($$select * from public.intento_reclamacion$$, '42501', null, 'anon no lee los intentos');
select throws_ok($$select * from public.subida_reclamacion$$, '42501', null, 'anon no lee las subidas pendientes');
select throws_ok($$select * from public.contador_reclamacion$$, '42501', null, 'anon no lee el contador');
select throws_ok($$select public.limpiar_subidas_reclamacion()$$, '42501', null, 'anon no limpia las subidas');
select throws_ok($$insert into public.hoja_reclamacion (nombre) values ('x')$$, '42501', null, 'anon no inserta directo');
select throws_ok($$select public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', now(), 'F-1')$$, '42501', null, 'anon no transcribe');
select throws_ok($$select public.responder_hoja(gen_random_uuid(), 'Una respuesta larga', null, null)$$, '42501', null, 'anon no responde');
select throws_ok($$select public.avisar_plazos_reclamaciones()$$, '42501', null, 'anon no corre el aviso de plazos');
select throws_ok($$select public.dias_habiles_restantes(now())$$, '42501', null, 'anon no calcula plazos');
reset role;

-- Numero, fecha, plazo y marca de spam
select matches((select numero from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'),
  '^[0-9]{9}-[0-9]{4}$', 'el numero son 9 cifras, guion y anio');
select is((select right(numero, 4) from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'),
  to_char(now() at time zone 'America/Lima', 'YYYY'), 'el anio es el de presentacion en Lima');
select is(public.anio_presentacion('2025-12-31 23:30-05'), 2025::smallint, 'el anio de presentacion es el de la fecha dada');
select is(public.anio_presentacion('2026-01-01 04:30+00'), 2025::smallint, 'el anio se cuenta con la hora de Lima (fin de ano)');
select is(public.anio_presentacion('2026-01-01 05:30+00'), 2026::smallint, 'el anio cambia a medianoche en Lima');
select is((select correlativo from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000002')
  - (select correlativo from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), 1::bigint,
  'el correlativo avanza de uno en uno');
select is((select creada_en from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), now(),
  'la fecha y hora las pone la base');
select is((select vence_respuesta from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'),
  public.sumar_dias_habiles(now(), 15), 'vence en 15 dias habiles');
select is((select (vence_respuesta at time zone 'America/Lima')::time from public.hoja_reclamacion
  where id = '11111111-0000-0000-0000-000000000001'), '23:59:59.999999'::time, 'vence al final del dia en Lima');
select is((select origen from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), 'web', 'origen web');
select is((select revisar_spam from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), false, 'sin campo trampa no se marca');
select is((select revisar_spam from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000002'), true, 'con campo trampa se marca para revisar');
select is((select id_cuenta from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), null, 'sin sesion no hay cuenta');

-- Feriados: no cuentan como dias habiles
insert into public.feriado (fecha, nombre)
select d::date, 'prueba' from generate_series((now() at time zone 'America/Lima')::date + 1,
  (now() at time zone 'America/Lima')::date + 3, interval '1 day') d;
select is(public.sumar_dias_habiles(now(), 15) > (select vence_respuesta from public.hoja_reclamacion
  where id = '11111111-0000-0000-0000-000000000001'), true, 'los feriados del catalogo alargan el plazo (la funcion los usa)');
delete from public.feriado;

-- Adjuntos y avisos al registrar
select matches((select ruta from public.subida_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001' and n = 1),
  '^11111111-0000-0000-0000-000000000001/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$',
  'la ruta de la subida pendiente la genera la base: id de la hoja, nombre aleatorio y extension del tipo');
select is((select count(*)::int from public.adjunto_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001'), 0,
  'el adjunto no existe hasta confirmar la subida');
select is((select caduca_en - now() from public.subida_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001' and n = 1),
  interval '10 minutes', 'la subida pendiente caduca a los 10 minutos');
select is((select count(*)::int from public.notificacion where tipo = 'reclamacion_registrada' and destinatario = 'ana@t.pe'), 2,
  'cada hoja envia la copia al consumidor');
select is((select count(*)::int from public.notificacion where tipo = 'reclamacion_recibida' and destinatario = 'ad@t.pe'), 2,
  'cada hoja avisa al administrador');
select is((select datos ->> 'numero' from public.notificacion where tipo = 'reclamacion_registrada' order by creada_en, id limit 1) ~ '^[0-9]{9}-', true,
  'el aviso trae el numero de la hoja');

-- Subida del adjunto de la hoja 1: solo a la ruta con subida pendiente vigente, una vez; luego se confirma
select set_config('zz.ruta', (select ruta from public.subida_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001' and n = 1), false);
set local role anon;
select lives_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.ruta'))$$,
  'anon sube a la ruta con subida pendiente vigente');
select throws_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.ruta'))$$, '42501', null,
  'anon no sube dos veces a la misma ruta');
select lives_ok($$select public.confirmar_adjunto(current_setting('zz.ruta'))$$, 'anon confirma el adjunto subido');
select throws_ok($$select public.confirmar_adjunto(current_setting('zz.ruta'))$$, 'P0002', null, 'la subida ya confirmada no se confirma otra vez');
select throws_ok($$select public.confirmar_adjunto('11111111-0000-0000-0000-000000000001/no-existe.pdf')$$, 'P0002', null,
  'una ruta sin subida pendiente no se confirma');
reset role;
select is((select nombre || ':' || tipo || ':' || tamano from public.adjunto_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001' and n = 1),
  'foto.pdf:application/pdf:1234', 'el adjunto confirmado conserva nombre, tipo y tamano declarados');
select is((select ruta from public.adjunto_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001' and n = 1),
  current_setting('zz.ruta'), 'el adjunto queda en la ruta subida');
select is((select count(*)::int from public.subida_reclamacion where id_hoja = '11111111-0000-0000-0000-000000000001'), 0,
  'confirmar consume la subida pendiente');

-- Con sesion: la hoja queda ligada a la cuenta
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select lives_ok($$select public.registrar_hoja('11111111-0000-0000-0000-000000000003', public.zz_datos('{"medio_respuesta": "carta"}'), '[]', '2.2.2.2', false)$$,
  'un cliente registra');
select is((select count(*)::int from public.hoja_reclamacion), 1, 'el cliente solo ve la suya');
select is((select id_cuenta::text from public.hoja_reclamacion), '00000000-0000-0000-0000-0000000000c1', 'queda ligada a su cuenta');
select throws_ok($$select revisar_spam from public.hoja_reclamacion$$, '42501', null, 'el cliente no lee revisar_spam');
select throws_ok($$select respondida_por from public.hoja_reclamacion$$, '42501', null, 'el cliente no lee respondida_por');
select lives_ok($$select id, numero, detalle, respuesta_texto from public.hoja_reclamacion$$, 'el cliente lee el resto de columnas');
select is((select count(*)::int from public.marcas_de_hojas()), 0, 'el cliente no recibe marcas de hojas');
select throws_ok($$update public.hoja_reclamacion set detalle = 'otro detalle largo' where true$$, '42501', null, 'el dueno no edita');
select throws_ok($$delete from public.hoja_reclamacion$$, '42501', null, 'el dueno no borra');
select throws_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000003', 'Una respuesta larga', 'C-1', now())$$, '42501', null,
  'el dueno no se responde a si mismo');
select throws_ok($$select public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', now(), 'F-1')$$, '42501', null, 'el cliente no transcribe');
select throws_ok($$select public.avisar_plazos_reclamaciones()$$, '42501', null, 'el cliente no corre el aviso de plazos');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c2","role":"authenticated"}', true);
select is((select count(*)::int from public.hoja_reclamacion), 0, 'otro cliente no ve hojas ajenas');
select is((select count(*)::int from public.adjunto_reclamacion), 0, 'otro cliente no ve adjuntos ajenos');
reset role;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from public.hoja_reclamacion), 3, 'el administrador ve todas');
select is((select revisar_spam from public.marcas_de_hojas() where id = '11111111-0000-0000-0000-000000000002'), true,
  'el administrador recibe las marcas por la funcion');
select throws_ok($$select revisar_spam from public.hoja_reclamacion$$, '42501', null, 'ni el administrador lee revisar_spam por la tabla');
select is((select count(*)::int from public.adjunto_reclamacion), 1, 'el administrador ve los adjuntos');
select throws_ok($$update public.hoja_reclamacion set detalle = 'otro detalle largo'$$, '42501', null, 'el administrador no edita por la API');
select throws_ok($$delete from public.hoja_reclamacion$$, '42501', null, 'el administrador no borra por la API');
select throws_ok($$delete from public.adjunto_reclamacion$$, '42501', null, 'el administrador no borra adjuntos');
select throws_ok($$insert into public.hoja_reclamacion (nombre) values ('x')$$, '42501', null, 'el administrador no inserta directo');

-- Transcripcion del libro fisico (solo administrador): plazo desde la fecha original
select lives_ok($$select public.transcribir_hoja('11111111-0000-0000-0000-000000000004', public.zz_datos('{"tipo": null}'),
  '[]', now() - interval '30 days', 'FIS-001')$$, 'el administrador transcribe');
reset role;
select is((select vence_respuesta from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000004'),
  public.sumar_dias_habiles(now() - interval '30 days', 15), 'la transcrita vence 15 dias habiles despues de la fecha original');
select is((select origen || ':' || numero_hoja_fisica from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000004'),
  'libro_fisico:FIS-001', 'queda marcada del libro fisico con su numero');
select is((select tipo from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000004'), null, 'una transcrita puede no traer tipo');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select throws_ok($$select public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', now() + interval '1 day', 'FIS-002')$$,
  'P0001', 'fecha_original_invalida', 'la fecha original no es futura');
select throws_ok($$select public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', now() - interval '91 days', 'FIS-002')$$,
  'P0001', 'fecha_original_invalida', 'la fecha original no es anterior a 90 dias');
select throws_ok($$select public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', '0026-03-01 10:00-05', 'FIS-002')$$,
  'P0001', 'fecha_original_invalida', 'una fecha del ano 26 no se admite');

-- Respuesta unica
select throws_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000003', 'Una respuesta larga', null, null)$$,
  '23514', null, 'una hoja con medio carta exige referencia y fecha de envio');
select throws_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000003', 'corta', 'C-1', now())$$, '23514', null,
  'la respuesta tiene al menos 10 caracteres');
select lives_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000003', 'Respuesta por carta.', 'CARTA-9', '2026-11-18 10:00-05')$$,
  'el administrador responde una hoja con medio carta');
select lives_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000001', 'Respuesta por correo.', null, null)$$,
  'el administrador responde una hoja con medio correo');
select throws_ok($$select public.responder_hoja('11111111-0000-0000-0000-000000000001', 'Otra respuesta larga', null, null)$$,
  'P0001', 'ya_respondida', 'la respuesta es unica');
select throws_ok($$select public.responder_hoja(gen_random_uuid(), 'Una respuesta larga', null, null)$$, 'P0002', null, 'una hoja inexistente no se responde');
reset role;
select is((select respondida_por::text from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'),
  '00000000-0000-0000-0000-0000000000ad', 'la respuesta guarda al autor');
select is((select count(*)::int from public.notificacion where tipo = 'reclamacion_respondida'), 1, 'solo el medio correo envia la respuesta');
select is((select respuesta_enviada_en from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000001'), now(),
  'con medio correo la fecha de envio es la de la respuesta');

-- Inmutabilidad incluso para el propietario de la tabla
select throws_ok($$update public.hoja_reclamacion set detalle = 'otro detalle largo' where id = '11111111-0000-0000-0000-000000000002'$$,
  'P0001', 'hoja_inmutable', 'la hoja no se edita');
select throws_ok($$update public.hoja_reclamacion set respuesta_texto = 'Cambio de respuesta' where id = '11111111-0000-0000-0000-000000000001'$$,
  'P0001', 'hoja_inmutable', 'la respuesta no se edita');
select throws_ok($$delete from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000002'$$,
  'P0001', 'hoja_inmutable', 'la hoja no se borra');
select throws_ok($$update public.adjunto_reclamacion set nombre = 'otro.pdf'$$, 'P0001', 'adjunto_inmutable', 'el adjunto no se edita');
select throws_ok($$delete from public.adjunto_reclamacion$$, 'P0001', 'adjunto_inmutable', 'el adjunto no se borra');

-- Restricciones de la base
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"es_menor": true}'), '[]', '3.3.3.3', false)$$,
  '23514', null, 'un menor exige los datos del representante');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"es_menor": true, "rep_nombre": "Rosa", "rep_domicilio": "Calle 1", "rep_correo": "r@t.pe"}'),
  '[]', '3.3.3.3', false)$$, 'un menor con representante se registra');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"documento": "123"}'), '[]', '3.3.3.3', false)$$,
  '23514', null, 'el DNI tiene 8 cifras');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"detalle": "corto"}'), '[]', '3.3.3.3', false)$$,
  '23514', null, 'el detalle tiene al menos 10 caracteres');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"monto": 0}'), '[]', '3.3.3.3', false)$$,
  '23514', null, 'el monto es mayor que cero');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"medio_respuesta": "paloma"}'), '[]', '3.3.3.3', false)$$,
  '23514', null, 'el medio de respuesta es correo o carta');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(),
  '[{"nombre":"a.pdf","tipo":"application/pdf","tamano":1},{"nombre":"b.pdf","tipo":"application/pdf","tamano":1},{"nombre":"c.pdf","tipo":"application/pdf","tamano":1},{"nombre":"d.pdf","tipo":"application/pdf","tamano":1}]',
  '3.3.3.3', false)$$, '23514', null, 'hasta 3 adjuntos');

-- Limite por IP: 5 por hora (la IP 3.3.3.3 ya registro 1 con exito y las fallidas no cuentan)
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$, 'IP nueva, hoja 1');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$, 'IP nueva, hoja 2');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$, 'IP nueva, hoja 3');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$, 'IP nueva, hoja 4');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$, 'IP nueva, hoja 5');
select throws_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '4.4.4.4', false)$$,
  'P0001', 'demasiadas_solicitudes', 'la sexta hoja de la misma IP en una hora se rechaza');
select lives_ok($$select public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '5.5.5.5', false)$$, 'otra IP no se ve afectada');
select is((select count(*)::int from public.intento_reclamacion where ip_hash = '4.4.4.4'), 0, 'no se guarda la IP en claro');

-- Lo que devuelven las funciones de alta: lo que la respuesta 201 necesita sin releer la hoja
select is((select r_dias from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '6.6.6.6', false)), 15,
  'registrar_hoja devuelve los dias habiles que quedan');
select matches((select r_numero from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '6.6.6.6', false)),
  '^[0-9]{9}-[0-9]{4}$', 'registrar_hoja devuelve el numero');
select is((select r_vence from public.transcribir_hoja(gen_random_uuid(), public.zz_datos(), '[]', now() - interval '80 days', 'FIS-003')),
  public.sumar_dias_habiles(now() - interval '80 days', 15), 'transcribir_hoja devuelve el plazo');
select is((select right(numero, 4) from public.hoja_reclamacion where numero_hoja_fisica = 'FIS-003'),
  public.anio_presentacion(now() - interval '80 days')::text, 'el anio del numero de una transcrita es el de su fecha original');
select is((select jsonb_array_length(r_subidas) from public.registrar_hoja(gen_random_uuid(), public.zz_datos(),
  '[{"nombre": "a.png", "tipo": "image/png", "tamano": 10}, {"nombre": "b.png", "tipo": "image/png", "tamano": 10}]', '0.0.0.1', false)), 2,
  'registrar_hoja devuelve una ruta por adjunto');

-- Correlativo sin huecos: una alta que falla (se deshace) no consume numero
select lives_ok($$select public.registrar_hoja('55555555-0000-0000-0000-000000000001', public.zz_datos(), '[]', '0.0.0.2', false)$$, 'alta antes del fallo');
create temp table zz_corr as select correlativo from public.hoja_reclamacion where id = '55555555-0000-0000-0000-000000000001';
select throws_ok($$select public.registrar_hoja('55555555-0000-0000-0000-000000000002', public.zz_datos('{"documento": "123"}'), '[]', '0.0.0.2', false)$$,
  '23514', null, 'una alta con datos invalidos falla');
select lives_ok($$select public.registrar_hoja('55555555-0000-0000-0000-000000000003', public.zz_datos(), '[]', '0.0.0.2', false)$$, 'alta despues del fallo');
select is((select correlativo from public.hoja_reclamacion where id = '55555555-0000-0000-0000-000000000003') - (select correlativo from zz_corr),
  1::bigint, 'la alta que fallo no consumio un numero del correlativo');
select is((select ultimo from public.contador_reclamacion), (select max(correlativo) from public.hoja_reclamacion), 'el contador va con el ultimo correlativo');

-- Clave de envio: un reintento con la misma clave (24 h) devuelve la hoja ya registrada sin duplicar nada
select lives_ok($$select public.registrar_hoja('33333333-0000-0000-0000-000000000001', public.zz_datos(), '[]', '7.7.6.1', false, 'cccccccc-1111-0000-0000-000000000001')$$,
  'primer envio con clave');
select is((select r_repetida from public.registrar_hoja('33333333-0000-0000-0000-000000000002', public.zz_datos(), '[]', '7.7.7.7', false, 'cccccccc-1111-0000-0000-000000000001')), true,
  'el reintento con la misma clave se reconoce');
select is((select r_existente ->> 'id' from public.registrar_hoja('33333333-0000-0000-0000-000000000003', public.zz_datos(), '[]', '7.7.7.7', false, 'cccccccc-1111-0000-0000-000000000001')),
  '33333333-0000-0000-0000-000000000001', 'devuelve la hoja ya registrada');
select is((select count(*)::int from public.hoja_reclamacion where clave_envio = 'cccccccc-1111-0000-0000-000000000001'), 1, 'no se crea otra hoja');
select is((select r_repetida from public.registrar_hoja('33333333-0000-0000-0000-000000000005', public.zz_datos('{"documento": "87654321"}'), '[]', '7.7.7.7', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'la misma clave con otro documento no es un reintento');
select is((select r_existente from public.registrar_hoja('33333333-0000-0000-0000-000000000006', public.zz_datos('{"correo": "otra@t.pe"}'), '[]', '7.7.6.2', false, 'cccccccc-1111-0000-0000-000000000001')), null::jsonb,
  'la misma clave con otro correo no devuelve la hoja ajena');
select is((select count(*)::int from public.hoja_reclamacion where id in ('33333333-0000-0000-0000-000000000005', '33333333-0000-0000-0000-000000000006')), 2,
  'esas dos altas si crean su hoja');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"detalle": "Otro detalle del servicio."}'), '[]', '7.7.6.3', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'la misma clave con otro detalle no es un reintento');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos('{"pedido": "Otro pedido distinto."}'), '[]', '7.7.6.4', false, 'cccccccc-1111-0000-0000-000000000001')), false,
  'la misma clave con otro pedido no es un reintento');
select is((select r_existente ? 'id_cuenta' from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '7.7.7.7', false, 'cccccccc-1111-0000-0000-000000000001')), true, 'la hoja devuelta trae su cuenta para calcular en_tu_cuenta');
select is((select count(*)::int from public.notificacion where tipo = 'reclamacion_registrada' and datos ->> 'id' = '33333333-0000-0000-0000-000000000001'), 1, 'no se reenvian correos');
select is((select count(*)::int from public.hoja_reclamacion where id in ('33333333-0000-0000-0000-000000000002', '33333333-0000-0000-0000-000000000003')), 0, 'el id del reintento no queda');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '7.7.7.7', false, 'cccccccc-1111-0000-0000-000000000009')), false, 'otra clave es otra hoja');
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '7.7.7.7', false, null)), false, 'sin clave, como siempre');
alter table public.hoja_reclamacion disable trigger user;
update public.hoja_reclamacion set creada_en = now() - interval '25 hours' where id = '33333333-0000-0000-0000-000000000001';
alter table public.hoja_reclamacion enable trigger user;
select is((select r_repetida from public.registrar_hoja(gen_random_uuid(), public.zz_datos(), '[]', '8.8.8.8', false, 'cccccccc-1111-0000-0000-000000000001')), false, 'pasadas 24 h la clave ya no cuenta');

-- dias_habiles_restantes y aviso de plazos (se fijan los plazos saltando la inmutabilidad solo en la prueba)
alter table public.hoja_reclamacion disable trigger user;
update public.hoja_reclamacion set vence_respuesta = public.fin_de_dia_lima(now(), -1)
  where id = '11111111-0000-0000-0000-000000000002';
update public.hoja_reclamacion set vence_respuesta = public.sumar_dias_habiles(now(), 40)
  where id = '11111111-0000-0000-0000-000000000004';
alter table public.hoja_reclamacion enable trigger user;
select cmp_ok(public.dias_habiles_restantes((select vence_respuesta from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000002')),
  '<=', -1, 'una hoja vencida da dias negativos');
select is(public.dias_habiles_restantes(public.fin_de_dia_lima(now(), 0)), 0, 'vence hoy: cero dias');
select is(public.dias_habiles_restantes(public.sumar_dias_habiles(now(), 3)), 3, 'cuenta dias habiles');
delete from public.notificacion where tipo = 'reclamaciones_por_vencer';
select lives_ok($$select public.avisar_plazos_reclamaciones()$$, 'el cron avisa');
select is((select jsonb_array_length(datos -> 'hojas') from public.notificacion where tipo = 'reclamaciones_por_vencer'), 2,
  'solo entran las vencidas (la fijada y la transcrita FIS-003 de marzo; las otras vencen lejos o ya estan respondidas)');

-- Storage: bucket privado, alta publica acotada, lectura del administrador
select is((select public from storage.buckets where id = 'reclamaciones'), false, 'el bucket es privado');
select is((select file_size_limit from storage.buckets where id = 'reclamaciones'), 5242880::bigint, 'el bucket limita a 5 MB');
select lives_ok($$select public.registrar_hoja('44444444-0000-0000-0000-000000000001', public.zz_datos(),
  '[{"nombre": "e.pdf", "tipo": "application/pdf", "tamano": 5}]', '9.9.9.9', false)$$, 'hoja con una subida que va a caducar');
select lives_ok($$select public.registrar_hoja('44444444-0000-0000-0000-000000000002', public.zz_datos(),
  '[{"nombre": "v.pdf", "tipo": "application/pdf", "tamano": 5}]', '9.9.9.8', false)$$, 'hoja con una subida vigente');
select set_config('zz.caducada', (select ruta from public.subida_reclamacion where id_hoja = '44444444-0000-0000-0000-000000000001'), false);
update public.subida_reclamacion set caduca_en = now() - interval '2 hours' where id_hoja = '44444444-0000-0000-0000-000000000001';
set local role anon;
select throws_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', '22222222-0000-0000-0000-000000000001/1.pdf')$$, '42501', null,
  'anon no sube a la ruta antigua <id>/<n>.<ext> sin subida pendiente');
select throws_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', 'cualquier/cosa.exe')$$, '42501', null,
  'anon no sube fuera de la ruta esperada');
select throws_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', gen_random_uuid()::text || '/' || gen_random_uuid()::text || '.pdf')$$, '42501', null,
  'anon no sube a una ruta inventada con la forma correcta');
select throws_ok($$insert into storage.objects (bucket_id, name) values ('reclamaciones', current_setting('zz.caducada'))$$, '42501', null,
  'anon no sube a una subida caducada');
select is((select count(*)::int from storage.objects where bucket_id = 'reclamaciones'), 0, 'anon no lee el bucket');
reset role;
select is(public.limpiar_subidas_reclamacion(), 1, 'la limpieza borra las subidas caducadas');
select is((select count(*)::int from public.subida_reclamacion where id_hoja in ('44444444-0000-0000-0000-000000000001', '44444444-0000-0000-0000-000000000002')), 1,
  'la subida vigente se conserva');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
select is((select count(*)::int from storage.objects where bucket_id = 'reclamaciones'), 0, 'un cliente no lee el bucket');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000ad","role":"authenticated"}', true);
select is((select count(*)::int from storage.objects where bucket_id = 'reclamaciones'), 1, 'el administrador lee el bucket');
reset role;

-- Baja de la cuenta: la hoja se conserva, sin cuenta ni autor
alter table public.usuario disable trigger usuario_conserva_administrador;
delete from auth.users where id in ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000ad');
select is((select count(*)::int from public.hoja_reclamacion where id = '11111111-0000-0000-0000-000000000003'
  and id_cuenta is null and respondida_por is null), 1, 'al borrar la cuenta la hoja se conserva sin ella');

select * from finish();
rollback;
