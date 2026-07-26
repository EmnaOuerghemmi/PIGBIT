"""add missing confirmed_slot_id foreign key

`interview_invitations.confirmed_slot_id` référence `interview_slots.id`, et
réciproquement `interview_slots.invitation_id` référence
`interview_invitations.id` : une dépendance circulaire. Le modèle la déclare
donc avec `use_alter=True`, qui demande à SQLAlchemy d'émettre la contrainte
dans un `ALTER TABLE` séparé, une fois les deux tables créées.

Or `op.create_table()` d'Alembic écrit les contraintes en ligne dans le
`CREATE TABLE` et ignore silencieusement celles marquées `use_alter` — sans
émettre l'ALTER correspondant. La migration de baseline déclarait donc bien la
contrainte sans jamais la créer : la base restait sans intégrité référentielle
sur ce lien, et un slot supprimé laissait un `confirmed_slot_id` pointant dans
le vide au lieu d'être remis à NULL.

Détecté par la vérification de dérive de schéma de la CI.

Revision ID: a3f8c1d94b62
Revises: 9b1c4d2e7f30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a3f8c1d94b62"
down_revision: Union[str, Sequence[str], None] = "9b1c4d2e7f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "interview_invitations_confirmed_slot_id_fkey"


def upgrade() -> None:
    op.create_foreign_key(
        CONSTRAINT_NAME,
        source_table="interview_invitations",
        referent_table="interview_slots",
        local_cols=["confirmed_slot_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        table_name="interview_invitations",
        type_="foreignkey",
    )
