-- ==========================================================
-- 01 bootstrap -> tabelas base
-- Estrutura principal do EducaGame.
-- Seguro para base nova e para base existente.
-- ==========================================================

create extension if not exists pgcrypto;

create table if not exists public.escolas (
  id uuid default gen_random_uuid() primary key,
  nome text not null,
  slug text unique not null,
  cor_tema text default '#003366',
  mostrar_ranking boolean default true,
  modo_guilda boolean default true,
  created_at timestamptz default now()
);

create table if not exists public.alunos (
  id uuid default gen_random_uuid() primary key,
  nome text not null,
  ra_identificacao text,
  ano_escolar text not null,
  periodo text not null,
  pontos_totais integer default 0,
  ensino_religioso boolean default false,
  escola_id uuid references public.escolas(id) on delete cascade,
  criado_em timestamptz default now()
);

alter table public.alunos
  add column if not exists pontos_totais integer default 0,
  add column if not exists ensino_religioso boolean default false,
  add column if not exists criado_em timestamptz default now();

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'unique_ra_por_escola'
  ) then
    alter table public.alunos
      add constraint unique_ra_por_escola unique (escola_id, ra_identificacao);
  end if;
end
$$;

update public.alunos
set pontos_totais = 0
where pontos_totais is null;

create table if not exists public.rpg_config (
  id uuid default gen_random_uuid() primary key,
  escola_id uuid references public.escolas(id) on delete cascade,
  titulo text not null,
  materia text not null,
  serie text not null,
  cenario text not null,
  heroi_nome text,
  poderes text,
  objetivo_final text,
  descricao text,
  created_at timestamptz default now()
);

alter table public.rpg_config
  add column if not exists heroi_nome text,
  add column if not exists poderes text,
  add column if not exists objetivo_final text,
  add column if not exists descricao text;

create index if not exists idx_rpg_config_escola
  on public.rpg_config(escola_id);

-- MELHORIA: RLS habilitada em todas as tabelas public.* (antes ficavam com
-- "disable row level security" explicito). O backend Flask sempre acessa o
-- Supabase com a service_role key (repositories/supabase_client.py), que
-- ignora RLS por definicao — entao isso nao muda nada no comportamento do
-- app. O que muda: se a anon key ou uma authenticated key vazarem algum dia,
-- elas nao conseguem ler/escrever nada aqui, porque nenhuma policy foi
-- criada pra essas roles (RLS habilitada + zero policies = deny by default).
alter table public.escolas enable row level security;
alter table public.alunos enable row level security;
alter table public.rpg_config enable row level security;
