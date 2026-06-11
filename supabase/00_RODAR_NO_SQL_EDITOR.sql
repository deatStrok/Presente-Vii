-- Presente Vii - instalação limpa em UM arquivo.
-- Use este arquivo se você está vendo erros como:
-- relation "public.app_users" does not exist
-- column "group_id" does not exist
-- Direct deletion from storage tables is not allowed
--
-- ATENÇÃO: este script apaga as tabelas públicas deste app e recria tudo.
-- Ele NÃO apaga arquivos do Storage; se quiser limpar arquivos antigos, use
-- Storage > memories no painel do Supabase ou a Storage API.

begin;

drop table if exists public.media cascade;
drop table if exists public.member_locations cascade;
drop table if exists public.open_when_letters cascade;
drop table if exists public.playlists cascade;
drop table if exists public.places cascade;
drop table if exists public.timeline_entries cascade;
drop table if exists public.group_members cascade;
drop table if exists public.groups cascade;
drop table if exists public.app_users cascade;
drop table if exists public.profiles cascade;
drop table if exists public.couples cascade;

drop function if exists public.set_updated_at() cascade;

commit;

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.app_users (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  username_normalized text not null unique,
  display_name text not null,
  avatar_emoji text default '💌',
  password_hash text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login_at timestamptz,
  constraint app_users_username_format check (username_normalized ~ '^[a-z0-9_.-]{3,24}$'),
  constraint app_users_password_hash_not_plain check (
    password_hash like 'pbkdf2_sha256$%'
    or password_hash like '$argon2%'
  )
);

create table public.groups (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  theme_color text not null default 'verde' check (theme_color in ('azul', 'verde', 'rosa')),
  invite_code text not null unique,
  is_active boolean not null default true,
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.group_members (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.app_users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'admin', 'member')),
  joined_at timestamptz not null default now(),
  unique (group_id, user_id)
);

create table public.member_locations (
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

create table public.timeline_entries (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  place_id uuid,
  title text not null,
  body text,
  occurred_on date,
  tags text[] not null default '{}',
  sort_order integer not null default 0,
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.places (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  title text not null,
  description text,
  address text,
  latitude numeric(10, 7) not null,
  longitude numeric(10, 7) not null,
  visited_on date,
  tags text[] not null default '{}',
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.playlists (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  title text not null,
  platform text not null default 'other' check (platform in ('spotify', 'youtube', 'apple_music', 'deezer', 'other')),
  url text not null,
  note text,
  tags text[] not null default '{}',
  created_by uuid references public.app_users(id) on delete set null,
  updated_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.open_when_letters (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  title text not null,
  trigger_label text not null,
  body text not null,
  unlock_at timestamptz not null,
  audience_type text not null default 'all' check (audience_type in ('all', 'specific')),
  recipient_user_id uuid references public.app_users(id) on delete set null,
  is_active boolean not null default true,
  tags text[] not null default '{}',
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint specific_letter_has_recipient check (
    (audience_type = 'all' and recipient_user_id is null)
    or (audience_type = 'specific' and recipient_user_id is not null)
  )
);

create table public.media (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  related_table text not null,
  related_id uuid,
  type text not null check (type in ('image', 'audio', 'video')),
  mime_type text,
  storage_bucket text not null default 'memories',
  storage_path text not null unique,
  caption text,
  sort_order integer not null default 0,
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now()
);


alter table public.timeline_entries
add constraint timeline_entries_place_id_fkey
foreign key (place_id) references public.places(id) on delete set null;

create index idx_group_members_user_id on public.group_members(user_id);
create index idx_group_members_group_id on public.group_members(group_id);
create index idx_member_locations_group on public.member_locations(group_id, updated_at desc);
create index idx_member_locations_user on public.member_locations(user_id);
create index idx_timeline_group_date on public.timeline_entries(group_id, occurred_on desc);
create index idx_timeline_place on public.timeline_entries(group_id, place_id);
create index idx_places_group_date on public.places(group_id, visited_on desc);
create index idx_playlists_group_updated on public.playlists(group_id, updated_at desc);
create index idx_letters_group_unlock on public.open_when_letters(group_id, unlock_at desc);
create index idx_letters_recipient on public.open_when_letters(recipient_user_id);
create index idx_media_related on public.media(group_id, related_table, related_id, sort_order);

create trigger set_app_users_updated_at
before update on public.app_users
for each row execute function public.set_updated_at();

create trigger set_groups_updated_at
before update on public.groups
for each row execute function public.set_updated_at();

create trigger set_member_locations_updated_at
before update on public.member_locations
for each row execute function public.set_updated_at();

create trigger set_timeline_entries_updated_at
before update on public.timeline_entries
for each row execute function public.set_updated_at();

create trigger set_places_updated_at
before update on public.places
for each row execute function public.set_updated_at();

create trigger set_playlists_updated_at
before update on public.playlists
for each row execute function public.set_updated_at();

create trigger set_open_when_letters_updated_at
before update on public.open_when_letters
for each row execute function public.set_updated_at();

alter table public.app_users enable row level security;
alter table public.groups enable row level security;
alter table public.group_members enable row level security;
alter table public.member_locations enable row level security;
alter table public.timeline_entries enable row level security;
alter table public.places enable row level security;
alter table public.playlists enable row level security;
alter table public.open_when_letters enable row level security;
alter table public.media enable row level security;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'memories',
  'memories',
  false,
  209715200,
  array[
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/x-wav', 'audio/aac', 'audio/mp4',
    'video/mp4', 'video/webm', 'video/quicktime', 'video/mpeg'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
