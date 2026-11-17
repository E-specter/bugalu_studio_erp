-- RF-18 (parte A, ADR-015): niveles de cancelacion, cancelacion con pagos, credito y su uso, devoluciones,
-- inasistencia, caso excepcional y avisos. La politica se calcula y se protege aqui; el backend solo la expone.
-- Orden de bloqueo unico (como RF-05): cuotas de la reserva -> reserva -> creditos.

-- 1. Foto de parametros: los cinco que faltaban viajan en parametros_vigentes() y en cada reserva.
create or replace function public.parametros_vigentes()
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'porcentaje_igv', (select to_char(porcentaje_igv, 'FM990.00') from public.configuracion_impuestos),
    'precios_incluyen_igv', (select precios_incluyen_igv from public.configuracion_impuestos),
    'horas_limite_pago', (select valor from public.parametro where clave = 'horas_limite_pago'),
    'horas_nivel_1', (select valor from public.parametro where clave = 'horas_nivel_1'),
    'horas_nivel_2', (select valor from public.parametro where clave = 'horas_nivel_2'),
    'porcentaje_adelanto', (select valor from public.parametro where clave = 'porcentaje_adelanto'),
    'porcentaje_penalizacion_nivel_2', (select valor from public.parametro where clave = 'porcentaje_penalizacion_nivel_2'),
    'minutos_tolerancia_inasistencia', (select valor from public.parametro where clave = 'minutos_tolerancia_inasistencia'),
    'dias_vigencia_credito', (select valor from public.parametro where clave = 'dias_vigencia_credito'),
    'reprogramaciones_nivel_1', (select valor from public.parametro where clave = 'reprogramaciones_nivel_1'),
    'reprogramaciones_nivel_2', (select valor from public.parametro where clave = 'reprogramaciones_nivel_2'));
$$;

-- Las reservas existentes reciben los valores vigentes de los cinco nuevos (los que ya tenian no cambian).
update public.reserva set parametros_aplicados = public.parametros_vigentes() || parametros_aplicados;
alter table public.reserva drop constraint reserva_parametros_aplicados_check;
alter table public.reserva add constraint reserva_parametros_aplicados_check check (
  parametros_aplicados ?& array['porcentaje_igv', 'precios_incluyen_igv', 'horas_limite_pago',
    'horas_nivel_1', 'horas_nivel_2', 'porcentaje_adelanto', 'porcentaje_penalizacion_nivel_2',
    'minutos_tolerancia_inasistencia', 'dias_vigencia_credito', 'reprogramaciones_nivel_1',
    'reprogramaciones_nivel_2']);

-- 2. Reserva: estado `no_asistio`, momento de creacion y los datos de la cancelacion (solo las funciones los escriben).
alter table public.reserva drop constraint reserva_estado_check;
alter table public.reserva add constraint reserva_estado_check check (
  estado in ('pre_reservada', 'confirmada', 'en_curso', 'finalizada', 'cancelada', 'no_asistio'));
alter table public.reserva
  add column creada_en timestamptz not null default now(),
  add column nivel_cancelacion smallint check (nivel_cancelacion in (1, 2, 3)),
  add column aviso_en timestamptz,
  add column cancelacion_por text check (cancelacion_por in ('cliente', 'estudio', 'inasistencia')),
  add column id_cancelador uuid references public.usuario (id) on delete set null,
  add column pagado_cancelacion numeric(10, 2) check (pagado_cancelacion >= 0),
  add column retenido numeric(10, 2) check (retenido >= 0),
  add column credito_generado numeric(10, 2) check (credito_generado >= 0),
  add column eleccion_estudio text check (eleccion_estudio in ('pendiente', 'reprogramada', 'devolucion')),
  add column excepcion_motivo text check (char_length(excepcion_motivo) between 10 and 500),
  add column excepcion_por uuid references public.usuario (id) on delete set null,
  add column excepcion_en timestamptz;

-- Cuota: estado `anulada` y lo aplicado (capturas aprobadas y credito).
alter table public.cuota drop constraint cuota_estado_check;
alter table public.cuota add constraint cuota_estado_check check (estado in ('pendiente', 'pagada', 'anulada'));
alter table public.cuota add column pagado numeric(10, 2) not null default 0 check (pagado >= 0);
update public.cuota c set pagado = coalesce(
  (select sum(p.monto) from public.comprobante_pago p where p.id_cuota = c.id and p.estado = 'aprobado'), c.monto)
  where c.estado = 'pagada';

-- Avisos nuevos.
alter table public.notificacion drop constraint notificacion_tipo_check;
alter table public.notificacion add constraint notificacion_tipo_check check (tipo in
  ('reserva_creada', 'reserva_caducada', 'pago_registrado', 'pago_aprobado', 'pago_rechazado',
   'reserva_finalizada_saldo', 'reserva_cancelada_cliente', 'reserva_cancelada_estudio', 'texto_legal_nuevo',
   'reserva_cancelada_con_pagos', 'inasistencia_marcada', 'credito_por_vencer', 'devolucion_solicitada',
   'devolucion_decidida', 'devolucion_realizada'));

-- "Tiene pagos" ahora incluye lo aplicado a las cuotas (credito) ademas de capturas en validacion o aprobadas.
create or replace function public.tiene_pagos(p_id_reserva uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (select 1 from public.cuota where id_reserva = p_id_reserva and (estado = 'pagada' or pagado > 0))
      or exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                 where c.id_reserva = p_id_reserva and p.estado in ('pendiente_validacion', 'aprobado'));
$$;

