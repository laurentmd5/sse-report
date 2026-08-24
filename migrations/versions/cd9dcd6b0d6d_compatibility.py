"""Restore the migration revision used by the pre-production database.

This revision was applied in pre-production but its source file is not
available in the repository. It is kept as a no-op compatibility step so the
database can continue to the tracked migrations.
"""

revision = 'cd9dcd6b0d6d'
down_revision = 'f09366ff3b17'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass