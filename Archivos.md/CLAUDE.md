# CLAUDE.md — Gestor de Citas Peluquería RM
 
> Archivo de contexto del proyecto para Claude Code. Léelo antes de generar o modificar código y respeta todas las decisiones.
 
---
 
## Contexto
 
App web de gestión de citas para una peluquería/barbería real ("RM — Peluquería · Barbería"), un único peluquero que trabaja en **dos ciudades: Alcalá la Real y Granada** (con una única agenda). Proyecto en producción, desarrollador único. **Uso principal en móvil**, pero responsiva.
 
---
 
## Stack (fijado)
 
- Backend: FastAPI (Python 3.14). Frontend: React + Vite (JavaScript). BD: PostgreSQL.
- ORM: SQLAlchemy + Alembic. Validación: Pydantic. Auth: JWT (cabecera `Authorization: Bearer`). Rate limiting: slowapi. Tests: pytest.
- Entorno local: **PostgreSQL 18** en contenedor Docker (docker-compose), la misma versión que producción (Neon), + HeidiSQL.
- **Hosting de producción**: **Vercel Hobby** con dos proyectos: raíz `frontend/` (static Vite) y raíz `backend/` (FastAPI con el runtime de Python de Vercel), región de funciones `fra1`. BD: **Neon Free** (Frankfurt). DNS en Cloudflare ("DNS only"). Tareas programadas con **Vercel Cron**. Detalles en `DESPLIEGUE_VERCEL.md`.
- **Dos formas de despliegue**:
  - **Vercel**: la de producción, elegida **a petición del dueño del negocio (el peluquero)** por coste.
  - **Render**: alternativa, con `render.yaml` y `DESPLIEGUE_RENDER.md`. El código detecta la plataforma (`VERCEL=1` / `RENDER=true`). **No hay nada desplegado en Render** (se borró el 10-nov-2026): habría que montarlo desde cero con `render.yaml`.

  Nunca las dos activas a la vez. La versión que estuvo desplegada en Render está en la rama `render` y en el tag `render-v1`: **no tocar** esa rama.
- Sin tiempo real: la disponibilidad se refresca al recargar.
---
 
## Ramas
 
- `main` = producción (Vercel despliega automáticamente desde aquí).
- `render` = congelada (versión de Render).
- Las funciones nuevas se desarrollan en ramas `feature/*` creadas desde `main`, se prueban en local y se mezclan en `main` cuando están listas.
- En Vercel, `DATABASE_URL`, `TELEGRAM_*` y `CRON_SECRET` se configuran **solo en el entorno Production**: las previews de otras ramas no deben tocar la BD real ni avisar al peluquero.
---
 
## Reglas serverless (Vercel + Neon) — obligatorias
 
- **Nada de trabajo después de enviar la respuesta** (no usar `BackgroundTasks`): todo se hace antes de responder.
- Conexiones a BD con `NullPool` (`DB_NULLPOOL=true`) y `prepare_threshold=None`, usando la URL `-pooler` de Neon. Si quedan conexiones abiertas, Neon no escala a cero y se agotan las 100 CU-hours gratis del mes.
- `/health` **nunca** toca la BD (lo consulta el monitor de uptime cada pocos minutos).
- **No** se ejecutan migraciones al arrancar. Migraciones a mano: `alembic upgrade head` contra la URL **directa** de Neon (sin `-pooler`).
- La IP del cliente se obtiene de las cabeceras de Vercel (`app/rate_limit.py`, detección por plataforma). El rate limiting es "best effort" (contadores en memoria por instancia).
- `tzdata` es dependencia obligatoria (sin ella, `ZoneInfo("Europe/Madrid")` falla en Linux y no arranca la API).
---
 
## Convenciones
 
- Dominio en español (`Usuario`, `Cita`, `Servicio`...). Secretos solo en variables de entorno.
- Cada endpoint nuevo con su test pytest. Esquemas de entrada y salida separados.
- En FastAPI, rutas literales antes que rutas con parámetro.
---
 
## Roles y autenticación
 
