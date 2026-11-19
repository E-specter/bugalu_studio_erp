-- La funcion recreada en 20261228100000 recibio los privilegios por defecto de Supabase: solo `bugalu_api` la ejecuta.
revoke all on function public.datos_reserva_para_correo(uuid[]) from service_role;
