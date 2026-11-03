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
