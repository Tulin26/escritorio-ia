-- ==========================================================
-- 02 usuarios -> login por papel (aluno / professor / desenvolvedor)
-- Substitui a "senha mestra" unica (SENHA_MESTRA) por uma tabela real,
-- com senha em hash (gerado pelo Flask via werkzeug.security, nao aqui).
-- Seguro para base nova e para base existente.
-- ==========================================================

create table if not exists public.usuarios (
  id uuid default gen_random_uuid() primary key,
  username text unique not null,
  senha_hash text not null,
  role text not null check (role in ('aluno', 'professor', 'desenvolvedor')),
  ativo boolean default true,
  criado_em timestamptz default now()
);

create index if not exists idx_usuarios_role
  on public.usuarios(role);

-- Sem seed aqui de proposito: rode `python scripts/seed_usuarios.py` depois
-- de aplicar as migrations pra criar os 3 usuarios iniciais (aluno/aluno,
-- professores/professores, desenvolvedor/desenvolvedor) com o mesmo
-- algoritmo de hash que o Flask usa pra validar login.

alter table public.usuarios enable row level security;
