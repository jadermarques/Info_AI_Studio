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