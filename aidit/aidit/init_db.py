"""
Initialize database tables in Supabase
Run this script to create all required tables in your Supabase database
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def init_tables():
    """Initialize database tables using Supabase SQL editor or direct connection"""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
            return False
        
        # Read schema file
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if not os.path.exists(schema_path):
            print(f"❌ Error: Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        print("📋 Database Schema:")
        print("=" * 60)
        print(schema_sql)
        print("=" * 60)
        print("\n⚠️  Note: Supabase Python client doesn't support executing raw SQL directly.")
        print("📝 Please run the SQL above in your Supabase SQL Editor:")
        print("   1. Go to your Supabase dashboard")
        print("   2. Navigate to SQL Editor")
        print("   3. Paste the SQL above and run it")
        print("\nAlternatively, you can use psql or Supabase CLI to run the schema.sql file.")
        
        return True
        
    except ImportError:
        print("❌ Error: supabase library not installed")
        print("   Install it with: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def check_tables():
    """Check if tables exist in Supabase"""
    try:
        from app.database import get_supabase_client
        
        client = get_supabase_client()
        
        # List of tables to check
        tables = [
            "media",
            "video_processing",
            "image_processing",
            "frames",
            "scene_indexes",
            "transcriptions",
            "processing_logs"
        ]
        
        print("\n🔍 Checking tables...")
        print("=" * 60)
        
        missing_tables = []
        for table in tables:
            try:
                # Try to select from table (will fail if table doesn't exist)
                result = client.table(table).select("id").limit(1).execute()
                print(f"✅ {table} - exists")
            except Exception as e:
                if "not found" in str(e).lower() or "PGRST205" in str(e):
                    print(f"❌ {table} - missing")
                    missing_tables.append(table)
                else:
                    print(f"⚠️  {table} - error checking: {str(e)}")
        
        print("=" * 60)
        
        if missing_tables:
            print(f"\n❌ Missing tables: {', '.join(missing_tables)}")
            print("   Run the SQL in schema.sql in your Supabase SQL Editor")
            return False
        else:
            print("\n✅ All tables exist!")
            return True
            
    except Exception as e:
        print(f"❌ Error checking tables: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Initializing database tables...\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_tables()
    else:
        init_tables()
        print("\n" + "=" * 60)
        print("After running the SQL, you can verify with:")
        print("  python init_db.py check")
        print("=" * 60)

