// Misma regla que el backend (app/schemas.py → _validar_instagram). Aquí solo es
// para avisar al usuario mientras escribe: la validación que manda es la del backend.
const INSTAGRAM_RE = /^(?!\.)(?!.*\.\.)(?!.*\.$)[a-z0-9._]{1,30}$/

export function normalizarInstagram(valor) {
  let v = (valor ?? '').trim()
  if (v.startsWith('@')) v = v.slice(1)
  return v.toLowerCase()
}

export function esInstagramValido(valor) {
  return INSTAGRAM_RE.test(normalizarInstagram(valor))
}

export const AYUDA_INSTAGRAM =
  "Hasta 30 caracteres: letras, números, '.' y '_' (sin '..' ni '.' al principio o al final)."

// Enlace al perfil. Se codifica por si acaso, aunque un usuario válido solo tiene [a-z0-9._].
export function urlInstagram(usuario) {
  return `https://instagram.com/${encodeURIComponent(usuario)}`
}
