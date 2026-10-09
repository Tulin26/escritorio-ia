# Plano m-008: TCC (EducaGame IA) - análise, propostas, arquitetura e resumo antes do GitHub

- **Projeto:** tcc (briefing em `projetos/tcc.md`)
- **Pedido:** p-003, 2026-10-09 13:53
- **Data do plano:** 2026-10-09 14:10

## Pedido original

> "eu quero que voce analise meu projeto de tcc , me de propostas do que melhorar ou do que adicionar , ver se teria como melhorar a arquitetura tambem me de um resumo de tudo antes de subir para esse git https://github.com/LucasNishigima/EducaGame"

O pedido tem quatro partes: (1) analisar o projeto; (2) propor o que melhorar e o que adicionar; (3) dizer se dá para melhorar a arquitetura; (4) entregar um resumo de tudo **antes** de subir para o GitHub.

## Anexos recebidos

Uma pasta com o código do projeto: `anexos/p-003/tcc/educagame/` (393 arquivos). Como é pasta grande, o Diretor usou a lista de `pedidos[p-003].anexos` e o Glob como índice e leu só o que importa para planejar.

| Arquivo / pasta | O que é | Para que serve | Qual sala usa |
|---|---|---|---|
| `readme.md` | Apresentação do projeto: dois frontends (Flask e Streamlit) sobre o mesmo núcleo, 8 modos de jogo, cascata de IA com banco offline de 50.900 questões, LGPD, RLS. | Visão geral e afirmações a conferir. | todas |
| `proximos-passos.md` (1.716 linhas, lido em partes) | Diário técnico do projeto: o que foi feito, o que está aberto, decisões conscientes, situação do TG (documento escrito do TCC). | Mostra pendências, dívidas e decisões já tomadas (para não propor de novo o que já foi recusado). | Revisão, Estratégia |
| `readme-ordem-execucao.txt`, `readme-flask.md`, `notes-codex.md` | Instruções de banco/migrations, notas do Flask e notas deixadas por uma ferramenta de IA. | Conferir se a documentação bate com o código. | Revisão |
| `env.example`, `gitignore`, `gitattributes`, `render.yaml`, `procfile`, `gunicorn-conf.py`, `runtime.txt`, `requirements*.txt`, `package.json`, `pytest.ini` | Configuração, dependências e deploy (Render, Streamlit Cloud). | Segurança, prontidão para o GitHub, deploy. | Revisão |
| `github/` (dependabot, workflow de auditoria), `devcontainer/`, `claude/launch.json` | Automação do GitHub e arquivos de ferramentas (eram `.github/`, `.devcontainer/`, `.claude/`). | Checklist pré-push e CI. | Revisão |
| `flask-app.py`, `app.py` | Entradas do Flask e do Streamlit. | Arquitetura. | Revisão |
| `core/`, `services/` (inclui `ia/`, `banks/`, `relatorios/`), `repositories/` | Regras puras, IA/pedagogia/relatórios e acesso ao Supabase. | Arquitetura e qualidade. | Revisão, Estratégia |
| `web/` (rotas, templates, CSS, imagens, áudios) e `st/ui/` | Telas do Flask e do Streamlit. | Análise de UI/UX. | Marca & Design |
| `supabase/migrations/` (19 arquivos SQL) | Esquema do banco, RLS, consentimento LGPD, metas. | Segurança e dados pessoais. | Revisão |
| `scripts/` (6 arquivos) | Seed de usuários, guia de acesso, dados/exclusão de aluno (LGPD). | Segurança e LGPD. | Revisão |
| `tests/` (cerca de 175 arquivos) | Testes pytest. | Qualidade e cobertura. | Revisão |
| `assets/` (logos da ETEC e da Delta), `web/static/img/` (logo do app) | Imagens. | UI/UX e direitos de uso. | Marca & Design, Revisão |
| `data/banco-especifico-*.json` (0,5 MB e 1,1 MB), `suno/*.mp3`, `web/static/audio/*.mp3` (cerca de 23 MB de áudio) | Bancos de questões e trilhas. | **Não lidos** (não precisam). Os áudios só entram no checklist (tamanho e licença). | Revisão (só checklist) |

O que o Diretor **não leu**: o código das pastas `core/`, `services/`, `repositories/`, `web/`, `st/`, os testes e os SQL (ficam para as salas), os bancos JSON e os MP3.

### Atenção: a cópia em `anexos/` não é a pasta que vai para o GitHub

Ao subir a pasta para o escritório, os nomes foram simplificados: `flask_app.py` virou `flask-app.py`, `__init__.py` virou `init.py`, `.gitignore` virou `gitignore`, `.env.example` virou `env.example`, `.github/` virou `github/`, e assim por diante (sublinhado vira hífen, ponto inicial some). Os `import` do Python não funcionam com hífen. Consequências:

