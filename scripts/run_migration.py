import os
import sys
import psycopg
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration(migration_file):
    load_dotenv()
    db_url = os.getenv("PG_DATABASE_URL")
    
    if not db_url:
        print("❌ PG_DATABASE_URL not found in .env")
        sys.exit(1)

    # Allow for potentially different driver schemes if needed, but psycopg usually takes postgres://
    # If using SQLAlchemy style postgresql+psycopg://, we might need to strip the driver part for raw psycopg,
    # or just use it if psycopg supports it.
    # psycopg 3 supports "postgresql://" and "postgres://"
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    print(f"🔌 Connecting to database...")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                print(f"📖 Reading migration file: {migration_file}")
                with open(migration_file, 'r') as f:
                    sql = f.read()
                
                print(f"🚀 Executing migration...")
                cur.execute(sql)
                
            conn.commit()
            print("✅ Migration executed successfully!")
            
    except Exception as e:
        print(f"❌ Error executing migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migration.py <path_to_sql_file>")
        sys.exit(1)
        
    migration_path = sys.argv[1]
    run_migration(migration_path)