- **admin**: peluquero y desarrollador. Solo 2 cuentas fijas (ya existen en la BD). No hay registro público de admins.
- **cliente**: se registra él mismo.
Registro de cliente (`POST /registro`, solo crea rol cliente; el rol nunca se acepta del body):
- `nombre_completo`: obligatorio. Al menos nombre y apellido (mínimo dos palabras), solo letras/espacios/guiones/acentos.
- `telefono`: obligatorio, formato España, normalizado. Sirve para **contactar** al cliente.
- `email`: obligatorio, válido y único.
- `password`: obligatorio, mínimo 8 caracteres, hasheado con bcrypt directamente. Nunca en texto plano.
- Checkbox de consentimiento no premarcado (ver "Cumplimiento legal").
Dependencias de seguridad: `get_usuario_actual`, `solo_admin`.
 
**Duración de sesión**: el JWT de cliente dura **7 días** (`ACCESS_TOKEN_EXPIRE_MINUTES`) y el de admin **12 h** (`ADMIN_TOKEN_EXPIRE_MINUTES`). Sin refresh tokens. El token lleva la versión de sesión del usuario (claim `ver` = `usuarios.token_version`) y `get_usuario_actual` devuelve 401 si no coincide con la de la BD. La versión sube, y todos los tokens anteriores dejan de valer, al cambiar la contraseña, al eliminar la cuenta y con "Cerrar sesión en todos los dispositivos" (`POST /usuarios/me/cerrar-sesiones`). Un token sin `ver` cuenta como versión 0. El logout borra el token del `localStorage`. Si en el futuro hay pagos/datos sensibles → access token corto + refresh token.
 
---
 
## Modelo de datos (basado en FRANJAS de 30 min)
 
- **Usuario**: `id`, `email` (único), `password_hash`, `telefono`, `nombre_completo`, `rol` ('admin' | 'cliente'), `bloqueado` (bool), `inasistencias` (int, almacenado), `consentimiento_version`, `consentimiento_fecha`, **`instagram`** (str, nullable en BD pero obligatorio para reservar — Fase E, en producción), **`token_version`** (int, def. 0: versión de sesión que va en el claim `ver` del JWT; subirla invalida los tokens emitidos antes), **`acepta_comunicaciones`** (bool, def. false), **`comunicaciones_fecha`** (timestamp, nullable), **`ultimo_email_reactivacion`** (timestamp, nullable) — los tres últimos NUEVOS, Fase G.
- **Servicio**: `id`, `nombre`, `duracion_minutos` (**múltiplo de 30, máximo 300 min = 5 h**), `precio`, `activo` (borrado lógico). **Mismos servicios y precios en las dos ciudades.**
- **HorarioPeluquero**: tramos de apertura por día de la semana (varios tramos/día). Horario recurrente semanal, **único para las dos ciudades**.
- **Cita**: `id`, `cliente_id`, `servicio_id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` ('activa' | 'cancelada' | 'no_asistida'), **`ubicacion`** ('alcala' | 'granada', obligatoria — Fase E, en producción, ver "Ubicaciones").
- **FranjaOcupada**: `id`, `cita_id` (FK), `fecha`, `hora`. Fuente de verdad de la disponibilidad. Agenda única: una franja ocupada lo está para las dos ciudades.
- **ExcepcionFecha** (días cerrados): excepción por fecha concreta, con prioridad sobre el horario semanal.
**Tamaño de franja = 30 min**, centralizado en UNA constante (`FRANJA_MINUTOS = 30`) — nunca hardcodear. Nº de franjas = `duracion_minutos / FRANJA_MINUTOS`. Duración máxima = `DURACION_MAX_MINUTOS = 300`.
 
---
 
## REGLA CRÍTICA: no reservas solapadas
 
`UNIQUE (fecha, hora)` en `FranjaOcupada`: cada franja pertenece a una sola cita. Crear cita = insertar la Cita + sus N franjas en UNA transacción; si una franja ya existe → IntegrityError → rollback → `409 Conflict` → el frontend pide recargar. Concurrencia resuelta a nivel de BD.
 
