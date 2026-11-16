-- RF-03 / RF-04: franjas, cierres, reservas, cuotas minimas, caducidad y bandeja de correos (ADR-009).
create extension if not exists btree_gist with schema extensions;
create extension if not exists pg_cron with schema pg_catalog;

-- Personal o administrador: leen todas las reservas.
create function public.es_personal()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.usuario
    where id = (select auth.uid()) and rol in ('personal', 'administrador')
  );
$$;
revoke all on function public.es_personal() from public, anon;
grant execute on function public.es_personal() to authenticated;

-- Franjas publicadas y cierres (RN-12). Instantes en multiplos de 30 min.
create table public.franja_sala (
  id uuid primary key default gen_random_uuid(),
  id_sala uuid not null references public.sala_tecnica (id),
  inicio timestamptz not null,
  fin timestamptz not null,
  id_publicador uuid references public.usuario (id) on delete set null,
  check (fin > inicio),
  check (mod(extract(epoch from inicio), 1800) = 0 and mod(extract(epoch from fin), 1800) = 0),
  exclude using gist (id_sala with =, tstzrange(inicio, fin) with &&)
);

create table public.cierre_sala (
  id uuid primary key default gen_random_uuid(),
  id_sala uuid not null references public.sala_tecnica (id),
  inicio timestamptz not null,
  fin timestamptz not null,
  motivo text not null,
  id_autor uuid references public.usuario (id) on delete set null,
  check (fin > inicio)
);

-- Reservas de sala (RN-01, RN-02, RN-12, RN-13).
create sequence public.reserva_folio_seq;

create table public.reserva (
  id uuid primary key default gen_random_uuid(),
  folio text not null unique
    default 'R-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('public.reserva_folio_seq')::text, 5, '0'),
  id_cliente uuid not null references public.usuario (id),
  id_sala uuid not null references public.sala_tecnica (id),
  id_servicio uuid not null references public.servicio (id),
  id_franja uuid references public.franja_sala (id),
  inicio timestamptz not null,
  fin timestamptz not null,
  fin_buffer timestamptz not null, -- lo fija el trigger: fin + 30 min
  estado text not null default 'pre_reservada'
    check (estado in ('pre_reservada', 'confirmada', 'en_curso', 'finalizada', 'cancelada')),
  motivo_cancelacion text check (motivo_cancelacion in ('cliente', 'caducada', 'administrador')),
  precio jsonb not null default '{}',
  total numeric(10, 2) not null check (total >= 0),
  vence_pago timestamptz,
  detalle text,
  check ((estado = 'cancelada') = (motivo_cancelacion is not null)),
  check (mod(extract(epoch from inicio), 1800) = 0 and mod(extract(epoch from fin), 1800) = 0),
  check (fin - inicio between interval '30 minutes' and interval '8 hours'),
  exclude using gist (id_sala with =, tstzrange(inicio, fin_buffer) with &&) where (estado <> 'cancelada')
);

create table public.reserva_especialista (
  id_reserva uuid not null references public.reserva (id) on delete cascade,
  id_especialista uuid not null references public.especialista (id),
  monto_fijo numeric(10, 2) not null check (monto_fijo >= 0),
  monto_variable numeric(10, 2) not null check (monto_variable >= 0),
  unidad text not null check (unidad in ('hora', 'lapso_30')),
  primary key (id_reserva, id_especialista)
);

-- Cuota minima para RF-04 (RN-13). Pendiente: id_asesoria, id_cotizacion, id_proyecto y vence (modelo-datos).
create table public.cuota (
  id uuid primary key default gen_random_uuid(),
  id_reserva uuid not null references public.reserva (id) on delete cascade,
  hito text not null check (hito in ('al_reservar', 'al_terminar', 'al_encargar', 'al_aprobar_version')),
  monto numeric(10, 2) not null check (monto >= 0),
  estado text not null default 'pendiente' check (estado in ('pendiente', 'pagada'))
);

-- Bandeja de salida de correos (ADR-009): la lee y marca el backend con su rol.
create table public.notificacion (
  id uuid primary key default gen_random_uuid(),
  tipo text not null check (tipo in ('reserva_creada', 'reserva_caducada')),
  destinatario text not null,
  datos jsonb not null default '{}',
  creada_en timestamptz not null default now(),
  enviada_en timestamptz,
  intentos integer not null default 0,
  error text
);
create index notificacion_pendiente_idx on public.notificacion (creada_en) where enviada_en is null;

-- Punto de extension: cuando exista comprobante_pago (RF-04), "tiene pagos" debe incluir los comprobantes
-- registrados (pendientes de validacion o aprobados), no solo las cuotas pagadas.
create function public.tiene_pagos(p_id_reserva uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (select 1 from public.cuota where id_reserva = p_id_reserva and estado = 'pagada');
$$;
revoke all on function public.tiene_pagos(uuid) from public, anon, authenticated;

-- RN-18: cancela por caducidad las pre_reservadas vencidas sin pagos y encola el aviso. Sin argumentos
-- revisa toda la tabla (pg_cron); con sala y rango solo los tramos que se solapan (trigger de insercion).
create function public.caducar_reservas(
  p_id_sala uuid default null, p_desde timestamptz default null, p_hasta timestamptz default null)
returns integer
language sql
security definer
set search_path = ''
as $$
  with caducadas as (
    update public.reserva r
    set estado = 'cancelada', motivo_cancelacion = 'caducada'
    where r.estado = 'pre_reservada' and r.vence_pago < now() and not public.tiene_pagos(r.id)
      and (p_id_sala is null
           or (r.id_sala = p_id_sala and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)))
    returning r.id, r.id_cliente, r.folio, r.inicio, r.fin
  ), avisos as (
    insert into public.notificacion (tipo, destinatario, datos)
    select 'reserva_caducada', u.email,
           jsonb_build_object('id_reserva', c.id, 'folio', c.folio, 'inicio', c.inicio, 'fin', c.fin)
    from caducadas c join auth.users u on u.id = c.id_cliente
    returning 1
  )
  select count(*)::int from caducadas;
