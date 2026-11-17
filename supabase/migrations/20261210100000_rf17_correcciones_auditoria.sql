-- RF-17, correcciones de la auditoria A (ronda 1).

-- Cada parte de la version con como mucho 9 cifras: `string_to_array(version, '.')::int[]` (orden de las versiones)
-- no puede desbordar un int, ni siquiera por SQL. Sustituye a la restriccion sin tope.
alter table public.texto_legal drop constraint texto_legal_version_check;
alter table public.texto_legal add constraint texto_legal_version_check check (
  version ~ '^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$');

-- Las reglas de CA-02 viven tambien en la funcion (el backend las valida antes y traduce estos codigos):
-- version mayor que la ultima del tipo y coherente con `tipo_cambio`, y 15 dias de aviso en mayor y menor
-- (salvo la primera version). Un parche rige al publicarse. Una version repetida la rechaza la unicidad.
create or replace function public.publicar_texto_legal(
  p_tipo text, p_version text, p_tipo_cambio text, p_contenido text, p_resumenes jsonb,
  p_resumen_cambios text, p_vigente_desde timestamptz)
returns public.texto_legal
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.texto_legal;
  ultima int[];
  nueva int[];
  coherente boolean;
  vigente timestamptz := coalesce(p_vigente_desde, now());
begin
  if not public.es_administrador() then
    raise exception 'Solo un administrador.' using errcode = '42501';
  end if;
  perform pg_advisory_xact_lock(20261208, hashtext(p_tipo));
  if exists (select 1 from public.texto_legal where tipo = p_tipo and vigente_desde > now()) then
    raise exception 'version_programada';
  end if;
  -- Una version mal formada o repetida la rechaza la insercion (check y unicidad).
  if p_version ~ '^(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})$'
     and not exists (select 1 from public.texto_legal where tipo = p_tipo and version = p_version) then
    select string_to_array(t.version, '.')::int[] into ultima
      from public.texto_legal t where t.tipo = p_tipo
     order by string_to_array(t.version, '.')::int[] desc limit 1;
    if ultima is not null then
      nueva := string_to_array(p_version, '.')::int[];
      coherente := case p_tipo_cambio
        when 'mayor' then nueva[1] > ultima[1]
        when 'menor' then nueva[1] = ultima[1] and nueva[2] > ultima[2]
        when 'parche' then nueva[1:2] = ultima[1:2] and nueva[3] > ultima[3]
        else true end;  -- otro valor lo rechaza el check de la tabla
      if not coherente then
        raise exception 'version_invalida';
      end if;
      if p_tipo_cambio = 'parche' then
        vigente := now();
      elsif p_vigente_desde is null or p_vigente_desde < now() + interval '15 days' then
        raise exception 'aviso_insuficiente';
      end if;
    end if;
  end if;
  insert into public.texto_legal (tipo, version, tipo_cambio, contenido, resumenes, resumen_cambios, vigente_desde, id_autor)
    values (p_tipo, p_version, p_tipo_cambio, p_contenido, coalesce(p_resumenes, '{}'), p_resumen_cambios, vigente, auth.uid())
    returning * into v;
  if ultima is not null and p_tipo_cambio in ('mayor', 'menor') then
    insert into public.notificacion (tipo, destinatario, datos)
      select 'texto_legal_nuevo', a.email,
             jsonb_build_object('tipo', v.tipo, 'version', v.version, 'tipo_cambio', v.tipo_cambio,
                                'vigente_desde', v.vigente_desde, 'resumen_cambios', v.resumen_cambios)
        from public.usuario u join auth.users a on a.id = u.id
       where u.rol = 'cliente' and a.email is not null;
  end if;
  return v;
end;
$$;

-- Dos cuentas que guardan el mismo documento a la vez no se ven entre si: el bloqueo por documento las serializa.
create or replace function public.recalcular_documento_repetido()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  d record;
begin
  for d in
    select documento_tipo as tipo, documento_numero as numero
      from (values (case when tg_op = 'UPDATE' then old.documento_tipo end,
                    case when tg_op = 'UPDATE' then old.documento_numero end),
                   (new.documento_tipo, new.documento_numero)) v (documento_tipo, documento_numero)
     where documento_numero is not null
  loop
    perform pg_advisory_xact_lock(hashtext(d.tipo || ':' || d.numero));
    update public.usuario u
       set documento_repetido = (select count(*) > 1 from public.usuario o
                                  where o.documento_tipo = d.tipo and o.documento_numero = d.numero)
     where u.documento_tipo = d.tipo and u.documento_numero = d.numero;
  end loop;
  return null;
end;
$$;
