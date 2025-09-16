# Projeto Info_AI_Studio

## Resumo da aplicacao

Nome do app: Info_AI_Studio
Elevator pitch: Aplicacao que tem como objetivo buscar informacoes em diversas fontes (web e canais do youtube), analisando sites, blogs e conteudos de canais do youtube para gerar um relatório resumido e objetivo sobre as principais noticias, tendencias, insights, analises e novidades encontradas nas fontes. Depois da busca das informações, a aplicação terá que, através de um modelo de IA (LLM), realizar resumos (sumarizaçoes de conteúdos) para gerar relatórios e saida de informacoes através de prompts que serao executados nos LLMs configurados na aplicacao.
A aplicacao terá diversos cadastros como fontes, tipos de fontes, canais, assuntos, configuracoes da aplicacao (nome do LLM, API_KEY, limite de tokens e etc.). a aplicação poderá ser executada via interface web (Streamlit) ou através de linha de comando (CLI). 

Personas: usuários que precisa de informações atualizadas em diversas fontes
Canais de uso: GUI (Streamlit) + CLI (Typer).
Dados: SQLite em arquivo local (DB_PATH, default ./data.db). Backups: cópia com frequencia a ser programada do arquivo (.db) para pasta segura.
Métricas de sucesso: (i) cadastro de item ≤ 10s; (ii) zero erros de gravação em 7 dias; (iii) tempo de abertura da home ≤ 1s com até 5 mil itens.
Padrões de código: PEP 8 + PEP 257 (docstrings curtas)

## Requisitos funcionais

RF-01 — Cadastrar PROVEDOR / MODELO / API_KEY
Descrição: registrar os modelos de LLMs que poderao ser utilizados com suas respectiva API_KEY. Por exemplo, PROVEDOR=OPENAI;MODELO=GPT-5-NANO;OPENAI_API_KEY=xxxxxxxxxxxx; 
Entrada: provedor, modelo, api_key
Interfaces: GUI página “Configurações”; CLI modelo-ia --provedor --modelo --api_key.

RF-02 — Cadastrar Canal Youtube
Descrição: nome_canal (obrigatorio), descricao_canal (obrigatorio), grupo_canal (obrigatorio), id_canal(obrigatorio), status (ativo/inativo)(default ativo)
Interfaces: GUI página "Cadastros/Canais"

RF-03 — Cadastrar Fonte
Descrição: tipo_fonte (exemplo: site, blog, youtube)(obrigatorio), fonte (obrigatorio), descricao_fonte(opcional), status_fonte (ativa/inativa), ativa(default).
Condiçoes: se tipo_fonte for site, blog, o campo fonte deverá receber uma url completa; se o tipo_fonte for youtube, o campo fonte deverá receber o canal (previamente cadastrado);
Interfaces: GUI página "Cadastros/Fontes"

RF-04 — Cadastrar Parametros da Aplicacao
Descrição: max_palavras_resumo (int) - serao salvos no arquivo .env
Interfaces: GUI na página "Configuracoes/Parametros"

RF-05 — Inicializar Banco
Descrição: criar tabelas caso não existam.
Interfaces: GUI na página "Configurações/Banco" e CLI db-init.

RF-06 - Realizar Backup
Descriçao: gerar backup na pasta backup
Interfaces: GUI na página "Configurações/Backup"e CLI db-backup.



RF-07 - Execucao Pesquisa Fontes WEB
OBS: será implementado depois
Interfaces: GUI na página "Execucao/Pesquisa Fontes WEB"

