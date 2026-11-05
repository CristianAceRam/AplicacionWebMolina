"""
Recordatorio diario de citas al peluquero por Telegram (CLI).

La lógica vive en app/tareas/recordatorio.py y también se expone como
GET /cron/recordatorio (Vercel Cron). Este script se mantiene para ejecutarlo
a mano o desde Render Cron.

Uso local:
    cd backend && python scripts/recordatorio_diario.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tareas.recordatorio import enviar_recordatorio  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    enviado = enviar_recordatorio()
    print("Recordatorio enviado." if enviado else "Recordatorio NO enviado (ver avisos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
