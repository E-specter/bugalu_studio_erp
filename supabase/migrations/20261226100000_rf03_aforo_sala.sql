-- RF-03 ampliacion (CA-10): aforo por sala y certificado ITSE que lo sustenta.
-- La escritura ya es solo del Administrador (politica y grant de update de sala_tecnica, RF-02/RF-03).
alter table public.sala_tecnica
  add column aforo integer check (aforo between 1 and 200),
  add column itse_certificado text check (itse_certificado ~ '^[^\r\n]{1,40}$'),
  add column itse_vence date,
  add constraint sala_tecnica_itse_completo check (
    (aforo is null and itse_certificado is null and itse_vence is null)
    or (aforo is not null and itse_certificado is not null and itse_vence is not null)
  );
