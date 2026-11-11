# Estado del proyecto — Gestor de Citas Peluquería RM
 
> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo. Última actualización: 11 de noviembre de 2026.
 
## Qué es
 
App web de gestión de citas para una peluquería/barbería real (RM, de Molina), un único peluquero que trabaja en Alcalá la Real y Granada. Stack: FastAPI + React (Vite) + PostgreSQL. Mobile-first. Desarrollador único (Cristian / AceitunoDev). En producción en `rmolinastyle.com` (frontend) y `api.rmolinastyle.com` (API).
 
---
 
## Situación actual (10 de noviembre de 2026)
 
- **Dos formas de despliegue** preparadas en el repo, con el mismo código:
  - **Vercel + Neon**: la de producción. Se usa **a petición de Molina, dueño del negocio**, por coste (~0 €). Guía en `DESPLIEGUE_VERCEL.md`.
  - **Render**: la alternativa, solo como configuración en el repo (`render.yaml` + `DESPLIEGUE_RENDER.md`). **No hay nada desplegado en Render**: se borró el 10 de noviembre de 2026. Para usarlo habría que montarlo **desde cero** con `render.yaml` (Blueprint nuevo) y llevar los datos desde Neon con `pg_dump`/`pg_restore`. La versión que estuvo en producción está en la rama `render` y en el tag `render-v1`.

  Comparación en la sección "Despliegue" del `README.md`. Nunca las dos activas a la vez.
- **Producción en Vercel Hobby + Neon Free desde el 8 de noviembre de 2026** (corte hecho un domingo, con la peluquería cerrada). Verificado: HTTPS, `www` → apex con 308, login de admin y de cliente, datos migrados, reservar/cancelar, recarga sin 404, cabeceras de seguridad, CSP sin errores, `/health` 200, `/cron/recordatorio` sin cabecera → 401. **Confirmado el 10 nov**: el resumen diario de Telegram llega cada noche (el cron de Vercel funciona) y producción se mantiene estable.
- **Fase E (ciudad de la cita + Instagram obligatorio) en producción desde el 8 de noviembre de 2026**: migración `e5f6a1b2c3d4` aplicada a mano en Neon (URL directa) antes del merge — 230 citas rellenadas con `alcala`, ninguna sin ciudad, `CHECK` creado — y merge fast-forward de `feature/ubicacion-instagram` a `main` (`2212f88`). Ver "Despliegue de la Fase E" más abajo.
- **`citas.ubicacion` sin DEFAULT desde el 10 de noviembre de 2026**: migración `f6a1b2c3d4e5` (`ALTER COLUMN ubicacion DROP DEFAULT`) aplicada a mano en Neon (URL directa) y merge fast-forward de `chore/ubicacion-sin-default` a `main` (`fd0f78d`). Antes se probó en Docker el ciclo upgrade → downgrade → upgrade: sin DEFAULT, un `INSERT` sin ciudad falla con `NotNullViolation`; tras el downgrade vuelve a rellenarse con `'alcala'`. `alembic check` sin diferencias. Ahora una cita sin ciudad falla en vez de quedarse en Alcalá sin avisar.
- **Pendiente de confirmar**: reserva de prueba en producción en Alcalá la Real y en Granada (recargando antes la página), con su aviso de Telegram (ciudad + Instagram, sin vista previa del enlace); cancelar las citas de prueba.
- **Render borrado el 10 de noviembre de 2026**: `rm-postgres`, `rm-backend`, `rm-recordatorios` y `rm-frontend` eliminados, y el Blueprint desconectado. Ya no hay rollback a Render.
- **Backups de Neon**:
  - `pg_dump` **semanal** con un script propio que está **fuera del repo** (`backup-rm.ps1`).
  - Cada dump se cifra con RAR5 y `-hp`, que cifra también los nombres de los ficheros. La contraseña está en el gestor de contraseñas.
  - Se guarda una copia fuera del portátil y se conservan los **4 últimos**.
  - Primer backup: 10 de noviembre de 2026.
  - Recuerda que la restauración de Neon Free solo cubre las últimas 6 h, así que estos dumps son la copia real.
