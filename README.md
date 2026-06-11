# Presente Vii — Streamlit + Supabase, multi-grupos

MVP privado e fofo para guardar lembranças em vários grupos: namoro, família dela, sua família e todo mundo junto.

## O que esta versão faz

- Login simples por **nome de usuário + senha**.
- Primeira conta criada no app vira dona dos grupos iniciais.
- Depois disso, novas contas entram por **código de convite, link ou QR Code**.
- O login fica persistente neste navegador por token revogável salvo no localStorage.
- Uma pessoa pode participar de vários grupos.
- Cada grupo tem timeline, mapa, playlists, cartas e mídias separados.
- Membros podem adicionar fotos, vídeos, áudios, momentos, lugares, playlists e cartas.
- Playlists podem ser alteradas por todos os membros do grupo.
- Cartas podem ser para todos ou para uma pessoa específica.
- Cartas só abrem depois da data/hora definida pelo criador.
- Cartas aceitam foto, áudio e vídeo.
- Storage privado no Supabase.
- QR Code e link de convite apontando para `https://memorium.streamlit.app` por padrão.
- Layout responsivo com estética azul + verde escuro + rosa.

## Arquitetura

```txt
Presente_Vii_grupos_streamlit_supabase/
  app.py
  requirements.txt
  install_windows_cmd.bat
  run_windows_cmd.bat
  check_deps_cmd.bat
  .streamlit/
    config.toml
    secrets.example.toml
  src/
    auth.py              # login simples, cadastro por convite
    security.py          # hash/verificação de senha com PBKDF2-HMAC-SHA256
    config.py            # leitura de secrets
    persistent_login.py  # token persistente no navegador/localStorage
    db.py                # CRUD, grupos, permissões, sessões persistentes e exportação
    storage.py           # upload/signed URL de imagem, áudio e vídeo
    supabase_client.py   # client Supabase com service_role/secret key no servidor
    ui.py                # CSS responsivo e componentes visuais
    validators.py
    pages/
      home.py
      groups.py
      timeline.py
      places.py
      playlists.py
      open_when.py
      admin.py
  supabase/
    00_RODAR_NO_SQL_EDITOR.sql      # instalação limpa em um arquivo
    migrations/
      000_reset_previous_version.sql
      001_schema.sql
      002_rls_private.sql
      003_storage.sql
    seed_demo.sql
```

## Modelo de dados

- `app_users`: usuários do app, com `username`, `display_name` e `password_hash`.
- `groups`: grupos privados com nome, descrição, cor e `invite_code`.
- `group_members`: associação muitos-para-muitos entre pessoas e grupos, com papel `owner`, `admin` ou `member`.
- `persistent_sessions`: tokens revogáveis para manter o usuário conectado no navegador.
- `timeline_entries`: momentos do grupo.
- `places`: lugares do grupo para o mapa.
- `playlists`: links e notas de playlists.
- `open_when_letters`: cartas com destinatário, texto e data/hora obrigatória de desbloqueio.
- `media`: fotos, áudios e vídeos relacionados a home, timeline, lugares, playlists ou cartas.

## Segurança desta versão

Esta versão não usa Supabase Auth porque o objetivo agora é login simples por usuário/senha.

Como o usuário do app não vira um JWT do Supabase, o app usa a `SUPABASE_SERVICE_ROLE_KEY` **somente no servidor Streamlit** e aplica autorização no código Python. Por isso:

- nunca coloque `.streamlit/secrets.toml` no GitHub;
- nunca exponha a service role/secret key no navegador;
- mantenha o bucket privado;
- publique o app apenas em ambiente onde secrets fiquem no backend;
- use HTTPS no deploy.

As senhas não ficam em texto puro. Esta versão usa `hashlib.pbkdf2_hmac`, da biblioteca padrão do Python, com PBKDF2-HMAC-SHA256 e 600.000 iterações. Assim não depende mais do pacote `argon2-cffi` e evita o erro `ModuleNotFoundError: No module named 'argon2'`.

As tabelas ficam com RLS ativado e sem policies públicas. A anon/publishable key não deve ser usada nesta versão.

A persistência de login usa um token aleatório salvo no localStorage do navegador e apenas o hash SHA-256 dele fica no Supabase. O token expira em 60 dias e é revogado ao clicar em **Sair**. Para um produto público com requisito rígido de segurança, o ideal continua sendo autenticação com backend e cookie HttpOnly/Secure/SameSite.

## Instalação no Windows sem PowerShell

Use o **Prompt de Comando** (`cmd.exe`) ou dê dois cliques nos arquivos `.bat`.

### Opção 1 — clicando nos arquivos

1. Dê dois cliques em `install_windows_cmd.bat`.
2. Aguarde terminar a instalação.
3. Configure `.streamlit/secrets.toml`.
4. Dê dois cliques em `run_windows_cmd.bat`.

