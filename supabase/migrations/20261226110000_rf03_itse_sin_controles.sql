-- RF-03 (auditoria): el certificado ITSE no admite caracteres de control (tabulador, \x00-\x1f, \x7f-\x9f), no solo saltos de linea.
alter table public.sala_tecnica drop constraint sala_tecnica_itse_certificado_check;
alter table public.sala_tecnica add constraint sala_tecnica_itse_certificado_check
  check (char_length(itse_certificado) between 1 and 40 and itse_certificado !~ '[[:cntrl:]]');