- Motivo de la migración: Molina quiere coste ~0 € (Render costaba ~18,50 €/mes). Con Render borrado, el único coste fijo es el dominio (~10 €/año).
- Molina conoce y **asume** el riesgo de que Vercel Hobby es solo para uso no comercial según sus términos.
- **Las cuentas de Vercel y Neon son de Cristian** (misma identidad que su GitHub). Si Vercel actuara por el uso comercial en Hobby, afectaría a la cuenta personal de Cristian y a sus otros proyectos.
### Infraestructura de producción
 
- **Neon**: proyecto `rm-production`, AWS Europe Central 1 (Frankfurt), **Postgres 18** (misma versión que tenía Render). Ojo con los nombres: el **proyecto** se llama `rm-production`, pero la **base de datos** dentro de él es `rm_postgres` (rol `rm_postgres_owner`); es la misma BD de producción. URLs pooled y directa en el gestor de contraseñas. Alembic en **`9d2b7e4a1c63 (head)`** (11 nov 2026). `citas.ubicacion` es NOT NULL y ya **sin DEFAULT**.
- **Vercel backend**: proyecto `aplicacion-web-molina` (raíz `backend/`), dominio `api.rmolinastyle.com` (también responde en `aplicacion-web-molina.vercel.app`). Python 3.14. Variables (solo Production): `DATABASE_URL` (pooled), `DB_NULLPOOL=true`, `SECRET_KEY` (la de Render), `ENVIRONMENT=production`, `ALLOWED_ORIGINS=["https://rmolinastyle.com","https://www.rmolinastyle.com"]` (**array JSON**: el campo es `list[str]` en pydantic-settings), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CRON_SECRET`.
- **Vercel frontend**: proyecto `aplicacion-web-molina-frontend` (raíz `frontend/`), dominios `rmolinastyle.com` (principal) y `www.rmolinastyle.com` (308 al apex). `VITE_API_URL=https://api.rmolinastyle.com`, de tipo **Config** (no sensible: todo lo que lleva `VITE_` acaba en el JS del navegador; nunca poner secretos ahí). `connect-src` de la CSP solo con `https://api.rmolinastyle.com`.
- **Cloudflare**: los 3 registros (`rmolinastyle.com`, `www`, `api`) apuntan a Vercel, en "DNS only" (nube gris; con proxy naranja el rate limiting de `/login` vería la IP de Cloudflare). Sin registros CAA.
### Lecciones del corte
 
- `pg_dump` tiene que ser de versión ≥ que el servidor: con Render en 18, imagen `postgres:18`.
- "SSL connection has been closed unexpectedly" desde Render = IP no permitida (p. ej., VPN activada).
- En PowerShell, las URLs con contraseña se meten con `Read-Host` (pegándolas en el aviso, sin comillas) para que no queden en el historial y el `&` no dé problemas.
- No usar el "agent prompt" que ofrece Neon al crear el proyecto: escribe en `.env` y toca el código.
- Las variables sensibles de Vercel no se pueden pasar a Config: hay que borrarlas y crearlas de nuevo.
### Despliegue de la Fase E (8 nov 2026)

- Orden seguido: migración en Neon → verificación (`citas.ubicacion` NOT NULL con default, `usuarios.instagram` nullable, 230/230 citas en `alcala`, `CHECK ck_cita_ubicacion`) → merge fast-forward a `main` y push → Vercel despliega los dos proyectos.
- La migración es compatible con el código anterior (sus `INSERT` no envían `ubicacion` y la BD pone `'alcala'`), por eso se pudo aplicar antes del merge.
- Ventana de versiones mezcladas (1–2 min): backend nuevo + frontend viejo, o al revés, → `POST /citas` da 422 en los dos sentidos (sin datos corruptos). Una pestaña abierta antes del despliegue ve "No se pudo crear la reserva. Inténtalo de nuevo." hasta que recarga.
- Rollback: *Instant Rollback* en Vercel (el backend anterior funciona con la BD ya migrada). La migración tiene `downgrade`, pero borra las columnas nuevas (perdería ciudades e Instagram).
---
 
