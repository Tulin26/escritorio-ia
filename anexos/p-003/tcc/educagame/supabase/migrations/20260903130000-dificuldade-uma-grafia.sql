-- ==========================================================
-- 14 logs_pedagogicos.dificuldade -> uma grafia so
--
-- Medido nos logs reais: a dificuldade chegava ao banco em QUATRO grafias.
--
--   "Medio"       RPG, Treino, Boss Rush, ENEM
--   "Médio"       Laboratorio, Oraculo, Escape Room
--   "Difícil"     Laboratorio, Oraculo
--   "🔴 Difícil"  Laboratorio do Streamlit -- o rotulo do slider ia DIRETO
--                 para o log, emoji e tudo
--
-- O painel do professor filtra e agrupa por este campo, entao "Medio" e
-- "Médio" contavam como dificuldades DIFERENTES. E o mesmo defeito ja
-- corrigido no prefixo de materia ("LAB-Fisica" x "Fisica"), que fragmentava
-- a tela de Progresso.
--
-- A escrita nova ja normaliza (repositories/log_repo.py chama
-- core.config.normalizar_dificuldade, no mesmo lugar onde "resultado" e
-- "modo" ja eram normalizados). Esta migracao arruma o que ficou para tras.
--
-- A regra e a do resto do projeto: a CHAVE fica sem acento e sem emoji, e o
-- ROTULO com acento vem de exibir_dificuldade() na hora de desenhar.
--
-- Idempotente: rodar duas vezes nao muda nada na segunda.
-- ==========================================================

update public.logs_pedagogicos
   set dificuldade = 'Facil'
 where dificuldade is not null
   and dificuldade <> 'Facil'
   and translate(lower(btrim(dificuldade)), 'áàâãéêíóôõúç', 'aaaaeeiooouc') like '%facil%';

update public.logs_pedagogicos
   set dificuldade = 'Medio'
 where dificuldade is not null
   and dificuldade <> 'Medio'
   and translate(lower(btrim(dificuldade)), 'áàâãéêíóôõúç', 'aaaaeeiooouc') like '%medio%';

update public.logs_pedagogicos
   set dificuldade = 'Dificil'
 where dificuldade is not null
   and dificuldade <> 'Dificil'
   and translate(lower(btrim(dificuldade)), 'áàâãéêíóôõúç', 'aaaaeeiooouc') like '%dificil%';

-- "Facil" tem de vir antes de "Dificil"? Nao: os LIKE sao sobre a palavra
-- inteira normalizada, e "dificil" nao contem "facil" -- d-i-f-i-c-i-l nao
-- tem a sequencia f-a-c-i-l. A ordem acima nao importa.


-- ==========================================================
-- CONFERIR depois de aplicar -- tem de sobrar so as tres chaves:
--
--   select dificuldade, count(*)
--     from public.logs_pedagogicos
--    where dificuldade is not null
--    group by dificuldade
--    order by 2 desc;
-- ==========================================================
