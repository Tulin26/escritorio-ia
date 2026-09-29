# m-006: placas dos nomes sem sobrepor janelas e decorações

- **Projeto:** alinhamento-dos-nomes-e-janelas (briefing em `projetos/alinhamento-dos-nomes-e-janelas.md`)
- **Plano:** m-005 (aprovado)
- **Sala:** Marca & Design (UI/UX, skill ui-ux-pro-max)
- **Data:** 2026-09-29

> **Para ver a correção no painel, o dono precisa gerar o build de novo:** na raiz do escritório, rode `npm run painel`
> e depois recarregue o painel (`npm start`). Sem isso o painel continua usando o `painel/dist/` antigo. No painel online,
> a mudança só aparece depois de o build novo ir para o GitHub e o Vercel publicar. Publicar é decisão sua.

## Objetivo

Nas 14 salas, a placa do nome fica na mesma altura (9px do topo, como hoje), centralizada, e **nunca** passa por cima da
janela, da decoração da parede, dos troféus nem do relógio da Diretoria, em qualquer largura de tela.

## Anexo usado

- `anexos/p-002/image.png` (print do painel, é o "antes"). Pelo print: a placa passa por cima da janela em **Marca & Design**,
  **Tráfego & Mídia** e **Sala de Reunião** e encosta nela em **Git & GitHub**. As contas abaixo confirmam isso.
  O anexo não foi alterado.

## Diagnóstico (medidas do CSS de antes)

Medidas em px, contadas a partir da borda de dentro da sala (a sala tem 6px de borda). **W** = largura da sala por dentro da borda.

| Elemento | Onde fica na parede (faixa de 42px de altura) |
|---|---|
| Janela da esquerda | de 12 a 58 |
| Janela da direita (só Diretoria) | de W−58 a W−12 |
| Decoração da parede (direita) | de W−12−d a W−12; d vai de 26 (prancheta) a 40 (quadro, painel de anúncios), então no máximo de W−52 a W−12 |
| Troféus (Diretoria) | de 74 a 74 + (22 × nível + 4); com 5 troféus vai até 188 |
| Relógio (Diretoria) | de W−142 a W−74 (5 caracteres de 10px + 12 de padding + 6 de borda = 68) |
| Placa (antes) | centralizada, sem limite: largura = 9 × letras + 26 (fonte Press Start 2P tem 1em por letra) |

Largura da placa em 9px: Você e Copy 62 · Social e Vendas 80 · Revisão e Memória 89 · Recepção e Pesquisa 98 · Diretoria 107 ·
Estratégia 116 · Git & GitHub 134 · Marca & Design 152 · Sala de Reunião e Tráfego & Mídia 161.

**Causa:** a placa centralizada só não encosta na janela se W ≥ largura da placa + 116. Em tela cheia a sala comum tem W = 246,
então qualquer placa acima de 130px passa por cima da janela (Git, Marca & Design, Reunião, Tráfego). Em 1366px (W = 212) já
são 7 salas. Entre 1101 e 1280px a placa de Reunião, Tráfego e Marca & Design fica **mais larga que a sala** e é cortada pelo
`overflow: hidden`. Na Diretoria, entre 1101 e 1276px e entre 761 e 898px, a placa passa por cima do relógio. A placa tem
`z-index: 3`, maior que o da janela (2), por isso fica por cima.

## Solução escolhida e por quê

Hipótese (a) do plano: **a placa continua centralizada** em todas as salas, na mesma altura, e passa a respeitar uma **reserva**
dos dois lados da parede:

1. **Reserva** (`--reserva`): a placa só ocupa o espaço entre `left: reserva` e `right: reserva`, centralizada com
   `margin: 0 auto` e `width: fit-content`. Como a placa é centralizada, a reserva é igual dos dois lados. Nas salas comuns
   ela vale 64px (janela: 12 + 46 + 6 de folga). Isso cobre também qualquer decoração da direita, que ocupa no máximo 52px.
   Por isso **nenhuma decoração das salas comuns precisa sumir**.