## Completado
 
### Backend
1. Configuración y seguridad base: estructura backend/frontend, Alembic, cabeceras de seguridad, CORS, slowapi, `/health`.
2. Modelos: Usuario, Servicio, HorarioPeluquero, Cita, FranjaOcupada (`UNIQUE(fecha, hora)`), ExcepcionFecha.
3. Autenticación: registro (solo clientes), login JWT (7 días), `get_usuario_actual`, `solo_admin`. Los 2 admins ya existen en la BD (seed solo histórico).
4. Servicios (CRUD admin, borrado lógico, reactivar vía `PUT`) y horario con N tramos por día (validación de solapes).
5. Disponibilidad y reserva (`POST /citas` transaccional, 409 ante solape), ventana de reserva de 30 días, días cerrados (ExcepcionFecha).
6. Cancelación, reprogramación (`PATCH /citas/{id}/reprogramar`, mínimo 24 h, transaccional), inasistencias (contador almacenado) y bloqueo.
7. Validación de registro (nombre completo, teléfono España) y gestión de cuenta (`PATCH /usuarios/me`, `PATCH /usuarios/me/password`).
8. Telegram al peluquero: avisos de reserva/cancelación/reprogramación y resumen diario de las citas de mañana.
9. Bloque legal RGPD/LOPDGDD/LSSI-CE: páginas legales con marcadores, footer, consentimiento en el registro (`consentimiento_version`/`consentimiento_fecha`), exportación y anonimización de datos, purga de citas (24 meses).
10. Zona horaria unificada en Europe/Madrid en todos los endpoints (corrigió un bug en producción). `CheckConstraint` de duración de servicio.
11. Migración a Vercel + Neon: `NullPool`/`prepare_threshold=None`, `/health` sin BD, Telegram síncrono tras el commit (timeout 3 s), crons como endpoints `/cron/recordatorio` y `/cron/purga` con `CRON_SECRET` (la purga se programa por primera vez), IP real desde cabeceras de Vercel para el rate limiting, `tzdata`, `backend/vercel.json` (región `fra1`, 2 crons), Python 3.14.
12. **Fase E — ciudad de la cita + Instagram obligatorio**: enum `Ubicacion` (`alcala`/`granada`) y `NOMBRES_UBICACION` en `app/constants.py`; `Cita.ubicacion` (NOT NULL + `CHECK`) y `Usuario.instagram` (nullable); validador único de Instagram en `app/schemas.py` (normaliza sin `@` y en minúsculas; 1–30 caracteres, letras/números/`.`/`_`, sin `..` ni `.` al principio o al final) usado por `POST /citas` y `PATCH /usuarios/me`. `POST /citas` exige ciudad y, si el perfil no tiene Instagram, que llegue en el body (422 si no); el Instagram del body se guarda en el perfil **en la misma transacción** que la cita (un 409 no lo guarda). La reprogramación mantiene la ciudad. `PATCH /usuarios/me` permite cambiar el Instagram pero no vaciarlo. Exportación con Instagram y ciudad; anonimizar pone Instagram a NULL. Telegram: ciudad e Instagram (enlace) en avisos y resumen diario, texto plano sin `parse_mode` y con `link_preview_options.is_disabled` en todos los envíos. **260 tests** en verde.
13. **Retirada del DEFAULT temporal de `citas.ubicacion`** (10 nov 2026): migración `f6a1b2c3d4e5`, con un `downgrade` que lo restaura. El modelo ya no lo tenía. Docker local pasado a `postgres:18`, la misma versión que Neon.
14. **Tope de citas, horario, límites de peticiones y contraseñas** (11 nov 2026):
    - **Tope de citas activas futuras por cliente**: `MAX_CITAS_ACTIVAS = 2` en `app/constants.py`. Al llegar al tope, `POST /citas` devuelve 403. El admin está exento. No cuentan las citas canceladas ni las ya pasadas, tampoco las de hoy a una hora anterior.
    - **Citas que cruzan la medianoche**: `_validar_slot` las rechaza con 422, al crear y al reprogramar, y devuelve la `hora_fin` que usan los dos endpoints.
    - **Límites de peticiones**:
      - por usuario en `PATCH /citas/{id}/cancelar` (10/min) y `PATCH /citas/{id}/reprogramar` (5/min y 20/día);
      - `SlowAPIMiddleware` aplica el límite global (100/min por IP) a las rutas sin límite propio, con `/health` exento.
    - **Contraseñas limitadas a 72 bytes**:
      - en el registro y en la contraseña nueva, más de 72 bytes da 422;
      - `max_length=100` en el login y en la contraseña actual;
      - `verify_password` devuelve `False` en lugar de lanzar `ValueError`.
    - **`ENVIRONMENT`**: es un `Literal` (`development` | `production`) con `production` por defecto. Cualquier otro valor impide arrancar la API.
    - **291 tests** en verde.
