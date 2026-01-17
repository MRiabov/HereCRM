from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///crm.db")
inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tables found:", tables)

required = {"import_jobs", "export_requests"}
missing = required - set(tables)

if missing:
    print(f"Missing tables: {missing}")
    exit(1)
else:
    print("All required tables are present.")
    exit(0)
