# Despliegue en Vercel + Neon — Gestor de Citas RM

> **Documentación de la producción actual**: **Vercel Hobby** (2 proyectos) + **Neon Free**, todo en **Frankfurt**, en producción desde el 8 de noviembre de 2026. Frontend en `rmolinastyle.com` y API en `api.rmolinastyle.com`. **Las cuentas de Vercel y Neon son de Cristian.**
>
> **Es una de las dos formas de despliegue del proyecto, y la que se usa en producción.** Se eligió **a petición del dueño del negocio (el peluquero)**, para que el coste fuera prácticamente cero. La otra forma, Render, sigue preparada como alternativa: [`render.yaml`](../render.yaml) y [`DESPLIEGUE_RENDER.md`](DESPLIEGUE_RENDER.md). La comparación está en la sección "Despliegue" del [`README.md`](../README.md).
>
> §6 y §7 son el runbook de la migración desde Render y se conservan como **histórico**.
>
> **Render, después del corte.** Los servicios de Render estuvieron suspendidos como rollback y **se borraron el 10 de noviembre de 2026**. `render.yaml`, `seed.py` y `DESPLIEGUE_RENDER.md` siguen en el repo como forma de despliegue alternativa. El commit previo a la migración está etiquetado como **`render-v1`**.

---

## 1. Arquitectura

| Pieza | Dónde | Detalles |
|---|---|---|
| Frontend | Proyecto Vercel, Root Directory `frontend/` | Static site Vite (`npm run build` → `dist/`). Rewrite SPA y cabeceras de seguridad en [`frontend/vercel.json`](../frontend/vercel.json). |
| Backend | Proyecto Vercel, Root Directory `backend/` | FastAPI en el runtime de Python de Vercel. La app (`app` en `app/main.py`) se detecta sola. Región `fra1` y crons en [`backend/vercel.json`](../backend/vercel.json). Python fijado en `backend/.python-version`. |
| Base de datos | Neon Free, región AWS Europe Central (Frankfurt, `eu-central-1`) | La app usa la URL **pooled** (`-pooler`) con `DB_NULLPOOL=true`. Migraciones y dumps, con la URL **directa**. |
| Crons | Vercel Cron (proyecto backend) | `GET /cron/recordatorio` y `GET /cron/purga`, protegidos con `CRON_SECRET`. |

Neon da dos cadenas de conexión para la misma BD:
- **Pooled**: el host lleva `-pooler` (`ep-xxxx-pooler.eu-central-1.aws.neon.tech`). Pasa por PgBouncer en modo transacción → **la usa la app**.
- **Directa**: el mismo host sin `-pooler`. **Para `alembic`, `pg_dump` y `pg_restore`** (usan sentencias que el pooler en modo transacción no admite).

Ambas deben llevar `?sslmode=require` (Neon la incluye; si añade `&channel_binding=require` también vale). El backend convierte `postgresql://` a `postgresql+psycopg://` automáticamente.

---

## 2. Variables de entorno (sin valores)

### Proyecto backend (Vercel → Settings → Environment Variables, entorno *Production*)

| Variable | Obligatoria | Notas |
|---|---|---|
| `DATABASE_URL` | ✅ | URL **pooled** de Neon (host con `-pooler`, `?sslmode=require`). |
| `DB_NULLPOOL` | ✅ | `true`. Sin conexiones ociosas entre peticiones → Neon escala a cero y no consume CU-hours de más. |
| `SECRET_KEY` | ✅ | Es la misma que tenía Render (copiada en el corte). Si se cambia, todas las sesiones abiertas caducan y todo el mundo tiene que volver a iniciar sesión. |
| `ENVIRONMENT` | ✅ | `production` (desactiva `/docs` y `/openapi.json`, activa HSTS). |
| `ALLOWED_ORIGINS` | ✅ | Array JSON. Definitivo: `["https://rmolinastyle.com","https://www.rmolinastyle.com"]`. Durante las pruebas, añade la URL `.vercel.app` del frontend (ver §6). |
| `TELEGRAM_BOT_TOKEN` | ✅ | Token del bot de Telegram. |
| `TELEGRAM_CHAT_ID` | ✅ | Chat del peluquero, que es quien recibe los avisos y el resumen diario. |
| `CRON_SECRET` | ✅ | Ver §4. Sin ella los endpoints `/cron/*` responden 404 (desactivados). |
| `ALGORITHM` | | Por defecto `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Por defecto `10080` (7 días). |
| `RETENCION_MESES` | | Por defecto `24` (purga RGPD). |
| `VERCEL` | — | **La pone Vercel sola** (`1`). El backend la usa para tomar la IP del cliente de las cabeceras del edge de Vercel (rate limiting). No hay que crearla. |
| `ADMIN1_*`, `ADMIN2_*` | — | **No hacen falta**: no hay seed; los admins llegan con el dump de datos. |

### Proyecto frontend

| Variable | Notas |
|---|---|
| `VITE_API_URL` | `https://api.rmolinastyle.com`, de tipo **Config**. No es sensible: todo lo que lleva `VITE_` acaba en el JS del navegador, así que nunca se ponen secretos ahí. Las variables sensibles no se pueden pasar a Config: hay que borrarlas y crearlas de nuevo. Se lee **en build**: tras cambiarla hay que redesplegar. |