RF-08 - Execucao Pesquisa Youtube
Informação importante:
Esta funcionalidade já foi implementada, mas está em outros códigos.
Irei anexar os códigos que implementam estas funcionalidades e preciso que sejam adaptadas para esta aplicaçao.
Serão anexados os seguites arquivos com as implementações desta funcionalidade para adaptação.
- INSTALACAO.md
- README.md
- canal.txt
- cookies.txt
- exemplo_uso_plus.py
- requirements.txt
- youtube_extractor_plus.py
exemplos de execucao da implementacao acima no modo CLI:
exemplo 1:
        (venv) jader@hp-desenv:~/analisa_canais_youtube$ python exemplo_uso_plus.py -h
        API== None
        usage: exemplo_uso_plus.py [-h] [--outdir OUTDIR] [--prefix PREFIX] [-d DAYS] [--channels-file CHANNELS_FILE] [-c CHANNEL] [--no-asr]
                                [--asr-provider {faster-whisper,openai}] [--model MODEL] [--openai-key OPENAI_KEY]
                                [--resumo-max-palavras RESUMO_MAX_PALAVRAS] [-m MODE] [--no-llm] [--cookies COOKIES] [--user-agent USER_AGENT]
                                [--format {txt,json,pdf,html}] [--max-videos MAX_VIDEOS]

        Extração em lote de canais do YouTube

        options:
        -h, --help            show this help message and exit
        --outdir OUTDIR       Diretório de saída (default: resultados_extracao)
        --prefix PREFIX       Prefixo do nome dos arquivos (default: youtube_extraction)
        -d DAYS, --days DAYS  Janela de dias dos vídeos (default: 3)
        --channels-file CHANNELS_FILE
                                Arquivo com lista de canais (um por linha; linhas iniciadas com # são comentários)
        -c CHANNEL, --channel CHANNEL
                                Adiciona canal manualmente (pode repetir)
        --no-asr              Desliga o fallback ASR
        --asr-provider {faster-whisper,openai}
                                Fornecedor de ASR para fallback
        --model MODEL         Modelo LLM para análises
        --openai-key OPENAI_KEY
                                Sobrescreve a chave OpenAI via CLI
        --resumo-max-palavras RESUMO_MAX_PALAVRAS
                                Limite de palavras do resumo
        -m MODE, --mode MODE  Modo de execução do programa: use full para executar o programa completo e simple para executar no modo simplificado
        --no-llm              Desativa as análises LLM
        --cookies COOKIES     Arquivo de cookies (formato Netscape) para evitar bloqueios
        --user-agent USER_AGENT
                                User-Agent a ser usado nas requisições (default: navegador Chrome)
        --format {txt,json,pdf,html}
                                Formato do relatório de saída (default: txt)
        --max-videos MAX_VIDEOS
                                Limita a quantidade de vídeos por canal (padrão: sem limite)

exemplo 2:
        (venv) jader@hp-desenv:~/analisa_canais_youtube$ python exemplo_uso_plus.py --channels-file canal.txt -d 1 --mode simple
        API== None
        Iniciando execução do YouTubeChannelAnalyzer

        Data: 2025-09-15

        Hora: 21:33:05

        Parâmetros utilizados:
        • Dias para filtrar vídeos recente(-d): 1 dia
        • Arquivo de canais (-f): canal.txt
        • Prefixo para arquivos de saída (--prefix): youtube_extraction

        Modelo LLM: gpt-5-nano

        API Key: None

        2025-09-15 21:33:05,518 - INFO - Iniciando extração em lote de 1 canais
        2025-09-15 21:33:05,519 - INFO - Processando canal 1/1: @canalsandeco
        2025-09-15 21:33:05,519 - INFO - Extraindo dados do canal: @canalsandeco
        2025-09-15 21:33:06,018 - INFO - Canal extraído com sucesso: @canalsandeco
        2025-09-15 21:33:06,018 - INFO - Extraindo vídeos recentes (≤ 1 dias) do canal @canalsandeco
        2025-09-15 21:33:06,018 - INFO - Extraindo vídeos do canal @canalsandeco (max_age_days=1, videos_tab_only=True, max_videos=None)
        2025-09-15 21:33:06,269 - INFO - Aba /videos: analisados=2, válidos=1, ignorados: live=0, upcoming=0, sem_data=0, antigos=1, shelves=0
        2025-09-15 21:33:06,269 - INFO - Aba /videos: 1 vídeos válidos (≤ 1 dias)
        2025-09-15 21:33:06,269 - INFO - Vídeos extraídos (aba /videos): 1
        2025-09-15 21:33:06,269 - INFO - Extração concluída. 1/1 canais extraídos com sucesso
        Resultado da pesquisa
        Total de canais com videos (dentro do critério de pesquisa): 1
        Total de videos (dentro do critério de pesquisa): 1

        Canal: @canalsandeco https://www.youtube.com/@canalsandeco
        Titulo do Video - Duracao - Publicacao - url_completa_do_video
        Essa Biblioteca da Microsoft vai MUDAR seu jeito de usar IA - 09:15 - publicado há 4 horas - https://www.youtube.com/watch?v=KA7hp2uyPOQ

        2025-09-15 21:33:06,968 - INFO - Resultados (JSON) salvos em: resultados_extracao/youtube_extraction_20250915_213305.json
        2025-09-15 21:33:06,968 - INFO - Relatório (TXT) salvo em: resultados_extracao/youtube_extraction_20250915_213305.txt
        2025-09-15 21:33:06,968 - INFO - Log completo: resultados_extracao/youtube_extraction_20250915_213305.log
        💾 Resultados salvos em: resultados_extracao/youtube_extraction_20250915_213305.json
        📄 Relatório salvo em: resultados_extracao/youtube_extraction_20250915_213305.txt
        📝 Log completo: resultados_extracao/youtube_extraction_20250915_213305.log
        2025-09-15 21:33:06,968 - INFO - Extração modo simples concluída
        (venv) jader@hp-desenv:~/analisa_canais_youtube$ 

exemplo 3:
        (venv) jader@hp-desenv:~/analisa_canais_youtube$ python exemplo_uso_plus.py --channels-file canal.txt -d 1 --mode full
        API== None
        Iniciando execução do YouTubeChannelAnalyzer

        Data: 2025-09-15

        Hora: 21:33:45

        Parâmetros utilizados:
        • Dias para filtrar vídeos recente(-d): 1 dia
        • Arquivo de canais (-f): canal.txt
        • Prefixo para arquivos de saída (--prefix): youtube_extraction

        Modelo LLM: gpt-5-nano

        API Key: None

        2025-09-15 21:33:45,752 - INFO - Iniciando extração em lote de 1 canais
        2025-09-15 21:33:45,753 - INFO - Processando canal 1/1: @canalsandeco
        2025-09-15 21:33:45,753 - INFO - Extraindo dados do canal: @canalsandeco
        2025-09-15 21:33:46,273 - INFO - Canal extraído com sucesso: @canalsandeco
        2025-09-15 21:33:46,273 - INFO - Extraindo vídeos recentes (≤ 1 dias) do canal @canalsandeco
        2025-09-15 21:33:46,273 - INFO - Extraindo vídeos do canal @canalsandeco (max_age_days=1, videos_tab_only=True, max_videos=None)
        2025-09-15 21:33:46,541 - INFO - Aba /videos: analisados=2, válidos=1, ignorados: live=0, upcoming=0, sem_data=0, antigos=1, shelves=0
        2025-09-15 21:33:46,541 - INFO - Aba /videos: 1 vídeos válidos (≤ 1 dias)
        2025-09-15 21:33:46,541 - INFO - Vídeos extraídos (aba /videos): 1
        2025-09-15 21:33:46,541 - INFO - Extração concluída. 1/1 canais extraídos com sucesso

        💾 Salvando resultados...
        💾 Resultados salvos em: resultados_extracao/youtube_extraction_20250915_213345.json
        📊 Tamanho do arquivo: 674 bytes

        ========================================================================
        📊 RESUMO DA EXTRAÇÃO
        ========================================================================

        📈 Estatísticas Gerais:
        • Canais processados: 1
        • Canais bem-sucedidos: 1
        • Canais com falha: 0
        • Taxa de sucesso: 100.0%
        • Total de requisições: 2
        • Tempo de extração: 2025-09-15T21:33:45.752905

        📺 Detalhes por Canal:
        ✅ @canalsandeco
            ID: @canalsandeco
            Inscritos: N/A
            Vídeos extraídos: 1
            • Vídeos encontrados:
                - Essa Biblioteca da Microsoft vai MUDAR seu jeito de usar IA — 2025-09-15 (há 4 horas)

        🎥 Total de vídeos extraídos: 1
        ========================================================================

        ✨ Extração concluída com sucesso!
        [LLM] OPENAI_API_KEY não definido — análises serão puladas.
        2025-09-15 21:33:48,113 - INFO - Transcrição: disponíveis ['pt(auto)'] para KA7hp2uyPOQ
        2025-09-15 21:33:48,214 - INFO - Transcrição: falha ao obter pt(auto) para KA7hp2uyPOQ: 'FetchedTranscriptSnippet' object has no attribute 'get'
        2025-09-15 21:33:48,214 - INFO - Transcrição: tradução pt indisponível para pt em KA7hp2uyPOQ
        2025-09-15 21:33:48,317 - INFO - Transcrição: falha ao obter pt(auto) para KA7hp2uyPOQ: 'FetchedTranscriptSnippet' object has no attribute 'get'
        2025-09-15 21:33:48,317 - INFO - Transcrição: não encontrada para KA7hp2uyPOQ
        2025-09-15 21:33:48,352 - INFO - yt-dlp usando cookies de cookies.txt
        2025-09-15 21:33:53,585 - INFO - [Transcrição YouTube] encontrada para KA7hp2uyPOQ (len=111302)
        [LLM] Cliente LLM ausente — pulando análise.
        2025-09-15 21:33:53,586 - INFO - Detalhe gerado para vídeo KA7hp2uyPOQ (@canalsandeco)
        DETALHE DOS VÍDEOS
        ------------------------------------------------------------------------
        • @canalsandeco
        - URL: https://www.youtube.com/watch?v=KA7hp2uyPOQ
        - Título: Essa Biblioteca da Microsoft vai MUDAR seu jeito de usar IA
        - Duração: 09:15
        - Data de postagem: 2025-09-15T12:58:28-07:00
        - Assunto principal: 
        - Resumo (1 frase): 
        - Resumo (<= 150 palavras): 
        - Palavras-chave: 
        - Resumo em tópicos:

        - Modelo LLM: gpt-5-nano
        - Tokens enviados: 0
        - Tokens recebidos: 0
        - Custo estimado: R$ 0.0000

        Nenhuma chamada LLM registrada.
        📄 Relatório salvo em: resultados_extracao/youtube_extraction_20250915_213345.txt
        2025-09-15 21:33:53,586 - INFO - Relatório (TXT) salvo em: resultados_extracao/youtube_extraction_20250915_213345.txt
        📄 Arquivo de resultados: youtube_extraction_20250915_213345.json
        📁 Diretório: resultados_extracao
        📝 Log completo: resultados_extracao/youtube_extraction_20250915_213345.log


Interfaces: GUI na página "Execucao/Pesquisa Youtube"

## Requisitos não-funcionais

Qualidade & Estilo: PEP 8, PEP 257, type hints em funções públicas. 
Configuração: .env com DB_PATH.
Observabilidade: logs no console (nível INFO, DEBUG, ERROR, FULL; mensagens de sucesso/erro claras).
Portabilidade: comandos simples: make gui, make cli, make test.
Desempenho-alvo: home ≤ 1s com 5k itens; listar itens ≤ 2s.


## Arquitetura e Pastas (layout src/)
Separação por camadas: domínio (regras), infra (DB/SQLite), interfaces (CLI/GUI), tests. Layout src/ para evitar imports acidentais e favorecer o pacote instalado.
.
├── README.md
├── .env.example
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain/            # regras e contratos do negócio (sem ORM)
│       ├── infrastructure/    # db (sqlite3), schema.sql, helpers
│       └── interfaces/
│           ├── cli/           # comandos Typer (db-init, users-create, items-add)
│           └── web/           # Streamlit app + pages/
│               ├── app.py
│               └── pages/
│                   ├── 1_Dashboard.py
│                   ├── 2_Cadastros.py
│                   └── 3_Configurações.py
│                   └── 4_Execução.py 
│                   └── 5_Logs.py 
└── tests/                     # smoke test + unitários simples

## Especificação da GUI (Streamlit Multipage)
Navegação:
    Método (mais customizável): st.Page + st.navigation para configurar rotas/urls/ícones. 
Páginas:
    Home: status do banco (ex.: “conectado”/“não inicializado”), atalhos p/ cadastros; Status da LLM ("conectada"/"não conectada")
    Dashboard: Relatórios gerados, tokens gerados (saida, entrada, custos e etc), utilização e outras informações a serem especificadas depois.
    Cadastros: 
        PROVEDOR / MODELO / API_KEY
        Canal Youtube
        Fonte
    Configurações:
        Parametros da Aplicacao
        Banco
        Backup
    Execução:
        Pesquisa Fontes WEB
        Pesquisa Youtube
    Logs:

## Especificação da CLI (Typer)
OBS: será especificado posteriormente.

Para cada comando, documente: propósito, args/opts obrigatórios, validações (ex.: email vazio), saída/exit codes e erros esperados.
Base: Typer (oficial, baseado em type hints).

## Modelo de Dados

Entidades e Regras:
    modelo_llm
        modl_id (int PK autoincrement)
        modl_provedor (tex not null)
        modl_modelo_llm (text not null)
        modl_api_key (text not null)
        modl_status (bool default 1)
    fonte_web
        fowe_id (int PK autoincrement)
        fowe_tipo (text not null, default "site")
        fowe_fonte (text not null)
        fowe_descricao (text not null)
        fowe_status (bool default 1)
    fonte_youtube
        foyt_id (int PK autoincrement)
        foyt_nome_canal (text not null)
        foyt_descricao (text not null)
        foyt_grupo_canal (text not null)
        foyt_id_canal (text not null)
        foyt_status (bool default 1)

Transações & Acesso (DB-API 2.0):
    Abrir conexão (sqlite3.connect(DB_PATH)), row_factory = sqlite3.Row, uso de executemany/execute, commit e close.
    Utilizar helpers atômicos (context manager) para leitura/escrita.
    Bases oficiais: sqlite3 (stdlib/DB-API 2.0) e documentação do SQLite


## Critérios de Aceitação
OBS: será definido posteriormente

## Testes (mínimo viável)
OBs: será definido posteriormente

# PROMPT
Gere um projeto Python chamado "Info_AI_Studio" com layout src/, GUI em Streamlit (multipage usando st.Page + st.navigation) e CLI com Typer. NÃO use ORM nem Alembic; persista com sqlite3 (stdlib, DB-API 2.0) e arquivo de esquema .sql. Siga PEP 8/PEP 257 e inclua type hints em funções públicas. Entregue a árvore de pastas indicada, arquivos essenciais e um README com instruções de execução. Use exatamente os nomes/rotas especificados abaixo.

1) RESUMO / PRODUTO
- Nome do app: Info_AI_Studio
- Elevator pitch: Buscar informações em múltiplas fontes (web, YouTube), analisar sites/blogs/canais e gerar relatórios resumidos (notícias, tendências, insights). Após coleta, executar sumarizações via LLM configurado (prompts). Execução via GUI (Streamlit) e CLI (Typer).
- Personas: usuários que precisam de informações atualizadas de várias fontes
- Canais: GUI + CLI
- Dados: SQLite local (DB_PATH, default ./data.db). Backups: cópia programável do .db em pasta segura.
- Métricas de sucesso: (i) cadastro ≤ 10s; (ii) zero erros de gravação em 7 dias; (iii) home ≤ 1s com até 5k itens.
- Padrões de código: PEP 8 + PEP 257 (docstrings curtas)

