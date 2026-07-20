"""Create all tables. Run: python -m database.setup"""
from pathlib import Path
from database.connection import executescript

def run():
    schema = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()
    executescript(schema)
    migrate()
    print("Schema created / verified.")


def migrate():
    """Add columns introduced after v1 to existing databases (safe to re-run).

    Checks actual table structure first, so it works reliably on both
    Turso and local SQLite, and reports problems instead of hiding them.
    """
    from database.connection import query, execute
    needed = {
        "clients": [
            ("daily_calorie_target", "REAL"),
            ("daily_protein_target", "REAL"),
            ("weekly_weight_target_kg", "REAL"),
        ],
        "diet_items": [
            ("day_of_week", "TEXT"),
        ],
    }
    for table, cols in needed.items():
        try:
            existing = {c["name"] for c in query(f"PRAGMA table_info({table})")}
        except Exception:
            continue  # table doesn't exist yet — schema.sql creates it with columns
        for name, ctype in cols:
            if name in existing:
                continue
            try:
                execute(f"ALTER TABLE {table} ADD COLUMN {name} {ctype}")
                print(f"migrated: {table}.{name}")
            except Exception as exc:
                # duplicate-column race is fine; anything else should be visible
                if "duplicate" not in str(exc).lower():
                    print(f"MIGRATION WARNING {table}.{name}: {exc}")

if __name__ == "__main__":
    run()
