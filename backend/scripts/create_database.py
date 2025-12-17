"""
Script to create MySQL database for DataGenAgent
"""
import pymysql
import sys
import os
from dotenv import load_dotenv

# Load .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def create_database():
    """Create database if it doesn't exist"""
    # Parse database URL
    # Format: mysql+pymysql://user:password@host:port/database
    db_url = settings.DATABASE_URL
    
    # Extract components
    if db_url.startswith('mysql+pymysql://'):
        db_url = db_url.replace('mysql+pymysql://', '')
    
    # Split into parts
    if '@' in db_url:
        auth_part, host_part = db_url.split('@', 1)
        user, password = auth_part.split(':', 1)
        
        if ':' in host_part:
            host, port_db = host_part.split(':', 1)
            if '/' in port_db:
                port, database = port_db.split('/', 1)
            else:
                port = port_db
                database = None
        else:
            if '/' in host_part:
                host, database = host_part.split('/', 1)
                port = 3306
            else:
                host = host_part
                port = 3306
                database = None
    else:
        # No authentication
        user = 'root'
        password = ''
        if ':' in db_url:
            host, port_db = db_url.split(':', 1)
            if '/' in port_db:
                port, database = port_db.split('/', 1)
            else:
                port = port_db
                database = None
        else:
            host = db_url
            port = 3306
            database = None
    
    port = int(port) if port else 3306
    database = database or 'datagenagent'
    
    print(f"Connecting to MySQL server: {user}@{host}:{port}")
    
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Check if database exists
            cursor.execute("SHOW DATABASES LIKE %s", (database,))
            result = cursor.fetchone()
            
            if result:
                print(f"Database '{database}' already exists.")
            else:
                # Create database
                cursor.execute(f"CREATE DATABASE {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"Database '{database}' created successfully.")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
