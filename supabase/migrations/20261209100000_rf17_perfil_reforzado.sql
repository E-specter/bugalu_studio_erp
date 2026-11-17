-- RF-17 (etapa A): perfil reforzado (CA-06), pendientes de aceptacion (CA-05), consentimientos opcionales (CA-12)
-- y aceptacion de las condiciones al reservar y al pagar (CA-08, decision 8).

-- Perfil reforzado. `documento_repetido` solo lo escribe el trigger: el cliente no tiene privilegio sobre la columna.
alter table public.usuario
  add column modalidad text not null default 'individual' check (modalidad in ('individual', 'agrupacion')),
  add column documento_tipo text,
  add column documento_numero text,
  add column domicilio text check (domicilio is null or length(domicilio) <= 200),
  add column redes jsonb not null default '[]'
    check (jsonb_typeof(redes) = 'array' and jsonb_array_length(redes) <= 5),
  add column integrantes jsonb not null default '[]'
    check (jsonb_typeof(integrantes) = 'array' and jsonb_array_length(integrantes) <= 20),
  add column es_menor boolean not null default false,
  add column documento_repetido boolean not null default false,
  add constraint usuario_documento_completo check ((documento_tipo is null) = (documento_numero is null)),
  add constraint usuario_documento_formato check (
    documento_tipo is null
    or (documento_tipo = 'dni' and documento_numero ~ '^[0-9]{8}$')
    or (documento_tipo in ('ce', 'pasaporte') and documento_numero ~ '^[A-Z0-9]{6,12}$'));

create index usuario_documento_idx on public.usuario (documento_tipo, documento_numero)
  where documento_numero is not null;

grant update (modalidad, documento_tipo, documento_numero, domicilio, redes, integrantes, es_menor)
  on public.usuario to authenticated;

-- Un documento usado por varias cuentas no bloquea: todas quedan marcadas para revision del Administrador (decision 4).
create function public.recalcular_documento_repetido()
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
    update public.usuario u
       set documento_repetido = (select count(*) > 1 from public.usuario o
                                  where o.documento_tipo = d.tipo and o.documento_numero = d.numero)
     where u.documento_tipo = d.tipo and u.documento_numero = d.numero;
  end loop;
  return null;
end;
$$;
revoke all on function public.recalcular_documento_repetido() from public, anon, authenticated;
create trigger usuario_documento_repetido
  after insert or update of documento_tipo, documento_numero on public.usuario
  for each row execute function public.recalcular_documento_repetido();

-- Consentimiento opcional que registra cada aceptacion (promociones y usos promocionales comparten contexto).
alter table public.aceptacion
  add column consentimiento text,
  add constraint aceptacion_consentimiento_coherente check (
    (contexto = 'promociones' and consentimiento in ('promociones_correo', 'promociones_whatsapp'))
    or (contexto = 'usos_promocionales' and consentimiento in ('fotos_videos', 'excluir_material'))
    or (contexto not in ('promociones', 'usos_promocionales') and consentimiento is null));
create unique index aceptacion_consentimiento_activo on public.aceptacion (id_usuario, consentimiento)
  where retirada_en is null and consentimiento is not null;
-- Una operacion acepta una vez por contexto.
create unique index aceptacion_operacion_unica on public.aceptacion (contexto, id_operacion)
  where id_operacion is not null;

-- Textos del registro que el usuario debe aceptar: los que nunca vio y, de terminos y declaracion, una version
-- mayor posterior a la que acepto (menor y parche no piden nada; la politica se muestra, no se reacepta).
create function public.mis_pendientes()
returns table (tipo text, version text, contexto text, motivo text)
language sql
stable
set search_path = ''
as $$
  select v.tipo, v.version, 'registro'::text,
         case when ult.version is null then 'registro_pendiente' else 'version_mayor' end
    from public.textos_vigentes() v
    left join lateral (
      select a.version from public.aceptacion a
       where a.id_usuario = (select auth.uid()) and a.contexto = 'registro' and a.tipo = v.tipo
       order by string_to_array(a.version, '.')::int[] desc limit 1) ult on true
   where (v.tipo in ('terminos_uso', 'politica_privacidad')
          or (v.tipo = 'declaracion_agrupacion' and exists (
                select 1 from public.usuario u where u.id = (select auth.uid()) and u.modalidad = 'agrupacion')))
     and (ult.version is null
          or (v.tipo <> 'politica_privacidad'
              and (string_to_array(v.version, '.')::int[])[1] > (string_to_array(ult.version, '.')::int[])[1]))
   order by v.tipo;
