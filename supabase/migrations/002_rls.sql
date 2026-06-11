-- RLS and authorization helpers.
-- Keep this app private: only authenticated users in the same couple can read.
-- Only admin profile for the couple can create/update/delete content.

alter table public.couples enable row level security;
alter table public.profiles enable row level security;
alter table public.timeline_entries enable row level security;
alter table public.places enable row level security;
alter table public.playlists enable row level security;
alter table public.open_when_letters enable row level security;
alter table public.media enable row level security;

create or replace function public.current_couple_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select couple_id from public.profiles where id = auth.uid()
$$;

create or replace function public.is_admin_for_couple(target_couple_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.couple_id = target_couple_id
      and p.role = 'admin'
  )
$$;

-- Drop old policies for idempotent local reruns.
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('couples','profiles','timeline_entries','places','playlists','open_when_letters','media')
  LOOP
    EXECUTE format('drop policy if exists %I on %I.%I', r.policyname, r.schemaname, r.tablename);
  END LOOP;
END $$;

create policy "couples_select_same_couple"
  on public.couples for select to authenticated
  using (id = public.current_couple_id());

create policy "couples_update_admin"
  on public.couples for update to authenticated
  using (public.is_admin_for_couple(id))
  with check (public.is_admin_for_couple(id));

create policy "profiles_select_same_couple"
  on public.profiles for select to authenticated
  using (couple_id = public.current_couple_id());

create policy "profiles_update_self_or_admin"
  on public.profiles for update to authenticated
  using (id = auth.uid() or public.is_admin_for_couple(couple_id))
  with check (id = auth.uid() or public.is_admin_for_couple(couple_id));

create policy "timeline_select_same_couple"
  on public.timeline_entries for select to authenticated
  using (couple_id = public.current_couple_id());

create policy "timeline_insert_admin"
  on public.timeline_entries for insert to authenticated
  with check (public.is_admin_for_couple(couple_id));

create policy "timeline_update_admin"
  on public.timeline_entries for update to authenticated
  using (public.is_admin_for_couple(couple_id))
  with check (public.is_admin_for_couple(couple_id));

create policy "timeline_delete_admin"
  on public.timeline_entries for delete to authenticated
  using (public.is_admin_for_couple(couple_id));

create policy "places_select_same_couple"
  on public.places for select to authenticated
  using (couple_id = public.current_couple_id());

create policy "places_insert_admin"
  on public.places for insert to authenticated
  with check (public.is_admin_for_couple(couple_id));

create policy "places_update_admin"
  on public.places for update to authenticated
  using (public.is_admin_for_couple(couple_id))
  with check (public.is_admin_for_couple(couple_id));

create policy "places_delete_admin"
  on public.places for delete to authenticated
  using (public.is_admin_for_couple(couple_id));

create policy "playlists_select_same_couple"
  on public.playlists for select to authenticated
  using (couple_id = public.current_couple_id());

create policy "playlists_insert_admin"
  on public.playlists for insert to authenticated
  with check (public.is_admin_for_couple(couple_id));

create policy "playlists_update_admin"
  on public.playlists for update to authenticated
  using (public.is_admin_for_couple(couple_id))
  with check (public.is_admin_for_couple(couple_id));

create policy "playlists_delete_admin"
  on public.playlists for delete to authenticated
  using (public.is_admin_for_couple(couple_id));

create policy "letters_select_same_couple"
  on public.open_when_letters for select to authenticated
  using (couple_id = public.current_couple_id() and is_active = true);

create policy "letters_insert_admin"
  on public.open_when_letters for insert to authenticated
  with check (public.is_admin_for_couple(couple_id));

create policy "letters_update_admin"
  on public.open_when_letters for update to authenticated
  using (public.is_admin_for_couple(couple_id))
  with check (public.is_admin_for_couple(couple_id));

create policy "letters_delete_admin"
  on public.open_when_letters for delete to authenticated
  using (public.is_admin_for_couple(couple_id));

create policy "media_select_same_couple"
  on public.media for select to authenticated
  using (couple_id = public.current_couple_id());

create policy "media_insert_admin"
  on public.media for insert to authenticated
  with check (public.is_admin_for_couple(couple_id));

create policy "media_update_admin"
  on public.media for update to authenticated
  using (public.is_admin_for_couple(couple_id))
  with check (public.is_admin_for_couple(couple_id));

create policy "media_delete_admin"
  on public.media for delete to authenticated
  using (public.is_admin_for_couple(couple_id));
