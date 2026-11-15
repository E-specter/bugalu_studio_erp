begin;
create extension if not exists pgtap with schema extensions;
select plan(4);

insert into auth.users (id, instance_id, aud, role, email)
values ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'c1@t.pe');
update public.usuario set correo_verificado_en = now() where id = '00000000-0000-0000-0000-0000000000c1';

update auth.users set raw_user_meta_data = '{"x":1}' where id = '00000000-0000-0000-0000-0000000000c1';
select isnt((select correo_verificado_en from public.usuario where id = '00000000-0000-0000-0000-0000000000c1'), null, 'tocar otra columna no quita la verificacion');

update auth.users set email = 'c1@t.pe' where id = '00000000-0000-0000-0000-0000000000c1';
select isnt((select correo_verificado_en from public.usuario where id = '00000000-0000-0000-0000-0000000000c1'), null, 'reescribir el mismo correo no quita la verificacion');

update auth.users set email = 'c1-nuevo@t.pe' where id = '00000000-0000-0000-0000-0000000000c1';
select is((select correo_verificado_en from public.usuario where id = '00000000-0000-0000-0000-0000000000c1'), null, 'cambiar el correo reinicia la verificacion');
select is((select correo_confirmado_en_usuario), false, 'y el usuario deja de estar confirmado')
  from (select coalesce(correo_verificado_en is not null, false) as correo_confirmado_en_usuario
        from public.usuario where id = '00000000-0000-0000-0000-0000000000c1') x;

select * from finish();
rollback;