### Opção 2 — pelo Prompt de Comando

Abra o menu iniciar, digite `cmd`, abra o **Prompt de Comando** e rode:

```bat
cd /d "C:\Presente Vii"
install_windows_cmd.bat
```

Crie o arquivo de secrets:

```bat
copy .streamlit\secrets.example.toml .streamlit\secrets.toml
notepad .streamlit\secrets.toml
```

Preencha:

```toml
SUPABASE_URL = "https://SEU-PROJECT-REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "SUA-SERVICE-ROLE-OU-SECRET-KEY"
APP_NAME = "Presente Vii"
APP_BASE_URL = "https://memorium.streamlit.app"
APP_DEBUG_AUTH = false
```

Depois rode:

```bat
run_windows_cmd.bat
```

O app abrirá em algo como:

```txt
http://localhost:8501
```

## Banco de dados no Supabase

Para evitar erro de ordem, use **um único arquivo**:

```txt
supabase/00_RODAR_NO_SQL_EDITOR.sql
```

No Supabase:

1. Abra seu projeto.
2. Vá em **SQL Editor**.
3. Clique em **New query**.
4. Copie todo o conteúdo de `supabase/00_RODAR_NO_SQL_EDITOR.sql`.
5. Clique em **Run**.

Esse script recria as tabelas públicas deste app e cria/atualiza o bucket privado `memories`. Ele não tenta apagar `storage.objects`, porque o Supabase bloqueia exclusão direta das tabelas internas do Storage. Se quiser limpar arquivos antigos, use o painel **Storage > memories**.

## Primeiro acesso

1. Abra o app.
2. Clique em **Criar conta**.
3. Como ainda não existe usuário, o app vai criar você como dono.
4. Ele cria automaticamente estes grupos:
   - Nós dois
   - Família dela
   - Minha família
   - Todo mundo junto
5. Vá em **Grupos**.
6. Selecione um grupo.
7. Copie o código de convite e envie para quem deve participar.

Depois que já existir pelo menos um usuário, novas pessoas só criam conta com código de convite.

## Como convidar alguém

1. Entre no app.
2. Vá em **Grupos**.
3. Selecione o grupo.
4. Em **Configurações**, copie o código, o link ou use o QR Code.
5. O link/QR Code aponta para `APP_BASE_URL/?invite=CODIGO`.
6. A pessoa entra no app, vai em **Criar conta** e o código já aparece preenchido.

## Permissões

| Ação | Owner/Admin | Membro |
|---|---:|---:|
| Ver conteúdo do grupo | Sim | Sim |
| Criar timeline/lugares/playlists/cartas | Sim | Sim |
| Alterar playlists | Sim | Sim |
| Editar conteúdo próprio | Sim | Sim |
| Editar conteúdo dos outros | Sim | Não, exceto playlists |
| Gerenciar convite/membros | Sim | Não |
| Exportar/apagar conteúdo do grupo | Sim | Não |

## Cartas “Abrir quando...”

Cada carta tem:

- título;
- gatilho;
- texto;
- destinatário: todos ou uma pessoa específica;
- data e hora de liberação obrigatórias;
- tags;
- fotos, áudios e vídeos opcionais.

Antes da data, a carta aparece fechada. Depois da data, o texto e as mídias são liberados.

## Seed opcional

Depois de rodar `00_RODAR_NO_SQL_EDITOR.sql` e criar seu primeiro usuário pela tela, rode:

```txt
supabase/seed_demo.sql
```

Ele adiciona exemplos fictícios no primeiro grupo.

## Erros comuns

### `relation "public.app_users" does not exist`

Você rodou o app ou o seed antes de criar as tabelas. Rode `supabase/00_RODAR_NO_SQL_EDITOR.sql` no SQL Editor.

### `column "group_id" does not exist`

Você está com tabelas de uma versão antiga. Rode `supabase/00_RODAR_NO_SQL_EDITOR.sql` para resetar e recriar o schema novo.

### `Direct deletion from storage tables is not allowed`

A versão antiga do reset tentava apagar `storage.objects` via SQL. A versão nova não faz isso. Para limpar arquivos, use **Storage > memories** no painel do Supabase.

### `ModuleNotFoundError: No module named 'argon2'`

A versão nova não usa mais `argon2`. Instale novamente as dependências com `install_windows_cmd.bat` e rode com `run_windows_cmd.bat`.

## Atualizar banco sem apagar dados

Se você já tem dados no Supabase e quer apenas ativar a persistência de login, rode:

```txt
supabase/03_LOGIN_PERSISTENTE.sql
```

Se ainda não rodou as atualizações anteriores, rode também:

```txt
supabase/01_ATUALIZAR_SEM_APAGAR_DADOS.sql
supabase/02_MAPA_BUSCA_E_LOCALIZACOES.sql
```

