-- Chatly update: display names + active status.
-- Run once in Supabase: SQL Editor -> New query -> paste -> Run. Safe to run again.

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
