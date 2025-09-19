 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/src/app/domain/entities.py b/src/app/domain/entities.py
index 060e7a4123c3f13a560c50f3002ab3e07a95c225..65b5831652f8391ebef474330c262de43e2b9100 100644
--- a/src/app/domain/entities.py
+++ b/src/app/domain/entities.py
@@ -3,51 +3,51 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
 from datetime import datetime
 from pathlib import Path
 from typing import Any, Optional
 
 
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
-    grupo: str
+    grupos: str
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
 
EOF
)