-- Atualização sem apagar dados: relacionar momentos da Timeline com lugares do Mapa.
-- Rode no SQL Editor se você já tem o app instalado e não quer resetar o banco.

alter table public.timeline_entries
add column if not exists place_id uuid;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'timeline_entries_place_id_fkey'
      and conrelid = 'public.timeline_entries'::regclass
  ) then
    alter table public.timeline_entries
    add constraint timeline_entries_place_id_fkey
    foreign key (place_id) references public.places(id) on delete set null;
  end if;
end $$;

create index if not exists idx_timeline_place
on public.timeline_entries(group_id, place_id);


-- Endereço textual dos lugares, para aparecer no popup do mapa.
alter table public.places
add column if not exists address text;

-- Localização compartilhada de cada membro por grupo.
create table if not exists public.member_locations (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.app_users(id) on delete cascade,
  latitude numeric(10, 7) not null,
  longitude numeric(10, 7) not null,
  address text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (group_id, user_id)
);

create index if not exists idx_member_locations_group
on public.member_locations(group_id, updated_at desc);

create index if not exists idx_member_locations_user
on public.member_locations(user_id);

alter table public.member_locations enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgname = 'set_member_locations_updated_at'
      and tgrelid = 'public.member_locations'::regclass
  ) then
    create trigger set_member_locations_updated_at
    before update on public.member_locations
    for each row execute function public.set_updated_at();
  end if;
end $$;