2. **Letra que se ajusta** (uma regra só para todas as salas, sem medida fixa por sala): se o nome não cabe em 9px, a fonte
   diminui até caber, no mínimo 6px, que é o menor tamanho que o painel já usa (`.tarefa` e `.balao`). A conta usa a largura
   real da sala (`100cqi`) e o número de letras do nome (`--letras`, que o `Escritorio.jsx` manda). Assim uma sala nova com nome
   longo também se ajusta.
3. **Último recurso: 2 linhas.** Se nem em 6px o nome cabe numa linha, ele quebra no espaço ("Tráfego &" / "Mídia"). Em 6px,
   duas linhas medem 29px de altura (vão de 9 a 38), ainda dentro da parede (42px). Nenhuma letra fica escondida.
4. **Diretoria**: a reserva é de 194px com os troféus (até 5) e o relógio, 148px sem os troféus e 64px sem os dois. Na
   Diretoria cedem primeiro os troféus, depois o relógio, como diz o plano. Com isso a placa da Diretoria fica **sempre em 9px**.
5. **Janela**: continua sumindo só onde já sumia (sala com até 190px por dentro). Quando some, a reserva cai para 12px.

**Ordem do que cede (plano m-005):** nas salas comuns, a decoração da direita nunca é o que aperta. O que aperta é a janela da
esquerda, que é maior (58px contra 52px), e a centralização repete essa medida do outro lado. Então a ordem real fica assim:
(1) na Diretoria, somem os troféus e depois o relógio; (2) a letra da placa diminui até 6px; (3) o nome quebra em 2 linhas;
(4) a janela some, só onde já sumia antes.

**De onde saiu cada escolha (skill ui-ux-pro-max, `data/ux-guidelines.csv`):**
- Linha 117 (nº 116, *Compact Label Overflow*): a placa fica em uma linha sempre que der, com a fonte encolhendo antes de quebrar.
- Linha 114 (nº 113, *Essential Text Truncation*, crítica): o nome da sala distingue uma sala da outra, então nada de reticências
  nem de corte. Ela pesa mais que a 117, e por isso, quando não há outro jeito, quebra em 2 linhas em vez de cortar.
- Linha 112 (nº 111, *Long Token Wrapping*): `overflow-wrap: anywhere` fica como rede de segurança para um nome futuro com uma
  palavra enorme, para ele não vazar da parede.
- Linha 17 (nº 16, *Overflow Hidden*): antes, o `overflow: hidden` da sala cortava a placa entre 1101 e 1280px. Agora ela nunca
  passa da largura da sala.
- Linha 16 (nº 15, *Z-Index Management*): a correção não mexe em `z-index`. Tirar a placa de cima da janela só escondia o
  problema. A solução é não haver cruzamento.
- Linha 111 (nº 110, *Heading Line Balance*): não uso `text-wrap: balance` nem `<br>` forçado. A quebra é a natural do
  navegador, e a entrega não promete uma quebra exata em todo navegador.

## Regras alteradas (antes e depois)

### 1. `painel/src/estilo.css`: `.placa`

Antes:
```css
.placa {
  position: absolute; top: 9px; left: 50%; z-index: 3; transform: translateX(-50%);
  padding: 6px 10px 5px; white-space: nowrap;
  font: 9px/1 var(--pixel); color: #ffe7a8;
  background: #2a1a0e; border: 3px solid #120a04;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, .45), 0 3px 0 rgba(0, 0, 0, .45);
}
```
Depois:
```css
.placa {
  --reserva: 64px; /* janela: 12px da borda + 46px de largura + 6px de folga */
  position: absolute; top: 9px; left: var(--reserva); right: var(--reserva); z-index: 3;
  width: fit-content; margin: 0 auto;
  padding: 5px calc(10em / 9) 4px; text-align: center; overflow-wrap: anywhere;
  font: 9px/1.2 var(--pixel); color: #ffe7a8;
  background: #2a1a0e; border: 3px solid #120a04;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, .45), 0 3px 0 rgba(0, 0, 0, .45);
}
@supports (width: 1cqi) {
  .placa { font-size: clamp(6px, calc((100cqi + 12px - 2 * var(--reserva)) / (var(--letras, 10) + 2.23)), 9px); }
}
.sala-dir .placa { --reserva: 194px; }
```
O que mudou e por quê:
- `left: 50%` + `transform` virou `left/right: var(--reserva)` + `margin: 0 auto` + `width: fit-content`: continua centralizada,
  mas presa na faixa livre.
