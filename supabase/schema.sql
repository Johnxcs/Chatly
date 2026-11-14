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

-- ===== v6: friends, bios =====
create table if not exists public.friendships (
  id           bigint generated always as identity primary key,
  requester    uuid not null references public.profiles(id) on delete cascade,
  addressee    uuid not null references public.profiles(id) on delete cascade,
  status       text not null default 'pending' check (status in ('pending', 'accepted')),
  created_at   timestamptz not null default now(),
  responded_at timestamptz,
  check (requester <> addressee)
);
create unique index if not exists friendships_pair_idx
  on public.friendships (least(requester, addressee), greatest(requester, addressee));
create index if not exists friendships_addressee_idx on public.friendships (addressee, status);

alter table public.friendships enable row level security;
drop policy if exists "see own friendships" on public.friendships;
create policy "see own friendships" on public.friendships for select to authenticated
  using (auth.uid() in (requester, addressee));

create or replace function public.are_friends(a uuid, b uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.friendships f
    where f.status = 'accepted'
      and ((f.requester = a and f.addressee = b) or (f.requester = b and f.addressee = a)));
$$;

insert into public.friendships (requester, addressee, status, responded_at)
select distinct on (least(sender, receiver), greatest(sender, receiver)) sender, receiver, 'accepted', now()
from public.messages
where sender <> receiver
order by least(sender, receiver), greatest(sender, receiver), id
on conflict do nothing;

drop policy if exists "send as yourself" on public.messages;
create policy "send as yourself" on public.messages for insert to authenticated
  with check (auth.uid() = sender and public.are_friends(sender, receiver));

drop policy if exists "read live posts" on public.posts;
create policy "read live posts" on public.posts for select to authenticated
  using ((expires_at is null or expires_at > now())
         and (author = auth.uid() or public.are_friends(author, auth.uid())));

drop policy if exists "like as yourself" on public.post_likes;
create policy "like as yourself" on public.post_likes for insert to authenticated
  with check (auth.uid() = user_id and exists (select 1 from public.posts p where p.id = post_id));

create table if not exists public.profile_bios (
  user_id    uuid primary key references public.profiles(id) on delete cascade,
  bio        text check (bio is null or char_length(bio) <= 150),
  updated_at timestamptz not null default now()
);
alter table public.profile_bios enable row level security;
drop policy if exists "see bio of friends" on public.profile_bios;
create policy "see bio of friends" on public.profile_bios for select to authenticated
  using (user_id = auth.uid() or public.are_friends(user_id, auth.uid()));
drop policy if exists "write own bio" on public.profile_bios;
create policy "write own bio" on public.profile_bios for insert to authenticated
  with check (user_id = auth.uid());
drop policy if exists "update own bio" on public.profile_bios;
create policy "update own bio" on public.profile_bios for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create or replace function public.set_bio(p_bio text) returns void
language sql security invoker as $$
  insert into public.profile_bios (user_id, bio, updated_at)
  values (auth.uid(), nullif(left(trim(coalesce(p_bio, '')), 150), ''), now())
  on conflict (user_id) do update set bio = excluded.bio, updated_at = now();
$$;

create or replace function public.send_friend_request(p_user uuid) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); f public.friendships;
begin
  if me is null then raise exception 'not signed in'; end if;
  if p_user is null or p_user = me then raise exception 'invalid user'; end if;
  select * into f from public.friendships
   where (requester = me and addressee = p_user) or (requester = p_user and addressee = me);
  if found then
    if f.status = 'accepted' then return 'friends'; end if;
    if f.requester = p_user then      -- they already asked you: that makes you friends
      update public.friendships set status = 'accepted', responded_at = now() where id = f.id;
      return 'friends';
    end if;
    return 'outgoing';
  end if;
  insert into public.friendships (requester, addressee) values (me, p_user);
  return 'outgoing';
end; $$;

