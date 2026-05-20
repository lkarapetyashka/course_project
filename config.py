from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "integral_trainer.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
SEED_PATH = BASE_DIR / "seed.sql"