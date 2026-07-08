"""add missing columns to job_offers table

Revision ID: 001_add_job_offers_columns
Revises: 
Create Date: 2026-04-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '001_add_job_offers_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to job_offers table
    # Use raw SQL with conditional logic to avoid errors if columns already exist
    conn = op.get_bind()
    
    # Check if columns exist before adding them
    if conn.dialect.name == 'postgresql':
        # required_skills column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_skills json DEFAULT '[]'::json;
        """))
        
        # required_experience_years column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_experience_years double precision;
        """))
        
        # required_education_level column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_education_level varchar(20);
        """))
        
        # weight_skills column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_skills double precision DEFAULT 0.5 NOT NULL;
        """))
        
        # weight_experience column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_experience double precision DEFAULT 0.3 NOT NULL;
        """))
        
        # weight_education column
        conn.execute(sa.text("""
            ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_education double precision DEFAULT 0.2 NOT NULL;
        """))


def downgrade() -> None:
    # Remove the columns (this will fail silently if they don't exist in PostgreSQL)
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS weight_education;
        """))
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS weight_experience;
        """))
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS weight_skills;
        """))
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS required_education_level;
        """))
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS required_experience_years;
        """))
        conn.execute(sa.text("""
            ALTER TABLE job_offers DROP COLUMN IF EXISTS required_skills;
        """))
