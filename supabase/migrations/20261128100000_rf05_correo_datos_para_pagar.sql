-- RF-05: la bandeja de correos (rol `bugalu_api`, sin `set local role`) lee los datos para pagar
-- y los agrega al correo de reserva creada. Solo lectura.
grant select on public.instruccion_pago to bugalu_api;
create policy instruccion_pago_bandeja_lee on public.instruccion_pago for select to bugalu_api using (true);
