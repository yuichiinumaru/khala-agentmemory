import asyncio
import os
import logging
from khala.infrastructure.surrealdb.client import SurrealDBClient, SurrealConfig
from pydantic import SecretStr

# Set logging to see what's happening
logging.basicConfig(level=logging.INFO)

# User credentials
# Ideally these should be set in the environment, but for this example script we allow overrides.
URL_PROVIDED = os.getenv("TEST_SURREAL_URL", "wss://shiny-ember-06dfk97es5rgddp8jq05v3jckk.aws-use1.surreal.cloud")
TOKEN = os.getenv("TEST_SURREAL_TOKEN", "") # Token should be provided via env for security
NS = "main"
DB = "main"

# Set environment variables so SurrealConfig.from_env() picks them up
os.environ["SURREAL_URL"] = URL_PROVIDED
os.environ["SURREAL_NS"] = NS
os.environ["SURREAL_DB"] = DB
if TOKEN:
    os.environ["SURREAL_TOKEN"] = TOKEN

# Clean up any potential conflicting env vars
if "SURREAL_USER" in os.environ: del os.environ["SURREAL_USER"]
if "SURREAL_PASS" in os.environ: del os.environ["SURREAL_PASS"]

async def main():
    print("Testing Cloud SurrealDB connection...")

    try:
        # Initialize client
        # Note: initialize() creates schema which might fail if permissions are restricted.
        # But let's try.
        client = SurrealDBClient()

        # We manually skip full schema init if we just want to test connectivity
        # But client.initialize() does both.
        # Let's try initialize().
        await client.initialize()

        # Test query
        async with client.get_connection() as conn:
            # Simple query
            response = await conn.query("RETURN 'Connection Successful';")
            print(f"Query Response: {response}")

        await client.close()
        print("Test passed!")

    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
