# m-004 | Matriz | Revisão do resumo (m-003)

- **Entrega revisada:** m-003 — `copy/m-003-matriz-resumo.md`
- **Base usada:** briefing `projetos/matriz.md`, plano `diretor/m-001-matriz-plano.md`, pesquisa aprovada `pesquisa/m-002-matriz-conteudo.md`.
- **Anexos da missão:** nenhum (m-004 não tem anexos).

## Tabela de notas

| Critério | Nota (1-5) | Justificativa curta |
|---|---|---|
| Precisão | 5 | Todas as contas, fórmulas e gabaritos refeitos de forma independente e nenhum erro encontrado. |
| Completude | 5 | Cobre 100% dos tópicos do plano (m-001) e da recomendação da pesquisa (m-002): definição, tipos, operações, determinante 2x2/Sarrus, inversa 2x2, aplicações, erros comuns, 5 exercícios com gabarito, pendências. |
| Clareza | 5 | Linguagem direta, notação explicada logo no início, exemplos passo a passo em todas as contas centrais. |
| Acionabilidade | 5 | Pendências deixam claro o que o dono precisa confirmar antes de aprovar (sentido de "matriz", nível, uso); nada de externo é sugerido sem aprovação. |
| Concisão | 5 | Sem clichês, sem enrolação; cada seção só tem o que o nível ensino médio/vestibular pede. |

**Veredito: pode ir para aprovação.** Nenhum problema GRAVE ou MÉDIO encontrado. Há só observações LEVES (lista abaixo), nenhuma delas bloqueia a aprovação.

## Contas refeitas (todas, independentemente)

Refiz cada conta do zero, sem olhar o resultado do m-003 antes de calcular, e só depois comparei.

| # | Conta | Resultado do m-003 | Meu recálculo | Confere? |
|---|---|---|---|---|
| 1 | a_12 e a_23 de A(2x3)=[[1,2,3],[4,5,6]] | a_12=2, a_23=6 | a_12=2, a_23=6 | Sim |
| 2 | Transposta de A(2x3)=[[1,2,3],[4,5,6]] | A^T=[[1,4],[2,5],[3,6]], ordem 3x2 | Idem | Sim |
| 3 | A+B, A-B com A=[[1,2],[3,4]], B=[[5,6],[7,8]] | A+B=[[6,8],[10,12]]; A-B=[[-4,-4],[-4,-4]] | Idem (c11=6, c12=8, c21=10, c22=12; A-B idem) | Sim |
| 4 | 3A com A=[[1,2],[3,4]] | [[3,6],[9,12]] | Idem | Sim |
| 5 | A(2x3)xB(3x2), A=[[1,2,3],[4,5,6]], B=[[7,8],[9,10],[11,12]] | [[58,64],[139,154]] | c11=1·7+2·9+3·11=58; c12=1·8+2·10+3·12=64; c21=4·7+5·9+6·11=139; c22=4·8+5·10+6·12=154 | Sim |
| 6 | det 2x2 de A=[[4,3],[6,2]] | -10 | 4·2-3·6=8-18=-10 | Sim |
| 7 | det 3x3 (Sarrus) de A=[[1,2,3],[4,5,6],[7,8,10]] | -3 | ↘: 1·5·10+2·6·7+3·4·8=50+84+96=230; ↗: 3·5·7+1·6·8+2·4·10=105+48+80=233; det=230-233=-3. Confirmado também por cofatores: 1(50-48)-2(40-42)+3(32-35)=2+4-9=-3 | Sim |
| 8 | A^-1 de A=[[4,3],[6,2]], det=-10 | [[-0.2,0.3],[0.6,-0.4]] | (1/-10)·[[2,-3],[-6,4]] = idem | Sim |
| 9 | Conferência A·A^-1 = I | linha a linha = [[1,0],[0,1]] | 4(-0.2)+3(0.6)=1; 4(0.3)+3(-0.4)=0; 6(-0.2)+2(0.6)=0; 6(0.3)+2(-0.4)=1 | Sim |
| 10 | Sistema 2x+y=5, x-y=1 | x=2, y=1 | x=1+y → 2(1+y)+y=5 → 3y=3 → y=1, x=2. Confere nas duas equações | Sim |
| 11 | Exercício 1: A+B, A-B (A=[[2,-1],[0,3]], B=[[1,4],[-2,5]]) | A+B=[[3,3],[-2,8]]; A-B=[[1,-5],[2,-2]] | Idem | Sim |
| 12 | Exercício 2: transposta de A=[[3,0,-1],[5,2,4]] | A^T=[[3,5],[0,2],[-1,4]], ordem 3x2 | Idem | Sim |
| 13 | Exercício 3: AxB (A=[[2,1],[0,3]], B=[[1,-1],[4,2]]) | [[6,0],[12,6]] | c11=2·1+1·4=6; c12=2·(-1)+1·2=0; c21=0·1+3·4=12; c22=0·(-1)+3·2=6 | Sim |
| 14 | Exercício 4a: det de A=[[5,2],[3,4]] | 14 | 5·4-2·3=20-6=14 | Sim |
| 15 | Exercício 4b: A^-1 de A=[[5,2],[3,4]] | [[2/7,-1/7],[-3/14,5/14]] | (1/14)·[[4,-2],[-3,5]] = [[4/14,-2/14],[-3/14,5/14]] = [[2/7,-1/7],[-3/14,5/14]] | Sim |
| 16 | Exercício 5: det de A=[[2,0,1],[1,3,-1],[0,2,4]] (Sarrus) | 30 | ↘: 2·3·4+0·(-1)·0+1·1·2=24+0+2=26; ↗: 1·3·0+2·(-1)·2+0·1·4=0-4+0=-4; det=26-(-4)=30. Confirmado por cofatores: 2(12+2)-0(4-0)+1(2-0)=28+2=30 | Sim |

