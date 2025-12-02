import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient

async def check(username, password, url="ws://localhost:8001/rpc"):
    print(f"Checking {username}:{password} on {url}...")
    client = SurrealDBClient(url=url, username=username, password=password)
    try:
        # initialize calls signin
        await client.initialize()
        print(f"SUCCESS: {username}:{password}")
        return True
    except Exception as e:
        print(f"FAILED: {username}:{password} - {e}")
        return False
    finally:
        await client.close()

async def main():
    creds = [
        ("root", "root"),
        ("user", "pass"),
        ("admin", "admin"),
        ("khala", "khala"),
        ("root", "surrealdb"),
    ]
    
    ports = ["ws://localhost:8001/rpc", "ws://localhost:8000/rpc"]
    
    for port in ports:
        print(f"--- Checking port {port} ---")
        for user, pwd in creds:
            if await check(user, pwd, url=port):
                return

if __name__ == "__main__":
    asyncio.run(main())
