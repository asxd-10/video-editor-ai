"""
Download current database schema from Supabase
This script queries the database and generates a schema file
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def download_schema_cli():
    """Download schema using Supabase CLI"""
    print("📥 Downloading schema using Supabase CLI...")
    print("=" * 60)
    print("\nOption 1: Using Supabase CLI (recommended)")
    print("  supabase db dump --schema public > supabase/schemas/current_schema.sql")
    print("\nOption 2: Download only table definitions")
    print("  supabase db dump --schema public --data-only=false > supabase/schemas/current_schema.sql")
    print("\nOption 3: Download from remote project")
    print("  supabase db dump --linked > supabase/schemas/current_schema.sql")
    print("\n" + "=" * 60)
    return True


def download_schema_python():
    """Download schema using Python/Supabase client"""
    try:
        from app.database import get_supabase_client
        import psycopg2
        from urllib.parse import urlparse
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
            return False
        
        # Get database URL from Supabase URL
        # Supabase URL format: https://project-ref.supabase.co
        # Database URL format: postgresql://postgres:[password]@db.project-ref.supabase.co:5432/postgres
        
        print("📥 Downloading schema using Python...")
        print("=" * 60)
        print("\n⚠️  Note: Direct schema download via Python client is limited.")
        print("   The Supabase Python client doesn't support raw SQL execution for schema dumps.")
        print("\n💡 Recommended: Use Supabase CLI or psql instead:")
        print("\n   1. Supabase CLI:")
        print("      supabase db dump --linked > supabase/schemas/current_schema.sql")
        print("\n   2. Using psql (if you have DATABASE_URL):")
        print("      pg_dump -h [host] -U postgres -d postgres --schema-only > schema.sql")
        print("\n   3. From Supabase Dashboard:")
        print("      - Go to SQL Editor")
        print("      - Run: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("      - Export table definitions")
        print("\n" + "=" * 60)
        
        return False
        
    except ImportError:
        print("❌ Error: Required libraries not installed")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def get_table_list():
    """Get list of tables from Supabase"""
    try:
        from app.database import get_supabase_client
        
        client = get_supabase_client()
        
        # Try to query information_schema (this might not work with Supabase client)
        # Instead, we'll try to detect tables by attempting to query them
        
        print("🔍 Detecting existing tables...")
        print("=" * 60)
        
        # List of tables we know about
        known_tables = [
            "media",
            "video_processing",
            "image_processing",
            "frames",
            "scene_indexes",
            "transcriptions",
            "processing_logs"
        ]
        
        existing_tables = []
        for table in known_tables:
            try:
                result = client.table(table).select("id").limit(1).execute()
                existing_tables.append(table)
                print(f"✅ {table} - exists")
            except Exception as e:
                if "not found" in str(e).lower() or "PGRST205" in str(e):
                    print(f"❌ {table} - missing")
                else:
                    print(f"⚠️  {table} - error: {str(e)[:50]}")
        
        print("=" * 60)
        print(f"\n📊 Found {len(existing_tables)} existing tables")
        
        if existing_tables:
            print("\n💡 To get full schema, use Supabase CLI:")
            print("   supabase db dump --linked > supabase/schemas/current_schema.sql")
        
        return existing_tables
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


if __name__ == "__main__":
    print("🚀 Schema Download Tool")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            get_table_list()
        elif sys.argv[1] == "cli":
            download_schema_cli()
        else:
            print("Usage:")
            print("  python download_schema.py          # Show options")
            print("  python download_schema.py list     # List existing tables")
            print("  python download_schema.py cli      # Show CLI commands")
    else:
        print("\n📋 Options to download schema:")
        print("\n1. Using Supabase CLI (BEST):")
        print("   supabase db dump --linked > supabase/schemas/current_schema.sql")
        print("\n2. Check existing tables:")
        print("   python download_schema.py list")
        print("\n3. Show CLI commands:")
        print("   python download_schema.py cli")
        print("\n" + "=" * 60)
        
        # Try to list tables
        print("\n")
        get_table_list()

