from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import time
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()

# Supabase connection pooler settings
# Format: postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
SUPABASE_DB_USER = os.getenv("SUPABASE_DB_USER", "postgres.wctnszbithsykyauvgyu")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
SUPABASE_DB_HOST = os.getenv("SUPABASE_DB_HOST", "aws-0-ap-south-1.pooler.supabase.com")
SUPABASE_DB_PORT = os.getenv("SUPABASE_DB_PORT", "6543")
SUPABASE_DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Create database URL for Supabase PostgreSQL connection with connection pooler
SQLALCHEMY_DATABASE_URL = f"postgresql://{SUPABASE_DB_USER}:{SUPABASE_DB_PASSWORD}@{SUPABASE_DB_HOST}:{SUPABASE_DB_PORT}/{SUPABASE_DB_NAME}"

# Create SQLAlchemy engine with retry mechanism
def create_engine_with_retry(max_retries=5, retry_interval=5):
    for attempt in range(max_retries):
        try:
            # Create engine with SSL parameters required for Supabase
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                connect_args={
                    "sslmode": "require",
                }
            )
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Database connection attempt {attempt + 1} failed. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

# Create engine with retry
engine = create_engine_with_retry()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 