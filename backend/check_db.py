import asyncio
from sqlalchemy import text
from app.database.session import AsyncSessionLocal

async def run():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("SELECT COUNT(*) FROM climate_records"))
        print("Total records:", r.scalar())
        
        r2 = await s.execute(text("SELECT COUNT(DISTINCT CAST(latitude AS TEXT) || ',' || CAST(longitude AS TEXT)) FROM climate_records"))
        print("Unique stations:", r2.scalar())
        
        r3 = await s.execute(text("SELECT COUNT(*) FROM climate_records WHERE temperature IS NOT NULL"))
        print("With temperature:", r3.scalar())
        
        r4 = await s.execute(text("SELECT COUNT(*) FROM climate_records WHERE temperature_max IS NOT NULL"))
        print("With tmax:", r4.scalar())
        
        r5 = await s.execute(text("SELECT COUNT(*) FROM climate_records WHERE temperature_min IS NOT NULL"))
        print("With tmin:", r5.scalar())
        
        r6 = await s.execute(text("SELECT COUNT(*) FROM climate_records WHERE rainfall IS NOT NULL"))
        print("With rainfall:", r6.scalar())
        
        r7 = await s.execute(text("SELECT source, COUNT(*) AS cnt FROM climate_records GROUP BY source ORDER BY cnt DESC"))
        for row in r7:
            print(f"  {row[0]}: {row[1]}")
        
        r8 = await s.execute(text("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM climate_records"))
        row = r8.one()
        print(f"Lat range: {row[0]} to {row[1]}")
        print(f"Lon range: {row[2]} to {row[3]}")
        
        r9 = await s.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM climate_records"))
        row = r9.one()
        print(f"Date range: {row[0]} to {row[1]}")

asyncio.run(run())
