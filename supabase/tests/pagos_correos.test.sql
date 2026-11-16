begin;
create extension if not exists pgtap with schema extensions;
select plan(5);

-- RF-05: la bandeja (rol bugalu_api, sin asumir otro rol) lee los datos para pagar del correo de reserva.
select ok(has_table_privilege('bugalu_api', 'public.instruccion_pago', 'select'), 'bugalu_api lee instruccion_pago');
select ok(not has_table_privilege('bugalu_api', 'public.instruccion_pago', 'update'), 'bugalu_api no escribe instruccion_pago');
select is((select count(*)::int from pg_policies where tablename = 'instruccion_pago' and 'bugalu_api' = any(roles)), 1, 'una politica de lectura para bugalu_api');
select ok(not has_table_privilege('bugalu_api', 'public.comprobante_pago', 'select'), 'bugalu_api no lee comprobantes');
select ok(not has_table_privilege('bugalu_api', 'public.contacto_estudio', 'select'), 'bugalu_api no lee el contacto');

select * from finish();
rollback;
