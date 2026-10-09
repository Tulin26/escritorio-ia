-- ==========================================================
-- 03 logs_pontos -> logs + trigger
-- Logs pedagogicos, validacoes e pontuacao.
-- Seguro para base nova e para base existente.
-- ==========================================================

create table if not exists public.logs_pedagogicos (
  id uuid default gen_random_uuid() primary key,
  aluno_id uuid references public.alunos(id) on delete cascade,
  escola_id uuid references public.escolas(id) on delete cascade,
  materia text not null,
  resultado text not null check (resultado in ('Acertou', 'Errou')),
  pergunta_texto text,
  resposta_correta text,
  resposta_aluno text,
  explicacao_ia text,
  tempo_resposta numeric(8,2),
  modo text default 'oraculo',
  area_bncc text,
  competencia_bncc text,
  habilidade_bncc text,
  codigo_bncc text,
  dificuldade text,
  matriz_enem text,
  data_hora timestamptz default now()
);

alter table public.logs_pedagogicos
  add column if not exists pergunta_texto text,
  add column if not exists resposta_correta text,
  add column if not exists resposta_aluno text,
  add column if not exists explicacao_ia text,
  add column if not exists tempo_resposta numeric(8,2),
  add column if not exists modo text default 'oraculo',
  add column if not exists area_bncc text,
  add column if not exists competencia_bncc text,
  add column if not exists habilidade_bncc text,
  add column if not exists codigo_bncc text,
  add column if not exists dificuldade text,
  add column if not exists matriz_enem text,
  add column if not exists data_hora timestamptz default now();

alter table public.logs_pedagogicos
  drop constraint if exists logs_tempo_resposta_nonneg;

alter table public.logs_pedagogicos
  add constraint logs_tempo_resposta_nonneg
  check (tempo_resposta is null or tempo_resposta >= 0);

create index if not exists idx_logs_aluno
  on public.logs_pedagogicos(aluno_id);

create index if not exists idx_logs_escola
  on public.logs_pedagogicos(escola_id);

create index if not exists idx_logs_modo
  on public.logs_pedagogicos(modo);

create index if not exists idx_logs_area
  on public.logs_pedagogicos(area_bncc);

create or replace function public.atualizar_pontos_ranking()
returns trigger
language plpgsql
as $$
begin
  if new.resultado = 'Acertou' then
    update public.alunos
      set pontos_totais = coalesce(pontos_totais, 0) + 10
      where id = new.aluno_id;
  elsif new.resultado = 'Errou' then
    update public.alunos
      set pontos_totais = greatest(0, coalesce(pontos_totais, 0) - 5)
      where id = new.aluno_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_atualizar_pontos on public.logs_pedagogicos;
drop trigger if exists trg_pontos on public.logs_pedagogicos;

create trigger trg_atualizar_pontos
  after insert on public.logs_pedagogicos
  for each row execute function public.atualizar_pontos_ranking();

alter table public.logs_pedagogicos enable row level security;
