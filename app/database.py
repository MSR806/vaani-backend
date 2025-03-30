from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import time
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()

# Get database credentials from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "writers_llm")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Create database URL
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create SQLAlchemy engine with retry mechanism
def create_engine_with_retry(max_retries=5, retry_interval=5):
    for attempt in range(max_retries):
        try:
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
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