---
 
## Disponibilidad
 
`GET /disponibilidad?fecha=&servicio_id=` devuelve SOLO las horas de inicio válidas: N franjas de 30 min consecutivas libres dentro de un mismo tramo de apertura. Si la fecha es hoy, no se ofrecen horas pasadas. Fuera de la ventana de reserva o en día cerrado → sin horas. **La ciudad no afecta a la disponibilidad** (agenda única).
 
---
 
## Ventana de reserva
 
Ventana rodante de `DIAS_MAX_RESERVA = 30` días: rango [hoy, hoy + 30] con "hoy" en **Europe/Madrid**.
- Backend: `/disponibilidad` vacío fuera de la ventana; `POST /citas` → 422.
- Frontend: calendario con los días fuera de la ventana deshabilitados. Fechas con componentes locales del `Date` (nunca `toISOString()`).
---
 
## Excepciones de horario (días cerrados)
 
Fechas concretas cerradas sin tocar el horario semanal; tienen prioridad sobre él.
- Modelo `ExcepcionFecha` (solo fecha, sin motivo, discriminador `tipo` = "cerrado", extensible a horarios especiales en el futuro).
- Endpoints admin: listar, añadir, eliminar. Añadir con citas activas en esa fecha → 409 con el conteo.
- Endpoint cliente: fechas cerradas dentro de la ventana.
- Fecha cerrada → `/disponibilidad` vacío; `POST /citas` → 422. Chequeo en Europe/Madrid, idéntico en ambos.
---
 
## Ubicaciones: Alcalá la Real / Granada (Fase E — en producción desde el 8-nov-2026)
 
- Dos ciudades: `alcala` ("Alcalá la Real") y `granada` ("Granada"). Constantes:
  - backend: enum `Ubicacion` en `app/models.py` y `NOMBRES_UBICACION` en `app/constants.py`;
  - frontend: `src/constants/ubicaciones.js`.
- Agenda, horario, servicios y precios **únicos** para las dos.
- `POST /citas` recibe `ubicacion` **obligatoria** (422 si falta o no es válida).
- **Alcalá la Real** tiene local fijo: al elegirla se muestra su dirección, `DIRECCION_ALCALA = 'C/Camino Nuevo Nº 11'` (una sola constante).
  - Hoy está solo en `frontend/src/constants/ubicaciones.js`.
  - En la Fase F pasa al backend (`app/constants.py` + un endpoint público sin BD que la sirva al frontend), porque el mensaje de WhatsApp también la usa.
- **Granada** no tiene dirección fija: se muestra un texto indicando que el peluquero contactará por Instagram para concretar.
- La reprogramación **mantiene la ciudad** (igual que el servicio, no se cambia).
- Migraciones (las dos aplicadas en Neon):
  - `e5f6a1b2c3d4` añadió `citas.ubicacion` NOT NULL con backfill `'alcala'` y un DEFAULT temporal para convivir con el código anterior;
  - `f6a1b2c3d4e5` retiró ese DEFAULT.
- Visible en: Mis citas, agenda del admin, avisos de Telegram y resumen diario.
---
 
## Instagram del cliente (Fase E — en producción desde el 8-nov-2026)
 
