# EducaGame IA

Plataforma educacional gamificada que usa IA para transformar conteúdo escolar
em desafios interativos, sessões de treino, simulados e aventuras em RPG.

Em uso por duas escolas: ETEC Araçatuba e Educacional Delta.

## Dois frontends, um núcleo

O mesmo código de negócio serve duas interfaces. Isso não é duplicação: são
públicos diferentes, e cada uma roda numa hospedagem gratuita distinta.

| | Flask | Streamlit |
|---|---|---|
| entrada | `flask_app.py` | `app.py` |
| dependências | `requirements_flask.txt` | `requirements.txt` |
| hospedagem | Render | Streamlit Cloud |
| telas | `web/routes/`, `web/templates/` | `st/ui/` (reexportado por `ui/`) |

Os dois compartilham `core/` (regras puras), `services/` (IA, pedagogia,
relatórios) e `repositories/` (Supabase). Uma correção em `services/` vale
para os dois.

O `requirements.txt` tem esse nome porque o Streamlit Cloud exige exatamente
ele. Os dois herdam de `requirements_base.txt`, que guarda o que é comum.

## Modos de jogo

- **Oráculo** — desafio gerado por IA em qualquer matéria
- **Treino** — sessão personalizada por matéria e dificuldade
- **Laboratório de Exatas** — problema guiado, com fórmula e passos de resolução
- **ENEM** — simulado
- **Boss Rush ENEM** — batalha contra chefes, um por área do ENEM
- **Escape Room** — salas encadeadas, com pistas a cada erro
- **RPG** — progresso narrativo, com HP, escolhas e crônica
- **Guildas** — batalha entre grupos da escola, montados a partir do desempenho

Além dos modos: progresso do aluno, painel do professor com análises, painel
administrativo e uma **ajuda dentro do app** (`/ajuda`), pesquisável e
alcançável de qualquer tela — inclusive antes do login, que é onde se pergunta
o que é o código da escola. O texto dela mora em `core/ajuda.py` e é o mesmo
que alimenta o PDF do guia de acesso.

Também pública, e alcançável do mesmo rodapé: a **política de privacidade**
(`/privacidade`, texto em `core/privacidade.py`), com o que a LGPD exige —
quais dados são coletados, com quem são compartilhados (inclusive o que os
provedores de IA recebem, ou melhor, não recebem: nunca nome, e-mail ou
identificação do aluno) e como pedir acesso, correção ou exclusão. O cadastro
exige aceite explícito dela, com a data gravada por aluno.

## Quando a IA falha, o jogo continua

A geração passa por uma cascata de três provedores — Groq, Gemini,
OpenRouter — com orçamento de tempo; o Groq entra duas vezes, com dois
modelos de cota separada. Se todos falharem,
ou se a resposta vier incoerente, entra o banco offline de **50.900 questões
autorais** em `services/banks/`. O aluno não vê tela de erro.

Cada questão gerada passa por validações antes de chegar ao aluno (alternativa
que contradiz a resolução, passo final que não bate com a resposta, raiz e
funções trigonométricas mal aproximadas). Toda validação foi ligada só depois
de medir sua taxa de falso positivo contra as 50.900 questões — o histórico
está em `tests/test_*_no_passo_final.py`.

## Tecnologias

- **Python 3.12** (`runtime.txt`)
- **Flask 3** + **Gunicorn** — frontend web e produção no Render
- **Streamlit 1.56** — frontend alternativo
- **Supabase** (PostgreSQL) — cliente próprio via `urllib`, em `repositories/supabase_client.py`
- **IA:** `groq`, `openai` (OpenRouter). O Gemini é chamado por HTTP direto, sem SDK
- **pandas**, **plotly** — análises do professor
- **reportlab**, **pillow** — relatórios e guias em PDF
- **pytest** — mais de 1.000 funções de teste

## Estrutura

```text
EducaGame/
|-- flask_app.py              # entrada Flask
|-- app.py                    # entrada Streamlit
|-- Procfile                  # gunicorn (Render)
|-- requirements_base.txt     # comum aos dois frontends
|-- requirements_flask.txt    # base + Flask
|-- requirements.txt          # base + Streamlit (nome exigido pelo Cloud)
|-- requirements-dev.txt      # pytest
|-- .env.example              # as 38 variaveis que o codigo le
|-- core/                     # regras puras, sem framework
|-- services/                 # IA, pedagogia, relatorios
|   `-- banks/                # 50.900 questoes offline
|-- repositories/             # acesso ao Supabase
|-- web/                      # Flask: routes/, templates/, static/
|-- st/ui/                    # Streamlit: telas (ui/ so reexporta)
|-- scripts/                  # seed, guias de acesso, medicoes
|-- supabase/migrations/      # SQL, em ordem de nome de arquivo
`-- tests/
```

## Como executar

Escolha o frontend — os dois usam o mesmo `.env` e o mesmo banco.

**Flask** (o principal):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements_flask.txt
python flask_app.py
```

Abra `http://localhost:5000`.

**Streamlit:**

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha. Ele documenta as 38 variáveis que
o código lê, quais são obrigatórias e quais armadilhas cada uma tem — não
duplique a lista aqui, porque a cópia envelhece.

O mínimo para subir com banco e login: `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY` e `FLASK_SECRET_KEY`. Sem nenhuma chave de IA o
app funciona apenas com o banco offline.

Em produção os mesmos nomes valem como variável de ambiente (Render) ou como
secret em TOML (Streamlit Cloud).

## Banco de dados

Aplique as migrations de `supabase/migrations/` **em ordem de nome de
arquivo** — o prefixo é a data. Depois, uma vez:

```bash
python scripts/seed_usuarios.py
```

Isso cria os três usuários iniciais, um por papel: `aluno`, `professores` e
`desenvolvedor`. O script avisa no fim que a conta de professor nasce sem
escola e precisa ser vinculada por SQL, senão ela não entra em lugar nenhum.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Segurança

- `.env` não é versionado; chaves só em variável de ambiente ou Secret File.
- A `SUPABASE_SERVICE_ROLE_KEY` ignora RLS. Ela nunca pode ir para código que
  roda no navegador.
- **RLS está habilitado em todas as tabelas, sem nenhuma policy** — ou seja,
  negação total para as chaves `anon` e `authenticated`. É deliberado: o acesso
  passa sempre pelo backend, com a service_role. Ao criar uma policy, saiba que
  está abrindo uma porta que hoje está fechada.

### Pedido de LGPD (acesso e exclusão)

A página `/privacidade` promete os direitos do Art. 18 e diz que o pedido
passa pela escola. Quem atende usa estes dois, nunca o painel do banco na mão:

```bash
python scripts/dados_do_aluno.py --quem aluno@escola.com --arquivo copia.json
python scripts/excluir_aluno.py --quem aluno@escola.com --confirmar
```

O primeiro só lê. O segundo, sem `--confirmar`, apenas mostra o que apagaria;
com ele, grava o backup antes, pede o nome do aluno digitado por extenso e
confere depois se o CASCADE levou logs e progresso junto. Não há tela para
isso de propósito — o porquê está em `services/dados_pessoais.py`.

---

Projeto desenvolvido com foco educacional por **Lucas Barbosa Nishigima**.
