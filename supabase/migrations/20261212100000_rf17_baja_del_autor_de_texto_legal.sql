-- RF-17: la baja de la cuenta de un administrador (ADR-015) pone `id_autor` a nulo por el `on delete set null`;
-- el trigger de inmutabilidad lo admite solo si no cambia ninguna otra columna.
create or replace function public.texto_legal_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' and old.vigente_desde > now() then
    return old;
  end if;
  if tg_op = 'UPDATE' and new.id_autor is null and old.id_autor is not null
     and to_jsonb(new) - 'id_autor' = to_jsonb(old) - 'id_autor' then
    return new;
  end if;
  raise exception 'Una version publicada no se edita ni se borra.';
end;
$$;