---

## 3. Migraciones (manuales)

Vercel no tiene paso de pre-deploy y la app **no** migra al arrancar. Cuando haya una migración nueva, ejecútala **a mano desde tu equipo** contra la URL **directa** de Neon (sin `-pooler`), **antes** de desplegar el código que la necesita:

PowerShell (desde `backend/`, con el venv activado):

```powershell
# URL DIRECTA de Neon (sin -pooler, con ?sslmode=require). Con Read-Host no queda en el historial.
$env:DATABASE_URL = Read-Host "URL directa de Neon"
alembic current          # confirma la revisión antes de migrar
alembic upgrade head
alembic current          # debe mostrar la nueva head
Remove-Item Env:DATABASE_URL   # o cierra la terminal
```

bash:

```bash
cd backend
read -rsp "URL directa de Neon: " DATABASE_URL && export DATABASE_URL
alembic current && alembic upgrade head && alembic current
unset DATABASE_URL
```

- **Confirma a qué BD apuntas antes de migrar.** El host no debe llevar `-pooler` y `alembic current` debe dar la revisión que esperas. Si no cuadra, para.
- La variable del shell tiene prioridad sobre tu `backend/.env`, que solo aporta el resto (p. ej. `SECRET_KEY`). Quítala al terminar: si no, cualquier `alembic` o `seed.py` posterior en esa terminal irá contra producción.
- Head actual: **`f6a1b2c3d4e5`** (aplicada en Neon el 10 de noviembre de 2026).
- **Si la migración se aplica antes del merge**, tiene que ser compatible con el código antiguo. Un ejemplo es el `server_default` temporal de la Fase E: rellenaba la columna nueva mientras el código antiguo no la enviaba, y se retiró en una migración posterior.
- Recordatorio (ver `ESTADO_PROYECTO.md`): si una migración **endurece** una restricción (`CHECK`, `UNIQUE`…), corrige antes los datos que la incumplan.
- **No hace falta `seed.py`**: los dos admins vienen en los datos migrados desde Render.

---

## 4. Crons

Definidos en [`backend/vercel.json`](../backend/vercel.json) (horas en **UTC**):

| Ruta | Schedule | Qué hace |
|---|---|---|
| `/cron/recordatorio` | `0 20 * * *` | Resumen de las citas de mañana al peluquero por Telegram ("mañana" calculado en Europe/Madrid). |
| `/cron/purga` | `0 3 * * *` | Purga RGPD de citas anteriores a `RETENCION_MESES`. |

- **Precisión en Hobby: ±59 min dentro de la hora.** `0 20` UTC llega entre las **22:00 y las 22:59** de Madrid en verano (CEST) y entre las **21:00 y las 21:59** en invierno (CET).
- Vercel solo ejecuta crons en el deployment de **producción**, **no reintenta** si fallan y la entrega es "best effort" (muy rara vez puede saltarse una ejecución o duplicarla). Las dos tareas son seguras ante duplicados: la purga es idempotente y el recordatorio, como mucho, se recibiría dos veces.
- Vercel envía `Authorization: Bearer <CRON_SECRET>` automáticamente. El backend lo compara en tiempo constante: **401** si no coincide; **404** si `CRON_SECRET` no está definida (desactivados).

**Generar `CRON_SECRET`:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Pégalo en Vercel **sin espacios ni saltos de línea** al final.

**Lanzarlos a mano** (desde el panel: proyecto backend → Settings → Cron Jobs → *Run*, o con curl):

```bash
curl -i -H "Authorization: Bearer <CRON_SECRET>" https://api.rmolinastyle.com/cron/recordatorio
curl -i -H "Authorization: Bearer <CRON_SECRET>" https://api.rmolinastyle.com/cron/purga
```

