"""Create all tables. Run: python -m database.setup"""
from pathlib import Path
from database.connection import executescript

def run():
    schema = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()
    executescript(schema)
    print("Schema created / verified.")

if __name__ == "__main__":
    run()
