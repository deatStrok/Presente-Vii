-- Seed opcional. Primeiro rode supabase/00_RODAR_NO_SQL_EDITOR.sql.
-- Depois crie o primeiro usuário pela tela do app.
-- Só então rode este arquivo para preencher o primeiro grupo com exemplos fictícios.

do $$
declare
  v_user_id uuid;
  v_group_id uuid;
begin
  if to_regclass('public.app_users') is null then
    raise notice 'Tabela public.app_users não existe. Rode supabase/00_RODAR_NO_SQL_EDITOR.sql primeiro.';
    return;
  end if;

  execute 'select id from public.app_users order by created_at asc limit 1' into v_user_id;
  if v_user_id is null then
    raise notice 'Nenhum app_user encontrado. Crie uma conta pela tela do Streamlit primeiro.';
    return;
  end if;

  execute 'select id from public.groups where created_by = $1 order by created_at asc limit 1' into v_group_id using v_user_id;
  if v_group_id is null then
    raise notice 'Nenhum grupo encontrado para o primeiro usuário.';
    return;
  end if;

  insert into public.timeline_entries (group_id, title, body, occurred_on, tags, created_by)
  values
    (v_group_id, 'Café X', 'Mesa no canto, luz quente e conversa que passou do horário.', current_date - 90, array['café','começo'], v_user_id),
    (v_group_id, 'Praia do Forte', 'Um dia de vento, mar e risadas pequenas que ficaram enormes.', current_date - 45, array['viagem','mar'], v_user_id);

  insert into public.places (group_id, title, description, latitude, longitude, visited_on, tags, created_by)
  values
    (v_group_id, 'Praia do Forte', 'Onde o dia pareceu mais devagar.', -12.5765000, -38.0075000, current_date - 45, array['mar','viagem'], v_user_id),
    (v_group_id, 'Café X', 'Mesa no canto e duas xícaras.', -12.9714000, -38.5014000, current_date - 90, array['café'], v_user_id);

  insert into public.playlists (group_id, title, platform, url, note, tags, created_by, updated_by)
  values
    (v_group_id, 'Músicas para voltar para casa', 'spotify', 'https://open.spotify.com/', 'Para tocar baixinho quando a saudade apertar.', array['saudade','noite'], v_user_id, v_user_id),
    (v_group_id, 'Domingo lento', 'youtube', 'https://youtube.com/', 'Trilha sonora de café e janela aberta.', array['domingo','casa'], v_user_id, v_user_id);

  insert into public.open_when_letters (group_id, title, trigger_label, body, unlock_at, audience_type, recipient_user_id, tags, created_by)
  values
    (v_group_id, 'Abrir quando estiver com saudade', 'saudade', 'Fecha os olhos por dez segundos. Tem carinho guardado aqui para te encontrar.', now() + interval '1 minute', 'all', null, array['saudade'], v_user_id),
    (v_group_id, 'Abrir em um dia difícil', 'dia difícil', 'Hoje não precisa ser perfeito. Só precisa passar. Você não está só.', now() + interval '1 day', 'all', null, array['acolhimento'], v_user_id);

  raise notice 'Seed demo criado no primeiro grupo.';
end $$;
