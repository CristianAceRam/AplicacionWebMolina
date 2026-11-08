# Estado del proyecto — Gestor de Citas Peluquería RM
 
> Documento de continuidad. Léelo junto a `CLAUDE.md` para retomar el proyecto en cualquier chat nuevo. Última actualización: 8 de noviembre de 2026.
 
## Qué es
 
App web de gestión de citas para una peluquería/barbería real (RM, de Molina), un único peluquero que trabaja en Alcalá la Real y Granada. Stack: FastAPI + React (Vite) + PostgreSQL. Mobile-first. Desarrollador único (Cristian / AceitunoDev). En producción en `rmolinastyle.com` (frontend) y `api.rmolinastyle.com` (API).
 
---
 
## Situación actual (8 de noviembre de 2026)
 
- **Producción en Vercel Hobby + Neon Free desde el 8 de noviembre de 2026** (corte hecho un domingo, con la peluquería cerrada). Verificado: HTTPS, `www` → apex con 308, login de admin y de cliente, datos migrados, reservar/cancelar, recarga sin 404, cabeceras de seguridad, CSP sin errores, `/health` 200, `/cron/recordatorio` sin cabecera → 401.
- **Pendiente de confirmar**:
  - Que a Molina le llegaron los avisos de Telegram de la reserva y cancelación de prueba del corte. Si no: revisar los logs del backend en Vercel y que `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` sean idénticos a los de Render (sin espacios), y redeploy.
  - Que el resumen diario de la noche del 8 de noviembre (21:00–21:59) le llega → el cron de Vercel funciona.
- **Render**: `rm-backend` y `rm-recordatorios` suspendidos; `rm-postgres` y `rm-frontend` siguen existiendo como rollback. **Borrar todo hacia el martes o miércoles (10–11 nov)** si va estable, empezando por la Postgres (datos personales, RGPD). Después, comprobar en *Billing* de Render que no queda ninguna suscripción activa.
- Motivo de la migración: Molina quiere coste ~0 € (Render costaba ~18,50 €/mes). Tras borrar Render, el único coste fijo es el dominio (~10 €/año).
- Molina conoce y **asume** el riesgo de que Vercel Hobby es solo para uso no comercial según sus términos.
- **Las cuentas de Vercel y Neon son de Cristian** (misma identidad que su GitHub). Si Vercel actuara por el uso comercial en Hobby, afectaría a la cuenta personal de Cristian y a sus otros proyectos.
### Infraestructura de producción
 
- **Neon**: proyecto `rm-production`, AWS Europe Central 1 (Frankfurt), **Postgres 18** (misma versión que tenía Render). URLs pooled y directa en el gestor de contraseñas. Alembic en `d4e5f6a1b2c3 (head)`.
- **Vercel backend**: proyecto `aplicacion-web-molina` (raíz `backend/`), dominio `api.rmolinastyle.com` (también responde en `aplicacion-web-molina.vercel.app`). Python 3.14. Variables (solo Production): `DATABASE_URL` (pooled), `DB_NULLPOOL=true`, `SECRET_KEY` (la de Render), `ENVIRONMENT=production`, `ALLOWED_ORIGINS=["https://rmolinastyle.com","https://www.rmolinastyle.com"]` (**array JSON**: el campo es `list[str]` en pydantic-settings), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CRON_SECRET`.
- **Vercel frontend**: proyecto `aplicacion-web-molina-frontend` (raíz `frontend/`), dominios `rmolinastyle.com` (principal) y `www.rmolinastyle.com` (308 al apex). `VITE_API_URL=https://api.rmolinastyle.com`, de tipo **Config** (no sensible: todo lo que lleva `VITE_` acaba en el JS del navegador; nunca poner secretos ahí). `connect-src` de la CSP solo con `https://api.rmolinastyle.com`.
- **Cloudflare**: los 3 registros (`rmolinastyle.com`, `www`, `api`) apuntan a Vercel, en "DNS only" (nube gris; con proxy naranja el rate limiting de `/login` vería la IP de Cloudflare). Sin registros CAA.
### Rollback (mientras exista Render)
 
1. En Cloudflare, restaurar los CNAME de Render:
   - `api` → `rm-backend-z7zb.onrender.com`
   - `rmolinastyle.com` → `rm-frontend-4wr6.onrender.com`
   - `www` → `rm-frontend-4wr6.onrender.com`
2. Reanudar `rm-backend` y `rm-recordatorios` en Render; quitar `CRON_SECRET` en Vercel para no duplicar el resumen.
3. Ojo: lo escrito en Neon después del corte no está en Render. Haría falta el dump inverso (Neon URL directa → Render, imagen `postgres:18`, añadiendo la IP propia en *PostgreSQL Inbound IP Rules* de `rm-postgres`).
### Lecciones del corte
 
