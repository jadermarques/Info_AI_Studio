#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-.}"

if [[ "${TARGET_DIR}" == "." ]]; then
  echo "Generating project in current directory"
else
  echo "Generating project in ${TARGET_DIR}"
fi

mkdir -p "${TARGET_DIR}"

cat <<'EOF_1' > "${TARGET_DIR}/.env.example"
# Caminho para o banco de dados SQLite
DB_PATH=./data.db

# Limite de palavras para resumos de vídeos
MAX_PALAVRAS_RESUMO=150

# Configurações padrão do modelo LLM
LLM_PROVIDER=OPENAI
LLM_MODEL=gpt-5-nano
# Variável genérica (legado)
LLM_API_KEY=
# Variável específica do provedor (ex.: OPENAI_API_KEY, ANTHROPIC_API_KEY)
OPENAI_API_KEY=
TOKEN_LIMIT=4096
EOF_1

cat <<'EOF_2' > "${TARGET_DIR}/Makefile"
.PHONY: gui cli test backup

ENV?=.env

gui:
streamlit run src/app/interfaces/web/main.py

cli:
python -m app.interfaces.cli.main --help

test:
pytest

backup:
python -m app.interfaces.cli.main db-backup
EOF_2

cat <<'EOF_3' > "${TARGET_DIR}/README.md"
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
- Log individual por execução em `logs/`.
- Metadados registrados na tabela `youtube_extraction`.

### GUI

Na página **Execução**:

1. Selecione canais cadastrados, acrescente canais manualmente ou envie arquivo `.txt`.
2. Configure parâmetros (dias, formato, ASR, LLM, limite de vídeos etc.).
3. Clique em **Executar modo simple** ou **Executar modo full**. Os caminhos gerados e totais são exibidos após a execução.

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
EOF_3

mkdir -p "${TARGET_DIR}/backup"
cat <<'EOF_4' > "${TARGET_DIR}/backup/.gitkeep"

EOF_4

mkdir -p "${TARGET_DIR}/examples"
cat <<'EOF_5' > "${TARGET_DIR}/examples/canal.txt"
# Lista de canais para exemplo
@canalsandeco
EOF_5

mkdir -p "${TARGET_DIR}/examples"
cat <<'EOF_6' > "${TARGET_DIR}/examples/cookies.txt"
# Netscape HTTP Cookie File
# Substitua este arquivo pelos cookies exportados do YouTube (yt-dlp)
# Linhas abaixo são apenas ilustrativas e não funcionais.
.youtube.com    TRUE    /   FALSE   0   CONSENT    PENDING
EOF_6

mkdir -p "${TARGET_DIR}/logs"
cat <<'EOF_7' > "${TARGET_DIR}/logs/.gitkeep"

EOF_7

cat <<'EOF_8' > "${TARGET_DIR}/pyproject.toml"
[project]
name = "info-ai-studio"
version = "0.1.0"
description = "Info_AI_Studio: coleta de informações web e YouTube com interface CLI e Streamlit"
authors = [{name = "Info_AI_Studio Team"}]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.32",
    "typer[all]>=0.9",
    "python-dotenv>=1.0",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=4.9",
    "python-dateutil>=2.8",
    "youtube-transcript-api>=0.6.2",
    "openai>=1.12",
    "yt-dlp>=2024.3.10",
    "faster-whisper>=1.0.0",
    "fpdf2>=2.7.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
]

[project.scripts]
app = "app.interfaces.cli.main:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-q"
EOF_8

mkdir -p "${TARGET_DIR}/resultados_extracao"
cat <<'EOF_9' > "${TARGET_DIR}/resultados_extracao/.gitkeep"

EOF_9

mkdir -p "${TARGET_DIR}/src/app"
cat <<'EOF_10' > "${TARGET_DIR}/src/app/__init__.py"

EOF_10

mkdir -p "${TARGET_DIR}/src/app"
cat <<'EOF_11' > "${TARGET_DIR}/src/app/config.py"
"""Application configuration helpers."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency during tests
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return False


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    db_path: Path
    max_palavras_resumo: int
    llm_provider: str
    llm_model: str
    llm_api_key: str
    token_limit: int
    resultados_dir: Path
    backup_dir: Path
    log_dir: Path
    cookies_path: Optional[Path]


def _load_env() -> None:
    """Load .env file values if available."""

    load_dotenv(override=False)


def _provider_env_var(provider: str) -> str:
    """Compute the provider-specific API key environment variable."""

    normalized = re.sub(r"[^A-Z0-9]+", "_", provider.strip().upper()).strip("_")
    return f"{normalized or 'LLM'}_API_KEY"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    _load_env()
    db_path = Path(os.getenv("DB_PATH", "./data.db")).expanduser().resolve()
    max_palavras = int(os.getenv("MAX_PALAVRAS_RESUMO", "150") or 150)
    llm_provider = os.getenv("LLM_PROVIDER", "OPENAI").strip()
    llm_model = os.getenv("LLM_MODEL", "gpt-5-nano").strip()
    provider_env_var = _provider_env_var(llm_provider)
    llm_api_key = os.getenv(provider_env_var, os.getenv("LLM_API_KEY", "")).strip()
    token_limit = int(os.getenv("TOKEN_LIMIT", "4096") or 4096)
    resultados_dir = Path(os.getenv("RESULTADOS_DIR", "resultados_extracao"))
    backup_dir = Path(os.getenv("BACKUP_DIR", "backup"))
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    cookies_env = os.getenv("COOKIES_PATH", "cookies.txt").strip()
    cookies_path = Path(cookies_env) if cookies_env else None
    return Settings(
        db_path=db_path,
        max_palavras_resumo=max_palavras,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        token_limit=token_limit,
        resultados_dir=resultados_dir,
        backup_dir=backup_dir,
        log_dir=log_dir,
        cookies_path=cookies_path,
    )


def reload_settings() -> None:
    """Clear cached configuration to reload updated environment variables."""

    get_settings.cache_clear()
EOF_11

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_12' > "${TARGET_DIR}/src/app/domain/__init__.py"

EOF_12

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_13' > "${TARGET_DIR}/src/app/domain/entities.py"
"""Domain entities used throughout the application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class LLMModel:
    """Representa um modelo LLM disponível."""

    provedor: str
    modelo: str
    api_key: str
    status: bool = True
    model_id: int | None = None


@dataclass(slots=True)
class YouTubeChannel:
    """Informações básicas de um canal do YouTube."""

    nome: str
    descricao: str
    grupo: str
    canal_id: str
    status: bool = True


@dataclass(slots=True)
class WebSource:
    """Fonte web cadastrada."""

    tipo: str
    fonte: str
    descricao: str
    status: bool = True


@dataclass(slots=True)
class YouTubeExtractionConfig:
    """Parâmetros para execução da extração do YouTube."""

    outdir: Path
    prefix: str
    days: Optional[int]
    channels: list[str]
    channels_file: Optional[Path]
    mode: str
    no_llm: bool
    asr_enabled: bool
    asr_provider: str
    llm_provider: Optional[str]
    llm_model: str
    llm_key: Optional[str]
    resumo_max_palavras: int
    cookies: Optional[Path]
    user_agent: str
    report_format: str
    max_videos: Optional[int]


@dataclass(slots=True)
class YouTubeExtractionResult:
    """Resultado da execução da extração do YouTube."""

    json_path: Optional[Path]
    report_path: Optional[Path]
    log_path: Optional[Path]
    total_videos: int
    total_channels: int
    message: str
    token_details: list[dict[str, int | str]]
    channel_tokens: list[dict[str, int | str]]
    total_prompt_tokens: int
    total_completion_tokens: int
EOF_13

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_14' > "${TARGET_DIR}/src/app/domain/fonte_service.py"
"""Domain services for registering sources and channels."""

from __future__ import annotations

from typing import Any

from app.domain.entities import WebSource, YouTubeChannel
from app.domain import validators
from app.infrastructure import repositories


def register_youtube_channel(channel: YouTubeChannel) -> None:
    """Persist YouTube channel metadata."""

    channel_id = validators.normalize_channel_id(channel.canal_id)
    repositories.save_youtube_channel(
        nome_canal=channel.nome,
        descricao=channel.descricao,
        grupo=channel.grupo,
        canal_id=channel_id,
        status=1 if channel.status else 0,
    )


def list_youtube_channels(active_only: bool = True) -> list[dict[str, Any]]:
    """Return stored channels."""

    return repositories.list_youtube_channels(active_only=active_only)


def register_web_source(source: WebSource) -> None:
    """Persist a new web source using domain validations."""

    validators.validate_fonte_web(source.tipo, source.fonte)
    repositories.save_web_source(
        tipo=source.tipo,
        fonte=source.fonte,
        descricao=source.descricao,
        status=1 if source.status else 0,
    )


def list_web_sources(active_only: bool = True) -> list[dict[str, Any]]:
    """Return stored web sources."""

    return repositories.list_web_sources(active_only=active_only)