15. **Sesiones revocables y sesión de admin de 12 h** (11 nov 2026):
    - **`usuarios.token_version`** (INTEGER NOT NULL, DEFAULT 0): migración `9d2b7e4a1c63`, aplicada en Neon el 11 nov 2026. Pone los admins a 1, así que sus tokens anteriores dejaron de valer al desplegar.
    - **El JWT lleva la versión** en el claim `ver`. `get_usuario_actual` devuelve 401 si no coincide con la de la BD. Un token sin `ver` cuenta como versión 0.
    - **La versión sube**:
      - al cambiar la contraseña (cierra todas las sesiones, incluida la actual);
      - al anonimizar la cuenta;
      - con `POST /usuarios/me/cerrar-sesiones` (204, para cliente y admin).
    - **Caducidad**: admin 12 h (`ADMIN_TOKEN_EXPIRE_MINUTES`, por defecto 720) y cliente 7 días (`ACCESS_TOKEN_EXPIRE_MINUTES`).
    - **303 tests** en verde.
### Frontend
- Fase A: cimientos (axios con interceptores 401/409, AuthContext, rutas por rol).
- Fase B: Login y Registro con estética premium negro/oro, tema claro/oscuro, fuentes self-hosted.
- Fase C: dashboard del cliente (Reservar con calendario propio, Mis citas con cancelar/reprogramar).
- Fase C.extra: Mi cuenta (perfil + contraseña).
- Fase D: panel admin (Agenda, Servicios, Horario con tramos y días cerrados, Clientes).
- Favicon RM completo. Monitor de uptime con BetterStack sobre `/health`.
- Migración: `frontend/vercel.json` (rewrite SPA + cabeceras de seguridad con CSP sin `unsafe-inline`), script del tema en `public/tema-init.js`, política de privacidad con Vercel y Neon.
- **Fase E**: `src/constants/ubicaciones.js` (ciudades, `DIRECCION_ALCALA = 'C/Camino Nuevo Nº 11'` y texto de Granada) y `src/utils/instagram.js`. Reservar: ciudad → servicio → calendario → horas → Instagram → resumen; los **servicios se ven siempre** (con duración y precio) y se pueden elegir tras escoger ciudad; cambiar de ciudad no borra lo ya elegido; Instagram precargado del perfil con texto de para qué se usa. Ciudad en Mis citas (y dirección si es Alcalá); ciudad e Instagram (enlace `noopener noreferrer`) en la agenda y Clientes; Instagram editable en Mi cuenta. Política de privacidad con Instagram (obligatorio para reservar) y ciudad de la cita.
- Reservar muestra el mensaje del backend en los 403: cuenta bloqueada o tope de citas activas.
- Mi cuenta:
  - al cambiar la contraseña se cierra la sesión y se vuelve a `/login` con un aviso;
  - sección "Sesiones" con el botón "Cerrar sesión en todos los dispositivos": pide confirmación con un modal y lleva a `/login` con un aviso.
---
 
## Limitaciones conocidas (aceptadas)
 
