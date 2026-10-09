-- ==========================================================
-- 07 seed -> escola inicial
-- Seed inicial do projeto.
-- ==========================================================

insert into public.escolas (
  nome,
  slug,
  cor_tema,
  mostrar_ranking,
  modo_guilda
)
values (
  'ETEC - Araçatuba',
  'etec-aracatuba',
  '#003366',
  true,
  true
)
on conflict (slug) do update
set
  nome = excluded.nome,
  cor_tema = excluded.cor_tema,
  mostrar_ranking = excluded.mostrar_ranking,
  modo_guilda = excluded.modo_guilda;