$$;

-- Da o retira un consentimiento opcional (CA-12). Dar es idempotente; retirar solo marca `retirada_en`.
create function public.cambiar_consentimiento(p_consentimiento text, p_dar boolean)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_tipo text;
  v_contexto text;
  v public.texto_legal;
begin
  if auth.uid() is null then
    raise exception 'Sin sesion.' using errcode = '42501';
  end if;
  if p_consentimiento in ('promociones_correo', 'promociones_whatsapp') then
    v_tipo := 'politica_privacidad';
    v_contexto := 'promociones';
  elsif p_consentimiento in ('fotos_videos', 'excluir_material') then
    v_tipo := 'condiciones_contratacion';
    v_contexto := 'usos_promocionales';
  else
    raise exception 'Consentimiento no admitido.' using errcode = '22023';
  end if;
  if p_dar then
    select * into v from public.textos_vigentes() t where t.tipo = v_tipo;
    if not found then
      raise exception 'texto_desactualizado';
    end if;
    insert into public.aceptacion (id_usuario, tipo, version, contexto, consentimiento)
      values (auth.uid(), v.tipo, v.version, v_contexto, p_consentimiento)
      on conflict (id_usuario, consentimiento) where retirada_en is null and consentimiento is not null do nothing;
  else
    update public.aceptacion set retirada_en = now()
     where id_usuario = auth.uid() and consentimiento = p_consentimiento and retirada_en is null;
  end if;
end;
$$;

-- Aceptacion de las condiciones de contratacion vigentes para una reserva (version del cliente, debe ser la
-- vigente) o un pago (la version vigente, sin que la envie el cliente; sin texto publicado no registra nada).
create function public.aceptar_condiciones(p_contexto text, p_id_operacion uuid, p_version text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v public.texto_legal;
begin
  if auth.uid() is null then
    raise exception 'Sin sesion.' using errcode = '42501';
  end if;
  if p_contexto not in ('reserva', 'pago') or (p_contexto = 'reserva' and p_version is null) then
    raise exception 'Contexto no admitido.' using errcode = '22023';
  end if;
  select * into v from public.textos_vigentes() t where t.tipo = 'condiciones_contratacion';
  if not found then
    if p_contexto = 'pago' then
      return;
    end if;
    raise exception 'texto_desactualizado';
  end if;
  if p_version is not null and p_version <> v.version then
    raise exception 'texto_desactualizado';
  end if;
  if p_contexto = 'reserva' then
    if not exists (select 1 from public.reserva where id = p_id_operacion and id_cliente = auth.uid()) then
      raise exception 'La reserva no es tuya.' using errcode = '42501';
    end if;
  elsif not exists (select 1 from public.comprobante_pago where id = p_id_operacion and id_cliente = auth.uid()) then
    raise exception 'El pago no es tuyo.' using errcode = '42501';
  end if;
  perform public.insertar_aceptacion(auth.uid(), v.tipo, v.version, p_contexto, p_id_operacion, null);
end;
$$;

-- Datos que faltan para la primera reserva (CA-07); una sola regla para identidad y reservas.
create function public.campos_faltantes_para_reservar()
returns text[]
language sql
stable
set search_path = ''
as $$
  select coalesce(array_remove(array[
      case when nullif(btrim(u.nombre), '') is null then 'nombre' end,
      case when u.documento_numero is null then 'documento' end,
      case when u.telefono is null then 'telefono' end], null), array['nombre', 'documento', 'telefono'])
    from public.usuario u where u.id = (select auth.uid());
$$;

revoke all on function public.mis_pendientes() from public, anon;
revoke all on function public.cambiar_consentimiento(text, boolean) from public, anon;
revoke all on function public.aceptar_condiciones(text, uuid, text) from public, anon;
revoke all on function public.campos_faltantes_para_reservar() from public, anon;
grant execute on function public.mis_pendientes() to authenticated;
grant execute on function public.cambiar_consentimiento(text, boolean) to authenticated;
grant execute on function public.aceptar_condiciones(text, uuid, text) to authenticated;
grant execute on function public.campos_faltantes_para_reservar() to authenticated;
