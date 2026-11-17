-- RF-17, auditoria A ronda 2: `documento_repetido` se calcula al leer, sin trigger que actualice filas ajenas
-- (dos cuentas que intercambiaban documentos a la vez se interbloqueaban). El indice
-- `usuario_documento_idx (documento_tipo, documento_numero)` sirve la consulta `exists`.
drop trigger usuario_documento_repetido on public.usuario;
drop function public.recalcular_documento_repetido();
alter table public.usuario drop column documento_repetido;