2) STACK E PADRÕES
- Python 3.11+
- GUI: Streamlit com multipage por st.Page/st.navigation
- CLI: Typer
- Banco: sqlite3 (DB-API 2.0) + schema.sql
- Config (.env): DB_PATH, MAX_PALAVRAS_RESUMO, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, TOKEN_LIMIT
- Logging: console com níveis INFO, DEBUG, ERROR, FULL (mapear FULL para nível detalhado/verbose)
- Make: make gui, make cli, make test (e opcional: make backup)

3) ENTREGÁVEIS (OBRIGATÓRIOS)
- Árvore de pastas conforme “Arquitetura e Pastas (layout src/)”
- Arquivos: README.md, .env.example, src/app/infrastructure/schema.sql, helpers de DB (sqlite3), entrypoint Streamlit, CLI Typer, teste de fumaça em tests/
- pyproject.toml (PEP 621) com [project] e [project.scripts] → app = "app.interfaces.cli.main:app"

4) REQUISITOS FUNCIONAIS (implementar GUI e, quando indicado, CLI)
RF-01 — Cadastrar PROVEDOR / MODELO / API_KEY
  • Registrar LLMs e chaves: provedor, modelo, api_key  
  • GUI: “Configurações” (form+lista)  
  • CLI: `modelo-ia --provedor --modelo --api_key`  