-- 3. Tablas nuevas. Todas con RLS; nadie las escribe por fuera de las funciones de este archivo.
create table public.credito (
  id uuid primary key default gen_random_uuid(),
  id_cliente uuid not null references public.usuario (id),
  id_reserva uuid not null references public.reserva (id) on delete cascade, -- reserva de origen
  tipo text not null check (tipo in ('nivel_1', 'nivel_2', 'reprogramacion', 'excepcion')),
  monto numeric(10, 2) not null check (monto > 0),
  saldo numeric(10, 2) not null check (saldo >= 0 and saldo <= monto),
  vence timestamptz not null,
  estado text not null default 'vigente' check (estado in ('vigente', 'agotado', 'vencido')),
  congelado boolean not null default false, -- hay una devolucion pendiente: no se usa ni vence
  aviso_enviado_en timestamptz,
  creado_en timestamptz not null default now(),
  check ((estado = 'agotado') = (saldo = 0))
);
create index credito_cliente_idx on public.credito (id_cliente, vence);

create table public.aplicacion_credito (
  id uuid primary key default gen_random_uuid(),
  id_credito uuid not null references public.credito (id) on delete cascade,
  id_cuota uuid not null references public.cuota (id) on delete cascade,
  monto numeric(10, 2) not null check (monto > 0),
  id_usuario uuid references public.usuario (id),
  aplicada_en timestamptz not null default now()
);
create index aplicacion_credito_cuota_idx on public.aplicacion_credito (id_cuota);

create table public.devolucion (
  id uuid primary key default gen_random_uuid(),
  id_credito uuid references public.credito (id) on delete cascade,
  id_reserva uuid not null references public.reserva (id) on delete cascade,
  id_cliente uuid not null references public.usuario (id),
  tipo text not null check (tipo in ('nivel_1', 'estudio')),
  motivo text not null check (char_length(motivo) between 1 and 500),
  monto_solicitado numeric(10, 2) not null check (monto_solicitado >= 0),
  solicitada_en timestamptz not null default now(),
  estado text not null default 'pendiente' check (estado in ('pendiente', 'aprobada', 'rechazada', 'realizada')),
  monto_aprobado numeric(10, 2) check (monto_aprobado > 0),
  motivo_decision text check (char_length(motivo_decision) between 1 and 500),
  decidida_en timestamptz,
  id_decisor uuid references public.usuario (id) on delete set null,
  nota_realizada text check (char_length(nota_realizada) between 1 and 500),
  realizada_en timestamptz,
  id_realizador uuid references public.usuario (id) on delete set null,
  limite timestamptz, -- plazo de 7 dias habiles de las del estudio
  check (tipo <> 'nivel_1' or id_credito is not null),
  check ((estado in ('aprobada', 'realizada')) = (monto_aprobado is not null)),
  check ((estado = 'pendiente') = (decidida_en is null)),
  check ((estado = 'realizada') = (realizada_en is not null))
);
create unique index devolucion_pendiente_uq on public.devolucion (id_credito) where estado = 'pendiente';
create index devolucion_estado_idx on public.devolucion (estado, solicitada_en);
create index devolucion_reserva_idx on public.devolucion (id_reserva);

-- Historial de reprogramaciones (lo escribe la TAREA-RF18-3; aqui solo existe, inmutable, para la vista previa).
create table public.reprogramacion (
  id uuid primary key default gen_random_uuid(),
  id_reserva uuid not null references public.reserva (id) on delete cascade,
  anterior_inicio timestamptz not null,
  nuevo_inicio timestamptz not null,
  nivel smallint check (nivel in (1, 2)), -- null: tras una cancelacion del estudio, no cuenta para los limites
  penalizacion numeric(10, 2) not null default 0 check (penalizacion >= 0),
  total_anterior numeric(10, 2) not null,
  total_nuevo numeric(10, 2) not null,
  id_autor uuid references public.usuario (id),
  en timestamptz not null default now()
);
create index reprogramacion_reserva_idx on public.reprogramacion (id_reserva, en);

alter table public.credito enable row level security;
alter table public.aplicacion_credito enable row level security;
alter table public.devolucion enable row level security;
alter table public.reprogramacion enable row level security;
revoke all on public.credito, public.aplicacion_credito, public.devolucion, public.reprogramacion from anon, authenticated;
grant select on public.credito, public.aplicacion_credito, public.devolucion, public.reprogramacion to authenticated;
create policy credito_lee on public.credito for select to authenticated
  using (id_cliente = (select auth.uid()) or public.es_administrador());
create policy aplicacion_credito_lee on public.aplicacion_credito for select to authenticated
  using (exists (select 1 from public.credito k where k.id = id_credito));
create policy devolucion_lee on public.devolucion for select to authenticated
  using (id_cliente = (select auth.uid()) or public.es_administrador());
create policy reprogramacion_lee on public.reprogramacion for select to authenticated
  using (exists (select 1 from public.reserva r where r.id = id_reserva));

-- Inmutabilidad (como RF-17): el credito solo cambia saldo, estado, vencimiento y marcas; la aplicacion y el
-- historial no cambian; la devolucion no cambia lo pedido ni lo decidido. Borrar solo en cascada desde la reserva.
create function public.sin_borrado_directo()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' and pg_trigger_depth() > 1 then
    return old; -- en cascada desde la reserva, nunca una sentencia directa
  end if;
  raise exception 'Un registro de % no se edita ni se borra.', tg_table_name;
end;
$$;
create trigger aplicacion_credito_inmutable before update or delete on public.aplicacion_credito
  for each row execute function public.sin_borrado_directo();
create trigger reprogramacion_inmutable before update or delete on public.reprogramacion
  for each row execute function public.sin_borrado_directo();

create function public.credito_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' and to_jsonb(new) - 'saldo' - 'estado' - 'vence' - 'congelado' - 'aviso_enviado_en'
     = to_jsonb(old) - 'saldo' - 'estado' - 'vence' - 'congelado' - 'aviso_enviado_en' then
    return new;
  end if;
  if tg_op = 'DELETE' and pg_trigger_depth() > 1 then
    return old;
  end if;
  raise exception 'Un registro de % no se edita ni se borra por fuera de las funciones.', tg_table_name;
end;
$$;
create trigger credito_sin_edicion before update or delete on public.credito
  for each row execute function public.credito_inmutable();

