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

-- ===== v4: delete account =====
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = public, auth as $$
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  delete from auth.users where id = auth.uid();
end; $$;

revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

notify pgrst, 'reload schema';

-- ===== v5: feed =====
create table if not exists public.posts (
  id         bigint generated always as identity primary key,
  author     uuid not null references public.profiles(id) on delete cascade,
  body       text not null check (char_length(body) between 1 and 500),
  vibe       text check (vibe is null or vibe in ('chill','hyped','focused','grateful','sleepy')),
  prompt     text check (prompt is null or char_length(prompt) <= 120),
  created_at timestamptz not null default now(),
  expires_at timestamptz            -- null = never vanishes
);
create index if not exists posts_created_idx on public.posts (created_at desc);

create table if not exists public.post_likes (
  post_id    bigint not null references public.posts(id) on delete cascade,
  user_id    uuid   not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (post_id, user_id)
);

alter table public.posts enable row level security;
alter table public.post_likes enable row level security;

drop policy if exists "read live posts" on public.posts;
create policy "read live posts" on public.posts for select to authenticated
  using (expires_at is null or expires_at > now());
drop policy if exists "write own posts" on public.posts;
create policy "write own posts" on public.posts for insert to authenticated
  with check (auth.uid() = author);
drop policy if exists "delete own posts" on public.posts;
create policy "delete own posts" on public.posts for delete to authenticated
  using (auth.uid() = author);

drop policy if exists "read likes" on public.post_likes;
create policy "read likes" on public.post_likes for select to authenticated using (true);
drop policy if exists "like as yourself" on public.post_likes;
create policy "like as yourself" on public.post_likes for insert to authenticated
  with check (auth.uid() = user_id);
drop policy if exists "unlike as yourself" on public.post_likes;
create policy "unlike as yourself" on public.post_likes for delete to authenticated
  using (auth.uid() = user_id);

create or replace function public.create_post(
  p_body text, p_vibe text default null, p_prompt text default null, p_hours int default null)
returns bigint language sql security invoker as $$
  insert into public.posts (author, body, vibe, prompt, expires_at)
  values (auth.uid(),
          left(trim(p_body), 500),
          nullif(p_vibe, ''),
          nullif(left(trim(coalesce(p_prompt, '')), 120), ''),
          case when p_hours is null or p_hours <= 0 then null
               else now() + make_interval(hours => p_hours) end)
  returning id;
$$;

create or replace function public.get_feed(p_vibe text default null, p_limit int default 40)
returns table (id bigint, author uuid, username text, display_name text, body text, vibe text,
               prompt text, age_seconds bigint, expires_in bigint, likes bigint, liked boolean)
language sql stable security invoker as $$
  select p.id, p.author, pr.username, pr.display_name, p.body, p.vibe, p.prompt,
         extract(epoch from (now() - p.created_at))::bigint,
         case when p.expires_at is null then null
              else extract(epoch from (p.expires_at - now()))::bigint end,
         (select count(*) from public.post_likes l where l.post_id = p.id),
         exists (select 1 from public.post_likes l where l.post_id = p.id and l.user_id = auth.uid())
  from public.posts p
  join public.profiles pr on pr.id = p.author
  where (p.expires_at is null or p.expires_at > now())
    and (p_vibe is null or p.vibe = p_vibe)
  order by p.created_at desc
  limit least(coalesce(p_limit, 40), 100);
$$;

create or replace function public.toggle_like(p_post bigint)
returns table (liked boolean, likes bigint)
language plpgsql security invoker as $$
begin
  delete from public.post_likes where post_id = p_post and user_id = auth.uid();
  if found then
    return query select false, (select count(*) from public.post_likes where post_id = p_post);
  else
    insert into public.post_likes (post_id, user_id) values (p_post, auth.uid());
    return query select true, (select count(*) from public.post_likes where post_id = p_post);
  end if;
end; $$;

grant execute on function public.create_post(text, text, text, int) to authenticated;
grant execute on function public.get_feed(text, int) to authenticated;
grant execute on function public.toggle_like(bigint) to authenticated;

notify pgrst, 'reload schema';
