// Textos de marca, visual y pie de las pantallas de acceso (RF-01-acceso*.md, tabla Copy). Los comparten varias paginas.
const pieArtistas = { texto: 'SALA VIRTUAL BUGALÚ STUDIO © 2026', enlace: { texto: '¿Eres del equipo? Acceso interno', href: '/acceso/interno' } };
const pieInterno = { texto: 'BUGALÚ STUDIO · CONVERGE Y CREA' };

export const artistasIniciar = {
  antetitulo: 'ACCESO DE ARTISTAS',
  marca: { codigo: '[PORTAL_ARTISTAS]', texto: 'Escucha tus premezclas, aprueba versiones, pide ajustes a nuestros ingenieros y revisa el historial de tus sesiones.', etiquetas: ['ESTADO: LISTO', 'CONVERGE Y CREA'] },
  visual: { titulo: 'NUESTRAS SALAS DE SEGUIMIENTO', nota: 'Descarga tus versiones en WAV de alta resolución y en MP3 para escucharlas en el móvil.' },
  pie: pieArtistas,
};

export const artistasRegistro = {
  antetitulo: 'NUEVA CUENTA DE ARTISTA O BANDA',
  marca: { codigo: '[ALTA_CREADORES]', texto: 'Regístrate para llevar tu proyecto musical en un solo lugar: reserva sesiones, revisa versiones y habla con el estudio.', etiquetas: ['CONEXIÓN DIRECTA', 'CREADORES BIENVENIDOS'] },
  visual: { titulo: 'REGISTRA TU PROYECTO', nota: 'Recibe tus premezclas y envía tus comentarios en el mismo lugar.' },
  pie: pieArtistas,
};

const visualInterno = { titulo: '“La rigurosidad acústica exige una interfaz sin adornos.”', nota: '— Manual del ingeniero de sonido, Bugalú' };
const marcaInterno = { codigo: '[ACCESO_INTERNO]', texto: 'Panel de producción, ingeniería y administración de Bugalú Studio. Inicia sesión para gestionar sesiones, proyectos y versiones.', etiquetas: ['SALA DE CONTROL', 'V1.0'] };

export const internoIniciar = { antetitulo: 'SISTEMA DE ACCESO INTERNO', marca: marcaInterno, visual: visualInterno, pie: pieInterno };
export const internoEstado = { antetitulo: 'ACCESO INTERNO', marca: marcaInterno, visual: visualInterno, pie: pieInterno };
export const internoSolicitar = {
  antetitulo: 'INGRESO DE EQUIPO',
  marca: { codigo: '[REGISTRO_TÉCNICO]', texto: 'Pide tu acceso al panel del estudio. El Administrador revisa cada solicitud.', etiquetas: ['REGISTRO: SOLO EQUIPO', 'V1.0'] },
  visual: visualInterno,
  pie: { texto: 'SISTEMA DE CONTROL INTERNO · BUGALÚ STUDIO' },
};

// Recuperar y nueva contraseña: marca de artistas; con ?origen=interno la isla alterna a la del acceso interno.
export const recuperacion = { ...artistasIniciar, antetitulo: 'RECUPERACIÓN DE ACCESO', alterna: { marca: marcaInterno, pie: pieInterno } };
