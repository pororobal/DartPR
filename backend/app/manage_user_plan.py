import sys
import os
import argparse
from supabase import create_client

# Add parent directory to path so we can import app config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

def get_supabase_client():
    is_placeholder_url = "your-project" in settings.supabase_url or not settings.supabase_url
    is_placeholder_key = "your_service_role_key" in settings.supabase_service_role_key or not settings.supabase_service_role_key
    
    if is_placeholder_url or is_placeholder_key:
        print("ERROR: Supabase URL or Service Role Key is not configured in backend/.env.")
        print("Please configure backend/.env first.")
        sys.exit(1)
        
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

def list_users():
    supabase = get_supabase_client()
    print("Fetching users list from Supabase...")
    try:
        res = supabase.table("users").select("*").order("created_at", desc=True).execute()
        users = res.data or []
        if not users:
            print("No users found in database.")
            return
            
        print("\n" + "="*80)
        print(f"{'User ID':<38} | {'Email':<25} | {'Plan':<10} | {'API Key'}")
        print("="*80)
        for u in users:
            api_key = u.get("api_key") or "None"
            # Truncate API key for safety in listing
            if api_key != "None" and len(api_key) > 20:
                api_key = api_key[:15] + "..." + api_key[-5:]
            print(f"{u['id']:<38} | {u['email']:<25} | {u['plan']:<10} | {api_key}")
        print("="*80 + "\n")
    except Exception as e:
        print(f"Error fetching users: {e}")

def update_plan(email: str, plan: str):
    if plan not in ("free", "pro", "developer"):
        print("ERROR: Plan must be 'free', 'pro', or 'developer'")
        return

    supabase = get_supabase_client()
    print(f"Searching for user with email '{email}'...")
    try:
        user_res = supabase.table("users").select("*").eq("email", email).maybe_single().execute()
        if not user_res.data:
            print(f"ERROR: User with email '{email}' not found.")
            return
            
        user = user_res.data
        user_id = user["id"]
        
        print(f"Found user. Current plan: '{user['plan']}'. Updating to: '{plan}'...")
        
        update_data = {
            "plan": plan,
            "plan_updated_by": "CLI_Admin",
            "plan_updated_at": "now()"
        }
        
        # Generate API key for developer plan if they don't have one
        if plan == "developer" and not user.get("api_key"):
            import secrets
            update_data["api_key"] = f"dart0s_dev_{secrets.token_hex(24)}"
            print("Generating new API Key for developer plan.")
            
        supabase.table("users").update(update_data).eq("id", user_id).execute()
        
        # Verify update
        updated_res = supabase.table("users").select("*").eq("id", user_id).single().execute()
        updated_user = updated_res.data
        
        print("\n[SUCCESS] Plan updated successfully!")
        print(f" - User Email: {updated_user['email']}")
        print(f" - New Plan: {updated_user['plan'].upper()}")
        if updated_user.get("api_key"):
            print(f" - API Key: {updated_user['api_key']}")
        print()
        
    except Exception as e:
        print(f"Error updating plan: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage user plans in DartPR")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all users")
    group.add_argument("--email", help="User email to update")
    
    parser.add_argument("--plan", choices=["free", "pro", "developer"], help="Plan to assign (required with --email)")
    
    args = parser.parse_args()
    
    if args.email and not args.plan:
        parser.error("--plan is required when --email is specified.")
        
    if args.list:
        list_users()
    else:
        update_plan(args.email, args.plan)
