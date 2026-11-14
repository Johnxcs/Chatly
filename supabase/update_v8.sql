-- Chatly update: FORUM COMMUNITIES (communities, threads, replies, upvotes) + open messaging.
-- Run once in Supabase: SQL Editor -> New query -> Run. Requires update_v2..v7. Safe to run again.
-- Old friends/posts tables are left untouched (the app just stops using them).

-- ---------------------------------------------------------------- tables
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

-- ---------------------------------------------------------------- security: everyone signed in can read; all writes go through the functions below
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

-- ---------------------------------------------------------------- messaging: any member can message any member
drop policy if exists "send as yourself" on public.messages;
create policy "send as yourself" on public.messages for insert to authenticated
  with check (auth.uid() = sender and receiver <> sender);

-- bios are public in a forum
drop policy if exists "see bio of friends" on public.profile_bios;
drop policy if exists "bios are public" on public.profile_bios;
create policy "bios are public" on public.profile_bios for select to authenticated using (true);

-- ---------------------------------------------------------------- write functions
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

-- Posting in a community joins you to it
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

-- Authors can delete their own; the community's moderator can delete anything in it
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

-- ---------------------------------------------------------------- read functions
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

-- p_sort: 'new' or 'top'.  p_joined_only: only communities you joined.
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

-- Everyone on the forum (for messaging and search); presence respects "show when I'm active"
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

-- Your conversations: the latest message with each person
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

-- ---------------------------------------------------------------- starter communities
insert into public.communities (name, description)
select v.name, v.description
from (values
  ('General',       'Talk about anything. Be kind.'),
  ('Introductions', 'New here? Say hello and tell us about yourself.'),
  ('Help & Support','Ask questions and help each other out.'),
  ('Off Topic',     'Fun, hobbies and everything else.')
) as v(name, description)
where not exists (select 1 from public.communities c where lower(c.name) = lower(v.name));

-- ---------------------------------------------------------------- permissions
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
