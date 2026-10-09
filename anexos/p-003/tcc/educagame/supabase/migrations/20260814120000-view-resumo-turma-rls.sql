-- ==========================================================
-- 09 view_resumo_turma -> respeitar RLS das tabelas de origem
-- MELHORIA: a view estava marcada como "Unrestricted" no painel do
-- Supabase -- views, por padrao, rodam com o privilegio de quem CRIOU a
-- view (o dono), nao de quem consulta, entao elas ignoram o RLS das
-- tabelas de origem mesmo quando essas tabelas tem RLS habilitado. Como
-- alunos/logs_pedagogicos tem RLS habilitado mas nenhuma policy (deny-
-- -all pra chave anon), a view furava essa protecao: qualquer requisicao
-- com a chave publica (anon) conseguia listar nome + escola + desempenho
-- de TODOS os alunos de TODAS as escolas, sem autenticacao nenhuma.
-- A aplicacao so consulta essa view via service role key (que ja ignora
-- RLS de qualquer forma, ver repositories/database_repo.py:
-- buscar_resumo_turma), entao isso nunca foi necessario pra funcionar --
-- so sobrou aberto por padrao.
-- "security_invoker = true" (Postgres 15+, suportado pelo Supabase) faz
-- a view passar a rodar com o privilegio de QUEM CONSULTA, entao ela
-- volta a respeitar o RLS (deny-all) das tabelas de origem pra chaves
-- anon/authenticated, igual as tabelas normais.
-- ==========================================================

alter view public.view_resumo_turma set (security_invoker = true);

do $$
begin
  perform pg_notify('pgrst', 'reload schema');
exception
  when undefined_function then
    null;
end
$$;