⚠️ El recordatorio **envía de verdad** el mensaje al peluquero y la purga **borra de verdad**. Respuestas: `{"ok": true, "enviado": true|false}` y `{"ok": true, "purgadas": N}` (sin datos personales).

Los scripts siguen funcionando por CLI (desde `backend/`): `python scripts/recordatorio_diario.py` y `python scripts/purga_citas.py [--dry-run]`.

---

## 5. Configurar los proyectos en Vercel

### Backend
1. *Add New → Project* → importa el repo → **Root Directory: `backend`**. Vercel detecta FastAPI y `requirements.txt`; no hace falta comando de build ni de arranque.
2. Variables de §2 (de momento **sin** `CRON_SECRET` ni Telegram reales).
3. Deploy. Comprueba `https://<proyecto-backend>.vercel.app/health` → `{"status":"ok"}` (no toca la BD).
4. En *Settings → Cron Jobs* deben aparecer los 2 crons.

### Frontend
1. *Add New → Project* → mismo repo → **Root Directory: `frontend`**, preset **Vite** (build `npm run build`, output `dist`).
2. `VITE_API_URL` (§2).
3. Deploy.

### CSP y URLs `.vercel.app`
En producción, `connect-src` en [`frontend/vercel.json`](../frontend/vercel.json) solo tiene `https://api.rmolinastyle.com`:

```
connect-src https://api.rmolinastyle.com
```

- **Para pruebas** contra la URL `.vercel.app` del backend:
  1. Añade a `connect-src` la URL **exacta** de ese backend (`https://<proyecto>.vercel.app`, la que aparece en *Domains* del proyecto).
  2. Haz las pruebas.
  3. **Quítala después** (con su commit).
- **Nunca** un comodín `*.vercel.app`: permitiría al frontend conectar con cualquier proyecto de Vercel de cualquier persona.

---

## 6. Pruebas antes del corte (histórico, 8 nov 2026)

Objetivo: verificar el stack Vercel + Neon de punta a punta **sin afectar a producción** (que sigue en Render).

1. **Datos en Neon**: restaura un dump de Render (§7, pasos 1–3) o usa datos de prueba.
2. **Backend**: `ALLOWED_ORIGINS` = los dominios definitivos **más** la URL `.vercel.app` del frontend, p. ej. `["https://rmolinastyle.com","https://www.rmolinastyle.com","https://<proyecto-frontend>.vercel.app"]`.
3. **Frontend**: `VITE_API_URL` = `https://<proyecto-backend>.vercel.app` y la URL exacta del backend añadida a `connect-src` (§5). Redeploy.
4. **Sin `CRON_SECRET` y sin Telegram reales** en Vercel: si no, el peluquero recibiría avisos de reservas de prueba y **dos recordatorios** cada noche (el de Render y el de Vercel). Si quieres probar Telegram, usa un `TELEGRAM_CHAT_ID` tuyo.
5. Prueba en `https://<proyecto-frontend>.vercel.app`: registro/login, reservar, cancelar, reprogramar, panel admin, recarga en `/admin` y `/mi-cuenta` (sin 404), exportar datos en "Mi cuenta", modo claro/oscuro sin parpadeo. Consola del navegador **sin violaciones de CSP**.
6. Cabeceras: `curl -I https://<proyecto-frontend>.vercel.app` (HSTS, CSP, X-Frame-Options, nosniff, Referrer-Policy).

---

## 7. Corte (histórico, 8 nov 2026)

Hazlo en una franja tranquila (p. ej. por la noche).

1. **Congela escrituras en Render**: suspende `rm-backend` para que no entren reservas durante el dump. Suspende también, **ya al principio**, el cron `rm-recordatorios`, para evitar recordatorios duplicados.
2. **Dump de Render** (la BD tiene `ipAllowList: []`: añade tu IP temporalmente en el panel de `rm-postgres` y quítala al terminar). Usa un `pg_dump` de versión ≥ a la del servidor (18); p. ej. con Docker:
   ```bash
   docker run --rm -v "$PWD:/w" postgres:18 pg_dump --format=custom --no-owner --no-acl \
     --dbname="<External Database URL de Render>" --file=/w/rm.dump
   ```
3. **Restore en Neon** contra la URL **directa** (`--clean --if-exists` sustituye lo restaurado en las pruebas):
   ```bash
   docker run --rm -v "$PWD:/w" postgres:18 pg_restore --no-owner --no-acl --clean --if-exists \
     --dbname="<URL DIRECTA de Neon>" /w/rm.dump
   ```
   Comprueba con `alembic current` (§3) que está en `d4e5f6a1b2c3` y que los admins pueden entrar.
   ⚠️ `rm.dump` contiene **datos personales**: bórralo en cuanto termines (RGPD).