- **Obligatorio en todas las reservas** (decisión de Molina, que asume el riesgo de que algún cliente no quiera darlo o no tenga Instagram). En BD es nullable (las cuentas existentes no lo tienen), pero `POST /citas` devuelve 422 si al final de la reserva el cliente no tiene Instagram (ni guardado ni enviado en el body).
- Se guarda normalizado (sin `@`, en minúsculas) y validado con las reglas de Instagram: 1–30 caracteres; letras, números, `.` y `_`; sin `..`; no empieza ni acaba en `.`.
- En la reserva aparece **precargado** si ya lo tiene; si lo cambia, se actualiza el perfil. Si se envía en `POST /citas`, se guarda en el perfil **en la misma transacción** que la cita. El `cliente_id` sigue saliendo del token.
- Editable en "Mi cuenta" (`PATCH /usuarios/me`: está en la whitelist; se puede cambiar pero no vaciar).
- Visible para el admin en la agenda y en la pestaña Clientes, como enlace `https://instagram.com/<usuario>`.
- Va en los avisos de Telegram (con enlace), en texto plano, sin `parse_mode` y con la vista previa de enlaces desactivada. Si algún día se usa `parse_mode`, hay que escapar el usuario (`_` y `.` pueden romper el formato).
- RGPD: está incluido en la exportación (`GET /usuarios/me/datos`), se pone a NULL al anonimizar (`DELETE /usuarios/me`) y figura en "datos recogidos" de la política de privacidad como **obligatorio para reservar**, con su finalidad (canal de contacto del peluquero con el cliente). Ojo: pedirlo obligatorio teniendo ya el teléfono choca con el principio de minimización; la justificación la asume el titular.
---
 
## Notificaciones al peluquero (Telegram)
 
Solo al peluquero (nunca al cliente, en V1). `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en variables de entorno; si faltan, no se envía nada.
 
1. **Avisos instantáneos**: envío **síncrono, tras el commit**, con timeout de 3 s (`TELEGRAM_TIMEOUT_SEGUNDOS`). Los fallos se registran sin datos personales ni token y **nunca rompen** la operación. Se avisa cuando un cliente **reserva**, **cancela** (solo si cancela el cliente) o **reprograma** (indicando de → a). Mensaje: nombre, teléfono, servicio, fecha y hora, **ciudad**, **Instagram** (si lo hay) y acción.
2. **Recordatorio diario**: `GET /cron/recordatorio`, llamado por Vercel Cron con schedule `0 20 * * *` (UTC). En Hobby la precisión es de ±59 min: 21:00–21:59 Madrid en invierno y 22:00–22:59 en verano. "Mañana" se calcula en Europe/Madrid. Se envía SIEMPRE: sin citas → "Mañana DD/MM no tienes citas"; con citas → una línea por cita con hora, nombre, **ciudad**, Instagram y **enlace de recordatorio por WhatsApp** (ver punto 3). Entrega "best effort" (posibles duplicados u omisiones).
3. **Recordatorios a clientes por WhatsApp (gratis, semiautomáticos — Fase F)**: en cada línea del resumen diario va un enlace `https://wa.me/<telefono>?text=<mensaje>` (teléfono en formato internacional sin `+`, mensaje URL-encoded). El peluquero lo pulsa, se abre WhatsApp con el mensaje ya escrito y él le da a enviar: la app **no envía nada a los clientes**. Mensaje: saludo con el nombre, "te recuerdo tu cita de mañana DD/MM a las HH:MM", ciudad (+ `DIRECCION_ALCALA` si es Alcalá) y firma "RM Molina Style". Solo el recordatorio, sin promociones. Si el teléfono no es válido, la línea va sin enlace. Si el resumen supera el límite de 4096 caracteres de Telegram, dividirlo en varios mensajes. Nunca usar bots no oficiales de WhatsApp (incumplen sus términos y pueden bloquear el número).
Endpoints `/cron/*`: protegidos con `Authorization: Bearer <CRON_SECRET>` (comparación en tiempo constante; 401 si no coincide; 404 si falta `CRON_SECRET`), con `include_in_schema=False`. La lógica está en `app/tareas/`; los scripts de `scripts/` siguen funcionando por línea de comandos.
 
---
 
## Purga de citas (RGPD)
 
`GET /cron/purga`, diario (`0 3 * * *` UTC). Borra las citas más antiguas que `RETENCION_MESES` (por defecto 24). Idempotente. Aritmética de meses robusta (29 de febrero). El contador de inasistencias está almacenado en `Usuario`, así que la purga no lo altera.
 
---
 
## Email de reactivación "¡Te echamos de menos en RM Molina Style!" (NUEVO — Fase G)
 
Email a clientes que llevan `DIAS_REACTIVACION = 28` días (constante configurable) sin cita.
 
