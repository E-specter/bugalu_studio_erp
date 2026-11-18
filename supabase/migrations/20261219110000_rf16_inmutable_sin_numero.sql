-- RF-16: `numero` es una columna generada y aun no esta calculada en un BEFORE UPDATE: la comparacion de la
-- inmutabilidad la excluye. (Ya incluido en la migracion anterior para un esquema nuevo; esto actualiza el ya aplicado.)
create or replace function public.hoja_reclamacion_inmutable()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  -- `numero` es generada: en un BEFORE UPDATE aun no esta calculada, por eso se excluye de la comparacion.
  if tg_op = 'UPDATE' then
    if old.respuesta_texto is null and new.respuesta_texto is not null
       and to_jsonb(new) - array['numero', 'respuesta_texto', 'respuesta_referencia_carta', 'respuesta_enviada_en', 'respondida_en', 'respondida_por']
         = to_jsonb(old) - array['numero', 'respuesta_texto', 'respuesta_referencia_carta', 'respuesta_enviada_en', 'respondida_en', 'respondida_por'] then
      return new;
    end if;
    if new.id_cuenta is not distinct from old.id_cuenta or new.id_cuenta is null then
      if (new.respondida_por is null or new.respondida_por is not distinct from old.respondida_por)
         and to_jsonb(new) - array['numero', 'id_cuenta', 'respondida_por'] = to_jsonb(old) - array['numero', 'id_cuenta', 'respondida_por'] then
        return new;
      end if;
    end if;
  end if;
  raise exception 'hoja_inmutable';
end;
$$;