- `pg_dump` tiene que ser de versión ≥ que el servidor: con Render en 18, imagen `postgres:18`.
- "SSL connection has been closed unexpectedly" desde Render = IP no permitida (p. ej., VPN activada).
- En PowerShell, las URLs con contraseña se meten con `Read-Host` (pegándolas en el aviso, sin comillas) para que no queden en el historial y el `&` no dé problemas.
- No usar el "agent prompt" que ofrece Neon al crear el proyecto: escribe en `.env` y toca el código.
- Las variables sensibles de Vercel no se pueden pasar a Config: hay que borrarlas y crearlas de nuevo.
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
### Frontend
- Fase A: cimientos (axios con interceptores 401/409, AuthContext, rutas por rol).
- Fase B: Login y Registro con estética premium negro/oro, tema claro/oscuro, fuentes self-hosted.
- Fase C: dashboard del cliente (Reservar con calendario propio, Mis citas con cancelar/reprogramar).
- Fase C.extra: Mi cuenta (perfil + contraseña).
- Fase D: panel admin (Agenda, Servicios, Horario con tramos y días cerrados, Clientes).
- Favicon RM completo. Monitor de uptime con BetterStack sobre `/health`.
- Migración: `frontend/vercel.json` (rewrite SPA + cabeceras de seguridad con CSP sin `unsafe-inline`), script del tema en `public/tema-init.js`, política de privacidad con Vercel y Neon.
---
 
## Limitaciones conocidas (aceptadas)
 
- **Vercel Hobby**: uso no comercial según sus términos (riesgo asumido por Molina, en la cuenta personal de Cristian); cron una vez al día con ±59 min de precisión; 1 asiento.
- **Neon Free**: 0,5 GB, 100 CU-hours/mes (si se agotan, la BD se suspende hasta el mes siguiente), restauración solo de las últimas 6 h → **hacer `pg_dump` manual periódico** (con la URL directa, guardado cifrado; ya no hay backups gestionados como en Render).
- Arranques en frío: la primera petición tras un rato sin tráfico tarda algo más.
- Rate limiting "best effort" (contadores en memoria por instancia).
---
 
## Pendientes menores
 
- **Borrar Render** (10–11 nov si todo va estable): Postgres primero, luego `rm-backend`, `rm-recordatorios` y `rm-frontend`. Comprobar *Billing*.
- **Montar el `pg_dump` periódico de Neon** (frecuencia y dónde guardarlo cifrado, por decidir).
- **Corregir `DESPLIEGUE_VERCEL.md`** en el repo: Render tenía Postgres **18** (no 16) → imagen `postgres:18`; la cuenta de Vercel es la de Cristian; suspender `rm-recordatorios` al principio del corte; `VITE_API_URL` de tipo Config. Convertirlo en documentación de la producción actual más que en runbook de migración.
- Política de privacidad: mecanismo de transferencia de Vercel (`[…]`), lo rellena Molina o un profesional.
- `passlib` no tiene mantenimiento: cambiar algún día por `bcrypt` directamente o por `pwdlib`.
- 17 errores previos de `npm run lint`.
- Probar `python scripts/purga_citas.py --dry-run` con Docker levantado.
---
 
## Próximas funciones (rama `feature/*` desde `main`)
 
Se pueden empezar ya en su rama; **el merge a `main` (= despliegue a producción) cuando Vercel lleve unos días estable**. Todo está decidido con Molina; el detalle técnico está en `CLAUDE.md`. Una fase por rama y por chat. Las migraciones Alembic se aplican a mano en Neon (URL directa) **antes** del merge.
 