- **Es comunicación comercial (LSSI-CE art. 21)**: solo se envía a clientes con `acepta_comunicaciones = true`.
  - Registro: checkbox **separado** del de privacidad, **no premarcado** ("Quiero recibir por email avisos y novedades de RM").
  - Mi cuenta: interruptor para activarlo o desactivarlo.
  - Se guarda `comunicaciones_fecha` al aceptar.
  - Las cuentas existentes quedan en `false`: no reciben nada hasta que lo activen.
- **Baja en un clic** en cada email: enlace con token firmado (HMAC con `SECRET_KEY` y propósito "baja", sin caducidad corta), sin login, que pone `acepta_comunicaciones = false` y muestra una página de confirmación. Añadir también la cabecera `List-Unsubscribe`.
- **Proveedor**: **Brevo** (plan gratis: 300 emails/día, empresa de la UE). API key en `BREVO_API_KEY`; remitente en `EMAIL_REMITENTE` (p. ej. `hola@rmolinastyle.com`, pendiente de confirmar); reply-to pendiente de confirmar. Autenticar el dominio en Brevo (registros SPF/DKIM/DMARC en Cloudflare). Envío síncrono con timeout; un fallo de un email no para el resto.
- **Cron**: `GET /cron/reactivacion`, diario (p. ej. `0 9 * * *` UTC → 10:00–10:59 Madrid en invierno), protegido con `CRON_SECRET` como los demás. Tope de envíos por ejecución (p. ej. 50) muy por debajo del límite de Brevo.
- **A quién**: rol cliente, no bloqueado, no anonimizado, `acepta_comunicaciones = true`, con al menos una cita pasada no cancelada, cuya última cita fue hace ≥ `DIAS_REACTIVACION` días, **sin citas futuras activas**, y que no haya recibido ya el email desde su última cita (`ultimo_email_reactivacion` es NULL o anterior a la fecha de esa cita). Así recibe **un solo email por periodo de inactividad**, no uno al día. Al enviar, se actualiza `ultimo_email_reactivacion`.
- **Contenido**: texto corto con el nombre, enlace para reservar (`https://rmolinastyle.com`) y enlace de baja. Sin datos de citas.
- RGPD: añadir Brevo como encargado (UE) y la finalidad "comunicaciones comerciales, solo con consentimiento" en la política de privacidad; incluir `acepta_comunicaciones` en la exportación.
---
 
## Cancelación
 
`PATCH /citas/{id}/cancelar`: estado → 'cancelada' y borra sus franjas, en una transacción. Solo dueño o admin. No se cancela una pasada ni una ya cancelada.
 
---
 
## Reprogramación (cambiar fecha/hora sin cancelar)
 
`PATCH /citas/{id}/reprogramar` con body `{fecha, hora_inicio}`. **Mismo servicio y misma ciudad.** Solo dueño o admin, y solo citas activas y futuras.
- Antelación mínima: 24 h respecto a la cita original ("ahora" en Europe/Madrid) → 422.
- El hueco nuevo cumple todas las reglas de reserva (horario, ventana, día cerrado, cliente no bloqueado, sin solape).
- Transacción: borrar franjas viejas + crear nuevas + actualizar la cita. Si el hueco se ocupa a la vez → 409 y la cita queda intacta.
- Errores: 403, 404, 409, 422. Aviso a Telegram ("de … a …").
## Inasistencias y bloqueo
 
- `PATCH /citas/{id}/no-asistida` (solo admin): marca una cita pasada y activa como 'no_asistida'. Marca manual.
- `Usuario.inasistencias` visible para el admin.
- `bloqueado` (controlado por el admin): si está bloqueado, `POST /citas` → 403. El cobro de inasistencias es presencial.
---
 
## Estados de cita y su VISUALIZACIÓN (derivada — no hay "confirmar")
 
- 'activa' y futura → "Reservada" / "Próxima".
- 'activa' y pasada → "Realizada".
- 'no_asistida' → "No asistió".
- 'cancelada' → "Cancelada".
NO usar nunca la etiqueta "Confirmada".
---
 