- `white-space: nowrap` saiu para permitir as 2 linhas do último recurso. Com a fonte ajustada, o nome só quebra quando nem
  6px cabem.
- `padding 6px 10px 5px` + `line-height 1` virou `5px 1,11em 4px` + `line-height 1.2`. Em 9px dá o mesmo resultado de antes
  (10px de lado, 26px de altura, texto na mesma posição, com diferença de 0,1px). O padding lateral encolhe junto com a letra e
  as 2 linhas não se encostam.
- A cor, o fundo, a borda, a sombra, a fonte (Press Start 2P), o `z-index` e o `top: 9px` continuam iguais.
- O `@supports` protege navegador antigo sem `cqi`: nele a placa fica em 9px e, se preciso, quebra dentro da faixa livre, sem
  cruzar nada.

### 2. `painel/src/estilo.css`: salas estreitas (`@container`)

Antes:
```css
@container (max-width: 190px) {
  .janela.e, .deco.parede, .interruptor-parede { display: none; }
}
@container (max-width: 420px) {
  .trofeus { display: none; }
}
```
Depois:
```css
@container (max-width: 190px) {
  .janela.e, .deco.parede, .interruptor-parede { display: none; }
  .placa { --reserva: 12px; }
}
@container (max-width: 480px) {
  .trofeus { display: none; }
  .sala-dir .placa { --reserva: 148px; } /* relógio: 74 + 68 + 6 */
}
@container (max-width: 390px) {
  .relogio { display: none; }
  .sala-dir .placa { --reserva: 64px; }
}
```
- Os troféus passam a sumir com a Diretoria de até **480px** por dentro (antes, 420). Com 5 troféus, a placa em 9px só cabe a
  partir de 477px.
- **Regra nova:** o relógio some com a Diretoria de até **390px** por dentro. A partir de 385px ele cabe ao lado da placa em 9px.
  Antes ele ficava por baixo da placa entre 1101 e 1276px e entre 761 e 898px.
- A regra da janela (190px) não mudou: só ganhou a reserva menor para a placa.

### 3. `painel/src/estilo.css`: `@media (max-width: 760px)`

Antes: `.trofeus, .relogio { display: none; }`
Depois: a mesma linha + `.sala-dir .placa { --reserva: 64px; }` (sem troféus e relógio, a Diretoria usa a reserva das salas comuns).

### 4. `painel/src/componentes/Escritorio.jsx`: a placa informa quantas letras tem

Foi preciso mexer no JSX porque o CSS não consegue contar as letras de um texto.

Antes:
```jsx
<div className="placa">{sala.nome}</div>
```
Depois:
```jsx
<div className="placa" style={{ '--letras': [...String(sala.nome || '')].length || 1 }}>{sala.nome}</div>
```
Só acrescenta uma variável de estilo. O texto, o clique da sala, as linhas animadas e a fase do dia continuam iguais.

**Arquivos mexidos:** `painel/src/estilo.css` e `painel/src/componentes/Escritorio.jsx`. O `painel/dist/`, o anexo e os sprites
não foram tocados. **Para desfazer**, é só trocar cada bloco "Depois" pelo "Antes" acima.

## Como ficam as salas em cada largura

