# RM — Peluquería · Barbería · Gestor de citas

Aplicación web de reservas para una peluquería/barbería real con un único peluquero. Los clientes se registran y reservan, cancelan o reprograman sus citas desde el móvil. El peluquero gestiona la agenda, los servicios, el horario y los días cerrados desde un panel de administración, y recibe los avisos por Telegram.

**En producción:** [rmolinastyle.com](https://rmolinastyle.com) · API en `https://api.rmolinastyle.com`

---

## 📸 Capturas

<p align="center">
  <img src="docs/capturas/login.png" alt="Pantalla de inicio de sesión en modo oscuro, con el logo de RM, los campos de email y contraseña y el botón dorado Entrar" width="90%">
  <br>
  <sub><b>Público</b> · inicio de sesión (modo oscuro)</sub>
</p>

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/capturas/registro.png" alt="Formulario de registro con los campos nombre, apellidos y teléfono y un texto de ayuda bajo cada uno">
      <br>
      <sub><b>Público</b> · registro de cliente con ayudas en cada campo</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/capturas/registro-consentimiento.png" alt="Parte final del formulario de registro con la casilla de aceptación de la política de privacidad sin marcar y el botón Registrarse desactivado">
      <br>
      <sub><b>Público</b> · consentimiento RGPD no premarcado</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/capturas/cliente-reservar.png" alt="Calendario de reserva con los días no disponibles atenuados, un día seleccionado en dorado y la lista de horas libres debajo">
      <br>
      <sub><b>Cliente</b> · reservar: calendario y horas disponibles</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/capturas/cliente-confirmar-reserva.png" alt="Resumen de la reserva con servicio, día, hora y duración, y el botón Confirmar reserva">
      <br>
      <sub><b>Cliente</b> · confirmación de la reserva</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/capturas/cliente-mis-citas.png" alt="Lista de citas del cliente con las etiquetas de estado Cancelada y Realizada">
      <br>
      <sub><b>Cliente</b> · mis citas con su estado</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/capturas/admin-agenda.png" alt="Agenda del día en el panel de administración con una cita a las 12:00 marcada como Reservada y el enlace Cancelar cita">
      <br>
      <sub><b>Admin</b> · agenda del día</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/capturas/admin-servicios.png" alt="Lista de servicios con duración, precio, etiqueta Activo y los enlaces Editar y Desactivar">
      <br>
      <sub><b>Admin</b> · gestión de servicios</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/capturas/admin-nuevo-servicio.png" alt="Formulario de nuevo servicio con nombre, desplegable de duración y precio en euros">
      <br>
      <sub><b>Admin</b> · nuevo servicio (de 30 min a 5 h)</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/capturas/admin-horario.png" alt="Pestaña de horario con la sección Días cerrados y los tramos de mañana y tarde de lunes, martes y miércoles">
      <br>
      <sub><b>Admin</b> · horario semanal por tramos y días cerrados</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/capturas/admin-clientes.png" alt="Lista de clientes con sus datos ocultos, la etiqueta Activo y el enlace Bloquear">
      <br>
      <sub><b>Admin</b> · clientes: bloquear y desbloquear</sub>
    </td>
  </tr>
</table>

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PyJWT · bcrypt · slowapi |
| Frontend | React 19 · Vite · React Router · Axios · CSS Modules |
| Base de datos | PostgreSQL 18 (Docker en local, Neon en producción) |
| Tests | pytest (SQLite en memoria, sin necesidad de Docker) |
| Hosting | **Vercel** en producción (frontend + backend serverless en Frankfurt, Vercel Cron) · **Render** como alternativa (ver [Despliegue](#despliegue)) |
| DNS / dominio | Cloudflare |

---

## Funcionalidades

**Cliente**
- Registro con validación (nombre y apellido, teléfono, email) y consentimiento RGPD explícito.
- Reserva: ciudad (**Alcalá la Real** o **Granada**, con una sola agenda), servicio, calendario limitado a **[hoy, hoy + 30 días]** que deshabilita los días cerrados, y hora. Solo muestra las horas de inicio en las que cabe el servicio entero. Para reservar hace falta el **Instagram** del cliente.
- Mis citas: con la ciudad de cada cita; cancelar y **reprogramar** (con al menos 24 h de antelación).
- Mi cuenta: editar perfil, cambiar contraseña, **exportar mis datos** (JSON) y **eliminar la cuenta** (se anonimiza).

**Administrador (peluquero)**
- Agenda con estados derivados (*Próxima*, *Realizada*, *No asistió* y *Cancelada*), y la ciudad y el Instagram de cada cita.
- Marcar inasistencias; contador de inasistencias por cliente; bloquear y desbloquear clientes.
- CRUD de servicios (de 30 min a 5 h, en pasos de 30 min; se desactivan en vez de borrarse).
- Horario semanal con varios tramos por día (jornada partida) y **días cerrados** por fecha concreta.

**Notificaciones (Telegram, solo al peluquero)**
- Aviso instantáneo cuando un cliente reserva, cancela o reprograma.
- Resumen cada noche con las citas del día siguiente. El cron está programado a las 20:00 UTC; en Vercel Hobby llega dentro de esa hora, entre las 21:00 y las 21:59 de Madrid en invierno y entre las 22:00 y las 22:59 en verano.

---

## Reglas de negocio clave

- **Franjas de 30 min.** La agenda se divide en franjas definidas en [`backend/app/constants.py`](backend/app/constants.py) (`FRANJA_MINUTOS`, `DURACION_MAX_MINUTOS = 300` y `DIAS_MAX_RESERVA = 30`). No escribas estos valores a mano en otras partes del código.
- **Sin solapes, garantizado por la BD.** Cada cita ocupa N filas en `franjas_ocupadas`, que tiene `UNIQUE (fecha, hora)`. La cita y sus franjas se insertan en una sola transacción; si hay colisión, se devuelve `409 Conflict`.
- **Zona horaria.** "Hoy", "mañana" y "ahora" se calculan siempre en `Europe/Madrid` y de la misma forma en todos los endpoints.
- **Estados de cita:** `activa`, `cancelada` y `no_asistida`. La etiqueta que se muestra depende del estado y de la fecha. No existe el estado "confirmada".

El detalle completo de las decisiones de diseño está en [`CLAUDE.md`](Archivos.md/CLAUDE.md).

---

## Estructura

```
.
├── Archivos.md/               # Documentación: CLAUDE.md, ESTADO_PROYECTO.md, DESPLIEGUE_VERCEL.md, DESPLIEGUE_RENDER.md
├── CLAUDE.md                  # Solo importa Archivos.md/CLAUDE.md (para que Claude Code lo cargue al arrancar)
├── backend/
│   ├── app/
│   │   ├── main.py            # App FastAPI, middlewares (CORS, cabeceras de seguridad), routers
│   │   ├── config.py          # Settings (pydantic-settings, lee .env)
│   │   ├── constants.py       # FRANJA_MINUTOS, DIAS_MAX_RESERVA, DURACION_MAX_MINUTOS
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   ├── schemas.py         # Esquemas Pydantic (entrada / salida separados)
│   │   ├── security.py        # JWT + bcrypt
│   │   ├── dependencies.py    # get_usuario_actual, solo_admin
│   │   ├── rate_limit.py
│   │   ├── notificaciones/    # Telegram
│   │   ├── tareas/            # Lógica del recordatorio diario y de la purga
│   │   └── routers/           # auth, usuarios, servicios, horario, disponibilidad, citas, excepciones, cron
│   ├── alembic/               # Migraciones
│   ├── scripts/               # Las mismas tareas por línea de comandos (el cron de Render las usa)
│   │   ├── recordatorio_diario.py   # Resumen diario (Telegram)
│   │   └── purga_citas.py           # Purga RGPD de citas antiguas
│   ├── tests/                 # pytest
│   ├── seed.py                # Crea las 2 cuentas admin si no existen
│   └── vercel.json            # Vercel: región fra1 y crons
├── frontend/
│   ├── src/
│   │   ├── api/client.js      # Axios con Bearer automático y manejo central de 401/409
│   │   ├── context/           # AuthContext, ThemeContext
│   │   ├── pages/             # Login, Registro, DashboardCliente, PanelAdmin, MiCuenta, páginas legales
│   │   ├── components/        # admin/, cliente/, cuenta/, layout/, ui/
│   │   └── styles/theme.css   # Paleta negro/oro, modo claro/oscuro, escala tipográfica
│   └── vercel.json            # Vercel: rewrite SPA y cabeceras de seguridad (CSP)
├── docker-compose.yaml        # PostgreSQL 18 local
└── render.yaml                # Render: infraestructura como Blueprint (despliegue alternativo)
```

---

## Puesta en marcha en local

### Requisitos

- Python 3.14 (la misma versión que en Vercel, fijada en `backend/.python-version`)
- Node.js 20+
- Docker (para PostgreSQL)

### 1. Base de datos

```bash
docker compose up -d
```

Levanta PostgreSQL 18 (la misma versión que Neon) en `127.0.0.1:5434` (usuario `peluqueria`, contraseña `dev_local_2024`, BD `peluqueria`), accesible solo desde el propio equipo. Usa el 5434 y no el 5432 para no chocar con otros Postgres del equipo. Conéctate a `127.0.0.1` y no a `localhost`: en Windows `localhost` resuelve primero a `::1`, donde no escucha el contenedor, y la conexión se queda esperando. Puedes conectarte con HeidiSQL o con cualquier otro cliente.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env        # y edita los valores (ver "Variables de entorno")

alembic upgrade head           # crea el esquema
python seed.py                 # crea las 2 cuentas admin (idempotente)

uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Documentación interactiva (solo fuera de producción): `http://localhost:8000/docs` y `/redoc`
- Health check: `http://localhost:8000/health`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env           # VITE_API_URL=/api
npm run dev
```

La app queda en `http://127.0.0.1:5173` (Vite solo escucha en el propio equipo). En desarrollo, Vite redirige `/api/*` a `http://localhost:8000` (ver [`vite.config.js`](frontend/vite.config.js)), así que no hace falta configurar CORS.

> Para enseñar una demo desde el entorno local a través de un túnel de Cloudflare, sigue [`TUNEL_LOCAL.md`](TUNEL_LOCAL.md).

---

## Variables de entorno

**Backend** (`backend/.env`; la plantilla con comentarios está en [`.env.example`](.env.example)):

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+psycopg://…`. Si llega `postgres://` (Render) o `postgresql://` (Neon), se normaliza sola. En Vercel, la URL **pooled** de Neon; para migraciones, la **directa**. |
| `SECRET_KEY` | ✅ | Firma de los JWT. Genérala con `openssl rand -hex 32`. |
| `ALGORITHM` | | Por defecto `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Por defecto `10080` (7 días). |
| `ALLOWED_ORIGINS` | | Array JSON, p. ej. `["http://localhost:5173"]`. |
| `ENVIRONMENT` | | `development` o `production`. En producción se desactivan `/docs` y `/openapi.json` y se activa HSTS. |
| `RETENCION_MESES` | | Meses que se conservan las citas antes de la purga (por defecto `24`). |
| `DB_NULLPOOL` | | `true` en Vercel: sin pool de conexiones, para que Neon pueda escalar a cero. En local y en Render, `false` (por defecto). |
| `CRON_SECRET` | | Protege `/cron/*` (solo Vercel). Si falta, esos endpoints responden 404. |
| `ADMIN1_*`, `ADMIN2_*` | Para el seed | `EMAIL`, `PASSWORD`, `NOMBRE` y `TELEFONO` de las dos cuentas admin. La contraseña solo se usa al crear la cuenta. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | Si faltan, no se envía ningún aviso y la app sigue funcionando. |
| `VERCEL`, `RENDER` | — | Las pone la propia plataforma (no hay que crearlas). Sirven para saber de qué cabeceras tomar la IP del cliente para el rate limiting. |

**Frontend** (`frontend/.env`):

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | `/api` en desarrollo (a través del proxy de Vite); `https://api.rmolinastyle.com` en producción. |

Los secretos nunca se suben al repositorio: `.env` está en `.gitignore`.

---

## Tests

```bash
cd backend
pytest
```

Los tests usan SQLite en memoria (ver [`tests/conftest.py`](backend/tests/conftest.py)), así que no necesitan Docker ni una base de datos levantada. Cada endpoint tiene sus tests: autenticación, citas, disponibilidad, reprogramación, días cerrados, horario, servicios, usuarios, RGPD, notificaciones, recordatorio diario y purga.

Lint del frontend:

```bash
cd frontend
npm run lint
```

---

## API (resumen)

| Método | Ruta | Acceso |
|---|---|---|
| `POST` | `/registro`, `/login` | Público (5/min por IP) |
| `GET` · `PATCH` · `DELETE` | `/usuarios/me` | Autenticado (`DELETE` anonimiza la cuenta) |
| `GET` | `/usuarios/me/datos` | Autenticado (exportación RGPD) |
| `PATCH` | `/usuarios/me/password` | Autenticado |
| `GET` | `/usuarios`, `/usuarios/{id}` | Admin |
| `PATCH` | `/usuarios/{id}/bloquear`, `/usuarios/{id}/desbloquear` | Admin |
| `GET` | `/servicios`, `/servicios/{id}` | Autenticado (los inactivos, solo admin) |
| `POST` · `PUT` · `DELETE` | `/servicios[/{id}]` | Admin |
| `GET` | `/horario` | Autenticado |
| `POST` · `PUT` · `DELETE` | `/horario[/{id}]` | Admin |
| `GET` | `/disponibilidad?fecha=&servicio_id=` | Autenticado |
| `GET` | `/excepciones/proximas` | Autenticado |
| `GET` · `POST` · `DELETE` | `/excepciones[/{id}]` | Admin |
| `POST` | `/citas` | Cliente (10/min y 50/día por usuario) |
| `GET` | `/citas/mias` | Cliente |
| `GET` | `/citas` | Admin |
| `GET` | `/citas/{id}` | Dueño o admin |
| `PATCH` | `/citas/{id}/cancelar`, `/citas/{id}/reprogramar` | Dueño o admin |
| `PATCH` | `/citas/{id}/no-asistida` | Admin |
| `GET` | `/health` | Público (no toca la BD) |
| `GET` | `/cron/recordatorio`, `/cron/purga` | Solo Vercel Cron (`Authorization: Bearer <CRON_SECRET>`) |

Con el backend en local, la especificación completa está en `/docs`.

---

## Despliegue

Hay **dos formas de desplegar** el proyecto, y las dos están preparadas en el repositorio:

- **Vercel + Neon**: la que se usa en producción. Se eligió **a petición del dueño del negocio (el peluquero)**, para que el coste fuera prácticamente cero.
- **Render**: la alternativa. Fue la producción hasta el 8 de noviembre de 2026.

El código es el mismo en las dos. Detecta en qué plataforma se ejecuta por las variables que pone ella misma (`VERCEL=1` o `RENDER=true`).

| | **Vercel + Neon** (producción) | **Render** (alternativa) |
|---|---|---|
| Frontend | Proyecto Vercel con raíz `frontend/` (estático, Vite) | Static Site `rm-frontend` |
| Backend | Proyecto Vercel con raíz `backend/` (FastAPI serverless, región `fra1`) | Web Service `rm-backend` (uvicorn, Starter) |
| Base de datos | Neon Free, Postgres 18 (Frankfurt) | PostgreSQL gestionada `rm-postgres` (Frankfurt, backups diarios) |
| Tareas programadas | Vercel Cron → `/cron/recordatorio` (`0 20 * * *` UTC) y `/cron/purga` (`0 3 * * *` UTC) | Cron Job `rm-recordatorios` → `python scripts/recordatorio_diario.py` (`0 20 * * *` UTC) |
| Migraciones | **A mano**, contra la URL directa de Neon, antes del merge a `main` | Automáticas en el pre-deploy: `alembic upgrade head && python seed.py` |
| Configuración | [`backend/vercel.json`](backend/vercel.json) y [`frontend/vercel.json`](frontend/vercel.json) | [`render.yaml`](render.yaml) (Blueprint) |
| Coste aproximado | 0 € (más el dominio) | ~18,50 €/mes |
| Guía | [`DESPLIEGUE_VERCEL.md`](Archivos.md/DESPLIEGUE_VERCEL.md) | [`DESPLIEGUE_RENDER.md`](Archivos.md/DESPLIEGUE_RENDER.md) |

**Vercel + Neon (producción):**
- `main` se despliega solo en Vercel con cada push. Las variables con secretos (`DATABASE_URL`, `TELEGRAM_*` y `CRON_SECRET`) están solo en el entorno *Production*, para que las previews de otras ramas no toquen la BD real ni avisen al peluquero.
- El backend es serverless: abre conexiones sin pool (`DB_NULLPOOL=true`), no hace trabajo después de responder y `/health` no toca la BD.
- Vercel no tiene paso de pre-deploy, así que las migraciones se aplican a mano. Ver §3 de [`DESPLIEGUE_VERCEL.md`](Archivos.md/DESPLIEGUE_VERCEL.md).
- En el plan Hobby, el cron se ejecuta en algún momento dentro de la hora programada.

**Render (alternativa):**
- La versión que estuvo desplegada en Render está en la rama `render` y en el tag `render-v1`.
- Los secretos con `sync: false` se introducen a mano en el panel de Render **de cada servicio**. El cron necesita sus propios `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- `render.yaml` solo programa el recordatorio. La purga se lanza a mano (`python scripts/purga_citas.py`) o añadiendo un segundo Cron Job.
- Si una migración endurece una restricción (`CHECK`, `UNIQUE`…), corrige antes los datos que la incumplan. Si no, el pre-deploy falla.
- **No hay nada desplegado en Render**: los servicios se borraron el 10 de noviembre de 2026. Para usarlo habría que montarlo **desde cero** con `render.yaml` (Blueprint nuevo), probarlo y pasar los datos desde Neon con `pg_dump`/`pg_restore`.

> ⚠️ Solo una de las dos debe estar activa a la vez. Con las dos, el peluquero recibiría dos resúmenes cada noche y las reservas quedarían repartidas entre dos bases de datos distintas.

---

## Seguridad y cumplimiento

- JWT en la cabecera `Authorization: Bearer`, contraseñas con bcrypt y rate limiting en login, registro y reservas.
- Control de acceso por objeto en cada endpoint. El `cliente_id` y el rol se toman siempre del token, nunca del body.
- Cabeceras de seguridad: CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` y HSTS en producción.
- Los errores 500 son genéricos y no devuelven el stack trace. No se registran datos personales en los logs.
- **RGPD / LOPDGDD / LSSI-CE:**
  - Páginas `/aviso-legal`, `/politica-privacidad` y `/politica-cookies`, enlazadas desde el footer.
  - Consentimiento con versión y fecha guardadas en la BD.
  - Exportación de datos y anonimización de la cuenta.
  - Purga de citas antiguas: cron diario `/cron/purga` en Vercel, o `scripts/purga_citas.py [--dry-run]` por línea de comandos.
  - Solo se usa almacenamiento técnico (el JWT en `localStorage`), así que no hace falta banner de cookies.
  - Las fuentes están alojadas en el propio servidor.

> Los textos legales contienen marcadores `[…]` que debe completar el titular del negocio.

---

## Documentación adicional

- [`CLAUDE.md`](Archivos.md/CLAUDE.md): especificación y decisiones de diseño (fuente de verdad).
- [`ESTADO_PROYECTO.md`](Archivos.md/ESTADO_PROYECTO.md): estado actual, incidentes y tareas pendientes.
- [`DESPLIEGUE_VERCEL.md`](Archivos.md/DESPLIEGUE_VERCEL.md): despliegue en Vercel + Neon (producción).
- [`DESPLIEGUE_RENDER.md`](Archivos.md/DESPLIEGUE_RENDER.md): despliegue en Render (alternativa).
- [`TUNEL_LOCAL.md`](TUNEL_LOCAL.md): demo local con un túnel de Cloudflare.

---

Desarrollado por **Cristian Aceituno**.
