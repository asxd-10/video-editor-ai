from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import get_settings

settings = get_settings()

# Get database URL (handles both DATABASE_URL and individual components)
database_url = settings.get_database_url()

# Configure engine based on database type
connect_args = {}
pool_class = None

if database_url.startswith("sqlite"):
    # SQLite-specific settings
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL/Supabase settings
    # For session pooler, use regular pooling
    # For transaction pooler (port 6543), use NullPool
    connect_args = {
        "connect_timeout": 10,
        "sslmode": "require",
    }
    # If using transaction pooler (port 6543), uncomment:
    # pool_class = NullPool

engine = create_engine(
    database_url,
    connect_args=connect_args,
    poolclass=pool_class,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,  # Adjust based on your needs
    max_overflow=10,
    echo=settings.DB_ECHO
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()