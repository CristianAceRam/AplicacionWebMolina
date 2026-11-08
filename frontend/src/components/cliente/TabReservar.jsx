import { useEffect, useState } from 'react'
import client from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { UBICACIONES, NOMBRE_UBICACION, DIRECCION_ALCALA, detalleUbicacion } from '../../constants/ubicaciones'
import { AYUDA_INSTAGRAM, esInstagramValido, normalizarInstagram } from '../../utils/instagram'
import Button from '../ui/Button'
import FormField from '../ui/FormField'
import Spinner from '../ui/Spinner'
import { capitalizar } from '../../utils/texto'
import Calendario from './Calendario'
import styles from './TabReservar.module.css'

function formatDuracion(minutos) {
  if (minutos >= 60 && minutos % 60 === 0) return `${minutos / 60} h`
  if (minutos >= 60) return `${Math.floor(minutos / 60)} h ${minutos % 60} min`
  return `${minutos} min`
}

function formatPrecio(precio) {
  return `${parseFloat(precio).toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} €`
}

function formatFechaLarga(date) {
  return date.toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

function fechaAString(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// Extrae el error de Instagram de una respuesta 422 (Pydantic → lista; negocio → texto).
function errorInstagramDe(detail) {
  if (Array.isArray(detail)) {
    const item = detail.find(d => d.loc?.[1] === 'instagram')
    return item ? 'Revisa tu usuario de Instagram. ' + AYUDA_INSTAGRAM : ''
  }
  if (typeof detail === 'string' && detail.includes('Instagram')) return detail
  return ''
}

export default function TabReservar({ servicios, diasAbiertos, fechasCerradas = new Set(), onVerMisCitas }) {
  const { usuario, refreshUsuario } = useAuth()

  const [ubicacion, setUbicacion]   = useState(null)
  const [servicio, setServicio]     = useState(null)
  const [fecha, setFecha]           = useState(null)
  const [hora, setHora]             = useState(null)
  const [horas, setHoras]           = useState([])
  const [cargandoHoras, setCargandoHoras] = useState(false)
  // Precargado del perfil; si lo cambia, se guarda en el perfil al reservar.
  const [instagram, setInstagram]   = useState(() => usuario?.instagram ?? '')
  const [errorInstagram, setErrorInstagram] = useState('')
  const [confirmado, setConfirmado] = useState(false)
  const [cargandoPost, setCargandoPost] = useState(false)
  const [errorReserva, setErrorReserva] = useState('')

  // Al cambiar servicio o fecha, cargar disponibilidad (la ciudad no influye: agenda única)
  useEffect(() => {
    if (!servicio || !fecha) return
    setHora(null)
    setHoras([])
    setErrorReserva('')
    setCargandoHoras(true)
    client
      .get('/disponibilidad', {
        params: { fecha: fechaAString(fecha), servicio_id: servicio.id },
      })
      .then(r => setHoras(r.data.horas_disponibles))
      .catch(() => setHoras([]))
      .finally(() => setCargandoHoras(false))
  }, [servicio, fecha])

  // Cambiar de ciudad NO borra servicio/fecha/hora: la ciudad no afecta a la disponibilidad.
  const handleUbicacion = (id) => {
    setUbicacion(id)
    setErrorReserva('')
  }

  const handleServicio = (s) => {
    setServicio(s)
    setFecha(null)
    setHora(null)
    setHoras([])
    setConfirmado(false)
    setErrorReserva('')
  }

  const handleFecha = (d) => {
    setFecha(d)
    setHora(null)
    setErrorReserva('')
  }

  const handleInstagram = (e) => {
    setInstagram(e.target.value)
    setErrorInstagram('')
  }

  const recargarDisponibilidad = () => {
    if (!servicio || !fecha) return
    setHora(null)
    setCargandoHoras(true)
    client
      .get('/disponibilidad', {
        params: { fecha: fechaAString(fecha), servicio_id: servicio.id },
      })
      .then(r => setHoras(r.data.horas_disponibles))
      .catch(() => setHoras([]))
      .finally(() => setCargandoHoras(false))
  }

  const handleConfirmar = async () => {
    if (!ubicacion || !servicio || !fecha || !hora) return
    setErrorReserva('')
    if (!esInstagramValido(instagram)) {
      setErrorInstagram(
        instagram.trim() ? `Usuario de Instagram no válido. ${AYUDA_INSTAGRAM}` : 'El Instagram es obligatorio para reservar.'
      )
      return
    }
    const igNormalizado = normalizarInstagram(instagram)
    const body = {
      servicio_id: servicio.id,
      fecha: fechaAString(fecha),
      hora_inicio: hora,
      ubicacion,
    }
    // Solo se envía si es nuevo o distinto del guardado (el backend lo guarda en el perfil).
    if (igNormalizado !== usuario?.instagram) body.instagram = igNormalizado

    setCargandoPost(true)
    try {
      await client.post('/citas', body)
      setConfirmado(true)
      refreshUsuario().catch(() => {})
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (err.isConflict || status === 409) {
        setErrorReserva('Ese hueco acaba de ocuparse. Las horas se han actualizado.')
        recargarDisponibilidad()
      } else if (status === 403) {
        setErrorReserva(
          'No puedes hacer reservas ahora. Contacta con el peluquero para más información.'
        )
      } else if (status === 422 && errorInstagramDe(detail)) {
        setErrorInstagram(errorInstagramDe(detail))
      } else {
        setErrorReserva(
          typeof detail === 'string' ? detail : 'No se pudo crear la reserva. Recarga la página e inténtalo de nuevo.'
        )
      }
    } finally {
      setCargandoPost(false)
    }
  }

  const handleNuevaReserva = () => {
    setUbicacion(null)
    setServicio(null)
    setFecha(null)
    setHora(null)
    setHoras([])
    setConfirmado(false)
    setErrorReserva('')
    setErrorInstagram('')
  }

  // ── Éxito ──────────────────────────────────────────────────────────────────
  if (confirmado) {
    return (
      <div className={styles.exito}>
        <p className={styles.exitoIcono}>✓</p>
        <h2>¡Reserva confirmada!</h2>
        <p className={styles.exitoDetalle}>
          <strong>{servicio.nombre}</strong> — {formatFechaLarga(fecha)} a las {hora.slice(0, 5)}
          {' '}en <strong>{NOMBRE_UBICACION[ubicacion]}</strong>
        </p>
        <p className={styles.exitoDetalle}>{detalleUbicacion(ubicacion)}</p>
        <div className={styles.exitoAcciones}>
          <Button onClick={onVerMisCitas}>Ver mis citas</Button>
          <Button variant="ghost" onClick={handleNuevaReserva}>
            Hacer otra reserva
          </Button>
        </div>
      </div>
    )
  }

  const listo = ubicacion && servicio && fecha && hora

  return (
    <div className={styles.flujo}>
      {/* ── Sección 1: elegir ciudad ─────────────────────────────────────── */}
      <section className={styles.seccion}>
        <h2 className={styles.seccionTitulo}>¿Dónde quieres tu cita?</h2>
        <div className={styles.serviciosGrid}>
          {UBICACIONES.map(u => (
            <button
              key={u.id}
              type="button"
              className={`${styles.servicioCard} ${ubicacion === u.id ? styles.servicioSeleccionado : ''}`}
              onClick={() => handleUbicacion(u.id)}
              aria-pressed={ubicacion === u.id}
            >
              <span className={styles.servicioNombre}>{u.nombre}</span>
              <span className={styles.servicioMeta}>{detalleUbicacion(u.id)}</span>
            </button>
          ))}
        </div>
      </section>

      {/* ── Sección 2: servicios (siempre visibles; se pueden elegir tras la ciudad) ── */}
      <section className={styles.seccion}>
        <h2 className={styles.seccionTitulo}>Elige un servicio</h2>
        {!ubicacion && (
          <p className={styles.explicacion} id="aviso-elige-ciudad">
            Elige primero dónde quieres tu cita para poder seleccionar un servicio.
          </p>
        )}
        <div className={styles.serviciosGrid}>
          {servicios.map(s => (
            <button
              key={s.id}
              type="button"
              disabled={!ubicacion}
              aria-describedby={!ubicacion ? 'aviso-elige-ciudad' : undefined}
              className={`${styles.servicioCard} ${servicio?.id === s.id ? styles.servicioSeleccionado : ''}`}
              onClick={() => handleServicio(s)}
            >
              <span className={styles.servicioNombre}>{s.nombre}</span>
              <span className={styles.servicioMeta}>
                {formatDuracion(s.duracion_minutos)} · {formatPrecio(s.precio)}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* ── Sección 3: elegir fecha ─────────────────────────────────────── */}
      {ubicacion && servicio && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Elige un día</h2>
          <Calendario
            diasAbiertos={diasAbiertos}
            fechasCerradas={fechasCerradas}
            fechaSeleccionada={fecha}
            onSeleccionar={handleFecha}
          />
        </section>
      )}

      {/* ── Sección 4: elegir hora ──────────────────────────────────────── */}
      {ubicacion && servicio && fecha && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Elige una hora</h2>
          {cargandoHoras ? (
            <div className={styles.centrado}><Spinner size={22} /></div>
          ) : horas.length === 0 ? (
            <p className={styles.vacio}>No hay horas disponibles para ese día.</p>
          ) : (
            <div className={styles.horasGrid}>
              {horas.map(h => (
                <button
                  key={h}
                  type="button"
                  className={`${styles.horaBtn} ${hora === h ? styles.horaSeleccionada : ''}`}
                  onClick={() => { setHora(h); setErrorReserva('') }}
                >
                  {h.slice(0, 5)}
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ── Sección 5: Instagram (obligatorio) ──────────────────────────── */}
      {listo && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Tu Instagram</h2>
          <p className={styles.explicacion}>
            Es obligatorio para reservar: Molina lo usa para contactar contigo sobre tu cita
            {ubicacion === 'granada' ? ' y, en Granada, para concretar el sitio' : ''}.
            Se guarda en tu perfil y puedes cambiarlo en «Mi cuenta».
          </p>
          <FormField
            label="Usuario de Instagram"
            name="instagram"
            value={instagram}
            onChange={handleInstagram}
            error={errorInstagram}
            ayuda={AYUDA_INSTAGRAM}
            placeholder="tu.usuario"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            required
          />
        </section>
      )}

      {/* ── Sección 6: resumen y confirmar ──────────────────────────────── */}
      {listo && (
        <section className={styles.seccion}>
          <h2 className={styles.seccionTitulo}>Confirma tu reserva</h2>
          <div className={styles.resumen}>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Ciudad</span>
              <span>{NOMBRE_UBICACION[ubicacion]}</span>
            </div>
            {ubicacion === 'alcala' && (
              <div className={styles.resumenFila}>
                <span className={styles.resumenLabel}>Dirección</span>
                <span className={styles.resumenValor}>{DIRECCION_ALCALA}</span>
              </div>
            )}
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Servicio</span>
              <span>{servicio.nombre}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Día</span>
              <span>{capitalizar(formatFechaLarga(fecha))}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Hora</span>
              <span>{hora.slice(0, 5)}</span>
            </div>
            <div className={styles.resumenFila}>
              <span className={styles.resumenLabel}>Duración</span>
              <span>{formatDuracion(servicio.duracion_minutos)}</span>
            </div>
          </div>
          {errorReserva && (
            <p className={styles.errorMsg} role="alert">{errorReserva}</p>
          )}
          <Button
            type="button"
            loading={cargandoPost}
            onClick={handleConfirmar}
          >
            Confirmar reserva
          </Button>
        </section>
      )}
    </div>
  )
}
