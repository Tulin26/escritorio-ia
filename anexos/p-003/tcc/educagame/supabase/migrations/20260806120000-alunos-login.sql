-- ==========================================================
-- 08 alunos login -> cadastro individual do aluno por email/senha
-- Antes so existia um login unico compartilhado (role "aluno") e o
-- aluno especifico era escolhido depois, numa lista, sem senha propria.
-- Agora cada linha de alunos pode ter suas proprias credenciais; o
-- cadastro faz upsert por (escola_id, ra_identificacao) — se o professor
-- ja matriculou o aluno antes, o cadastro so completa esse registro
-- (preservando pontos_totais e historico) em vez de duplicar.
-- ==========================================================

alter table public.alunos
  add column if not exists email text,
  add column if not exists senha_hash text,
  add column if not exists email_confirmado boolean not null default false;

create unique index if not exists idx_alunos_email
  on public.alunos(email)
  where email is not null;
