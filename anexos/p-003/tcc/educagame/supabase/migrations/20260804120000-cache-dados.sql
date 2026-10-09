-- ==========================================================
-- 06 cache_dados -> cache de leitura compartilhado (RuntimeContext.cache_data)
-- Substitui o dict em memoria de processo que existia em
-- core/runtime_context.py. Um dict local nao e compartilhado entre
-- workers/instancias do Gunicorn: cada worker cacheava (e invalidava) por
-- conta propria, entao uma escrita num worker podia deixar os demais
-- servindo dados obsoletos por ate o TTL inteiro. Guarda apenas resultados
-- de leitura de curta duracao (alunos, ranking, logs); nunca e a fonte
-- de verdade dos dados.
-- ==========================================================

create table if not exists public.cache_dados (
  chave text primary key,
  valor jsonb not null,
  expira_em timestamptz not null,
  atualizado_em timestamptz not null default now()
);

create index if not exists idx_cache_dados_expira_em
  on public.cache_dados(expira_em);

alter table public.cache_dados enable row level security;
