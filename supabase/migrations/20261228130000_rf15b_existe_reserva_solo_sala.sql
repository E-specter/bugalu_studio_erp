-- GET /reservas/{id} sigue siendo solo de sala: el id de una asesoria ajena no se delata con un 403.
create or replace function public.existe_reserva(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.reserva where id = p_id and tipo = 'sala');
$$;