- **Vercel Hobby**: uso no comercial según sus términos (riesgo asumido por Molina, en la cuenta personal de Cristian); cron una vez al día con ±59 min de precisión; 1 asiento.
- **Neon Free**: 0,5 GB, 100 CU-hours/mes (si se agotan, la BD se suspende hasta el mes siguiente), restauración solo de las últimas 6 h. Por eso se hace el `pg_dump` semanal cifrado con `backup-rm.ps1` (ver "Situación actual").
- Arranques en frío: la primera petición tras un rato sin tráfico tarda algo más.
- Rate limiting "best effort" (contadores en memoria por instancia).
---
 
## Pendientes menores
 
- Política de privacidad: mecanismo de transferencia de Vercel (`[…]`), y los nuevos marcadores de la Fase E (justificación de pedir Instagram obligatorio —minimización— y transferencia de Meta). Los rellena Molina o un profesional.
- Dependencias: FastAPI 0.115.5 / Starlette / slowapi usan `asyncio.iscoroutinefunction`, deprecado en Python 3.14 (~580 warnings en pytest; se elimina en 3.16). Fase aparte de actualización (en Starlette moderno `HTTP_422_UNPROCESSABLE_ENTITY` pasa a ser `HTTP_422_UNPROCESSABLE_CONTENT`).
- 17 errores previos de `npm run lint`.
- Probar `python scripts/purga_citas.py --dry-run` con Docker levantado.
---
 
## Próximas funciones (rama `feature/*` desde `main`)
 
Se pueden empezar ya en su rama. Todo está decidido con Molina; el detalle técnico está en `CLAUDE.md`. Una fase por rama y por chat. Las migraciones Alembic se aplican a mano en Neon (URL directa) **antes** del merge.
 
### ~~Fase E — Ciudad de la cita + Instagram obligatorio~~ ✅ en producción (8 nov 2026, ver "Completado")
### Fase F — Recordatorios a clientes por WhatsApp (`feature/recordatorio-whatsapp`)
- Gratis y semiautomático: en el resumen diario de Telegram, cada cita lleva un enlace `wa.me` con el mensaje de recordatorio ya escrito. Molina lo pulsa y envía desde su WhatsApp. La app no envía nada a los clientes.
- El mensaje lleva `DIRECCION_ALCALA`, que hoy solo está en el frontend (`src/constants/ubicaciones.js`): **moverla al backend** (p. ej. `app/constants.py` + un endpoint público sin BD que la sirva al frontend) para que siga siendo una sola constante.
- A tener en cuenta: el resumen llega entre las 21:00 y las 22:59 según la época del año. Si a Molina le parece tarde para escribir a clientes, se adelanta el cron (decisión suya).
- Con los enlaces `wa.me` el resumen crece: dividirlo si supera los 4096 caracteres de Telegram. La vista previa de enlaces ya está desactivada.
- Avisar del tope de citas activas al entrar en Reservar (con `GET /citas/mias`), antes de que el cliente recorra todo el flujo.
### Fase G — Email "¡Te echamos de menos!" (`feature/email-reactivacion`)
- Email a clientes con 28 días sin cita, un solo email por periodo de inactividad. Gratis con **Brevo** (300 emails/día, empresa de la UE).
- Es comunicación comercial: **solo a quien dé su consentimiento** (checkbox aparte y no premarcado en el registro + interruptor en Mi cuenta). Las cuentas existentes no reciben nada hasta que lo activen. Baja en un clic en cada email.
- Necesita: cuenta de Brevo, autenticar el dominio (SPF/DKIM/DMARC en Cloudflare; ahora mismo el dominio solo tiene los 3 registros de la web), un cron diario `/cron/reactivacion` y 3 campos nuevos en `Usuario`.
### Datos que tiene que dar Molina
- ~~Dirección exacta del local de Alcalá la Real (Fase E)~~ → dada: C/Camino Nuevo Nº 11.
- Remitente y dirección de respuesta del email, y si quiere retocar el texto (Fase G).
- Rellenar los marcadores `[…]` de las páginas legales, incluido el mecanismo de transferencia de Vercel.
### Futuro próximo — Reserva como invitado (sin diseñar)
Reservar sin cuenta, con limitaciones: sin historial, sin recordatorios y sin emails. Cuestiones abiertas en `CLAUDE.md` ("Fuera de alcance").
 
---
 
## Contratos de backend confirmados (los usa el frontend)
 
