# m-007: revisão do alinhamento das placas (nomes x janelas)

- **Entrega revisada:** m-006 (Marca & Design): `design/m-006-alinhamento-dos-nomes-e-janelas-placas.md` e o código
  alterado em `painel/src/estilo.css` (linhas 149-168 e 742-771) e `painel/src/componentes/Escritorio.jsx` (linhas 107-108)
- **Plano:** m-005 (aprovado) · **Briefing:** `projetos/alinhamento-dos-nomes-e-janelas.md`
- **Anexo usado:** `anexos/p-002/image.png` (print do "antes"; não foi alterado)
- **Data:** 2026-09-29
- **Código:** só lido, nada foi alterado nesta revisão.

## Veredito

**Pode ir para aprovação.** Refiz as contas sala por sala e largura por largura. Em nenhuma largura a placa cruza a janela,
a decoração da parede, os troféus ou o relógio. A placa fica presa entre `left` e `right` = reserva, e cada reserva é maior que
o elemento que ela protege, com pelo menos 6px de folga. Não achei problema GRAVE. Há 3 MÉDIOS, que pedem uma decisão sua
(troféus e relógio somem em mais larguras que o necessário, e a letra diminui também em tela cheia), e alguns erros de texto
na descrição do "antes" da m-006.

| Eixo | Nota | Por quê |
|---|---|---|
| Precisão | 4 | O código e as 170 células da tabela de letras batem com as minhas contas. Mas a m-006 erra duas faixas do "antes" (relógio e placa cortada) e usa "por dentro" com dois sentidos. |
| Completude | 4 | Cumpre o critério: 14 salas, todas as larguras, antes e depois de cada regra, arquivos, build. Só que a letra também diminui em tela cheia, e o critério aceitava diminuir só em "telas estreitas". |
| Clareza | 4 | As tabelas são boas. A confusão está em "por dentro": nos limites 190, 390 e 480 é a largura útil (sem o padding de 10px de cada lado), e na tabela é a largura sem a borda. |
| Acionabilidade | 5 | Traz o passo do build (`npm run painel`), como desfazer, o que conferir e perguntas objetivas. |
| Concisão | 4 | É longa, mas cada tabela tem uso. A lista das diretrizes da skill poderia ser mais curta. |

## Contas refeitas

### Base (lida no CSS)

- Sala: `box-sizing: border-box`, borda de 6px e padding de 52px/10px/12px, `container-type: inline-size`.
  **W** = largura sem a borda (é onde a placa, a janela e a decoração se posicionam) = coluna − 12.
  **C** = largura que o `@container` e o `100cqi` medem = largura útil sem o padding = W − 20.
- Planta com o painel lateral (tela de 1101 a 1500): planta = mín(tela, 1500) − 18×2 − 360 − 18 = mín(tela, 1500) − 414.
  Sem o painel lateral: tela − 36. Com 1 coluna: tela − 32.
- 4 colunas: coluna = (planta − 54) ÷ 4. Diretoria e Memória ocupam 2 colunas: 2 × coluna + 18.
- Placa: largura = letras × fonte + 2 × (10/9) × fonte + 6 (borda) = fonte × (letras + 2,222) + 6.
  O CSS usa fonte = (C + 12 − 2 × reserva) ÷ (letras + 2,23), limitada entre 6 e 9. Com C + 12 = W − 8, isso é o
  "(A − 8) ÷ (letras + 2,23)" da m-006 (A = W − 2 × reserva). Sobram 2px e um pouco de arredondamento. ✔

### Posições na parede (px a partir da borda de dentro)

| Elemento | Conta | Faixa | Reserva que o protege | Folga |
|---|---|---|---|---|
| Janela da esquerda | 12 + 46 | 12 a 58 | 64 | 6 ✔ |
| Janela da direita (Diretoria) | espelho | W−58 a W−12 | 64 / 148 / 194 | 6 ou mais ✔ |
| Decoração da parede, a maior (quadro e painel de anúncios, 40) | 12 + 40 | W−52 a W−12 | 64 | 12 ✔ |
| Nuvem do Git (36), estante (32), mural, gráfico e cartela (38), prancheta (26) | 12 + d | até W−50 | 64 | 14 ou mais ✔ |
| Troféus (5, o pior caso) | 74 + (8 + 18×5 + 4×4) = 74 + 114 | 74 a 188 | 194 | 6 ✔ |
| Relógio "HH:MM" | 5 × 10 + 12 de padding + 6 de borda = 68; right 74 | W−142 a W−74 | 148 e 194 | 6 ✔ |
| Interruptor do Git | top 54 | abaixo da parede (0 a 42) | não disputa com a placa | ✔ |

