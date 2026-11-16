-- Solo desarrollo local (`db reset` lo aplica). Contrasena de bugalu_api para backend/.env.
alter role bugalu_api with password 'bugalu_api_dev';

-- Datos para pagar de ejemplo (RN-22); en produccion los edita el administrador.
update public.instruccion_pago set activo = true, texto = case metodo
  when 'transferencia' then 'Banco de ejemplo - Cuenta 000-0000000-0-00 - CCI 000-000-000000000000-00 - Titular: Bugalu Studio'
  when 'yape' then 'Yape al 999 999 999 - Bugalu Studio'
  when 'plin' then 'Plin al 999 999 999 - Bugalu Studio'
  else 'Tarjeta: paga en el POS del estudio e indica el numero del voucher' end;

-- Contacto del estudio de ejemplo (RF-05); en produccion lo edita el administrador.
update public.contacto_estudio set texto = 'Escribenos por WhatsApp al 999 999 999 o a hola@bugalu.pe';
