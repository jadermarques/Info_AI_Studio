#!/usr/bin/env bash
set -euo pipefail

# Diretório alvo (default: diretório atual)
TARGET_DIR="${1:-.}"

# Lista de arquivos vazios que desejamos criar
FILES=(
  "README.md"
  ".env.example"
  "Makefile"
  "pyproject.toml"

  "src/app/__init__.py"
  "src/app/config.py"

  "src/app/domain/__init__.py"
  "src/app/domain/entities.py"
  "src/app/domain/fonte_service.py"
  "src/app/domain/llm_client.py"
  "src/app/domain/llm_service.py"
  "src/app/domain/parameters_service.py"
  "src/app/domain/validators.py"
  "src/app/domain/youtube/extractor_plus.py"
  "src/app/domain/youtube/service.py"

  "src/app/infrastructure/__init__.py"
  "src/app/infrastructure/backup.py"
  "src/app/infrastructure/db.py"
  "src/app/infrastructure/env_manager.py"
  "src/app/infrastructure/logging_setup.py"
  "src/app/infrastructure/repositories.py"
  "src/app/infrastructure/schema.sql"

  "src/app/interfaces/cli/__init__.py"
  "src/app/interfaces/cli/main.py"

  "src/app/interfaces/web/app.py"
  "src/app/interfaces/web/pages/1_Dashboard.py"
  "src/app/interfaces/web/pages/2_Cadastros.py"
  "src/app/interfaces/web/pages/3_Configurações.py"
  "src/app/interfaces/web/pages/4_Execução.py"
  "src/app/interfaces/web/pages/5_Logs.py"

  "examples/canal.txt"
  "examples/cookies.txt"

  "tests/test_smoke.py"
)

# Criação das pastas e arquivos
for f in "${FILES[@]}"; do
  mkdir -p "$TARGET_DIR/$(dirname "$f")"
  [ -f "$TARGET_DIR/$f" ] || touch "$TARGET_DIR/$f"
done

echo "Estrutura criada em ${TARGET_DIR}"
