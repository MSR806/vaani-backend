#!/usr/bin/env python3
"""
Setup script to initialize the Supabase database schema.
This script will create all the tables defined in your SQLAlchemy models.
"""

import os
import sys

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine


def setup_database():
    """
    Create all tables defined in SQLAlchemy models.
    """
    print("Creating database schema in Supabase...")

    # Create all tables
    Base.metadata.create_all(bind=engine)

    print("Database schema created successfully!")
    print("The following tables have been created:")
    for table in Base.metadata.tables:
        print(f"- {table}")


if __name__ == "__main__":
    setup_database()
