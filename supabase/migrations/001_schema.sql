-- Presente Vii: schema para Streamlit + Supabase com autenticação simples por usuário/senha.
-- Rode no SQL Editor do Supabase após 000_reset_previous_version.sql se já existirem tabelas antigas.

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

create table if not exists public.app_users (
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

create table if not exists public.groups (
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

create table if not exists public.group_members (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  user_id uuid not null references public.app_users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'admin', 'member')),
  joined_at timestamptz not null default now(),
  unique (group_id, user_id)
);

create table if not exists public.timeline_entries (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  title text not null,
  body text,
  occurred_on date,
  tags text[] not null default '{}',
  sort_order integer not null default 0,
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.places (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.groups(id) on delete cascade,
  title text not null,
  description text,
  latitude numeric(10, 7) not null,
  longitude numeric(10, 7) not null,
  visited_on date,
  tags text[] not null default '{}',
  created_by uuid references public.app_users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.playlists (
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

create table if not exists public.open_when_letters (
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

create table if not exists public.media (
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

create index if not exists idx_group_members_user_id on public.group_members(user_id);
create index if not exists idx_group_members_group_id on public.group_members(group_id);
create index if not exists idx_timeline_group_date on public.timeline_entries(group_id, occurred_on desc);
create index if not exists idx_places_group_date on public.places(group_id, visited_on desc);
create index if not exists idx_playlists_group_updated on public.playlists(group_id, updated_at desc);
create index if not exists idx_letters_group_unlock on public.open_when_letters(group_id, unlock_at desc);
create index if not exists idx_letters_recipient on public.open_when_letters(recipient_user_id);
create index if not exists idx_media_related on public.media(group_id, related_table, related_id, sort_order);

create or replace trigger set_app_users_updated_at
before update on public.app_users
for each row execute function public.set_updated_at();

create or replace trigger set_groups_updated_at
before update on public.groups
for each row execute function public.set_updated_at();

create or replace trigger set_timeline_entries_updated_at
before update on public.timeline_entries
for each row execute function public.set_updated_at();

create or replace trigger set_places_updated_at
before update on public.places
for each row execute function public.set_updated_at();

create or replace trigger set_playlists_updated_at
before update on public.playlists
for each row execute function public.set_updated_at();

create or replace trigger set_open_when_letters_updated_at
before update on public.open_when_letters
for each row execute function public.set_updated_at();
