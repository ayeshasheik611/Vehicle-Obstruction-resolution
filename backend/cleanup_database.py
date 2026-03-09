"""
Database cleanup script
- Removes all request history
- Resets rate limit counters to 0
- Keeps user login details (users collection)
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/freeway_db")
DATABASE_NAME = os.getenv("DATABASE_NAME", "freeway_db")


async def cleanup_database():
    """Clean up database - remove requests, reset counters"""
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(DATABASE_URL)
    db = client[DATABASE_NAME]
    
    try:
        # 1. Delete all requests
        print("\n1. Deleting all requests...")
        result = await db.requests.delete_many({})
        print(f"   ✓ Deleted {result.deleted_count} requests")
        
        # 2. Delete all reports
        print("\n2. Deleting all reports...")
        result = await db.reports.delete_many({})
        print(f"   ✓ Deleted {result.deleted_count} reports")
        
        # 3. Delete all audit logs (optional - keeps login history if you want)
        print("\n3. Deleting all audit logs...")
        result = await db.audit_logs.delete_many({})
        print(f"   ✓ Deleted {result.deleted_count} audit logs")
        
        # 4. Reset user counters to 0
        print("\n4. Resetting user rate limit counters...")
        result = await db.users.update_many(
            {},
            {"$set": {"requestCount": 0, "reportCount": 0}}
        )
        print(f"   ✓ Updated {result.modified_count} users")
        
        # 5. Show remaining data
        print("\n5. Remaining data in database:")
        user_count = await db.users.count_documents({})
        vehicle_count = await db.vehicles.count_documents({})
        device_token_count = await db.device_tokens.count_documents({})
        
        print(f"   - Users: {user_count}")
        print(f"   - Vehicles: {vehicle_count}")
        print(f"   - Device Tokens: {device_token_count}")
        print(f"   - Requests: 0 (cleaned)")
        print(f"   - Reports: 0 (cleaned)")
        print(f"   - Audit Logs: 0 (cleaned)")
        
        print("\n✅ Database cleanup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
    finally:
        client.close()
        print("\nMongoDB connection closed.")


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CLEANUP SCRIPT")
    print("=" * 60)
    print("\nThis will:")
    print("  - Delete ALL requests")
    print("  - Delete ALL reports")
    print("  - Delete ALL audit logs")
    print("  - Reset requestCount and reportCount to 0 for all users")
    print("  - Keep user login details (users collection)")
    print("  - Keep vehicles")
    print("  - Keep device tokens")
    print("\n" + "=" * 60)
    
    confirm = input("\nAre you sure you want to proceed? (yes/no): ")
    
    if confirm.lower() == "yes":
        asyncio.run(cleanup_database())
    else:
        print("\n❌ Cleanup cancelled.")
