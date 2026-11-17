// Formatos compartidos (sin navegador): título de semana (N9) y partidas de precio (B3).
import { test, expect } from '@playwright/test';
import { inicioValido, duracionValida, esFecha, rangoSemana, duracionReserva, partidasPrecio, filasPrecio, porcentaje, soles } from '../src/servicios/formatos.js';

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

test('inicioValido: ISO con hora y zona y fecha real; si no, null', () => {
  expect(inicioValido('2026-11-19T15:00:00Z')).toBe('2026-11-19T15:00:00Z');
  expect(inicioValido('2026-11-19T10:00:00-05:00')).toBe('2026-11-19T10:00:00-05:00');
  for (const x of ['2026-11-31T15:00:00Z', '2026-02-30T10:00:00Z', '2026-11-19', '2026-11-19T10:00', 'basura', '', null]) expect(inicioValido(x)).toBeNull();
});

test('duracionValida: solo digitos, multiplo de 30, de 30 a 480; si no, 0', () => {
  expect(['30', '60', '480'].map(duracionValida)).toEqual([30, 60, 480]);
  for (const x of ['0x1e', '1e2', '+30', '30.0', '45', '0', '510', '', null]) expect(duracionValida(x)).toBe(0);
});

test('desglose de IGV: incluido y no incluido salen del backend; el adelanto usa su porcentaje', () => {
  const precio = { lineas: [], recargos: [], total: '150.00', anticipo: '45.00', porcentaje_adelanto: 30 };
  const incluido = { ...precio, impuesto: { nombre: 'IGV', porcentaje: '18.00', incluido: true, base: '127.12', monto: '22.88' } };
  const neto = { ...precio, impuesto: { nombre: 'IGV', porcentaje: '18.00', incluido: false, base: '127.12', monto: '22.88' } };
  expect(partidasPrecio(incluido).pie).toEqual([['Total', 'S/ 150,00'], ['Incluye IGV (18 %)', 'S/ 22,88', true], ['Anticipo 30 %', 'S/ 45,00']]);
  expect(partidasPrecio(neto).pie).toEqual([['Subtotal', 'S/ 127,12'], ['IGV (18 %)', 'S/ 22,88', true], ['Total', 'S/ 150,00'], ['Anticipo 30 %', 'S/ 45,00']]);
  expect(filasPrecio(incluido)[1]).toEqual(['Incluye IGV (18 %)', 'S/ 22,88']);
  expect(filasPrecio(neto)[1]).toEqual(['Más IGV (18 %)', 'S/ 22,88']);
  expect(porcentaje('12.50')).toBe('12,5 %');
});
