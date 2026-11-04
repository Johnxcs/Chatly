-- Chatly update: notes ("What's up?") shown above avatars for 24 hours.
-- Requires update_v2.sql to have been run first. Run once in Supabase: SQL Editor -> New query -> Run.

alter table public.profiles
  add column if not exists note text check (note is null or char_length(note) between 1 and 60);
alter table public.profiles add column if not exists note_at timestamptz;
grant update (note, note_at) on public.profiles to authenticated;

-- Set (or clear, with an empty string) your note; the timestamp is taken on the server
create or replace function public.set_note(p_note text) returns void
language sql security invoker as $$
  update public.profiles
     set note    = nullif(left(trim(coalesce(p_note, '')), 60), ''),
         note_at = case when nullif(trim(coalesce(p_note, '')), '') is null then null else now() end
   where id = auth.uid();
$$;

-- People list now also returns each person's note (hidden after 24 hours)
drop function if exists public.get_people();
create function public.get_people()
returns table (id uuid, username text, display_name text, seconds_ago bigint, note text)
language sql stable security invoker as $$
  select p.id, p.username, p.display_name,
         case when p.show_active and p.last_seen is not null
              then extract(epoch from (now() - p.last_seen))::bigint end,
         case when p.note_at > now() - interval '24 hours' then p.note end
  from public.profiles p
  where p.id <> auth.uid()
  order by coalesce(p.display_name, p.username);
$$;

-- Your own profile (with your unexpired note)
create or replace function public.get_me()
returns table (id uuid, username text, display_name text, show_active boolean, note text)
language sql stable security invoker as $$
  select p.id, p.username, p.display_name, p.show_active,
         case when p.note_at > now() - interval '24 hours' then p.note end
  from public.profiles p
  where p.id = auth.uid();
$$;

grant execute on function public.set_note(text) to authenticated;
grant execute on function public.get_people() to authenticated;
grant execute on function public.get_me() to authenticated;

notify pgrst, 'reload schema';
