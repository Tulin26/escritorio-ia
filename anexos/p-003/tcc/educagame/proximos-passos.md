# Próximos passos

Lista viva do que ficou aberto. Quando um item for feito, apague — o histórico
do git guarda o que aconteceu.

Atualizado em 09/09/2026.

---

## Aberto — atualizado em 09/09/2026

**Nada aqui é código.** Os cinco itens abertos de manhã foram fechados, e a
migração `20260909120000` já está aplicada (conferido no banco: as três
colunas existem). O que sobra é espera por dado e decisão sua.

### Esperando uso acumulado, não trabalho

Duas medições estão prontas e sem amostra. Rodar depois de algumas aulas de
exatas:

```
python scripts/medir_legenda_sem_formula.py
python scripts/medir_resolucao_simbolica.py
```

A primeira responde a dúvida que ficou de hoje: a validação
`legenda-com-variavel-sem-formula` foi ligada com 0 falso positivo em 7.200
questões **do banco offline**, e no mesmo dia a regra vizinha provou que esse
corpus engana — 0% offline contra 25% no dado real. O número dela ainda não
foi confirmado onde importa.

O gargalo é uso: 115 logs em um mês. Não adianta mexer em coleta.

### Defesa em profundidade que ficou para depois

`parece_formula_laboratorio` ainda cola prosa que venha sem dois-pontos
("identificar os valores a = -2"). Deixou de ser urgente porque a fonte secou
— o prompt parou de dar o exemplo errado —, mas a função decide a renderização
de **todo passo de todo modo**, e mexer nela sem medir contra as 50.900 é como
a `exatas-sem-estrutura` foi parar desligada.

---

## O que foi fechado em 09/09/2026

### O painel da turma mostrava duas coisas que não eram verdade

**1. O gráfico dizia que 43 alunos acertaram 0%.** Dos 45 da ETEC, 43 nunca
tinham respondido nada — e o gráfico de desempenho plotava todo mundo, então
"não respondeu" saía desenhado como "acertou 0%", em **vermelho** na escala.
Os dois com dado real sumiam no meio.

A guarda já existia em três lugares do mesmo arquivo (alerta de baixo
desempenho, destaque da tabela, gráfico de tempo ao lado) e faltava só nele —
o mesmo padrão do `parece_formula_laboratorio`, em que a guarda entra uma
porta por vez. Era também por isso que os dois gráficos lado a lado mostravam
populações diferentes: 45 à esquerda, 2 à direita. O Flask não tinha o
defeito; lá o gráfico já vinha com `{% if metricas.total %}`.

**2. A tela dizia "ativa" para uma conta que não entra.** `aluno` aparecia com
escola "—" e situação ativa, enquanto `conta_pode_entrar` a recusa — a regra
do login não olha o papel. E a tela promete o contrário no próprio texto
("Conta sem vínculo aparece marcada"): só cumpria para professor, porque
`PAPEIS_COM_ESCOLA` tinha só `("professor",)`.

Há agora um teste que confere a marcação **contra a regra do login**, papel
por papel. Eram duas listas respondendo à mesma pergunta, e foi assim que
"aluno" ficou de fora de uma delas.

**3. O gráfico não escalava — e a primeira correção piorou isso.** Barra
horizontal resolveu a legibilidade e criou `26 × 100 = 2.600px` de altura numa
turma de 100. Trocar um problema por outro não é consertar.

O ponto de fundo é que cem barras não respondem pergunta nenhuma que o
professor faça. Então o gráfico passou a depender do tamanho da turma: até 15
alunos, uma barra por aluno; acima disso, **distribuição do aproveitamento**
("como vai a turma?") e **os 10 menores** ("quem eu preciso olhar?"), os dois
com altura fixa de 380px. E a tela diz que trocou, com a tabela como saída
para ver todos.

14/14 mutantes. Um sobreviveu na primeira rodada — o aviso de quantos ficaram
de fora do gráfico mora dentro do render, e nenhum teste desenhava a tela.
Passou a ser coberto pela bancada (`tests/apoio_streamlit.py`).


### 1. Prosa colada dentro da fórmula (a causa era nossa)

Resolvido, e a causa não era o renderizador. O modelo que mandávamos para a
IA trazia, no campo **`conteudo`**:

    {"titulo": "1º Passo", "conteudo": "identificar os valores"}

A IA copiou o modelo e anexou a conta — `"identificar os valores a = -2,
b = 8, c = 10"` —, o texto foi classificado como fórmula e a tela mostrou
`identificarosvaloresa = -2`. A regra que proíbe prosa no `conteudo` **já
existia** no system prompt; ela era contradita pelo modelo logo abaixo, e o
modelo venceu.

Por que a IA copia esta descrição e não as outras: `"pergunta": "problema
numerico com pelo menos dois valores"` não é um valor plausível para o campo.
`"identificar os valores"` **é** um conteúdo de passo plausível. Descrição que
parece valor vira valor. Os quatro slots viraram `<...>`.

O endurecimento do renderizador (`parece_formula_laboratorio` colar prosa sem
dois-pontos) continua valendo como defesa em profundidade, e continua
precisando de medição — mas deixou de ser urgente, porque a fonte secou.

### 2. Conta sem "=" era rebaixada a texto — feito em 09/09/2026

Eram **dois** defeitos empilhados no mesmo passo
`(-8 ± sqrt(144)) / (2*(-2))`.

**A quinta porta.** `parece_formula_laboratorio` exigia um `=` (ou comando
LaTeX, ou `^`). Sem isso o passo inteiro descia para prosa — mas
`(-8 ± 12)/(-4)` é passo legítimo: mostrar a substituição *antes* de resolver
é o que o prompt pede.

A porta nova não pergunta *"tem prosa demais?"*. As quatro antigas perguntam
isso, e a história delas é a de um mesmo defeito que voltou **duas vezes**,
porque ausência de prosa não é presença de fórmula. A quinta pergunta *"isto
é só notação?"* — evidência positiva: sobra alguma palavra depois de tirar
números, operadores, comandos LaTeX, nomes de função e unidades?

Medido antes de ligar: **5.784 passos distintos** dos bancos, **0
regressões** e 105 passos que passaram a ser matemática — frações (`10/13`,
`2/5`) e valores com unidade (`2,18 g/L`), que renderizam melhor como LaTeX
do que como texto.

**A raiz.** `sqrt(144)` virava `\sqrt(144)`: radical sobre o **vazio**, com
"(144)" ao lado. A conversão para chave existia só em `formatar_latex()`, do
Streamlit; o caminho do Flask nunca teve. Das cinco grafias que a IA usa —
`sqrt(144)`, `raiz(144)`, `√(144)`, `√144`, `sqrt{144}` — só a última chegava
certa. Agora as cinco convergem.

12/12 mutantes. Duas coisas só a mutação pegou:

- o **">= 2 dígitos"** da porta era chute meu, e nenhum teste o sustentava.
  Medido: baixar para um dígito aceita 4 casos a mais (`3 g/L`, `4 g/L`,
  `5 g/mL`, `6 g/L`), todos legítimos, e recusa `x + 1` se ficasse em dois;
- apagar o strip de comandos LaTeX não quebrava nada, **porque todos os meus
  casos usavam o `±` Unicode**. Sem o strip, `\pm` vira a palavra "pm" e
  `(-8 \pm 12)/(-4)` voltava a ser prosa. A IA escreve das duas formas. O
  mesmo teste mostrou que `_OPERADOR` não conhecia `	imes` nem `pprox`.

Conferido no navegador, com o MathJax do próprio Laboratório.

### 3. [FEITO 09/09] "Resultado Final: −1, 5" é ambíguo em português