RF-02 — Cadastrar Canal Youtube
  • Campos: nome_canal*, descricao_canal*, grupo_canal*, id_canal*, status (ativo/inativo, default ativo)  
  • GUI: “Cadastros/Canais” (form+lista)  

RF-03 — Cadastrar Fonte
  • Campos: tipo_fonte* (site|blog|youtube), fonte*, descricao_fonte (opcional), status_fonte (ativa/inativa, default ativa)  
  • Regras: tipo=site/blog → fonte deve ser URL completa; tipo=youtube → fonte referencia canal previamente cadastrado  
  • GUI: “Cadastros/Fontes” (form+lista com validação de regras)  

RF-04 — Cadastrar Parâmetros da Aplicação
  • Campo: max_palavras_resumo (int) → persista em .env (MAX_PALAVRAS_RESUMO)  
  • GUI: “Configurações/Parametros”  

RF-05 — Inicializar Banco
  • Criar tabelas se não existirem (executar schema.sql)  
  • GUI: “Configurações/Banco” (botão “Inicializar banco”)  
  • CLI: `db-init`  

RF-06 — Realizar Backup
  • Gerar backup do arquivo .db em ./backup com timestamp (ex.: YYYYMMDD_HHMMSS.db)  
  • GUI: “Configurações/Backup” (botão)  
  • CLI: `db-backup`  

