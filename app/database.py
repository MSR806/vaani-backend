import os
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# MySQL database settings
# Format: mysql+pymysql://username:password@host:port/database_name
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME", "vaani")

# Create database URL for MySQL connection
SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB_NAME}"
)


# Create SQLAlchemy engine with retry mechanism
def create_engine_with_retry(max_retries=5, retry_interval=5):
    for attempt in range(max_retries):
        try:
            # Create MySQL engine
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_pre_ping=True,
            )

            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            if attempt == max_retries - 1:
                raise e
            print(
                f"Database connection attempt {attempt + 1} failed. Retrying in {retry_interval} seconds..."
            )
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
