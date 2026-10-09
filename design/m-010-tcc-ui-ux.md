# m-010 · TCC (EducaGame IA): análise de UI/UX das telas Flask e Streamlit

- **Projeto:** tcc · **Plano:** m-008 (aprovado) · **Sala:** Marca & Design
- **Data:** 2026-10-09
- **Natureza:** só proposta. Nenhum arquivo do projeto foi alterado, nenhuma imagem foi gerada, nada foi executado
  (nem o app, nem os testes). Tudo o que está aqui foi **lido no código**; onde o efeito só se confirma abrindo a tela,
  está escrito "a conferir no navegador".

---

## 1. Objetivo

Dizer, tela por tela, o que atrapalha o aluno do fundamental e do médio, o professor e a impressão da banca, e propor
até 15 melhorias priorizadas (problema, tela/arquivo, proposta, esforço, impacto), mais de 3 a 5 ganhos rápidos para a
apresentação. O Flask é o frontend principal (decisão de 02/09/2026 registrada no `proximos-passos.md`: "Render é o
oficial; Streamlit é a reserva"). O Streamlit entra como comparação e só recebe as correções que não podem esperar.

## 2. Veredito em 6 linhas

1. O Flask tem uma base de design **melhor do que a média de TCC**: tokens de cor sem cor solta nos componentes, tema
   claro e escuro, contraste conferido, foco visível, ícones em SVG, aviso de carregamento global e ajuda alcançável de
   qualquer tela. Isso é defensável na banca.
2. O que falta é **cara de jogo** e **acabamento para aluno**: os modos de jogo parecem formulários iguais, a vitória e a
   derrota têm a mesma cor, a pílula da questão mostra palavra técnica ("offline", "ia"), a música do RPG toca sem botão
   para desligar.
3. A **entrada** (escola, código, login) funciona e o atrito do código é proposital (decisão registrada, respeitada aqui),
   mas abre com uma tela cheia da **logo antiga** ("EducaGames IA") por 2,85 s e não diz em que passo o aluno está.
4. No **celular** a barra de cima fixa ocupa perto de um quarto da tela e o resultado da resposta pode cair fora da vista.
5. Os **dois frontends não parecem o mesmo produto**: Flask claro, sóbrio, "apostila"; Streamlit escuro, neon, cheio de
   emoji, com nomes de modos diferentes. Pela decisão de manter o Streamlit como reserva, a proposta é corrigir só o que
   é falha (foco invisível, erro técnico na tela, modo sem porta de entrada) e alinhar o visual depois da banca.
6. A **logo** precisa ser redesenhada: grafia antiga, formato largo que não funciona pequeno, sem versão para favicon.
   Segue um brief e um prompt pronto (seção 9).

## 3. Anexos usados e o que ficou de fora

Todos em `anexos/p-003/tcc/educagame/` (cópia com nomes simplificados: `flask_app.py` virou `flask-app.py`,
`selecionar_escola.html` virou `selecionar-escola.html` etc.; cito os nomes da cópia).

**Lidos por inteiro**
- `readme.md`
- `web/templates/`: `base.html`, `selecionar-escola.html`, `codigo-escola.html`, `login.html`, `cadastro.html`,
  `home.html`, `treino.html`, `oraculo.html`, `rpg.html`, `boss-rush.html`, `escape-room.html`, `perfil.html`,
  `progresso.html`, `ajuda.html`
- `web/templates/partials/`: `options-form.html`, `result-card.html`, `ia-notice.html`, `student-context.html`,
  `student-selector.html`, `trocar-escola-link.html`, `icones.html`
- `web/static/css/flask.css` (2.144 linhas)
- `core/design-system.py`, `core/design-system-base.py`, `core/design-system-global.py`, `core/design-system-rpg.py`
- Imagens: `web/static/img/educagames-ia-logo.jpeg`, `assets/etecaracatuba.png`, `assets/deltaeducacional.jpg`

**Lidos em parte ou por busca**
- `web/templates/professor.html` (linhas 1 a 130 e busca por emoji e `role=`), `laboratorio.html` (busca)
- `core/estilos/design-system-global.css` (linhas 1 a 500 e 960 a 1.155) e `design-system-rpg.css` (linhas 1 a 130),
  mais busca por `@media`, `outline`, tamanhos de fonte
- `st/ui/home-st.py` (linhas 1 a 220 e 500 a 830), `app.py` (linhas 110 a 190), busca em todo `st/ui/` por
  `spinner`, mensagens de erro e Boss Rush
- `web/routes/home-fla.py` e `auth-fla.py` (só `trocar_escola` e `logout`), `core/origem-questao.py` (aviso de origem)
- `proximos-passos.md` (seções de capturas de tela, Render x Streamlit, código da escola, acentuação, CSS do Flask, ideias
  recusadas), para não propor de novo o que já foi decidido
- `tests/test-animacoes-css.py` e `tests/test-readme-confere-com-o-projeto.py` (só os nomes dos testes que cobrem a
  splash e a grafia do nome)

**Fora** (não precisam para UI/UX ou não abrem): `enem.html`, `guildas.html`, `privacidade.html`,
`redefinir-senha.html`, `partials/admin-panel.html`, `partials/suporte-questao.html` e o resto do `professor.html` (só
amostrados por busca); as demais telas de `st/ui/`; as rotas `web/routes/*` (fora as duas funções citadas); os três MP3
de `web/static/audio/` (a Read não toca áudio: avaliei só o código que os toca).

## 4. Método e de onde saiu cada escolha (skill ui-ux-pro-max)

Sem terminal: consultei os CSV da skill com busca. Linha = número da linha no arquivo.

| Arquivo da skill | Linha | O que tirei |
|---|---|---|
| `products.csv` | 10 (Educational App) | Estilo sugerido "Claymorphism + Micro-interactions", alternativa "Flat Design"; "Playful colors + clear hierarchy"; "Age-appropriate design" |
| `products.csv` | 104 (Flashcard & Study Tool) | "correct green + incorrect red + progress blue", "Session progress bar. Streak tracking" |
| `colors.csv` | 10 (Educational App) | Primária índigo `#4F46E5` + destaque laranja `#EA580C` ("playful indigo + energetic orange"): é a mesma dupla do app (índigo) e da logo (laranja) |
| `ui-reasoning.csv` | 10 (Educational App) | Regras `if_gamification: add-progress-animation`, `if_children: increase-playfulness`; antipadrões "Dark modes + Complex jargon" |
| `typography.csv` | 21 (DM Sans) e 72 (Nunito + DM Sans, "children education") | Confirma DM Sans, que o Flask já usa; Nunito fica como opção para títulos de jogo depois da banca |
| `styles.csv` | 9 (Accessible & Ethical) e 13 (Flat Design) | Base para manter o estilo plano atual em vez de trocar por claymorphism |
| `ux-guidelines.csv` | 3, 23, 29, 34, 38, 41, 44, 45, 46, 55, 56, 67, 81, 93, 97, 101 | Barra fixa, toque, foco, erro perto do campo e anunciado, cor sozinha, rótulos, link de pular, recuperação de erro, aviso de IA, mídia automática, foco encoberto |

**Decisão de estilo.** A skill sugere claymorphism para app educacional, mas a linha 153 do `products.csv` mostra que
esse estilo mira crianças de 2 a 8 anos. O público aqui vai do 6º ano ao 3º do médio, mais a banca, e o Flask já tem
uma identidade plana, coerente e acessível. **A identidade existente manda**; a skill só completa o que falta: uma cor de
recompensa (o laranja da logo), barras de progresso com movimento sutil e menos jargão.

**Contrastes.** Calculei pela fórmula da WCAG 2.x a partir dos HEX do código (arredondado em 0,1). Não medi a tela
renderizada.

## 5. O que já está bom (para não mexer e para defender na banca)

| O que | Onde | Por que vale citar |
|---|---|---|
| Tokens de cor, nenhum componente com cor literal | `flask.css` linhas 7 a 109 | Sistema de design de verdade, claro e escuro com as mesmas variáveis |
| Tema escuro sem piscar, segue o sistema | `base.html` linhas 8 a 19 | Detalhe de qualidade |
| Contraste do texto | `flask.css` | Texto principal sobre painel 16,6:1; texto apagado `#5F6470` sobre fundo 4,9:1 e sobre painel 5,5:1; botão 10,1:1; tema escuro, texto apagado 5,5:1 |
| Foco visível em tudo | `flask.css` linha 142 (`:focus-visible`) | Teclado funciona |
| Aviso de carregamento global e trava de duplo clique | `base.html` linhas 121 a 172, `flask.css` 2022 a 2074 | Heurística 1 de Nielsen; respeita "menos movimento"; `role="status"` para leitor de tela |
| Ajuda pesquisável em toda tela, inclusive antes do login | `base.html` rodapé, `ajuda.html` | Heurística 10; busca sem acento |
| Aviso amigável quando a questão vem do banco próprio | `core/origem-questao.py` linha 37 | Transparência sobre a IA |
| Ícones SVG no lugar de emoji, com `aria-hidden` | `partials/icones.html` | Consistência entre sistemas |
| Alternativas com área de toque grande (54 px, label inteiro clicável) | `flask.css` linhas 1260 a 1290 | Bom no celular |
| Campos com rótulo visível, botões de 48 px, texto base 16 px | `flask.css` linhas 946 a 963, 129 | Checklist de UX básico cumprido |
| Código da escola sem autocorreção no celular | `codigo-escola.html` linhas 26 a 36 | Cuidado com o aluno |

## 6. Diagnóstico por critério

### 6.1 Clareza para alunos
- **Palavra técnica na tela.** A pílula no topo da questão mostra o valor interno `_origem_geracao`, que é `offline` ou
  `ia` (`treino.html:63`, `oraculo.html:55`, `laboratorio.html:55`). O mesmo app já tem a frase boa para isso
  (`AVISO_BANCO_PROPRIO`), então a pílula contradiz o próprio aviso. Também: "liberar o RPG no Flask" (`rpg.html:21`),
  "Periodo nao informado" sem acento (`perfil.html:34`).
- **Linguagem de correção dura.** O cartão de resultado diz só "Acertou" ou "Errou" (`result-card.html:3`); o RPG diz
  "Desafio perdido". Para o fundamental, "Não foi dessa vez" com a explicação logo abaixo funciona melhor.
- **Vitória e derrota com a mesma cor.** O resultado final da Batalha e do Escape Room usa sempre a classe verde
  `result ok`, mesmo com 0% de acerto (`boss-rush.html:91`, `escape-room.html:162`).
- **Configurar antes de jogar.** Todo modo começa com 4 a 5 campos; o Escape Room soma até 6 seletores de "matéria da
  sala" (`escape-room.html:41-52`). Um aluno de 11 anos quer o botão "Começar".
- **Pontos escondidos.** O CSS tem `.score-chip` e `.avatar-chip` prontos (`flask.css:227` e `:282`), mas nenhum
  template usa: o aluno só vê os pontos entrando no Perfil.

### 6.2 Fluxo de entrada (escola, código, login)
- Ordem: lista de escolas (com splash de 2,85 s e redirecionamento automático quando há uma escola só) → código da
  escola → login → início. O atrito do código é proposital ("Código da escola — atrito de propósito", `proximos-passos.md`)
  e fica.
- **Splash com a logo antiga** em tela cheia, sobre fundo azul-marinho fixo `#071321` que vem do tema escuro antigo
  (`flask.css:454-482`, `selecionar-escola.html:19-27`). A imagem tem fundo claro, então aparece um retângulo claro sobre
  o escuro, e o desenho ainda diz "EducaGames". É a primeira coisa que a banca vê.
- **Sem indicação de passo.** As três telas não dizem "passo 1 de 3". O Streamlit até explica a sequência ("Depois vêm
  o código da escola e o seu login", `home-st.py:707`), o Flask não.
- **Textos diferentes para a mesma coisa:** no Flask, "Aluno: entre com seu e-mail cadastrado"; no Streamlit, "Aluno:
  use seu e-mail ou usuário". Botão do código: "Entrar" no Flask, "Continuar" no Streamlit.
- **Sem "Sair" na tela inicial.** O início zera o bloco `header` (`home.html:4`), onde mora o botão Sair, e a barra de
  cima não tem Sair. Em computador de laboratório compartilhado, o aluno precisa entrar num modo para achar o botão.
  "Trocar Escola" não desloga (`home-fla.py:226-229` só limpa escola e aluno).

### 6.3 Carregamento e erro
- **Carregamento no Flask: resolvido** (seção 5). No Streamlit há `st.spinner` com texto temático em todos os modos.
- **Erro com cara de aviso.** Erro de login, de código e de cadastro usam `notice warn` (barra dourada), igual a um
  aviso comum (`login.html:16`, `codigo-escola.html:14`, `cadastro.html:21`). Só o painel do professor anuncia o erro
  ao leitor de tela (`professor.html:101`, `role="alert"`). Nenhum erro aponta o campo (`aria-describedby`,
  `aria-invalid`). Senha do cadastro exige 6 caracteres, mas a tela não diz isso antes (`cadastro.html:49`).
- **Streamlit mostra a exceção crua ao usuário** em cerca de 10 lugares, por exemplo `st.warning(f"Não foi possível
  carregar o perfil: {e}")` (`app.py:164`), `st.error(f"Erro ao buscar aventuras: {e}")` (`tela-rpg-st.py:461`) e os
  "PDF indisponível: {e}" de vários modos. Na tela de escolas sem resultado, mostra o diagnóstico do Supabase em JSON
  para quem estiver na entrada (`home-st.py:612-631`). É jargão para o aluno e informação técnica à vista.

### 6.4 Acessibilidade

| Ponto | Onde | Situação |
|---|---|---|
| Música do RPG toca no primeiro clique, sem botão de pausa ou volume | `rpg.html:249-320` | Falha: WCAG 1.4.2 (controle de áudio) e `ux-guidelines.csv` linha 97. Em sala com 40 computadores, 40 trilhas ao mesmo tempo |
| Conquista bloqueada com `opacity: 0.5` | `flask.css:1607` | Descrição fica em cerca de 2,1:1 e título em 3,4:1 (precisa 4,5:1) |
| Seletor de matéria e de modo sem rótulo | `perfil.html:86`, `progresso.html:126` e `:148` | O leitor de tela lê só "caixa de combinação" |
| Emoji como ícone, lido em voz alta | `professor.html:28, 32, 39-47, 58, 69, 87, 106, 257`; `perfil.html:74` | Contradiz a regra do próprio `icones.html` |
| Textos de 11 a 11,5 px, mono, maiúsculas | `.eyebrow` 0,7rem (`flask.css:364`), `.school-card-hint`, `.table-head`, `.formula-box h3`, `.suporte-titulo`, `.admin-card-action`, `.choice-summary::after` (0,72rem); Streamlit `.edu-stat-label` 0,72rem | Abaixo de 12 px: leitura difícil para o fundamental |
| Alvos de toque abaixo de 44 px | `.theme-toggle` 36 px (`flask.css:246`); links do menu cerca de 40 px; links do rodapé cerca de 20 px de altura | A regra do escritório é 44 px |
| Sem link "Pular para o conteúdo" | `base.html` | Médio (`ux-guidelines.csv` linha 46) |
| Streamlit: foco invisível | `design-system-global.css:85-136` | `outline: none` e a mesma borda no repouso e no foco; a borda ciano a 42% dá cerca de 2,8:1 contra o campo (precisa 3:1 e precisa diferir do repouso) |
| Status só por cor | Resultado final verde mesmo na derrota | O texto existe, mas a cor contradiz o texto |

### 6.5 Celular
- **Barra de cima fixa e empilhada.** Abaixo de 760 px a `topbar` vira coluna (marca, 4 links quebrando linha, botão de
  tema) e continua `position: sticky` (`flask.css:149-161` e `1884-1900`). Pelo CSS dá cerca de 150 px fixos, perto de um
  quarto da altura de um celular comum. A conferir no navegador.
- **Resultado fora da vista.** Depois de responder, a página recarrega no topo e o cartão de resultado vem **depois** da
  questão (`treino.html:115-117`, igual nos outros modos). Em questão longa, o aluno vê a mesma pergunta sem as
  alternativas e precisa rolar para descobrir se acertou. A conferir no navegador.
- **Painel fixo do Laboratório passa por baixo da barra.** `.mode-config` é `sticky` com `top: 18px` (`flask.css:771`),
  e a barra de cima tem 60 px fixos com `z-index` maior: ao rolar no computador, o topo do painel some atrás dela
  (`ux-guidelines.csv` linha 101). A conferir no navegador.
- **Bom:** grades viram uma coluna, linhas de formulário viram uma coluna, tabelas escondem colunas e a das metas tem
  arranjo próprio (`flask.css:1876-2020`). Não vi nada que gere rolagem para o lado.

### 6.6 Consistência entre os modos e entre os dois frontends
- **Entre os modos do Flask:** consistentes demais. Treino, Oráculo, RPG, Batalha e Escape Room usam o mesmo painel,
  a mesma barra de progresso de 4 px e a mesma pílula. A cor de cada modo (`--mode-rpg`, `--mode-boss`...) só aparece
  no cartão do início e some ao entrar no modo. HP e vidas são só números (`rpg.html:62`, `boss-rush.html:45`).
- **Entre os frontends:**

| Item | Flask (principal) | Streamlit (reserva) |
|---|---|---|
| Tema | Claro "Apostila" (bege, índigo, cantos de 3 px), escuro opcional | Só escuro, gradientes neon, cantos de 8 a 24 px |
| Fontes | DM Sans + Bitter + JetBrains Mono | Source Sans 3 + Cinzel (o CSS global importa Cinzel e não usa) |
| Ícones | SVG próprio | Emoji |
| Nome do produto na barra | "EducaGame" (a grafia decidida é "EducaGame IA") | "EducaGame IA" |
| Treino | "Treino Rápido" | "Modo Treino" |
| Batalha | "Batalha contra Chefes" | "Boss Rush ENEM", e **sem cartão no início**: só abre por `?pagina=bossrush` (`home-st.py:766-791`) |
| Perfil e Progresso | Telas próprias | Os dois cartões levam à página "Jogar" (`home-st.py:784-785`); não há tela de progresso |
| Missão do dia | Não existe | Existe, mas conta as respostas **da escola inteira** (`db.buscar_logs(escola_id)`, `home-st.py:761-764`) e a barra usa uma fórmula fixa (64% para quem tem 5 respostas ou mais, `home-st.py:179`) |

  O bloco "Ajustes de paridade visual com a versão Flask/Render" (`design-system-global.css:1013`) ficou para trás: o
  Flask mudou de tema e o Streamlit não acompanhou.

### 6.7 A logo antiga
- Arquivo `web/static/img/educagames-ia-logo.jpeg`: cérebro meio circuito, controle de videogame laranja, nome
  "EducaGames IA" em degradê azul, círculo claro de fundo. Proporção larga (o próprio CSS diz cerca de 1,83:1).
- Problemas: (1) grafia antiga, contra a decisão de 09/09/2026 ("fica `EducaGame IA`"); (2) muitos detalhes finos
  (circuitos, engrenagem, gráfico) que somem abaixo de 64 px; (3) JPEG com fundo claro, sem transparência, que não vai
  sobre o tema escuro; (4) não há versão pequena: a barra usa uma letra "E" num quadrado (`base.html:46`) e o site não
  declara favicon; (5) o canto inferior direito tem um pequeno brilho de quatro pontas que **parece** a marca d'água de
  imagem gerada por IA. Se for, convém confirmar os termos de uso da ferramenta e citar a origem no TG.
- Uso hoje: só na splash. As logos das escolas (`assets/`) aparecem só nos relatórios em PDF; a da ETEC está com
  compressão visível (borrada).

## 7. Identidade usada (o que manda e o que a skill completa)

**Manda:** o tema "Apostila" do `flask.css`. Ele passa a ser a referência dos dois frontends e da logo nova.

| Papel | Claro | Escuro | Onde usar | Origem |
|---|---|---|---|---|
| Fundo | `#EFE9DC` | `#121215` | Página | `flask.css` |
| Painel | `#F9F5EC` | `#1A1A1F` | Cartões, formulários | `flask.css` |
| Texto | `#14161C` | `#F2F1EC` | Texto principal | `flask.css` |
| Texto apagado | `#5F6470` | `#8A8B96` | Apoio, legendas | `flask.css` |
| Destaque (ação) | `#33357F` | `#A9AAF2` | Botões, links, foco | `flask.css` |
| Acerto | `#1C6349` | `#6DBF97` | Resultado certo | `flask.css` |
| Erro | `#A6362C` | `#E68A80` | Resultado errado, **erro de formulário (novo uso)** | `flask.css` |
| **Recompensa (novo)** | preenchimento `#EA580C`, texto `#B7410E` | `#F59E5B` | XP ganho, conquista desbloqueada, vitória, símbolo da logo | `colors.csv` linha 10 e laranja da logo (HEX da logo aproximados a partir da imagem) |
| Cor de cada modo | `--mode-*` | `--mode-*` | Cartão do início **e agora o topo da tela do modo** | `flask.css` |

Contraste da cor nova: `#B7410E` sobre o painel 5,1:1 e sobre o fundo 4,6:1 (texto); `#EA580C` sobre o painel 3,3:1, só
para ícone, barra e texto grande; `#F59E5B` sobre o fundo escuro 8,8:1.

**Fontes:** continuam DM Sans (texto) e Bitter (títulos), as duas do Google Fonts sob licença SIL Open Font License.
Opcional depois da banca: Nunito nos títulos dos modos de jogo (`typography.csv` linha 72), também OFL.

**Regras novas:** nenhum texto abaixo de 0,8125rem (13 px); alvo de toque de 44 px; erro sempre com cor, ícone e texto;
barra de progresso de 8 px com transição de 300 ms (zerada por `prefers-reduced-motion`, que o CSS já trata).

**Nunca:** cor sozinha para dizer certo ou errado; emoji como ícone; palavra técnica para o aluno ("offline", "Flask",
"Supabase", exceção do Python); som que começa sem o aluno pedir.

## 8. Propostas priorizadas (15)

Esforço: **P** até 2 h · **M** de meio dia a 2 dias · **G** mais que isso (hipótese de quem conhece o código).
Impacto: efeito em aluno, professor e banca. Bloco: **A** antes da banca · **D** depois da banca.

| # | Problema | Tela / arquivo | Proposta | Esforço | Impacto | Bloco |
|---|---|---|---|---|---|---|
| 1 | Pílula da questão mostra "offline" / "ia" | `treino.html:63`, `oraculo.html:55`, `laboratorio.html:55` | Trocar pelo rótulo "Gerada por IA" ou "Banco EducaGame (revisado)" | P | Alto | A |
| 2 | Música do RPG sem controle | `rpg.html:249-320` | Botão "Música: desligada/ligada" com `aria-pressed`, começa **desligada**, lembra a escolha | P | Alto | A |
| 3 | Entrada abre com a logo antiga em tela cheia e não diz o passo | `selecionar-escola.html:19-72`, `flask.css:454-482`, `codigo-escola.html`, `login.html` | Tirar a splash (ou trocar pelo nome "EducaGame IA" em texto até a logo nova sair) e pôr "Passo 1 de 3 · Escola", "Passo 2 de 3 · Código", "Passo 3 de 3 · Entrar" | P | Alto | A |
| 4 | Sem "Sair" no início; pontos escondidos | `base.html:42-66`, `home.html:4`, `.score-chip` | "Sair" na barra de cima em toda tela logada; chip "120 pontos" ao lado (o CSS já existe) | P (Sair) / M (pontos) | Alto | A |
| 5 | Resultado cai abaixo da questão, fora da vista no celular | `partials/result-card.html`, ordem em `treino.html`, `oraculo.html`, `boss-rush.html`, `escape-room.html`, `rpg.html` | Mostrar o resultado **antes** da questão já respondida, ou levar a página até `#resultado` com foco nele | P | Alto | A |
| 6 | Logo antiga, sem versão pequena nem favicon | `img/educagames-ia-logo.jpeg`, `base.html:46` | Logo nova pelo brief da seção 9; favicon; símbolo no lugar do "E" | M | Alto | A |
| 7 | Vitória e derrota com a mesma cor; "Errou" seco | `boss-rush.html:91`, `escape-room.html:162`, `result-card.html:3`, `rpg.html:75` | Três faixas por aproveitamento, com cor, ícone e frase; "Acertou!" / "Não foi dessa vez"; laranja de recompensa no XP | P | Médio-alto | A |
| 8 | A tela do modo não tem cara de jogo | `flask.css` (`.section-head`, `.progress-bar`, `.stat-card`), `rpg.html:61-71`, `boss-rush.html:45` | Levar a cor do modo para o topo da tela; HP como barra com texto "HP 70 de 100"; vidas como 3 corações SVG com texto "2 de 3 vidas"; barra de 8 px | M | Alto | A |
| 9 | Erro igual a aviso, não anunciado nem ligado ao campo | `login.html:16`, `codigo-escola.html:14`, `cadastro.html:21`, `flask.css:1039-1056` | Classe `notice erro` (cor de erro, ícone, "Não deu certo:"), `role="alert"`, `aria-invalid` e `aria-describedby` no campo; dica "mínimo de 6 caracteres" no cadastro | P | Médio | A |
| 10 | Seletores sem rótulo, textos de desenvolvedor, nome do produto | `perfil.html:34, 86`, `progresso.html:126, 148`, `rpg.html:21`, `base.html:47`, `ajuda.html:2` | Rótulo "Ver a matéria" / "Ver o modo"; textos revistos; "EducaGame IA" na barra e nos títulos; link "Pular para o conteúdo" | P | Médio | A |
| 11 | Alvos pequenos e barra fixa pesada no celular | `flask.css:149-161, 198-208, 246-258, 771, 1884-1900, 2081-2094` | Botão de tema 44×44; links do menu e do rodapé com 44 px de altura; no celular, barra não fixa e em duas linhas (marca + tema + Sair; menu em 4 colunas); `.mode-config` com `top: 76px` | P | Médio | A |
| 12 | Textos de 11 px | `flask.css` (`.eyebrow`, `.school-card-hint`, `.table-head`, `.suporte-titulo`, `.formula-box h3`, `.admin-card-action`, `.choice-summary::after`, `.profile-score span`) | Piso de 0,8125rem (13 px) e espaçamento de letras menor | P | Médio | A |
| 13 | Emoji no painel do professor e nas conquistas; conquista bloqueada ilegível | `professor.html` (linhas na 6.4), `perfil.html:74`, `flask.css:1607` | Ícones SVG de `icones.html` (criar análises, matrícula, ranking, metas, configurações); conquista bloqueada com texto normal, ícone cinza e selo "Bloqueada" | M | Médio | D |
| 14 | Muitos campos antes de jogar | `treino.html:22-51`, `oraculo.html`, `escape-room.html:41-52`, `boss-rush.html` | Botão principal "Começar agora" com padrão (Médio, 5 questões); "Personalizar" num `<details>`; matérias por sala do Escape Room num `<details>` opcional | M | Médio | D |
| 15 | Streamlit: foco invisível, exceção crua, Batalha sem porta, cartões no lugar errado, missão do dia com dado da escola | `design-system-global.css:85-136`, `app.py:164`, `tela-rpg-st.py:461`, `professor-panel-st.py:50`, `home-st.py:178-201, 612-631, 761-791` | Só o mínimo: foco de 2 px sólido; mensagem amigável com o detalhe no log; cartão da Batalha; "Meu Progresso" leva ao Perfil; missão do dia com as respostas do aluno, ou sem barra. Alinhar o tema ao "Apostila" fica para depois (G) | M | Médio (alto se o Streamlit for mostrado) | D |

### Detalhes e como conferir

1. **Pílula de origem.** O rótulo vira um filtro de template (`origem_label`), como já se faz com `dificuldade_label` e
   `materia_label`. "Gerada por IA" segue `ux-guidelines.csv` linha 93 (conteúdo de IA deve ser identificado) e
   transforma a cascata com banco offline num ponto forte **visível**. Conferir: gerar questão com e sem chave de IA.
2. **Som do RPG.** Hoje o script toca no primeiro clique em qualquer lugar da tela. Proposta: botão fixo no topo do
   painel do RPG, texto visível ("Música desligada"), 44 px, estado salvo no `localStorage` (já usado para a faixa).
   Conferir: abrir o RPG em duas abas, clicar, nada toca até ligar.
3. **Entrada.** Os testes `test-animacoes-css.py` e `test-tela-selecionar-escola.py` protegem a splash contra a "tela
   preta" que já aconteceu. Ao tirar a splash, a garantia continua (a lista aparece sem depender de animação) e os testes
   precisam ser ajustados junto. O redirecionamento automático com uma escola só pode continuar, sem splash, com a frase
   "Abrindo a sua escola..." por 1 s e um link "Escolher outra escola".
4. **Sair e pontos.** O formulário de Sair com CSRF já existe em `base.html:72-74`; basta levar para `topbar-meta`. Os
   pontos precisam chegar a toda tela (por exemplo, um `context_processor` lendo o total do aluno da sessão): por isso M.
5. **Resultado visível.** O mais simples: quando há `resultado`, renderizar o `result_card` logo depois do `section-head`
   e a questão respondida embaixo, recolhida num `<details>` "Ver a questão de novo". Conferir no Chrome com a tela de
   360×740.
6. **Logo.** Ver seção 9. Aplicar: símbolo em SVG no lugar do "E" (`brand-mark`), favicon 32 e 16 px declarado no
   `base.html`, logo horizontal no topo da tela de escolher escola, versão monocromática nos PDFs ao lado da logo da escola.
7. **Fim de partida.** Faixas: 70% ou mais "Mandou bem!" (verde + troféu), de 40% a 69% "Bom caminho" (laranja de
   recompensa + estrela), abaixo de 40% "Vamos treinar mais" (neutro + seta para "Treinar os erros"). Nunca vermelho
   para o resultado final: vermelho fica para a questão errada.
8. **Cara de jogo.** Uma classe por modo no `<main>` (`{% block modo %}`) define `--mode-cor` e o CSS pinta uma barra de
   4 px no topo do `section-head` e o `eyebrow` com ela. Barras com `transition: width 300ms` (`ui-reasoning.csv`
   linha 10, `add-progress-animation`). Corações e barra sempre com o número em texto (`ux-guidelines.csv` linha 38).
9. **Erros.** Já existe a cor `--bad`; falta a classe. Exemplo de frase: "Não deu certo: o código não confere. Confira no
   papel que o professor entregou." (erro com caminho de volta, `ux-guidelines.csv` linha 81).
10. **Textos.** Ajustar junto com `tests/test-acentuacao-das-mensagens.py` e o teste de grafia do nome
    (`test-readme-confere-com-o-projeto.py`), que já cobram essas regras.
11. **Celular.** Conferir com Tab e no modo dispositivo do Chrome. Medir antes e depois com o Lighthouse (gratuito, já
    vem no Chrome) e guardar os números para o TG.
12. **Textos pequenos.** Só tamanho e `letter-spacing`; não muda layout.
13. **Emoji.** `icones.html` já tem o padrão; são 5 ou 6 desenhos novos de 24×24.
14. **Começar rápido.** O formulário completo continua lá para o professor e para quem quer escolher.
15. **Streamlit.** Respeita a decisão "refatoração só de aparência das telas `st/ui/` deixa de ser prioridade": aqui só
    entra o que é falha. Se a banca for ver o Streamlit, adiantar os itens de foco, exceção e Batalha.

## 9. Ganhos rápidos para a banca (5, todos esforço P)

1. **Entrada limpa** (proposta 3): sem a logo antiga em tela cheia, com "Passo 1 de 3". É a primeira impressão.
2. **Pílula "Gerada por IA" / "Banco EducaGame (revisado)"** (proposta 1): troca jargão por um argumento da banca. Dá
   para mostrar ao vivo a IA falhando e o jogo continuando.
3. **Música só quando o aluno liga** (proposta 2): evita a trilha disparando no meio da apresentação.
4. **Resultado à vista e com linguagem de jogo** (propostas 5 e 7): o momento "acertei / não foi dessa vez" é o que
   mostra que o sistema ensina, junto com o feedback pedagógico que já existe.
5. **Sair na barra de cima** (proposta 4, parte P): mostra cuidado com computador compartilhado e LGPD.

Depois de aplicar, refazer as capturas `07c`, `08c` e `09b` citadas no `proximos-passos.md` (as 30 capturas existentes
mostram a pílula "offline" e a splash antiga) e guardar a nota do Lighthouse de antes e de depois.

## 10. Brief da logo nova (proposta; nenhuma imagem foi gerada)

**Objetivo:** marca "EducaGame IA" reconhecível de 16 px (aba do navegador) a 1200 px (capa do TG), coerente com o tema
"Apostila".

**Manter:** a ideia de aprender + jogar (cérebro + controle) e a dupla azul/índigo com laranja.

**Mudar:** nome certo "EducaGame IA"; desenho plano em 2 cores, sem degradê, sem círculo de fundo e sem os detalhes
finos (circuitos, engrenagem, gráfico); símbolo que cabe num quadrado.

**Composição sugerida:** contorno simples de um cérebro visto de lado, em traço grosso índigo `#33357F`, com o controle
laranja `#EA580C` encaixado na metade de baixo, os dois botões do controle viram dois pontos. Ao lado, "EducaGame" em
Bitter 600, índigo, e "IA" em DM Sans 700 num selo laranja (texto claro `#FBF8F1` sobre `#B7410E`, 5,3:1 aproximado;
conferir na arte final).

**Versões e medidas:**
- Horizontal (símbolo + nome): SVG; PNG 1200×400 com fundo transparente
- Só o símbolo: SVG; PNG 512×512; favicon 32×32 e 16×16
- Cartão para link compartilhado: 1200×630
- Monocromática (índigo e branco) para PDF e impressão; negativa para o tema escuro (`#A9AAF2` + `#F59E5B`)

**Nunca:** esticar, girar, pôr sobre foto sem faixa sólida, recolorir fora da paleta, colocar junto das logos das escolas
sem autorização delas.

**Como produzir sem custo:** o prompt abaixo serve para **explorar ideias** numa ferramenta de imagem gratuita que o
dono escolher. Logo feita por IA sai sem vetor e com texto falho (a skill `image` diz que logo deve ser desenhada); o
caminho é escolher a ideia e redesenhar em vetor no Inkscape ou no Figma (gratuitos), digitando o nome com as fontes.

**Prompt pronto (em inglês, porque as ferramentas respondem melhor):**

```
Flat vector logo symbol for an educational game platform. A simple side-view outline of a human brain
drawn with a thick, uniform stroke in deep indigo (#33357F); the lower half of the brain merges into a
rounded game controller filled with orange (#EA580C), its two buttons shown as two small solid dots.
Only two colors, no gradients, no shadows, no circuit lines, no gears, no background circle.
Bold, friendly, geometric shapes that remain readable at 16x16 pixels. Centered on a plain white
background, square 1:1 composition, generous margin, no text, no watermark.
```

Variação para o tema escuro: trocar `#33357F` por `#A9AAF2`, `#EA580C` por `#F59E5B` e o fundo por `#121215`.

**Texto alternativo:** na barra e nas telas de entrada, `alt="EducaGame IA"`; na splash (se ficar), a imagem é
decorativa e continua com `alt=""` e `aria-hidden="true"`, como já está.

## 11. Achados fora de UI que passo para a m-009 (Revisão)

- **Batalha contra Chefes: a assinatura da questão está fora do formulário.** O `<input type="hidden"
  name="assinatura_questao">` vem antes do `<form>` (`boss-rush.html:59-60`), então não é enviado. A proteção do
  "achado 3.4" do QA (página velha reenviada pontuada contra a questão seguinte) parece não valer nesse modo. Lido no
  código; a Revisão confere na rota.
- **Streamlit mostra exceção e diagnóstico na tela** (seção 6.3): além de UX, é informação técnica exposta.
- **Missão do dia do Streamlit** usa as respostas da escola inteira para um aluno (seção 6.6).

## 12. Checklist de UX (ficha do Designer)

| Item | Flask hoje | Streamlit hoje | Com as propostas |
|---|---|---|---|
| Contraste 4,5:1 | Sim, menos conquista bloqueada | Sim no texto; foco abaixo de 3:1 | Sim (13 e 15) |
| Alvos de toque de 44 px | Quase: tema 36 px, menu cerca de 40, rodapé cerca de 20 | Botões do Streamlit, não medi | Sim (11) |
| Rótulos visíveis | Sim, menos 3 seletores | Sim (componentes do Streamlit) | Sim (10) |
| Texto base de 16 px | Sim; rótulos de 11 px | Sim; rótulos de 11,5 px | Sim, piso de 13 px (12) |
| Sem rolagem para o lado | Sim (pelo CSS) | Não conferido | Sim |
| Estado de carregando | Sim, global | Sim, `st.spinner` | Sim |
| Estado de erro | Existe, mas igual a aviso e não anunciado | Existe, com exceção crua | Sim (9 e 15) |
| Sistema de design com a origem de cada escolha | Seções 4 e 7 | Seções 4 e 7 | Sim |

`references/pro-rules.md` da skill não foi aplicado: ele é para app nativo (iOS, Android), e as duas telas são web.

## 13. Perguntas para o dono (sigo com a hipótese entre parênteses)

1. A banca vai ver o Streamlit ou só o Flask? (Hipótese: só o Flask, como diz o TG; por isso a proposta 15 ficou para
   depois.)
2. A logo atual foi feita numa ferramenta de IA? Qual? (Hipótese: sim, pelo brilho no canto; confirmar os termos e citar
   no TG.)
3. Quem desenha a logo nova: alguém do grupo, ou é para usar o prompt e redesenhar no Inkscape/Figma? (Hipótese: o
   grupo, com o prompt.)
4. A música do RPG pode começar desligada? (Hipótese: sim, é o padrão mais seguro para sala de aula.)
5. As escolas autorizam as logos delas no repositório público e nas telas? (Hipótese: só nos PDFs, como hoje; a m-009
   trata a licença.)

## 14. Pendências [PREENCHER]

- [PREENCHER] Logo nova em vetor (SVG) e favicon, depois de escolhida a ideia.
- [PREENCHER] Prints novos depois dos ganhos rápidos (substituir os que mostram "offline" e a splash antiga).
- [PREENCHER] Nota do Lighthouse (acessibilidade) antes e depois, no Flask, para o TG.
- [PREENCHER] Logos das escolas em resolução melhor (a da ETEC está borrada), se as escolas autorizarem.
- Aplicar qualquer proposta no código depende da aprovação do dono e é feito por ele, na pasta original do projeto.
