#!/usr/bin/env python
"""
Quick verification that all job_offers columns exist
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def verify_columns():
    """Verify all required columns exist in job_offers table"""
    required_columns = {
        'id', 'title', 'description', 'salary_min', 'salary_max',
        'required_skills', 'required_experience_years', 'required_education_level',
        'weight_skills', 'weight_experience', 'weight_education',
        'is_active', 'created_at', 'updated_at', 'created_by'
    }
    
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'job_offers' 
                ORDER BY column_name
            """))
            
            existing_columns = {row[0] for row in result}
            missing_columns = required_columns - existing_columns
            
            print("✅ Database Columns Verification")
            print("=" * 50)
            print(f"Existing columns: {len(existing_columns)}")
            print(f"Required columns: {len(required_columns)}")
            
            if missing_columns:
                print(f"\n❌ Missing columns: {missing_columns}")
                return False
            else:
                print("\n✅ All required columns exist!")
                print("\nColumns in job_offers table:")
                for col in sorted(existing_columns):
                    print(f"   • {col}")
                return True
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(verify_columns())
    sys.exit(0 if success else 1)
