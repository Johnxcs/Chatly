-- Run this once in Supabase: SQL Editor -> New query -> Run

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
