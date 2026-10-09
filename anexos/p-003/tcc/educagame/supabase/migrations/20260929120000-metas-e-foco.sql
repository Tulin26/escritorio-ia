-- ==========================================================
-- Meta semanal de exercicios e foco de estudo por aluno.
--
-- Pedido da coordenacao em 28/09/2026: metas semanais por modo, com o
-- professor vendo quanto cada aluno ja fez, zerando toda semana; e um
-- tema de foco anotado por aluno ("Aluno X fica com progressao
-- aritmetica").
--
-- Duas tabelas, porque sao dois fatos diferentes:
--
--   conclusoes_modo -- UM EVENTO: "este aluno terminou uma partida de
--     Escape Room agora". A contagem de questoes ja sai de
--     logs_pedagogicos, mas partida CONCLUIDA nao existia em lugar
--     nenhum: rpg_progressos guarda o estado ATUAL, sobrescrito a cada
--     jogada, entao nao da para contar quantas corridas fecharam na
--     semana. Sem este evento, a meta de "uma jornada" nao teria como ser
--     medida -- e contar questoes nesses modos premiaria quem abre dez
--     Escape Rooms e responde a primeira sala de cada.
--
--   foco_do_aluno -- UM ESTADO: "o foco deste aluno, nesta materia, e
--     este tema". Uma linha por aluno e materia (o upsert troca o tema),
--     entao o professor pode dar um foco de Matematica e outro de
--     Historia para a mesma pessoa sem apagar nenhum dos dois.
--
-- As duas apagam em CASCADE junto com o aluno: sao dado pessoal, e um
-- pedido de exclusao da LGPD precisa levar tudo (ver
-- services/dados_pessoais.py).
--
-- RLS habilitado e SEM policy, como todas as outras: negacao total para
-- as chaves anon/authenticated, porque o acesso passa sempre pelo backend
-- com a service_role.
-- ==========================================================

create table if not exists public.conclusoes_modo (
  id uuid primary key default gen_random_uuid(),
  aluno_id uuid not null references public.alunos(id) on delete cascade,
  escola_id uuid not null references public.escolas(id) on delete cascade,
  modo text not null,
  concluido_em timestamp with time zone not null default now(),
  acertos integer,
  total integer
);

-- A consulta e sempre "o que este aluno (ou esta escola) concluiu desde
-- segunda-feira".
create index if not exists conclusoes_modo_aluno_idx
  on public.conclusoes_modo (aluno_id, concluido_em desc);
create index if not exists conclusoes_modo_escola_idx
  on public.conclusoes_modo (escola_id, concluido_em desc);

alter table public.conclusoes_modo enable row level security;


create table if not exists public.foco_do_aluno (
  id uuid primary key default gen_random_uuid(),
  aluno_id uuid not null references public.alunos(id) on delete cascade,
  escola_id uuid not null references public.escolas(id) on delete cascade,
  materia text not null,
  tema text not null,
  observacao text,
  definido_por text,
  definido_em timestamp with time zone not null default now(),
  unique (aluno_id, materia)
);

create index if not exists foco_do_aluno_escola_idx
  on public.foco_do_aluno (escola_id);

alter table public.foco_do_aluno enable row level security;
