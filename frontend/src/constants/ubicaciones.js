// Ciudades donde trabaja el peluquero (agenda, horario y servicios únicos para las dos).
// Las claves coinciden con Cita.ubicacion en el backend (app/constants.py → NOMBRES_UBICACION).
export const UBICACIONES = [
  { id: 'alcala',  nombre: 'Alcalá la Real' },
  { id: 'granada', nombre: 'Granada' },
]

export const NOMBRE_UBICACION = Object.fromEntries(UBICACIONES.map(u => [u.id, u.nombre]))

// ⚠️ PENDIENTE: dirección exacta del local de Alcalá la Real (la da Molina).
// Única constante con la dirección; revisarla en la checklist de merge antes de producción.
export const DIRECCION_ALCALA = '[dirección de Alcalá la Real]'

// Granada no tiene local fijo.
export const TEXTO_GRANADA =
  'En Granada no hay local fijo: Molina te escribirá por Instagram para concretar el sitio.'

// Texto de apoyo para la ciudad (dirección en Alcalá, aviso en Granada).
export function detalleUbicacion(id) {
  if (id === 'alcala') return DIRECCION_ALCALA
  if (id === 'granada') return TEXTO_GRANADA
  return ''
}
