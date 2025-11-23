from app.database import get_database_url, init_db
from sqlalchemy import text
url = get_database_url(); print(f"URL: {url.split('@')[0]}@...")
engine = init_db()
with engine.connect() as conn: result = conn.execute(text("SELECT 1 as test")); print(f"✅ Connected! Result: {result.fetchone()[0]}")

