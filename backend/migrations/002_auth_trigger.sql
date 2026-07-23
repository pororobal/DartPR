-- Supabase Auth to Public Users Sync Trigger
-- Run this in the Supabase SQL Editor to automatically sync auth.users to public.users

-- 1. Create the trigger function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, plan)
  VALUES (
    new.id,
    new.email,
    'free' -- Default plan for new signups
  )
  ON CONFLICT (id) DO NOTHING; -- Avoid duplicate key errors if already exists
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Create the trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