create or replace function public.respond_friend_request(p_user uuid, p_accept boolean) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid();
begin
  if me is null then raise exception 'not signed in'; end if;
  if p_accept then
    update public.friendships set status = 'accepted', responded_at = now()
     where requester = p_user and addressee = me and status = 'pending';
    if found then return 'friends'; end if;
    return 'none';
  end if;
  delete from public.friendships where requester = p_user and addressee = me and status = 'pending';
  return 'none';
end; $$;

create or replace function public.remove_friend(p_user uuid) returns text
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from public.friendships
   where (requester = auth.uid() and addressee = p_user) or (requester = p_user and addressee = auth.uid());
  return 'none';
end; $$;

drop function if exists public.get_people();
create function public.get_people()
returns table (id uuid, username text, display_name text, seconds_ago bigint, note text,
               status text, mutual bigint)
language sql stable security definer set search_path = public as $$
  with rel as (
    select case when f.requester = auth.uid() then f.addressee else f.requester end as other_id,
           f.status as fstatus, f.requester as fromwho
    from public.friendships f
    where auth.uid() in (f.requester, f.addressee)
  ), my_friends as (
    select other_id from rel where fstatus = 'accepted'
  )
  select p.id, p.username, p.display_name,
         case when r.fstatus = 'accepted' and p.show_active and p.last_seen is not null
              then extract(epoch from (now() - p.last_seen))::bigint end,
         case when r.fstatus = 'accepted' and p.note_at > now() - interval '24 hours' then p.note end,
         case when r.fstatus = 'accepted' then 'friends'
              when r.fstatus = 'pending' and r.fromwho = auth.uid() then 'outgoing'
              when r.fstatus = 'pending' then 'incoming'
              else 'none' end,
         (select count(*) from public.friendships f2
           where f2.status = 'accepted'
             and p.id in (f2.requester, f2.addressee)
             and (case when f2.requester = p.id then f2.addressee else f2.requester end)
                 in (select other_id from my_friends))
  from public.profiles p
  left join rel r on r.other_id = p.id
  where p.id <> auth.uid()
  order by coalesce(p.display_name, p.username);
$$;

create or replace function public.get_profile(p_user uuid)
returns table (id uuid, username text, display_name text, bio text, status text,
               mutual bigint, friends_count bigint, posts_count bigint)
language sql stable security definer set search_path = public as $$
  with st as (
    select case
             when p_user = auth.uid() then 'self'
             when public.are_friends(p_user, auth.uid()) then 'friends'
             when exists (select 1 from public.friendships f where f.status = 'pending'
                          and f.requester = auth.uid() and f.addressee = p_user) then 'outgoing'
             when exists (select 1 from public.friendships f where f.status = 'pending'
                          and f.requester = p_user and f.addressee = auth.uid()) then 'incoming'
             else 'none' end as s
  )
  select p.id, p.username, p.display_name,
         case when st.s in ('self', 'friends')
              then (select b.bio from public.profile_bios b where b.user_id = p.id) end,
         st.s,
         (select count(*) from public.friendships f2
           where f2.status = 'accepted'
             and p.id in (f2.requester, f2.addressee)
             and (case when f2.requester = p.id then f2.addressee else f2.requester end) in (
                   select case when f.requester = auth.uid() then f.addressee else f.requester end
                   from public.friendships f
                   where f.status = 'accepted' and auth.uid() in (f.requester, f.addressee))),
         case when st.s in ('self', 'friends')
              then (select count(*) from public.friendships f3
                     where f3.status = 'accepted' and p.id in (f3.requester, f3.addressee)) end,
         case when st.s in ('self', 'friends')
              then (select count(*) from public.posts x
                     where x.author = p.id and (x.expires_at is null or x.expires_at > now())) end
  from public.profiles p cross join st
  where p.id = p_user;
$$;

drop function if exists public.get_feed(text, int);
create or replace function public.get_feed(p_vibe text default null, p_limit int default 40,
                                           p_author uuid default null)
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
    and (p_author is null or p.author = p_author)
  order by p.created_at desc
  limit least(coalesce(p_limit, 40), 100);