create function public.devolucion_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE'
     and (to_jsonb(new) - 'estado' - 'monto_aprobado' - 'motivo_decision' - 'decidida_en' - 'id_decisor'
          - 'nota_realizada' - 'realizada_en' - 'id_realizador')
       = (to_jsonb(old) - 'estado' - 'monto_aprobado' - 'motivo_decision' - 'decidida_en' - 'id_decisor'
          - 'nota_realizada' - 'realizada_en' - 'id_realizador')
     and (old.estado = 'pendiente'
          or ((new.monto_aprobado, new.motivo_decision, new.decidida_en, new.id_decisor)
              is not distinct from (old.monto_aprobado, old.motivo_decision, old.decidida_en, old.id_decisor)
              and old.estado = 'aprobada')) then
    return new;
  end if;
  if tg_op = 'DELETE' and pg_trigger_depth() > 1 then
    return old;
  end if;
  raise exception 'Un registro de % no se edita ni se borra por fuera de las funciones.', tg_table_name;
end;
$$;
create trigger devolucion_sin_edicion before update or delete on public.devolucion
  for each row execute function public.devolucion_inmutable();

-- Una solicitud pendiente congela su credito (no se usa ni vence).
create function public.congelar_credito()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.estado = 'pendiente' and new.id_credito is not null then
    update public.credito set congelado = true where id = new.id_credito;
  end if;
  return null;
end;
$$;
revoke all on function public.congelar_credito() from public, anon, authenticated;
create trigger devolucion_congela after insert on public.devolucion
  for each row execute function public.congelar_credito();

-- Barrera sobre `reserva`: una persona con rol de API no cancela con pagos ni marca inasistencia por UPDATE directo
-- (eso lo hacen las funciones, que calculan el nivel y los montos), y la excepcion aplicada no se quita.
create function public.reserva_barrera()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.excepcion_en is not null and new.excepcion_en is null then
    raise exception 'La excepcion aplicada no se quita.';
  end if;
  if current_user in ('authenticated', 'anon') then
    if new.estado = 'no_asistio' and old.estado <> 'no_asistio' then
      raise exception 'La inasistencia se marca con marcar_inasistencia.' using errcode = '42501';
    end if;
    if new.estado = 'cancelada' and old.estado <> 'cancelada'
       and (exists (select 1 from public.cuota where id_reserva = old.id and (estado = 'pagada' or pagado > 0))
            or exists (select 1 from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                       where c.id_reserva = old.id and p.estado in ('pendiente_validacion', 'aprobado'))) then
      raise exception 'Una reserva con pagos se cancela con cancelar_reserva.' using errcode = '42501';
    end if;
  end if;
  return new;
end;
$$;
create trigger reserva_barrera before update on public.reserva
  for each row execute function public.reserva_barrera();

-- 4. Politica pura.
create function public.nivel_cancelacion(p_inicio timestamptz, p_aviso timestamptz, p_parametros jsonb)
returns smallint
language sql
immutable
set search_path = ''
as $$
  select case
    when p_inicio - p_aviso > make_interval(hours => (p_parametros ->> 'horas_nivel_1')::int) then 1
    when p_inicio - p_aviso > make_interval(hours => (p_parametros ->> 'horas_nivel_2')::int) then 2
    else 3
  end::smallint;
$$;

create function public.penalizacion_nivel_2(p_total numeric, p_parametros jsonb)
returns numeric
language sql
immutable
set search_path = ''
as $$
  select round(p_total * (p_parametros ->> 'porcentaje_penalizacion_nivel_2')::numeric / 100, 2);
$$;

-- Final del dia `p_dias` dias despues, en Lima: el ultimo microsegundo (el credito se usa mientras vence > ahora).
create function public.fin_de_dia_lima(p_desde timestamptz, p_dias integer)
returns timestamptz
language sql
stable
set search_path = ''
as $$
  select (date_trunc('day', (p_desde at time zone 'America/Lima') + make_interval(days => p_dias + 1))
          at time zone 'America/Lima') - interval '1 microsecond';
$$;

-- 'antes' | 'abierta' | 'despues': ventana para marcar la inasistencia (desde inicio + tolerancia hasta el fin).
create function public.ventana_inasistencia(p_inicio timestamptz, p_fin timestamptz, p_minutos integer, p_ahora timestamptz)
returns text
language sql
immutable
set search_path = ''
as $$
  select case
    when p_ahora < p_inicio + make_interval(mins => p_minutos) then 'antes'
    when p_ahora > p_fin then 'despues'
    else 'abierta'
  end;
$$;
revoke all on function public.nivel_cancelacion(timestamptz, timestamptz, jsonb), public.penalizacion_nivel_2(numeric, jsonb),
  public.fin_de_dia_lima(timestamptz, integer), public.ventana_inasistencia(timestamptz, timestamptz, integer, timestamptz)
  from public, anon;
grant execute on function public.nivel_cancelacion(timestamptz, timestamptz, jsonb), public.penalizacion_nivel_2(numeric, jsonb),
  public.fin_de_dia_lima(timestamptz, integer), public.ventana_inasistencia(timestamptz, timestamptz, integer, timestamptz)
  to authenticated;

