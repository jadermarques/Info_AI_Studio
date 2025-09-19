-- Migração para tornar a descrição opcional e garantir suporte a múltiplos grupos no campo grupo_canal

-- 1. Renomear tabela antiga
ALTER TABLE fonte_youtube RENAME TO fonte_youtube_old;

-- 2. Criar nova tabela com foyt_descricao opcional
CREATE TABLE fonte_youtube (
    foyt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    foyt_nome_canal TEXT NOT NULL,
    foyt_descricao TEXT,
    foyt_grupo_canal TEXT NOT NULL,
    foyt_id_canal TEXT NOT NULL,
    foyt_status INTEGER NOT NULL DEFAULT 1,
    foyt_created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Copiar dados da tabela antiga para a nova
INSERT INTO fonte_youtube (foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal, foyt_status, foyt_created_at)
SELECT foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal, foyt_status, foyt_created_at
FROM fonte_youtube_old;

-- 4. Recriar índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_fonte_youtube_canal ON fonte_youtube (foyt_id_canal);

-- 5. Remover tabela antiga
DROP TABLE fonte_youtube_old;
