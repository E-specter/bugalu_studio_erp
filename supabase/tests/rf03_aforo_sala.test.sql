begin;
create extension if not exists pgtap with schema extensions;
select plan(13);

-- RF-03 ampliacion: aforo, certificado ITSE y vencimiento por sala (CA-10). Los tres juntos o los tres nulos.
insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data)
select ('00000000-0000-0000-0000-0000000000' || n)::uuid, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
       n || '@t.pe', '{"nombre":"Usuario"}'
from unnest(array['ad', 'c1']) as n;
update public.usuario set rol = 'administrador' where id = '00000000-0000-0000-0000-0000000000ad';
update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> '00000000-0000-0000-0000-0000000000ad';
insert into public.sala_tecnica (id, nombre, sede) values ('00000000-0000-0000-0000-0000000005a1', 'Sala aforo', 'Sede aforo');

select has_column('public', 'sala_tecnica', 'aforo', 'aforo existe');
select has_column('public', 'sala_tecnica', 'itse_certificado', 'itse_certificado existe');
select has_column('public', 'sala_tecnica', 'itse_vence', 'itse_vence existe');
select is((select aforo from public.sala_tecnica where id = '00000000-0000-0000-0000-0000000005a1'), null, 'una sala nueva no tiene aforo');

select lives_ok($$update public.sala_tecnica set aforo = 12, itse_certificado = 'ITSE-001-2026', itse_vence = '2027-12-31' where id = '00000000-0000-0000-0000-0000000005a1'$$, 'los tres presentes');
select throws_ok($$update public.sala_tecnica set aforo = 0 where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'aforo 0 no');
select throws_ok($$update public.sala_tecnica set aforo = 201 where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'aforo 201 no');
select throws_ok($$update public.sala_tecnica set itse_certificado = '' where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'certificado vacio no');
select throws_ok($$update public.sala_tecnica set itse_certificado = repeat('A', 41) where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'certificado de 41 no');
select throws_ok($$update public.sala_tecnica set itse_certificado = E'A\nB' where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'certificado con salto de linea no');
select throws_ok($$update public.sala_tecnica set itse_vence = null where id = '00000000-0000-0000-0000-0000000005a1'$$, '23514', null, 'dos presentes y uno nulo no');

-- anon y cliente no escriben; la fila queda intacta.
set local role anon;
select throws_ok($$update public.sala_tecnica set aforo = 99 where id = '00000000-0000-0000-0000-0000000005a1'$$, '42501', null, 'anon no escribe');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000c1","role":"authenticated"}', true);
update public.sala_tecnica set aforo = 99 where id = '00000000-0000-0000-0000-0000000005a1';
reset role;
select is((select aforo from public.sala_tecnica where id = '00000000-0000-0000-0000-0000000005a1'), 12, 'el cliente no cambia la fila (RLS)');

select * from finish();
rollback;