- Os agentes leem a cópia sabendo disso (ex.: `services/ia-service.py` é o `services/ia_service.py` do projeto).
- **O push tem de ser feito da pasta original do projeto**, nunca desta cópia.
- Os agentes analisam lendo o código: não rodam os testes nem o app.

## Pontos que o Diretor já viu (as salas confirmam e aprofundam)

**Segurança (nenhum valor de chave foi copiado para cá):**
- Procurei padrões de chaves (Groq, Gemini, OpenRouter, JWT/Supabase, chave privada) na cópia e **não achei nenhuma chave real**. O `env.example` só tem textos de exemplo e o `.env` não veio. O `gitignore` já cobre `.env`, `secrets.toml`, PDFs e os backups de pedido LGPD. Bom sinal.
- `scripts/seed-usuarios.py` cria três contas iniciais (aluno, professor e desenvolvedor, que é o admin global) com **senha igual ao nome de usuário**. Se o banco de produção ainda usa essas senhas, um repositório público entrega o acesso de administrador. Precisa confirmar antes do push.
- O próprio código (`flask-app.py`) diz que uma chave de sessão fixa já esteve "neste código público". Isso indica que o repositório já é (ou foi) público e que o **histórico do git** pode guardar segredos antigos. A cópia não traz a pasta `.git`, então só o dono consegue varrer o histórico.
- `proximos-passos.md` cita nomes de contas reais (professores e contas de avaliação), códigos de escola e o endereço de produção. É documento interno: decidir se vai para um repositório público.

**Documentação desatualizada:**
- `readme-ordem-execucao.txt` diz que são 14 migrations; há 19.
- `proximos-passos.md` diz "atualizado em 09/09/2026", mas o `env.example` registra mudanças de 15/09 e 02/10.
- O `readme.md` cita a pasta `ui/` (que reexporta `st/ui/`) e scripts de medição (`scripts/medir_*.py`, citados no `proximos-passos.md`). Eles não vieram na cópia: ou não foram enviados, ou não existem mais.
- `render.yaml` avisa que não está em uso (o serviço foi criado pelo painel do Render).

**Qualidade e CI:**
- O único workflow do GitHub é a auditoria de dependências (pip-audit), e ele roda com Python 3.11, enquanto o projeto usa 3.12. Os mais de 1.000 testes não rodam no GitHub a cada push.
- `package.json` só existe para a CLI do Supabase. `claude/launch.json` e `notes-codex.md` são arquivos de ferramentas de IA: decidir se ficam no repositório.

**Arquivos e direitos:**
- Cerca de 23 MB de MP3 (uma faixa em `suno/` e três em `web/static/audio/`) e as logos das duas escolas. Cabem no GitHub (limite de 100 MB por arquivo), mas é preciso confirmar a licença das músicas (faixa gerada no Suno, trilhas de terceiros) e a autorização das escolas para usar as logos num repositório público.

## Perguntas para o dono

1. **Quem sobe e para onde?** O repositório é de Lucas Barbosa Nishigima (autor citado no readme). Você é do grupo do TCC ou tem acesso de escrita? É para atualizar o repositório que já existe (a pasta original tem histórico, por exemplo a branch `StreamLit`) ou para criar um novo?
2. **O repositório é público ou privado?** Isso muda o peso dos riscos acima.
3. **Quando é a banca?** Para separar "fazer antes da banca" de "depois".
4. As **senhas das contas iniciais** e das contas de avaliação da Delta já foram trocadas em produção?
5. As **músicas** (Suno e trilhas) e as **logos das escolas** podem ficar num repositório público?
6. A pasta `ui/` e os `scripts/medir_*.py` existem na pasta original? Se sim, não vieram no envio.
7. Quer ajuda também com o **texto do TG** (o `proximos-passos.md` diz que faltam Resumo, Abstract e capítulos 3 a 5)? O arquivo é `.docx`, que não abrimos. Se quiser, mande em PDF num pedido novo.

## Hipótese de trabalho (seguimos com ela se não houver resposta)

- O dono participa do TCC e vai **atualizar o repositório que já existe**, fazendo o push **ele mesmo**, da pasta original, depois de ler o resumo e passar pelo checklist. **Tratamos o repositório como público**, porque é o caso mais arriscado e o código indica isso.
- A banca é no fim de 2026 (TG da Fatec Araçatuba, ADS 2026). As propostas são separadas em "antes do push", "antes da banca" e "depois da banca".
- **Nenhuma sala altera o código.** Toda melhoria e toda mudança de arquitetura vira **proposta em .md**: o que mudar, onde, por quê, esforço, risco e como testar.
- **Escolha das salas:** o escritório não tem sala de engenharia.
  - A **Revisão** fica com a análise técnica (arquitetura, qualidade, testes, segurança, LGPD e o checklist pré-push). Pela tabela de roteamento, "revisar algo que o dono já tem" vai para a Revisão, e ela é a sala de qualidade e risco.
  - **Marca & Design** analisa as telas (UI/UX), porque a skill de front-end/UI-UX está nela.
  - A **Estratégia** propõe o que adicionar (visão de produto: alunos, professores, escolas e banca), junta tudo num plano priorizado e escreve o **resumo final**.
  - A **Revisão** fecha conferindo o resumo.
