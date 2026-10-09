-- ==========================================================
-- 09 alunos username -> login simples (usuario/senha) pro aluno
-- Complementa o login por e-mail (migration 08): contas criadas
-- diretamente pelo professor/desenvolvedor (sem passar pelo cadastro
-- publico, sem exigir confirmacao de e-mail) usam um usuario simples em
-- vez de um endereco de e-mail real.
-- ==========================================================

alter table public.alunos
  add column if not exists username text;

create unique index if not exists idx_alunos_username
  on public.alunos(username)
  where username is not null;
