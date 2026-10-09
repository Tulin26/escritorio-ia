ORDEM DE EXECUCAO - EducaGame IA (SQL)

Primeira instalacao ou apos reset total:

  Aplique TODOS os arquivos de supabase/migrations/ em ordem de nome. O
  prefixo e a data (AAAAMMDDHHMMSS), entao a ordem alfabetica ja e a ordem
  cronologica correta. Hoje sao 14 arquivos, de 20260803120000_bootstrap.sql
  a 20260903130000_dificuldade_uma_grafia.sql.

  Nao ha lista fixa aqui de proposito. A versao anterior deste arquivo
  nomeava cinco migrations com prefixo 20260427 -- arquivos que nao existem
  mais. Quem seguisse o passo a passo travava no primeiro item.

  Depois: python scripts/seed_usuarios.py (cria os 3 usuarios iniciais).

Uso diario:
- Nao rode nada destrutivo em ambiente com dados reais. Nao ha arquivo de
  reset no repositorio; se voce escrever um, ele nao deve ficar aqui.
- Para adicionar novas escolas, use o painel ADM do app ou crie uma nova
  migration/insert controlado.
- Nao compacte nem envie a pasta supabase/.temp/ (ja esta no .gitignore).

Observacao sobre RLS -- ATENCAO, isto mudou:
- O RLS esta HABILITADO em todas as tabelas, e nenhuma policy foi criada.
  Na pratica: negacao total para as chaves anon e authenticated.
- Nao e "DEV MODE com RLS desativado", como este arquivo dizia antes. E o
  oposto, e e deliberado: todo acesso passa pelo backend com a service_role,
  que ignora RLS. Ver o comentario no 20260803120000_bootstrap.sql.
- Criar uma policy ABRE uma porta que hoje esta fechada. Pense antes.

Arquivos sensiveis:
- supabase/.temp/ e .env ficam fora do Git.
- A SUPABASE_SERVICE_ROLE_KEY nunca pode ir para codigo que roda no navegador.

Contexto geral do projeto: ver README.md.