RF-07 — Execução Pesquisa Fontes WEB
  • Placeholder (GUI “Execução/Pesquisa Fontes WEB”): apenas layout e logs “ação iniciada/concluída”. Implementação posterior.

RF-08 — Execução Pesquisa YouTube (ADAPTAÇÃO DE ARQUIVOS EXISTENTES)
  • Integre a funcionalidade já implementada nestes arquivos, que serão anexados para adaptação:  
    - INSTALACAO.md, README.md, canal.txt, cookies.txt, exemplo_uso_plus.py, requirements.txt, youtube_extractor_plus.py  
  • Objetivo: adaptar para o Info_AI_Studio sem quebrar a CLI atual de exemplos (simple/full), mas expondo botões/controles equivalentes na GUI “Execução/Pesquisa Youtube”.  
  • Preserve (para referência) os exemplos de uso via CLI indicados pelo cliente; disponibilize uma nova CLI do app que aceite parâmetros equivalentes (dias, channels-file, mode, no-llm, asr-provider, model, openai-key override, resumo-max-palavras, cookies, user-agent, format, max-videos).  
  • Salvar resultados em diretório configurável (ex.: ./resultados_extracao/), registrando também caminho dos artefatos (JSON, TXT, LOG) no banco.  
  • Caso LLM_API_KEY ausente, executar apenas extração/coleta (sumarização desabilitada), com mensagens claras.  
  • GUI “Execução/Pesquisa Youtube”: campos principais alinhados aos parâmetros acima; botões “Executar modo simple” e “Executar modo full”; painel de logs e links para arquivos produzidos.