- Altura da placa em 9px: 5 + 10,8 + 4 + 6 = 25,8 (antes 26). O texto fica a 0,1px do lugar de antes. ✔
- Em 2 linhas de 6px: 5 + 2 × 7,2 + 4 + 6 = 29,4 → vai de 9 a 38,4, mais 3 de sombra = 41,4. Cabe na parede de 42. ✔
- Largura da placa em 9px (9 × letras + 26): Você e Copy 62 · Social e Vendas 80 · Revisão e Memória 89 · Recepção e Pesquisa 98 ·
  Diretoria 107 · Estratégia 116 · Git & GitHub 134 · Marca & Design 152 · Sala de Reunião e Tráfego & Mídia 161. ✔
  Letras contadas nos nomes do `painel/src/dados.js` (15, 9, 4, 8, 8, 10, 14, 4, 6, 15, 6, 7, 12, 7). ✔

### Largura por largura (C = W − 20 decide o que some)

| Tela | Sala comum: W · C | Janela (some se C ≤ 190) | Reserva · A | Diretoria: W · C | O que aparece na Diretoria | Reserva · A | m-006 |
|---|---|---|---|---|---|---|---|
| 1500+ | 246 · 226 | aparece | 64 · 118 | 522 · 502 | troféus e relógio | 194 · 134 | ✔ |
| 1440 | 231 · 211 | aparece | 64 · 103 | 492 · 472 | só o relógio | 148 · 196 | ✔ |
| 1366 | 212,5 · 192,5 | aparece | 64 · 84,5 | 455 · 435 | só o relógio | 148 · 159 | ✔ |
| 1280 | 191 · 171 | some | 12 · 167 | 412 · 392 | só o relógio | 148 · 116 | ✔ |
| 1101 | 146,25 · 126,25 | some | 12 · 122,25 | 322,5 · 302,5 | nenhum dos dois | 64 · 194,5 | ✔ |
| 1100 | 240,5 · 220,5 | aparece | 64 · 112,5 | 511 · 491 | troféus e relógio | 194 · 123 | ✔ |
| 1024 | 221,5 · 201,5 | aparece | 64 · 93,5 | 473 · 453 | só o relógio | 148 · 177 | ✔ |
| 900 | 190,5 · 170,5 | some | 12 · 166,5 | 411 · 391 | só o relógio | 148 · 115 | ✔ |
| 761 | 155,75 · 135,75 | some | 12 · 131,75 | 341,5 · 321,5 | nenhum dos dois | 64 · 213,5 | ✔ |
| 760 | 341 · 321 | aparece | 64 · 213 | 712 · 692 | nenhum (`@media`) | 64 · 584 | ✔ |
| 600 | 261 · 241 | aparece | 64 · 133 | 552 | nenhum | 64 · 424 | ✔ |
| 500 | 211 · 191 | aparece | 64 · 83 | 452 | nenhum | 64 · 324 | ✔ |
| 441 | 181,5 · 161,5 | some | 12 · 157,5 | 393 | nenhum | 64 · 265 | ✔ |
| 440 / 360 / 320 | 396 / 316 / 276 | aparece | 64 · 268 / 188 / 148 | igual às outras | nenhum | 64 | ✔ |

**Diretoria sempre em 9px**, também entre os pontos da tabela: com troféus, C > 480 → A > 112 → fonte ≥ 9,26. Só com o
relógio, C > 390 → A > 114 → fonte ≥ 9,44. Os limites 477 e 385 que a m-006 cita são C, e estão certos. ✔

**Pior caso das salas comuns com janela:** C logo acima de 190 → W ≈ 210 → A ≈ 82 (acontece em cerca de 1357px com o painel
lateral, 979px sem ele e 499px em 2 colunas; a m-006 diz 83, em 500px). Em 6px cabem 10 letras por linha (82 − 6 − 13,3 = 62,7).
A linha mais longa é "Tráfego &", com 9 letras. ✔

### Tamanho da letra (refiz as 14 salas × 16 larguras)

Todas as células da m-006 batem, com diferença menor que 0,05px. Exemplos da conta:
- 1500+: Reunião e Tráfego 110 ÷ 17,23 = 6,38 · Marca & Design 110 ÷ 16,23 = 6,78 · Git 110 ÷ 14,23 = 7,73 · Estratégia 8,99 (a m-006
  arredonda para 9; a placa mede 115,9 de 118 livres).
