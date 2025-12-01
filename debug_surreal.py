import asyncio
from surrealdb import Surreal

async def main():
    print("Inspecting Surreal...")
    try:
        db = Surreal("ws://localhost:8000/rpc")
        print(f"DB Object: {db}")
        print(f"Dir: {dir(db)}")

        # Try context manager
        print("Trying context manager...")
        async with Surreal("ws://localhost:8000/rpc") as sdb:
            print("Connected via context manager")
            await sdb.signin({"user": "root", "pass": "root"})
            print("Signed in")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