$$;

revoke all on function public.send_friend_request(uuid) from public, anon;
revoke all on function public.respond_friend_request(uuid, boolean) from public, anon;
revoke all on function public.remove_friend(uuid) from public, anon;
revoke all on function public.get_people() from public, anon;
revoke all on function public.get_profile(uuid) from public, anon;
grant execute on function public.send_friend_request(uuid) to authenticated;
grant execute on function public.respond_friend_request(uuid, boolean) to authenticated;
grant execute on function public.remove_friend(uuid) to authenticated;
grant execute on function public.get_people() to authenticated;
grant execute on function public.get_profile(uuid) to authenticated;
grant execute on function public.set_bio(text) to authenticated;
grant execute on function public.get_feed(text, int, uuid) to authenticated;

notify pgrst, 'reload schema';

-- ===== v7: polls, streaks =====
alter table public.posts add column if not exists poll jsonb;   -- e.g. ["Pizza","Tacos"]; null = no poll

create table if not exists public.poll_votes (
  post_id    bigint not null references public.posts(id) on delete cascade,
  user_id    uuid   not null references public.profiles(id) on delete cascade,
  option_idx int    not null check (option_idx between 0 and 3),
  created_at timestamptz not null default now(),
  primary key (post_id, user_id)          -- one vote per person; changing your mind updates it
);
alter table public.poll_votes enable row level security;

drop policy if exists "see votes on visible posts" on public.poll_votes;
create policy "see votes on visible posts" on public.poll_votes for select to authenticated
  using (exists (select 1 from public.posts p where p.id = post_id));
drop policy if exists "vote as yourself" on public.poll_votes;
create policy "vote as yourself" on public.poll_votes for insert to authenticated
  with check (user_id = auth.uid() and exists (select 1 from public.posts p where p.id = post_id));
drop policy if exists "change own vote" on public.poll_votes;
create policy "change own vote" on public.poll_votes for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

drop function if exists public.create_post(text, text, text, int);
create or replace function public.create_post(
  p_body text, p_prompt text default null, p_poll jsonb default null)
returns bigint language plpgsql security invoker as $$
declare new_id bigint;
begin
  if p_poll is not null and (jsonb_typeof(p_poll) <> 'array'
                             or jsonb_array_length(p_poll) not between 2 and 4) then
    raise exception 'a poll needs 2 to 4 options';
  end if;
  insert into public.posts (author, body, prompt, poll)
  values (auth.uid(), left(trim(p_body), 500),
          nullif(left(trim(coalesce(p_prompt, '')), 120), ''), p_poll)
  returning id into new_id;
  return new_id;
end; $$;

create or replace function public.vote_poll(p_post bigint, p_option int) returns jsonb
language plpgsql security invoker as $$
begin
  if not exists (select 1 from public.posts p
                 where p.id = p_post and p.poll is not null
                   and p_option between 0 and jsonb_array_length(p.poll) - 1) then
    raise exception 'invalid poll option';
  end if;
  insert into public.poll_votes (post_id, user_id, option_idx)
  values (p_post, auth.uid(), p_option)
  on conflict (post_id, user_id) do update set option_idx = excluded.option_idx, created_at = now();
  return (select coalesce(jsonb_object_agg(v.option_idx::text, v.n), '{}'::jsonb)
            from (select option_idx, count(*) as n from public.poll_votes
                   where post_id = p_post group by option_idx) v);
end; $$;

drop function if exists public.get_feed(text, int, uuid);
create or replace function public.get_feed(p_limit int default 40, p_author uuid default null)
returns table (id bigint, author uuid, username text, display_name text, body text, prompt text,
               age_seconds bigint, likes bigint, liked boolean, poll jsonb, votes jsonb, my_vote int)
