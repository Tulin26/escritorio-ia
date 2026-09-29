# Plano m-005: alinhamento dos nomes e janelas

- **Projeto:** alinhamento-dos-nomes-e-janelas (briefing em `projetos/alinhamento-dos-nomes-e-janelas.md`)
- **Pedido:** p-002, 2026-09-29 08:08
- **Data do plano:** 2026-09-29 08:15

## Pedido original

> "como pode ver na imagem abaixo tem alguns nomes das salas que estão sobrepondo as janelas , corrija isso para todas ficarema linhadas e nenhuma sobre a outra"

## Anexos recebidos

| Arquivo | O que é | Para que serve | Qual sala usa |
|---|---|---|---|
| `anexos/p-002/image.png` | Print do painel do escritório: as 14 salas em pixel art, cada uma com a placa do nome no alto, a janela da esquerda e, em algumas, uma decoração na parede da direita. | Mostra onde a placa encosta ou fica por cima de outro elemento da parede. É o "antes" da correção. | Marca & Design (m-006) e Revisão (m-007) |

O que dá para ver no print:
- **Marca & Design**: a placa fica por cima da janela da esquerda e encosta na cartela de cores da direita.
- **Tráfego & Mídia**: a placa fica por cima da janela da esquerda e do gráfico da direita.
- **Git & GitHub**: a placa fica muito perto da janela da esquerda e da nuvem da direita.
- **Estratégia**, **Pesquisa**, **Revisão**, **Vendas** e **Copy**: a placa fica perto da janela ou da decoração da direita. Numa tela um pouco mais estreita, elas também se sobrepõem.
- **Diretoria**: a placa fica entre as duas janelas e o relógio. Hoje não se sobrepõe, mas precisa entrar na conferência.
- **Sala de Reunião**, **Recepção**, **Você** e **Memória**: sem sobreposição visível no print.

## Diagnóstico inicial (lido no código)

- As salas são desenhadas em `painel/src/componentes/Escritorio.jsx` e os estilos estão em `painel/src/estilo.css`.
- `.placa` fica em `position: absolute; top: 9px; left: 50%; transform: translateX(-50%)`, com `white-space: nowrap` e `z-index: 3`. Ela é centralizada e não sabe onde está a janela.
- `.janela` fica em `top: 6px; left: 12px`, com 46px de largura e `z-index: 2`. A Diretoria tem uma segunda janela em `right: 12px`.
- As decorações de parede (`.deco.parede`, `top: 8px; right: 12px`) e o relógio da Diretoria (`.relogio`, `right: 74px`) disputam a mesma faixa de 42px da parede.
- Resultado: quando o nome é longo ("Marca & Design", "Tráfego & Mídia", "Git & GitHub") ou a sala é estreita, a placa centralizada invade a janela e a decoração. Como a placa tem o `z-index` maior, ela fica por cima.
- Já existem regras `@container` e `@media` (linhas 730 a 760) que escondem a janela, os troféus e o relógio em larguras pequenas. A correção precisa conviver com elas.
- O painel usa o build de `painel/dist/`. Depois de mudar `painel/src/`, é preciso gerar o build de novo (`npm run painel` na raiz) para a mudança aparecer no `npm start` e no painel online.

## Perguntas para o dono

1. Como o alinhamento deve ficar? (a) a placa continua centralizada, mas nunca invade a janela nem a decoração (encolhe a fonte ou quebra o nome); (b) a placa fica sempre logo depois da janela, alinhada à esquerda em todas as salas; ou (c) a placa fica numa faixa própria, sem nada em volta.
2. Quando não houver espaço, o que pode ceder: a decoração da parede, o tamanho da letra da placa ou a janela?
3. Posso mexer direto em `painel/src/` (fica dentro do escritório) ou você prefere receber só a proposta em .md antes?

## Hipótese de trabalho (seguimos com ela se não houver resposta)

- **Opção (a)**: a placa continua **centralizada** em todas as salas, na mesma altura (alinhada entre as salas), e **nunca** se sobrepõe à janela, à decoração da parede nem ao relógio, em nenhuma largura de tela.
- Ordem do que cede quando falta espaço: primeiro a decoração da parede (some ou vai para baixo), depois a letra da placa diminui um pouco (sem ficar ilegível), e só por último a janela some. A regra atual que esconde a janela em salas muito estreitas continua.
- O Designer **aplica a correção direto** em `painel/src/estilo.css` (e em `Escritorio.jsx` só se não der para resolver só no CSS), porque o código fica dentro do escritório e o briefing permite isso depois de o plano ser aprovado. Tudo o que ele mudar fica anotado na entrega (antes e depois de cada regra), para dar para desfazer se o dono não aprovar.
- Nada muda além do alinhamento: o estilo pixel art, as cores das salas, a fonte, os sprites e o comportamento do painel ficam iguais (regra "Proibido" do briefing).

