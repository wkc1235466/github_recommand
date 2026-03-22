"""MongoDB database connection management."""

from motor.motor_asyncio import AsyncIOMotorClient
from .config import get_settings

settings = get_settings()

# Database client
client: AsyncIOMotorClient | None = None
database = None


async def get_database():
    """Get database instance."""
    global database
    if database is None:
        database = client[settings.mongodb_db_name]
    return database


async def connect_to_mongo():
    """Connect to MongoDB."""
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    # Test connection
    await client.admin.command('ping')
    print(f"Connected to MongoDB at {settings.mongodb_url}")


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


def get_collection(collection_name: str):
    """Get a collection from the database."""
    db = client[settings.mongodb_db_name]
    return db[collection_name]