## Fuera de alcance por ahora
 
- Pagos online (pago presencial).
- Envío automático de WhatsApp o SMS a clientes (de pago). Los recordatorios son semiautomáticos (ver Telegram, punto 3).
- **Reserva como invitado** (futuro próximo, sin diseñar): reservar sin cuenta, con limitaciones (sin historial, sin recordatorios, sin emails). Cuestiones abiertas: datos mínimos (nombre, teléfono, Instagram), cómo cancelar sin cuenta (enlace con token), antiabuso (rate limit por IP / captcha), consentimiento de privacidad en la propia reserva, retención de esos datos y cómo encaja con `Cita.cliente_id`.
- Verificación del teléfono por SMS.
- Tiempo real.
- Horarios especiales por fecha (el modelo `ExcepcionFecha` ya lo permite, sin implementar).
- Horario o servicios distintos por ciudad (no hacen falta: agenda única).
---
 
## Seguridad (OWASP Top 10:2025)
 
- Control de acceso por objeto en cada endpoint (anti-IDOR). Panel admin protegido con `solo_admin` en el backend.
- `cliente_id` se toma del token, nunca del body (anti mass-assignment). Whitelists estrictas en `PATCH /usuarios/me`.
- Validación Pydantic estricta (422). SQLAlchemy ORM parametrizado.
- HTTPS. Backend con cabeceras de seguridad (HSTS, CSP, X-Frame-Options, nosniff, Referrer-Policy). Frontend con cabeceras en `frontend/vercel.json` (HSTS, X-Frame-Options DENY, Referrer-Policy, nosniff, CSP sin `unsafe-inline`). **Nada de scripts inline**: el script del tema está en `public/tema-init.js`. React escapa por defecto; nunca `dangerouslySetInnerHTML`.
- Rate limiting: `/login` y `/registro` estricto por IP (~5/min); `POST /citas` por usuario. En serverless es "best effort".
- No filtrar stack traces (500 genérico). No registrar datos personales, contraseñas ni tokens.
---
 
## Cumplimiento legal (RGPD, LOPDGDD, LSSI-CE — España)
 
**Páginas legales** (públicas, enlazadas desde un footer en TODAS las páginas), con marcadores `[…]` que rellena el titular o un profesional:
- `/aviso-legal`: titular, NIF, dirección, email de contacto.
- `/politica-privacidad`: responsable (el negocio); encargados: **Vercel Inc.** (alojamiento y ejecución, funciones en Frankfurt; empresa de EE. UU. → transferencia internacional, mecanismo pendiente `[…]`), **Neon** (BD, Frankfurt/UE), **Cloudflare** (DNS), **Telegram** (transferencia fuera de la UE), **Brevo** (envío de emails, UE — Fase G); datos recogidos (nombre, email, teléfono, historial de citas, ciudad de la cita, **Instagram, obligatorio para reservar**); finalidades (gestión de reservas y avisos; contacto del peluquero por Instagram/WhatsApp; comunicaciones comerciales **solo con consentimiento**); base legal; plazo de conservación; derechos y cómo ejercerlos; reclamación ante la AEPD.
- `/politica-cookies`: solo almacenamiento técnico (JWT en `localStorage`) → **sin banner de cookies**. Si algún día se añade analítica: banner con aceptar/rechazar al mismo nivel, sin cargar nada antes del consentimiento.
**Consentimiento en el registro**: checkbox NO premarcado con enlace a la política de privacidad; se guarda `consentimiento_version` y `consentimiento_fecha`. La reserva no lleva checkbox (ejecución de contrato).
 
**Comunicaciones comerciales** (Fase G): consentimiento aparte, con checkbox no premarcado e independiente del de privacidad (el registro funciona sin marcarlo). Se puede retirar en Mi cuenta o con el enlace de baja de cada email.
 
