-- Chatly update: lets a user delete their own account (Settings -> Delete account).
-- Run once in Supabase: SQL Editor -> New query -> Run. Safe to run again.
-- Deleting the auth user also deletes their profile and messages (foreign keys cascade).

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
