-- Opcional, mas recomendado se você já rodou versões antigas deste app.
-- ATENÇÃO: apaga as tabelas públicas deste app.
-- Não tenta apagar storage.objects, porque o Supabase bloqueia exclusão direta
-- dessas tabelas. Para limpar arquivos antigos, use Storage > memories no painel
-- do Supabase ou a Storage API.

begin;

drop table if exists public.media cascade;
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