language sql stable security invoker as $$
  select p.id, p.author, pr.username, pr.display_name, p.body, p.prompt,
         extract(epoch from (now() - p.created_at))::bigint,
         (select count(*) from public.post_likes l where l.post_id = p.id),
         exists (select 1 from public.post_likes l where l.post_id = p.id and l.user_id = auth.uid()),
         p.poll,
         case when p.poll is null then null else
           (select coalesce(jsonb_object_agg(v.option_idx::text, v.n), '{}'::jsonb)
              from (select option_idx, count(*) as n from public.poll_votes
                     where post_id = p.id group by option_idx) v) end,
         (select pv.option_idx from public.poll_votes pv
           where pv.post_id = p.id and pv.user_id = auth.uid())
  from public.posts p
  join public.profiles pr on pr.id = p.author
  where (p.expires_at is null or p.expires_at > now())
    and (p_author is null or p.author = p_author)
  order by p.created_at desc
  limit least(coalesce(p_limit, 40), 100);
$$;

create or replace function public.get_streaks()
returns table (friend uuid, days int)
language sql stable security invoker as $$
  with per_day as (
    select case when m.sender = auth.uid() then m.receiver else m.sender end as friend,
           (m.created_at at time zone 'utc')::date as d,
           bool_or(m.sender = auth.uid()) as i_sent,
           bool_or(m.sender <> auth.uid()) as they_sent
    from public.messages m
    where auth.uid() in (m.sender, m.receiver)
    group by 1, 2
  ), both_days as (
    select friend, d from per_day where i_sent and they_sent
  ), numbered as (
    select friend, d, d - (row_number() over (partition by friend order by d))::int as grp
    from both_days
  ), runs as (
    select friend, count(*)::int as days, max(d) as last_day from numbered group by friend, grp
  )
  select friend, days from runs
  where last_day >= (now() at time zone 'utc')::date - 1
  order by days desc;
$$;

grant execute on function public.create_post(text, text, jsonb) to authenticated;
grant execute on function public.vote_poll(bigint, int) to authenticated;
grant execute on function public.get_feed(int, uuid) to authenticated;
grant execute on function public.get_streaks() to authenticated;

notify pgrst, 'reload schema';

-- ===== v8: forum =====
create table if not exists public.communities (
  id          bigint generated always as identity primary key,
  name        text not null check (char_length(name) between 3 and 30),
  description text check (description is null or char_length(description) <= 200),
  owner       uuid references public.profiles(id) on delete set null,   -- the moderator
  created_at  timestamptz not null default now()
);
create unique index if not exists communities_name_idx on public.communities (lower(name));

create table if not exists public.community_members (
  community_id bigint not null references public.communities(id) on delete cascade,
  user_id      uuid   not null references public.profiles(id) on delete cascade,
  joined_at    timestamptz not null default now(),
  primary key (community_id, user_id)
);
create index if not exists community_members_user_idx on public.community_members (user_id);

create table if not exists public.threads (
  id           bigint generated always as identity primary key,
  community_id bigint not null references public.communities(id) on delete cascade,
  author       uuid   not null references public.profiles(id) on delete cascade,
  title        text   not null check (char_length(title) between 3 and 120),
  body         text   not null check (char_length(body) between 1 and 2000),
  created_at   timestamptz not null default now()
);
create index if not exists threads_community_idx on public.threads (community_id, created_at desc);
create index if not exists threads_author_idx on public.threads (author, created_at desc);

create table if not exists public.replies (
  id         bigint generated always as identity primary key,
  thread_id  bigint not null references public.threads(id) on delete cascade,
  author     uuid   not null references public.profiles(id) on delete cascade,
  body       text   not null check (char_length(body) between 1 and 1000),
  created_at timestamptz not null default now()
);
create index if not exists replies_thread_idx on public.replies (thread_id, created_at);

create table if not exists public.thread_votes (
  thread_id bigint not null references public.threads(id) on delete cascade,
  user_id   uuid   not null references public.profiles(id) on delete cascade,
  primary key (thread_id, user_id)
);
create table if not exists public.reply_votes (
  reply_id bigint not null references public.replies(id) on delete cascade,
  user_id  uuid   not null references public.profiles(id) on delete cascade,
  primary key (reply_id, user_id)
);

