-- ADR-003: buckets privados; sin politicas, solo el rol de servicio accede.
insert into storage.buckets (id, name, public)
values ('entregables', 'entregables', false), ('comprobantes', 'comprobantes', false)
on conflict (id) do update set public = false;
