"""Create all tables. Run: python -m database.setup"""
from pathlib import Path
from database.connection import executescript

def run():
    schema = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()
    executescript(schema)
    migrate()
    print("Schema created / verified.")


def migrate():
    """Add columns introduced after v1 to existing databases (safe to re-run)."""
    from database.connection import execute
    for stmt in [
        "ALTER TABLE clients ADD COLUMN daily_calorie_target REAL",
        "ALTER TABLE clients ADD COLUMN daily_protein_target REAL",
        "ALTER TABLE clients ADD COLUMN weekly_weight_target_kg REAL",
        "ALTER TABLE diet_items ADD COLUMN day_of_week TEXT",
    ]:
        try:
            execute(stmt)
        except Exception:
            pass  # column already exists

if __name__ == "__main__":
    run()