alter table public.communities       enable row level security;
alter table public.community_members enable row level security;
alter table public.threads           enable row level security;
alter table public.replies           enable row level security;
alter table public.thread_votes      enable row level security;
alter table public.reply_votes       enable row level security;

do $$
declare t text;
begin
  foreach t in array array['communities','community_members','threads','replies','thread_votes','reply_votes'] loop
    execute format('drop policy if exists "read all" on public.%I', t);
    execute format('create policy "read all" on public.%I for select to authenticated using (true)', t);
  end loop;
end $$;

drop policy if exists "send as yourself" on public.messages;
create policy "send as yourself" on public.messages for insert to authenticated
  with check (auth.uid() = sender and receiver <> sender);

drop policy if exists "see bio of friends" on public.profile_bios;
drop policy if exists "bios are public" on public.profile_bios;
create policy "bios are public" on public.profile_bios for select to authenticated using (true);

create or replace function public.create_community(p_name text, p_description text default null)
returns bigint language plpgsql security definer set search_path = public as $$
declare new_id bigint;
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  insert into public.communities (name, description, owner)
  values (trim(p_name), nullif(trim(coalesce(p_description, '')), ''), auth.uid())
  returning id into new_id;
  insert into public.community_members (community_id, user_id) values (new_id, auth.uid());
  return new_id;
end; $$;

create or replace function public.join_community(p_id bigint) returns void
language sql security definer set search_path = public as $$
  insert into public.community_members (community_id, user_id)
  select p_id, auth.uid() where auth.uid() is not null and exists (select 1 from public.communities where id = p_id)
  on conflict do nothing;
$$;

create or replace function public.leave_community(p_id bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.communities where id = p_id and owner = auth.uid()) then
    raise exception 'moderators cannot leave their own community';
  end if;
  delete from public.community_members where community_id = p_id and user_id = auth.uid();
end; $$;

create or replace function public.create_thread(p_community bigint, p_title text, p_body text)
returns bigint language plpgsql security definer set search_path = public as $$
declare new_id bigint;
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  if not exists (select 1 from public.communities where id = p_community) then
    raise exception 'that community does not exist';
  end if;
  insert into public.threads (community_id, author, title, body)
  values (p_community, auth.uid(), left(trim(p_title), 120), left(trim(p_body), 2000))
  returning id into new_id;
  insert into public.community_members (community_id, user_id) values (p_community, auth.uid())
  on conflict do nothing;
  return new_id;
end; $$;

create or replace function public.create_reply(p_thread bigint, p_body text)
returns bigint language plpgsql security definer set search_path = public as $$
declare new_id bigint;
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  if not exists (select 1 from public.threads where id = p_thread) then
    raise exception 'that thread does not exist';
  end if;
  insert into public.replies (thread_id, author, body)
  values (p_thread, auth.uid(), left(trim(p_body), 1000))
  returning id into new_id;
  return new_id;
end; $$;

create or replace function public.delete_thread(p_thread bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from public.threads t join public.communities c on c.id = t.community_id
                 where t.id = p_thread and (t.author = auth.uid() or c.owner = auth.uid())) then
    raise exception 'not allowed';
  end if;
  delete from public.threads where id = p_thread;
end; $$;

create or replace function public.delete_reply(p_reply bigint) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from public.replies r
                 join public.threads t on t.id = r.thread_id
                 join public.communities c on c.id = t.community_id
                 where r.id = p_reply and (r.author = auth.uid() or c.owner = auth.uid())) then
    raise exception 'not allowed';
  end if;
  delete from public.replies where id = p_reply;
end; $$;

create or replace function public.toggle_thread_vote(p_thread bigint)
returns table (voted boolean, votes bigint)
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from public.thread_votes where thread_id = p_thread and user_id = auth.uid();
  if found then
    return query select false, (select count(*) from public.thread_votes where thread_id = p_thread);
    return;  -- stop here: do not re-add the vote
  end if;
  insert into public.thread_votes (thread_id, user_id) values (p_thread, auth.uid());
  return query select true, (select count(*) from public.thread_votes where thread_id = p_thread);
