-- ==========================================================
-- 12 usuarios.escola_id -> conta de professor presa a uma escola
--
-- A tabela usuarios nascia sem escola: so "aluno" carregava unidade (na
-- tabela alunos). Na pratica isso fazia de professor uma conta GLOBAL --
-- bastava escolher outra escola na lista de entrada para abrir o painel de
-- gestao dela: alunos, logs, ranking.
--
-- Visto ao vivo: a conta entregue ao diretor de uma escola alcancava a outra.
--
-- "desenvolvedor" continua global de proposito -- e a conta de manutencao, e
-- o painel ADM existe justamente para agir sobre todas as escolas.
--
-- ON DELETE CASCADE, e nao SET NULL, de proposito: apagada a escola, a conta
-- de professor dela vai junto. SET NULL faria a conta virar GLOBAL em
-- silencio, que e exatamente o problema que esta migracao existe para tirar.
-- ==========================================================

alter table public.usuarios
  add column if not exists escola_id uuid
  references public.escolas(id) on delete cascade;

create index if not exists idx_usuarios_escola
  on public.usuarios(escola_id);


-- ==========================================================
-- DEPOIS DE APLICAR: vincule as contas de professor que ja existem.
--
-- Enquanto escola_id estiver nulo, a conta de professor NAO entra em escola
-- nenhuma -- e recusada com "sua conta nao esta vinculada a nenhuma escola".
-- E deliberado: conta de professor sem escola era justamente a conta que
-- abria todas.
--
-- Veja o que existe:
--
--   select u.username, u.role, u.escola_id, e.nome
--     from public.usuarios u
--     left join public.escolas e on e.id = u.escola_id
--    where u.role = 'professor';
--
-- E vincule cada uma (ajuste username e slug):
--
--   update public.usuarios
--      set escola_id = (select id from public.escolas where slug = 'etecata')
--    where username = 'professores';
--
--   update public.usuarios
--      set escola_id = (select id from public.escolas where slug = 'deltaata')
--    where username = 'professordelta';
--
-- Conferir se sobrou alguma sem escola:
--
--   select username from public.usuarios
--    where role = 'professor' and escola_id is null;
-- ==========================================================