**Auth:**
- `POST /login` → `{ access_token, token_type: "bearer" }`.
- `GET /usuarios/me` → `{ id, email, telefono, nombre_completo, rol, instagram }` (`instagram`: `string | null`). Mismo esquema en la respuesta de `PATCH /usuarios/me` y `POST /registro`.
- `PATCH /usuarios/me` → body con al menos uno de `nombre_completo`, `telefono`, `instagram` (`instagram: null` → 422: se cambia, no se vacía). Cualquier otro campo → 422.
- `GET /usuarios`, `GET /usuarios/{id}`, `PATCH /usuarios/{id}/bloquear|desbloquear` (admin) → incluyen `instagram`.
- `GET /usuarios/me/datos` → `perfil.instagram` y `citas[].ubicacion`. `DELETE /usuarios/me` pone `instagram` a NULL y cierra todas las sesiones de la cuenta.
- `PATCH /usuarios/me/password` → 200 `{detail}`. Cierra todas las sesiones, incluida la actual: el token con el que se llama deja de valer y el frontend hace logout.
- `POST /usuarios/me/cerrar-sesiones` → 204, sin cuerpo (cliente y admin). Todos los tokens del usuario, incluido el actual, dejan de valer.
- JWT claims: `sub`, `rol`, `ver`, `exp`. El frontend no decodifica el JWT.
- `POST /registro` → 201 + UsuarioRead (sin token). Email duplicado → 409. Password mínimo 8.
**Citas/servicios:**
- `GET /servicios` → solo activos; `precio` como string decimal ("25.50"). `?incluir_inactivos=true` solo admin. Requiere token.
- `GET /disponibilidad?fecha=YYYY-MM-DD&servicio_id=int` → `{fecha, servicio_id, horas_disponibles: ["HH:MM", ...]}`.
- `POST /citas` → body `{servicio_id, fecha, hora_inicio, ubicacion, instagram?}`. `ubicacion` (`"alcala"` | `"granada"`) obligatoria; `instagram` obligatorio si el perfil aún no lo tiene (si llega, se guarda en el perfil). Errores: 403, 409, 422 (también si falta ciudad o Instagram).
- `GET /citas/mias` → `[{id, cliente_id, servicio_id, fecha, hora_inicio, hora_fin, estado, ubicacion}]` (solo `servicio_id`: cruzar con `/servicios`). Todas las respuestas de cita (`CitaRead`) incluyen `ubicacion`.
- `PATCH /citas/{id}/cancelar`, `PATCH /citas/{id}/reprogramar` (body `{fecha, hora_inicio}`; `ubicacion` → 422, la cita mantiene su ciudad), `PATCH /citas/{id}/no-asistida`.
- `GET /citas?fecha=YYYY-MM-DD` (admin, agenda del día).
- `GET /horario` → `[{id, dia_semana (0=lunes…6=domingo), hora_apertura, hora_cierre}]`.
- **Zona horaria: Europe/Madrid.** En el frontend, fechas con componentes locales del `Date`, nunca `toISOString()`.
---
 
## Decisiones acordadas
 
- Estética premium negro/oro, modo claro/oscuro manual (por defecto oscuro). Mobile-first. Logo como imagen.
- Estados de cita derivados (no hay "Confirmada"). Calendario propio; solo horas válidas del servicio.
- Fuentes self-hosted (RGPD). Email no editable (es el login). Sin banner de cookies (solo almacenamiento técnico).
- Avisos al peluquero por Telegram. Recordatorios a clientes por WhatsApp, enviados a mano por Molina desde los enlaces del resumen (gratis).
- Instagram obligatorio para reservar (decisión de Molina). Emails comerciales solo con consentimiento explícito.
- JavaScript (no TypeScript), axios, JWT en `localStorage`, CSS Modules + variables CSS, sin frameworks de UI.
- Producción en Vercel Hobby + Neon Free a petición de Molina (coste ~0), asumiendo sus limitaciones. Cuentas de Vercel y Neon a nombre de Cristian. Render se mantiene en el repo como segunda forma de despliegue (`render.yaml` + `DESPLIEGUE_RENDER.md`), pero sin nada desplegado: se borró el 10 nov 2026.
- Dominio principal: apex `rmolinastyle.com`; `www` redirige con 308.
- Documentos del proyecto de Claude (chat) actualizados a mano: al cerrar cada fase se suben las versiones del repo.
## Herramienta de desarrollo — compartir en local
 