- A **Pesquisa não entra**: tudo o que o pedido precisa está no código e nos documentos enviados. Comparar com outras plataformas educacionais pode virar um pedido à parte, se o dono quiser.

## Sub-missões

| id | Área | Título | Depende de | XP |
|---|---|---|---|---|
| m-009 | revisor (revisor) | Auditoria técnica do EducaGame: arquitetura, qualidade, segurança/LGPD e checklist pré-push | m-008 | 50 |
| m-010 | design (designer) | Análise de UI/UX das telas (Flask e Streamlit) com propostas de melhoria | m-008 | 30 |
| m-011 | estrategia (estrategista) | Propostas do que adicionar, plano priorizado de melhorias e resumo final antes do GitHub | m-009, m-010 | 40 |
| m-012 | revisor (revisor) | Revisão final do resumo e do checklist pré-push | m-011 | 20 |

## Critérios de aceite

**m-009 (Revisão: auditoria técnica)**, entrega `revisor/m-009-tcc-auditoria-tecnica.md`
- **Mapa da arquitetura** como ela é hoje: camadas (`core/`, `services/`, `repositories/`, `web/`, `st/ui/`), os dois frontends, a cascata de IA com o banco offline, o Supabase com RLS e service_role, o deploy (Render e Streamlit Cloud). Pode ter um diagrama em texto ou Mermaid.
- **Avaliação da arquitetura:** pontos fortes, acoplamentos, duplicações entre os frontends, módulos grandes demais, dependências entre camadas (ex.: `services/` importando algo de interface). Responde direto: "dá para melhorar a arquitetura? o quê, quanto custa, vale fazer antes da banca?". **Cada proposta** traz: arquivo ou pasta, problema, mudança proposta, esforço (P/M/G), risco e como testar.
- **Qualidade:** testes (quantidade, o que cobrem, o que falta, ausência de CI rodando pytest), tratamento de erros, configuração, dependências (versões fixadas, `openai>=1.0.0` sem teto, Python 3.11 no CI contra 3.12 no runtime).
- **Segurança e LGPD:** varredura de segredos no código (dizer onde procurou e o resultado, **sem copiar valores**); contas iniciais com senha igual ao usuário; RLS e uso da service_role; CSRF, cookie, rate limit e cabeçalhos; o que os provedores de IA recebem; scripts de acesso e exclusão de dados (LGPD Art. 18); dados pessoais em documentos e testes.
- **Documentação:** lista do que está desatualizado ou contraditório (readme, ordem de execução, próximos passos, render.yaml) e do que está citado mas não veio (`ui/`, `scripts/medir_*`).
- **Checklist pré-push** em itens marcáveis, para o dono executar na pasta original: varrer o histórico do git atrás de segredos (e trocar a chave que aparecer); confirmar que `.env`, `secrets.toml`, PDFs de guia e backups LGPD não estão no `git status`; trocar senhas padrão; decidir sobre `proximos-passos.md`, `notes-codex.md`, `.claude/`, áudios e logos; rodar `python -m pytest` antes do push; conferir o branch de destino; ligar o Dependabot e a varredura de segredos do GitHub.
- Separa claramente **o que foi verificado no código** do que é **suposição**, e lembra que a cópia tem nomes simplificados e que nada foi executado.
- Não copia nenhuma chave, senha, e-mail ou nome de aluno/professor para a entrega.

**m-010 (Marca & Design: UI/UX)**, entrega `design/m-010-tcc-ui-ux.md`
- Analisa as telas do Flask (`web/templates/`, `web/static/css/flask.css`), que são o frontend principal, e compara com as do Streamlit (`st/ui/`, `core/estilos/`, `core/design-system*.py`).
- Avalia: clareza para alunos do fundamental e médio, fluxo de entrada (escola, código, login), feedback de carregamento e erro, acessibilidade (contraste, foco, leitor de tela, tamanho de toque), celular (responsivo), consistência visual entre os modos e entre os dois frontends, e a logo antiga, cujo desenho ainda diz "EducaGames" (citado no `proximos-passos.md`).
- Entrega uma lista priorizada de propostas (problema, tela/arquivo, proposta, esforço P/M/G, impacto), com no máximo 15 itens, e no fim de 3 a 5 "ganhos rápidos" que deixam a apresentação para a banca mais forte.
- É só proposta: não altera nenhum arquivo do projeto e não gera imagem.