### Fase E — Ciudad de la cita + Instagram obligatorio (`feature/ubicacion-instagram`)
- Elegir ciudad al reservar: **Alcalá la Real** (se muestra la dirección del local) o **Granada** (sin dirección fija: el peluquero contacta por Instagram). Agenda, horario, servicios y precios únicos para las dos.
- **Instagram obligatorio en todas las reservas** (decisión y riesgo de Molina). Se guarda en el perfil (`Usuario.instagram`), se precarga en la siguiente reserva y se edita en Mi cuenta. Visible en la agenda y en Clientes.
- Ciudad guardada en la cita (`Cita.ubicacion`), visible en Mis citas, la agenda, los avisos de Telegram y el resumen diario. La reprogramación mantiene la ciudad.
- Migración Alembic: `usuario.instagram` (nullable) + `cita.ubicacion` (NOT NULL, backfill `'alcala'`). Se aplica a mano en Neon antes de desplegar.
- RGPD: Instagram en la exportación, a NULL al anonimizar, y en la política de privacidad como obligatorio para reservar.
### Fase F — Recordatorios a clientes por WhatsApp (`feature/recordatorio-whatsapp`)
- Gratis y semiautomático: en el resumen diario de Telegram, cada cita lleva un enlace `wa.me` con el mensaje de recordatorio ya escrito. Molina lo pulsa y envía desde su WhatsApp. La app no envía nada a los clientes.
- A tener en cuenta: el resumen llega entre las 21:00 y las 22:59 según la época del año. Si a Molina le parece tarde para escribir a clientes, se adelanta el cron (decisión suya).
### Fase G — Email "¡Te echamos de menos!" (`feature/email-reactivacion`)
- Email a clientes con 28 días sin cita, un solo email por periodo de inactividad. Gratis con **Brevo** (300 emails/día, empresa de la UE).
- Es comunicación comercial: **solo a quien dé su consentimiento** (checkbox aparte y no premarcado en el registro + interruptor en Mi cuenta). Las cuentas existentes no reciben nada hasta que lo activen. Baja en un clic en cada email.
- Necesita: cuenta de Brevo, autenticar el dominio (SPF/DKIM/DMARC en Cloudflare; ahora mismo el dominio solo tiene los 3 registros de la web), un cron diario `/cron/reactivacion` y 3 campos nuevos en `Usuario`.
### Datos que tiene que dar Molina
- Dirección exacta del local de Alcalá la Real (Fase E).
- Remitente y dirección de respuesta del email, y si quiere retocar el texto (Fase G).
- Rellenar los marcadores `[…]` de las páginas legales, incluido el mecanismo de transferencia de Vercel.
### Futuro próximo — Reserva como invitado (sin diseñar)
Reservar sin cuenta, con limitaciones: sin historial, sin recordatorios y sin emails. Cuestiones abiertas en `CLAUDE.md` ("Fuera de alcance").
 
---
 
## Contratos de backend confirmados (los usa el frontend)
 
**Auth:**
- `POST /login` → `{ access_token, token_type: "bearer" }`.
- `GET /usuarios/me` → `{ id, email, telefono, nombre_completo, rol }` (Fase E añadirá `instagram`).
- JWT claims: `sub`, `rol`, `exp`. El frontend no decodifica el JWT.
- `POST /registro` → 201 + UsuarioRead (sin token). Email duplicado → 409. Password mínimo 8.
**Citas/servicios:**
- `GET /servicios` → solo activos; `precio` como string decimal ("25.50"). `?incluir_inactivos=true` solo admin. Requiere token.
- `GET /disponibilidad?fecha=YYYY-MM-DD&servicio_id=int` → `{fecha, servicio_id, horas_disponibles: ["HH:MM", ...]}`.
- `POST /citas` → body `{servicio_id, fecha, hora_inicio}` (Fase E añadirá `ubicacion` obligatoria e `instagram`, obligatorio si el perfil aún no lo tiene). Errores: 403, 409, 422.
- `GET /citas/mias` → `[{id, cliente_id, servicio_id, fecha, hora_inicio, hora_fin, estado}]` (solo `servicio_id`: cruzar con `/servicios`).
- `PATCH /citas/{id}/cancelar`, `PATCH /citas/{id}/reprogramar`, `PATCH /citas/{id}/no-asistida`.
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
- Producción en Vercel Hobby + Neon Free a petición de Molina (coste ~0), asumiendo sus limitaciones. Cuentas de Vercel y Neon a nombre de Cristian.
- Dominio principal: apex `rmolinastyle.com`; `www` redirige con 308.
## Herramienta de desarrollo — compartir en local
 
Túnel de Cloudflare con el proxy de Vite (`/api` → `localhost:8000`): `cloudflared tunnel --url http://localhost:5173` (si da errores QUIC: `--protocol http2` o desactivar la VPN). Solo para demos cortas; parar el túnel al terminar.
 
---
 
## Siguiente paso
 
1. Confirmar con Molina los avisos de Telegram del corte y el resumen de la noche del 8 de noviembre.
2. **Fase E** (`feature/ubicacion-instagram`) en un chat nuevo, con su prompt de Plan Mode. Merge a `main` cuando Vercel lleve unos días estable (y tras aplicar la migración en Neon).
3. Hacia el 10–11 de noviembre: borrar Render.
4. Después: Fase F → Fase G. Ir cerrando pendientes menores (`DESPLIEGUE_VERCEL.md`, `pg_dump` periódico).