$$;
revoke all on function public.caducar_reservas(uuid, timestamptz, timestamptz) from public, anon, authenticated;

select cron.schedule('caducar_reservas', '* * * * *', 'select public.caducar_reservas()');

-- Antes de insertar: fija el buffer (RN-02) y libera los tramos con una pre_reservada vencida sin marcar.
create function public.preparar_reserva()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.fin_buffer := new.fin + interval '30 minutes';
  if new.estado <> 'cancelada' then
    perform public.caducar_reservas(new.id_sala, new.inicio, new.fin_buffer);
  end if;
  return new;
end;
$$;
revoke all on function public.preparar_reserva() from public, anon, authenticated;
create trigger reserva_preparar before insert on public.reserva
  for each row execute function public.preparar_reserva();

-- Lectura publica de ocupacion (RN-19): solo inicio y fin con buffer; una pre_reservada vencida cuenta como libre.
create function public.ocupacion_sala(p_id_sala uuid, p_desde timestamptz, p_hasta timestamptz)
returns table (inicio timestamptz, fin_buffer timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select r.inicio, r.fin_buffer
  from public.reserva r
  where r.id_sala = p_id_sala
    and r.estado <> 'cancelada'
    and not (r.estado = 'pre_reservada' and coalesce(r.vence_pago < now(), false) and not public.tiene_pagos(r.id))
    and tstzrange(r.inicio, r.fin_buffer) && tstzrange(p_desde, p_hasta)
  order by r.inicio;
$$;
revoke all on function public.ocupacion_sala(uuid, timestamptz, timestamptz) from public;
grant execute on function public.ocupacion_sala(uuid, timestamptz, timestamptz) to anon, authenticated;

-- RLS y privilegios
alter table public.franja_sala enable row level security;
alter table public.cierre_sala enable row level security;
alter table public.reserva enable row level security;
alter table public.reserva_especialista enable row level security;
alter table public.cuota enable row level security;
alter table public.notificacion enable row level security;
revoke all on public.franja_sala, public.cierre_sala, public.reserva, public.reserva_especialista,
  public.cuota, public.notificacion from anon, authenticated;

-- Franjas y cierres: lectura publica, escritura del administrador.
do $$
declare
  t text;
begin
  foreach t in array array['franja_sala', 'cierre_sala'] loop
    execute format('grant select on public.%I to anon, authenticated', t);
    execute format('grant insert, update, delete on public.%I to authenticated', t);
    execute format('create policy %I on public.%I for select to anon, authenticated using (true)', t || '_lectura_publica', t);
    execute format('create policy %I on public.%I for insert to authenticated with check (public.es_administrador())', t || '_admin_inserta', t);
    execute format('create policy %I on public.%I for update to authenticated using (public.es_administrador()) with check (public.es_administrador())', t || '_admin_actualiza', t);
    execute format('create policy %I on public.%I for delete to authenticated using (public.es_administrador())', t || '_admin_borra', t);
  end loop;
end $$;

-- Reserva: el cliente lee e inserta las suyas (pre_reservada, sin motivo); folio y fin_buffer no se escriben;
-- el estado lo cambia el administrador (o funciones security definer).
grant select on public.reserva to authenticated;
grant insert (id_cliente, id_sala, id_servicio, id_franja, inicio, fin, estado, motivo_cancelacion,
  precio, total, vence_pago, detalle) on public.reserva to authenticated;
grant update (estado, motivo_cancelacion, vence_pago, detalle) on public.reserva to authenticated;
create policy reserva_lee on public.reserva for select to authenticated
  using (id_cliente = (select auth.uid()) or public.es_personal());
create policy reserva_cliente_inserta on public.reserva for insert to authenticated
  with check (id_cliente = (select auth.uid()) and estado = 'pre_reservada' and motivo_cancelacion is null);
create policy reserva_admin_actualiza on public.reserva for update to authenticated
  using (public.es_administrador()) with check (public.es_administrador());

-- reserva_especialista y cuota: visibles con la reserva; las inserta su dueño o el administrador.
grant select, insert on public.reserva_especialista, public.cuota to authenticated;
grant update (estado) on public.cuota to authenticated;
create policy reserva_especialista_lee on public.reserva_especialista for select to authenticated
  using (exists (select 1 from public.reserva r where r.id = id_reserva));
create policy reserva_especialista_inserta on public.reserva_especialista for insert to authenticated
  with check (exists (select 1 from public.reserva r where r.id = id_reserva
    and (r.id_cliente = (select auth.uid()) or public.es_administrador())));
create policy cuota_lee on public.cuota for select to authenticated
  using (exists (select 1 from public.reserva r where r.id = id_reserva));
create policy cuota_inserta on public.cuota for insert to authenticated
  with check (exists (select 1 from public.reserva r where r.id = id_reserva
    and (r.id_cliente = (select auth.uid()) or public.es_administrador())));
create policy cuota_admin_actualiza on public.cuota for update to authenticated
  using (public.es_administrador()) with check (public.es_administrador());

-- Notificacion: sin acceso para anon ni authenticated; solo el rol del backend.
grant select, insert, update on public.notificacion to bugalu_api;
create policy notificacion_backend on public.notificacion for all to bugalu_api using (true) with check (true);

-- El administrador quita especialistas por defecto de un servicio.
grant delete on public.servicio_especialista to authenticated;
create policy servicio_especialista_admin_borra on public.servicio_especialista
  for delete to authenticated using (public.es_administrador());