Conta usada: faixa livre **A = W − 2 × reserva**, e fonte = mín(9, (A − 8) ÷ (letras + 2,23)), com piso de 6px. A placa fica
sempre dentro da faixa livre, então **não cruza nada em nenhuma célula**. As larguras abaixo são da janela do navegador, sem a
barra de rolagem. Com ela (uns 17px no Windows), cada sala fica uns 4px mais estreita em 4 colunas; a conta é refeita na hora
pelo navegador, então a garantia continua.

### Medidas por largura

| Tela | Layout | Sala comum: W (por dentro da borda) | Janela e decoração | Reserva | Faixa livre A | Diretoria: W, o que aparece, reserva, A |
|---|---|---|---|---|---|---|
| 1500 ou mais | 4 colunas + painel lateral | 246 | aparecem | 64 | 118 | 522 · troféus e relógio · 194 · 134 |
| 1440 | 4 colunas + lateral | 231 | aparecem | 64 | 103 | 492 · só relógio · 148 · 196 |
| 1366 | 4 colunas + lateral | 212,5 | aparecem | 64 | 84,5 | 455 · só relógio · 148 · 159 |
| 1280 | 4 colunas + lateral | 191 | somem (já sumiam) | 12 | 167 | 412 · só relógio · 148 · 116 |
| 1101 | 4 colunas + lateral | 146 | somem (já sumiam) | 12 | 122 | 322,5 · sem os dois · 64 · 194,5 |
| 1100 | 4 colunas, sem lateral | 240,5 | aparecem | 64 | 112,5 | 511 · troféus e relógio · 194 · 123 |
| 1024 | 4 colunas | 221,5 | aparecem | 64 | 93,5 | 473 · só relógio · 148 · 177 |
| 900 | 4 colunas | 190,5 | somem (já sumiam) | 12 | 166,5 | 411 · só relógio · 148 · 115 |
| 761 | 4 colunas | 155,75 | somem (já sumiam) | 12 | 131,75 | 341,5 · sem os dois · 64 · 213,5 |
| 760 | 2 colunas | 341 | aparecem | 64 | 213 | 712 · sem os dois (já era assim) · 64 · 584 |
| 600 | 2 colunas | 261 | aparecem | 64 | 133 | 552 · sem os dois · 64 · 424 |
| 500 | 2 colunas | 211 | aparecem | 64 | 83 (o caso mais apertado) | 452 · sem os dois · 64 · 324 |
| 441 | 2 colunas | 181,5 | somem (já sumiam) | 12 | 157,5 | 393 · sem os dois · 64 · 265 |
| 440 | 1 coluna | 396 | aparecem | 64 | 268 | igual às outras · 64 · 268 |
| 360 | 1 coluna | 316 | aparecem | 64 | 188 | igual · 64 · 188 |
| 320 | 1 coluna | 276 | aparecem | 64 | 148 | igual · 64 · 148 |

A Memória ocupa 2 colunas nos layouts de 4 e de 2 colunas e fica em 9px em todas as larguras.

### Tamanho da letra da placa (px) por sala e largura

"9" = igual a hoje. "6 (2 linhas)" = quebra no espaço, em 6px. Nenhuma célula tem sobreposição.

**4 colunas com painel lateral (1101 a 1500 ou mais)**

| Sala (letras) | 1500+ | 1440 | 1366 | 1280 | 1101 |
|---|---|---|---|---|---|
| Sala de Reunião (15) | 6,4 | 6 (2 linhas) | 6 (2 linhas) | 9 | 6,6 |
| Diretoria (9) | 9 | 9 | 9 | 9 | 9 |
| Você (4) | 9 | 9 | 9 | 9 | 9 |
| Recepção (8) | 9 | 9 | 7,5 | 9 | 9 |
| Pesquisa (8) | 9 | 9 | 7,5 | 9 | 9 |
| Estratégia (10) | 9 | 7,8 | 6,3 | 9 | 9 |
| Marca & Design (14) | 6,8 | 6 (2 linhas) | 6 (2 linhas) | 9 | 7,0 |
| Copy (4) | 9 | 9 | 9 | 9 | 9 |
| Social (6) | 9 | 9 | 9 | 9 | 9 |
| Tráfego & Mídia (15) | 6,4 | 6 (2 linhas) | 6 (2 linhas) | 9 | 6,6 |
| Vendas (6) | 9 | 9 | 9 | 9 | 9 |
| Revisão (7) | 9 | 9 | 8,3 | 9 | 9 |
| Git & GitHub (12) | 7,7 | 6,7 | 6 (2 linhas) | 9 | 8,0 |
| Memória (7) | 9 | 9 | 9 | 9 | 9 |

