// Formatos compartidos (sin navegador): título de semana (N9) y partidas de precio (B3).
import { test, expect } from '@playwright/test';
import { esFecha, rangoSemana, duracionReserva, partidasPrecio, soles } from '../src/servicios/formatos.js';

test('rangoSemana: dentro de un mes, entre meses y entre años', () => {
  expect(rangoSemana('2026-11-16')).toBe('SEMANA DEL 16 AL 22 NOV 2026');
  expect(rangoSemana('2026-11-30')).toBe('SEMANA DEL 30 NOV AL 6 DIC 2026');
  expect(rangoSemana('2026-12-28')).toBe('SEMANA DEL 28 DIC 2026 AL 3 ENE 2027');
});

test('duracionReserva: horas y minutos, sin decimales', () => {
  expect([30, 60, 90, 150, 480].map(duracionReserva)).toEqual(['30 min', '1 h', '1 h 30 min', '2 h 30 min', '8 h']);
});

test('partidasPrecio: un solo formato para reservar y mis reservas', () => {
  const { filas, pie } = partidasPrecio({
    lineas: [{ concepto: 'Grabación', cantidad: '2.0', unidad: 'hora', monto: '240.00' }, { concepto: 'Productor', cantidad: '5', unidad: 'lapso_30', monto: '75.00' }, { concepto: 'Fijo', cantidad: '1', unidad: 'fijo', monto: '30.00' }],
    recargos: [{ tipo: 'noche', bloques: 2, monto: '20.00' }],
    total: '365.00',
    anticipo: '182.50',
  });
  expect(filas).toEqual([
    ['Grabación', '2 h', 'S/ 240,00'],
    ['Productor', '5 × 30 min', 'S/ 75,00'],
    ['Fijo', '1', 'S/ 30,00'],
    ['Recargo de noche', '2 × 30 min', 'S/ 20,00'],
  ]);
  expect(pie).toEqual([['Total', 'S/ 365,00'], ['Anticipo 50 %', 'S/ 182,50']]);
});

test('soles: miles con espacio no separable y coma decimal; el campo no agrupa', () => {
  expect(soles('1250.00')).toBe('S/ 1 250,00');
  expect(soles('1234567.5')).toBe('S/ 1 234 567,50');
  expect(soles('120.00')).toBe('S/ 120,00');
});

test('esFecha: solo días reales', () => {
  expect(['2026-11-16', '2028-02-29'].map(esFecha)).toEqual([true, true]);
  expect(['2026-13-01', '2026-99-99', '2026-11-99', '2026-02-30', 'basura', null].map(esFecha)).toEqual([false, false, false, false, false, false]);
});
