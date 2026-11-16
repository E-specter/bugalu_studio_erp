-- RF-05 (3a): formato del numero de operacion y contacto del estudio.

-- 4 a 40 letras, cifras o guiones (la API lo guarda en mayusculas).
alter table public.comprobante_pago
  add constraint comprobante_pago_numero_operacion_formato check (numero_operacion ~ '^[A-Za-z0-9-]{4,40}$');

-- Contacto del estudio: una sola fila; leen los autenticados, actualiza solo el administrador.
create table public.contacto_estudio (
  id boolean primary key default true check (id),
  texto text not null default '' check (char_length(texto) <= 500)
);
insert into public.contacto_estudio (id) values (true);
alter table public.contacto_estudio enable row level security;
revoke all on public.contacto_estudio from anon, authenticated;
grant select on public.contacto_estudio to authenticated;
grant update (texto) on public.contacto_estudio to authenticated;
create policy contacto_estudio_lee on public.contacto_estudio for select to authenticated using (true);
create policy contacto_estudio_admin_actualiza on public.contacto_estudio for update to authenticated
  using (public.es_administrador()) with check (public.es_administrador());

-- Distingue 403 de 404: la RLS oculta los pagos ajenos, pero el backend debe saber si existen (no devuelve datos).
create function public.existe_pago(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.comprobante_pago where id = p_id);
$$;
revoke all on function public.existe_pago(uuid) from public, anon;
grant execute on function public.existe_pago(uuid) to authenticated;