**4 colunas sem painel lateral (761 a 1100)**

| Sala (letras) | 1100 | 1024 | 900 | 761 |
|---|---|---|---|---|
| Sala de Reunião (15) | 6,1 | 6 (2 linhas) | 9 | 7,2 |
| Diretoria (9) | 9 | 9 | 9 | 9 |
| Você (4) | 9 | 9 | 9 | 9 |
| Recepção (8) | 9 | 8,4 | 9 | 9 |
| Pesquisa (8) | 9 | 8,4 | 9 | 9 |
| Estratégia (10) | 8,5 | 7,0 | 9 | 9 |
| Marca & Design (14) | 6,4 | 6 (2 linhas) | 9 | 7,6 |
| Copy (4) | 9 | 9 | 9 | 9 |
| Social (6) | 9 | 9 | 9 | 9 |
| Tráfego & Mídia (15) | 6,1 | 6 (2 linhas) | 9 | 7,2 |
| Vendas (6) | 9 | 9 | 9 | 9 |
| Revisão (7) | 9 | 9 | 9 | 9 |
| Git & GitHub (12) | 7,3 | 6,0 | 9 | 8,7 |
| Memória (7) | 9 | 9 | 9 | 9 |

**2 colunas (441 a 760) e 1 coluna (até 440)**

| Sala (letras) | 760 | 600 | 500 | 441 | 440 | 360 | 320 |
|---|---|---|---|---|---|---|---|
| Sala de Reunião (15) | 9 | 7,3 | 6 (2 linhas) | 8,7 | 9 | 9 | 8,1 |
| Diretoria (9) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Você (4) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Recepção (8) | 9 | 9 | 7,3 | 9 | 9 | 9 | 9 |
| Pesquisa (8) | 9 | 9 | 7,3 | 9 | 9 | 9 | 9 |
| Estratégia (10) | 9 | 9 | 6,1 | 9 | 9 | 9 | 9 |
| Marca & Design (14) | 9 | 7,7 | 6 (2 linhas) | 9 | 9 | 9 | 8,6 |
| Copy (4) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Social (6) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Tráfego & Mídia (15) | 9 | 7,3 | 6 (2 linhas) | 8,7 | 9 | 9 | 8,1 |
| Vendas (6) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| Revisão (7) | 9 | 9 | 8,1 | 9 | 9 | 9 | 9 |
| Git & GitHub (12) | 9 | 8,8 | 6 (2 linhas) | 9 | 9 | 9 | 9 |
| Memória (7) | 9 | 9 | 9 | 9 | 9 | 9 | 9 |

**Conferência do caso mais apertado** (faixa livre de 83px, a partir de 500px de tela): em 6px, "Tráfego &" mede 73px,
"Sala de" e "Reunião" medem 61px cada, "Marca &" mede 61px, "GitHub" mede 55px e "Estratégia" (numa linha, em 6,1px) mede 81px.
Tudo cabe em 83px. As 2 linhas vão de 9 a 38px de altura, e a parede tem 42px.

### O que passa a sumir, e onde (comparado com hoje)

