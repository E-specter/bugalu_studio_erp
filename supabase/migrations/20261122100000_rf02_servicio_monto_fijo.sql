-- RF-02 / ADR-009: parte fija del servicio, cobrada una vez por reserva (0 si no tiene).
-- Los privilegios y las politicas de servicio (grant update a nivel de tabla) ya cubren la columna nueva.
alter table public.servicio
  add column monto_fijo numeric(10, 2) not null default 0 check (monto_fijo >= 0);