**Resultado: as 16 contas conferidas batem exatamente com o m-003. Nenhum erro de sinal, de fórmula ou de gabarito encontrado.**

## Checagem de cobertura e nível

- Nível (ensino médio/vestibular, hipótese do plano m-001): respeitado — só determinante/inversa 2x2 e Sarrus 3x3, sem cofatores/adjunta, sem autovalores, sem posto. Confirma o que a pesquisa (m-002) recomendou não incluir.
- Tópicos do plano (seção 2 do m-001): definição/notação, tipos, operações (igualdade, adição/subtração, escalar, multiplicação), determinante (2x2 e Sarrus), inversa 2x2, aplicações (sistemas lineares, computação gráfica) — todos presentes. O resumo ainda adiciona "erros comuns" (bônus, não pedido mas coerente com o tom didático do briefing).
- Exercícios com gabarito: pedido no plano, entregue (5 exercícios inéditos + gabarito, todos conferidos acima).
- Pendências: o m-003 lista as mesmas incertezas do plano (sentido de "matriz", nível, uso, aprofundamento) e não assume nada alem da hipótese aprovada. Correto.
- Tamanho (3 a 5 páginas, pedido no plano): não pude medir em páginas reais (o documento é Markdown puro, sem paginação). Ver observação LEVE abaixo.

## Fontes conferidas

WebFetch direto foi **bloqueado pelo proxy de saída** para todos os domínios citados na pesquisa (khanacademy.org, todamateria.com.br, cesad.ufs.br, cursos.ime.unicamp.br) — erro `EGRESS_BLOCKED`. Usei WebSearch como alternativa, que retornou trechos indexados das próprias páginas citadas:

