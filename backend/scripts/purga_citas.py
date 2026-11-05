"""
Purga citas (y sus franjas) anteriores a la ventana de retención (CLI).

La lógica vive en app/tareas/purga.py y también se expone como
GET /cron/purga (Vercel Cron).

Uso:
    cd backend
    python scripts/purga_citas.py [--dry-run]

El script es idempotente: ejecutarlo varias veces tiene el mismo efecto que ejecutarlo una.
La variable de entorno RETENCION_MESES (por defecto 24) controla la ventana.
"""
import argparse
import logging
import os
import sys

# Permite importar 'app.*' cuando el script se ejecuta directamente desde backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tareas.purga import purgar  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purga citas antiguas de la BD.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo cuenta cuántas citas se borrarían, sin borrar nada.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    n = purgar(dry_run=args.dry_run)
    print(f"{'[dry-run] ' if args.dry_run else ''}Citas afectadas: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
