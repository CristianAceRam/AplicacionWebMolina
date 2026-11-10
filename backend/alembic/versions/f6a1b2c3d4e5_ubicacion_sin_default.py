"""retirar el DEFAULT temporal de citas.ubicacion

Revision ID: f6a1b2c3d4e5
Revises: e5f6a1b2c3d4
Create Date: 2026-11-10

La migración e5f6a1b2c3d4 (Fase E) añadió citas.ubicacion con DEFAULT 'alcala'
de forma TEMPORAL, para que el código anterior (que no enviaba la columna)
siguiera funcionando mientras se desplegaba el nuevo.

El código nuevo ya está en producción y siempre indica la ciudad, así que el
DEFAULT sobra y es peligroso: una cita sin ciudad se guardaría en silencio como
Alcalá la Real. Sin él, un INSERT sin ubicacion falla con NOT NULL.

Aplicar en Neon (URL directa) SOLO con el código de la Fase E ya desplegado.
Solo cambia metadatos del catálogo (no reescribe la tabla).
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a1b2c3d4e5"
down_revision = "e5f6a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "citas",
        "ubicacion",
        existing_type=sa.String(10),
        existing_nullable=False,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "citas",
        "ubicacion",
        existing_type=sa.String(10),
        existing_nullable=False,
        server_default="alcala",
    )