5) REQUISITOS NÃO FUNCIONAIS
- PEP 8, PEP 257, type hints  
- .env com DB_PATH (default ./data.db) e chaves LLM  
- Logs legíveis com níveis INFO/DEBUG/ERROR/FULL  
- Portabilidade: make gui, make cli, make test  
- Desempenho: home ≤ 1s (5k itens), listagem ≤ 2s

6) ARQUITETURA E PASTAS (layout src/)
Crie exatamente:
.
├── README.md
├── .env.example
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain/            # regras/contratos (sem ORM)
│       ├── infrastructure/    # sqlite3 (db helpers) + schema.sql + util de backup
│       └── interfaces/
│           ├── cli/           # Typer: db-init, db-backup, modelo-ia, (futuro) comandos de execução
│           └── web/           # Streamlit app + pages/
│               ├── app.py
│               └── pages/
│                   ├── 1_Dashboard.py
│                   ├── 2_Cadastros.py
│                   └── 3_Configurações.py
│                   └── 4_Execução.py
│                   └── 5_Logs.py
└── tests/                     # smoke test + unitários simples

7) GUI (Streamlit Multipage)
- Navegação: definir st.Page(...) e registrar via st.navigation(...) no entrypoint; páginas:  
  • Home: status do DB (conectado/não inicializado), atalhos p/ Cadastros, status da LLM (conectada/não conectada)  
  • Dashboard: placeholders para “Relatórios gerados”, “Tokens (entrada/saída)”, “Custos”, “Utilização”  
  • Cadastros:  
      - PROVEDOR/MODELO/API_KEY (form+lista)  
      - Canal YouTube (form+lista)  
      - Fonte (form+lista com validação por tipo)  
  • Configurações:  
      - Parâmetros da Aplicação (atualiza MAX_PALAVRAS_RESUMO em .env)  
      - Banco (botão “Inicializar banco”)  
      - Backup (botão “Gerar backup”)  
  • Execução:  
      - Pesquisa Fontes WEB (placeholder)  
      - Pesquisa YouTube (form+execução, exibição de logs/links de saída)  
  • Logs: feed de eventos recentes (rolável)  

