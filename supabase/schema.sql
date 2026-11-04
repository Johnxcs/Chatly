-- Chatly: full database setup (new projects). Run once in Supabase: SQL Editor -> New query -> Run.
-- Already ran an older version? Run update_v2.sql instead.

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null check (char_length(username) between 3 and 24),
  created_at timestamptz default now()
);

create table public.messages (
  id bigint generated always as identity primary key,
  sender uuid not null references public.profiles(id) on delete cascade,
  receiver uuid not null references public.profiles(id) on delete cascade,
  text text not null check (char_length(text) between 1 and 2000),
  created_at timestamptz default now()
);
create index on public.messages (receiver, id);
create index on public.messages (sender, receiver, id);

alter table public.profiles enable row level security;
alter table public.messages enable row level security;

create policy "profiles readable by signed-in users"
  on public.profiles for select to authenticated using (true);

create policy "read own messages"
  on public.messages for select to authenticated
  using (auth.uid() in (sender, receiver));

create policy "send as yourself"
  on public.messages for insert to authenticated
  with check (auth.uid() = sender);

-- Auto-create a profile when someone signs up
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, username)
  values (new.id, coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)));
  return new;
end; $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ===== v2: display names + active status =====
alter table public.profiles
  add column if not exists display_name text
    check (display_name is null or char_length(display_name) between 1 and 40);
alter table public.profiles add column if not exists last_seen timestamptz;
alter table public.profiles add column if not exists show_active boolean not null default true;

-- Users may update only their own row, and only these columns
drop policy if exists "update own profile" on public.profiles;
create policy "update own profile"
  on public.profiles for update to authenticated
  using (auth.uid() = id) with check (auth.uid() = id);
revoke update on public.profiles from authenticated;
grant update (display_name, last_seen, show_active) on public.profiles to authenticated;

-- New accounts: store the display name chosen at sign-up
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, username, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)),
    nullif(left(trim(coalesce(new.raw_user_meta_data->>'display_name', '')), 40), '')
  );
  return new;
end; $$;

-- Heartbeat: the app calls this every 30s while open
create or replace function public.touch_presence() returns void
language sql security invoker as $$
  update public.profiles set last_seen = now() where id = auth.uid();
$$;

-- People list with "seconds since last active" (computed on the server clock)
create or replace function public.get_people()
returns table (id uuid, username text, display_name text, seconds_ago bigint)
language sql stable security invoker as $$
  select p.id, p.username, p.display_name,
         case when p.show_active and p.last_seen is not null
              then extract(epoch from (now() - p.last_seen))::bigint end
  from public.profiles p
  where p.id <> auth.uid()
  order by coalesce(p.display_name, p.username);
$$;

grant execute on function public.touch_presence() to authenticated;
grant execute on function public.get_people() to authenticated;

notify pgrst, 'reload schema';

-- ===== v3: notes =====
alter table public.profiles
  add column if not exists note text check (note is null or char_length(note) between 1 and 60);
alter table public.profiles add column if not exists note_at timestamptz;
grant update (note, note_at) on public.profiles to authenticated;

create or replace function public.set_note(p_note text) returns void
language sql security invoker as $$
  update public.profiles
     set note    = nullif(left(trim(coalesce(p_note, '')), 60), ''),
         note_at = case when nullif(trim(coalesce(p_note, '')), '') is null then null else now() end
   where id = auth.uid();
$$;

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
