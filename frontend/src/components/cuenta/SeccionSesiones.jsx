import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import client from '../../api/client'
// Mismo aspecto (sección, botones y modal) que "Privacidad y datos".
import styles from './SeccionPrivacidad.module.css'

export default function SeccionSesiones() {
  const { logout } = useAuth()
  const navigate   = useNavigate()

  const [modalAbierto, setModalAbierto] = useState(false)
  const [cerrando,     setCerrando]     = useState(false)
  const [error,        setError]        = useState('')

  const abrirModal = () => {
    setError('')
    setModalAbierto(true)
  }

  const confirmarCerrar = async () => {
    setCerrando(true)
    setError('')
    try {
      await client.post('/usuarios/me/cerrar-sesiones')
      logout()
      navigate('/login', {
        replace: true,
        state: { mensaje: 'Has cerrado sesión en todos los dispositivos.' },
      })
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Demasiados intentos. Espera un momento e inténtalo de nuevo.')
      } else {
        setError('No se pudieron cerrar las sesiones. Inténtalo de nuevo.')
      }
      setCerrando(false)
    }
  }

  return (
    <section className={styles.seccion}>
      <h2 className={styles.titulo}>Sesiones</h2>

      <div className={styles.acciones}>
        <div className={styles.accion}>
          <p className={styles.accionDesc}>
            Cierra la sesión en todos los dispositivos donde hayas entrado, incluido este.
            Tendrás que volver a iniciar sesión.
          </p>
          <button
            type="button"
            className={styles.btnDescargar}
            onClick={abrirModal}
          >
            Cerrar sesión en todos los dispositivos
          </button>
        </div>
      </div>

      {modalAbierto && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="modal-sesiones-titulo">
          <div className={styles.modal}>
            <h3 id="modal-sesiones-titulo" className={styles.modalTitulo}>
              ¿Cerrar sesión en todos los dispositivos?
            </h3>
            <p className={styles.modalAviso}>
              Se cerrará la sesión en todos los dispositivos, también en este, y tendrás que
              volver a iniciar sesión.
            </p>
            {error && (
              <p className={styles.msgError} role="alert">{error}</p>
            )}
            <div className={styles.modalBotones}>
              <button
                type="button"
                className={styles.btnCancelarModal}
                onClick={() => setModalAbierto(false)}
                disabled={cerrando}
              >
                Cancelar
              </button>
              <button
                type="button"
                className={styles.btnConfirmar}
                onClick={confirmarCerrar}
                disabled={cerrando}
              >
                {cerrando ? 'Cerrando…' : 'Cerrar sesiones'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
