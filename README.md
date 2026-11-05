# Chatly - Messenger-style Android chat (KivyMD + Supabase)

## 1. Supabase setup
1. Create a project at supabase.com.
2. SQL Editor -> paste and run `supabase/schema.sql`.
3. Authentication -> Providers -> Email. For quick testing turn OFF "Confirm email".
4. Project Settings -> API: copy the Project URL and the anon public key.

## 2. GitHub secrets
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
- SUPABASE_URL
- SUPABASE_ANON_KEY

## 3. Build
Push to main (or run the workflow manually in the Actions tab) and download the `chatly-apk` artifact.

For local testing, edit `config.py` and run `python main.py`.

## Updating an existing Supabase project (display names + active status)
Run `supabase/update_v2.sql` once in the Supabase SQL Editor. New projects can run `supabase/schema.sql` instead.
The app still works without this update, but display names and "Active now" stay off until it is run.

## Notes + active friends strip
Run `supabase/update_v3.sql` once (after update_v2.sql) to enable notes. Without it the strip still shows
friends who are active, but notes are off.

## Settings: delete account
Run `supabase/update_v4.sql` once to enable Settings -> Delete account. Everything else in Settings works without it.
