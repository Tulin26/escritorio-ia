-- ==========================================================
-- 04 rpg_progressos -> progresso do RPG
-- Persistencia de progresso por aluno e aventura.
-- Seguro para base nova e para base existente.
-- ==========================================================

create table if not exists public.rpg_progressos (
  id uuid default gen_random_uuid() primary key,
  escola_id uuid references public.escolas(id) on delete cascade,
  aluno_id uuid references public.alunos(id) on delete cascade,
  aventura_id text not null,
  estado jsonb not null default '{}',
  origem text default 'manual',
  salvo_em timestamptz default now()
);

alter table public.rpg_progressos
  add column if not exists origem text default 'manual';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'unique_progresso_rpg'
  ) then
    alter table public.rpg_progressos
      add constraint unique_progresso_rpg unique (escola_id, aluno_id, aventura_id);
  end if;
end
$$;

create index if not exists idx_rpg_prog_aluno
  on public.rpg_progressos(aluno_id);

create index if not exists idx_rpg_prog_escola
  on public.rpg_progressos(escola_id);

alter table public.rpg_progressos enable row level security;