Lê-se como **−1,5**, um número só. O prompt já proíbe essa forma nas
alternativas (*"coloque tudo junto (...) por exemplo `{-1, -1,5}` ou
`x' = -1 e x'' = -1,5`"*), mas a regra não alcança o passo final.

**Feito em 09/09/2026**, via prompt: regra escrita, com o motivo junto (a vírgula é separador decimal em português; grandeza que não pode ser negativa descarta a raiz e diz por quê, na tela). Coberto por `tests/test_prompt_nao_ensina_o_defeito.py`, 9/9 mutantes.

### 4. [FEITO 09/09] A raiz negativa não foi descartada — e essa não é de renderização

A questão pede *"o tempo em que o projétil atinge o solo"*. `t = −1 s` é raiz
da equação mas não existe fisicamente: a resposta é **5 s**. A IA entregou as
duas raízes como se ambas valessem.

A conta está certa (Δ = 64 + 80 = 144; t = (−8 ± 12)/(−4) → −1 e 5) — o que
falta é o descarte da raiz sem sentido físico. É assunto de prompt, e vale
para toda questão de movimento/tempo/comprimento, onde valor negativo não é
resposta.

**Feito em 09/09/2026**, via prompt: regra escrita, com o motivo junto (a vírgula é separador decimal em português; grandeza que não pode ser negativa descarta a raiz e diz por quê, na tela). Coberto por `tests/test_prompt_nao_ensina_o_defeito.py`, 9/9 mutantes.

### 5. A validação da resolução — feita em 09/09/2026, e não era o Δ

Este item dizia "esperando dado". A espera acabou, mas não do jeito previsto.

**O gargalo não era a coleta, era o uso.** 115 logs em um mês; 8 resoluções
guardadas desde a migração de 03/09. Ampliar a coleta para os outros modos não
resolveria: o Oráculo de exatas é conceitual **de propósito**
(`_normalizar_questao_oraculo` apaga os passos, porque conta com passo a passo
é o Laboratório) e não-exatas não tem passos. Só o RPG de exatas os mantém.

**Os três desenhos disparam 0 vezes nas 8 reais.** O defeito que A, B e C
miravam nunca foi observado. O que apareceu foi outro — na tela, o passo final
tinha números (`x = 3`) e o buraco estava no passo **anterior**:

    3º Passo:  x = (-b ± √Δ)/(2a)     <- voltou para as letras
    Resultado: x = 3, x = 0,5         <- de onde vieram?

Daí o desenho **D**: o último passo antes do resultado ainda usa letra que um
passo anterior já tinha igualado a um número. Ligado como
`resolucao-nao-substitui-os-valores`, só no Laboratório e só para exatas.

Medido: 1 de 8 reais — exatamente a da tela — e **0 de 2.114** do banco
offline. Passa as duas outras Bhaskaras reais, que foram resolvidas certo:
esse é o caso difícil, e é o que dá valor à regra.

**A lição sobre medir, que vale mais que a regra.** Contra o banco offline os
quatro desenhos davam 0%. Contra as 8 reais, a primeira versão do D deu
**25% de falso positivo** — prosa dentro do passo virando variável
(`substituir na fórmula de Bhaskara` tem b, a, c nas palavras) e `P_f` lido
como `P`. O banco autoral responde *"a regra recusa o que NÓS escrevemos?"*,
que é uma pergunta mais fraca do que a que importa.

Isso deixa uma dúvida em aberto sobre a `legenda-com-variavel-sem-formula`,
ligada ontem com 0 de 7.200 **no mesmo corpus**. Ela é menos exposta — lê
`formula` e `legenda_variaveis`, que são campos curtos e estruturados, e não
o texto livre dos passos — mas o número dela não foi confirmado contra dado
real. Para confirmar é preciso guardar esses dois campos no log; hoje eles
não são gravados.

10/10 mutantes. Três deles acharam **código morto meu**: um strip de nomes de
função que a regra de "2+ letras" já cobria, um `< 3` que a interseção vazia
já garantia e um early-return redundante. E um teste meu era vacuoso — o
payload de Ciências morria três regras antes, em `laboratorio-sem-calculo`,
então a asserção passava sem medir nada.

## Avaliação da Educacional Delta — em andamento

Contas criadas para o diretor avaliar (`deltaata`): aluno `alunodelta` e
professor `professordelta`. **Remover ou trocar as senhas quando a avaliação
terminar** — as senhas estão em texto no PDF do guia, e só lá.

**O guia de acesso foi refeito** (`scripts/gerar_guia_acesso.py`). Ele estava
errado em três pontos, dois deles mandando o leitor para o lugar errado logo
na primeira tela:

1. mandava abrir `educagame.onrender.com/?escola=deltaata`, e esse parâmetro
   passou a ser ignorado — o diretor cairia na lista de escolas;
2. não mencionava o código da escola, que virou obrigatório;
3. garantia que *"a conta de professor não está presa a uma escola"* — hoje o
   oposto do que `conta_pode_entrar` faz. O guia descrevia como
   funcionalidade justamente o defeito que foi corrigido.

Ele envelheceu porque era um PDF avulso, sem fonte no repositório: quando o
login mudou, não havia arquivo para atualizar nem teste para reclamar. Agora
tem gerador, e o texto mora nele para poder ser cobrado por
`tests/test_guia_de_acesso.py`. Duas frases não são escritas, são
**perguntadas ao código**: o prazo da sessão vem de `core/sessao.py`, e a
frase sobre a conta presa roda `conta_pode_entrar` e conta o que aconteceu.
Assim não existe onde escrever a contradição que causou tudo isto.

Para trocar as senhas quando a avaliação terminar:

```bash
python scripts/gerar_guia_acesso.py --escola deltaata --aluno alunodelta --professor professordelta --redefinir --confirmar
```

Confirmado que o resto do caminho dele funciona: `professordelta` está
vinculado à Delta e `alunodelta` vive na tabela `alunos`, com escola própria.

### Capturas de tela — feitas

30 prints prontos e entregues, com índice descrevendo cada um. Cobrem os dez
modos, as três telas públicas e as seis abas do painel do professor.

As três mais úteis para o TCC, que não existiam na primeira leva:

- **`07c`** a resolução passo a passo do Laboratório, depois de responder;
- **`08c`** a correção do Oráculo com o bloco *Feedback pedagógico* (o que
  pode ter confundido, como evitar, próximo treino);
- **`09b`** o RPG em curso, com narrativa, HP/XP/fase e rotas de decisão.

São elas que sustentam a afirmação de que o sistema **ensina**, e não apenas
cobra — as telas de pergunta sozinhas não mostram isso.

Duas coisas foram corrigidas no caminho, não só fotografadas:

- O RPG mostrava *"Nenhuma campanha configurada"*. Ele só libera depois que o
  professor cria a aventura — o **diretor também encontraria o modo vazio**.
  Campanha criada ("A Torre dos Números Perdidos").
- A vírgula decimal partia a conta ao meio no passo a passo. Ver o commit
  `2694670`; foi um print que revelou.

O painel do professor tem dados reais: **34 questões** em quatro modos
(Laboratório, Oráculo, Escape Room, Chefes), 29% de aproveitamento. As
respostas foram **sorteadas** — não dá para saber pela tela qual alternativa é
a correta — então o percentual é acaso, não desempenho simulado. Está escrito
no índice do zip, para não ser apresentado como medição.

`playwright` foi instalado na venv para salvar os prints em arquivo. **Não está
no requirements.txt** de propósito: é ferramenta de desenvolvimento.

---

## TG — o que ainda é decisão sua

O documento foi revisado e reformatado pela ABNT (`TG - EDUCAGAME - ABNT.docx`,
arquivo novo; o original está intacto). Faltam decisões que não são minhas:

1. ~~BNCC e Moran sem citação~~ — **feito.** Os dois entraram na 2.1
   Contextualização, entre o parágrafo da gamificação e o da IA: a BNCC pela
   competência geral de cultura digital, o Moran pelo protagonismo do aluno
   nas metodologias ativas. Hoje as 20 referências estão todas citadas.
2. ~~O nome do produto em três grafias~~ — **decidido em 09/09/2026: fica
   `EducaGame IA`.** As três (`EducaGame AI` no documento, `EducaGame IA` na
   tela, `EducaGames IA` no alt da logo) foram unificadas no repositório, e há
   teste cobrando que não voltem. O arquivo de imagem da logo continua com o
   desenho antigo — trocar o desenho é decisão de design, não de texto.
3. **Faltam Resumo, Abstract, os capítulos 3, 4 e 5 e os pré-textuais.** As
   seções existem e estão numeradas; o que falta é o texto. Cada lacuna está
   marcada em vermelho no arquivo dizendo o que vai ali — são 24. Posso
   rascunhar a Metodologia e o Desenvolvimento a partir do sistema, mas aí
   você revisa linha por linha, porque quem defende é você.

**O documento foi reestruturado para a ordem do modelo da Fatec** (o TG do
Travel Wallet que você mandou): `TG - EDUCAGAME - ABNT (ordem Fatec).docx`.
Problema, objetivos e justificativa deixaram de ser capítulos e entraram na
Introdução; a contextualização virou 2.1. Capa e folha de rosto preenchidas
(Fatec Araçatuba, ADS, 2026) e a banca com as três linhas de assinatura, sem
nomes. Os títulos usam Estilo Título 1/2/3, então o sumário automático do Word
agora tem o que listar — era por isso que ele saía vazio.

O **2.2 Tecnologias utilizadas está escrito**: Python, Flask, Supabase e
PostgreSQL, e IA generativa. Nove referências novas entraram, todas conferidas
na fonte antes de escrever — três artigos com DOI (Albesher e Alfayez 2024
sobre Flask; Alfarwan 2025 e Yan et al. 2023 sobre IA na educação), dois
levantamentos recentes (GitHub Octoverse 2024, Stack Overflow 2025) e as
quatro documentações oficiais.

---

## Pendente com você (não dá para eu fazer)

### 0. Contas presas à escola — feito

A migração `20260831120000_usuarios_escola.sql` está aplicada e as três contas
de professor estão vinculadas: `professores` e `betto` na ETEC,
`professordelta` na Delta. Conferido no banco.

`desenvolvedor` continua global de propósito e **não** precisa de vínculo — é
por ele que você entra se algo der errado. A tela de gestão de contas (aba
ADM, nos dois frontends) destaca quem *não entra*, então professor sem
vínculo não some no meio da lista.

### 1. Arquivar a branch `StreamLit`

Ela está parada em `ca03d35` e não recebe mais nada — os dois frontends vivem
na `main` desde a unificação. Só continua existindo como rede: se algo der
errado no Streamlit Cloud, dá para apontar de volta para ela e voltar ao estado
de antes.

Quando estiver confiante, arquive. Não tem pressa.

### 2. Painel ADM do Streamlit — conferido em 09/09/2026

Feito por você, com o próprio olho, e valeu a pena: a conferência achou dois
defeitos que teste nenhum tinha pego.

- o gráfico de desempenho desenhava 43 alunos que nunca responderam como
  "0% de acerto", em vermelho;
- a conta `aluno`, sem escola, aparecia como **ativa** — e o login a recusa.

Os dois estão corrigidos (ver "O painel da turma mostrava duas coisas que não
eram verdade"). As seções de redefinir senha de aluno e diagnóstico do sistema
apareceram como esperado.

A tela de entrada eu já tinha conferido no navegador (o código da escola não é
senha — está impresso no papel dos alunos): clicar na escola pede o código;
`  ETECATA  ` com espaço e maiúscula é aceito; código da Delta na ETEC é
recusado com *"Código incorreto"*; e com a ETEC liberada, clicar na Delta pede
o código de novo.

### 3. Slug da escola — decidido: fica `etecata`

Levantei que `etecata` é difícil de ditar em voz alta, agora que todo aluno
digita o código. Você decidiu manter, e o PDF dos 40 acessos já foi impresso
com ele — trocar depois disso invalidaria o papel.

Se um dia trocar: é no painel ADM, e não é destrutivo — quem tiver o código
antigo recebe *"o código dessa escola mudou"* e volta para a lista. Mas o PDF
teria de ser refeito, e as senhas mudariam junto (só existem em texto no
momento em que são geradas).

O link que ia para os alunos **parou de escolher a escola sozinho**:

```
https://educagame.onrender.com/?escola=etecata     ← o ?escola= agora é ignorado
https://educagame.onrender.com/                    ← manda este; a escola e o
                                                     código vêm da tela
```


---

## Escolhas conscientes que valem revisita (não são bugs)

### Estado da cascata de IA — conferido em 02/09/2026

Você notou provedores caindo. Não era um: eram quatro, por motivos diferentes.
Levantado nos logs do Render e chamando cada um direto.

| provedor | estado | causa |
|---|---|---|
| Gemini | intermitente | `429` (cota) e `503` (sobrecarga) |
| Groq | cai todo dia | `429` — 200.000 tokens/dia do plano free, esgotados |
| Mistral | funcionando | é o que estava segurando o sistema sozinho |
| Cerebras | **removido** | `402 Payment required` — chave tirada do Render |
| Hugging Face | **corrigido** | modelo padrão descontinuado |
| OpenRouter | funciona | responde em ~5,4 s |

**O Hugging Face falhava em 100% das chamadas** e ninguém sabia, porque o log
mostrava só `BadRequestError: (Request ID: ...)`. A mensagem real vem nas
linhas seguintes da exceção, e o `print` pega só a primeira — vale lembrar
disso na próxima vez que um provedor "falhar sem motivo".

O modelo `Qwen/Qwen2.5-7B-Instruct` deixou de existir como serverless: o
roteador do HF passou a encaminhá-lo ao Together, que só serve a variante
`-Turbo` em endpoint dedicado. Trocado por `Qwen/Qwen3-4B-Instruct-2507`
(1,0 s; o `meta-llama/Llama-3.1-8B-Instruct` leva 3,2 s e é a troca de uma
linha se a qualidade pesar mais).

**`IA_CHAIN_TIMEOUT_SECONDS` subiu de 16 para 20** no Render. Motivo: o
OpenRouter é o sexto da cadeia e chegava a receber 3 s de orçamento quando
precisa de 5,4 — funcionava e nunca era usado. Com o Cerebras fora (que
queimava ~1,1 s por rodada) e o HF respondendo, sobra tempo para ele.

**O que ainda não foi verificado:** o efeito disso em uso real. A cascata só
aparece no log quando um aluno logado gera questão, e eu não entro com senha.
Vale olhar os logs `[IA]` depois de uma aula e conferir se o OpenRouter passou
a ser alcançado.


### Render é o oficial; Streamlit é a reserva

Decidido em 02/09/2026. A escola acessa pelo **Flask no Render** — é esse o
caminho que vai no TG (o capítulo 2.2 do trabalho lista Python, Flask,
Supabase e a cascata de IA; o Streamlit não aparece).

O frontend Streamlit **continua no repositório e continua tendo de funcionar**:
ele é a reserva para quando o Render estiver fora do ar. Isso não é o mesmo que
"aposentado", e a diferença importa na hora de decidir esforço:

- correção de regra compartilhada entra nos dois, como sempre (é o que
  `conta_pode_entrar` e `codigo_confere` fazem);
- refatoração só de aparência das telas `st/ui/` deixa de ser prioridade;
- o que quebra em silêncio no Streamlit continua sendo caro, porque só se
  descobre no dia em que ele for necessário — daí a conferência visual do
  painel ADM continuar na lista.


### scrypt em 2^16, abaixo do mínimo da OWASP

A OWASP recomenda 2^17 para scrypt. Ficamos em 2^16 de propósito, e o motivo
está medido na docstring de `core/senhas.py`:

| N | tempo | memória | fila de 40 alunos |
|---|---|---|---|
| 2^15 (padrão do Werkzeug) | 150 ms | 32 MB | 6 s |
| **2^16 (atual)** | **299 ms** | **64 MB** | **12 s** |
| 2^17 (mínimo OWASP) | 629 ms | 128 MB | 28 s |

O Render free tem 512 MB e roda 1 worker sync, então os logins são
serializados. Com 2^17 seriam 128 MB de pico por verificação e uma fila que,
na CPU mais lenta do plano free, chegaria perto do `--timeout 60` do gunicorn:
os últimos alunos tomariam timeout no começo da aula.

**Se sair do plano free, subir para 2^17 é trocar uma constante.**

### Prazo da sessão — 30 min parado, 12 h desde o login

A sessão não tinha prazo **nenhum**: o cookie saía sem `Expires` e sem
`Max-Age`, então quem decidia a hora de morrer era o navegador. Chrome e Edge
com *"continuar de onde parei"* restauram cookie de sessão (no Android é o
normal), e o login virava permanente — abrir o site caía direto no perfil,
dias depois, sem pedir escola nem senha.

Agora são duas travas, porque respondem a coisas diferentes:

| trava | conta desde | padrão | variável |
|---|---|---|---|
| inatividade | o último clique | 30 min | `SESSAO_MINUTOS_INATIVIDADE` |
| vida máxima | o login | 12 h | `SESSAO_HORAS_MAXIMAS` |

Sem a segunda, a máquina que fica aberta o dia inteiro renova a sessão para
sempre com qualquer clique.

**Os dois números são chute informado, não medição** — vale rever depois de
ver uma aula de verdade. 30 min não interrompe ninguém no meio de um quiz
(a conta só corre quando não há clique), mas se os alunos passam muito tempo
lendo enunciado antes de responder, suba. Para um laboratório compartilhado,
15 min é mais seguro. `0` desliga a trava.

Não foi feito de propósito, e vale considerar junto: `SESSION_COOKIE_SECURE`
e `SESSION_COOKIE_SAMESITE` continuam nos padrões do Flask (`False` e `None`).
Ligar o primeiro exige gate por ambiente — em `http://localhost` o cookie
pararia de funcionar.

### Código da escola — atrito de propósito

Clicar na escola entrava direto. O slug voltou a ser exigido como código: a
lista continua pública (é o que ajuda a pessoa a achar a sua escola), mas
entrar pede o código que o professor passa.

**Ele não é um segredo.** A lista de escolas é pública, o código não é
comparado em tempo constante e nada limita tentativas — de propósito: um
limite por IP derrubaria uma sala inteira atrás de um NAT só, e o que
protege acesso de verdade é a senha, no login. O código serve para que um
clique não leve ninguém à porta da escola errada.

**Os dois frontends pedem o código agora.** Por um tempo só o Flask pedia: no
`educagameai.streamlit.app`, clicar no cartão da escola continuava abrindo o
login direto. Era a mesma forma de `conta_pode_entrar` — uma checagem que
morava numa tela só e por isso valia para metade do produto. O efeito era mais
brando (o login cruzado já era recusado), mas o **papel entregue aos 40 alunos
manda "escolha a escola → código → usuário e senha", e aquela tela não tinha
onde digitar o código**. A comparação foi para
`services/escola_service.py::codigo_confere`, e as duas telas chamam a mesma
função.

O que a sessão do Streamlit guarda é o **id da escola liberada**, não um
booleano: num aparelho compartilhado, quem digitou o código da ETEC voltaria à
lista e entraria na Delta com um clique. Sair esquece a liberação pelo mesmo
motivo.

Saíram junto os três caminhos que faziam o código nunca ser digitado:
`?escola=<slug>` na URL, a rota `/e/<slug>` e o `DEFAULT_ESCOLA_SLUG` do
ambiente. Este último **já não surtia efeito**: `index()` decidia mostrar a
lista antes de consultar o padrão, então ele nunca vencia. Estava documentado
no `.env.example` como se funcionasse.

`/e/<slug>` continua existindo e leva à lista — para um link antigo cair em
algum lugar útil em vez de virar 404 no meio de uma aula.

**O PDF do guia da Delta ficou desatualizado**: ele manda abrir o link e
entrar. Agora há um passo a mais (escolher a escola e digitar o código).
Reveja antes de o diretor testar.

### Conta presa à escola — e por que o desenvolvedor não

`usuarios` nascia sem escola. Só `aluno` carregava unidade, então na prática
**professor era conta global**: bastava escolher outra escola na lista de
entrada para abrir o painel de gestão dela — alunos, logs, ranking.

Visto ao vivo, e com gente de fora envolvida: a conta entregue ao diretor de
uma escola alcançava a outra.

A checagem até existia — em um lugar só e para um papel só, escrita dentro da
tela do Streamlit com `role == "aluno"` na condição. O Flask não checava nada.
Agora é uma regra só, `services/auth_service.py::conta_pode_entrar`, chamada
pelos dois frontends.

**No Flask ela roda em dois pontos**, e vale saber por quê: dá para logar
antes de escolher escola (basta abrir `/login` direto), e nesse caso não há o
que comparar. A home é o ponto onde as duas pontas existem ao mesmo tempo.

**`desenvolvedor` continua global de propósito.** É a conta de manutenção, e o
painel ADM existe justamente para agir sobre todas as escolas — é o seletor de
escola que você viu lá. Se um dia isso incomodar, o caminho é dar escola ao
desenvolvedor também e deixar o ADM só para quem não tem nenhuma.

Rede: `tests/test_conta_presa_a_escola.py`, verificada por mutação — 7
defeitos plantados, 7 pegos. O último a ser pego foi o mais instrutivo:
guardar na sessão a escola **aberta** em vez da escola **da conta**. A regra
passaria a comparar a escola consigo mesma e nunca reprovaria ninguém — verde
por fora, desligada por dentro.

### Duplicação entre os dois frontends — varrida

Rodei uma varredura atrás da mesma função definida em módulos diferentes — o
modo de falha que este projeto já pagou duas vezes. **Onze nomes colidem;
três eram duplicação de verdade**, o resto é coincidência de nome entre telas
irmãs (`_init_estado`, `_render_config`, `tela_enem`).

Resolvido: o placar das guildas. `montar_guildas` (68 linhas), `parse_data` e
`inicio_semana` existiam iguais em `services/guildas_service.py` e na tela do
Streamlit — comparadas linha a linha, só mudavam o underscore do nome e a
formatação das chaves. A tela caiu de 258 para 170 linhas e passou a chamar o
serviço, como o Flask já fazia.

Idênticas era a hora certa de juntar: depois que divergem, alguém precisa
decidir qual está certa — e o placar decide quem ganha a semana.

De quebra a tela ganhou o primeiro teste de renderização que já teve
(`tests/test_placar_de_guildas.py`), porque tirar um terço de um arquivo sem
rede é apostar.

Resolvido também: `ler_css`, `PASTA_ESTILOS` e `bloco_html`, agora em
`core/design_system_base.py`. `bloco_html` estava em **quatro** lugares (os
dois módulos de design mais `home_st.py` e `rpg_helpers_st.py`).

São funções pequenas, e é por isso que ninguém as juntava — cada cópia parece
barata demais para incomodar. O preço não é o tamanho: é que uma correção
feita numa não chega às outras, e a de `ler_css` carrega uma decisão que
custou caro (o caminho sair de `__file__`, e não do diretório de trabalho).
Corrigir numa e esquecer a outra deixaria metade do app sem estilo — falha
muda: a tela abre, só fica feia.

**Da varredura, nada mais precisa de ação.** Os oito nomes restantes são
coincidência entre telas irmãs (`_init_estado`, `_render_config`, `tela_enem`
no Flask e no Streamlit) ou wrappers finos sobre um serviço compartilhado —
`_registrar_log` do Boss Rush só chama `registrar_resposta_modo`. Olhei um a
um.

### Chave Mestra — só onde ainda faz sentido

Duas coisas erradas no ADM do Streamlit, uma escondendo a outra.

**Pedia demais.** A Chave Mestra é anterior à tabela de usuários — a migração
`20260803120100_usuarios.sql` diz na primeira linha que ela *"substitui a
senha mestra única por uma tabela real, com senha em hash"*. No Flask a troca
foi até o fim; no Streamlit ficou pela metade, e quem entrava como
`desenvolvedor` tinha de apresentar **duas** credenciais para a mesma coisa.

**E protegia de menos.** `renderizar_painel_professor` desenhava a aba ADM
para todo mundo que chega ao painel, e `app.py` só barra aluno. Ou seja: um
**professor** via a aba, e a única coisa entre ele e o painel de
desenvolvedor era uma senha única, combinada de boca entre pessoas. No Flask
isso não acontece — há teste cobrando que professor não alcance a aba nem
digitando na URL.

Consertar só a primeira metade abriria o ADM para professor. As duas andam
juntas: a aba passa a existir apenas para `desenvolvedor`, e para ele a chave
deixa de ser pedida.

**ISTO MUDOU EM 08/09/2026 — a chave não existe mais.** O parágrafo abaixo
ficava aqui e estava errado:

> *"Onde a chave continua valendo: a tela de escolher escola oferece o ADM
> antes de qualquer login (...) Lá não existe usuário para consultar.
> `SENHA_MESTRA` continua sendo necessária só para esse caminho."*

O argumento era falso. A conta de desenvolvedor é **global** —
`conta_pode_entrar` devolve True para ela sem sequer olhar a escola —, então
dá para autenticar antes de escolher unidade. É o que as duas telas iniciais
fazem hoje, por usuário e senha. `SENHA_MESTRA` não é mais lida por nada.
Ver "O desenvolvedor entra global, nos dois frontends (08/09/2026)".

Rede: `tests/test_adm_streamlit_por_papel.py`, verificada por mutação — 4
defeitos plantados, 4 pegos.

### Raiz no passo final — não era conferida por ninguém (03/09/2026)

Visto na tela, questão de lei dos cossenos gerada por IA. Os três primeiros
passos certos:

```
BC² = 10² + 15² − 2·10·15·(−0,5)
BC² = 100 + 225 + 150
BC² = 475
```

e o final dizia **BC = √475 ≈ 19,4**. A raiz de 475 é 21,79; **19,4 é a raiz
de 375** — um dígito. O aluno respondeu 21,8, que está certo, levou "Errou" e
perdeu 15 pontos.

Por que passou, e são dois motivos somados:

- `"sqrt"` está em `_TERMOS_FUNCAO_TRANSCENDENTE`, e essa lista faz o passo
  inteiro ser **pulado** na comparação numérica. Isso existe por um bom
  motivo (o normalizador apaga o `sqrt` e leria `sqrt(25)` como 25), mas o
  efeito é que o passo onde a resposta nasce em Pitágoras, lei dos cossenos e
  Bhaskara não era conferido.
- `_resposta_marcada_diverge_do_resultado_final` não ajuda: ela pergunta se a
  alternativa bate com o resultado final **escrito**, e batia — o passo dizia
  19,4 e a alternativa era 19,4.

`_raiz_aproximada_incorreta` confere a raiz contra o radicando. A tolerância
é meia unidade na última casa que o próprio texto mostrou: `21,8`, `21,79` e
`22` passam (arredondar é legítimo), `19,4` e `21,7` não. Medido contra os
bancos offline: 20 das 50.900 questões têm o padrão, **zero** recusadas.

`tests/test_raiz_no_passo_final.py`, 12/12 mutantes pegos.

### `passo-final-diverge` foi consertada e ligada nos cinco modos (03/09/2026)

A seção abaixo dizia que a guarda `!= "oraculo"` estava certa nas duas
checagens. Estava certa numa só. Nesta aqui, o 1,6% de recusa era **defeito
do verificador**, e defeito consertável — as 228 questões estavam boas.

Ele lia o número errado do passo final em quatro formatos:

| passo final | lia | devia ler |
|---|---|---|
| `A = 48 m^2` | 2 — o expoente da **unidade** | 48 |
| `V = 125 cm^3` | 3 | 125 |
| `P = 3/10` | 10 — o **denominador** | 0,3 |
| `Vertice = (3, 4)` | 4 | nada: par ordenado não é um número |

mais `log_2(4) = 2`, tratado como aritmética comum porque `"log("` não casa
com `"log_2("` — a mesma armadilha do `_` já corrigida em
`_FUNCAO_APROXIMADA` no dia anterior. Ela apareceu duas vezes em dois lugares
diferentes; vale desconfiar dela sempre que houver `_` num nome de função.

`_valor_do_passo_final` resolve os quatro: descarta par ordenado, tira o
expoente que pertence à unidade (exigindo letra antes dele, para não comer o
expoente matemático de `2^3`), e **avalia** o lado direito do último `=` em
vez de pegar o último número solto — é o que preserva a fração.

Medição depois: **0 de 14.310**. Com isso a guarda perdeu o motivo e a
checagem passou a valer nos cinco modos. O que ela pega é grave e valia para
todos desde sempre: com a guarda, `d = 12 * 5` seguido de `d = 50` era
**aceito** no Treino, no Oráculo, no Escape Room e no RPG.

Um mutante mostrou que eu tinha escrito código morto junto — uma limpeza de
unidade sem expoente que não pegava nada, porque o avaliador já descarta
letra sozinho. Removida.

`tests/test_passo_final_em_todos_os_modos.py`, 9/9 mutantes pegos.

### A resolução passou a ser guardada, para dar como medir (03/09/2026)

A validação "recusar resolução que não calcula nada" ficou parada por um
motivo específico: **não havia como medir o risco dela**. Todas as outras
foram autorizadas por uma medição contra os bancos offline; esta não podia,
e vale entender por quê, porque a mesma limitação vale para qualquer regra
futura sobre passos de resolução.

O banco offline **não é amostra**. Medido: 2.200 questões do Laboratório em
apenas **81 formas distintas** de resolução — o resto é o mesmo molde com
outros números. E ampliá-lo de propósito tornaria a medição **circular**:
seria testar a regra contra exemplos escolhidos por causa dela. O valor das
medições anteriores veio de o banco ser *independente* — escrito antes, por
outro motivo.

A distribuição que importa é a das respostas reais da IA. Ela existia e não
era guardada: `logs_pedagogicos` tinha pergunta, alternativas e explicação,
mas **não os passos** — justamente o que essas regras julgam.

Agora tem. Migração `20260903120000_logs_passos_json.sql` acrescenta
`passos_json jsonb`, e o Laboratório preenche pelos dois frontends.

**Só o Laboratório**, e não é limitação: os outros modos passam por
`_normalizar_questao_oraculo`, que apaga `passos_resolucao` de exatas de
propósito. Laboratório é onde Bhaskara e o Δ aparecem.

Para medir, quando houver uso acumulado:

```bash
python scripts/medir_resolucao_simbolica.py
```

Ele roda os **três desenhos** prototipados contra as resoluções reais e diz
quantas cada um recusaria. Lembrando o que já se sabe dos casos construídos:
o desenho **B** (Δ ainda simbólico no passo final) acertou os 8; **A** e **C**
erram 5 dos 8 — não pegam o defeito (`x = (-b ± √Δ)/2a` *tem* dígito, o "2"
do `2a`) e recusam conclusão legítima em palavras.

O critério para ligar continua o mesmo das outras: as que foram ligadas
tinham **0%** de falso positivo medido.

`tests/test_passos_no_log.py`, 22 testes, 11/11 mutantes pegos. Dois deles
sobreviveram por o mesmo caso faltar nos dois caminhos: os testes de payload
inválido usavam `passos_resolucao`, que nem chega a `dados` (é filtrado por
`LOG_COLUMNS`) — o que precisa da limpeza é `passos_json`, que é como o
Streamlit entrega.

### Por que `exatas-sem-estrutura` continua desligada fora do Laboratório

Os cinco modos passam por **dois** pontos de validação: o Laboratório usa
`contexto="laboratorio"`; Treino, Oráculo, Escape Room **e RPG** usam
`"oraculo"`.

Esta é a checagem que **não** deve ser ligada fora do Laboratório, e o motivo
é diferente do da outra. Ela exige fórmula, subfórmula **ou** passos. Medida
por banco, a divisão é limpa:

| banco | sem estrutura |
|---|---|
| EM (Treino/Oráculo) — 6.000 questões | **100%** |
| EF (Treino/Oráculo) — 1.600 | **100%** |
| RPG — 4.950 | **100%** |
| Laboratório EM — 1.320 | 0% |
| Laboratório EF — 440 | 0% |

Não é falso positivo de um verificador quebrado: é **design**. Questão de
exatas no Oráculo é conceitual por definição, e o próprio código apaga
fórmula e passos logo depois de validar — `_normalizar_questao_oraculo`, com
o comentário *"No Oraculo, exatas e conceitual: conta com formula e passo a
passo e o Laboratorio de Exatas"*. Exigi-los ali seria cobrar exatamente o
que a linha seguinte descarta.

A guarda fica. Está coberta por
`test_estrutura_de_exatas_continua_so_no_laboratorio`, que prende os dois
lados: a questão conceitual passa no Oráculo e é recusada no Laboratório.

### A explicação e o feedback param de ser texto de gaveta — feito em 03/09/2026

Visto na tela, questão de Educação Física gerada por IA sobre fisiologia do
exercício. A IA escreveu um parágrafo bom sobre ATP e fosfocreatina, e o que
chegou ao aluno tinha quatro defeitos, todos medidos:

1. **48% do texto na tela era molde** (335 de 650 caracteres). O montador de
   explicação tinha quatro vagas fixas (introdução, explicação, exemplo,
   complemento) e enchia as que sobravam com texto genérico; das quatro, só
   **duas** podiam vir da IA — o terceiro parágrafo que ela escrevia era
   jogado fora para o molde caber. Agora o texto da IA tem prioridade, na
   ordem em que foi escrito, e o molde só entra quando falta conteúdo de
   verdade.
2. **A chave de normalização vazava para a tela** — "Educacao Fisica" em vez
   de "Educação Física". Medido: **9 das 14 matérias** perdem acento na
   chave. `exibir_materia()` já existia para isso — é a regra "chave ×
   rótulo" do projeto — e o montador não a usava.
3. **A dificuldade era usada como tema.** `_tema_curto` tinha `"dificuldade"`
   na cadeia de fallback do rodapé de feedback; sem tema, saía "Treine mais
   uma questão sobre Médio". Trocado por `objeto_conhecimento` (o campo da
   BNCC que de fato nomeia o assunto) e, por último, a matéria.
4. **`_feedback_conceitual` só era alcançada em exatas.** Ela nomeia o que o
   aluno marcou e o que era a resposta certa; as outras dez matérias caíam
   num texto que serve para qualquer questão ("você escolheu uma alternativa
   que parece plausível..."). Agora é alcançada em todas, preservando o
   conselho próprio de cada matéria (Português/História/Geografia/Inglês
   continuam com a dica específica deles — só o "confundiu" genérico foi
   trocado por um que nomeia as alternativas).

O exemplo de Educação Física também mudou: dizia "observe regras, cooperação
e o objetivo da prática corporal", que contradizia o assunto quando o tema
era teórico (fisiologia, e não esporte).

`tests/test_explicacao_e_feedback.py`, 42 testes, 10/10 mutantes pegos.

### sin, cos, tan e log no passo final — feito em 03/09/2026

A mesma cegueira da raiz vale para o resto da lista de funções
transcendentes. `sin`, `cos`, `tan` e `log` também fazem o passo inteiro ser
pulado, e é nele que a resposta nasce em trigonometria e em logaritmo.
`_funcao_aproximada_incorreta` confere as quatro.

A armadilha aqui é **grau × radiano**, e é severa: `sin(30)` vale 0,5 em
graus e −0,988 em radianos. O Ensino Médio trabalha em graus, mas a IA às
vezes escreve o ângulo em radianos (`π/6`). A mesma ambiguidade existe em
`log` sem base: `log(100)` pode ser 2 (decimal, o padrão da escola), 4,605
(natural) ou 6,64 (base 2). Por isso a regra recusa **só quando nenhuma
leitura plausível fecha** — o mesmo princípio da checagem de raiz.

Medido: das 50.900 questões offline, **64** têm o padrão nos passos (via
`explicacao` tipo "resultado", não só `passos_resolucao` — foi aí que a nota
anterior errou ao dizer "nenhuma"), e **nenhuma** é recusada pela regra nova.

Três defeitos apareceram só ao medir contra os bancos reais, não ao ler o
código:

- **`\log_{2}(8)` nunca casava.** `_` é caractere de palavra, então `\b`
  entre `"log"` e `"_{2}"` não existe — a forma com base escrita passava
  incontestada. Trocado por `(?![a-z])`.
- **`pH = -log(10⁻³) = 3`** é a fórmula real do banco de Química, com
  expoente em **sobrescrito Unicode** (`⁻³`, não `^{-3}`). Sem resolver, os
  dois caracteres eram apagados em silêncio pelo normalizador e `10⁻³` virava
  só `10` — as 8 questões reais de pH seriam recusadas, todas verdadeiras.
- **`h = 50 · tan(60°) = 86,6`.** `tan(60°)` sozinho vale 1,73, não 86,6 — o
  resultado escrito inclui a multiplicação por 50. Comparar o valor cru da
  função contra ele reprovava uma questão que já estava certa (e quebrou um
  teste existente). Resolvido logo em seguida — ver abaixo.

`tests/test_trigonometria_e_log_no_passo_final.py`, 13/13 mutantes pegos.

### A função dentro de expressão maior passou a ser julgada (03/09/2026)

Ao ligar a checagem acima, o caso `h = 50 · tan(60°)` obrigou a desligá-la
quando havia coeficiente na frente — e isso deixou um buraco:
`h = 50 · tan(60°) = 999,9` passava incontestado.

A correção resolve a função **dentro** da expressão e avalia o todo:

```
h = 50 · tan(60) = 86,6
        ↓ resolve tan(60) nas duas leituras
h = 50 · (1,7320)  → 86,60   ✓ fecha
h = 50 · (0,3200)  → 16,00
```

A regra de ouro continua: como grau × radiano é ambíguo, cada leitura
plausível gera uma versão da expressão, e **só recusa quando nenhuma fecha**.
`2 · log(100) = 9` passa, porque 9,21 em log natural arredonda para 9.

Medido: **104 questões offline têm o padrão, 0 recusadas.**

Três detalhes que só apareceram por mutação:

- **O recorte no último separador não é enfeite.** Com dois `=` do lado
  esquerdo, avaliar tudo cola os números vizinhos — o normalizador apaga o
  `=` e `5 + 2 = 7 · tan(30)` vira `5+27·tan(30)`: 20,59 em vez de 4,04.
- **Partir só no `=` deixava escapar o `≈`.** A IA escreve
  `50 · tan(60) ≈ 999,9` sem `=` nenhum, e a linha inteira virava o
  "resultado". Agora parte em qualquer marcador.
- **Teto de 16 leituras.** Cada função ambígua dobra as combinações; com
  cinco seriam 32, e uma delas quase sempre bate por acaso — o que tornaria a
  checagem inútil em vez de segura.

10/10 mutantes pegos. Um deles mostrou que um teste meu não testava o que
dizia: chamava pela cascata, onde o regex nem casa uma linha sem resultado,
então a guarda ficava inalcançável. Passou a chamar a função direto.

### O aluno passa a saber que está carregando (04/09/2026)

Heurística 1 de Nielsen (visibilidade do estado). O aluno apertava "Gerar" e
a tela ficava parada até 26 s, sem nada dizendo que algo acontecia — o padrão
de quem acha que travou é apertar de novo, e cada clique era uma questão a
mais gerada.

O indicador vive em `web/templates/base.html`, num listener de `submit`. Três
detalhes que não são óbvios:

- **`setTimeout(0)` antes de desabilitar.** Desabilitar o botão dentro do
  próprio `submit` faz o navegador não enviar o `name`/`value` dele — o
  formulário chega ao servidor sem saber qual botão foi apertado.
- **`checkValidity()` antes de tudo.** Sem isso, um campo obrigatório vazio
  trava o envio e o botão fica girando para sempre.
- **`pageshow` com `persisted`.** Voltar pelo histórico traz a página do cache
  do navegador, com o botão ainda desabilitado. Sem destravar, a tela do
  histórico fica morta.

O CSS usa `currentColor`, para o giro funcionar em botão claro e escuro, e
respeita `prefers-reduced-motion`.

### O tempo de resposta voltou a ser medido no Laboratório e no Oráculo (04/09/2026)

Medido: 53 dos 107 logs reais não tinham tempo. O Laboratório é o modo **mais
usado** e era o que não anotava — a causa era só uma linha ausente: nascia o
desafio e ninguém marcava quando. O Treino já fazia certo.

`registrar_log_com_tempo` + um `_tempo_inicio` no desafio. O painel do
professor já sabia mostrar o dado; faltava o dado.

### A dificuldade chega ao banco numa grafia só (04/09/2026)

Estava gravada em quatro grafias — `Difícil`, `Dificil`, `difícil`, `dificil`
— então qualquer contagem por dificuldade dividia o mesmo grupo em quatro.

`normalizar_dificuldade` em `core/config.py` reaproveita `_chave_materia`, que
já tira acento **e** emoji. A chave vai sem acento para o banco; a tela mostra
com acento por `exibir_dificuldade`. É a mesma regra chave × rótulo da seção
acima, aplicada a outro campo.

Migração `20260903130000_dificuldade_uma_grafia.sql`, aplicada — os dados
antigos foram unificados junto.

### A BNCC parou de ser inventada e passou a ser gravada por todos os modos (04/09/2026)

Três defeitos que se escondiam um atrás do outro:

1. **O código estava no campo errado.** `BNCC_REFERENCIAS` guarda o código no
   terceiro lugar da tupla, mas ele era desempacotado como `habilidade` e
   gravado em `habilidade_bncc`. A coluna `codigo_bncc` ficava vazia — e um
   teste existente (`test_fundamental_offline_bank`) *cobrava* o defeito,
   exigindo que `habilidade_bncc` começasse com "EF".
2. **O RPG inventava.** `RPG-QUI-01` não é código de habilidade nenhum, e a
   competência era a string `"RPG educacional: <perfil>"`. Isso é pior que
   campo vazio: aparece no painel com cara de referência oficial. 14.650
   questões.
3. **Metade dos modos não gravava.** Laboratório (os dois frontends), RPG (os
   dois) e Escape Room não mandavam nada; Oráculo, Treino, ENEM e Boss Rush
   mandavam três dos quatro campos, faltando justamente o código.

Cobertura: **0 → 50.900** de 50.900 questões com código válido e descrição
legível. Nada a aplicar no banco — a coluna já existia.

`habilidade_bncc` passou a guardar a frase, não o código: `EM13MAT101` não diz
nada a quem lê o relatório. As descrições são **resumos**, não transcrição
literal — está escrito assim no arquivo, e o texto oficial fica no link
`fonte_bncc` que cada questão já carrega.

Mutação começou em 8/11. Os três sobreviventes eram das rotas: meus testes
liam o *texto* do arquivo, e trocar o valor por `None` mantém a palavra lá.
Viraram teste de comportamento, exercitando a rota Flask do Laboratório, o
`log_da_resposta_rpg` do Streamlit e a rota Flask do RPG. Terminou 11/11.

### O README mentia em três pontos que quebravam (04/09/2026)

Não era "desatualizado" no sentido leve. Quem seguisse o texto travava:

1. `pip install -r requirements.txt` + `python flask_app.py` — o
   `requirements.txt` virou o do Streamlit Cloud (que exige esse nome) e não
   instala Flask. `ModuleNotFoundError` na primeira execução.
2. `README_ORDEM_EXECUCAO.txt` mandava aplicar cinco migrations com prefixo
   `20260427`, arquivos que não existem mais. Travava no primeiro item.
3. O mesmo arquivo dizia "DEV MODE, com RLS desativado" e mandava criar
   policies "antes de ativar RLS". O bootstrap faz o **oposto**: habilita RLS
   em todas as tabelas sem criar policy nenhuma (negação total, de propósito,
   porque o acesso passa pelo backend com a service_role). Seguir aquela
   instrução abriria o banco.

Além disso o README ignorava o frontend Streamlit inteiro, listava Python 3.11
(o `runtime.txt` diz 3.12), citava 2 dos 6 provedores de IA e 6 dos 8 modos.

Isso envelheceu porque **documentação não roda**. A correção é a mesma do guia
de acesso em PDF: `tests/test_readme_confere_com_o_projeto.py`, 13 testes que
cobram só o verificável — caminhos que existem, comandos que instalam o que
mandam rodar, versões que batem com `runtime.txt`, migrations que não são
fantasmas. Prosa não é cobrada, de propósito.

Verificado contra os documentos antigos: **10 dos 13 falham**. Os 3 que passam
são os pontos em que o texto antigo estava certo.

Duas armadilhas na escrita dos próprios testes:

- **O número exato de testes é uma armadilha de deriva.** Prometer "2.211
  testes" quebra no próximo teste escrito. Virou piso ("mais de 1.000 funções
  de teste"), que só quebra se alguém apagar testes em massa.
- **Meu primeiro teste de RLS proibia a frase "RLS desativado"** — e reprovava
  o texto novo, que cita a frase para dizer que estava errada. O dano real não
  era a frase, era a *instrução* que vinha junto. É ela que o teste proíbe.

### O desenvolvedor entra global, nos dois frontends (08/09/2026)

Entrar como `desenvolvedor` devolvia a **área do aluno** — a vitrine de modos.
O ADM existia, mas como sétima aba do painel do professor: uma área de um
papel escondida dentro da área de outro.

Os dois frontends erravam de jeitos **diferentes**, o que é pior que errarem
igual. No Streamlit a home era a mesma para todos (`_renderizar_dashboard` só
checava `_eh_aluno`). No Flask, `home_fla.index` já mandava professor e
desenvolvedor direto para a gestão — mas os dois para o *mesmo* painel.

Agora são duas áreas explícitas nos dois: **Professor** e **ADM**. E a área de
Professor ganhou a aba de professores cadastrados, agrupada por escola.

**A Chave Mestra saiu.** A porta do ADM antes do login pedia uma senha única
combinada entre pessoas. Ela é anterior à tabela de usuários — a migração
`20260803120100_usuarios.sql` veio *"substituir a senha mestra única por uma
tabela real, com senha em hash"* — e a troca tinha parado no meio, com este
argumento escrito no código:

> "A chave continua valendo onde ainda faz sentido: a tela de escolher escola
> oferece o ADM ANTES de qualquer login... Lá não existe usuário para
> consultar, então a chave é a única porta."

O argumento estava errado. A conta de desenvolvedor é **global**:
`conta_pode_entrar` devolve `True` para ela sem sequer olhar a escola. Sempre
deu para autenticar antes de escolher unidade. Enquanto a chave existisse, ela
era a porta mais fraca da casa — e é a porta mais fraca que define a tranca.

**E o código da escola saiu do caminho dele.** Para chegar ao ADM, o
desenvolvedor tinha de escolher uma unidade e digitar o código dela: a chave
de uma casa para entrar em outra. Pior no caso que mais importa — para
cadastrar a *primeira* escola era preciso o código de uma escola que ainda não
existe. O código continua obrigatório para todo mundo: ele é o combinado que o
professor passa à turma, e quem administra já lê todos eles no ADM.

Reserva, se ninguém souber a senha do desenvolvedor: `scripts/seed_usuarios.py`
(upsert da conta), que exige a chave do Supabase. `SENHA_MESTRA` pode ser
apagada do Render e do Streamlit Cloud.

33/33 mutantes pegos, em tres rodadas. Um sobreviveu na primeira e era o
próprio defeito relatado: meus testes chamavam a home do desenvolvedor
**direto**, então desligar o desvio que leva até ela mantinha tudo verde. A
função estava certa; ninguém chegava nela. O erro nunca esteve na tela de
destino, esteve no caminho — e o teste tinha o mesmo ponto cego.

A porta do ADM ficou igual nos dois: o formulario de usuario/senha mora na
propria tela inicial do Flask tambem, e nao mais num link para o `/login`. Ele
fica atras de um clique (`?adm=1`) porque quem chega nessa tela e aluno, e um
par usuario/senha aberto no meio da entrada convida a turma a tentar. A rota
nova leva o **mesmo** limite de tentativas do login -- sem ele seria um desvio
em volta da tranca. E `MOTIVO_ADM_RECUSADO` passou a morar em
`services/auth_service.py`, porque agora sao duas telas mostrando a frase.

Duas armadilhas na escrita dos testes:

- O roteiro da bancada corta cada linha em 90 caracteres. Procurar o título da
  tela ali reprovava a tela certa, e o assert **negativo** com a mesma frase
  era vazio — verdadeiro porque a frase nunca aparece.
- `_pediu_senha` varria o roteiro inteiro, e o painel tem campos de senha de
  propósito *depois* do portão (redefinir a de um aluno, a de uma conta).
- `setTimeout` nao serve de prova de redirect: o indicador de carregamento do
  `base.html` tambem usa. `window.location.href` e o que de fato redireciona --
  a mesma armadilha que `tests/test_tela_selecionar_escola.py` ja documenta.
- Afirmar que o carimbo de sessao EXISTE nao prova que `marcar_login` rodou: o
  `after_request` carimba qualquer sessao nova. O que `marcar_login` faz e
  ZERAR os dois relogios, e so um teste que entra com relogio velho pega isso.
  O mutante que apagava a chamada sobreviveu ate esse teste existir.

### O "±" era apagado por nós, e a legenda podia pedir o impossível (09/09/2026)

Três defeitos vindos da mesma sessão no Laboratório. Os dois primeiros estão
consertados; o terceiro virou prompt.

**1. O filtro de caracteres comia o "±".** A tela mostrava Bhaskara como
`x = (-b √Δ)/(2 a)` — sem o sinal ela não produz as duas raízes que o passo
seguinte apresentava. A IA escreveu o sinal; quem apagou fomos nós.

`_remover_caracteres_nao_latex` aceita ASCII e pula direto para `À` (U+00C0).
Toda a faixa U+0080–U+00BF cai fora, **em silêncio**. Medido:

| a IA escreve | o aluno via |
|---|---|
| `x = (-b ± √Δ)/(2a)` | `x = (-b √Δ)/(2a)` |
| `x = (-7 ± 5)/4` | `x = (-7 5)/4` |
| `sen(30°) = 0,5` | `sen(30) = 0,5` |
| `T = 25 °C` | `T = 25 C` |
| `d = 5 µm` | `d = 5 m` |

O último muda o valor por 10⁶ sem avisar.

**Este bug já tinha sido achado uma vez**, para o `·` (U+00B7), e o comentário
em `_normalizar_entrada_formula` descreve a causa com precisão — mas a
correção tratou só aquele caractere. Era uma classe, não um caso. Agora há
tabela (`_SIMBOLOS_LATIN1_EM_LATEX`) e um teste que cobra a **classe**:
qualquer símbolo dessa faixa que entre sem tradução reprova.

**2. A legenda declarava variável que nenhuma fórmula usava.** *"Triângulo
equilátero de lado 12, calcule a área do círculo circunscrito"*, com fórmula
`A = πR²` e legenda citando `a = lado do triângulo`. Nada liga `a` a `R`: o
aluno tem o lado, precisa do raio e não recebeu como sair de um para o outro.
Faltava `R = a√3/3`.

A causa era o próprio prompt, que dizia *"subformulas deve vir vazio na
maioria dos casos"* — pressão contra exatamente o que a questão exigia.

Validação nova (`legenda-com-variavel-sem-formula`), só no Laboratório: é o
único modo que preserva fórmula e legenda. Medido: **0 de 7.200** questões do
banco offline seriam recusadas.

**3. O passo da substituição vinha com letras.** O 3º passo trazia
`x = (-b ± √Δ)/(2a)` e o resultado aparecia do nada. O prompt **já pedia**
"mostrar a substituicao dos valores" e a IA não obedeceu — por isso agora ele
*mostra* a forma esperada, com um exemplo em que o passo tem números.

Duas armadilhas na escrita da regra, que só a mutação pegou:

- comparar com fronteira de palavra **recusava Bhaskara correta**: em `(2a)` e
  `4ac` as variáveis vêm coladas. Procurar a letra crua também não serve,
  porque `\Delta` contém um "a" e `\sqrt` contém um "r";
- legenda escrita como `\Delta = discriminante` não era sequer reconhecida
  como declaração, e escapava da checagem inteira.

11/11 mutantes pegos.

**O script de medição não rodava.** `scripts/medir_resolucao_simbolica.py`
usava `.not_`, que o cliente próprio deste projeto não tem — ele quebrava em
`'_SupabaseQuery' object has no attribute 'not_'`. Como ainda não havia dado
para medir, ninguém tentou e o erro esperou lá. Corrigido (o filtro foi para
o Python).

### A ajuda entrou no app (09/09/2026) — heurística 10

A única documentação era um PDF **fora** do sistema, entregue à mão. Falha por
dois lados: o aluno que trava no meio de uma questão não tem onde olhar, e
quem tem o PDF pode estar lendo uma versão velha.

O que **não** foi feito: escrever um texto de ajuda novo. Seriam três
descrições dos mesmos oito modos — PDF, Flask, Streamlit — e a segunda vez que
alguém mexesse numa delas as outras discordariam. Foi exatamente assim que o
guia de acesso envelheceu.

O texto mora em `core/ajuda.py`, **sem marcação**, e cada lugar aplica a sua: o
PDF embrulha em `<b>` para o ReportLab, as duas telas renderizam HTML. O
gerador do guia passou a importar de lá, e há teste cobrando que sejam o
*mesmo objeto*, não "um texto parecido".

Decisões que valem registrar:

- **Aberta sem login.** Metade das dúvidas ("o que é o código da escola?",
  "por que a primeira tela demora?") acontece ANTES de entrar — exatamente
  quando uma página presa atrás do login não seria alcançável. Ela não lê dado
  de aluno nenhum.
- **No rodapé de `base.html`, e não só na barra de cima.** Login, escolher
  escola e digitar o código *zeram* o bloco `topnav`, e são justamente as
  telas onde a dúvida aparece. No rodapé, nenhuma tela futura nasce sem ela.
- **Pesquisável**, com filtro client-side que ignora acento — no teclado do
  celular o acento nem costuma ser sugerido. Client-side também porque
  continua funcionando com o servidor em repouso, que é uma das dúvidas que a
  própria página responde.
- **O prazo da sessão é perguntado ao código**, nunca escrito: foi um número
  escrito à mão que fez o guia antigo mentir.
- A seção do painel só aparece para professor: pôr na ajuda do aluno uma área
  que ele não abre é ruído, e ruído é o que faz ninguém ler a ajuda de novo.

13/13 mutantes. Um sobreviveu na primeira rodada e mostrou um teste fraco meu:
eu procurava `data-ajuda-busca` em qualquer lugar do corpo, e o atributo
também aparece no seletor do JavaScript — apagá-lo do input deixava o campo
morto e o teste verde. Passou a exigir o atributo dentro da tag `input`.

Conferido no navegador: o filtro reduz a página, seção sem resultado some
junto com o título, "matematica" acha "Matemática", e o link aparece no rodapé
da tela de login.


### O aluno passa a saber quando a questão veio do banco (09/09/2026) — heurística 9

Quando a IA falha, o app serve uma questão do banco próprio para a atividade
não parar. Isso é bom — mas o aluno não era avisado, e o padrão do defeito era
o mesmo em três modos: **o trabalho estava feito e era jogado fora na última
etapa.**

Medido antes de mexer, nos oito modos do Flask:

| modo | estado |
|---|---|
| Oráculo, Treino, Laboratório, RPG | avisavam |
| ENEM | pílula escrita "offline" — rótulo, não explicação |
| Boss Rush | montava `origem_label` e não mostrava em lugar nenhum |
| Escape Room | gravava `estado["aviso_ia"]` e não passava ao template |
| Guildas | não gera questão |

E havia **dois marcadores** para a mesma informação — `_origem_geracao`
(Laboratório, RPG, cálculo) e `_origem` (ENEM, Boss Rush). É assim que o ENEM
acabou com uma pílula: quem escreveu o aviso não conhecia o segundo nome.
Agora `core/origem_questao.py` entende os dois e é a única fonte da frase,
para os dois frontends.

**A mensagem também mudou.** Era *"A IA não retornou uma questão válida agora.
Usei o banco offline para manter o treino funcionando."* Três problemas para
quem lê com 15 anos no meio de uma atividade valendo nota: "Usei" (quem é
"eu"?), "banco offline" (jargão nosso) e — principalmente — ela conta o
problema e não diz o que fazer. O aluno fica sem saber se a questão vale.

Agora: *"Esta questão veio do banco de questões do próprio EducaGame, já
revisado — a geração por inteligência artificial não respondeu a tempo. Pode
responder normalmente: a questão vale pontos como qualquer outra."*

No Streamlit, cinco das sete telas já chamavam `renderizar_origem_questao`
(a minha primeira medição procurou os nomes errados e disse que eram três).
Faltavam ENEM e Boss Rush, e a função mostrava a legenda "Questão gerada em
modo offline" — o mesmo meio-caminho da pílula do ENEM.

15/15 mutantes. Um teste antigo (`test_flask_parallel_structure`) reprovou a
mudança porque amarrava a FRASE ao arquivo em que ela morava — virou teste de
comportamento. E um teste meu nasceu errado: procurar `"eu "` como substring
casa dentro de "respond**eu** a tempo".

Conferido no navegador: o aviso aparece acima da questão, e some quando a
questão vem da IA.

### Acentuação — a regra é chave x rótulo

Feito: as mensagens de tela (Python **e** templates) estão acentuadas, e
`tests/test_acentuacao_das_mensagens.py` cobra isso nos dois sentidos.

A metade que exigiu cuidado foi a outra: boa parte das strings sem acento
aqui é **chave**, não texto. `"Matematica"` e `"Educacao Fisica"` são o nome
normalizado da matéria, `"Facil"/"Medio"/"Dificil"` vão para a sessão e para
o log, e `core/text_cleanup.py` casa padrões contra texto já sem acento.
Acentuar qualquer uma delas não seria ortografia — seria mudar comportamento
em silêncio.

A separação que já existia e virou regra: **a chave fica como está e ganha um
rótulo ao lado.** `MATERIAS_COM_ACENTO`, `LABEL_AREA`, e agora
`LABEL_DIFICULDADE` — este último porque as duas telas de simulado mostravam
a chave crua, e o aluno lia "Facil" e "Dificil" na própria lista de escolha.

Fora do teste de propósito, com o motivo: os bancos offline de questões. Lá
*pratica* (verbo), *faca* (a de cortar) e *media* (do inglês *social media*)
aparecem corretos sem acento — a lista de palavras reprovaria texto certo.

O conteúdo dos bancos não precisa de varredura: ele é acentuado **na hora de
exibir**, por `core/text_cleanup.py`. O que estava faltando lá eram palavras,
não uma correção arquivo por arquivo — 71 entradas novas, medidas no que
chegava cru à tela (`"Uma familia fara uma viagem... A distancia total"`).

Sobrou uma sobra conhecida, e o motivo é o mesmo de sempre: `"Idade Media"`
(`services/fundamental_conteudo_especifico.py`) é **chave** de tema, e
*media* está fora do dicionário por causa de *social media*. Acentuar a chave
quebraria a busca do tema; o certo seria um rótulo ao lado, como as outras.
Fica anotado, é uma linha na tela do Fundamental.

### Secret Files do Render — pronto, não migrado

O gerador existe:

```bash
python scripts/gerar_env_para_secret_file.py
```

A regra que decide se ajuda ou atrapalha: `load_dotenv(override=True)` faz o
Secret File **ganhar** das variáveis do painel. Ou migra tudo e apaga as
antigas, ou não migra nada — misturar faz o painel mostrar um valor e a app
usar outro, e depurar isso é péssimo.

---

## Refatoração que sobrou

### Telas do Streamlit — a bancada existe agora

`renderizar_tela_rpg` era a maior função do projeto (570 linhas) e estava
parada aqui há muito tempo, com o motivo escrito: tela de Streamlit não
devolve valor, então não dava para fotografar entrada → saída.

**O que faltava era enxergar qual é a "saída" de uma tela:** a sequência de
chamadas que ela faz ao Streamlit. `tests/apoio_streamlit.py` troca o
Streamlit por um dublê que anota essa sequência. Com isso valeu a mesma
receita de sempre, e a função caiu para 339 linhas.

**A bancada serve para as outras cinco telas** — era ela o trabalho, não a
extração.

### Outras funções longas

O `services/ia/enigma.py` está feito. `invocar_enigma` 171 → 64 e
`invocar_enigma_laboratorio` 131 → 43, com 64 testes e a política de rejeição
dos dois modos fundida numa função só.

**As cinco de UI do Streamlit estão feitas:**

| função | antes | depois |
|---|---|---|
| `tela_administrador` | 233 | **38** |
| `renderizar_aba_analises` | 212 | **122** |
| `renderizar_aba_treino` | 192 | **87** |
| `_tela_quiz` | 189 | **102** |
| `_usos_dia_a_dia_laboratorio` | 152 | **8** |

O padrão que apareceu nas cinco: **a maior parte do que estava lá dentro não
desenhava nada.** Era cálculo, tabela de dados ou montagem de dicionário,
embrulhado em tela — e por isso sem teste nenhum, porque ninguém chama meia
tela. Extraído, testa-se direto; três dos cinco arquivos de teste novos não
usam a bancada.

Cada uma foi fotografada antes e depois (a sequência de chamadas ao Streamlit,
em 11 a 14 cenários) e verificada por mutação. Total: **117 testes novos, 49
defeitos plantados, 49 pegos.**

O que a extração encontrou, sem estar procurando:

- **`tempo` virando `nan`** no boletim do ENEM/Boss Rush/Escape Room. Era
  `row.get("tempo_resposta", 0) or 0`, e o `or 0` não guardava nada: o ausente
  em pandas é `NaN`, que é **verdadeiro**. Um único NaN contamina a média.
  Corrigido.
- **O mesmo dicionário de histórico montado duas vezes** em `_tela_quiz`, um
  por caminho (tempo esgotado × clique). Doze chaves que precisavam ficar
  iguais para o PDF do simulado sair certo. Fundido.
- **Duas colisões de marcador** no cartão "onde usamos isso" — ver abaixo.
- `criterio_pdf = "materia"` atribuído igual nos dois ramos de um `if`: nunca
  foi decisão.

### As duas telas do RPG — feito em 02/09/2026

Eram as duas maiores funções do projeto: `renderizar_tela_rpg` (339, já caída
de 570) e `_renderizar_desafio_rpg` (277). Ficaram para o fim de propósito —
tela de Streamlit não devolve valor, então a rede tinha de vir antes.

Saíram **seis funções** que não desenham nada. O critério não foi tamanho, foi
onde estava o risco: **é aqui que o XP e o HP do aluno mudam**, e era a única
parte da tela sem teste nenhum.

| função | o que faz |
|---|---|
| `contexto_do_desafio` | as etiquetas acima da pergunta |
| `aplicar_resposta_ao_estado` | XP, HP, recompensa e histórico ao **responder** |
| `log_da_resposta_rpg` | o registro que alimenta o painel do professor |
| `aplicar_escolha_ao_estado` | XP e HP ao **escolher a ação**, antes da pergunta |
| `guardar_desafio_no_estado` | arma a pergunta e anota o tema sem repetir |
| `passo_da_cronica` | uma linha da crônica da jornada |

`_renderizar_desafio_rpg` 277 → 225, `renderizar_tela_rpg` 339 → 312.
`tests/test_estado_do_rpg.py` (32 testes), **26/26 mutantes pegos**.

Duas coisas que só apareceram por medir, e não por ler:

- **A fotografia de 15 cenários não cobria o clique.** Ela desenha as telas,
  mas nunca aperta nada — e o clique é onde o estado muda. Foi preciso uma
  segunda fotografia (`foto_clique`) com 8 casos, comparando o estado *depois*:
  XP, HP, risco, crônica, fase. Foi ela que pegou `passo_da_cronica` lendo
  `estado`, que não é parâmetro dela.
- **Essa fotografia chamou a IA de verdade na primeira rodada** — gastou cota e
  não repetia o resultado duas vezes. `gerar_desafio_academico` e
  `continuar_aventura` são as duas únicas funções do motor que falam com a
  rede; seladas, o resto é determinístico (`_rng` é semeado por opção e fase).

E um teste meu que nasceu vazio: o piso do HP na **escolha** usava o motor
real, cujo dano imediato nunca passou de 1 HP naquela cena — o `max(0, ...)`
podia ser arrancado com o teste verde. Dano menor que o HP não encosta no piso.

Os cinco `if` de `contexto_do_desafio` também sobreviviam a tudo: os chips
saem dentro de um bloco de HTML grande que o roteiro corta antes de chegar
lá. Foram cobertos testando a função direto, um campo por vez.

### Colisão de marcadores no cartão do Laboratório — resolvida

O cartão "onde usamos isso no dia a dia" era escolhido pelo **primeiro**
marcador que casasse. Isso dava o cartão errado sempre que um marcador
genérico de uma regra aparecia numa questão de outra. Medido contra **1070
questões** do banco offline do Laboratório: **117 (11%) iam para o cartão
errado**, em quatro pares:

| questão | ia para | por causa de |
|---|---|---|
| `quantos mol em 558 g com massa molar 186` | força | `"massa"` ⊂ `"massa molar"` |
| `corpo de 4 kg acelera a 3 m/s^2, qual a força` | velocidade | `"m/s"` ⊂ `"m/s^2"` |
| `qual massa corresponde a 23 mol, M = 44 g/mol` | força | empate 1 a 1 |
| `uma base forte tem pH acima de 7` | área e medidas | `"base"` do triângulo |

**Casar por palavra inteira não resolveria nenhum deles** — e eu tinha dito
que essa era a saída boa. `"massa"` é palavra inteira dentro de `"massa
molar"`, e `"base"` é palavra inteira na frase de química. O que falta não é
limite de palavra, é **corroboração**.

A regra passou a ser **quem casa mais marcadores**, com a ordem servindo só de
desempate (`>`, não `>=`). Onde não há sinal melhor, nada muda: *"uma mola
comprime sob força de 10 N"* casa `"mol"` e `"forca"`, 1 a 1, e força continua
vencendo por vir antes.

Mais um marcador entrou junto: `"g/mol"` na regra de mol, porque um template
do banco escreve `M = 44 g/mol` em vez das palavras "massa molar". Sozinho ele
corrige 39 questões e não mexe em mais nada.

Medido depois: a taxa de queda no cartão genérico **não muda** (255 nas duas,
23%), então não se perdeu cobertura — as 117 mudanças são todas correções.

Descartada por medição: escolher pelo **marcador mais longo**. `"concentracao"`
tem 12 letras e `"ph"` tem 2, então toda questão de pH viraria concentração e
o cartão de pH ficaria inalcançável.

### Trigonometria e proporção entraram no banco offline

O cartão de trigonometria não aparecia nenhuma vez nas 1070 questões, e puxar
esse fio deu num defeito maior: **`ALIASES_TEMAS_LAB` prometia dois temas que
o banco não tinha** — `trigonometria` (com os apelidos seno, cosseno e
tangente) e `proporcao`. Quem pedia trigonometria recebia estatística, taxas e
índices ou probabilidade condicional. Falha muda: a tela abre, a questão vem,
e só quem confere o assunto percebe.

Os dois temas agora existem (20 questões cada, como os outros): uma rampa com
`h = c·sen(30°)` e uma regra de três. O banco de Matemática foi de 400 para
440 questões, e os 13 cartões passaram a ser todos alcançáveis.

Mudar a contagem de templates (20 → 22) revelou um segundo defeito, escondido
havia tempo: `casos[(indice // 20) % len(casos)]` tinha um **20 fixo**
duplicando o número de templates — justamente o valor que a função já recebia
pronto em `k`. Enquanto os dois coincidiram ninguém notou; ao divergirem, duas
equações do 2º grau passaram a se repetir na mesma rodada. Corrigido para usar
o `k`, o que é exatamente equivalente ao comportamento antigo.

### Roteamento de tema — resolvido

Os 7 desvios (pedir um tema e receber outro) tinham **uma causa só**: o seletor
juntava todas as questões compatíveis e sorteava entre elas, sem distinguir
*quão* compatíveis eram. Pedir "energia cinética" trazia trabalho mecânico
junto, porque "energia" está entre os apelidos dele.

Agora o seletor fica só com o casamento mais direto — **nome exato vence
contenção, que vence apelido**. Medido nas 124 consultas do mapa: muda 17, e
todas as 17 são o mesmo movimento, estreitar para o tema mais específico.
Nenhuma consulta perdeu a resposta certa. Os 42 temas voltam por si.

Duas guardas entraram junto, as duas da forma que este projeto já conhece —
marcador curto casado como pedaço de texto:

- **contenção só vale com corpo** (lado curto ≥ 4 letras): sem isso `"pa"`
  casa dentro de "es**pa**cial", e pedir geometria espacial devolvia PA;
- **apelido casa como palavra**, não como pedaço: `"dinamica"` casava dentro
  de "termo**dinamica**", e pedir termodinâmica devolvia questão de força.
  Medido: muda 6 das 158, todas casamento espúrio saindo.

Aqui casar por palavra inteira **era** a saída certa — ao contrário dos
cartões, onde o problema era falta de corroboração, não de fronteira. São dois
defeitos parecidos com remédios diferentes, e vale saber distinguir.

### Perguntas repetidas — resolvido

As 16 repetições de Matemática eram todas de `funcao logaritmica`: base fixa em
2 e expoente em `3 + (k % 4)`, ou seja **quatro perguntas para vinte valores de
k**. Cinco bases × quatro expoentes dão exatamente 20 pares, um por k. Os três
bancos estão em 440 questões e 440 perguntas distintas.

### A receita que funcionou (para reaproveitar)

1. fotografar a função inteira — entrada → saída, byte a byte;
2. escrever a rede de comportamento;
3. **verificar a rede plantando defeitos de propósito;**
4. extrair fatiando o texto do fonte, nunca redigitando;
5. conferir que a fotografia bate.

O passo 3 é o que não dá para pular, e as duas rodadas provaram por quê: nas
duas, a rede passou inteira de primeira **e mesmo assim deixou mutantes
vivos.** Nas duas vezes o furo foi o mesmo — um teste que passava pelo motivo
errado, porque o payload era barrado por uma checagem anterior à que o teste
dizia cobrir. É o modo de falha típico deste tipo de teste.

Na segunda rodada o sobrevivente foi o mais útil: apontou que faltava provar
a única coisa que a fusão podia quebrar.

### CSS do Flask — **não precisa**

Já está certo: `web/static/css/flask.css` é arquivo de verdade, sem `<style>`
solto em template nem CSS dentro de Python. O Streamlit tinha esse problema
porque não serve arquivo estático; o Flask sempre serviu.

---

## Validação do Laboratório — resolvida

Física, Química e Matemática estão feitos. Os três eram o mesmo defeito:
texto casado como pedaço, não como palavra ou unidade.

| | antes | depois |
|---|---|---|
| Física/Química — recusa questão boa | 11 de 28 | **0** |
| Física/Química — aceita questão ruim | 5 de 11 | **0** |
| Matemática — recusa questão boa | 9 de 17 | **0** |
| Matemática — aceita questão ruim | 0 de 8 | **0** |

Em Matemática não deu para completar uma lista, porque número de Matemática
pura não carrega unidade. O critério virou estrutural: **a conta tem de
aparecer feita**, não apenas anunciada — um trecho sem incógnita, com operador
entre dois números. `15 - 5` conta; `2x + 5 = 15` não.

Só *remover* a lista de palavras não bastaria — medi antes de decidir: daria 9
→ 1 nos falsos positivos, mas 0 → **2** nos falsos negativos, passando a
aceitar resolução que só repete o enunciado ou só mostra o resultado.

Redes: `tests/test_unidades_laboratorio.py` e
`tests/test_conta_efetuada_laboratorio.py`.

## Varredura dos outros modos — o que foi olhado

Depois de três defeitos do mesmo tipo, varri o projeto atrás do padrão:
marcador curto procurado como pedaço de texto. **38 listas.**

A maioria é de símbolos (`{`, `\`, `^`, `±`, `√`, `(`, `+`) — símbolo não se
esconde dentro de palavra, e procurar por pedaço ali está certo. Ficam como
estão.

O que a varredura encontrou foi outra coisa, e já está corrigido: **"esta série
é de Ensino Médio?" estava escrita em cinco lugares**, um por modo, com listas
diferentes. A do Laboratório no Streamlit não tinha `MEDIO` sem acento — para
`ano_escolar = "Ensino Medio"` ela respondia Fundamental enquanto o resto do
sistema respondia Médio, e o aluno via só Matemática no Laboratório, sem Física
nem Química. Agora é uma só, em `core/config.py`, com
`tests/test_serie_ensino_medio.py` cobrando que os quatro caminhos concordem.

Sobraram três marcadores que examinei e **decidi não mexer**, com o motivo:

- `"solu"` em `core/answer_equivalence.py` — casa dentro de "absoluto", mas só
  atua quando a alternativa tem exatamente dois números, e o efeito de um falso
  positivo é tratar duas alternativas como equivalentes. Estreito demais para
  justificar risco.
- `"raz"` em `services/ia/validacao.py` — casa dentro de "prazo", mas o campo é
  a fórmula, onde "prazo" não aparece.
- `"em"` em `services/rpg_service.py` — resolvido junto com a unificação acima.

## Validação da IA — resolvida

O Oráculo de Inglês caía no banco offline na maioria das vezes, e o mesmo
acontecia com as humanas. Era **uma raiz só**: a checagem exigia que a
explicação apontasse para *uma única* alternativa, e recusava quando não
conseguia decidir. Isso cobrava prova; o que ela existe para pegar é
contradição — a IA marcar uma alternativa e explicar outra.

A regra agora só recusa quando alguma alternativa é nomeada pela explicação
**e a marcada não está entre elas**.

| | antes | depois |
|---|---|---|
| humanas/linguagens — recusa questão boa | 3 de 10 | **0** |
| humanas/linguagens — aceita questão ruim | 0 de 4 | **0** |
| formatos comuns de inglês recusados | 3 de 6 | **0** |

Rede: `tests/test_alternativa_contradita.py`.

### O log não pode mais matar uma questão

Achado no mesmo dia, nos logs:

```
[LAB] Falha ao gerar desafio; usando fallback offline seguro:
UnicodeEncodeError: 'charmap' codec can't encode character ' '
```

A IA gerou uma questão válida com um espaço estreito sem quebra; o `print`
do log morreu ao escrevê-lo em cp1252, a exceção subiu e a questão foi
descartada. Corrigido no boot dos dois frontends: a saída passa a substituir
o caractere impossível em vez de levantar. Rede:
`tests/test_log_nao_derruba_questao.py`.

### O app estragava o inglês que ele mesmo ensinava — resolvido

`aplicar_acentos_pt` conserta o ASCII que a IA e o banco offline escrevem.
Duas entradas legítimas em português são palavra comum em inglês:

| no dicionário | mas em inglês |
|---|---|
| `ate` → `até` | *ate* é o passado de *eat* |
| `area` → `área` | *area* é a mesma palavra |

`services/ia/normalizacao.py` já cuidava disso (todo `aplicar_acentos_pt` lá
está sob `if not modo_ingles`). **A camada de apresentação do Flask refazia a
correção sem saber a matéria**: `texto_explicacao` chama a função em cima do
que o serviço tinha acabado de proteger. Medido de ponta a ponta:

```
servico:  The simple past of "eat" is "ate". She ate lunch...
tela:     The simple past of "eat" is "até". She até lunch...
```

A explicação da resposta certa contradizia a resposta certa — num modo em que
a grafia **é** a lição.

A correção não foi tirar `ate` e `area` da lista (isso custaria dois termos
comuns em Matemática e Física): o reconhecimento de idioma mora dentro da
própria função, então protege as seis rotas de uma vez, inclusive as que não
têm como saber a matéria. Rede:
`tests/test_acentos_nao_estragam_ingles.py`, verificada por mutação — 5
defeitos plantados, 5 pegos, incluindo "consertar removendo as duas palavras".

### Inglês — resolvido em 03/09/2026, e não era o que a nota dizia

**A pendência antiga estava velha.** Ela dizia que a regra dos 4 caracteres
de `_texto_menciona_opcao` rejeitava metade dos formatos comuns de Inglês.
Remedido com payload completo pela cascata: **os seis passam**. Aquilo foi
resolvido quando `_explicacao_aponta_para_outra_alternativa` deixou de cobrar
*prova* (a explicação apontar para UMA alternativa) e passou a cobrar
*contradição* (apontar para OUTRA que não a marcada) — a nota não foi
atualizada junto.

**O defeito que existia de verdade era outro, e pior.**
`_texto_parece_portugues` guarda ~30 marcadores e casa por `any` — uma
palavra basta. Todos são inequívocos, **menos um**: `"observe"` também é
palavra inglesa, e das mais comuns em instrução pedagógica ("Observe the verb
form", "Observe that the adjective is short").

O estrago não era recusar a questão. Quando o campo principal "parecia
português", `_normalizar_resposta_ingles` **descartava a resposta inteira da
IA** e devolvia a do banco offline — em silêncio, sem passar por
`_motivo_rejeicao`, sem aparecer no log. Pior que recusar: não havia como
notar olhando os motivos de rejeição, porque nunca houve rejeição.

**Atinge quatro modos, não só o Oráculo.** Treino, Oráculo, Escape Room e RPG
passam todos por `invocar_enigma`, e os três bancos têm Inglês (2.000 EM +
400 EF + 950 RPG). O Laboratório não: só tem exatas.

A correção não remove o marcador — português com "observe" tem de continuar
caindo para o offline. Ele passa a exigir companhia: uma palavra que **não
existe em inglês**. Por isso `"do"`, `"no"`, `"a"`, `"as"`, `"e"` e `"com"`
ficaram de fora da lista de reforço — todas são palavras inglesas válidas, e
qualquer uma delas na lista reabriria o buraco.

`tests/test_ingles_nao_e_confundido_com_portugues.py`, 33 testes, 7/7
mutantes pegos. Os seis formatos da tabela antiga ficaram como rede: se
alguém voltar a cobrar prova em vez de contradição, eles caem juntos.

---

## Ideias que você levantou e não foram feitas

### Gestão de contas pelo site — feita

Era a única tabela sem interface. A aba ADM agora lista, vincula escola,
ativa/desativa, cria conta e gera senha nova, nos dois frontends, com as
regras em `services/usuario_service.py`.

Duas travas que valem saber:

- **Professor não nasce sem escola.** A conta seria criada e a pessoa
  descobriria no login que não entra em lugar nenhum. Recusa na hora, com o
  motivo na tela.
- **Não dá para desativar o último desenvolvedor ativo.** Um clique trancaria
  todo mundo do lado de fora do ADM, e a porta reserva (a Chave Mestra da tela
  inicial) depende de uma `SENHA_MESTRA` que pode nem estar configurada. Não
  haveria tela para desfazer — só SQL.

### Validação da IA que eu propus e você recusou

A IA às vezes devolve resolução que **não calcula nada** — deixa o Δ como
símbolo em vez de resolver, e o aluno não consegue seguir os passos. Dá para
rejeitar isso na validação.

Você recusou com razão: aumentaria a queda para o banco offline. Fica
registrado caso mude de ideia.

---

## Uma regra que vale para os testes daqui em diante

`get_runtime()` devolve o **módulo do streamlit** quando ele está em
`sys.modules`, e o contexto neutro quando não está. Em produção isso é o
adaptador funcionando: sob Streamlit usa o cache nativo, sob Flask usa o de
dois níveis.

**Em teste, isso é uma armadilha.** Um arquivo que faz `runtime = get_runtime()`
no import mede uma coisa quando roda sozinho e outra na suíte completa —
basta outro teste ter importado `st/ui/*` antes.

Foi assim que um defeito real ficou anos escondido: o cache devolvia o
próprio objeto guardado, e o teste que existia para pegar isso estava, na
suíte, medindo o cache do Streamlit. Verde no lugar onde se costuma olhar.

**Em teste, use `RuntimeContext()` direto.** Já está aplicado em
`test_runtime_context.py` e `test_cache_dois_niveis.py`; nenhum outro
arquivo tem o padrão hoje.

### A mesma armadilha, do outro lado: recarregar módulo

Teste de tela do Streamlit precisa tirar o módulo de `sys.modules` para ele
reexecutar `import streamlit as st` e pegar o dublê. Duas regras saíram disso,
as duas custaram um vermelho que só aparecia na suíte completa:

1. **Purgue só os módulos que você vai reimportar.** Uma purga larga
   (`st.ui*` + `ui.*`) derrubou `test_tela_guildas.py`, que não tem nada a ver
   com a mudança. E derrubou por ordem: verde sozinho, vermelho junto.
2. **Não faça monkeypatch por caminho de string** (`"ui.tela_guildas._x"`) em
   função que você importou no topo do arquivo. O caminho resolve o módulo na
   hora do patch; se alguém recarregou, o patch cai num objeto novo e a função
   que você tem em mãos continua vendo a original. Use
   `monkeypatch.setitem(funcao.__globals__, "_x", ...)` — é o namespace onde a
   própria função resolve os nomes, e não depende de identidade de módulo.

## Como o projeto se protege hoje

Vale saber que existe, para não refazer:

- **`test_fumaca_importacoes`** — importa os 44 módulos de interface dos dois
  frontends. Pega remoção de função compartilhada, que já quebrou o app duas
  vezes.
- **`test_fumaca_atributos`** — pega chamada em runtime (`rpg_engine.x`), que o
  teste de import não vê. Entende módulo injetado por argumento.
- **`test_sem_definicao_duplicada`** — nenhum módulo pode definir o mesmo nome
  duas vezes. A segunda vence em silêncio.
- **`test_env_example`** — o `.env.example` acompanha o que o código lê, nas
  duas direções.
- **`core/diagnostico_config.py`** — no boot, os dois frontends dizem no log o
  que está faltando ou suspeito na configuração.
- **`test_unidades_laboratorio`** — a alternativa de Fisica/Quimica carrega
  unidade de verdade. Prende as duas direcoes: `km/h` tem que passar e
  "12 bananas" nao. Verificada por mutacao: 13 plantados, 13 pegos.
- **`test_enigma_oracular`** — nenhuma frase que o modulo produz pode ser
  reprovada pelo criterio do proprio modulo, e todas as frases escritas tem
  que ser alcancaveis.
- **`test_oraculo_invocar_enigma`** e **`test_laboratorio_invocar_enigma`** —
  os dois modos de IA: tentativas, cada motivo de rejeição, o fallback
  offline, as regras por série e o formato de saída. Verificadas por mutação:
  31 defeitos plantados, 31 pegos. Os dois arquivos guardam **a mesma questão
  conceitual de exatas**, um esperando que ela seja aceita e o outro que seja
  recusada — é o par que impede um modo de herdar a regra do outro agora que
  compartilham a função de rejeição. Se mexer num, olhe o outro.

O que essas redes têm em comum: as duas piores falhas deste projeto foram do
tipo **"sobe bem e funciona errado, sem nada no log"**. Elas existem para
transformar isso em erro visível.