8) CLI (Typer)
- Mínimo para o MVP:  
  • `db-init` → cria tabelas a partir do schema.sql  
  • `db-backup` → copia DB_PATH para ./backup/AAAA-MM-DD_HHMMSS.db  
  • `modelo-ia --provedor --modelo --api_key` → insere/atualiza registro LLM  
- Para Execução YouTube: criar comandos alinhados aos parâmetros do módulo legado (dias, channels-file, mode, …) espelhando os exemplos fornecidos pelo cliente.  
- Todos os comandos devem imprimir mensagens de sucesso/erro e expor `--help`.

9) MODELO DE DADOS (SEM ORM) → gerar DDL em src/app/infrastructure/schema.sql
- modelo_llm
    modl_id INTEGER PK AUTOINCREMENT
    modl_provedor TEXT NOT NULL
    modl_modelo_llm TEXT NOT NULL
    modl_api_key TEXT NOT NULL
    modl_status INTEGER NOT NULL DEFAULT 1
- fonte_web
    fowe_id INTEGER PK AUTOINCREMENT
    fowe_tipo TEXT NOT NULL DEFAULT "site"
    fowe_fonte TEXT NOT NULL
    fowe_descricao TEXT NOT NULL
    fowe_status INTEGER NOT NULL DEFAULT 1
- fonte_youtube
    foyt_id INTEGER PK AUTOINCREMENT
    foyt_nome_canal TEXT NOT NULL
    foyt_descricao TEXT NOT NULL
    foyt_grupo_canal TEXT NOT NULL
    foyt_id_canal TEXT NOT NULL
    foyt_status INTEGER NOT NULL DEFAULT 1
- Acesso/Transações (helpers):
    Conexão sqlite3.connect(DB_PATH), row_factory=sqlite3.Row, execute/executescript, commit/close
    Context manager para operações atômicas de leitura/escrita

10) CONFIGURAÇÃO (.env e .env.example)
- DB_PATH=./data.db
- MAX_PALAVRAS_RESUMO=<int>
- LLM_PROVIDER=<ex.: OPENAI>
- LLM_MODEL=<ex.: GPT-5-NANO>
- LLM_API_KEY=<chave>
- TOKEN_LIMIT=<int>

11) CRITÉRIOS DE ACEITAÇÃO
- A definir posteriormente (deixe marcadores no README para estes critérios)

12) TESTES (MÍNIMO)
- Deixe um teste de fumaça que inicializa DB em diretório temporário, cria tabelas via schema.sql e valida operação básica (ex.: inserir 1 registro).

13) README (INCLUIR)
- Setup de venv, instalação, configuração .env, como rodar GUI (streamlit run) e CLI (app --help), inicializar banco, gerar backup e executar a Pesquisa YouTube (simple/full), anotando caminhos dos arquivos de saída.
