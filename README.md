# Info_AI_Studio

Aplicação para coletar dados de múltiplas fontes (web e YouTube), organizar cadastros e gerar relatórios resumidos com apoio de modelos LLM. A interface está disponível via Streamlit e a automação via CLI (Typer).

## Sumário
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Executando a GUI](#executando-a-gui)
- [Executando a CLI](#executando-a-cli)
- [Pesquisa no YouTube](#pesquisa-no-youtube)
- [Logs e Observabilidade](#logs-e-observabilidade)
- [Testes](#testes)
- [Critérios de aceitação](#critérios-de-aceitação)
- [Estrutura de pastas](#estrutura-de-pastas)

## Arquitetura

```
.
├── .env.example
├── Makefile
├── pyproject.toml
├── src/
│   └── app/
│       ├── config.py
│       ├── domain/
│       ├── infrastructure/
│       └── interfaces/
│           ├── cli/
│           └── web/
└── tests/
```

- **domain**: regras de negócio, entidades e serviços.
- **infrastructure**: acesso ao SQLite, backup, schema.sql e utilitários de logging/ambiente.
- **interfaces**: CLI (Typer) e GUI (Streamlit multipage com `st.Page` + `st.navigation`).
- **tests**: testes de fumaça com pytest.

## Pré-requisitos

- Python 3.11+
- pip

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## Configuração

1. Copie o arquivo `.env.example` para `.env` e ajuste as variáveis conforme necessário:
   - `DB_PATH` (caminho do SQLite, padrão `./data.db`)
   - `MAX_PALAVRAS_RESUMO`
   - `LLM_PROVIDER`, `LLM_MODEL`, `TOKEN_LIMIT` e a chave via `LLM_API_KEY`
     ou `PROVEDOR_API_KEY` (ex.: `OPENAI_API_KEY`)
   - Diretórios opcionais: `RESULTADOS_DIR`, `BACKUP_DIR`, `LOG_DIR`, `COOKIES_PATH`
2. Inicialize o banco (CLI ou GUI).
3. Cadastre modelos LLM e fontes pela GUI ou CLI.

## Executando a GUI

```bash
make gui
# ou
streamlit run src/app/interfaces/web/main.py
```

A página inicial exibe o status do banco/LLM. Navegue pelas páginas **Dashboard**, **Cadastros**, **Configurações**, **Execução** e **Logs**.

## Executando a CLI

Verifique os comandos disponíveis:

```bash
make cli
# ou
python -m app.interfaces.cli.main --help
```

Comandos principais:

- `app db-init` — inicializa o banco.
- `app db-backup` — gera backup em `./backup`.
- `app modelo-ia --provedor OPENAI --modelo gpt-5-nano --api-key <CHAVE>` — cadastra modelo LLM.
- `app youtube-exec [opções]` — executa a extração do YouTube.

## Pesquisa no YouTube

A extração utiliza o módulo `YouTubeExecutionService`, adaptado do projeto legado fornecido.

### CLI

Exemplos:

```bash
python -m app.interfaces.cli.main youtube-exec --channels-file examples/canal.txt -d 1 --mode simple
python -m app.interfaces.cli.main youtube-exec --channels-file examples/canal.txt -d 1 --mode full --no-llm
```

Opções relevantes:

- `--outdir`: diretório de saída (padrão `RESULTADOS_DIR` do `.env`).
- `--prefix`: prefixo dos arquivos gerados.
- `--days`: filtra vídeos pelos últimos N dias.
- `--channels-file`: arquivo com lista de canais (um por linha). Exemplo em `examples/canal.txt`.
- `-c/--channel`: adicionar canais diretamente na CLI (pode repetir).
- `--mode`: `full` (extração completa com transcrição/resumo) ou `simple` (somente listagem).
- `--no-llm`: desativa sumarização via LLM.
- `--no-asr`: desativa fallback ASR (yt-dlp + faster-whisper/OpenAI Whisper).
- `--asr-provider`: `faster-whisper` (padrão) ou `openai`.
- `--model`, `--openai-key`: sobrescrevem modelo/chave LLM da configuração.
- `--resumo-max-palavras`: limite de palavras no resumo.
- `--cookies`: arquivo Netscape com cookies (exemplo em `examples/cookies.txt`).
- `--format`: formato do relatório (`txt`, `json`, `pdf`, `html`).
- `--max-videos`: limita vídeos por canal.

Resultados:

- JSON sempre gerado no diretório de saída.
- Relatório no formato escolhido (TXT/HTML/PDF/JSON).
- Logs centralizados no `app.log` com rotação.
- Metadados registrados na tabela `youtube_extraction`.

### GUI

Na página **Execução**:

1. Selecione canais cadastrados, acrescente canais manualmente ou envie arquivo `.txt`.
2. Configure parâmetros (dias, formato, ASR, LLM, limite de vídeos etc.).
3. Clique em **Executar modo simple** ou **Executar modo full**. Os caminhos gerados e totais são exibidos após a execução.

## Logs e Observabilidade

- Centralização: todos os logs vão para `app.log` em `LOG_DIR` (padrão `./logs`). Há rotação por tamanho (padrão 10 MB) com backups (padrão 5).
- Níveis e tipos: além de `DEBUG/INFO/WARNING/ERROR`, existe o nível `FULL` para eventos detalhados de UI (cliques, ações). A seleção de tipos controla o que é persistido.
- run_id: cada execução (Web Prompt e YouTube) exibe um `run_id` na UI e nos nomes de arquivos baixados. Use-o para correlacionar linhas no `app.log`.
- Eventos de execução: a UI registra `WEB_PROMPT_START/END` (com `run_id`, modelo, parâmetros) e outros `UI_EVENT` com payload JSON (por exemplo, `page`, `button`).

Página “Logs do sistema” (GUI):
- Configurações: ajuste `LOG_LEVEL`, tamanho/backup de rotação e tipos habilitados.
- Manutenção: botão “Limpar logs” (com confirmação) e opção para remover backups.
- Filtros: por texto, níveis, últimos N minutos, `run_id`, ações `UI_EVENT` e páginas/áreas.
- Visualização: recarregar logs, ler somente a cauda (“Ler últimos N KB”) e limitar “Máx. linhas exibidas”.
- Exportação: baixar o trecho filtrado.

Variáveis de ambiente relevantes:
- `LOG_DIR`: diretório do `app.log`.
- `LOG_LEVEL`: nível mínimo (ex.: `INFO`).
- `LOG_TYPES`: tipos persistidos (ex.: `error,warning,info,full`).
- `LOG_ROTATE_MAX_MB`: tamanho de rotação em MB (padrão 10).
- `LOG_BACKUP_COUNT`: quantidade de backups (padrão 5).

### Guia rápido: investigar com run_id

1. Execute uma consulta (Web Prompt ou YouTube) pela página **Execução**.
2. Copie o `run_id` exibido no resultado (há um campo “Copiar run_id”).
3. Abra a página **Logs** e cole o `run_id` no campo “Filtrar por run_id”.
4. (Opcional) Ajuste filtros de nível (INFO/ERROR/FULL), período (Últimos N minutos) e, para eventos de UI, selecione “Ações UI_EVENT” e “Páginas UI_EVENT”.
5. Clique em **Aplicar filtros** para visualizar apenas as linhas relacionadas.
6. Use **Baixar trecho filtrado** para salvar o subset relevante.
7. Dicas úteis:
  - Ative **Autoatualizar** e ajuste o **Intervalo (s)** para acompanhar logs em tempo real mantendo os filtros.
  - Use **Recarregar logs** para atualizar manualmente quando o auto-refresh estiver desligado.
  - Para arquivos grandes, ajuste “Ler últimos N KB” e “Máx. linhas exibidas”.
  - Em caso de limpeza, use o expander **Manutenção** (com confirmação) e, se necessário, remova backups.

### Próximos passos (visuais)
- Inserir GIF/prints demonstrando: execução → copiar run_id → filtrar na página de Logs → autoatualização em tempo real.

## Testes

```bash
make test
```

O teste de fumaça inicializa o schema em um banco temporário e verifica inserção básica.

## Critérios de aceitação

- [ ] (A definir pelo time)

## Estrutura de pastas

```
examples/
├── canal.txt           # exemplo de lista de canais
├── cookies.txt         # modelo de cookies (substitua pelos seus)
logs/
resultados_extracao/
src/app/
├── config.py
├── domain/
│   ├── entities.py
│   ├── fonte_service.py
│   ├── llm_client.py
│   ├── llm_service.py
│   ├── parameters_service.py
│   ├── validators.py
│   └── youtube/
│       ├── __init__.py
│       ├── extractor_plus.py
│       └── service.py
├── infrastructure/
│   ├── backup.py
│   ├── db.py
│   ├── env_manager.py
│   ├── logging_setup.py
│   ├── repositories.py
│   └── schema.sql
└── interfaces/
    ├── cli/
    │   ├── __init__.py
    │   └── main.py
    └── web/
        ├── app.py
        ├── main.py
        └── pages/
            ├── 1_Dashboard.py
            ├── 2_Cadastros.py
            ├── 3_Configurações.py
            ├── 4_Execução.py
            └── 5_Logs.py
```
