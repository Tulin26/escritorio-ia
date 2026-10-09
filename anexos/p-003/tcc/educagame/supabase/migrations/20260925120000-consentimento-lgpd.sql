-- ==========================================================
-- Consentimento de dados (LGPD, Art. 8) no cadastro do aluno.
-- Guarda QUANDO a pessoa marcou a caixa de aceite da politica de
-- privacidade no cadastro -- null significa "nunca marcou" (cadastro
-- feito antes desta coluna existir, ou linha criada por upsert do
-- professor sem passar pelo formulario). Timestamp, e nao so um boolean,
-- porque prova a data em caso de duvida.
-- ==========================================================

alter table public.alunos
  add column if not exists consentimento_dados_em timestamp with time zone;
