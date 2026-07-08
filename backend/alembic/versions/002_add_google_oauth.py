"""Add Google OAuth columns to users table

Revision ID: 002_add_google_oauth
Revises: 001_add_job_offers_columns
Create Date: 2026-04-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_google_oauth'
down_revision = '001_add_job_offers_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OAuth columns to users table
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        # Add google_id column
        conn.execute(sa.text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id varchar(255);
        """))
        
        # Add oauth_provider column
        conn.execute(sa.text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider varchar(50);
        """))
        
        # Make hashed_password nullable for OAuth users
        # We need to check if it's already nullable
        conn.execute(sa.text("""
            ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;
        """))
        
        # Add unique constraint on google_id
        conn.execute(sa.text("""
            ALTER TABLE users ADD CONSTRAINT uq_users_google_id UNIQUE (google_id);
        """))
        
        # Add indices
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
        """))
        
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS ix_users_oauth_provider ON users(oauth_provider);
        """))


def downgrade() -> None:
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        # Remove indices
        conn.execute(sa.text("""
            DROP INDEX IF EXISTS ix_users_oauth_provider;
        """))
        conn.execute(sa.text("""
            DROP INDEX IF EXISTS ix_users_google_id;
        """))
        
        # Remove unique constraint
        conn.execute(sa.text("""
            ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_google_id;
        """))
        
        # Make hashed_password required again
        conn.execute(sa.text("""
            ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL;
        """))
        
        # Remove OAuth columns
        conn.execute(sa.text("""
            ALTER TABLE users DROP COLUMN IF EXISTS oauth_provider;
        """))
        conn.execute(sa.text("""
            ALTER TABLE users DROP COLUMN IF EXISTS google_id;
        """))