4. **Backend en Vercel**: `ALLOWED_ORIGINS` definitivo (sin `.vercel.app`), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` reales y `CRON_SECRET`. Redeploy.
5. **Dominios**: añade `api.rmolinastyle.com` al proyecto backend y `rmolinastyle.com` + `www.rmolinastyle.com` al frontend (apex principal, `www` redirige). En **Cloudflare** crea/actualiza los registros **exactos** que indique Vercel, en modo **"DNS only"** (nube gris). ⚠️ Si se activa el proxy de Cloudflare (nube naranja), el backend vería la IP de Cloudflare y todos los usuarios compartirían el límite de `/login`.
6. **Frontend**: `VITE_API_URL` = `https://api.rmolinastyle.com`, quita la URL `.vercel.app` de `connect-src` en `frontend/vercel.json` (commit) y redeploy.
7. **Render**: deja `rm-backend` y `rm-recordatorios` suspendidos (no borres nada hasta pasado el periodo de rollback). Se borraron el 10 nov 2026.
8. **BetterStack**: el monitor sobre `https://api.rmolinastyle.com/health` sigue valiendo (`/health` no toca la BD, no despierta a Neon).

---

## 8. Verificación final

- [ ] HTTPS en `rmolinastyle.com` y `api.rmolinastyle.com`; `www` redirige al apex.
- [ ] Login de admin, de peluquero y de un cliente.
- [ ] Reservar / cancelar / reprogramar → el peluquero recibe el aviso de Telegram.
- [ ] Marcar inasistencia, días cerrados, servicios y horario desde el panel.
- [ ] Recargar en `/admin` y `/mi-cuenta` no da 404.
- [ ] Consola del navegador sin errores de CSP; "Exportar mis datos" descarga el JSON.
- [ ] `curl -I` del frontend muestra las cabeceras de seguridad.
- [ ] Crons visibles en Vercel; *Run* del recordatorio llega al peluquero; `/cron/recordatorio` sin cabecera → 401.
- [ ] `/login`: tras 5 intentos fallidos desde tu IP → 429, y desde otra red sigue funcionando.
- [ ] En Neon, la compute pasa a *Idle* tras unos minutos sin tráfico.

---

## 9. Rollback

- **Ya no hay rollback a Render**: sus servicios se borraron el 10 de noviembre de 2026.
- Ante un despliegue malo en Vercel: *Instant Rollback* al deployment anterior desde el panel del proyecto.
- Ante una pérdida de datos: restaurar el último `pg_dump` semanal cifrado (`backup-rm.ps1`, ver `ESTADO_PROYECTO.md`) contra la URL directa de Neon. Si el problema es de menos de 6 h, también sirve la restauración de Neon.
- Volver a Render exigiría montarlo desde cero con `render.yaml` (ver [`DESPLIEGUE_RENDER.md`](DESPLIEGUE_RENDER.md)). El código está preparado para Render: detecta `RENDER=true` para la IP del rate limiting, y el cron por CLI sigue igual. Aun así, no se ha vuelto a probar allí.

---

## 10. Limitaciones conocidas

- **Rate limiting en memoria**: en serverless cada instancia lleva su propio contador y se reinicia en los arranques en frío, así que el límite es aproximado. Con el tráfico del piloto suele haber una sola instancia. Solución robusta (futura): almacenamiento compartido (p. ej. Redis).
- **Vercel Hobby** está pensado para uso personal/no comercial según sus términos; para una peluquería real puede ser necesario el plan Pro.
- **Neon Free**: la restauración a un punto anterior solo cubre una ventana corta (6 h). Por eso se hace un `pg_dump` semanal con la URL directa, cifrado y fuera del portátil (`backup-rm.ps1`, fuera del repo; ver `ESTADO_PROYECTO.md`).
- **Previews de Vercel**: la CSP bloquea la barra de herramientas de Vercel en los deployments de preview (no afecta a producción). Además, las previews **no tienen `DATABASE_URL`**, que solo está en *Production*, así que en ellas el backend no arranca. Las ramas se prueban en local.
- **Avisos de Telegram síncronos**: se envían dentro de la petición, tras confirmar la operación, con un timeout de 3 s. Si Telegram falla, la reserva/cancelación/reprogramación se completa igualmente (el fallo solo se registra).