**Derechos RGPD (autoservicio)**:
- Exportar: `GET /usuarios/me/datos` (perfil + historial, JSON).
- Suprimir: `DELETE /usuarios/me` → ANONIMIZA (no borra la fila): datos personales sustituidos por valores irreversibles, cuenta inutilizable, citas futuras canceladas. No aplicable a admins.
---
 
## Frontend
 
- Mobile-first y responsiva. Footer en todas las páginas.
- AuthContext (login/logout/usuario+rol, rehidratación vía `/usuarios/me`). Rutas protegidas por rol. Cliente HTTP centralizado con Bearer automático, 401 (logout → login) y 409 ("ese hueco se acaba de ocupar, recarga").
- `VITE_API_URL` = `https://api.rmolinastyle.com` en producción (se lee en build: cambiarla exige redeploy).
- **Dos dashboards**: cliente y admin.
- Pantallas:
  - Login, Registro (nombre, apellidos, teléfono, email, contraseña, consentimiento de privacidad y, aparte y opcional, consentimiento de comunicaciones — Fase G).
  - **Reservar**: **ciudad (Alcalá la Real / Granada)**, mostrando la dirección si es Alcalá o el aviso de contacto por Instagram si es Granada → servicio → calendario (ventana [hoy, hoy+30], días cerrados deshabilitados) → horas válidas → **Instagram, obligatorio** (precargado del perfil, con un texto que explique para qué se usa) → resumen (con ciudad y dirección) + confirmar.
  - Mis citas (con ciudad; cancelar y reprogramar, este último solo si faltan ≥ 24 h).
  - Mi cuenta (nombre, teléfono, **Instagram**, contraseña y, en la Fase G, el interruptor de comunicaciones).
  - Página pública de baja de comunicaciones (Fase G), a la que lleva el enlace de cada email.
  - Panel admin: agenda (con ciudad e Instagram de cada cita), marcar inasistencia, servicios, horario, días cerrados, clientes (con Instagram; bloquear/desbloquear).
- Crear servicio (admin): desplegable de duración de 30 min a 5 h en pasos de 30 min.
- Formato de duración: "30 min", "1 h", "1 h 30 min", "5 h".
### Diseño visual (estética premium, paleta de la marca RM)
- Negro y oro, modo claro y oscuro (manual, por defecto oscuro).
- Cuerpo ~17-18px; inputs y cuerpo nunca por debajo de 16px en móvil. Escala en variables CSS de `theme.css`.
- Logo: imagen RM con fondo transparente. Favicon: monograma "RM" dorado sobre oscuro (SVG + PNG + apple-touch-icon + webmanifest).
- Cormorant Garamond (títulos) + Inter (resto), self-hosted (RGPD).
- Micro-interacciones con mesura, solo `transform`/`opacity`, respetando `prefers-reduced-motion`.
Paleta:
- Oscuro: fondo #0B0B0C, superficie #161618, texto crema #F2ECDD, texto sec. #9A958A.
- Claro: fondo #FBF8F1, superficie #FFFFFF, texto carbón #1A1814, texto sec. #6E665C.
- Oro: principal #D4B35A, brillante #EBC76C, oscuro (sobre claro) #9C7A2A / #B8923A.
- Semánticos: verde #3B6D11 / #EAF3DE, ámbar #854F0B / #FAEEDA, rojo #A32D2D / #FCEBEB.
---
 
## Cómo trabajar (Claude Code)
 
- Plan Mode primero: propón el plan, espera aprobación, luego codifica.
- Fases pequeñas y verificables. Tests pytest por endpoint. Nunca secretos en el código. Si algo no está claro, pregunta antes de inventar.
- Trabaja en la rama `feature/*` que se indique; nunca en `render`.
- Si hay migración Alembic, recuerda que en producción se aplica a mano contra Neon (URL directa) antes de desplegar el código que la usa.
- Antes de ejecutar migraciones o scripts contra una BD (alembic, purga, seed), muestra host, puerto, nombre de la BD y `alembic current`, y espera confirmación. El contenedor local está en `localhost:5434`. Nunca asumas que un Postgres en `localhost` es el de Docker: en el 5432 hay otros.