- 1440: Marca & Design dá 5,85 → vai para 6 → a placa mediria 103,3 com 103 livres → 2 linhas (passa por 0,3px). ✔
- 1024: Git 85,5 ÷ 14,23 = 6,01 → a placa mede 91,4 de 93,5 → 1 linha. ✔
- 500: Estratégia 75 ÷ 12,23 = 6,13 → 80,9 de 83 ✔ · Revisão 8,13 ✔ · Recepção e Pesquisa 7,33 ✔.

### O "antes" (conferido contra o print)

- O print tem o layout de 1500px ou mais: a janela mede cerca de 28px no print e 46px no CSS (escala de uns 0,6), e a sala
  medida no print volta para a coluna de 258px. Com W = 246, a placa de 161 começa em 42,5, **15px por cima da janela** (Reunião
  e Tráfego). Marca & Design começa em 47 (11px por cima). Git começa em 56 (2px por cima). Bate com o print e com a m-006. ✔
- 7 salas por cima da janela em 1366 (placa > 96,5 com W = 212,5): Recepção, Pesquisa, Estratégia, Git, Marca & Design, Reunião e
  Tráfego. ✔
- **Relógio por baixo da placa (antes): a m-006 erra a faixa.** Há sobreposição quando W/2 + 53,5 > W − 142, ou seja,
  W < 391 (C < 371). Isso dá telas de **1101 a 1237** e de **761 a 859**, e não 1101-1276 e 761-898 como está escrito.
- **Placa mais larga que a sala (antes): a m-006 erra a faixa.** Isso só acontece com W < 161, ou seja, telas de **1101 a 1159**
  (Reunião e Tráfego) e de **1101 a 1123** (Marca & Design). Em 1280, W = 191 e a placa de 161 cabia.
- Troféus antes (C ≤ 420 → até 1336 com o painel lateral e até 958 sem) e agora (C ≤ 480 → até 1456 e até 1078): ✔

### Nada além do alinhamento mudou?

Não consigo rodar `git diff` nesta revisão. Comparei o `painel/src` com o build antigo (`painel/dist/assets/index-BVxTxxb-.css`
e `index-D-R5r2eD.js`, que ainda não foram gerados de novo) e com os blocos "Antes" da m-006:
- Continuam iguais ao build antigo: `.sala` (borda, padding, parede de 42px, `overflow`), `.sala::after` (noite), `.janela`,
  `.janela.e/.d`, `.deco`, `.deco.parede` e os tamanhos de todas as decorações, `.trofeus`, `.relogio`, `.tapete`, `.postos`,
  `.deco-planta`, `.interruptor-parede`, `.corpo`, `.planta` e os `@media` de 1100, 760 e 440 (a não ser a linha nova da placa). ✔
- A placa antiga no build tem as mesmas cor, fundo, borda, sombra, `z-index: 3` e `top: 9px` de hoje. ✔
- No JSX, só a linha da placa ganhou `style={{ '--letras': … }}` e um comentário. O clique, as linhas animadas, a fase do dia e
  os textos são iguais aos do build (conferi "Sem reunião agora", "esperando lá fora", "salva sozinho" e o `Math.min(5, …)` dos
  troféus). O React não põe "px" em variável CSS com número, então `--letras: 15` chega certo à conta. ✔
- O git status só mostra `estilo.css`, `Escritorio.jsx` e `estado.json` alterados. O `painel/dist/` e o anexo não foram tocados. ✔
- **Mudou além do alinhamento, mas está documentado e segue o plano:** (1) os troféus somem também em 1337-1456 e 959-1078;
  (2) o relógio some em 1101-1276 e 761-898; (3) a letra das placas longas diminui (6 a 8,8px), inclusive em tela cheia.
  Veja os problemas MÉDIOS.

## Fontes conferidas

