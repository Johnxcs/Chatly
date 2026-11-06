-- Chatly update: polls on posts + chat streaks. This replaces the old "vibes" and "vanishing posts" features.
-- Run once in Supabase: SQL Editor -> New query -> Run. Requires update_v2..v6. Safe to run again.

-- ---------------------------------------------------------------- polls
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

-- New create_post: text, optional question-of-the-day prompt, optional poll (2 to 4 options)
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

-- Vote (or change your vote); returns the vote counts per option, e.g. {"0": 3, "1": 5}
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

-- Feed: posts from you and your friends, with poll results and your own vote
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

-- ---------------------------------------------------------------- chat streaks
-- A day counts when BOTH of you sent at least one message (UTC days). A streak is the run of
-- consecutive counting days that includes today or yesterday.
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
