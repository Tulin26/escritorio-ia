-- ==========================================================
-- 15 logs_pedagogicos.formula / subformulas / legenda_variaveis
--
-- Por que existe: pelo mesmo motivo da 20260903120000 (passos_json), e por
-- uma licao que so apareceu depois dela.
--
-- Em 09/09/2026 a validacao `legenda-com-variavel-sem-formula` foi ligada
-- com 0 falso positivo em 7.200 questoes -- mas medidas no BANCO OFFLINE.
-- No mesmo dia, outra regra mostrou o quanto esse corpus engana: contra o
-- banco offline ela dava 0%, e contra 8 resolucoes REAIS a primeira versao
-- dela deu 25% de falso positivo. O banco autoral responde "a regra recusa
-- o que NOS escrevemos?", que e pergunta mais fraca do que a que importa.
--
-- Para confirmar a regra da legenda contra dado real e preciso ter, do lado
-- real, os campos que ela cruza. O log guardava pergunta, alternativas,
-- explicacao e (desde a 20260903120000) os passos -- mas nao a formula nem a
-- legenda de variaveis.
--
-- Sao TRES colunas e nao duas: a regra cruza a legenda contra a formula
-- principal E as subformulas. Sem subformulas a medicao sairia errada para
-- mais -- acusaria de orfa toda variavel que so aparece na formula auxiliar
-- (o "R" de "R = a\sqrt{3}/3", por exemplo), que e justamente o caso que a
-- regra existe para exigir.
--
-- SO O LABORATORIO preenche, e nao e limitacao: os outros modos passam por
-- _normalizar_questao_oraculo, que apaga formula, subformulas e legenda de
-- proposito ("no Oraculo, exatas e conceitual"). E o mesmo recorte da
-- passos_json, e o mesmo da propria validacao.
--
-- text para formula e legenda (sao frases curtas, e o que se quer e ler);
-- jsonb para subformulas, que e lista. Truncadas em repositories/log_repo.py.
--
-- Sem dado pessoal: e enunciado de matematica.
-- ==========================================================

alter table public.logs_pedagogicos
  add column if not exists formula text;

alter table public.logs_pedagogicos
  add column if not exists subformulas jsonb;

alter table public.logs_pedagogicos
  add column if not exists legenda_variaveis text;


-- ==========================================================
-- COMO MEDIR, quando houver uso acumulado:
--
--   python scripts/medir_legenda_sem_formula.py
--
-- Ou direto no SQL, para ver quantas questoes tem legenda e formula
-- guardadas (o denominador da medicao):
--
--   select count(*) as com_os_dois
--     from public.logs_pedagogicos
--    where legenda_variaveis is not null
--      and formula is not null;
-- ==========================================================