| Fonte | Confirma? |
|---|---|
| `.claude/skills/ui-ux-pro-max/data/ux-guidelines.csv` linha 16 (*Z-Index Management*), 17 (*Overflow Hidden*), 111 (*Heading Line Balance*), 112 (*Long Token Wrapping*: `overflow-wrap: anywhere`), 114 (*Essential Text Truncation*, crítica), 117 (*Compact Label Overflow*) | sim. Um detalhe: a linha 117 diz para **não** deixar o rótulo quebrar em 2 linhas. A m-006 reconhece isso e usa a 114 (crítica) para justificar a quebra. É uma leitura razoável. |
| `painel/src/dados.js` (nomes das 14 salas) | sim, as contagens de letras batem |
| `painel/dist/assets/*.css` e `*.js` (o "antes" no build) | sim, os blocos "Antes" da m-006 batem com o build |
| [Font Library: Press Start 2P](https://fontlibrary.org/en/font/press-start-2p) | sim: fonte monoespaçada, com Western European (tem as minúsculas acentuadas do português) |
| [Google Fonts: Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P) | a página não abriu para leitura. A busca diz que a fonte funciona melhor em 8px, 16px e outros múltiplos de 8. Não achei fonte que confirme "1em por letra"; tomo como hipótese. Se estiver errada, o arredondamento só pode fazer o nome quebrar em 2 linhas mais cedo, e a placa continua sem cruzar nada. |

## Problemas

- **[MÉDIO]** m-006, "Troféus da Diretoria… somem também em 1337 a 1456 e em 959 a 1078" · A reserva de 194px é para 5 troféus,
  mas hoje você tem 1. Com 1 ou 2 troféus, eles terminam em 100 ou 122px, abaixo da reserva de 148 que o relógio já pede. Ou seja,
  nas telas comuns de notebook (1366 e 1440) os troféus somem sem precisar. · **Correção:** só esconder os troféus com C ≤ 480
  quando houver 3 ou mais (por exemplo, com uma classe pela quantidade no `Escritorio.jsx`, ou `.trofeus:has(i:nth-child(3))`),
  e só usar a reserva de 194 nesse caso. Com 1 ou 2 troféus, eles ficam visíveis até C = 390, mais que antes (420).
- **[MÉDIO]** m-006, "Relógio… é o único caso novo. Nessas larguras ele ficava por baixo da placa" (1101-1276 e 761-898) · A conta
  mostra que ele só ficava por baixo em 1101-1237 e 761-859. Em **1238-1276 e 860-898**, o relógio passa a sumir sem nunca ter
  colidido: some porque a regra escolhe manter a placa da Diretoria em 9px. · **Correção:** acertar o texto. Se você quiser o
  relógio nessas faixas, baixar o limite de `@container (max-width: 390px)` para 370px: aí a placa da Diretoria encolhe para
  7,7 a 9px nessa faixa, ainda sem cruzar nada.
- **[MÉDIO]** Critério da m-005 ("nenhuma mudança… de fonte, fora um ajuste de tamanho em telas estreitas") · Em tela cheia (1500px
  ou mais, que é o layout do print), Reunião e Tráfego ficam em 6,4px, Marca & Design em 6,8px e Git em 7,7px, contra 9px nas
  outras salas. Em 1440 e 1366, essas placas ficam em 2 linhas. Com a janela mantida e a placa centralizada, não há outro jeito
  (em 1500+ só cabe em 9px nome de até 10 letras). · **Correção:** nenhuma no código. Decida pela pergunta 1 e pela 3 da m-006:
  aceitar como está, ou encurtar os nomes ("Reunião", "Tráfego", "Design", "GitHub" ficam em 9px em tela cheia). Encurtar nome
  muda texto do painel, então só com o seu ok.
- **[LEVE]** m-006, "Troféus… Diretoria de até 480px por dentro", "relógio… até 390px por dentro", "janela… sala com até 190px por
  dentro" · Nesses três casos, "por dentro" é a largura útil C = W − 20, e não o W da tabela (o mesmo termo com outro sentido).
  Os números de tela da m-006 estão certos. · **Correção:** escrever "largura útil (sem o padding)" nesses três pontos, ou dar os
  limites em W: 210, 410 e 500.
- **[LEVE]** m-006, "Entre 1101 e 1280px a placa… fica mais larga que a sala" e o checklist "Antes ela era cortada entre 1101 e
  1280px" · Na conta, é de 1101 a 1159 (Reunião e Tráfego) e de 1101 a 1123 (Marca & Design). · **Correção:** acertar as faixas.
- **[LEVE]** m-006, tabela de 1366px · O Windows mostra a barra de rolagem (a página rola), e ela tira uns 17px. Uma tela de 1366
  vira 1349 úteis: W = 208,25, C = 188,25, a **janela some** e todas as placas voltam a 9px. Não vai aparecer "2 linhas" como na
  tabela. A garantia continua valendo. · **Correção:** avisar isso na tabela, para você não estranhar na tela.
- **[LEVE]** Tamanhos quebrados (6,4px, 6,8px, 7,7px) numa fonte de pixel art que funciona melhor em múltiplos de 8 · A letra pode
  ficar um pouco borrada. A de 9px já era um tamanho quebrado. · **Correção:** conferir na tela. Se incomodar, trocar o
  `clamp` por degraus (9, 8, 7, 6) é uma segunda rodada, só se você pedir.
- **[LEVE]** Nomes futuros · Um nome com uma palavra de mais de 10 letras mais duas outras palavras (ex.: "Atendimento ao
  Cliente") iria para 3 linhas em 6px, com a palavra partida ("Atendiment/o"). A placa desceria até 45,6px, passando da parede
  (42), mas sem chegar aos personagens (52). Nenhum nome atual chega nisso. · **Correção:** nenhuma agora. Ao criar uma sala,
  use até 2 palavras de até 10 letras.
- **[LEVE]** Briefing, "Site / redes: [PREENCHER]" · Não se aplica a este ajuste interno. · **Correção:** trocar por "não se aplica".

**Ações externas:** nenhuma foi feita. `npm run painel` gera o build dentro do escritório, então não é ação externa. Publicar o
painel online (Vercel) está marcado na m-006 como decisão sua. ✔
**Riscos legais ou de reputação:** nenhum. É um ajuste interno, sem dados pessoais nem marca de terceiros.

## O que você deve olhar na tela depois de rodar `npm run painel`

1. Rode `npm run painel` na raiz, abra o painel (`npm start`) e recarregue com **Ctrl+F5**. Sem o build novo, nada muda.
2. **Tela cheia (a do print):** em Sala de Reunião, Marca & Design, Tráfego & Mídia e Git & GitHub, a placa fica menor e centrada,
   sem encostar na janela nem na decoração da direita. Veja se a letra pequena (6,4 a 7,7px) está legível e nítida.
3. **Mesma fileira:** o topo de todas as placas fica na mesma linha (9px). O texto das placas menores fica um pouco mais alto
   que o das de 9px, e as de 2 linhas ficam 3,6px mais altas. Decida se isso incomoda.
4. **Diretoria em tela cheia:** a placa em 9px, o troféu e o relógio visíveis, nada encostando.
5. **Diminua a janela do navegador aos poucos** (ou F12 → modo responsivo com 1440, 1366, 1280, 1100, 1024, 900, 760, 500, 440 e
   360px):
   - abaixo de cerca de 1456px, o troféu da Diretoria some (ver o MÉDIO 1);
   - entre cerca de 1276 e 1101px, o relógio some (ver o MÉDIO 2);
   - onde aparecerem 2 linhas, a placa não passa da faixa escura da parede nem encosta no personagem;
   - em nenhuma largura a placa passa por cima da janela, da decoração ou do relógio.
6. **Zoom do navegador em 90% e 110%:** o zoom muda as larguras, e a placa deve continuar entre a janela e a decoração.
7. **À noite** (ou pela fase do dia): a placa continua por cima do escurecimento, como antes.
8. **Clique** em cada sala: a ficha certa abre, e as linhas tracejadas continuam andando.
9. **Painel online:** só muda depois que o build novo for para o GitHub e o Vercel publicar. Isso é decisão sua.

## Perguntas para você (sigo com a hipótese se não houver resposta)

1. Troféus: prefere que eles fiquem visíveis enquanto forem 1 ou 2 (MÉDIO 1)? Hipótese: deixar como está até você pedir.
2. Relógio em 1238-1276 e 860-898: prefere o relógio visível com a placa da Diretoria um pouco menor (MÉDIO 2)? Hipótese: como está.
3. Letra menor em tela cheia nas 4 salas de nome longo: aceita, ou prefere nomes mais curtos (MÉDIO 3)? Hipótese: aceita.

## Pontos fortes

- A solução é uma regra só para todas as salas (reserva + fonte pela largura real), sem medida fixa por sala, e aguenta salas novas.
- A placa fica presa na faixa livre por construção: o navegador refaz a conta em qualquer largura, zoom ou barra de rolagem.
- Não mexe em `z-index`, cor, fonte ou sprite. A altura da placa em 9px ficou igual (0,1px de diferença).
- A entrega traz antes e depois de cada regra, o jeito de desfazer e perguntas objetivas.