| Elemento | Antes sumia em | Agora some em | Diferença |
|---|---|---|---|
| Troféus da Diretoria | Diretoria de até 420px por dentro: tela de até 1336 (com lateral) e de até 958 (sem lateral), e em qualquer tela de até 760 | Diretoria de até 480px por dentro: tela de até **1456** (com lateral) e de até **1078** (sem lateral), e em qualquer tela de até 760 | somem também em 1337 a 1456 e em 959 a 1078 |
| Relógio da Diretoria | só em telas de até 760 | Diretoria de até 390px por dentro: telas de **1101 a 1276** e de **761 a 898**, além de todas até 760 | é o único caso novo. Nessas larguras ele ficava por baixo da placa |
| Janela e decoração da parede | sala comum de até 190px por dentro | igual | nenhuma |
| Decoração do chão, interruptor do Git | igual | igual | nenhuma |

Com a barra de rolagem do Windows, some-se uns 17px a essas larguras de tela.

## Hipóteses (seguimos com elas porque ninguém responde na rodada)

1. O plano aprovado vale: **placa centralizada**, na mesma altura (9px do topo) em todas as salas, nunca por cima de nada.
2. **Piso de 6px** para a letra, o menor tamanho que o painel já usa. Abaixo disso, 2 linhas, em vez de cortar o nome com "…".
3. **Troféus e relógio podem sumir** em mais larguras que hoje. A conta usa o pior caso (5 troféus), para a correção não
   quebrar quando o seu nível subir. Hoje você está no nível 1, com 1 troféu.
4. A fonte Press Start 2P tem todas as letras com 1em de largura. Se ela não carregar, a fonte reserva é mais estreita e a placa
   fica com ainda mais folga.
5. As contas não incluem a barra de rolagem. Com ela nada muda na garantia, porque o navegador refaz a conta pela largura real.

## Perguntas para o dono (sigo com a hipótese se não houver resposta)

1. Em 1366 e 1440px, Sala de Reunião, Marca & Design, Tráfego & Mídia e Git & GitHub ficam em **2 linhas de 6px**. Prefere
   assim ou prefere uma linha só com letra do mesmo tamanho em todas as salas (todas as placas menores, por igual)?
2. Quer os troféus visíveis entre 1337 e 1456px enquanto você tiver poucos troféus? Dá para calcular a reserva pelo seu nível
   (mais código no `Escritorio.jsx`). Hoje a regra usa o pior caso.
3. Algum nome de sala pode ficar mais curto (ex.: "Reunião", "Tráfego")? Nome mais curto deixa a placa em 9px em mais telas.

## Checklist de UX (ui-ux-pro-max) conferido

- [x] **Contraste:** a cor não mudou (texto `#ffe7a8` sobre `#2a1a0e`, cerca de 13:1, acima de 4,5:1).
- [x] **Alvos de toque:** a placa não é clicável. O clique continua na sala inteira, do mesmo tamanho.
- [x] **Sem rolagem para o lado:** a placa não passa mais da largura da sala. Antes ela era cortada entre 1101 e 1280px.
- [x] **Nome completo sempre:** sem reticências nem corte, e a `section` continua com `aria-label="Sala …"` para leitor de tela.
- [~] **Texto base de 16px:** não se aplica às placas pixel art. O painel já usa de 6 a 9px na fonte Press Start 2P; a correção
  fica dentro dessa escala.
- [x] **Estado de carregando e de erro:** não se aplica (elemento decorativo, sem dados).
- [x] **Movimento:** nenhuma animação nova. Tirar o `transform` não afeta nenhuma animação.

## Pendências e o que olhar na tela depois do build

- [ ] **Rodar `npm run painel` na raiz** e recarregar o painel. Sem isso nada muda na tela.
- [ ] Conferir em tela cheia: Tráfego & Mídia, Sala de Reunião e Marca & Design ficam com a placa menor, entre a janela e a
      decoração, sem encostar.
- [ ] Conferir em 1366 ou 1440px (ou diminuindo a janela do navegador): as placas em 2 linhas cabem na parede, e na Diretoria
      os troféus somem.
- [ ] Conferir entre 1101 e 1276px: na Diretoria o relógio some e a placa fica livre.
- [ ] Painel online: só atualiza depois de o build ir para o GitHub e o Vercel publicar (decisão do dono).
- [ ] A m-007 (Revisão) confere estas contas no código.