EOF_14

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_15' > "${TARGET_DIR}/src/app/domain/llm_client.py"
"""LLM client abstraction used to summarise video transcripts."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Optional

LOGGER = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency for tests
    OpenAI = None  # type: ignore


@dataclass(slots=True)
class LLMResult:
    """Structured response from a summarisation request."""

    resumo_uma_frase: str
    resumo: str
    assunto_principal: str
    palavras_chave: list[str]
    resumo_em_topicos: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    cost: float


class LLMClient:
    """Wrapper around supported LLM providers."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str],
        token_limit: int,
    ) -> None:
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or ""
        self.token_limit = token_limit
        self._client = None
        if self.provider == "openai" and self.api_key and OpenAI is not None:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - depends on runtime
                LOGGER.warning("Falha ao inicializar cliente OpenAI: %s", exc)
                self._client = None
        elif self.api_key:
            LOGGER.warning("Provedor LLM '%s' não suportado; análises serão desativadas.", provider)

    @property
    def active(self) -> bool:
        """Return True when the provider can perform requests."""

        return self._client is not None

    def summarise(
        self,
        title: str,
        transcript: str,
        channel: str,
        max_palavras: int,
    ) -> LLMResult:
        """Generate a structured summary for a transcript."""

        transcript_clean = transcript.strip()
        if not transcript_clean:
            LOGGER.info("[LLM] Transcrição vazia — pulando análise para %s", title)
            return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
        if not self.active:
            LOGGER.info("[LLM] Cliente LLM ausente — usando resumo heurístico.")
            return self._heuristic_summary(title, transcript_clean, max_palavras)
        prompt = (
            "Você é um analista. Resuma a transcrição de um vídeo do YouTube.\n"
            f"Título: {title}\n"
            f"Canal: {channel}\n"
            f"Transcrição: {transcript_clean[: min(len(transcript_clean), 8000)]}\n"
            "Responda em JSON válido com as chaves: resumo_do_video_uma_frase,"
            " resumo_do_video, assunto_principal, palavras_chave (lista) e resumo_em_topicos (Markdown)."
            f" Limite o campo resumo_do_video a {max_palavras} palavras."
        )
        try:
            response = None
            client = self._client
            if client is None:
                raise RuntimeError("LLM client not available")

            if hasattr(client, "responses"):
                response = client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_output_tokens=self._max_output_tokens(),
                )
                content = self._extract_responses_content(response)
                usage = getattr(response, "usage", None)
                prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
                completion_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
            elif hasattr(client, "chat") and hasattr(client.chat, "completions"):
                token_limit = self._max_output_tokens()
                base_kwargs = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                }
                response = None
                last_exc: Exception | None = None
                for param_name in ("max_completion_tokens", "max_tokens"):
                    kwargs = dict(base_kwargs)
                    kwargs[param_name] = token_limit
                    try:
                        response = client.chat.completions.create(**kwargs)
                        break
                    except Exception as exc:  # pragma: no cover - depends on SDK behaviour
                        last_exc = exc
                        message = str(exc)
                        if param_name == "max_completion_tokens" and (
                            "max_completion_tokens" in message or "max_tokens" in message
                        ):
                            continue
                        if param_name == "max_tokens" and (
                            "max_tokens" in message or "max_completion_tokens" in message
                        ):
                            continue
                        raise
                if response is None:
                    if last_exc is not None:
                        raise last_exc
                    raise RuntimeError("Falha ao invocar chat.completions")
                content = response.choices[0].message.content if response.choices else ""
                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            else:  # pragma: no cover - legacy clients
                create = getattr(getattr(client, "ChatCompletion", None), "create", None)
                if not create:
                    raise RuntimeError("OpenAI client incompatível")
                response = create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self._max_output_tokens(),
                )
                content = response["choices"][0]["message"]["content"] if response else ""
                usage = response.get("usage", {}) if isinstance(response, dict) else {}
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
            if not content:
                LOGGER.warning("[LLM] Resposta vazia do modelo para %s", title)
                return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
            data = json.loads(content)
            return LLMResult(
                resumo_uma_frase=str(data.get("resumo_do_video_uma_frase", "")),
                resumo=str(data.get("resumo_do_video", "")),
                assunto_principal=str(data.get("assunto_principal", "")),
                palavras_chave=list(data.get("palavras_chave", [])),
                resumo_em_topicos=str(data.get("resumo_em_topicos", "")),
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
                model=self.model,
                cost=0.0,
            )
        except Exception as exc:  # pragma: no cover - depends on API
            LOGGER.warning("[LLM] Erro durante chamada ao modelo: %s", exc)
            return self._heuristic_summary(title, transcript_clean, max_palavras)

    def _heuristic_summary(
        self, title: str, transcript: str, max_palavras: int
    ) -> LLMResult:
        """Generate a lightweight summary when no LLM is available."""

        words = transcript.split()
        resumo_words = words[: max(1, min(len(words), max_palavras))]
        resumo = " ".join(resumo_words)
        resumo_uma_frase = resumo.split(".")[0][:280] if resumo else ""
        keywords = sorted({w.strip(".,;:!?\"'").lower() for w in words[:200] if len(w) > 4})
        topicos = "\n".join(f"- {token}" for token in keywords[:8])
        return LLMResult(
            resumo_uma_frase=resumo_uma_frase,
            resumo=resumo,
            assunto_principal=title[:120],
            palavras_chave=list(keywords[:12]),
            resumo_em_topicos=topicos,
            prompt_tokens=0,
            completion_tokens=0,
            model=self.model,
            cost=0.0,
        )

    def _extract_responses_content(self, response: Any) -> str:
        """Read textual content from the OpenAI responses payload."""

        if response is None:
            return ""
        text = getattr(response, "output_text", "")
        if text:
            return str(text)
        output_blocks = getattr(response, "output", None)
        if output_blocks:
            fragments: list[str] = []
            for block in output_blocks:
                content_items = getattr(block, "content", None)
                if content_items is None and isinstance(block, dict):
                    content_items = block.get("content")
                for item in content_items or []:
                    piece = getattr(item, "text", None)
                    if piece is None and isinstance(item, dict):
                        piece = item.get("text")
                    if piece:
                        fragments.append(str(piece))
            if fragments:
                return "".join(fragments)
        choices = getattr(response, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            if isinstance(message, dict):
                return str(message.get("content", ""))
            if message is not None:
                content = getattr(message, "content", "")
                if content:
                    return str(content)
        return ""

    def _max_output_tokens(self) -> int:
        """Calculate a conservative output token limit."""

        # heurística simples: 4 tokens por palavra + margem
        return max(256, math.ceil(self.token_limit * 0.25))
EOF_15

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_16' > "${TARGET_DIR}/src/app/domain/llm_service.py"
"""Domain services related to LLM models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.entities import LLMModel
from app.infrastructure import env_manager, repositories

try:  # pragma: no cover - optional dependency at runtime
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


@dataclass(slots=True)
class LLMConnectionResult:
    """Resultado de validação de credenciais do modelo LLM."""

    sucesso: bool
    mensagem: str
    variavel_ambiente: str


class LLMConnectionError(RuntimeError):
    """Erro ao validar conexão com LLM."""

    def __init__(self, message: str, env_var: str) -> None:
        super().__init__(message)
        self.message = message
        self.env_var = env_var


def _normalizar_provedor(provedor: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", provedor.strip().upper()).strip("_")


def compute_api_key_env_name(provedor: str) -> str:
    """Retorna o nome padrão da variável de API para o provedor informado."""

    normalizado = _normalizar_provedor(provedor)
    return f"{normalizado or 'LLM'}_API_KEY"


def register_llm_model(model: LLMModel) -> None:
    """Persist a new LLM model or update an existing one."""

    provedor_normalizado = _normalizar_provedor(model.provedor)
    if model.model_id is not None:
        repositories.update_llm_model(
            model_id=model.model_id,
            provedor=provedor_normalizado,
            modelo=model.modelo,
            api_key=model.api_key,
            status=1 if model.status else 0,
        )
    else:
        repositories.save_llm_model(
            provedor=provedor_normalizado,
            modelo=model.modelo,
            api_key=model.api_key,
            status=1 if model.status else 0,
        )

    env_var = compute_api_key_env_name(provedor_normalizado)
    env_manager.update_env_values(
        {
            "LLM_PROVIDER": provedor_normalizado,
            "LLM_MODEL": model.modelo,
            "LLM_API_KEY": model.api_key,
            env_var: model.api_key,
        }
    )


def list_llm_models() -> list[dict[str, Any]]:
    """Return stored LLM models using normalized field names."""

    registros = repositories.list_llm_models()
    resultado: list[dict[str, Any]] = []
    for row in registros:
        resultado.append(
            {
                "id": row["modl_id"],
                "provedor": row["modl_provedor"],
                "modelo": row["modl_modelo_llm"],
                "api_key": row["modl_api_key"],
                "status": bool(row["modl_status"]),
                "created_at": row["modl_created_at"],
                "env_var": compute_api_key_env_name(row["modl_provedor"]),
            }
        )
    return resultado


def get_llm_model(model_id: int) -> LLMModel | None:
    """Fetch an LLM model and adapt it to the domain entity."""

    dados = repositories.get_llm_model(model_id)
    if not dados:
        return None
    return LLMModel(
        provedor=dados["modl_provedor"],
        modelo=dados["modl_modelo_llm"],
        api_key=dados["modl_api_key"],
        status=bool(dados["modl_status"]),
        model_id=dados["modl_id"],
    )


def delete_llm_model(model_id: int) -> None:
    """Remove o modelo informado."""

    repositories.delete_llm_model(model_id)


def _traduzir_erro(mensagem: str) -> str:
    """Mapeia mensagens de erro comuns para Português."""

    texto = mensagem.strip()
    if not texto:
        return "Erro desconhecido ao validar o modelo."
    texto_lower = texto.lower()
    if "api key" in texto_lower and ("invalid" in texto_lower or "incorrect" in texto_lower):
        return "Chave de API inválida ou não autorizada."
    if "not found" in texto_lower or "does not exist" in texto_lower:
        return "Modelo informado não existe ou não está disponível."
    if "rate limit" in texto_lower:
        return "Limite de requisições atingido para o provedor."
    if "timeout" in texto_lower or "connection" in texto_lower:
        return "Não foi possível conectar ao provedor. Verifique sua rede."
    return texto


def test_llm_connection(model: LLMModel) -> LLMConnectionResult:
    """Verifica se as credenciais informadas permitem acessar o provedor."""

    provedor_normalizado = _normalizar_provedor(model.provedor)
    env_var = compute_api_key_env_name(provedor_normalizado)
    if not provedor_normalizado:
        raise LLMConnectionError("Informe o provedor do modelo.", env_var)
    if not model.api_key.strip():
        raise LLMConnectionError("Informe a chave de API para testar a conexão.", env_var)
    if provedor_normalizado == "OPENAI":
        if OpenAI is None:
            raise LLMConnectionError(
                "Biblioteca OpenAI não instalada no ambiente.", env_var
            )
        try:
            cliente = OpenAI(api_key=model.api_key)
            cliente.models.retrieve(model.modelo)
            return LLMConnectionResult(
                sucesso=True,
                mensagem=(
                    f"Conexão com {provedor_normalizado} bem-sucedida."
                    f" Variável {env_var} válida."
                ),
                variavel_ambiente=env_var,
            )
        except Exception as exc:  # pragma: no cover - depende da API externa
            mensagem = _traduzir_erro(str(exc))
            raise LLMConnectionError(mensagem, env_var) from exc
    raise LLMConnectionError(
        f"Provedor {provedor_normalizado} ainda não suportado para validação.", env_var
    )
EOF_16

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_17' > "${TARGET_DIR}/src/app/domain/parameters_service.py"
"""Domain services for configurable parameters stored in .env."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from app.config import reload_settings
from app.infrastructure.env_manager import update_env_values


def update_parameters(values: Mapping[str, str]) -> Path:
    """Persist parameters to the .env file and reload application settings."""

    path = update_env_values(values)
    reload_settings()
    return path
EOF_17

mkdir -p "${TARGET_DIR}/src/app/domain"
cat <<'EOF_18' > "${TARGET_DIR}/src/app/domain/validators.py"
"""Domain level validations for inputs."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.infrastructure import repositories


_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_valid_url(value: str) -> bool:
    """Validate basic structure of an URL."""

    if not value:
        return False
    if not _URL_RE.match(value.strip()):
        return False
    parsed = urlparse(value)
    return all([parsed.scheme, parsed.netloc])


def validate_fonte_web(tipo: str, fonte: str) -> None:
    """Validate source rules based on type."""

    tipo_norm = tipo.lower().strip()
    fonte_norm = fonte.strip()
    if tipo_norm in {"site", "blog"} and not is_valid_url(fonte_norm):
        raise ValueError("O campo 'fonte' deve conter uma URL completa para sites/blogs.")
    if tipo_norm == "youtube":
        if not repositories.get_youtube_channel_by_id(fonte_norm):
            raise ValueError(
                "Canal não encontrado. Cadastre o canal do YouTube antes de usá-lo como fonte."
            )


def normalize_channel_id(channel: str) -> str:
    """Normalize a channel identifier to start with @ when missing."""

    channel = channel.strip()
    if channel and not channel.startswith("@") and not channel.startswith("UC"):
        return f"@{channel}"
    return channel
EOF_18

mkdir -p "${TARGET_DIR}/src/app/domain/youtube"
cat <<'EOF_19' > "${TARGET_DIR}/src/app/domain/youtube/__init__.py"

EOF_19

mkdir -p "${TARGET_DIR}/src/app/domain/youtube"
cat <<'EOF_20' > "${TARGET_DIR}/src/app/domain/youtube/extractor_plus.py"
# -*- coding: utf-8 -*-
"""
YouTube Extractor (plus)
- Extrai vídeos da aba /videos (ignora Shorts/Live/Upcoming)
- Filtra por janela de dias (max_age_days)
- Lê /about para dados do canal
- Obtém metadados do vídeo (duração/data) pela página do vídeo
- Obtém transcrição com youtube_transcript_api (preferindo transcrições nativas; tradução se necessário)
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("youtube_extractor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class YouTubeExtractor:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: int = 25,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.user_agent = user_agent

    # --------------------- Infra ---------------------
    def get_http_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def _make_request(self, url: str) -> Optional[requests.Response]:
        try:
            return self.session.get(url, headers=self.get_http_headers(), timeout=self.timeout)
        except Exception as e:
            logger.warning(f"Falha ao requisitar {url}: {e}")
            return None

    def _normalize_text_basic(self, s: str) -> str:
        if not s:
            return ""
        import unicodedata
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s.lower().strip()

    def _normalize_channel_videos_url(self, channel_id: str) -> str:
        if channel_id.startswith("UC"):
            return f"https://www.youtube.com/channel/{channel_id}/videos"
        if channel_id.startswith("@"):
            return f"https://www.youtube.com/{channel_id}/videos"
        return f"https://www.youtube.com/@{channel_id}/videos"

    def _normalize_channel_about_url(self, channel_id: str) -> str:
        if channel_id.startswith("UC"):
            return f"https://www.youtube.com/channel/{channel_id}/about"
        if channel_id.startswith("@"):
            return f"https://www.youtube.com/{channel_id}/about"
        return f"https://www.youtube.com/@{channel_id}/about"

    # --------------------- Tempo relativo ---------------------
    def _parse_relative_time(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        t = text.strip().lower()
        if any(k in t for k in ["live now", "ao vivo", "transmitindo agora", "upcoming", "programado"]):
            return None
        now = datetime.utcnow()
        t = (
            t.replace("atrás", "")
            .replace("ago", "")
            .replace("há", "")
            .replace("streamed", "")
            .replace("transmitido", "")
            .strip()
        )
        pats = [
            (r"(\d+)\s*min", "minutes"),
            (r"(\d+)\s*minute", "minutes"),
            (r"(\d+)\s*hora", "hours"),
            (r"(\d+)\s*hour", "hours"),
            (r"(\d+)\s*dia", "days"),
            (r"(\d+)\s*day", "days"),
            (r"(\d+)\s*semana", "weeks"),
            (r"(\d+)\s*week", "weeks"),
            (r"(\d+)\s*m[eê]s", "months"),
            (r"(\d+)\s*month", "months"),
            (r"(\d+)\s*ano", "years"),
            (r"(\d+)\s*year", "years"),
        ]
        for pat, unit in pats:
            m = re.search(pat + r"s?", t)
            if m:
                n = int(m.group(1))
                if unit == "minutes":
                    return now - timedelta(minutes=n)
                if unit == "hours":
                    return now - timedelta(hours=n)
                if unit == "days":
                    return now - timedelta(days=n)
                if unit == "weeks":
                    return now - timedelta(weeks=n)
                if unit == "months":
                    return now - timedelta(days=30 * n)
                if unit == "years":
                    return now - timedelta(days=365 * n)
        return None

    # --------------------- Extração de vídeos ---------------------
    def extract_recent_videos(
        self,
        channel_id: str,
        max_age_days: Optional[int] = None,
        videos_tab_only: bool = True,
        max_videos: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        logger.info(
            "Extraindo vídeos do canal {} (max_age_days={}, videos_tab_only={}, max_videos={})".format(
                channel_id, max_age_days, videos_tab_only, max_videos
            )
        )
        return self._extract_from_videos_tab(
            channel_id, max_age_days=max_age_days, max_videos=max_videos
        )

    def _extract_from_videos_tab(
        self, channel_id: str, max_age_days: Optional[int], max_videos: Optional[int] = None
    ) -> List[Dict[str, str]]:
        url = self._normalize_channel_videos_url(channel_id)
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            logger.warning(f"Falha ao acessar {url}")
            return []
        html = resp.text

        # Localiza ytInitialData
        initial_data = None
        for ptn in [
            r"var ytInitialData = (\{.*?\});",
            r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayer',
            r'ytInitialData"\s*:\s*(\{.*?\})\s*[,}]',
        ]:
            m = re.search(ptn, html, re.S)
            if m:
                try:
                    initial_data = json.loads(m.group(1))
                    break
                except Exception:
                    pass
        if not initial_data:
            logger.warning("Não foi possível localizar ytInitialData na aba /videos")
            return []

        # Conteúdo da aba "Vídeos"
        contents = []
        continuation_token = None
        rgr = {}
        try:
            tabs = initial_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
            for tab in tabs:
                tr = tab.get("tabRenderer", {})
                raw_title = tr.get("title") or ""
                title_norm = self._normalize_text_basic(raw_title)
                selected = tr.get("selected") is True
                if "videos" in title_norm or selected:
                    rgr = tr.get("content", {}).get("richGridRenderer", {})
                    contents = rgr.get("contents", [])
                    try:
                        continuation_token = (
                            rgr["continuations"][0]["nextContinuationData"]["continuation"]
                        )
                    except Exception:
                        continuation_token = None
                    break
        except Exception:
            pass

        videos: List[Dict[str, str]] = []
        shelves_skipped = 0
        live_count = 0
        upcoming_count = 0
        nodate_count = 0
        older_count = 0
        parsed_count = 0

        def push_video(vr: dict) -> bool:
            nonlocal live_count, upcoming_count, nodate_count, older_count
            vid = vr.get("videoId")
            if not vid:
                return True

            badges = vr.get("badges") or []
            is_live = any("LIVE" in (b.get("metadataBadgeRenderer", {}).get("label") or "").upper() for b in badges)
            upcoming = vr.get("upcomingEventData") is not None
            if is_live or upcoming:
                if is_live:
                    live_count += 1
                if upcoming:
                    upcoming_count += 1
                return True

            title = ""
            try:
                title = vr["title"]["runs"][0]["text"]
            except Exception:
                pass

            rel = ""
            try:
                rel = vr.get("publishedTimeText", {}).get("simpleText", "") or ""
            except Exception:
                pass

            published_dt = self._parse_relative_time(rel)

            if max_age_days is not None:
                if published_dt is None:
                    nodate_count += 1
                    return True
                age_days = (datetime.utcnow() - published_dt).days
                if age_days > max_age_days:
                    older_count += 1
                    return False

            videos.append(
                {
                    "id": vid,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published": published_dt.isoformat() if published_dt else "",
                    "published_relative": rel,
                }
            )

            if max_videos is not None and len(videos) >= max_videos:
                return False

            return True

        stop = False
        for item in contents:
            if "reelShelfRenderer" in item or "richSectionRenderer" in item:
                shelves_skipped += 1
                continue
            content = item.get("richItemRenderer", {}).get("content") or item
            if "videoRenderer" in content:
                parsed_count += 1
                if not push_video(content["videoRenderer"]):
                    stop = True
                    break
            elif "gridVideoRenderer" in content:
                parsed_count += 1
                if not push_video(content["gridVideoRenderer"]):
                    stop = True
                    break

        # Processa continuations
        if not stop and continuation_token:
            api_key = None
            context = {}
            try:
                api_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html).group(1)
                context = json.loads(
                    re.search(r'"INNERTUBE_CONTEXT":(\{.*?\})', html, re.S).group(1)
                )
            except Exception:
                api_key = None
                context = {}

            headers = self.get_http_headers()
            headers["Content-Type"] = "application/json"

            token = continuation_token
            while token and (max_videos is None or len(videos) < max_videos):
                try:
                    browse_url = f"https://www.youtube.com/youtubei/v1/browse?key={api_key}"
                    payload = {"continuation": token, "context": context}
                    resp = self.session.post(
                        browse_url, json=payload, headers=headers, timeout=self.timeout
                    )
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                except Exception:
                    break

                items = (
                    data.get("onResponseReceivedActions", [{}])[0]
                    .get("appendContinuationItemsAction", {})
                    .get("continuationItems", [])
                )
                token = None
                for item in items:
                    if "continuationItemRenderer" in item:
                        try:
                            token = (
                                item["continuationItemRenderer"]["continuationEndpoint"][
                                    "continuationCommand"
                                ]["token"]
                            )
                        except Exception:
                            token = None
                        continue
                    if "reelShelfRenderer" in item or "richSectionRenderer" in item:
                        shelves_skipped += 1
                        continue
                    content = item.get("richItemRenderer", {}).get("content") or item
                    if "videoRenderer" in content:
                        parsed_count += 1
                        if not push_video(content["videoRenderer"]):
                            stop = True
                            break
                    elif "gridVideoRenderer" in content:
                        parsed_count += 1
                        if not push_video(content["gridVideoRenderer"]):
                            stop = True
                            break
                if stop or not token:
                    break

        logger.info(
            "Aba /videos: analisados={parsed}, válidos={validos}, ignorados: live={live}, upcoming={up}, "
            "sem_data={nd}, antigos={old}, shelves={shelves}".format(
                parsed=parsed_count,
                validos=len(videos),
                live=live_count,
                up=upcoming_count,
                nd=nodate_count,
                old=older_count,
                shelves=shelves_skipped,
            )
        )
        logger.info(
            "Aba /videos: {} vídeos válidos{}".format(
                len(videos), f" (≤ {max_age_days} dias)" if max_age_days is not None else ""
            )
        )
        return videos

    # --------------------- Canal /about ---------------------
    def extract_channel_info(self, channel_id: str) -> Dict[str, str]:
        url = self._normalize_channel_about_url(channel_id)
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            return {"status": "error", "message": f"Falha ao acessar {url}"}

        html = resp.text
        initial_data = None
        for ptn in [
            r"var ytInitialData = (\{.*?\});",
            r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayer',
            r'ytInitialData"\s*:\s*(\{.*?\})\s*[,}]',
        ]:
            m = re.search(ptn, html, re.S)
            if m:
                try:
                    initial_data = json.loads(m.group(1))
                    break
                except Exception:
                    pass

        name = channel_id
        description = ""
        subs = ""
        video_count = ""

        try:
            header = initial_data["header"]["c4TabbedHeaderRenderer"]
            name = header.get("title", name)
            subs = (header.get("subscriberCountText", {}).get("simpleText") or subs).strip()
            about_tabs = initial_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
            for tab in about_tabs:
                tr = tab.get("tabRenderer", {})
                title_norm = self._normalize_text_basic(tr.get("title") or "")
                if "about" in title_norm or "sobre" in title_norm:
                    sec = tr.get("content", {}).get("sectionListRenderer", {}).get("contents", [])
                    if sec:
                        text = sec[0].get("itemSectionRenderer", {}).get("contents", [])
                        if text:
                            desc = text[0].get("channelAboutFullMetadataRenderer", {}).get("description", {})
                            description = (desc.get("simpleText") or description).strip()
                    break
        except Exception:
            pass

        try:
            video_count = str(initial_data["metadata"]["channelMetadataRenderer"].get("videoCount", ""))
        except Exception:
            pass

        return {
            "status": "success",
            "name": name or channel_id,
            "subscriber_count": subs,
            "description": description or "",
            "video_count": video_count,
        }

    # --------------------- Lote ---------------------
    def extract_batch_channels(
        self,
        channel_ids: List[str],
        include_videos: bool = True,
        max_age_days: Optional[int] = None,
        videos_tab_only: bool = True,
        max_videos: Optional[int] = None,
    ) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {"channels": {}}
        start = time.time()
        for i, cid in enumerate(channel_ids, 1):
            logger.info(f"[{i}/{len(channel_ids)}] Canal: {cid}")
            info = self.extract_channel_info(cid)
            results["channels"][cid] = info
            if include_videos and info.get("status") == "success":
                vids = self.extract_recent_videos(
                    cid,
                    max_age_days=max_age_days,
                    videos_tab_only=videos_tab_only,
                    max_videos=max_videos,
                )
                info["recent_videos"] = vids
                info["video_count_extracted"] = len(vids)

        results["took_seconds"] = round(time.time() - start, 3)
        results["params"] = {
            "include_videos": include_videos,
            "max_age_days": max_age_days,
            "videos_tab_only": videos_tab_only,
            "max_videos": max_videos,
        }
        return results

    # --------------------- Metadados e Transcrição ---------------------
    def _parse_iso8601_duration(self, iso: str) -> int:
        try:
            m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
            if not m:
                return 0
            h = int(m.group(1) or 0)
            m_ = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            return h * 3600 + m_ * 60 + s
        except Exception:
            return 0

    def _format_hhmmss(self, seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def fetch_video_details(self, video_id: str) -> Dict[str, str]:
        """Duração (segundos, hh:mm:ss) e data de publicação pela página do vídeo."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            return {"duration_seconds": 0, "duration_hhmmss": "", "date_published": "", "url": url}

        html = resp.text
        duration_seconds = 0
        date_published = ""

        # JSON-LD
        try:
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S | re.I):
                data = json.loads(m.group(1))
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "VideoObject":
                            iso = item.get("duration") or ""
                            duration_seconds = self._parse_iso8601_duration(iso) or duration_seconds
                            date_published = item.get("uploadDate") or item.get("datePublished") or date_published
                elif isinstance(data, dict) and data.get("@type") == "VideoObject":
                    iso = data.get("duration") or ""
                    duration_seconds = self._parse_iso8601_duration(iso) or duration_seconds
                    date_published = data.get("uploadDate") or data.get("datePublished") or date_published
        except Exception:
            pass

        # ytInitialPlayerResponse
        if duration_seconds == 0 or not date_published:
            try:
                m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;", html, re.S)
                if m:
                    p = json.loads(m.group(1))
                    ls = p.get("videoDetails", {}).get("lengthSeconds")
                    if ls and str(ls).isdigit():
                        duration_seconds = int(ls)
                    micro = p.get("microformat", {}).get("playerMicroformatRenderer", {})
                    date_published = micro.get("publishDate") or micro.get("uploadDate") or date_published
            except Exception:
                pass

        return {
            "duration_seconds": duration_seconds,
            "duration_hhmmss": self._format_hhmmss(duration_seconds) if duration_seconds else "",
            "date_published": date_published or "",
            "url": url,
        }

    def _fetch_transcript_ytdlp(self, video_id: str, preferred_langs=None) -> str:
        """Fallback de transcrição via yt-dlp, usando legendas do YouTube."""
        try:
            import yt_dlp
        except Exception:
            return ""
        langs = preferred_langs or ["pt", "pt-BR", "pt-PT", "en"]
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
        }
        try:
            import os
            if os.path.exists("cookies.txt"):
                ydl_opts["cookiefile"] = "cookies.txt"
                logger.info("yt-dlp usando cookies de cookies.txt")
        except Exception:
            pass
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or {}
            auto = info.get("automatic_captions") or {}

            def _grab(src):
                for lang in langs:
                    tracks = src.get(lang)
                    if not tracks:
                        continue
                    link = tracks[0].get("url")
                    if not link:
                        continue
                    try:
                        resp = requests.get(
                            link, headers=self.get_http_headers(), timeout=self.timeout
                        )
                        if resp.status_code == 200:
                            return self._vtt_to_text(resp.text)
                    except Exception:
                        continue
                return ""

            text = _grab(subs)
            if text:
                return text
            return _grab(auto)
        except Exception as e:
            logger.info(f"Transcrição: yt-dlp falhou para {video_id}: {e}")
        return ""

    def _vtt_to_text(self, data: str) -> str:
        lines = []
        for line in data.splitlines():
            line = line.strip()
            if (
                not line
                or line.startswith("WEBVTT")
                or line.startswith("#")
                or "-->" in line
                or line.isdigit()
            ):
                continue
            lines.append(line)
        return " ".join(lines)

    def fetch_transcript_text(self, video_id: str, preferred_langs=None) -> str:
        """Transcrição concatenada via youtube_transcript_api (quando disponível).
        Preferência: manual > gerada; tenta idiomas preferidos e, se necessário, tradução.
        Importa apenas YouTubeTranscriptApi para ser compatível com várias versões.
        """
        if preferred_langs is None:
            preferred_langs = ["pt", "pt-BR", "pt-PT", "en"]

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            try:
                from youtube_transcript_api._errors import (
                    RequestBlocked,
                    IpBlocked,
                    YouTubeRequestFailed,
                    CouldNotRetrieveTranscript,
                    TranslationLanguageNotAvailable,
                )
            except Exception:
                RequestBlocked = IpBlocked = YouTubeRequestFailed = (
                    CouldNotRetrieveTranscript
                ) = TranslationLanguageNotAvailable = Exception
        except Exception as e:
            logger.info(f"Transcrição: biblioteca youtube_transcript_api indisponível: {e}")
            return ""

        blocked_errors = (
            RequestBlocked,
            IpBlocked,
            YouTubeRequestFailed,
            CouldNotRetrieveTranscript,
        )

        def _short_err(e: Exception) -> str:
            """Retorna uma versão resumida, porém sempre preenchida, do erro."""
            msg = str(e).strip()
            if not msg:
                msg = repr(e)
            return msg.splitlines()[0].strip()

        def _join(tr_list):
            parts: list[str] = []
            for item in tr_list or []:
                text = getattr(item, "text", None)
                if text is None and isinstance(item, dict):
                    text = item.get("text")
                elif text is None:
                    getter = getattr(item, "get", None)
                    if callable(getter):
                        text = getter("text", None)
                if text:
                    parts.append(str(text))
            return " ".join(parts)

        # 1) listar transcript objects (compatibilidade com versões novas/antigas)
        try:
            tl = None
            for attr in ("list_transcripts", "list"):
                fn = getattr(YouTubeTranscriptApi, attr, None)
                if not callable(fn):
                    continue
                try:
                    tl = fn(video_id)
                    break
                except TypeError:
                    # método de instância
                    api = YouTubeTranscriptApi()
                    inst_fn = getattr(api, attr, None)
                    if callable(inst_fn):
                        tl = inst_fn(video_id)
                        break
            if tl is None:
                raise AttributeError("YouTubeTranscriptApi.list(_transcripts) ausente")
        except blocked_errors as e:
            logger.info(
                f"Transcrição: acesso bloqueado ao listar para {video_id}: {_short_err(e)}"
            )
            return self._fetch_transcript_ytdlp(video_id, preferred_langs)
        except Exception as e:
            logger.info(
                f"Transcrição: falha ao listar para {video_id}: {_short_err(e)}"
            )
            return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        # lista concreta para múltiplas passagens
        all_transcripts = list(tl)
        if not all_transcripts:
            logger.info(f"Transcrição: nenhuma disponível para {video_id}")
            return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        disp = [f"{t.language_code}{'(auto)' if t.is_generated else ''}" for t in all_transcripts]
        logger.info(f"Transcrição: disponíveis {disp} para {video_id}")

        def _try_fetch(tr) -> Tuple[str, bool]:
            try:
                text = _join(tr.fetch())
                if text.strip():
                    logger.info(
                        f"Transcrição encontrada ({len(text)} chars, {tr.language_code}) para {video_id}"
                    )
                    return text, False
            except blocked_errors as e:
                logger.info(
                    f"Transcrição: acesso bloqueado ou indisponível para {video_id}: {_short_err(e)}"
                )
                text = self._fetch_transcript_ytdlp(video_id, preferred_langs)
                if text:
                    return text, False
                return "", True
            except Exception as e:
                logger.info(
                    f"Transcrição: falha ao obter {tr.language_code}{'(auto)' if getattr(tr, 'is_generated', False) else ''} para {video_id}: {_short_err(e)}"
                )
            return "", False

        # 2) buscar transcript manual ou gerada pelos idiomas preferidos
        for lang in preferred_langs + ["pt-BR", "pt-PT", "en"]:
            try:
                tr = tl.find_manually_created_transcript([lang])
                text, blocked = _try_fetch(tr)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception:
                pass
            try:
                tr = tl.find_generated_transcript([lang])
                text, blocked = _try_fetch(tr)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception:
                pass

        # 3) traduzir a primeira disponível para pt
        for tr in all_transcripts:
            try:
                tr_pt = tr.translate("pt")
                text, blocked = _try_fetch(tr_pt)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except TranslationLanguageNotAvailable:
                logger.info(
                    f"Transcrição: tradução pt indisponível para {tr.language_code} em {video_id}"
                )
            except blocked_errors as e:
                logger.info(
                    f"Transcrição: acesso bloqueado ao traduzir {tr.language_code} para {video_id}: {_short_err(e)}"
                )
                return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception as e:
                logger.info(
                    f"Transcrição: falha ao traduzir {tr.language_code} para {video_id}: {_short_err(e)}"
                )

        # 4) fallback: primeira transcript "como está"
        for tr in all_transcripts:
            text, blocked = _try_fetch(tr)
            if text:
                return text
            if blocked:
                return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        logger.info(f"Transcrição: não encontrada para {video_id}")
        return self._fetch_transcript_ytdlp(video_id, preferred_langs)
EOF_20

mkdir -p "${TARGET_DIR}/src/app/domain/youtube"
cat <<'EOF_21' > "${TARGET_DIR}/src/app/domain/youtube/service.py"
"""Service orchestrating YouTube extractions."""

from __future__ import annotations

import html
import json
import logging
import tempfile
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Callable, Optional

from fpdf import FPDF

from app.config import get_settings
from app.domain import validators
from app.domain.entities import YouTubeExtractionConfig, YouTubeExtractionResult
from app.domain.llm_client import LLMClient, LLMResult
from app.domain.youtube.extractor_plus import YouTubeExtractor
from app.infrastructure import repositories
from app.infrastructure.logging_setup import get_log_file_path, setup_logging

LOGGER = logging.getLogger(__name__)

ASR_LANG = "pt"
FASTER_WHISPER_MODEL = "small"
FASTER_WHISPER_COMPUTE = "auto"
OPENAI_WHISPER_MODEL = "whisper-1"


class YouTubeExecutionService:
    """Orchestrates the extraction workflow."""

    def __init__(self, config: YouTubeExtractionConfig) -> None:
        self.config = config
        self.settings = get_settings()
        self.resultados_dir = config.outdir.resolve()
        self.resultados_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self, progress_callback: Optional[Callable[[str], None]] = None
    ) -> YouTubeExtractionResult:
        """Execute the extraction and return metadata about generated files."""

        channels = self._resolve_channels()
        if not channels:
            raise ValueError("Nenhum canal informado ou cadastrado.")
        self._notify(progress_callback, f"{len(channels)} canais selecionados para análise.")
        timestamp = datetime.now()
        run_id = timestamp.strftime("%Y%m%d_%H%M%S")
        log_path = get_log_file_path(f"youtube_extraction_{run_id}.log")
        setup_logging(log_file=log_path)
        logger = logging.getLogger(f"app.youtube.run.{run_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = True
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(file_handler)

        logger.info("Iniciando extração em lote de %s canais", len(channels))
        self._notify(
            progress_callback,
            "Iniciando processamento dos canais selecionados...",
        )
        extractor = self._build_extractor()
        llm_client = self._build_llm_client()
        total_videos = 0
        channel_payload: list[dict] = []
        channel_tokens: list[dict[str, int | str]] = []
        token_details: list[dict[str, int | str]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        try:
            for index, channel in enumerate(channels, start=1):
                logger.info("Processando canal %s/%s: %s", index, len(channels), channel)
                self._notify(
                    progress_callback,
                    f"Processando canal {index}/{len(channels)}: {channel}",
                )
                info = extractor.extract_channel_info(channel)
                if info.get("status") != "success":
                    logger.warning("Falha ao extrair informações do canal %s", channel)
                    channel_payload.append({
                        "channel_id": channel,
                        "status": "error",
                        "message": info.get("message", "Falha ao extrair canal."),
                        "videos": [],
                    })
                    continue
                videos = extractor.extract_recent_videos(
                    channel,
                    max_age_days=self.config.days,
                    videos_tab_only=True,
                    max_videos=self.config.max_videos,
                )
                logger.info(
                    "Canal %s extraído com sucesso. Vídeos dentro do critério: %s",
                    channel,
                    len(videos),
                )
                self._notify(
                    progress_callback,
                    f"Canal {channel} com {len(videos)} vídeo(s) dentro do critério.",
                )
                enriched_videos = []
                prompt_tokens_channel = 0
                completion_tokens_channel = 0
                for video in videos:
                    video_id = video.get("id")
                    if not video_id:
                        continue
                    details = extractor.fetch_video_details(video_id)
                    transcript = ""
                    summary: Optional[LLMResult] = None
                    if self.config.mode.lower() == "full":
                        transcript = self._obter_transcricao(video_id, extractor, logger)
                        if transcript and not self.config.no_llm:
                            summary = llm_client.summarise(
                                title=video.get("title", ""),
                                transcript=transcript,
                                channel=info.get("name") or channel,
                                max_palavras=self.config.resumo_max_palavras,
                            )
                        elif self.config.no_llm:
                            logger.info(
                                "[LLM] Execução com --no-llm habilitado; resumos serão pulados."
                            )
                    prompt_tokens = summary.prompt_tokens if summary else 0
                    completion_tokens = summary.completion_tokens if summary else 0
                    prompt_tokens_channel += prompt_tokens
                    completion_tokens_channel += completion_tokens
                    token_details.append(
                        {
                            "canal": info.get("name") or channel,
                            "video": video.get("title", ""),
                            "tokens_entrada": prompt_tokens,
                            "tokens_saida": completion_tokens,
                            "tokens_totais": prompt_tokens + completion_tokens,
                        }
                    )
                    enriched_videos.append(
                        {
                            "id": video_id,
                            "title": video.get("title"),
                            "url": video.get("url"),
                            "published": video.get("published"),
                            "published_relative": video.get("published_relative"),
                            "duration": details.get("duration_hhmmss"),
                            "date_published": details.get("date_published"),
                            "transcript_available": bool(transcript),
                            "transcript": transcript if self.config.mode.lower() == "full" else "",
                            "summary": summary.__dict__ if summary else None,
                        }
                    )
                total_videos += len(enriched_videos)
                channel_payload.append(
                    {
                        "channel_id": channel,
                        "name": info.get("name", channel),
                        "subscriber_count": info.get("subscriber_count"),
                        "description": info.get("description"),
                        "video_count": info.get("video_count"),
                        "videos": enriched_videos,
                        "status": "success",
                    }
                )
                channel_tokens.append(
                    {
                        "canal": info.get("name") or channel,
                        "tokens_entrada": prompt_tokens_channel,
                        "tokens_saida": completion_tokens_channel,
                        "tokens_totais": prompt_tokens_channel
                        + completion_tokens_channel,
                    }
                )
                total_prompt_tokens += prompt_tokens_channel
                total_completion_tokens += completion_tokens_channel
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()

        json_path, report_path = self._persist_outputs(
            run_id, channel_payload, total_videos, timestamp
        )
        self._notify(
            progress_callback,
            "Extração finalizada. Resultados disponíveis para consulta.",
        )
        repositories.record_youtube_extraction(
            channel_label=", ".join(channels[:3]) + ("..." if len(channels) > 3 else ""),
            mode=self.config.mode,
            json_path=str(json_path) if json_path else None,
            report_path=str(report_path) if report_path else None,
            log_path=str(log_path),
            total_videos=total_videos,
            total_channels=len(channel_payload),
        )
        message = (
            "Extração concluída com sucesso" if channel_payload else "Nenhum resultado gerado"
        )
        return YouTubeExtractionResult(
            json_path=json_path,
            report_path=report_path,
            log_path=log_path,
            total_videos=total_videos,
            total_channels=len(channel_payload),
            message=message,
            token_details=token_details,
            channel_tokens=channel_tokens,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
        )

    def _resolve_channels(self) -> list[str]:
        """Return the list of channels considering CLI, files and database."""

        channels: list[str] = []
        for raw in self.config.channels:
            if raw:
                channels.append(validators.normalize_channel_id(raw))
        if self.config.channels_file and self.config.channels_file.exists():
            file_channels = self._load_channels_from_file(self.config.channels_file)
            channels.extend(file_channels)
        if not channels:
            db_channels = repositories.list_youtube_channels(active_only=True)
            channels = [validators.normalize_channel_id(c["foyt_id_canal"]) for c in db_channels]
        # remove duplicados mantendo ordem
        seen = set()
        deduped = []
        for ch in channels:
            if ch not in seen:
                deduped.append(ch)
                seen.add(ch)
        return deduped

    def _load_channels_from_file(self, path: Path) -> list[str]:
        """Read a channels file in the legacy format."""

        entries: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                entries.append(validators.normalize_channel_id(line))
        except FileNotFoundError:
            LOGGER.warning("Arquivo de canais %s não encontrado.", path)
        return entries

    def _build_extractor(self) -> YouTubeExtractor:
        extractor = YouTubeExtractor(user_agent=self.config.user_agent)
        if self.config.cookies and self.config.cookies.exists():
            try:
                jar = MozillaCookieJar(str(self.config.cookies))
                jar.load(ignore_discard=True, ignore_expires=True)
                extractor.session.cookies.update(jar)
                LOGGER.info("Cookies carregados de %s", self.config.cookies)
            except Exception as exc:
                LOGGER.warning("Falha ao carregar cookies: %s", exc)
        return extractor

    def _build_llm_client(self) -> LLMClient:
        if self.config.no_llm:
            return LLMClient("none", self.settings.llm_model, None, self.settings.token_limit)
        api_key = self.config.llm_key or self.settings.llm_api_key
        model = self.config.llm_model or self.settings.llm_model
        provider = (self.config.llm_provider or self.settings.llm_provider or "").strip()
        return LLMClient(provider, model, api_key, self.settings.token_limit)

    @staticmethod
    def _notify(
        callback: Optional[Callable[[str], None]], message: str
    ) -> None:
        if callback:
            callback(message)

    def _obter_transcricao(
        self,
        video_id: str,
        extractor: YouTubeExtractor,
        logger: logging.Logger,
    ) -> str:
        text = extractor.fetch_transcript_text(video_id)
        if text:
            return text
        if not self.config.asr_enabled:
            logger.info("[ASR desativado] Sem transcrição YouTube para %s", video_id)
            return ""
        logger.info("[ASR ativado] Transcrição não encontrada; iniciando fallback para %s", video_id)
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = self._download_audio(video_id, Path(tmp_dir), logger)
            if not audio_path:
                return ""
            if self.config.asr_provider == "openai":
                return self._asr_openai(audio_path, logger)
            return self._asr_faster_whisper(audio_path, logger)

    def _download_audio(
        self, video_id: str, outdir: Path, logger: logging.Logger
    ) -> Optional[Path]:
        try:
            import yt_dlp
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("yt-dlp não disponível: %s", exc)
            return None
        outdir.mkdir(parents=True, exist_ok=True)
        options = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(outdir / f"{video_id}.%(ext)s"),
            "nocheckcertificate": True,
        }
        if self.config.cookies and self.config.cookies.exists():
            options["cookiefile"] = str(self.config.cookies.resolve())
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                if "requested_downloads" in info and info["requested_downloads"]:
                    filepath = info["requested_downloads"][0].get("filepath")
                else:
                    filepath = ydl.prepare_filename(info)
            path = Path(filepath)
            if path.exists():
                logger.info("Áudio baixado para %s", path)
                return path
        except Exception as exc:  # pragma: no cover - heavy dependency
            logger.warning("yt-dlp falhou para %s: %s", video_id, exc)
        return None

    def _asr_faster_whisper(self, path: Path, logger: logging.Logger) -> str:
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("faster-whisper indisponível: %s", exc)
            return ""
        try:
            model = WhisperModel(
                FASTER_WHISPER_MODEL,
                device="auto",
                compute_type=FASTER_WHISPER_COMPUTE,
            )
            segments, _ = model.transcribe(str(path), language=ASR_LANG, vad_filter=True)
            return " ".join([getattr(seg, "text", "") for seg in segments if getattr(seg, "text", "")])
        except Exception as exc:  # pragma: no cover - heavy dependency
            logger.warning("faster-whisper falhou: %s", exc)
            return ""

    def _asr_openai(self, path: Path, logger: logging.Logger) -> str:
        api_key = self.config.llm_key or self.settings.llm_api_key
        if not api_key:
            logger.warning("OPENAI_API_KEY não definido; ASR será pulado.")
            return ""
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("SDK OpenAI indisponível: %s", exc)
            return ""
        client = OpenAI(api_key=api_key)
        try:
            if hasattr(client, "audio") and hasattr(client.audio, "transcriptions"):
                create = getattr(client.audio.transcriptions, "create", None)
                if create:
                    with path.open("rb") as stream:
                        response = create(model=OPENAI_WHISPER_MODEL, file=stream)
                    text = getattr(response, "text", "")
                    return str(text).strip()
            if hasattr(client, "Audio") and hasattr(client.Audio, "transcribe"):
                with path.open("rb") as stream:
                    response = client.Audio.transcribe(OPENAI_WHISPER_MODEL, stream)
                return str(getattr(response, "text", "")).strip()
        except Exception as exc:  # pragma: no cover
            logger.warning("Transcrição via OpenAI falhou: %s", exc)
        return ""

    def _persist_outputs(
        self,
        run_id: str,
        channels: list[dict],
        total_videos: int,
        timestamp: datetime,
    ) -> tuple[Optional[Path], Optional[Path]]:
        metadata = {
            "executed_at": timestamp.isoformat(),
            "mode": self.config.mode,
            "total_channels": len(channels),
            "total_videos": total_videos,
            "params": {
                "days": self.config.days,
                "max_videos": self.config.max_videos,
                "mode": self.config.mode,
                "no_llm": self.config.no_llm,
                "asr_provider": self.config.asr_provider,
                "format": self.config.report_format,
            },
            "channels": channels,
        }
        json_path = self.resultados_dir / f"{self.config.prefix}_{run_id}.json"
        json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path = self._build_report(run_id, metadata)
        return json_path, report_path

    def _build_report(self, run_id: str, metadata: dict) -> Optional[Path]:
        formato = self.config.report_format.lower()
        texto = self._report_text(metadata)
        if formato == "txt":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.txt"
            path.write_text(texto, encoding="utf-8")
            return path
        if formato == "html":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.html"
            html_content = f"<html><body><pre>{html.escape(texto)}</pre></body></html>"
            path.write_text(html_content, encoding="utf-8")
            return path
        if formato == "pdf":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.pdf"
            self._save_pdf(texto, path)
            return path
        if formato == "json":
            return None
        # fallback para txt
        path = self.resultados_dir / f"{self.config.prefix}_{run_id}.txt"
        path.write_text(texto, encoding="utf-8")
        return path

    def _report_text(self, metadata: dict) -> str:
        lines = []
        lines.append("=======================================================================")
        lines.append("📊 RESUMO DA EXTRAÇÃO")
        lines.append("=======================================================================\n")
        lines.append(f"Canais processados: {metadata['total_channels']}")
        lines.append(f"Total de vídeos extraídos: {metadata['total_videos']}")
        lines.append(f"Modo: {metadata['params']['mode']}")
        lines.append(
            f"Parâmetros: dias={metadata['params']['days']}, max_videos={metadata['params']['max_videos']},"
            f" formato={metadata['params']['format']}"
        )
        lines.append("")
        for channel in metadata.get("channels", []):
            lines.append(f"✅ {channel.get('name')} ({channel.get('channel_id')})")
            videos = channel.get("videos", [])
            lines.append(f"    Vídeos extraídos: {len(videos)}")
            for video in videos:
                lines.append(
                    f"    - {video.get('title')} — {video.get('duration') or 'N/A'} — {video.get('url')}"
                )
                summary = video.get("summary")
                if summary:
                    lines.append(f"      Resumo: {summary.get('resumo_uma_frase', '')}")
        lines.append("\n=======================================================================")
        lines.append("✨ Extração concluída!")
        return "\n".join(lines)

    def _save_pdf(self, texto: str, path: Path) -> None:
        pdf = FPDF()
        pdf.add_page()
        try:
            pdf.set_font("Helvetica", size=12)
        except Exception:  # pragma: no cover - fallback for environments without Helvetica
            pdf.set_font("Arial", size=12)
        max_width = pdf.w - pdf.l_margin - pdf.r_margin
        for line in texto.splitlines():
            if not line.strip():
                pdf.ln(8)
                continue
            chunk = line
            while chunk:
                span = len(chunk)
                while span > 0 and pdf.get_string_width(chunk[:span]) > max_width:
                    span -= 1
                pdf.cell(0, 6, txt=chunk[:span], ln=1)
                chunk = chunk[span:]
        pdf.output(str(path))
EOF_21

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_22' > "${TARGET_DIR}/src/app/infrastructure/__init__.py"

EOF_22

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_23' > "${TARGET_DIR}/src/app/infrastructure/backup.py"
"""Backup utilities for the SQLite database."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from app.config import get_settings

LOGGER = logging.getLogger(__name__)


def create_backup() -> Path:
    """Create a timestamped copy of the database file."""

    settings = get_settings()
    db_path = settings.db_path
    if not db_path.exists():
        msg = (
            "Banco de dados não encontrado. Inicialize o banco antes de executar o backup."
        )
        LOGGER.error(msg)
        raise FileNotFoundError(msg)
    backup_dir = settings.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"info_ai_studio_{timestamp}.db"
    shutil.copy(db_path, backup_path)
    LOGGER.info("Backup gerado em %s", backup_path)
    return backup_path
EOF_23

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_24' > "${TARGET_DIR}/src/app/infrastructure/db.py"
"""SQLite helpers for the application."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence

from app.config import get_settings


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Return a context manager for sqlite3 connections."""

    settings = get_settings()
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(schema_path: Path | None = None) -> None:
    """Create database tables if they do not exist."""

    settings = get_settings()
    schema_file = schema_path or Path(__file__).with_name("schema.sql")
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    sql = schema_file.read_text(encoding="utf-8")
    with get_connection(settings.db_path) as conn:
        conn.executescript(sql)


def is_database_initialized() -> bool:
    """Check if the base tables exist."""

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("modelo_llm",),
            )
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def execute(query: str, params: Sequence[Any] | None = None) -> None:
    """Execute a write query."""

    with get_connection() as conn:
        conn.execute(query, params or [])


def executemany(query: str, params: Iterable[Sequence[Any]]) -> None:
    """Execute a write query for multiple parameter sets."""

    with get_connection() as conn:
        conn.executemany(query, list(params))


def fetch_all(query: str, params: Sequence[Any] | None = None) -> list[sqlite3.Row]:
    """Return all rows for a query."""

    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchall()


def fetch_one(query: str, params: Sequence[Any] | None = None) -> sqlite3.Row | None:
    """Return a single row for a query."""

    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchone()
EOF_24

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_25' > "${TARGET_DIR}/src/app/infrastructure/env_manager.py"
"""Utilities to manage values inside the .env file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def update_env_values(values: Mapping[str, str], env_path: Path | None = None) -> Path:
    """Persist values to a .env file, preserving existing comments and keys."""

    path = env_path or Path(".env")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    updated: list[str] = []
    handled: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in values:
            value = values[key]
            updated.append(f"{key}={value}")
            handled.add(key)
            os.environ[key] = value
        else:
            updated.append(line)

    for key, value in values.items():
        if key in handled:
            continue
        updated.append(f"{key}={value}")
        os.environ[key] = value

    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return path
EOF_25

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_26' > "${TARGET_DIR}/src/app/infrastructure/logging_setup.py"
"""Central logging configuration for the application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings

FULL_LOG_LEVEL = 15
logging.addLevelName(FULL_LOG_LEVEL, "FULL")


def _log_full(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(FULL_LOG_LEVEL):
        self._log(FULL_LOG_LEVEL, message, args, **kwargs)


if not hasattr(logging.Logger, "full"):
    logging.Logger.full = _log_full  # type: ignore[attr-defined]


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """Configure root logging with console and optional file handler."""

    logger = logging.getLogger()
    if not logger.handlers:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        console = logging.StreamHandler()
        console.setLevel(numeric_level)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        logger.addHandler(console)
    if log_file is not None:
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file):
                break
        else:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            )
            logger.addHandler(file_handler)
    return logger


def get_log_file_path(filename: str) -> Path:
    """Return a path inside the configured log directory."""

    settings = get_settings()
    return settings.log_dir / filename
EOF_26

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_27' > "${TARGET_DIR}/src/app/infrastructure/repositories.py"
"""Database repositories for domain entities."""

from __future__ import annotations

from typing import Any, Iterable

from app.infrastructure import db


def save_llm_model(provedor: str, modelo: str, api_key: str, status: int = 1) -> None:
    """Insert or update a registered LLM model."""

    query = (
        "INSERT INTO modelo_llm (modl_provedor, modl_modelo_llm, modl_api_key, modl_status)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT(modl_provedor, modl_modelo_llm) DO UPDATE SET"
        " modl_api_key = excluded.modl_api_key,"
        " modl_status = excluded.modl_status"
    )
    db.execute(query, (provedor.strip(), modelo.strip(), api_key.strip(), status))


def list_llm_models() -> list[dict[str, Any]]:
    """Return registered LLM models."""

    rows = db.fetch_all(
        "SELECT modl_id, modl_provedor, modl_modelo_llm, modl_api_key, modl_status, modl_created_at"
        " FROM modelo_llm ORDER BY modl_created_at DESC"
    )
    return [dict(row) for row in rows]


def save_youtube_channel(
    nome_canal: str,
    descricao: str,
    grupo: str,
    canal_id: str,
    status: int = 1,
) -> None:
    """Insert or update a YouTube channel entry."""

    query = (
        "INSERT INTO fonte_youtube (foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal, foyt_status)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(foyt_id_canal) DO UPDATE SET"
        " foyt_nome_canal = excluded.foyt_nome_canal,"
        " foyt_descricao = excluded.foyt_descricao,"
        " foyt_grupo_canal = excluded.foyt_grupo_canal,"
        " foyt_status = excluded.foyt_status"
    )
    db.execute(query, (nome_canal.strip(), descricao.strip(), grupo.strip(), canal_id.strip(), status))


def list_youtube_channels(active_only: bool = True) -> list[dict[str, Any]]:
    """Return registered YouTube channels."""

    query = (
        "SELECT foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal,"
        " foyt_status, foyt_created_at"
        " FROM fonte_youtube"
    )
    params: Iterable[Any] = ()
    if active_only:
        query += " WHERE foyt_status = 1"
    query += " ORDER BY foyt_nome_canal ASC"
    rows = db.fetch_all(query, params)
    return [dict(row) for row in rows]


def get_youtube_channel_by_id(channel_id: str) -> dict[str, Any] | None:
    """Return channel data by the stored channel id."""

    row = db.fetch_one(
        "SELECT foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal,"
        " foyt_status FROM fonte_youtube WHERE foyt_id_canal = ?",
        (channel_id,),
    )
    return dict(row) if row else None


def save_web_source(
    tipo: str,
    fonte: str,
    descricao: str,
    status: int = 1,
) -> None:
    """Insert a new web source."""

    query = (
        "INSERT INTO fonte_web (fowe_tipo, fowe_fonte, fowe_descricao, fowe_status)"
        " VALUES (?, ?, ?, ?)"
    )
    db.execute(query, (tipo.strip(), fonte.strip(), descricao.strip(), status))


def list_web_sources(active_only: bool = True) -> list[dict[str, Any]]:
    """Return registered web sources."""

    query = (
        "SELECT fowe_id, fowe_tipo, fowe_fonte, fowe_descricao, fowe_status, fowe_created_at"
        " FROM fonte_web"
    )
    if active_only:
        query += " WHERE fowe_status = 1"
    query += " ORDER BY fowe_created_at DESC"
    rows = db.fetch_all(query)
    return [dict(row) for row in rows]


def record_youtube_extraction(
    channel_label: str,
    mode: str,
    json_path: str | None,
    report_path: str | None,
    log_path: str | None,
    total_videos: int,
    total_channels: int,
) -> None:
    """Persist metadata for a YouTube extraction run."""

    query = (
        "INSERT INTO youtube_extraction (ytex_channel, ytex_mode, ytex_json_path, ytex_report_path,"
        " ytex_log_path, ytex_total_videos, ytex_total_channels)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    db.execute(
        query,
        (
            channel_label,
            mode,
            json_path,
            report_path,
            log_path,
            total_videos,
            total_channels,
        ),
    )


def list_youtube_extractions(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent extraction runs."""

    rows = db.fetch_all(
        "SELECT ytex_id, ytex_channel, ytex_mode, ytex_created_at, ytex_json_path, ytex_report_path,"
        " ytex_log_path, ytex_total_videos, ytex_total_channels"
        " FROM youtube_extraction ORDER BY ytex_created_at DESC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in rows]
EOF_27

mkdir -p "${TARGET_DIR}/src/app/infrastructure"
cat <<'EOF_28' > "${TARGET_DIR}/src/app/infrastructure/schema.sql"
-- Schema for Info_AI_Studio

CREATE TABLE IF NOT EXISTS modelo_llm (
    modl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    modl_provedor TEXT NOT NULL,
    modl_modelo_llm TEXT NOT NULL,
    modl_api_key TEXT NOT NULL,
    modl_status INTEGER NOT NULL DEFAULT 1,
    modl_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fonte_web (
    fowe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fowe_tipo TEXT NOT NULL DEFAULT 'site',
    fowe_fonte TEXT NOT NULL,
    fowe_descricao TEXT NOT NULL,
    fowe_status INTEGER NOT NULL DEFAULT 1,
    fowe_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fonte_youtube (
    foyt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    foyt_nome_canal TEXT NOT NULL,
    foyt_descricao TEXT NOT NULL,
    foyt_grupo_canal TEXT NOT NULL,
    foyt_id_canal TEXT NOT NULL,
    foyt_status INTEGER NOT NULL DEFAULT 1,
    foyt_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_llm_unique ON modelo_llm (modl_provedor, modl_modelo_llm);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fonte_youtube_canal ON fonte_youtube (foyt_id_canal);

CREATE TABLE IF NOT EXISTS youtube_extraction (
    ytex_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ytex_channel TEXT NOT NULL,
    ytex_mode TEXT NOT NULL,
    ytex_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ytex_json_path TEXT,
    ytex_report_path TEXT,
    ytex_log_path TEXT,
    ytex_total_videos INTEGER NOT NULL DEFAULT 0,
    ytex_total_channels INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_youtube_extraction_created_at ON youtube_extraction (ytex_created_at DESC);
EOF_28

mkdir -p "${TARGET_DIR}/src/app/interfaces"
cat <<'EOF_29' > "${TARGET_DIR}/src/app/interfaces/__init__.py"

EOF_29

mkdir -p "${TARGET_DIR}/src/app/interfaces/cli"
cat <<'EOF_30' > "${TARGET_DIR}/src/app/interfaces/cli/__init__.py"

EOF_30

mkdir -p "${TARGET_DIR}/src/app/interfaces/cli/commands"
cat <<'EOF_31' > "${TARGET_DIR}/src/app/interfaces/cli/commands/__init__.py"

EOF_31

mkdir -p "${TARGET_DIR}/src/app/interfaces/cli"
cat <<'EOF_32' > "${TARGET_DIR}/src/app/interfaces/cli/main.py"
"""Typer CLI for Info_AI_Studio."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from app.config import get_settings
from app.domain.entities import LLMModel, YouTubeExtractionConfig
from app.domain.llm_service import register_llm_model
from app.domain.youtube.service import YouTubeExecutionService
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized
from app.infrastructure.logging_setup import setup_logging

app = typer.Typer(help="CLI principal do Info_AI_Studio")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


@app.callback()
def cli_callback() -> None:
    """Inicializa logging padrão para todos os comandos."""

    setup_logging()


@app.command("db-init")
def db_init() -> None:
    """Inicializa o banco de dados executando o schema.sql."""

    initialize_database()
    typer.echo("Banco inicializado com sucesso.")


@app.command("db-backup")
def db_backup() -> None:
    """Gera um backup do banco SQLite na pasta configurada."""

    path = create_backup()
    typer.echo(f"Backup gerado em: {path}")


@app.command("modelo-ia")
def modelo_ia(
    provedor: str = typer.Option(..., "--provedor", help="Nome do provedor do modelo."),
    modelo: str = typer.Option(..., "--modelo", help="Nome do modelo LLM."),
    api_key: str = typer.Option(..., "--api-key", help="Chave de API para acesso ao modelo."),
    ativo: bool = typer.Option(True, "--ativo/--inativo", help="Define se o modelo está ativo."),
) -> None:
    """Cadastra ou atualiza um modelo LLM."""

    register_llm_model(LLMModel(provedor=provedor, modelo=modelo, api_key=api_key, status=ativo))
    typer.echo(f"Modelo {provedor}/{modelo} cadastrado com sucesso.")


@app.command("youtube-exec")
def youtube_exec(
    outdir: Optional[Path] = typer.Option(None, "--outdir", help="Diretório de saída."),
    prefix: str = typer.Option("youtube_extraction", "--prefix", help="Prefixo dos arquivos."),
    days: Optional[int] = typer.Option(3, "-d", "--days", help="Janela de dias para filtrar vídeos."),
    channels_file: Optional[Path] = typer.Option(
        None, "--channels-file", help="Arquivo com lista de canais (um por linha)."
    ),
    channel: List[str] = typer.Option(
        [], "-c", "--channel", help="Canal individual para análise (pode repetir)."
    ),
    no_asr: bool = typer.Option(False, "--no-asr", help="Desabilita o fallback de ASR."),
    asr_provider: str = typer.Option(
        "faster-whisper",
        "--asr-provider",
        help="Fornecedor de ASR para fallback.",
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Modelo LLM para análises."),
    openai_key: Optional[str] = typer.Option(None, "--openai-key", help="Sobrescreve a chave da API."),
    resumo_max_palavras: Optional[int] = typer.Option(
        None, "--resumo-max-palavras", help="Limite de palavras para o resumo."),
    mode: str = typer.Option(
        "full", "-m", "--mode", help="Modo de execução (full ou simple)."
    ),
    no_llm: bool = typer.Option(False, "--no-llm", help="Ignora análises via LLM."),
    cookies: Optional[Path] = typer.Option(
        None, "--cookies", help="Arquivo de cookies no formato Netscape."
    ),
    user_agent: str = typer.Option(DEFAULT_USER_AGENT, "--user-agent", help="User-Agent usado nas requisições."),
    report_format: str = typer.Option(
        "txt", "--format", help="Formato do relatório (txt, json, pdf, html)."
    ),
    max_videos: Optional[int] = typer.Option(
        None, "--max-videos", help="Limita a quantidade de vídeos por canal."
    ),
) -> None:
    """Executa a extração de canais do YouTube."""

    settings = get_settings()
    output_dir = (outdir or settings.resultados_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    mode_normalized = mode.lower()
    if mode_normalized not in {"full", "simple"}:
        typer.echo("Modo inválido. Use 'full' ou 'simple'.")
        raise typer.Exit(code=1)
    provider_normalized = asr_provider.lower()
    if provider_normalized not in {"faster-whisper", "openai"}:
        typer.echo("Fornecedor de ASR inválido. Use 'faster-whisper' ou 'openai'.")
        raise typer.Exit(code=1)
    report_format_normalized = report_format.lower()
    if report_format_normalized not in {"txt", "json", "pdf", "html"}:
        typer.echo("Formato inválido. Use txt, json, pdf ou html.")
        raise typer.Exit(code=1)
    config = YouTubeExtractionConfig(
        outdir=output_dir,
        prefix=prefix,
        days=days,
        channels=channel,
        channels_file=channels_file,
        mode=mode_normalized,
        no_llm=no_llm,
        asr_enabled=not no_asr,
        asr_provider=provider_normalized,
        llm_provider=settings.llm_provider,
        llm_model=model or settings.llm_model,
        llm_key=openai_key,
        resumo_max_palavras=resumo_max_palavras or settings.max_palavras_resumo,
        cookies=cookies or settings.cookies_path,
        user_agent=user_agent,
        report_format=report_format_normalized,
        max_videos=max_videos,
    )
    if not is_database_initialized():
        typer.echo("Banco de dados não inicializado. Execute 'app db-init' antes de prosseguir.")
        raise typer.Exit(code=1)
    service = YouTubeExecutionService(config)
    result = service.run()
    typer.echo("Extração concluída.")
    typer.echo(f"JSON: {result.json_path}")
    if result.report_path:
        typer.echo(f"Relatório: {result.report_path}")
    typer.echo(f"Log: {result.log_path}")
    typer.echo(
        f"Totais — canais: {result.total_channels}, vídeos: {result.total_videos}."
    )
    total_tokens = result.total_prompt_tokens + result.total_completion_tokens
    if total_tokens:
        typer.echo(
            "Tokens — entrada: "
            f"{result.total_prompt_tokens}, saída: {result.total_completion_tokens}, total: {total_tokens}."
        )


if __name__ == "__main__":
    app()
EOF_32

mkdir -p "${TARGET_DIR}/src/app/interfaces/web"
cat <<'EOF_33' > "${TARGET_DIR}/src/app/interfaces/web/__init__.py"

EOF_33

mkdir -p "${TARGET_DIR}/src/app/interfaces/web"
cat <<'EOF_34' > "${TARGET_DIR}/src/app/interfaces/web/main.py"
"""Streamlit entrypoint for Info_AI_Studio."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.infrastructure.db import is_database_initialized


def render_home() -> None:
    """Renderiza a página inicial com status gerais."""

    settings = get_settings()
    st.title("Info_AI_Studio")
    st.caption("Coleta e análise de informações em múltiplas fontes")

    db_status = "Conectado" if is_database_initialized() else "Não inicializado"
    llm_status = "Configurada" if settings.llm_api_key else "Não configurada"

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Status do banco de dados", db_status)
        st.page_link("pages/3_Configurações.py", label="Ir para Configurações", icon="⚙️")
    with col2:
        st.metric("Status da LLM", llm_status)
        st.page_link("pages/2_Cadastros.py", label="Ir para Cadastros", icon="🗂️")

    st.divider()
    st.subheader("Ações rápidas")
    st.write("Utilize o menu lateral para navegar entre as páginas da aplicação.")
    st.page_link("pages/4_Execução.py", label="Executar pesquisas", icon="🚀")


def main() -> None:
    """Configura navegação multipage usando st.navigation."""

    st.set_page_config(page_title="Info_AI_Studio", layout="wide")

    navigation = st.navigation(
        {
            "Principal": [st.Page(render_home, title="Home", icon="🏠")],
            "Aplicação": [
                st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
                st.Page("pages/2_Cadastros.py", title="Cadastros", icon="🗂️"),
                st.Page("pages/3_Configurações.py", title="Configurações", icon="⚙️"),
                st.Page("pages/4_Execução.py", title="Execução", icon="🚀"),
                st.Page("pages/5_Logs.py", title="Logs", icon="📝"),
            ],
        }
    )
    navigation.run()


if __name__ == "__main__":
    main()
EOF_34

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_35' > "${TARGET_DIR}/src/app/interfaces/web/pages/1_Dashboard.py"
"""Dashboard da aplicação com indicadores básicos."""

from __future__ import annotations

import streamlit as st

from app.domain.fonte_service import list_web_sources, list_youtube_channels
from app.domain.llm_service import list_llm_models
from app.infrastructure import repositories

st.title("Dashboard")

llm_models = list_llm_models()
youtube_channels = list_youtube_channels()
web_sources = list_web_sources()
extractions = repositories.list_youtube_extractions(limit=5)

col1, col2, col3 = st.columns(3)
col1.metric("Modelos LLM", len(llm_models))
col2.metric("Canais YouTube", len(youtube_channels))
col3.metric("Fontes Web", len(web_sources))

st.subheader("Últimas execuções do YouTube")
if extractions:
    st.table(extractions)
else:
    st.info("Nenhuma execução registrada até o momento.")

st.subheader("Progresso geral")
st.write(
    "Esta área exibirá relatórios agregados de tokens, custos e utilização assim que as execuções forem realizadas."
)
EOF_35

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_36' > "${TARGET_DIR}/src/app/interfaces/web/pages/2_Cadastros.py"
"""Página de cadastros (LLM, canais e fontes)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.domain.entities import LLMModel, WebSource, YouTubeChannel
from app.domain.fonte_service import (
    list_web_sources,
    list_youtube_channels,
    register_web_source,
    register_youtube_channel,
)
from app.domain.llm_service import (
    LLMConnectionError,
    compute_api_key_env_name,
    delete_llm_model,
    list_llm_models,
    register_llm_model,
    test_llm_connection,
)


def _ensure_llm_state() -> None:
    defaults = {
        "llm_form_provedor": "",
        "llm_form_modelo": "",
        "llm_form_api_key": "",
        "llm_form_status": True,
        "llm_form_model_id": None,
        "llm_test_feedback": None,
        "llm_flash": None,
        "llm_delete_pending": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_llm_form() -> None:
    st.session_state.llm_form_model_id = None
    st.session_state.llm_form_provedor = ""
    st.session_state.llm_form_modelo = ""
    st.session_state.llm_form_api_key = ""
    st.session_state.llm_form_status = True


def _populate_llm_form(row: dict[str, Any]) -> None:
    st.session_state.llm_form_model_id = row["id"]
    st.session_state.llm_form_provedor = row["provedor"]
    st.session_state.llm_form_modelo = row["modelo"]
    st.session_state.llm_form_api_key = row["api_key"]
    st.session_state.llm_form_status = row["status"]


def _status_badge(is_active: bool) -> str:
    cor = "green" if is_active else "red"
    texto = "Ativo" if is_active else "Inativo"
    return f"<span style='color:{cor}; font-weight:bold;'>●</span> {texto}"


def _record_test_feedback(success: bool, message: str, env_var: str) -> None:
    st.session_state.llm_test_feedback = {
        "type": "success" if success else "error",
        "message": message,
        "env_var": env_var,
    }

st.title("Cadastros")

_ensure_llm_state()

st.subheader("Modelos LLM")

flash_message = st.session_state.llm_flash
if flash_message:
    level, message = flash_message
    if level == "success":
        st.success(message)
    else:
        st.error(message)
    st.session_state.llm_flash = None

pending_delete = st.session_state.llm_delete_pending
if pending_delete is not None:
    with st.container():
        st.warning(
            "Confirma excluir o modelo "
            f"{pending_delete['provedor']} / {pending_delete['modelo']}?"
        )
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("Excluir", type="primary", key="confirm_delete_llm"):
            delete_llm_model(pending_delete["id"])
            st.session_state.llm_flash = (
                "success",
                f"Modelo {pending_delete['provedor']} / {pending_delete['modelo']} removido.",
            )
            if st.session_state.llm_form_model_id == pending_delete["id"]:
                _reset_llm_form()
            st.session_state.llm_delete_pending = None
            st.rerun()
        if cancel_col.button("Cancelar", key="cancel_delete_llm"):
            st.session_state.llm_delete_pending = None
            st.rerun()

with st.form("llm_form"):
    col1, col2 = st.columns(2)
    with col1:
        provedor = st.text_input("Provedor", key="llm_form_provedor", placeholder="OPENAI")
        modelo = st.text_input("Modelo", key="llm_form_modelo", placeholder="gpt-5-nano")
    with col2:
        api_key = st.text_input("API Key", key="llm_form_api_key", type="password")
        ativo = st.checkbox("Ativo", key="llm_form_status")
    if provedor:
        st.caption(
            f"Variável de ambiente: {compute_api_key_env_name(provedor)}"
        )
    col_save, col_test = st.columns(2)
    with col_save:
        salvar = st.form_submit_button("Salvar modelo", type="primary")
    with col_test:
        testar = st.form_submit_button("Testar conexão", type="secondary")

    model_id = st.session_state.llm_form_model_id
    if salvar:
        if not provedor or not modelo or not api_key:
            st.session_state.llm_flash = (
                "error",
                "Informe provedor, modelo e API key para salvar.",
            )
        else:
            try:
                register_llm_model(
                    LLMModel(
                        provedor=provedor,
                        modelo=modelo,
                        api_key=api_key,
                        status=ativo,
                        model_id=model_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - depende do provedor
                st.session_state.llm_flash = ("error", str(exc))
            else:
                st.session_state.llm_flash = (
                    "success",
                    f"Modelo {provedor}/{modelo} salvo com sucesso.",
                )
                _reset_llm_form()
        st.rerun()
    if testar:
        if not provedor or not modelo or not api_key:
            _record_test_feedback(
                False,
                "Informe provedor, modelo e API key para testar a conexão.",
                compute_api_key_env_name(provedor),
            )
        else:
            try:
                resultado = test_llm_connection(
                    LLMModel(
                        provedor=provedor,
                        modelo=modelo,
                        api_key=api_key,
                        status=ativo,
                        model_id=model_id,
                    )
                )
            except LLMConnectionError as err:
                _record_test_feedback(False, err.message, err.env_var)
            except Exception as exc:  # pragma: no cover - depende do provedor
                _record_test_feedback(
                    False,
                    str(exc),
                    compute_api_key_env_name(provedor),
                )
            else:
                _record_test_feedback(True, resultado.mensagem, resultado.variavel_ambiente)
        st.rerun()

if st.session_state.llm_form_model_id is not None:
    st.info(
        "Editando modelo ID "
        f"{st.session_state.llm_form_model_id}."
    )
    if st.button("Cancelar edição", key="cancel_llm_edit"):
        _reset_llm_form()
        st.rerun()

feedback = st.session_state.llm_test_feedback
if feedback:
    texto = feedback["message"]
    if feedback.get("env_var"):
        texto = f"{texto} (variável {feedback['env_var']})"
    if feedback["type"] == "success":
        st.success(texto)
    else:
        st.error(texto)

llm_models = list_llm_models()
if not llm_models:
    st.info("Nenhum modelo cadastrado ainda.")
else:
    header_cols = st.columns([2, 2, 3, 1, 2, 2])
    header_cols[0].markdown("**Provedor**")
    header_cols[1].markdown("**Modelo**")
    header_cols[2].markdown("**API Key**")
    header_cols[3].markdown("**Status**")
    header_cols[4].markdown("**Data de criação**")
    header_cols[5].markdown("**Ações**")
    for row in llm_models:
        row_cols = st.columns([2, 2, 3, 1, 2, 2])
        row_cols[0].markdown(row["provedor"])
        row_cols[1].markdown(row["modelo"])
        row_cols[2].markdown(f"`{row['api_key']}`")
        row_cols[3].markdown(_status_badge(row["status"]), unsafe_allow_html=True)
        row_cols[4].markdown(row["created_at"])
        action_cols = row_cols[5].columns(3)
        if action_cols[0].button("✏️", key=f"llm_edit_{row['id']}", help="Editar modelo"):
            _populate_llm_form(row)
            st.session_state.llm_delete_pending = None
            st.rerun()
        if action_cols[1].button("🧪", key=f"llm_test_{row['id']}", help="Testar modelo"):
            try:
                resultado = test_llm_connection(
                    LLMModel(
                        provedor=row["provedor"],
                        modelo=row["modelo"],
                        api_key=row["api_key"],
                        status=row["status"],
                        model_id=row["id"],
                    )
                )
            except LLMConnectionError as err:
                _record_test_feedback(False, err.message, err.env_var)
            except Exception as exc:  # pragma: no cover - depende do provedor
                _record_test_feedback(False, str(exc), row.get("env_var", ""))
            else:
                _record_test_feedback(True, resultado.mensagem, resultado.variavel_ambiente)
            st.rerun()
        if action_cols[2].button("🗑️", key=f"llm_delete_{row['id']}", help="Excluir modelo"):
            st.session_state.llm_delete_pending = row
            st.rerun()

st.divider()

st.subheader("Canais do YouTube")
with st.form("youtube_form"):
    nome = st.text_input("Nome do canal")
    descricao = st.text_area("Descrição")
    grupo = st.text_input("Grupo do canal")
    canal_id = st.text_input("ID do canal", placeholder="@exemplo")
    ativo_canal = st.checkbox("Ativo", value=True)
    submit_channel = st.form_submit_button("Salvar canal")
    if submit_channel:
        if not nome or not descricao or not grupo or not canal_id:
            st.error("Todos os campos são obrigatórios.")
        else:
            register_youtube_channel(
                YouTubeChannel(
                    nome=nome,
                    descricao=descricao,
                    grupo=grupo,
                    canal_id=canal_id,
                    status=ativo_canal,
                )
            )
            st.success("Canal salvo com sucesso.")
            st.rerun()

st.table(list_youtube_channels(active_only=False))

st.divider()

st.subheader("Fontes Web")
with st.form("web_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        tipo = st.selectbox("Tipo", options=["site", "blog", "youtube"])
        status = st.checkbox("Ativo", value=True)
    with col_b:
        fonte = st.text_input("Fonte", placeholder="https://exemplo.com")
    descricao_fonte = st.text_area("Descrição")
    submit_web = st.form_submit_button("Salvar fonte")
    if submit_web:
        if not fonte or not descricao_fonte:
            st.error("Fonte e descrição são obrigatórias.")
        else:
            try:
                register_web_source(
                    WebSource(tipo=tipo, fonte=fonte, descricao=descricao_fonte, status=status)
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Fonte registrada com sucesso.")
                st.rerun()

st.table(list_web_sources(active_only=False))

EOF_36

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_37' > "${TARGET_DIR}/src/app/interfaces/web/pages/3_Configurações.py"
"""Página de configurações gerais (parâmetros, banco e backup)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Optional

import streamlit as st

from app.config import get_settings, reload_settings
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized
from app.infrastructure.env_manager import update_env_values

_domain_update_parameters: Optional[Callable[[Mapping[str, str]], object]]
_domain_import_error: Optional[Exception]
try:  # pragma: no cover - defensive fallback for partially installed packages
    from app.domain.parameters_service import update_parameters as _domain_update_parameters
except Exception as exc:  # pragma: no cover - catch any import-time failure
    _domain_update_parameters = None
    _domain_import_error = exc
else:
    _domain_import_error = None


def _persist_parameters(values: Mapping[str, str]) -> None:
    """Persist parameters via the domain service or fallback directly to .env."""

    if _domain_update_parameters is not None:
        _domain_update_parameters(values)
        return

    update_env_values(values)
    reload_settings()
    st.info("Parâmetros atualizados usando fallback direto no arquivo .env.")


st.title("Configurações")
settings = get_settings()

if _domain_update_parameters is None:
    message = "Serviço de parâmetros indisponível; utilizando fallback direto no arquivo .env."
    if _domain_import_error is not None:
        message += f" (motivo: {type(_domain_import_error).__name__}: {_domain_import_error})"
    st.warning(message)

st.subheader("Parâmetros da aplicação")
with st.form("params_form"):
    max_palavras = st.number_input(
        "Máximo de palavras para resumos", min_value=50, max_value=1000, value=settings.max_palavras_resumo
    )
    submitted = st.form_submit_button("Salvar parâmetros")
    if submitted:
        _persist_parameters({"MAX_PALAVRAS_RESUMO": str(int(max_palavras))})
        st.success("Parâmetros atualizados.")
        st.rerun()

st.divider()

st.subheader("Banco de dados")
col_a, col_b = st.columns(2)
with col_a:
    st.metric("Status", "Conectado" if is_database_initialized() else "Não inicializado")
with col_b:
    if st.button("Inicializar banco", use_container_width=True):
        initialize_database()
        st.success("Banco inicializado com sucesso.")
        st.rerun()

st.divider()

st.subheader("Backup do banco")
if st.button("Gerar backup", icon="💾"):
    try:
        backup_path = create_backup()
    except FileNotFoundError as exc:
        st.error(str(exc))
    else:
        st.success(f"Backup gerado em {backup_path}")
EOF_37

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_38' > "${TARGET_DIR}/src/app/interfaces/web/pages/4_Execução.py"
"""Página de execução das pesquisas."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.domain.entities import YouTubeExtractionConfig
from app.domain.fonte_service import list_youtube_channels
from app.domain.llm_service import list_llm_models
from app.domain.youtube.service import YouTubeExecutionService
from app.infrastructure.db import is_database_initialized

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

st.title("Execução")

st.subheader("Pesquisa Fontes WEB")
st.info(
    "Funcionalidade em desenvolvimento. Aqui serão executadas buscas em sites e blogs registrados."
)
if st.button("Iniciar placeholder", icon="🛠️"):
    st.toast("Execução simulada concluída.")

st.divider()

st.subheader("Pesquisa YouTube")
if not is_database_initialized():
    st.error("Banco de dados não inicializado. Vá até Configurações e execute 'Inicializar banco'.")
else:
    settings = get_settings()
    channels_data = list_youtube_channels(active_only=True)
    options = {
        f"{item['foyt_nome_canal']} ({item['foyt_id_canal']})": item["foyt_id_canal"]
        for item in channels_data
    }
    llm_models = [model for model in list_llm_models() if model["status"]]
    llm_options = {
        f"{model['provedor']} - {model['modelo']}": model for model in llm_models
    }
    if not llm_options:
        st.warning(
            "Nenhum modelo LLM ativo encontrado. Cadastre um modelo antes de executar a pesquisa."
        )
    with st.form("youtube_exec_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected = st.multiselect("Canais cadastrados", options=list(options.keys()))
            manual_entries = st.text_area("Canais adicionais (um por linha)")
            days = st.number_input("Dias para filtrar", min_value=0, max_value=30, value=3)
            max_videos = st.number_input("Limite de vídeos por canal", min_value=0, max_value=200, value=0)
        with col2:
            prefix = st.text_input("Prefixo dos arquivos", value="youtube_extraction")
            report_format = st.selectbox("Formato do relatório", options=["txt", "json", "pdf", "html"], index=0)
            asr_provider = st.selectbox("Fornecedor de ASR", options=["faster-whisper", "openai"])
            no_asr = st.checkbox("Desativar ASR", value=False)
            llm_label = st.selectbox(
                "Modelo LLM",
                options=list(llm_options.keys()),
                disabled=not llm_options,
            )
            resumo_max = st.number_input(
                "Máximo de palavras no resumo", min_value=50, max_value=1000, value=settings.max_palavras_resumo
            )
            user_agent = st.text_input("User-Agent", value=DEFAULT_USER_AGENT)
        col_run1, col_run2 = st.columns(2)
        disabled_buttons = not llm_options
        run_simple = col_run1.form_submit_button(
            "Executar modo simple", use_container_width=True, disabled=disabled_buttons
        )
        run_full = col_run2.form_submit_button(
            "Executar modo full", use_container_width=True, disabled=disabled_buttons
        )
    progress_container = st.container()
    results_container = st.container()
    if run_simple or run_full:
        mode = "simple" if run_simple else "full"
        channels: list[str] = [options[label] for label in selected]
        if manual_entries:
            channels.extend([line.strip() for line in manual_entries.splitlines() if line.strip()])
        if not selected:
            st.error("Selecione ao menos um canal cadastrado para executar a pesquisa.")
            st.stop()
        if not channels:
            st.error("Nenhum canal válido informado.")
            st.stop()
        if not llm_label:
            st.error("Selecione um modelo LLM para continuar.")
            st.stop()
        selected_model = llm_options.get(llm_label)
        if not selected_model or not selected_model.get("api_key"):
            st.error("O modelo LLM selecionado não possui uma chave de API válida.")
            st.stop()
        progress_messages: list[str] = []
        progress_placeholder = progress_container.empty()

        def update_progress(message: str) -> None:
            progress_messages.append(message)
            formatted = "\n".join(f"- {msg}" for msg in progress_messages)
            progress_placeholder.markdown(formatted or "- Aguardando início da execução...")

        update_progress("Preparando execução...")
        try:
            config = YouTubeExtractionConfig(
                outdir=(settings.resultados_dir).resolve(),
                prefix=prefix,
                days=int(days) if days else None,
                channels=channels,
                channels_file=None,
                mode=mode,
                no_llm=False,
                asr_enabled=not no_asr,
                asr_provider=asr_provider,
                llm_provider=selected_model.get("provedor"),
                llm_model=selected_model.get("modelo", settings.llm_model),
                llm_key=selected_model.get("api_key"),
                resumo_max_palavras=int(resumo_max),
                cookies=settings.cookies_path,
                user_agent=user_agent,
                report_format=report_format,
                max_videos=int(max_videos) if max_videos else None,
            )
            service = YouTubeExecutionService(config)
            result = service.run(progress_callback=update_progress)
        except Exception as exc:
            st.error(f"Falha na execução: {exc}")
        else:
            with results_container:
                st.success(result.message)
                st.write(f"Canais processados: {result.total_channels}")
                st.write(f"Vídeos extraídos: {result.total_videos}")
                st.write(f"JSON: {result.json_path}")
                if result.report_path:
                    st.write(f"Relatório: {result.report_path}")
                st.write(f"Log: {result.log_path}")
                if result.token_details:
                    st.subheader("Tokens por vídeo")
                    ordered = sorted(result.token_details, key=lambda item: item["canal"])
                    st.dataframe(ordered, hide_index=True)
                total_prompt = result.total_prompt_tokens
                total_completion = result.total_completion_tokens
                total_tokens = total_prompt + total_completion
                st.metric(
                    "Total geral de tokens",
                    value=f"{total_tokens}",
                    delta=f"Entrada: {total_prompt} · Saída: {total_completion}",
                )
EOF_38

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_39' > "${TARGET_DIR}/src/app/interfaces/web/pages/5_Logs.py"
"""Visualização de logs e execuções recentes."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.infrastructure import repositories

st.title("Logs")
settings = get_settings()
log_dir = settings.log_dir
log_dir.mkdir(parents=True, exist_ok=True)

log_files = sorted(log_dir.glob("*.log"), reverse=True)
if log_files:
    labels = [f"{path.name}" for path in log_files]
    selected_label = st.selectbox("Selecione um log", options=labels)
    selected_path = log_dir / selected_label
    content = selected_path.read_text(encoding="utf-8") if selected_path.exists() else ""
    st.text_area("Conteúdo do log", value=content, height=400)
else:
    st.info("Nenhum log disponível.")

st.subheader("Histórico de execuções do YouTube")
st.table(repositories.list_youtube_extractions(limit=20))
EOF_39

mkdir -p "${TARGET_DIR}/src/app/interfaces/web/pages"
cat <<'EOF_40' > "${TARGET_DIR}/src/app/interfaces/web/pages/__init__.py"

EOF_40

mkdir -p "${TARGET_DIR}/tests"
cat <<'EOF_41' > "${TARGET_DIR}/tests/test_smoke.py"
"""Smoke tests for basic infrastructure."""

from __future__ import annotations

from app.config import reload_settings
from app.infrastructure.db import get_connection, initialize_database


def test_initialize_and_insert(tmp_path, monkeypatch) -> None:
    """Ensure the database schema can be created and used."""

    db_path = tmp_path / "data.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    reload_settings()
    initialize_database()
    assert db_path.exists()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO modelo_llm (modl_provedor, modl_modelo_llm, modl_api_key) VALUES (?, ?, ?)",
            ("TEST", "model", "key"),
        )
        cursor = conn.execute("SELECT COUNT(*) FROM modelo_llm")
        assert cursor.fetchone()[0] == 1
EOF_41

echo "Project files created in ${TARGET_DIR}."