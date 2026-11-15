begin;
create extension if not exists pgtap with schema extensions;
select plan(6);

select is(
  (select (rolcanlogin, rolinherit, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole)::text
   from pg_roles where rolname = 'bugalu_api'),
  '(t,f,f,f,f,f)',
  'bugalu_api: login, noinherit, sin superusuario, bypassrls, createdb ni createrole');
select is((select count(*)::int from pg_auth_members m join pg_roles r on r.oid = m.member
           where r.rolname = 'bugalu_api'), 2, 'bugalu_api solo es miembro de anon y authenticated');
select ok(pg_has_role('bugalu_api', 'authenticated', 'member'), 'puede asumir authenticated');
select ok(pg_has_role('bugalu_api', 'anon', 'member'), 'puede asumir anon');
select ok(not pg_has_role('bugalu_api', 'postgres', 'member'), 'no puede asumir postgres');
select ok(not has_table_privilege('bugalu_api', 'public.usuario', 'select'), 'sin asumir un rol no lee usuario');

select * from finish();
rollback;
