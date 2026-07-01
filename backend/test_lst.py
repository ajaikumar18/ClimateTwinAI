import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.services.real_satellite_ingestor import read_lst_file

files = list(Path("../datasets/lst").glob("*.h5"))

rows = read_lst_file(files[0])

print(f"File: {files[0].name}")
print(f"Records parsed: {len(rows)}")

if rows:
    print(f"Sample: {rows[0]}")
    print(f"Temp range: {min(r['temperature'] for r in rows):.1f} to {max(r['temperature'] for r in rows):.1f} ÅãC")
