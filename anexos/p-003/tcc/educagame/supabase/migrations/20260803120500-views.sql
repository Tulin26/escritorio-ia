-- ==========================================================
-- 06 views -> resumo turma
-- View consumida pela aplicacao (repositories/database_repo.py:
-- buscar_resumo_turma). As demais views que existiam antes
-- (view_ranking_top5, view_ranking, view_desempenho, view_desempenho_enem)
-- nao sao consultadas em nenhum lugar do codigo Python — o ranking e a
-- guilda sao montados direto a partir da tabela alunos/logs_pedagogicos
-- (repositories/database_repo.py: buscar_ranking, buscar_ranking_guildas;
-- services/guildas_service.py). Removidas aqui pra nao manter SQL morto.
-- Recarrega o schema cache do PostgREST ao final.
-- ==========================================================

drop view if exists public.view_ranking_top5 cascade;
drop view if exists public.view_ranking cascade;
drop view if exists public.view_desempenho cascade;
drop view if exists public.view_desempenho_enem cascade;

create or replace view public.view_resumo_turma as
select
  a.id as aluno_id,
  a.escola_id,
  a.nome,
  a.ano_escolar,
  a.periodo,
  count(l.id) as total_questoes,
  coalesce(sum(case when l.resultado = 'Acertou' then 1 else 0 end), 0) as acertos,
  coalesce(
    round(
      avg(l.tempo_resposta) filter (where l.tempo_resposta is not null and l.tempo_resposta > 0),
      2
    ),
    0
  ) as tempo_medio_resposta,
  coalesce(
    round(
      100.0 * sum(case when l.resultado = 'Acertou' then 1 else 0 end) / nullif(count(l.id), 0),
      1
    ),
    0
  ) as percentual
from public.alunos a
left join public.logs_pedagogicos l on a.id = l.aluno_id
group by a.id, a.escola_id, a.nome, a.ano_escolar, a.periodo;

do $$
begin
  perform pg_notify('pgrst', 'reload schema');
exception
  when undefined_function then
    null;
end
$$;
