import asyncio
from surrealdb import Surreal

async def main():
    print("Connecting to ws://localhost:8001/rpc...")
    try:
        async with Surreal("ws://localhost:8001/rpc") as db:
            print("Connected.")
            try:
                await db.signin({"username": "root", "password": "root"})
                print("Signed in as root/root (username/password keys)")
            except Exception as e:
                print(f"Failed with username/password: {e}")
                try:
                    await db.signin({"user": "root", "pass": "root"})
                    print("Signed in as root/root (user/pass keys)")
                except Exception as e2:
                    print(f"Failed with user/pass: {e2}")

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
