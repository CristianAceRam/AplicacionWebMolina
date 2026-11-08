"""ubicacion de la cita e instagram del usuario (Fase E)

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-11-08

Compatible con el código anterior (que no conoce estas columnas), para poder
aplicarla en Neon ANTES de desplegar el código nuevo:

- citas.ubicacion: NOT NULL con DEFAULT 'alcala'. El default rellena las citas
  existentes (backfill: hasta ahora todas eran en Alcalá la Real) y hace que los
  INSERT del código anterior, que no envían la columna, sigan funcionando.
  En PostgreSQL >= 11 añadir una columna con default constante es solo de
  metadatos (no reescribe la tabla).
  El DEFAULT es TEMPORAL: se retira en una migración posterior, en otra rama,
  cuando el código nuevo ya esté en producción.
- usuarios.instagram: nullable (las cuentas existentes no lo tienen).
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a1b2c3d4"
down_revision = "d4e5f6a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "citas",
        sa.Column("ubicacion", sa.String(10), nullable=False, server_default="alcala"),
    )
    op.create_check_constraint(
        "ck_cita_ubicacion", "citas", "ubicacion IN ('alcala','granada')"
    )
    op.add_column("usuarios", sa.Column("instagram", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "instagram")
    op.drop_constraint("ck_cita_ubicacion", "citas", type_="check")
    op.drop_column("citas", "ubicacion")
