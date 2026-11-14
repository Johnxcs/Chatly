# Chatly Forum

A community forum app with private messaging, built with Python, KivyMD and Supabase, and compiled to an Android APK by GitHub Actions.

## What it does
- **Home**: a feed of threads from the communities you joined (or popular threads if you haven't joined any). Sort by *New* or *Top*.
- **Communities**: browse, search, join, leave and create communities. The creator is the moderator and can remove any thread or reply in it.
- **Threads and replies**: write threads (title + details), reply, and upvote threads and replies. Authors can delete their own posts.
- **Messaging**: direct messages with any member. Unread badges, "active now" status, message previews, saved history, and chat streaks (days in a row you both messaged).
- **Profiles**: display name, bio, your threads, and anyone else's profile with a Message button.
- **Settings**: edit profile, change password, privacy (show when I'm active), message previews, clear saved chats, error log, log out, delete account.

## Setup
1. **Supabase**: create a project. In the SQL Editor run `supabase/schema.sql` (new project), or run the update files in order if you already have an older version: `update_v2.sql` ... `update_v8.sql`.
2. **Keys**: put your project URL and publishable key in `config.py`, or add the GitHub secrets `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
3. **Build**: push to GitHub. The workflow in `.github/workflows/build.yml` builds the APK (Actions tab -> artifact `chatly-apk`).

## Files
- `main.py`: tiny launcher; shows the real error on screen if the app cannot start.
- `chatly_app.py`: the app (layout + logic).
- `errscreen.py`: plain-Kivy error screen with a Copy button.
- `supabase/`: database setup and updates (`update_v8.sql` adds the forum).

## If something crashes
Each page loads on its own: a broken page shows a message and the rest still works. If the app dies while a page is loading or showing, that page is switched off next time (tap "Try this page again", then reopen the app). Errors are saved: Menu > Settings > About > View error log > Copy.

## Notes
The old friends, posts, polls and notes tables from earlier versions are left in the database but the app no longer uses them.
