"""versión de sesión del usuario (usuarios.token_version)

Revision ID: 9d2b7e4a1c63
Revises: f6a1b2c3d4e5
Create Date: 2026-11-11

- usuarios.token_version: INTEGER NOT NULL DEFAULT 0 (el DEFAULT es permanente).
  Los JWT llevan esta versión en el claim "ver"; al subirla, los tokens emitidos
  con la versión anterior dejan de valer.
- Los usuarios admin pasan a token_version = 1: con el código nuevo, sus tokens
  ya emitidos (sin "ver", que cuenta como 0) dejan de valer y tienen que volver a
  iniciar sesión. Los clientes se quedan en 0 y conservan la sesión.

Compatible con el código anterior (que no conoce la columna): sus INSERT no la
envían y el DEFAULT pone 0. Se puede aplicar en Neon (URL directa) ANTES de
desplegar el código nuevo. Añadir una columna con DEFAULT constante solo cambia
metadatos del catálogo (no reescribe la tabla).
"""
from alembic import op
import sqlalchemy as sa

revision = "9d2b7e4a1c63"
down_revision = "f6a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    # rol es VARCHAR(10) (SAEnum native_enum=False) con los valores 'admin' / 'cliente'.
    op.execute("UPDATE usuarios SET token_version = 1 WHERE rol = 'admin'")


def downgrade() -> None:
    op.drop_column("usuarios", "token_version")
