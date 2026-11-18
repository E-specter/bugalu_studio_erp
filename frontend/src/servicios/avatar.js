// Avatar pintado en el navegador (avatar.md): el nodo sale de la plantilla con <Avatar>; aqui se le dan las iniciales y la foto.
// Si la imagen no carga, se quita y quedan las iniciales (sin aviso).
export const iniciales = (nombre) => {
  const p = String(nombre ?? '').trim().split(/\s+/).filter(Boolean);
  return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : (p[0]?.[0] ?? '')).toUpperCase();
};

// `avatar`: el <span class="avatar"> clonado; `foto`: URL o null; `alt`: vacio si el nombre va al lado.
export function ponerAvatar(avatar, nombre, foto, alt = '') {
  avatar.querySelector('.avatar-iniciales').textContent = iniciales(nombre);
  avatar.querySelector('.avatar-foto')?.remove();
  if (!foto) return avatar;
  if (alt) avatar.removeAttribute('aria-hidden'); // sin nombre al lado, la foto es el contenido
  const lado = avatar.classList.contains('avatar-retrato') ? 344 : avatar.classList.contains('avatar-miniatura') ? 96 : 38;
  const img = Object.assign(new Image(lado, lado), { className: 'avatar-foto', alt, loading: avatar.classList.contains('avatar-retrato') ? 'eager' : 'lazy' });
  img.addEventListener('error', () => img.remove());
  img.src = foto;
  avatar.append(img);
  return avatar;
}
