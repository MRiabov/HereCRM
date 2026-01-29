import os
import sqlite3
import asyncio
from clerk_backend_api import Clerk
from dotenv import load_dotenv

# Load .env from backend
load_dotenv(".env")

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
DATABASE_PATH = "data/crm.db"
TEST_USER_EMAIL = "debug+clerk_test@example.com"
# Use a complex password to satisfy Clerk security checks
TEST_USER_PASSWORD = "SecureTestPass123!@#"
TEST_USER_NAME = "Test E2E User"


async def seed_user():
    if not CLERK_SECRET_KEY:
        print("Error: CLERK_SECRET_KEY not set in .env")
        return

    clerk_client = Clerk(bearer_auth=CLERK_SECRET_KEY)

    print(f"Checking for user {TEST_USER_EMAIL} in Clerk...")

    # 1. Check/Create in Clerk
    clerk_user_id = None
    try:
        # List users and find the one with the matching email
        users_response = clerk_client.users.list()

        # Check if users_response is a list or an object with a data attribute
        if hasattr(users_response, "data"):
            users = users_response.data
        else:
            users = users_response

        found_user = None
        for u in users:
            for email_obj in u.email_addresses:
                if email_obj.email_address == TEST_USER_EMAIL:
                    found_user = u
                    break
            if found_user:
                break

        if found_user:
            clerk_user_id = found_user.id
            print(f"Found existing user in Clerk: {clerk_user_id}")
            # Ensure password is set for existing user
            try:
                print("Updating password for existing user...")
                clerk_client.users.update(
                    user_id=clerk_user_id,
                    password=TEST_USER_PASSWORD,
                    skip_password_checks=True,
                )
                print("Password updated successfully.")
            except Exception as e:
                print(f"Failed to update password (maybe already set?): {e}")

        else:
            print("User not found in Clerk. Attempting to create...")
            # Note: create might fail depending on your Clerk settings (e.g. password required)
            # In some instances legal_accepted_at is required
            import datetime

            now_iso = (
                datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
            )

            new_user = clerk_client.users.create(
                email_address=[TEST_USER_EMAIL],
                first_name="Test",
                last_name="E2E User",
                password=TEST_USER_PASSWORD,
                skip_password_checks=True,
                skip_password_requirement=True,
                legal_accepted_at=now_iso,
            )
            clerk_user_id = new_user.id
            print(f"Created new user in Clerk: {clerk_user_id}")
    except Exception as e:
        print(f"Error interacting with Clerk: {e}")
        # If it failed because it already exists but list didn't find it (unlikely), handle that if needed
        return

    # 2. Check/Create in Local DB
    print(f"Checking for user in local database {DATABASE_PATH}...")
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute(
            "SELECT id FROM users WHERE clerk_id = ? OR email = ?",
            (clerk_user_id, TEST_USER_EMAIL),
        )
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"User already exists in local DB with ID {existing_user[0]}")
            # Ensure clerk_id is synced if it matched by email
            cursor.execute(
                "UPDATE users SET clerk_id = ? WHERE email = ?",
                (clerk_user_id, TEST_USER_EMAIL),
            )
            conn.commit()
        else:
            print("User not found in local DB. Creating...")

            # We need a business ID. Let's find or create a test business.
            cursor.execute("SELECT id FROM businesses LIMIT 1")
            business = cursor.fetchone()
            if not business:
                print("Creating test business...")
                cursor.execute(
                    "INSERT INTO businesses (name, created_at) VALUES (?, datetime('now'))",
                    ("E2E Test Business",),
                )
                business_id = cursor.lastrowid
            else:
                business_id = business[0]

            cursor.execute(
                """
                INSERT INTO users (
                    name, email, clerk_id, business_id, role, created_at,
                    preferred_channel, preferences, timezone, google_calendar_sync_enabled
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?)
                """,
                (
                    TEST_USER_NAME,
                    TEST_USER_EMAIL,
                    clerk_user_id,
                    business_id,
                    "OWNER",
                    "WHATSAPP",
                    '{"confirm_by_default": false}',
                    "UTC",
                    0,
                ),
            )
            conn.commit()
            print("Successfully seeded user in local database.")

        conn.close()
    except Exception as e:
        print(f"Error interacting with database: {e}")


if __name__ == "__main__":
    asyncio.run(seed_user())