**m-011 (Estratégia: o que adicionar + plano + resumo)**, entrega `estrategia/m-011-tcc-plano-e-resumo.md`
- **Resumo do projeto** em 1 página: o que é, para quem, o que já faz, onde roda, números que estão nos documentos (modos, questões offline, testes, escolas), sempre dizendo de onde veio cada número.
- **Propostas do que adicionar** (de 5 a 10), pensando em aluno, professor, escola e banca do TCC. Cada uma com valor pedagógico, esforço, risco (LGPD, custo de IA, hospedagem gratuita) e se cabe antes da banca. Não repete o que o `proximos-passos.md` já registra como feito ou recusado (seção "Validação da IA que eu propus e você recusou").
- **Plano priorizado único** juntando m-009, m-010 e as propostas novas, em três blocos: "antes do push", "antes da banca" e "depois da banca", com uma ordem sugerida.
- **Como mostrar a arquitetura na banca:** de 3 a 5 pontos fortes defensáveis (ex.: fallback offline, validações medidas contra o banco, LGPD), com as provas que existem no próprio projeto.
- Fecha com o **checklist pré-push** da m-009 (resumido) e as perguntas ainda abertas para o dono.

**m-012 (Revisão final)**, entrega `revisor/m-012-tcc-revisao-final.md`
- Confere cada número e afirmação do resumo da m-011 contra o código e os documentos do anexo (ex.: 50.900 questões, mais de 1.000 testes, 38 variáveis, 19 migrations, modos de jogo).
- Confere que o plano priorizado não contradiz a m-009 nem a m-010 e que nada que exige ação externa aparece como "feito".
- Confere que nenhuma entrega da missão (m-009 a m-011) traz chave, senha, e-mail, nome real de aluno ou professor ou código de escola.
- Dá nota por critério e lista os problemas. Se encontrar erro na própria m-009, aponta também.

## Ordem

1. m-008 (este plano): o dono aprova.
2. m-009 (Revisão) e m-010 (Marca & Design) **em paralelo**: são independentes.
3. m-011 (Estratégia): depois que m-009 e m-010 forem aprovadas.
4. m-012 (Revisão final): depois da m-011.
5. Com tudo aprovado, o dono passa pelo checklist e faz o push **ele mesmo**, da pasta original.

## Riscos

- **Cópia com nomes trocados:** subir a pasta de `anexos/` quebraria o app (imports com hífen, `.gitignore` e `.github` sem o ponto). O resumo e o checklist repetem isso.
- **Segredos no histórico:** a cópia não tem `.git`. Se alguma chave já foi commitada um dia, ela continua no histórico mesmo apagada do código. Só a varredura no PC do dono resolve. Chave encontrada = trocar a chave no provedor (Supabase, Groq, Gemini, OpenRouter, Brevo), não só apagar.
- **Senhas padrão e contas de avaliação:** risco de acesso de administrador se o repositório for público e as senhas não tiverem sido trocadas.
- **Dados pessoais e documentos internos:** `proximos-passos.md` cita contas e escolas reais. Os testes têm e-mails, que parecem fictícios, mas a m-009 confere.
- **Análise sem execução:** nenhum teste é rodado. Afirmações sobre "funciona" ficam marcadas como lidas no código, não testadas.
- **Mesma sala no início e no fim:** a Revisão faz a auditoria (m-009) e a revisão final (m-012). Para compensar, a m-012 confere fatos contra o código, não contra a m-009, e aponta erros da própria auditoria.
- **Escopo grande:** com 393 arquivos, a m-009 pode amostrar. Ela deve dizer o que leu por inteiro, o que leu por amostra e o que não leu.
- **Autoria:** o repositório é de outra pessoa (Lucas). Subir sem combinar com ele pode gerar conflito no histórico ou sobrescrever trabalho.

## O que exige aprovação para agir fora do escritório

- **Subir para o GitHub** (https://github.com/LucasNishigima/EducaGame): ação externa. Nenhuma sala faz isso. Quem faz é o dono, da pasta original, depois do checklist.
- **Qualquer mudança no código do projeto**, inclusive as propostas de arquitetura, UI/UX e documentação: só como proposta em .md. Aplicar fica com o dono ou vira pedido próprio com aprovação explícita.
- **Trocar chaves ou senhas em produção** (Supabase, provedores de IA, Brevo, Render, Streamlit Cloud): só o dono.
- **Apagar ou tirar arquivos do repositório** (áudios, logos, documentos internos): decisão do dono.
