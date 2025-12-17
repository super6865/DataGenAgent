#!/usr/bin/env python3
"""
Add indexes to documents table for better query performance
This fixes the "Out of sort memory" error when sorting by upload_time
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_index_exists(conn, index_name):
    """Check if an index exists"""
    result = conn.execute(text("""
        SELECT COUNT(*) as count
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
        AND table_name = 'documents'
        AND index_name = :index_name
    """), {"index_name": index_name})
    row = result.fetchone()
    return row[0] > 0 if row else False


def add_indexes():
    """Add indexes to documents table"""
    try:
        with engine.connect() as conn:
            # Add index on upload_time for sorting
            index_name = "idx_documents_upload_time"
            if check_index_exists(conn, index_name):
                logger.info(f"Index {index_name} already exists, skipping...")
            else:
                logger.info(f"Adding index {index_name}...")
                conn.execute(text(f"""
                    CREATE INDEX {index_name} 
                    ON documents(upload_time)
                """))
                conn.commit()
                logger.info(f"Index {index_name} added successfully!")
            
            # Add index on parse_status for filtering
            index_name = "idx_documents_parse_status"
            if check_index_exists(conn, index_name):
                logger.info(f"Index {index_name} already exists, skipping...")
            else:
                logger.info(f"Adding index {index_name}...")
                conn.execute(text(f"""
                    CREATE INDEX {index_name} 
                    ON documents(parse_status)
                """))
                conn.commit()
                logger.info(f"Index {index_name} added successfully!")
            
            logger.info("All indexes processed successfully!")
            return True
    except Exception as e:
        logger.error(f"Error adding indexes: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = add_indexes()
    sys.exit(0 if success else 1)
