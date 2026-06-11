-- Este MVP usa autenticação simples própria no Streamlit e service_role apenas no servidor.
-- Mantemos RLS ativado e sem policies públicas para impedir acesso com anon/publishable key.
-- A service_role key bypassa RLS; por isso ela deve ficar somente em secrets do servidor Streamlit.

alter table public.app_users enable row level security;
alter table public.groups enable row level security;
alter table public.group_members enable row level security;
alter table public.timeline_entries enable row level security;
alter table public.places enable row level security;
alter table public.playlists enable row level security;
alter table public.open_when_letters enable row level security;
alter table public.media enable row level security;
