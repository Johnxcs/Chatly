-- Chatly update: the Home feed (posts, vibes, vanishing posts, likes).
-- Run once in Supabase: SQL Editor -> New query -> Run. Safe to run again.

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

-- Create a post. p_hours = how long it lives (null or 0 = never vanishes). Times use the server clock.
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

-- The feed: live posts, newest first, optionally filtered by vibe
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

-- Like / unlike in one call; returns the new state and count
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