| Fonte | Confirma o que o m-003 usa? |
|---|---|
| Khan Academy Brasil — Matrizes (pré-cálculo) | **Sim.** Busca confirma notação `a_ij`, ordem `m x n`, e que a página cobre soma, subtração, multiplicação e inversa — igual ao que a seção 1 do resumo usa. |
| Toda Matéria — Regra de Sarrus | **Sim.** Trecho indexado descreve exatamente o método usado na seção 4.2 do resumo: repetir as duas primeiras colunas, somar as diagonais que descem, subtrair as que sobem. |
| Toda Matéria — Multiplicação de Matrizes | **Sim.** Trecho confirma a condição de existência (colunas de A = linhas de B) e a não comutatividade (A·B ≠ B·A em geral) — igual à seção 3.4 do resumo. |
| UFS/cesad — "Matemática para o Ensino Médio III", Aula 3 (Determinantes) | **Parcial.** O PDF existe no link citado e o título confirma que o tema é "Determinantes" (Unidade III). Não consegui ler o conteúdo completo (PDF bloqueado e busca não trouxe o texto das propriedades específicas: linha nula, linhas proporcionais, troca de sinal, transposta). Risco baixo porque essas propriedades são padrão em qualquer material de determinantes, mas não é uma confirmação linha a linha. |
| UNICAMP/IME — Sistemas lineares e matrizes - Aplicações | **Parcial.** A URL exata existe e o tema (sistemas lineares e matrizes, aplicações) confere com a citação. Não consegui confirmar o trecho específico sobre computação gráfica citado no resumo (não apareceu no snippet). |
| Matemática Básica (matematicabasica.net) — Matriz Inversa | **Não conferida nesta revisão.** Já é sinalizada como fonte de apoio (não institucional) tanto na pesquisa quanto nos riscos do m-002; a fórmula que ela sustenta (inversa 2x2) já está confirmada de forma independente pela Khan Academy e por conta própria refeita nesta revisão (ver tabela de contas). Risco baixo. |

Resumo: 5 de 6 fontes citadas foram verificadas (3 com confirmação plena, 2 com confirmação parcial de existência/tema por bloqueio de acesso direto); 1 não foi verificada nesta rodada. Nenhuma fonte contradisse o conteúdo do resumo.

## Checagem contra anexos

Não se aplica — a m-004 não tem anexos, e a m-003 também não usou anexos do dono (o conteúdo vem só da pesquisa aprovada m-002).

## Riscos legais e de reputação

Nenhum. É material de estudo pessoal sem marca, sem dados pessoais, sem comparação com terceiros e sem promessa comercial. A m-003 já sinaliza corretamente que publicar ou vender o material exige aprovação explícita antes de qualquer divulgação (seção "Pendências", item 3) — nenhuma ação externa foi ou está sendo executada.

## Problemas encontrados

1. `[LEVE]` Trecho: seção "4.3 Propriedades úteis" (as 4 propriedades do determinante) · Problema: as propriedades são listadas sem exemplo numérico, diferente do resto do documento, que sempre traz um exemplo por regra/fórmula (isso toca de raspão o item "fórmula sem exemplo" do proibido do briefing, embora sejam propriedades e não fórmulas centrais) · Correção sugerida: adicionar um exemplo rápido por propriedade (ex.: "linha nula → det=0" com uma matriz 2x2 de exemplo).
2. `[LEVE]` Trecho: tamanho geral do documento · Problema: o plano pede um resumo de "3 a 5 páginas"; o arquivo é Markdown puro (256 linhas), sem paginação real, então não dá para confirmar se cabe nesse intervalo quando exportado/impresso · Correção sugerida: ao exportar para PDF/Word para uso real, checar a contagem de páginas e cortar/condensar se passar de 5.
3. `[LEVE]` Trecho: fontes UFS (Determinantes) e UNICAMP/IME (Aplicações) · Problema: confirmação apenas parcial (existência e tema, não o conteúdo detalhado) porque o acesso direto às páginas foi bloqueado pelo proxy de rede nesta revisão · Correção sugerida: se o dono quiser 100% de certeza, reabrir esses dois links manualmente (fora deste ambiente) antes de usar o resumo para ensinar terceiros; para uso próprio o risco é baixo, pois as propriedades citadas são padrão em qualquer material de determinantes.
4. `[LEVE]` Trecho: fonte "Matemática Básica" (matematicabasica.net) · Problema: não foi verificada nesta rodada (nem por fetch nem por busca) · Correção sugerida: como ela só sustenta a fórmula da inversa 2x2, já confirmada por outra fonte e por conta própria, nenhuma ação é necessária; apenas registrando para transparência.

Nenhum problema GRAVE ou MÉDIO foi encontrado.

## Pontos fortes

- As 16 contas centrais e dos exercícios batem exatamente com o refazimento independente, incluindo o determinante 3x3 confirmado por dois métodos (Sarrus e cofatores).
- Notação explicada uma vez no início e usada de forma consistente até o fim.
- Nível respeitado com rigor (sem cofatores 3x3, sem autovalores/posto), exatamente como a pesquisa recomendou.
- Pendências e riscos herdados do plano/pesquisa foram mantidos de forma honesta, sem forçar uma certeza que não existe.
