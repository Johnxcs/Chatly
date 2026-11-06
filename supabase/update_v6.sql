-- Chatly update: friends (requests, suggestions), bios, friends-only chat / posts / profiles.
-- Run once in Supabase: SQL Editor -> New query -> Run. Requires update_v2..v5 to have been run. Safe to run again.

-- ---------------------------------------------------------------- friendships
create table if not exists public.friendships (
  id           bigint generated always as identity primary key,
  requester    uuid not null references public.profiles(id) on delete cascade,
  addressee    uuid not null references public.profiles(id) on delete cascade,
  status       text not null default 'pending' check (status in ('pending', 'accepted')),
  created_at   timestamptz not null default now(),
  responded_at timestamptz,
  check (requester <> addressee)
);
-- one row per pair, whoever asked first
create unique index if not exists friendships_pair_idx
  on public.friendships (least(requester, addressee), greatest(requester, addressee));
create index if not exists friendships_addressee_idx on public.friendships (addressee, status);

alter table public.friendships enable row level security;
drop policy if exists "see own friendships" on public.friendships;
create policy "see own friendships" on public.friendships for select to authenticated
  using (auth.uid() in (requester, addressee));
-- no insert/update/delete policies: changes go through the functions below

create or replace function public.are_friends(a uuid, b uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.friendships f
    where f.status = 'accepted'
      and ((f.requester = a and f.addressee = b) or (f.requester = b and f.addressee = a)));
$$;

-- People who have already exchanged messages stay friends, so existing chats keep working
insert into public.friendships (requester, addressee, status, responded_at)
select distinct on (least(sender, receiver), greatest(sender, receiver)) sender, receiver, 'accepted', now()
from public.messages
where sender <> receiver
order by least(sender, receiver), greatest(sender, receiver), id
on conflict do nothing;

-- ---------------------------------------------------------------- friends-only chat and posts
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

-- ---------------------------------------------------------------- bios (visible to friends only)
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

-- ---------------------------------------------------------------- friend actions
-- returns the new relationship: 'outgoing' | 'friends' | 'none'
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

-- cancel a request you sent, or unfriend
create or replace function public.remove_friend(p_user uuid) returns text
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from public.friendships
   where (requester = auth.uid() and addressee = p_user) or (requester = p_user and addressee = auth.uid());
  return 'none';
end; $$;

-- ---------------------------------------------------------------- people list with friendship state + mutual friends
-- Presence and notes are only revealed for friends.
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

-- One person's profile. Bio, counts and posts are only returned for yourself and your friends.
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

-- Feed, now optionally for one author (the posts policy above already limits it to you + friends)
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