## Sub-missões

| id | Área | Título | Depende de | XP |
|---|---|---|---|---|
| m-006 | design (designer) | Corrigir a sobreposição das placas com as janelas e decorações em todas as salas | m-005 | 30 |
| m-007 | revisor (revisor) | Revisar o alinhamento das placas em todas as salas e larguras | m-006 | 20 |

A Pesquisa não entra: o pedido é uma correção de interface e todos os dados necessários estão no print e no código.

## Critérios de aceite

**m-006 (Marca & Design)**
- Nas 14 salas (Sala de Reunião, Diretoria, Você, Recepção, Pesquisa, Estratégia, Marca & Design, Copy, Social, Tráfego & Mídia, Vendas, Revisão, Git & GitHub, Memória), a placa não se sobrepõe à janela, à decoração da parede nem ao relógio.
- As placas ficam na mesma altura em todas as salas, com o mesmo espaço até o topo.
- A regra vale nas larguras do painel: tela cheia (4 colunas), até 1100px, até 760px e até 440px, e nas salas estreitas pelas regras `@container`. A entrega traz uma tabela sala x largura com o que acontece em cada caso, com base nas medidas do CSS.
- Nenhuma mudança de cor, de sprite, de fonte (fora um ajuste de tamanho em telas estreitas, se for preciso) ou de comportamento (clique das salas, linhas animadas, fase do dia).
- Entrega em `design/m-006-alinhamento-dos-nomes-e-janelas-placas.md` com: diagnóstico, a solução escolhida e o porquê, cada regra alterada (antes e depois), a lista de arquivos mexidos e o passo para gerar o build de novo.

**m-007 (Revisão)**
- Confere no código, sala por sala e largura por largura, que as medidas (posição e largura da placa, da janela, da decoração e do relógio) não se cruzam.
- Confere que nada fora do alinhamento mudou (cores, sprites, comportamento), comparando com o print do anexo.
- Aponta o que só dá para confirmar abrindo o painel e diz o que o dono deve olhar na tela depois do build.
- Entrega em `revisor/m-007-alinhamento-dos-nomes-e-janelas-revisao.md` com nota por critério e a lista de problemas (se houver).

## Ordem

1. m-005 (este plano): o dono aprova.
2. m-006 (Marca & Design): corrige e documenta.
3. m-007 (Revisão): confere depois que a m-006 estiver aprovada.
4. Depois das aprovações: a sessão principal (ou o dono) roda `npm run painel` para gerar o build e confere o painel na tela.

## Riscos

- **Build desatualizado:** os agentes não rodam comandos. Sem gerar o build de novo (`npm run painel`), o painel continua mostrando a versão antiga, mesmo com `painel/src/` corrigido.
- **Painel online:** a correção só aparece no Vercel depois de o build novo ir para o GitHub e o Vercel publicar. Enviar para o GitHub pela sala Git & GitHub é arquivo do escritório. Publicar no Vercel é o fluxo normal do repositório, mas quem decide é o dono.
- **Sem conferir na tela:** a Revisão confere pelas medidas do CSS, não por print novo. Pode sobrar algum caso que só aparece no navegador (fonte que carrega com outra largura, zoom do navegador). Por isso o dono confere na tela no fim.
- **Nomes futuros:** se o dono criar uma sala com nome maior, a solução precisa aguentar isso (encolher ou quebrar o nome), e não depender de medidas fixas por sala.
- **Regras que já existem:** mexer nas regras `@container` e `@media` pode esconder a janela ou a decoração onde hoje ela aparece. A entrega deve dizer exatamente o que passa a sumir e em qual largura.

## O que exige aprovação para agir fora do escritório

- Nada deste plano sai da pasta do escritório: as mudanças ficam em `painel/src/` e nas pastas `design/` e `revisor/`.
- Publicar o painel online (deploy no Vercel) é ação externa: só com pedido explícito do dono depois das aprovações.