Túnel de Cloudflare con el proxy de Vite (`/api` → `localhost:8000`): `cloudflared tunnel --url http://localhost:5173` (si da errores QUIC: `--protocol http2` o desactivar la VPN). Solo para demos cortas; parar el túnel al terminar.

## Base de datos local (desarrollo)

- La BD de desarrollo es **solo la de Docker** (`peluqueria-db`, **`postgres:18`, la misma versión que Neon**, **`localhost:5434`** desde el 11 nov (antes 5432), BD `peluqueria`). El volumen se monta en `/var/lib/postgresql`, porque la imagen 18 ya no usa `/var/lib/postgresql/data`.
- El 10 nov se recreó vacía al pasar de la 16 a la 18 y se migró a `f6a1b2c3d4e5`; el 11 nov, a `9d2b7e4a1c63` (head). El **admin local** se creó registrándose desde la web y después con `UPDATE usuarios SET rol='admin' WHERE email='…'`. `seed.py` también sirve, pero necesita las variables `ADMIN1_*`/`ADMIN2_*` en `.env`. Servicios, horario y clientes se crean desde la web.
- ⚠️ En el equipo hay **otros dos Postgres en el 5432**. Por eso el contenedor se publica en el 5434:
  - **PostgreSQL 18 nativo de Windows**: su servicio (`postgresql-x64-18`) está **parado y deshabilitado (Disabled)** desde el 10 nov; antes estaba en Automatic y volvía a arrancar tras cada reinicio.
  - **Contenedor `db` de otro proyecto, en el Docker nativo de la distro Ubuntu (WSL)**, con `restart=always`. Arranca con WSL (y Docker Desktop arranca Ubuntu). `wslrelay` lo expone en `127.0.0.1:5432`.
- Antes de migraciones o scripts (alembic, purga, seed), comprobar:
  - el puerto de la URL (5434);
  - con `select version()`, a qué servidor se conecta (Docker = "… on x86_64-pc-linux-gnu"; Windows = "… on x86_64-windows"). Como todos son 18, la versión no sirve para distinguirlos;
  - `alembic current`, contrastado con `docker exec peluqueria-db psql -U peluqueria -d peluqueria -c "select version_num from alembic_version"`.
- Esa BD de Windows se migró por error a `e5f6a1b2c3d4` el 8 nov (antes estaba en `c70da527d6e9`; solo cambios de esquema, sin pérdida de datos). No se usa.
- Para pruebas locales, vaciar `TELEGRAM_CHAT_ID` (o poner uno propio) para no avisar a Molina con reservas de prueba.
 
---
 
## Siguiente paso
 
1. ~~Confirmar el resumen diario de Telegram con el cron de Vercel~~ ✅ 10 nov 2026.
2. Reserva de prueba en producción en Alcalá la Real y en Granada (recargando antes la página), ciudad en Mis citas y en la agenda, aviso de Telegram con ciudad e Instagram sin vista previa del enlace; cancelar las citas de prueba.
3. ~~Retirar el `DEFAULT 'alcala'` de `citas.ubicacion`~~ ✅ en producción el 10 nov 2026 (migración `f6a1b2c3d4e5`).
4. ~~Borrar Render~~ ✅ 10 nov 2026 (servicios borrados y Blueprint desconectado). La configuración (`render.yaml`, `DESPLIEGUE_RENDER.md`) se queda en el repo como forma de despliegue alternativa.
5. ~~`pg_dump` periódico de Neon~~ ✅ semanal con `backup-rm.ps1` desde el 10 nov 2026.
6. **Fase F** en un chat nuevo (incluye mover `DIRECCION_ALCALA` al backend) → Fase G. Ir cerrando pendientes menores (dependencias, lint, política de privacidad).