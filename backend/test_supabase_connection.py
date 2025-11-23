#!/usr/bin/env python3
"""
Test Supabase database connection.
Run this to verify your connection is working.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.config import get_settings

def main():
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)
    print()
    
    settings = get_settings()
    db_url = settings.get_database_url()
    
    # Debug: Show what we're using
    print(f"DB_USER: {settings.DB_USER[:10]}..." if settings.DB_USER else "DB_USER: (empty)")
    print(f"DB_HOST: {settings.DB_HOST}")
    print(f"DB_NAME: {settings.DB_NAME}")
    print()
    
    # Show connection info (hide password)
    if '@' in db_url:
        safe_url = db_url.split('@')[0].split(':')[-1] + '@' + db_url.split('@')[1]
        print(f"Connecting to: {safe_url}")
    else:
        print(f"Using: {db_url[:50]}...")
    print()
    
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("✅ Connection successful!")
            print()
            print(f"PostgreSQL version: {version[:50]}...")
            print()
            
            # Test if tables exist
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("No tables found. Run migrate_to_supabase.py to create tables.")
            print()
            
            return 0
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Check your .env file has:")
        print("  user=postgres.ujertelpchurerutnjpp")
        print("  password=YOUR_PASSWORD")
        print("  host=aws-0-us-west-2.pooler.supabase.com")
        print("  port=5432")
        print("  dbname=postgres")
        return 1

if __name__ == "__main__":
    sys.exit(main())

