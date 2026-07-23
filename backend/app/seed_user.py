import sys
import os
import argparse
from supabase import create_client

# Add parent dir to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

def seed_admin_user(email: str = "kimdy3185@gmail.com", password: str = "dnflskfk1!", plan: str = "developer"):
    # Check for placeholder values
    is_placeholder_url = "your-project" in settings.supabase_url or not settings.supabase_url
    is_placeholder_key = "your_service_role_key" in settings.supabase_service_role_key or not settings.supabase_service_role_key
    
    if is_placeholder_url or is_placeholder_key:
        print("ERROR: Supabase URL or Service Role Key is not configured in backend/.env.")
        print("Please edit backend/.env to include your actual credentials, then run this script again.")
        print(f"Current URL: {settings.supabase_url}")
        return False

    print(f"Connecting to Supabase at {settings.supabase_url}...")
    
    # We use service role client to bypass RLS and use admin auth actions
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    
    try:
        # Check if user already exists in auth
        print(f"Creating/updating user in Supabase Auth: {email}...")
        try:
            auth_resp = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            user_id = auth_resp.user.id
            print(f"Auth user created successfully. ID: {user_id}")
        except Exception as e:
            err_msg = str(e)
            if "already registered" in err_msg or "already exists" in err_msg or "User already exists" in err_msg:
                print("User already exists in Supabase Auth. Proceeding to update/insert database entry.")
                user_res = supabase.table("users").select("id").eq("email", email).maybe_single().execute()
                if user_res.data:
                    user_id = user_res.data["id"]
                    print(f"Found existing user database ID: {user_id}")
                else:
                    # If user is in Auth but not in the database table 'users', let's search auth.users list
                    # (since we are service_role, we can list users in auth)
                    print("Searching in auth.admin.list_users()...")
                    auth_users = supabase.auth.admin.list_users()
                    user_id = None
                    for u in auth_users:
                        if u.email == email:
                            user_id = u.id
                            break
                    
                    if user_id:
                        print(f"Found user ID in auth: {user_id}")
                    else:
                        print("User exists in Auth but could not retrieve ID. Please delete the user from Supabase dashboard or use a different email.")
                        return False
            else:
                print(f"Error creating user in Supabase Auth: {e}")
                return False

        # Insert or update entry in public.users
        print(f"Upserting user record in database with plan={plan}...")
        upsert_data = {
            "id": user_id,
            "email": email,
            "plan": plan
        }
        
        # Check if key needs to be generated for developer plan
        if plan == "developer":
            import secrets
            existing = supabase.table("users").select("api_key").eq("id", user_id).maybe_single().execute()
            if existing.data and existing.data.get("api_key"):
                print("User already has an API key. Keeping existing key.")
            else:
                upsert_data["api_key"] = f"dart0s_dev_{secrets.token_hex(24)}"
                print(f"Generated new API key for developer plan.")

        res = supabase.table("users").upsert(upsert_data, on_conflict="id").execute()
        print("Successfully registered/updated admin user record in 'users' table.")
        print(res.data)
        return True

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed admin user in Supabase")
    parser.add_argument("--email", default="kimdy3185@gmail.com", help="Email for admin user")
    parser.add_argument("--password", default="dnflskfk1!", help="Password for admin user")
    parser.add_argument("--plan", default="developer", choices=["free", "pro", "developer"], help="Plan type")
    args = parser.parse_args()
    
    seed_admin_user(args.email, args.password, args.plan)