Não rode `00_RODAR_NO_SQL_EDITOR.sql` em produção com dados reais, porque ele reseta as tabelas do app.

## Deploy

### Streamlit Community Cloud

1. Suba o projeto para um repositório privado.
2. Crie app apontando para `app.py`.
3. Configure os secrets no painel do Streamlit, incluindo `APP_BASE_URL = "https://memorium.streamlit.app"`.
4. Rode `supabase/00_RODAR_NO_SQL_EDITOR.sql` no Supabase se for instalação limpa, ou `03_LOGIN_PERSISTENTE.sql` se já tiver dados.
5. Acesse o app e crie o primeiro usuário.

No Streamlit Community Cloud, selecione Python 3.12 nas configurações avançadas do deploy para evitar a tentativa de compilar `pyarrow` em Python 3.14.

### Render/Fly/Railway-like

Comando:

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
```

Configure `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` como variáveis secretas da plataforma.

## Observações importantes

- Esta versão prioriza simplicidade de presente/MVP.
- Para segurança mais forte em produto público, o ideal é voltar para Supabase Auth ou criar um backend tradicional com cookies HttpOnly/Secure/SameSite.
- Como o app é privado por convite, mantenha a URL só com pessoas confiáveis.

## Ajuste visual: mapa e cards da Home

Nesta versão ajustada:

- A página **Mapa** sempre renderiza um mapa real, mesmo quando o grupo ainda não tem nenhum lugar cadastrado.
- Quando não há lugares, o mapa começa centralizado em Salvador/BA como ponto inicial do MVP.
- Ao clicar no mapa, o app mostra a latitude e longitude clicadas para facilitar o cadastro manual do lugar.
- Os cards da **Home** viraram links clicáveis:
  - Momentos → Timeline
  - Lugares → Mapa
  - Playlists → Playlists
  - Cartas → Abrir quando...
  - Membros → Grupos
- No celular, esses cards ficam em **duas colunas por linha**.

Arquivos alterados neste ajuste:

```txt
src/pages/home.py
src/pages/places.py
src/ui.py
```

## Correção para `httpx.ReadError: [WinError 10035]`

Essa versão reduz chamadas repetidas ao Supabase e adiciona retentativas curtas nas consultas de banco. O erro costuma aparecer no Windows quando uma operação de rede assíncrona/non-blocking não consegue terminar imediatamente. O app agora:

- busca grupos do usuário em uma consulta única, em vez de fazer uma chamada HTTP por grupo;
- cria um cliente Supabase novo a cada rerun do Streamlit, evitando reaproveitar conexões HTTP antigas;
- configura timeout maior para PostgREST e Storage;
- tenta novamente consultas afetadas por `httpx.ReadError`, `httpx.ReadTimeout`, `httpx.ConnectError` e erros de transporte semelhantes.

Se o erro continuar:

1. Feche o terminal do app.
2. Rode `install_windows_cmd.bat` novamente.
3. Rode `check_deps_cmd.bat`.
4. Abra com `run_windows_cmd.bat`.
5. Se estiver usando Python 3.14, instale Python 3.12 ou 3.11 e rode `install_windows_cmd.bat` de novo. O instalador agora tenta preferir Python 3.12/3.11 quando existir no Windows.

## Correção dos cards mostrando HTML cru

Se os cards da Home aparecerem com tags como `<a class='nav-card'>`, atualize para esta versão. A função `render_nav_cards` foi alterada para gerar HTML compacto e usar `st.html` quando disponível. Isso evita que o parser Markdown interprete HTML indentado como bloco de código.

Não precisa rodar SQL novo no Supabase para essa correção.

## Atualização: QR Code, carrossel e momentos ligados a lugares

Esta versão adiciona:

- Convite por QR Code na página **Grupos**.
- Login/entrada por convite usando `?invite=CODIGO`.
- Cards da Home como botões Streamlit, preservando a sessão ao navegar.
- Carrossel automático para múltiplas fotos/vídeos. Imagens passam sozinhas; vídeos só avançam quando acabam ou quando a pessoa usa as setas.
- Campo **Lugar relacionado** nos momentos da Timeline.
- Em cada lugar do Mapa, aparecem os momentos vinculados a ele.

### Atualizar banco sem apagar dados

Se você já rodou a instalação anterior, execute no SQL Editor:

```txt
supabase/01_ATUALIZAR_SEM_APAGAR_DADOS.sql
```

Se for instalar do zero, basta rodar o arquivo principal:

```txt
supabase/00_RODAR_NO_SQL_EDITOR.sql
```

### QR Code

Configure no `.streamlit/secrets.toml` a URL pública do app para o QR Code funcionar fora do seu computador:

```toml
APP_BASE_URL = "https://memorium.streamlit.app"
```

Para desenvolvimento local pode ficar:

```toml
APP_BASE_URL = "http://localhost:8501"
```
