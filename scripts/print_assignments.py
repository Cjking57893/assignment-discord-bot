import asyncio
import aiosqlite

DB_PATH = "data/canvas_bot.db"

async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, course_id, name, due_at FROM assignments ORDER BY due_at") as cursor:
            rows = await cursor.fetchall()
            print("Assignments in DB:")
            for row in rows:
                print(row)

if __name__ == "__main__":
    asyncio.run(main())
