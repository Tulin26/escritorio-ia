-- ==========================================================
-- 05 estados_sessao -> cache de estado de fluxo (oraculo/treino/laboratorio)
-- Substitui o dict em memoria de processo (_ESTADOS_FLASK_LOCAIS) que nao
-- sobrevivia a reinicio, nao era compartilhado entre workers/instancias
-- e crescia sem limite (memory leak). Guarda apenas estado de curta duracao
-- de um fluxo em andamento; nao e o progresso definitivo do aluno
-- (isso continua em rpg_progressos).
-- ==========================================================

create table if not exists public.estados_sessao (
  chave text primary key,
  estado jsonb not null default '{}',
  atualizado_em timestamptz not null default now()
);

create index if not exists idx_estados_sessao_atualizado_em
  on public.estados_sessao(atualizado_em);

alter table public.estados_sessao enable row level security;