end; $$;

create or replace function public.toggle_reply_vote(p_reply bigint)
returns table (voted boolean, votes bigint)
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from public.reply_votes where reply_id = p_reply and user_id = auth.uid();
  if found then
    return query select false, (select count(*) from public.reply_votes where reply_id = p_reply);
    return;  -- stop here: do not re-add the vote
  end if;
  insert into public.reply_votes (reply_id, user_id) values (p_reply, auth.uid());
  return query select true, (select count(*) from public.reply_votes where reply_id = p_reply);
end; $$;

create or replace function public.get_communities()
returns table (id bigint, name text, description text, members bigint, joined boolean, mine boolean)
language sql stable security invoker as $$
  select c.id, c.name, c.description,
         (select count(*) from public.community_members m where m.community_id = c.id),
         exists (select 1 from public.community_members m where m.community_id = c.id and m.user_id = auth.uid()),
         (c.owner = auth.uid())
  from public.communities c
  order by 5 desc, 4 desc, c.name
  limit 300;
$$;

create or replace function public.get_threads(
  p_community bigint default null, p_author uuid default null, p_sort text default 'new',
  p_joined_only boolean default false, p_limit int default 30)
returns table (id bigint, community_id bigint, community_name text, author uuid, username text,
               display_name text, title text, snippet text, age_seconds bigint,
               votes bigint, replies bigint, voted boolean)
language sql stable security invoker as $$
  select t.id, t.community_id, c.name, t.author, pr.username, pr.display_name, t.title,
         left(t.body, 240),
         extract(epoch from (now() - t.created_at))::bigint,
         (select count(*) from public.thread_votes v where v.thread_id = t.id),
         (select count(*) from public.replies r where r.thread_id = t.id),
         exists (select 1 from public.thread_votes v where v.thread_id = t.id and v.user_id = auth.uid())
  from public.threads t
  join public.communities c on c.id = t.community_id
  join public.profiles pr on pr.id = t.author
  where (p_community is null or t.community_id = p_community)
    and (p_author is null or t.author = p_author)
    and (not coalesce(p_joined_only, false)
         or exists (select 1 from public.community_members m
                    where m.community_id = t.community_id and m.user_id = auth.uid()))
  order by case when p_sort = 'top'
                then (select count(*) from public.thread_votes v where v.thread_id = t.id) end desc nulls last,
           t.created_at desc
  limit least(coalesce(p_limit, 30), 100);
$$;

create or replace function public.get_thread(p_thread bigint)
returns table (id bigint, community_id bigint, community_name text, author uuid, username text,
               display_name text, title text, body text, age_seconds bigint,
               votes bigint, replies bigint, voted boolean, can_delete boolean)
language sql stable security invoker as $$
  select t.id, t.community_id, c.name, t.author, pr.username, pr.display_name, t.title, t.body,
         extract(epoch from (now() - t.created_at))::bigint,
         (select count(*) from public.thread_votes v where v.thread_id = t.id),
         (select count(*) from public.replies r where r.thread_id = t.id),
         exists (select 1 from public.thread_votes v where v.thread_id = t.id and v.user_id = auth.uid()),
         (t.author = auth.uid() or c.owner = auth.uid())
  from public.threads t
  join public.communities c on c.id = t.community_id
  join public.profiles pr on pr.id = t.author
  where t.id = p_thread;
$$;

create or replace function public.get_replies(p_thread bigint)
returns table (id bigint, author uuid, username text, display_name text, body text,
               age_seconds bigint, votes bigint, voted boolean, can_delete boolean)
