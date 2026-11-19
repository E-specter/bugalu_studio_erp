-- RF-15 CA-16 (correccion): el profesional ve el AVISO de la cancelacion y "a pedido de" (D4) y las fechas de las
-- reprogramaciones (D5), nunca dinero, nivel, nota ni devolucion. Parte de la ULTIMA definicion de `asesoria_vista`
-- (20261229100000): solo `aviso_en` y `cancelacion_por` dejan de anularse para el profesional.
create or replace view public.asesoria_vista as
select r.id, r.folio, r.estado, r.motivo_cancelacion, r.inicio, r.fin, r.vence_pago, r.id_cliente, r.id_profesional,
       r.creada_en, r.precio, r.parametros_aplicados, r.eleccion_estudio,
       a.modalidad, a.lugar, a.enlace, a.realizada_en,
       d.dinero as con_dinero,
       case when d.dinero then r.total end as total,
       case when d.dinero then r.detalle end as detalle,
       case when d.dinero then r.nota_cancelacion end as nota_cancelacion,
       case when d.dinero then r.nivel_cancelacion end as nivel_cancelacion,
       r.aviso_en,
       r.cancelacion_por,
       case when d.dinero then r.id_cancelador end as id_cancelador,
       case when d.dinero then r.pagado_cancelacion end as pagado_cancelacion,
       case when d.dinero then r.retenido end as retenido,
       case when d.dinero then r.credito_generado end as credito_generado,
       case when d.dinero then r.excepcion_motivo end as excepcion_motivo,
       case when d.dinero then r.excepcion_por end as excepcion_por,
       case when d.dinero then r.excepcion_en end as excepcion_en
from public.reserva r
join public.asesoria a on a.id_reserva = r.id
cross join lateral (select r.id_cliente = (select auth.uid()) or public.es_administrador() as dinero) d
where r.tipo = 'asesoria'
  and (d.dinero or r.id_profesional = (select auth.uid()));

-- Las reprogramaciones no se leen por SQL (CA-16): esta funcion da al profesional solo fechas, sin penalizacion,
-- totales ni nivel. Hereda la visibilidad de la vista (cliente, su profesional, administrador).
create function public.reprogramaciones_visibles(p_ids uuid[])
returns table (id_reserva uuid, anterior_inicio timestamptz, nuevo_inicio timestamptz, en timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select g.id_reserva, g.anterior_inicio, g.nuevo_inicio, g.en
  from public.reprogramacion g
  where g.id_reserva = any(p_ids) and exists (select 1 from public.asesoria_vista v where v.id = g.id_reserva)
  order by g.en, g.id;
$$;
revoke all on function public.reprogramaciones_visibles(uuid[]) from public, anon;
grant execute on function public.reprogramaciones_visibles(uuid[]) to authenticated;