-- Vista previa calculada (interna): nivel, montos y reprogramaciones restantes con los parametros guardados.
create function public.calcular_cancelacion(p_id_reserva uuid, p_aviso timestamptz)
returns table (nivel smallint, anticipacion_horas numeric, pagado numeric, en_validacion numeric, retenido numeric,
               credito numeric, credito_vence timestamptz, puede_reprogramar boolean, reprogramaciones_restantes integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_hechas integer;
  v_hechas_2 integer;
begin
  select * into r from public.reserva where id = p_id_reserva;
  pagado := coalesce((select sum(c.pagado) from public.cuota c where c.id_reserva = r.id), 0);
  en_validacion := coalesce((select sum(p.monto) from public.comprobante_pago p join public.cuota c on c.id = p.id_cuota
                             where c.id_reserva = r.id and p.estado = 'pendiente_validacion'), 0);
  anticipacion_horas := round(extract(epoch from (r.inicio - p_aviso)) / 3600, 2);
  if public.tiene_pagos(r.id) then
    nivel := public.nivel_cancelacion(r.inicio, p_aviso, r.parametros_aplicados);
    retenido := case nivel when 1 then 0 when 2 then least(pagado, public.penalizacion_nivel_2(r.total, r.parametros_aplicados))
                else pagado end;
  else
    nivel := null;
    retenido := 0;
  end if;
  credito := pagado - retenido;
  credito_vence := case when credito > 0
    then public.fin_de_dia_lima(now(), (r.parametros_aplicados ->> 'dias_vigencia_credito')::int) end;
  select count(*) filter (where g.nivel is not null), count(*) filter (where g.nivel = 2) into v_hechas, v_hechas_2
    from public.reprogramacion g where g.id_reserva = r.id;
  reprogramaciones_restantes := case
    when r.estado <> 'confirmada' or nivel is null or nivel = 3 then 0
    when nivel = 1 then greatest((r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int - v_hechas, 0)
    else greatest(least((r.parametros_aplicados ->> 'reprogramaciones_nivel_1')::int - v_hechas,
                        (r.parametros_aplicados ->> 'reprogramaciones_nivel_2')::int - v_hechas_2), 0)
  end;
  puede_reprogramar := reprogramaciones_restantes > 0;
  return next;
end;
$$;
revoke all on function public.calcular_cancelacion(uuid, timestamptz) from public, anon, authenticated;

-- Genera un credito vigente con vencimiento al final del dia `p_dias` en Lima.
create function public.generar_credito(p_id_cliente uuid, p_id_reserva uuid, p_tipo text, p_monto numeric, p_dias integer)
returns void
language sql
security definer
set search_path = ''
as $$
  insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence)
  values (p_id_cliente, p_id_reserva, p_tipo, p_monto, p_monto, public.fin_de_dia_lima(now(), p_dias));
$$;
revoke all on function public.generar_credito(uuid, uuid, text, numeric, integer) from public, anon, authenticated;

-- Valida `aviso_en` de quien cancela en nombre del cliente: ni futuro ni anterior a la creacion.
create function public.validar_aviso(p_aviso timestamptz, p_creada timestamptz)
returns void
language plpgsql
stable
set search_path = ''
as $$
begin
  if p_aviso is null or p_aviso > now() or p_aviso < p_creada then
    raise exception 'aviso_invalido' using errcode = 'P0001';
  end if;
end;
$$;
revoke all on function public.validar_aviso(timestamptz, timestamptz) from public, anon, authenticated;

-- Vista previa de la cancelacion (CA-02): sin cambiar nada. Dueno o administrador; `aviso_en` solo del administrador.
-- P0002 si no es suya (404), 42501 si es personal u otro rol sin derecho, P0001 no_cancelable / aviso_invalido.
create function public.vista_cancelacion(p_id uuid, p_aviso_en timestamptz default null)
returns table (nivel smallint, anticipacion_horas numeric, pagado numeric, en_validacion numeric, retenido numeric,
               credito numeric, credito_vence timestamptz, puede_reprogramar boolean, reprogramaciones_restantes integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_admin boolean;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into r from public.reserva where id = p_id;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_admin := public.es_administrador();
  if r.id_cliente <> v_uid and not v_admin then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p_aviso_en is not null and not v_admin then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada') or r.inicio <= now() then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if p_aviso_en is not null then
    perform public.validar_aviso(p_aviso_en, r.creada_en);
  end if;
  return query select * from public.calcular_cancelacion(r.id, coalesce(p_aviso_en, now()));
end;
$$;
revoke all on function public.vista_cancelacion(uuid, timestamptz) from public, anon;
grant execute on function public.vista_cancelacion(uuid, timestamptz) to authenticated;

-- 5. Cancelar (CA-01, CA-03, CA-04, CA-13 parcial). Con pagos el cliente confirma el nivel (`nivel_cambiado` lleva la
-- vista previa nueva en DETAIL); el administrador cancela `por` el estudio (motivo administrador, eleccion pendiente
-- si habia pagos) o en nombre del cliente (con `aviso_en` y nota). Todo en una transaccion.
drop function public.cancelar_reserva(uuid, text);
create function public.cancelar_reserva(
  p_id uuid, p_nota text default null, p_nivel_esperado integer default null, p_por text default null,
  p_aviso_en timestamptz default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_dueno boolean;
  v_admin boolean;
  v_directo boolean; -- el cliente cancela por si mismo
  v_por text;
  v_nota text := nullif(btrim(p_nota), '');
  v_aviso timestamptz;
  v_tiene boolean;
  v_vista record;
  v_nivel smallint;
  v_dias integer;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  v_dueno := r.id_cliente = v_uid;
  v_admin := public.es_administrador();
  if not v_dueno and not v_admin then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p_por is not null and p_por not in ('cliente', 'estudio') then
    raise exception 'por_invalido' using errcode = '22023';
  end if;
  v_directo := v_dueno and p_aviso_en is null and coalesce(p_por, 'cliente') = 'cliente';
  if not v_directo and not v_admin then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  v_por := case when v_directo then 'cliente' else coalesce(p_por, 'estudio') end;
  if r.estado not in ('pre_reservada', 'confirmada') or r.inicio <= now() then
    raise exception 'no_cancelable' using errcode = 'P0001';
  end if;
  if char_length(v_nota) > 300 or v_nota ~ '[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]' then
    raise exception 'nota_invalida' using errcode = '22023';
  end if;
  if v_por = 'cliente' and not v_directo then
    perform public.validar_aviso(p_aviso_en, r.creada_en);
    v_aviso := p_aviso_en;
  else
    v_aviso := now();
  end if;
  v_tiene := public.tiene_pagos(r.id);
  if not v_directo and v_nota is null and (v_tiene or v_por = 'cliente') then
    raise exception 'nota_requerida' using errcode = 'P0001';
  end if;
  select * into v_vista from public.calcular_cancelacion(r.id, v_aviso);
  if v_directo and v_tiene and p_nivel_esperado is distinct from v_vista.nivel then
    raise exception 'nivel_cambiado' using errcode = 'P0001', detail = jsonb_build_object(
      'nivel', v_vista.nivel, 'anticipacion_horas', v_vista.anticipacion_horas, 'pagado', v_vista.pagado::text,
      'en_validacion', v_vista.en_validacion::text, 'retenido', v_vista.retenido::text, 'credito', v_vista.credito::text,
      'credito_vence', v_vista.credito_vence, 'puede_reprogramar', v_vista.puede_reprogramar,
      'reprogramaciones_restantes', v_vista.reprogramaciones_restantes)::text;
  end if;
  -- Por el estudio no hay nivel ni retencion: el cliente elige despues (CA-13).
  v_nivel := case when v_por = 'estudio' then null else v_vista.nivel end;
  update public.reserva
  set estado = 'cancelada', motivo_cancelacion = case when v_por = 'estudio' then 'administrador' else 'cliente' end,
      nota_cancelacion = v_nota, nivel_cancelacion = v_nivel, aviso_en = v_aviso, cancelacion_por = v_por,
      id_cancelador = v_uid, pagado_cancelacion = v_vista.pagado,
      retenido = case when v_por = 'estudio' then 0 else v_vista.retenido end,
      credito_generado = case when v_por = 'estudio' then 0 else v_vista.credito end,
      eleccion_estudio = case when v_por = 'estudio' and v_tiene then 'pendiente' end
  where id = r.id;
  if v_tiene then
    update public.cuota q set estado = 'anulada'
    where q.id_reserva = r.id and q.estado = 'pendiente'
      and not exists (select 1 from public.comprobante_pago p where p.id_cuota = q.id and p.estado = 'pendiente_validacion');
  end if;
  v_dias := (r.parametros_aplicados ->> 'dias_vigencia_credito')::int;
  if v_por = 'cliente' and v_vista.credito > 0 then
    perform public.generar_credito(r.id_cliente, r.id, 'nivel_' || v_nivel, v_vista.credito, v_dias);
  end if;
  if v_directo then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_cliente', au.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'cliente', cl.nombre,
                              'inicio', r.inicio, 'fin', r.fin)
    from public.usuario a
    join auth.users au on au.id = a.id
    left join public.usuario cl on cl.id = r.id_cliente
    where a.rol = 'administrador';
  elsif v_por = 'estudio' then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_estudio', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'nota', v_nota)
    from auth.users u where u.id = r.id_cliente;
  end if;
  if v_por = 'cliente' and v_tiene then
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_cancelada_con_pagos', u.email,
           jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin,
                              'nivel', v_nivel, 'pagado', v_vista.pagado, 'retenido', v_vista.retenido,
                              'credito', v_vista.credito, 'credito_vence', v_vista.credito_vence)
    from auth.users u where u.id = r.id_cliente;
  end if;
end;
$$;
revoke all on function public.cancelar_reserva(uuid, text, integer, text, timestamptz) from public, anon;
grant execute on function public.cancelar_reserva(uuid, text, integer, text, timestamptz) to authenticated;

-- 6. Inasistencia (CA-11).
create function public.aplicar_inasistencia(p_id uuid, p_id_autor uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_pagado numeric;
begin
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found or r.estado not in ('pre_reservada', 'confirmada', 'en_curso') then
    return;
  end if;
  v_pagado := coalesce((select sum(pagado) from public.cuota where id_reserva = r.id), 0);
  update public.reserva
  set estado = 'no_asistio', aviso_en = now(), cancelacion_por = 'inasistencia', nivel_cancelacion = null,
      id_cancelador = p_id_autor, pagado_cancelacion = v_pagado, retenido = v_pagado, credito_generado = 0
  where id = r.id;
  update public.cuota q set estado = 'anulada'
  where q.id_reserva = r.id and q.estado = 'pendiente'
    and not exists (select 1 from public.comprobante_pago p where p.id_cuota = q.id and p.estado = 'pendiente_validacion');
  insert into public.notificacion (tipo, destinatario, datos)
  select 'inasistencia_marcada', u.email,
         jsonb_build_object('id_reserva', r.id, 'folio', r.folio, 'inicio', r.inicio, 'fin', r.fin, 'retenido', v_pagado)
  from auth.users u where u.id = r.id_cliente;
end;
$$;
revoke all on function public.aplicar_inasistencia(uuid, uuid) from public, anon, authenticated;

create function public.marcar_inasistencia(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
begin
  if v_uid is null or not public.es_personal() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.estado not in ('pre_reservada', 'confirmada', 'en_curso') then
    raise exception 'no_aplicable' using errcode = 'P0001';
  end if;
  case public.ventana_inasistencia(r.inicio, r.fin, (r.parametros_aplicados ->> 'minutos_tolerancia_inasistencia')::int, now())
    when 'antes' then raise exception 'tolerancia_no_cumplida' using errcode = 'P0001';
    when 'despues' then raise exception 'no_aplicable' using errcode = 'P0001';
    else null;
  end case;
  perform public.aplicar_inasistencia(r.id, v_uid);
end;
$$;
revoke all on function public.marcar_inasistencia(uuid) from public, anon;
grant execute on function public.marcar_inasistencia(uuid) to authenticated;

-- RN-23 + ADR-015: una pre_reservada con pagos que llega a su fin sin confirmarse pasa sola a `no_asistio`;
-- lo demas igual (confirmada -> en_curso -> finalizada). Las cuotas se bloquean antes que las reservas.
create or replace function public.avanzar_reservas()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_avanzadas integer;
  v_sin_asistir integer := 0;
  v_id uuid;
begin
  for v_id in
    select r.id from public.reserva r
    where r.estado = 'pre_reservada' and r.fin <= now() and public.tiene_pagos(r.id) order by r.id
  loop
    perform public.aplicar_inasistencia(v_id, null);
    v_sin_asistir := v_sin_asistir + 1;
  end loop;
  perform 1 from public.reserva r
  where (r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now())
  order by r.id
  for update;
  with avanzadas as (
    update public.reserva r
    set estado = case when r.fin <= now() then 'finalizada' else 'en_curso' end
    where (r.estado = 'confirmada' and r.inicio <= now()) or (r.estado = 'en_curso' and r.fin <= now())
    returning r.id, r.id_cliente, r.folio, r.estado, r.inicio, r.fin
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_finalizada_saldo', u.email,
           jsonb_build_object('id_reserva', a.id, 'folio', a.folio, 'inicio', a.inicio, 'fin', a.fin, 'saldo', c.monto)
    from avanzadas a
    join public.cuota c on c.id_reserva = a.id and c.hito = 'al_terminar' and c.estado = 'pendiente'
    join auth.users u on u.id = a.id_cliente
    where a.estado = 'finalizada'
      and not exists (select 1 from public.comprobante_pago p
                      where p.id_cuota = c.id and p.estado = 'pendiente_validacion')
    returning 1
  )
  select count(*)::int into v_avanzadas from avanzadas;
  return v_avanzadas + v_sin_asistir;
end;
$$;

-- 7. Caso excepcional (CA-12): lo retenido pasa a un credito `excepcion` que vence a los dias de vigencia de la decision.
create function public.aplicar_excepcion(p_id uuid, p_motivo text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 10 and 500 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  perform 1 from public.cuota where id_reserva = p_id order by id for update;
  select * into r from public.reserva where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if r.excepcion_en is not null then
    raise exception 'excepcion_ya_aplicada' using errcode = 'P0001';
  end if;
  if not ((r.estado = 'cancelada' and r.cancelacion_por = 'cliente' and r.nivel_cancelacion in (2, 3))
          or r.estado = 'no_asistio') or coalesce(r.retenido, 0) <= 0 then
    raise exception 'excepcion_no_aplicable' using errcode = 'P0001';
  end if;
  perform public.generar_credito(r.id_cliente, r.id, 'excepcion', r.retenido,
    (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  update public.reserva
  set credito_generado = coalesce(credito_generado, 0) + retenido, retenido = 0, excepcion_motivo = v_motivo,
      excepcion_por = v_uid, excepcion_en = now()
  where id = r.id;
end;
$$;
revoke all on function public.aplicar_excepcion(uuid, text) from public, anon;
grant execute on function public.aplicar_excepcion(uuid, text) to authenticated;

-- 8. Pagos: lo aplicado por cuota, el monto restante tras un credito parcial y el pago aprobado despues de cancelar.
create function public.aplicar_pago_tardio(p_id_reserva uuid, p_monto numeric)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  r public.reserva%rowtype;
  v_nivel smallint;
  v_pagado numeric;
  v_ret numeric;
  v_delta_ret numeric;
begin
  select * into r from public.reserva where id = p_id_reserva;
  v_pagado := coalesce(r.pagado_cancelacion, 0) + p_monto;
  v_nivel := case when r.excepcion_en is not null then 1 when r.cancelacion_por = 'inasistencia' then 3
                  when r.cancelacion_por = 'estudio' then null else r.nivel_cancelacion end;
  if v_nivel is null then
    update public.reserva set pagado_cancelacion = v_pagado where id = r.id;
    return;
  end if;
  v_ret := case v_nivel when 1 then coalesce(r.retenido, 0)
                        when 2 then least(v_pagado, public.penalizacion_nivel_2(r.total, r.parametros_aplicados))
                        else coalesce(r.retenido, 0) + p_monto end;
  v_delta_ret := v_ret - coalesce(r.retenido, 0);
  update public.reserva
  set pagado_cancelacion = v_pagado, retenido = v_ret, credito_generado = coalesce(credito_generado, 0) + (p_monto - v_delta_ret)
  where id = r.id;
  if p_monto - v_delta_ret > 0 then
    perform public.generar_credito(r.id_cliente, r.id, case when r.excepcion_en is not null then 'excepcion' else 'nivel_' || v_nivel end,
      p_monto - v_delta_ret, (r.parametros_aplicados ->> 'dias_vigencia_credito')::int);
  end if;
end;
$$;
revoke all on function public.aplicar_pago_tardio(uuid, numeric) from public, anon, authenticated;

create or replace function public.validar_pago_nuevo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  c public.cuota%rowtype;
  r public.reserva%rowtype;
begin
  select * into c from public.cuota where id = new.id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente is distinct from (select auth.uid()) or new.id_cliente <> r.id_cliente then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'pago_en_validacion' using errcode = 'P0001';
  end if;
  if c.estado = 'anulada' or r.estado in ('cancelada', 'no_asistio') or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada')) then
    raise exception 'cuota_no_pagable' using errcode = 'P0001';
  end if;
  if c.pagado > 0 and new.monto <> c.monto - c.pagado then
    raise exception 'monto_invalido' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.instruccion_pago where metodo = new.metodo and activo) then
    raise exception 'metodo_no_disponible' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.comprobante_pago
             where metodo = new.metodo and estado <> 'rechazado'
               and lower(btrim(numero_operacion)) = lower(btrim(new.numero_operacion))) then
    raise exception 'operacion_duplicada' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

create or replace function public.aprobar_pago(p_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  p public.comprobante_pago%rowtype;
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_confirma boolean := false;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into p from public.comprobante_pago where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p.estado <> 'pendiente_validacion' then
    raise exception 'pago_ya_validado' using errcode = 'P0001';
  end if;
  update public.comprobante_pago set estado = 'aprobado', validado_en = now(), id_validador = v_uid where id = p_id;
  update public.cuota set estado = 'pagada', pagado = pagado + p.monto where id = p.id_cuota returning * into c;
  select * into r from public.reserva where id = c.id_reserva for update;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' then
    update public.reserva set estado = 'confirmada' where id = r.id;
    v_confirma := true;
  end if;
  if r.estado in ('cancelada', 'no_asistio') and r.aviso_en is not null then
    perform public.aplicar_pago_tardio(r.id, p.monto); -- sigue el nivel con que se cancelo (ADR-015)
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_aprobado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'reserva_confirmada', v_confirma)
  from auth.users u where u.id = p.id_cliente;
end;
$$;

create or replace function public.rechazar_pago(p_id uuid, p_motivo text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  p public.comprobante_pago%rowtype;
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 1 and 300 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  select * into p from public.comprobante_pago where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if p.estado <> 'pendiente_validacion' then
    raise exception 'pago_ya_validado' using errcode = 'P0001';
  end if;
  update public.comprobante_pago
  set estado = 'rechazado', motivo_rechazo = v_motivo, validado_en = now(), id_validador = v_uid
  where id = p_id;
  select * into c from public.cuota where id = p.id_cuota;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.estado = 'pre_reservada' and not public.tiene_pagos(r.id) then
    update public.reserva
    set vence_pago = greatest(coalesce(vence_pago, now()),
      least(inicio, now() + make_interval(hours => (r.parametros_aplicados ->> 'horas_limite_pago')::int)))
    where id = r.id;
  end if;
  if r.estado in ('cancelada', 'no_asistio') then
    update public.cuota set estado = 'anulada' where id = c.id and estado = 'pendiente'; -- ya no se puede pagar
  end if;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'pago_rechazado', u.email,
         jsonb_build_object('id_pago', p.id, 'id_reserva', r.id, 'folio', r.folio, 'hito', c.hito,
                            'monto', p.monto, 'motivo', v_motivo)
  from auth.users u where u.id = p.id_cliente;
end;
$$;

-- 9. Usar credito al pagar (CA-06): al momento, sin validacion; el que vence antes se usa primero. Las filas de credito
-- se bloquean en orden de vencimiento: dos pagos simultaneos no dejan saldo negativo ni usan dos veces lo mismo.
create function public.aplicar_credito(p_id_cuota uuid, p_monto numeric, p_id_credito uuid default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  c public.cuota%rowtype;
  r public.reserva%rowtype;
  k record;
  v_resto numeric;
  v_toma numeric;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  select * into c from public.cuota where id = p_id_cuota for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  select * into r from public.reserva where id = c.id_reserva for update;
  if r.id_cliente <> v_uid then
    if public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if c.estado = 'pagada' then
    raise exception 'cuota_pagada' using errcode = 'P0001';
  end if;
  if c.estado = 'anulada' or r.estado in ('cancelada', 'no_asistio') or (r.estado = 'pre_reservada' and r.vence_pago <= now())
     or (c.hito = 'al_terminar' and r.estado not in ('confirmada', 'en_curso', 'finalizada'))
     or exists (select 1 from public.comprobante_pago where id_cuota = c.id and estado = 'pendiente_validacion') then
    raise exception 'no_pagable' using errcode = 'P0001';
  end if;
  if p_monto is null or p_monto <= 0 or p_monto <> round(p_monto, 2) or p_monto > c.monto - c.pagado then
    raise exception 'monto_invalido' using errcode = '22023';
  end if;
  if p_id_credito is not null
     and not exists (select 1 from public.credito where id = p_id_credito and id_cliente = v_uid) then
    raise exception 'credito_no_encontrado' using errcode = 'P0002';
  end if;
  v_resto := p_monto;
  for k in
    select * from public.credito cr
    where cr.id_cliente = v_uid and cr.estado = 'vigente' and cr.saldo > 0 and cr.vence > now() and not cr.congelado
      and (p_id_credito is null or cr.id = p_id_credito)
    order by cr.vence, cr.id
    for update
  loop
    v_toma := least(k.saldo, v_resto);
    update public.credito
    set saldo = saldo - v_toma, estado = case when saldo - v_toma = 0 then 'agotado' else estado end
    where id = k.id;
    insert into public.aplicacion_credito (id_credito, id_cuota, monto, id_usuario) values (k.id, c.id, v_toma, v_uid);
    v_resto := v_resto - v_toma;
    exit when v_resto = 0;
  end loop;
  if v_resto > 0 then
    raise exception 'credito_insuficiente' using errcode = 'P0001';
  end if;
  update public.cuota
  set pagado = pagado + p_monto, estado = case when pagado + p_monto >= monto then 'pagada' else estado end
  where id = c.id;
  if c.hito = 'al_reservar' and r.estado = 'pre_reservada' and c.pagado + p_monto >= c.monto then
    update public.reserva set estado = 'confirmada' where id = r.id;
  end if;
end;
$$;
revoke all on function public.aplicar_credito(uuid, numeric, uuid) from public, anon;
grant execute on function public.aplicar_credito(uuid, numeric, uuid) to authenticated;

-- 10. Devoluciones (CA-07).
create function public.solicitar_devolucion(p_id_credito uuid, p_motivo text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_motivo text := btrim(p_motivo);
  k public.credito%rowtype;
  v_id uuid;
begin
  if v_uid is null then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_motivo is null or char_length(v_motivo) not between 10 and 500 then
    raise exception 'motivo_invalido' using errcode = '22023';
  end if;
  select * into k from public.credito where id = p_id_credito for update;
  if not found or k.id_cliente <> v_uid then
    if found and public.es_personal() then
      raise exception 'sin_permiso' using errcode = '42501';
    end if;
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if k.tipo in ('nivel_2', 'reprogramacion') then
    raise exception 'devolucion_no_permitida' using errcode = 'P0001';
  end if;
  if k.congelado then
    raise exception 'devolucion_pendiente' using errcode = 'P0001';
  end if;
  if k.estado <> 'vigente' or k.vence <= now() or k.saldo <= 0 then
    raise exception 'credito_no_vigente' using errcode = 'P0001';
  end if;
  insert into public.devolucion (id_credito, id_reserva, id_cliente, tipo, motivo, monto_solicitado)
  values (k.id, k.id_reserva, v_uid, 'nivel_1', v_motivo, k.saldo)
  returning id into v_id;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'devolucion_solicitada', au.email,
         jsonb_build_object('id_devolucion', v_id, 'id_credito', k.id, 'cliente', cl.nombre, 'saldo', k.saldo,
                            'motivo', v_motivo, 'folio_origen', (select folio from public.reserva where id = k.id_reserva))
  from public.usuario a
  join auth.users au on au.id = a.id
  left join public.usuario cl on cl.id = v_uid
  where a.rol = 'administrador';
  return v_id;
end;
$$;
revoke all on function public.solicitar_devolucion(uuid, text) from public, anon;
grant execute on function public.solicitar_devolucion(uuid, text) to authenticated;

create function public.decidir_devolucion(p_id uuid, p_decision text, p_monto numeric default null, p_motivo text default null)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_motivo text := nullif(btrim(p_motivo), '');
  d public.devolucion%rowtype;
  k public.credito%rowtype;
  v_monto numeric;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if p_decision is null or p_decision not in ('total', 'parcial', 'rechazo') then
    raise exception 'decision_invalida' using errcode = '22023';
  end if;
  select * into d from public.devolucion where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if d.estado <> 'pendiente' then
    raise exception 'devolucion_decidida' using errcode = 'P0001';
  end if;
  select * into k from public.credito where id = d.id_credito for update;
  if p_decision = 'parcial' and (p_monto is null or p_monto < 0.01 or p_monto > k.saldo or p_monto <> round(p_monto, 2)) then
    raise exception 'monto_invalido' using errcode = '22023';
  end if;
  if (p_decision <> 'total' and (v_motivo is null or char_length(v_motivo) not between 10 and 500))
     or char_length(v_motivo) > 500 then
    raise exception 'motivo_requerido' using errcode = '22023';
  end if;
  v_monto := case p_decision when 'total' then k.saldo when 'parcial' then p_monto end;
  update public.devolucion
  set estado = case when p_decision = 'rechazo' then 'rechazada' else 'aprobada' end, monto_aprobado = v_monto,
      motivo_decision = v_motivo, decidida_en = now(), id_decisor = v_uid
  where id = d.id;
  update public.credito
  set saldo = saldo - coalesce(v_monto, 0), congelado = false,
      estado = case when saldo - coalesce(v_monto, 0) = 0 then 'agotado' else estado end,
      vence = case when vence <= now() then public.fin_de_dia_lima(now(), 7) else vence end
  where id = k.id;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'devolucion_decidida', u.email,
         jsonb_build_object('id_devolucion', d.id, 'decision', p_decision, 'monto_aprobado', v_monto, 'motivo', v_motivo,
                            'folio_origen', (select folio from public.reserva where id = d.id_reserva))
  from auth.users u where u.id = d.id_cliente;
end;
$$;
revoke all on function public.decidir_devolucion(uuid, text, numeric, text) from public, anon;
grant execute on function public.decidir_devolucion(uuid, text, numeric, text) to authenticated;

create function public.marcar_devolucion_realizada(p_id uuid, p_nota text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_nota text := btrim(p_nota);
  d public.devolucion%rowtype;
begin
  if v_uid is null or not public.es_administrador() then
    raise exception 'sin_permiso' using errcode = '42501';
  end if;
  if v_nota is null or char_length(v_nota) not between 1 and 500 then
    raise exception 'nota_invalida' using errcode = '22023';
  end if;
  select * into d from public.devolucion where id = p_id for update;
  if not found then
    raise exception 'no_encontrada' using errcode = 'P0002';
  end if;
  if d.estado <> 'aprobada' then
    raise exception 'devolucion_no_aprobada' using errcode = 'P0001';
  end if;
  update public.devolucion set estado = 'realizada', nota_realizada = v_nota, realizada_en = now(), id_realizador = v_uid
  where id = d.id;
  insert into public.notificacion (tipo, destinatario, datos)
  select 'devolucion_realizada', u.email,
         jsonb_build_object('id_devolucion', d.id, 'monto_aprobado', d.monto_aprobado, 'nota', v_nota,
                            'folio_origen', (select folio from public.reserva where id = d.id_reserva))
  from auth.users u where u.id = d.id_cliente;
end;
$$;
revoke all on function public.marcar_devolucion_realizada(uuid, text) from public, anon;
grant execute on function public.marcar_devolucion_realizada(uuid, text) to authenticated;

-- 11. Cron diario (00:05 de Lima = 05:05 UTC): aviso 7 dias antes de vencer (una sola vez) y vencimiento.
-- Un credito congelado por una devolucion pendiente no avisa ni vence. Devuelve cuantos cambios hizo.
create function public.procesar_creditos()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_vencidos integer;
  v_avisos integer;
begin
  update public.credito set estado = 'vencido'
  where estado = 'vigente' and not congelado and vence <= now();
  get diagnostics v_vencidos = row_count;
  with por_vencer as (
    update public.credito set aviso_enviado_en = now()
    where estado = 'vigente' and not congelado and saldo > 0 and aviso_enviado_en is null
      and vence > now() and vence <= now() + interval '7 days'
    returning id, id_cliente, id_reserva, saldo, vence
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'credito_por_vencer', u.email,
           jsonb_build_object('id_credito', k.id, 'saldo', k.saldo, 'vence', k.vence,
                              'folio_origen', (select folio from public.reserva where id = k.id_reserva))
    from por_vencer k join auth.users u on u.id = k.id_cliente
    returning 1
  )
  select count(*)::int into v_avisos from por_vencer;
  return v_vencidos + v_avisos;
end;
$$;
revoke all on function public.procesar_creditos() from public, anon, authenticated;
select cron.schedule('procesar_creditos', '5 5 * * *', 'select public.procesar_creditos()');
