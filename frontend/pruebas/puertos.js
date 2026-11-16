// Puertos y origenes de los servidores de prueba, compartidos por la config y las pruebas. Con PUERTO_PRUEBAS la suite corre en otro puerto.
export const PUERTO = Number(process.env.PUERTO_PRUEBAS) || 4321;
export const PUERTO_PROVEEDORES = PUERTO + 1; // segundo build, con proveedores sociales
export const ORIGEN = `http://localhost:${PUERTO}`;
export const ORIGEN_PROVEEDORES = `http://localhost:${PUERTO_PROVEEDORES}`;
