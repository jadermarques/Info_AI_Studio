 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/src/app/infrastructure/repositories.py b/src/app/infrastructure/repositories.py
index 3373f496b0a27e2983ca628da94eddff766d2507..fc9809ddd163fc646169c19a7bc05e4f86f4f3ca 100644
--- a/src/app/infrastructure/repositories.py
+++ b/src/app/infrastructure/repositories.py
@@ -11,66 +11,69 @@ def save_llm_model(provedor: str, modelo: str, api_key: str, status: int = 1) ->
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
-    grupo: str,
+    grupos: str,
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
-    db.execute(query, (nome_canal.strip(), descricao.strip(), grupo.strip(), canal_id.strip(), status))
+    db.execute(
+        query,
+        (nome_canal.strip(), descricao.strip(), grupos.strip(), canal_id.strip(), status),
+    )
 
 
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
 
EOF
)