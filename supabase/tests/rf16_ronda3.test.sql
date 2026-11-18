begin;
create extension if not exists pgtap with schema extensions;
select plan(10);

-- RF-16, auditoria A ronda 3: IPv4 mapeada en IPv6 y privilegios de las funciones de hoja y de huerfanos.
select isnt(public.ip_para_limite('::ffff:1.2.3.4'), public.ip_para_limite('::ffff:5.6.7.8'), 'dos IPv4 mapeadas distintas no comparten limite');
select is(public.ip_para_limite('::ffff:1.2.3.4'), public.ip_para_limite('1.2.3.4'), 'una IPv4 mapeada vale como la IPv4 embebida');
select is(public.ip_para_limite('::ffff:102:304'), public.ip_para_limite('1.2.3.4'), 'tambien con la forma hexadecimal');
select isnt(public.ip_para_limite('2001:db8::1'), public.ip_para_limite('2001:db8:0:1::1'), 'IPv6 comun sigue agrupado por /64');

select ok(has_function_privilege('bugalu_api', 'public.avisar_hoja(uuid)', 'execute'), 'bugalu_api ejecuta avisar_hoja');
select ok(not has_function_privilege('anon', 'public.avisar_hoja(uuid)', 'execute')
  and not has_function_privilege('authenticated', 'public.avisar_hoja(uuid)', 'execute'), 'anon y authenticated no ejecutan avisar_hoja');
select ok(not has_function_privilege('service_role', 'public.avisar_hoja(uuid)', 'execute'), 'service_role tampoco');
select ok(has_function_privilege('bugalu_api', 'public.subida_reclamacion_huerfana(text)', 'execute'), 'bugalu_api ejecuta subida_reclamacion_huerfana');
select ok(not has_function_privilege('authenticated', 'public.subida_reclamacion_huerfana(text)', 'execute')
  and not has_function_privilege('service_role', 'public.subida_reclamacion_huerfana(text)', 'execute'),
  'authenticated y service_role no ejecutan subida_reclamacion_huerfana');
select ok(has_function_privilege('anon', 'public.subida_reclamacion_huerfana(text)', 'execute'), 'anon si: la politica de borrado la evalua con sus privilegios');

select * from finish();
rollback;
