begin;
create extension if not exists pgtap with schema extensions;
select plan(5);

select has_column('public', 'servicio', 'monto_fijo', 'servicio.monto_fijo existe');
select col_not_null('public', 'servicio', 'monto_fijo', 'monto_fijo no admite nulos');
select is((select count(*)::int from public.servicio where monto_fijo <> 0), 0, 'los servicios existentes parten con monto fijo 0');
select throws_ok($$update public.servicio set monto_fijo = -1 where nombre = 'Ensayo'$$, '23514', null, 'monto fijo negativo');
select lives_ok($$update public.servicio set monto_fijo = 15.50 where nombre = 'Ensayo'$$, 'monto fijo con dos decimales');

select * from finish();
rollback;