language sql stable security invoker as $$
  select r.id, r.author, pr.username, pr.display_name, r.body,
         extract(epoch from (now() - r.created_at))::bigint,
         (select count(*) from public.reply_votes v where v.reply_id = r.id),
         exists (select 1 from public.reply_votes v where v.reply_id = r.id and v.user_id = auth.uid()),
         (r.author = auth.uid() or c.owner = auth.uid())
  from public.replies r
  join public.threads t on t.id = r.thread_id
  join public.communities c on c.id = t.community_id
  join public.profiles pr on pr.id = r.author
  where r.thread_id = p_thread
  order by r.created_at
  limit 300;
$$;

drop function if exists public.get_people();
create function public.get_people()
returns table (id uuid, username text, display_name text, seconds_ago bigint)
language sql stable security invoker as $$
  select p.id, p.username, p.display_name,
         case when p.show_active and p.last_seen is not null
              then extract(epoch from (now() - p.last_seen))::bigint end
  from public.profiles p
  where p.id <> auth.uid()
  order by coalesce(p.display_name, p.username);
$$;

drop function if exists public.get_profile(uuid);
create function public.get_profile(p_user uuid)
returns table (id uuid, username text, display_name text, bio text,
               threads_count bigint, replies_count bigint, communities_count bigint)
language sql stable security invoker as $$
  select p.id, p.username, p.display_name,
         (select b.bio from public.profile_bios b where b.user_id = p.id),
         (select count(*) from public.threads t where t.author = p.id),
         (select count(*) from public.replies r where r.author = p.id),
         (select count(*) from public.community_members m where m.user_id = p.id)
  from public.profiles p
  where p.id = p_user;
$$;

create or replace function public.get_conversations()
returns table (partner uuid, last_id bigint, sender uuid, last_text text)
language sql stable security invoker as $$
  select distinct on (m.partner) m.partner, m.id, m.sender, m.text
  from (select case when x.sender = auth.uid() then x.receiver else x.sender end as partner,
               x.id, x.sender, x.text
        from public.messages x
        where auth.uid() in (x.sender, x.receiver)) m
  order by m.partner, m.id desc;
$$;

insert into public.communities (name, description)
select v.name, v.description
from (values
  ('General',       'Talk about anything. Be kind.'),
  ('Introductions', 'New here? Say hello and tell us about yourself.'),
  ('Help & Support','Ask questions and help each other out.'),
  ('Off Topic',     'Fun, hobbies and everything else.')
) as v(name, description)
where not exists (select 1 from public.communities c where lower(c.name) = lower(v.name));

revoke all on function public.create_community(text, text)   from public, anon;
revoke all on function public.join_community(bigint)         from public, anon;
revoke all on function public.leave_community(bigint)        from public, anon;
revoke all on function public.create_thread(bigint, text, text) from public, anon;
revoke all on function public.create_reply(bigint, text)     from public, anon;
revoke all on function public.delete_thread(bigint)          from public, anon;
revoke all on function public.delete_reply(bigint)           from public, anon;
revoke all on function public.toggle_thread_vote(bigint)     from public, anon;
revoke all on function public.toggle_reply_vote(bigint)      from public, anon;
grant execute on function public.create_community(text, text)   to authenticated;
grant execute on function public.join_community(bigint)         to authenticated;
grant execute on function public.leave_community(bigint)        to authenticated;
grant execute on function public.create_thread(bigint, text, text) to authenticated;
grant execute on function public.create_reply(bigint, text)     to authenticated;
grant execute on function public.delete_thread(bigint)          to authenticated;
grant execute on function public.delete_reply(bigint)           to authenticated;
grant execute on function public.toggle_thread_vote(bigint)     to authenticated;
grant execute on function public.toggle_reply_vote(bigint)      to authenticated;
grant execute on function public.get_communities()              to authenticated;
grant execute on function public.get_threads(bigint, uuid, text, boolean, int) to authenticated;
grant execute on function public.get_thread(bigint)             to authenticated;
grant execute on function public.get_replies(bigint)            to authenticated;
grant execute on function public.get_people()                   to authenticated;
grant execute on function public.get_profile(uuid)              to authenticated;
grant execute on function public.get_conversations()            to authenticated;

notify pgrst, 'reload schema';
