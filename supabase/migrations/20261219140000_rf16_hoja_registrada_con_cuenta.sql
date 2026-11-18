-- RF-16 (precision 12): el reintento con la misma clave devuelve tambien la cuenta de la hoja, para calcular `en_tu_cuenta`.
create or replace function public.hoja_registrada_json(p_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object(
    'id', h.id, 'numero', h.numero, 'creada_en', h.creada_en, 'vence_respuesta', h.vence_respuesta,
    'dias', public.dias_habiles_restantes(h.vence_respuesta), 'id_cuenta', h.id_cuenta,
    'nombre', h.nombre, 'tipo_documento', h.tipo_documento, 'documento', h.documento, 'domicilio', h.domicilio,
    'telefono', h.telefono, 'correo', h.correo, 'es_menor', h.es_menor,
    'rep_nombre', h.rep_nombre, 'rep_domicilio', h.rep_domicilio, 'rep_telefono', h.rep_telefono, 'rep_correo', h.rep_correo,
    'bien_tipo', h.bien_tipo, 'monto', h.monto, 'descripcion', h.descripcion, 'tipo', h.tipo,
    'detalle', h.detalle, 'pedido', h.pedido, 'medio_respuesta', h.medio_respuesta,
    'adjuntos', coalesce((select jsonb_agg(jsonb_build_object('n', a.n, 'nombre', a.nombre, 'tipo', a.tipo,
                 'tamano', a.tamano, 'ruta', a.ruta) order by a.n)
               from public.adjunto_reclamacion a where a.id_hoja = h.id), '[]'))
  from public.hoja_reclamacion h where h.id = p_id;
$$;
