-- ==========================================================
-- Pontos por dificuldade, somados SO no banco
-- ==========================================================
--
-- O defeito, medido em 13/09/2026
-- -------------------------------
-- Os pontos eram somados DUAS vezes a cada resposta no Flask: a rota gravava
-- o log (e o gatilho trg_atualizar_pontos somava +10 / -5) e, linhas depois,
-- chamava somar_pontos_aluno (que somava de novo, por dificuldade). A conta de
-- teste tinha 510 pontos: 355 do app + 155 do gatilho. O Streamlit ja confiava
-- so no gatilho, e avisava por escrito que somar no app "causaria
-- double-count".
--
-- Decidido: vale a pontuacao POR DIFICULDADE, e quem soma e so o banco. O app
-- deixou de somar no mesmo commit desta migracao. A conta vira UM update --
-- sem o ler-e-gravar do app, que perdia pontos com duas respostas juntas.
--
-- O erro desconta e o total nao passa de 0: e o que o gatilho ja fazia desde
-- 20260803120200. (O app aceitava total negativo, mas o commit que abriu isso
-- -- "Perda - pontuacao" -- so queria que o erro descontasse; antes dele o
-- max(0, ...) era sobre o valor da resposta, e errar nao tirava nada.)
--
-- De brinde, os 4 avisos do Security Advisor do Supabase
-- ------------------------------------------------------
--   * atualizar_pontos_ranking: "search path mutable" -> search_path fixo.
--   * atualizar_pontos: "search path mutable" -> e a funcao do gatilho
--     antigo trg_pontos, que 20260803120200 ja removia. Sem gatilho, sai.
--   * atualizar_tempo_medio_aluno: os dois de SECURITY DEFINER -> funcao
--     vazia (so "return new"), sem gatilho nenhum. Sai.
--   Se algum gatilho ainda usasse uma das duas, o "drop function" falha (nao
--   ha cascade) e a transacao inteira volta atras: nada e apagado em uso.
--
-- Os 8 "RLS Enabled No Policy" FICAM, de proposito: sem policy, as chaves anon
-- e authenticated nao leem nada, e o app acessa tudo pelo servidor com a
-- service_role (ver README). Criar policy ali abriria os dados.
-- ==========================================================

begin;

create or replace function public.atualizar_pontos_ranking()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
  -- O log grava "Facil", "Medio" ou "Dificil" (normalizar_dificuldade), mas a
  -- leitura aceita acento e caixa, como o Python.
  nivel text := lower(translate(coalesce(new.dificuldade, ''), 'ÁáÍíÉé', 'AaIiEe'));
  ganho integer;
  perda integer;
begin
  -- Os MESMOS valores de web/routes/flask_helpers_fla.py
  -- (pontuacao_por_dificuldade / perda_pontuacao_por_dificuldade), que a tela
  -- mostra. tests/test_pontos_so_no_banco.py prende os dois juntos.
  if nivel like '%dificil%' or nivel like 'dif%' then ganho := 30; perda := 15;
  elsif nivel like '%facil%' then ganho := 10; perda := 5;
  else ganho := 20; perda := 10;
  end if;

  if new.resultado = 'Acertou' then
    update public.alunos
      set pontos_totais = coalesce(pontos_totais, 0) + ganho
      where id = new.aluno_id;
  elsif new.resultado = 'Errou' then
    update public.alunos
      set pontos_totais = greatest(0, coalesce(pontos_totais, 0) - perda)
      where id = new.aluno_id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_pontos on public.logs_pedagogicos;
drop trigger if exists trg_atualizar_pontos on public.logs_pedagogicos;

create trigger trg_atualizar_pontos
  after insert on public.logs_pedagogicos
  for each row execute function public.atualizar_pontos_ranking();

drop function if exists public.atualizar_pontos();
drop function if exists public.atualizar_tempo_medio_aluno();

commit;

-- Conferencia (e o resultado que aparece no SQL Editor): tem de sair UMA linha,
-- trg_atualizar_pontos -> atualizar_pontos_ranking, com search_path fixo.
select t.tgname as gatilho, p.proname as funcao, p.proconfig as configuracao
from pg_trigger t
join pg_proc p on p.oid = t.tgfoid
where t.tgrelid = 'public.logs_pedagogicos'::regclass
  and not t.tgisinternal;
