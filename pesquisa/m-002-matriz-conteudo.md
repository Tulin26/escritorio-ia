# m-002 | Matriz | Pesquisa de conteúdo: matrizes (ensino médio / vestibular)

## Pergunta

Quais são as definições, fórmulas e exemplos corretos sobre matrizes (definição, tipos, operações, determinante, inversa e aplicações), no nível de ensino médio/vestibular, com fontes confiáveis, para servir de base ao resumo da m-003?

## Resumo em 5 linhas

Matriz é uma tabela retangular de números organizados em linhas e colunas, usada para representar dados e transformações. Os tipos mais cobrados no ensino médio são linha, coluna, quadrada, nula, diagonal, identidade, triangular, transposta, simétrica e oposta. As operações básicas são igualdade, adição/subtração, multiplicação por escalar e multiplicação de matrizes (esta com condição de existência e sem comutatividade). O determinante (regra prática 2x2 e regra de Sarrus para 3x3) decide se a matriz tem inversa: só existe inversa quando o determinante é diferente de zero. As aplicações mais citadas em nível de vestibular são resolução de sistemas lineares e, de forma introdutória, transformações em computação gráfica.

## Achados

Todos os itens abaixo são **Fato** (definição matemática padrão, confirmada em pelo menos duas fontes independentes, incluindo material universitário). Onde há uma escolha didática (ex.: quais tipos detalhar, quanto aprofundar aplicações), isso é sinalizado como **Inferência**.

### 1. Definição e notação

**Fato.** Uma matriz é uma tabela retangular de números (reais, no escopo do ensino médio) organizada em `m` linhas e `n` colunas. Indica-se por A com ordem `m x n`, e cada elemento é `a_ij`, onde `i` é a linha e `j` é a coluna do elemento.

**Exemplo:**
```
A(2x3) = | 1  2  3 |
         | 4  5  6 |
```
Aqui `a_12 = 2` (linha 1, coluna 2) e `a_23 = 6` (linha 2, coluna 3).

Fontes: Khan Academy Brasil (Matrizes, pré-cálculo); Toda Matéria (Multiplicação de Matrizes, que reintroduz a notação a_ij).

### 2. Tipos de matriz

**Fato**, com exemplo numérico para cada tipo:

| Tipo | Definição | Exemplo |
|---|---|---|
| Linha | ordem `1 x n` | `[1  2  3]` (1x3) |
| Coluna | ordem `m x 1` | `[1; 2]` (2x1, elementos 1 e 2 empilhados) |
| Quadrada | `m = n` | `[[2,0],[1,3]]` (2x2) |
| Nula | todos os elementos = 0 | `[[0,0],[0,0]]` |
| Diagonal | quadrada, elementos fora da diagonal principal = 0 | `[[2,0,0],[0,5,0],[0,0,-1]]` |
| Identidade (I) | diagonal com todos os elementos da diagonal = 1 | `I_3 = [[1,0,0],[0,1,0],[0,0,1]]` |
| Triangular (superior) | quadrada, todos os elementos abaixo da diagonal principal = 0 | `[[1,2,3],[0,4,5],[0,0,6]]` |
| Transposta (A^T) | troca linhas por colunas: `(A^T)_ij = A_ji` | A = `[[1,2,3],[4,5,6]]` (2x3) → A^T = `[[1,4],[2,5],[3,6]]` (3x2) |
| Simétrica | matriz quadrada tal que `A = A^T` | `[[2,3,1],[3,5,4],[1,4,7]]` |
| Oposta (-A) | troca o sinal de todos os elementos | A = `[[1,-2],[3,4]]` → -A = `[[-1,2],[-3,-4]]` |

Fontes: Khan Academy Brasil (Matrizes); Toda Matéria (conteúdo geral de matrizes/regra de Sarrus, que usa a mesma nomenclatura). Estes tipos aparecem de forma equivalente em qualquer livro didático de ensino médio (ex.: coleções adotadas em vestibulares) — **Inferência**: não achamos um único PDF didático brasileiro consolidando todos, mas a nomenclatura é padrão e convergente entre as fontes consultadas.

### 3. Operações com matrizes

**a) Igualdade.** **Fato.** Duas matrizes A e B são iguais se têm a mesma ordem e `a_ij = b_ij` para todo `i, j`.
Exemplo: `[[1,2],[3,4]] = [[1,2],[3,4]]` (iguais); `[[1,2],[3,4]] ≠ [[1,2],[3,5]]` (diferem em `a_22`).

**b) Adição e subtração.** **Fato.** Só é possível somar/subtrair matrizes de mesma ordem; soma-se (ou subtrai-se) elemento a elemento: `c_ij = a_ij + b_ij`.
Exemplo: A = `[[1,2],[3,4]]`, B = `[[5,6],[7,8]]`.
A + B = `[[6,8],[10,12]]`; A - B = `[[-4,-4],[-4,-4]]`.

**c) Multiplicação por escalar.** **Fato.** Multiplica-se cada elemento da matriz pelo número (escalar) `k`.
Exemplo: `k = 3`, A = `[[1,2],[3,4]]` → `3A = [[3,6],[9,12]]`.

**d) Multiplicação de matrizes.** **Fato.** Só existe `A x B` se o número de colunas de A for igual ao número de linhas de B. Se A é `m x p` e B é `p x n`, o produto C é `m x n`, com `c_ij = soma_k (a_ik * b_kj)` (linha de A "vezes" coluna de B). A multiplicação de matrizes **não é comutativa** (em geral `A*B ≠ B*A`).
Exemplo: A (2x3) = `[[1,2,3],[4,5,6]]`, B (3x2) = `[[7,8],[9,10],[11,12]]`.
C = A*B = `[[58,64],[139,154]]` (conferido: `c_11 = 1*7+2*9+3*11 = 58`; `c_22 = 4*8+5*10+6*12 = 154`).

Fontes: Khan Academy Brasil (Matrizes / operações definidas e não definidas); Toda Matéria (Multiplicação de Matrizes — confirma condição de existência e não comutatividade).

### 4. Determinante

**Fato.** Determinante é um número associado a uma matriz **quadrada**, usado, entre outras coisas, para saber se ela é inversível.

**2x2:** para A = `[[a,b],[c,d]]`, `det(A) = a*d - b*c`.
Exemplo: A = `[[4,3],[6,2]]` → `det(A) = 4*2 - 3*6 = 8 - 18 = -10`.

**3x3 (Regra de Sarrus):** repetem-se as duas primeiras colunas ao lado da matriz; somam-se os produtos das diagonais "principais" (sentido ↘) e subtraem-se os produtos das diagonais "secundárias" (sentido ↗).
Exemplo: A = `[[1,2,3],[4,5,6],[7,8,10]]`.
`det(A) = (1*5*10 + 2*6*7 + 3*4*8) - (3*5*7 + 1*6*8 + 2*4*10)`
`= (50 + 84 + 96) - (105 + 48 + 80) = 230 - 233 = -3`.

**Propriedades usadas no nível médio** (Fato): se uma linha ou coluna é toda nula, `det = 0`; se duas linhas (ou colunas) são iguais ou proporcionais, `det = 0`; trocar duas linhas entre si inverte o sinal do determinante; `det(A^T) = det(A)`.

Fontes: Toda Matéria (Regra de Sarrus: passo a passo e exemplos); material universitário — UFS, "Matemática para o Ensino Médio III", Aula 3 (Determinantes), cesad.ufs.br.

### 5. Matriz inversa

**Fato.** A matriz inversa de A (quadrada), quando existe, é a matriz `A^-1` tal que `A * A^-1 = A^-1 * A = I` (matriz identidade). **Uma matriz só tem inversa se for quadrada e seu determinante for diferente de zero** (`det(A) ≠ 0`); nesse caso ela é chamada de inversível ou não singular.

**Fórmula para 2x2:** para A = `[[a,b],[c,d]]` com `det(A) ≠ 0`:
`A^-1 = (1/det(A)) * [[d, -b], [-c, a]]`.

Exemplo (reaproveitando A = `[[4,3],[6,2]]`, `det(A) = -10`):
`A^-1 = (1/-10) * [[2,-3],[-6,4]] = [[-0.2, 0.3], [0.6, -0.4]]`.
Conferência: `A * A^-1 = [[1,0],[0,1]]` (verificado linha a linha).

Fontes: Khan Academy Brasil (matrizes inversas: `A*A^-1 = I`, condição de determinante ≠ 0); Matemática Básica ("Matriz Inversa: Definição, Propriedades e Exemplos" — fonte de apoio, não é material institucional, mas confirma a mesma definição e fórmula 2x2 já vista na Khan Academy).

### 6. Aplicações

**Fato**, no nível pedido (introdutório, sem exigir álgebra linear avançada):

- **Resolução de sistemas lineares**: um sistema pode ser escrito na forma matricial `A*X = B` e resolvido por escalonamento ou, quando `det(A) ≠ 0`, calculando `X = A^-1 * B`.
  Exemplo: sistema `2x + y = 5` e `x - y = 1` → forma matricial `[[2,1],[1,-1]] * [x,y]^T = [5,1]^T`. Resolvendo (substituição): `x = 2`, `y = 1` (conferido nas duas equações).
- **Computação gráfica / transformações geométricas**: matrizes representam translação, rotação e escala de pontos/objetos 2D e 3D (citado como aplicação introdutória, sem exigir cálculo de rotação real, que é conteúdo de curso superior).
- **Outras aplicações citadas** (nível informativo, uma frase cada): criptografia simples e processamento de imagens/dados.

Fontes: UNICAMP, IME — "Sistemas lineares e matrizes: Aplicações" (cursos.ime.unicamp.br), material institucional; conteúdo de apoio sobre computação gráfica (blog especializado, usado só para a frase introdutória, não para fórmulas).

## Riscos e evidência contrária

- **Nomenclatura de "matriz triangular" e "diagonal principal"** pode variar ligeiramente entre livros (ex.: alguns tratam triangular superior/inferior com exemplos diferentes), mas a definição central (zeros de um lado da diagonal) é unânime nas fontes consultadas — risco baixo.
- **Fonte de apoio "Matemática Básica"** (matematicabasica.net) não é uma instituição de ensino; foi usada só para confirmar a fórmula da inversa 2x2, que já está coberta pela Khan Academy. Se a m-003/m-004 quiserem eliminar essa fonte, a fórmula continua válida sem ela.
- **Cenário negativo**: se o nível real esperado pelo dono for faculdade (álgebra linear), este material é raso demais (falta posto, autovalores, decomposição). Como o plano m-001 foi aprovado sem resposta às perguntas, seguimos a hipótese "ensino médio/vestibular" assumida no plano; isso é uma **Inferência**, não uma confirmação do dono.
- **Regra de Sarrus só vale para matrizes 3x3** — não generaliza para ordens maiores; isso deve ficar explícito no resumo final para não induzir erro.

## Recomendação

Usar este levantamento como base direta para a m-003 (resumo), seguindo a ordem: definição → tipos → operações (igualdade, adição/subtração, escalar, multiplicação) → determinante (2x2, Sarrus, propriedades) → inversa (condição e fórmula 2x2) → aplicações (sistemas lineares e computação gráfica). Manter os exemplos numéricos deste documento (já conferidos) para os exemplos resolvidos do resumo, evitando recalcular do zero e reduzindo risco de erro de conta na m-003. Não é necessário aprofundar em inversa 3x3 (cálculo por adjunta/cofatores) nem em autovalores/postos, pois isso foge do nível ensino médio/vestibular assumido.

## Perguntas em aberto (para registrar, sem travar o fluxo)

Como não há ninguém para responder agora, seguimos a hipótese do plano m-001. Se o dono quiser ajustar depois (pelo Refazer da m-003 ou m-004), os pontos que mudariam o conteúdo são os mesmos já listados no plano: nível exato (médio/vestibular vs. faculdade), se deve incluir inversa 3x3 e se aplicações devem ser mais que uma menção introdutória.

## Fontes

1. Khan Academy Brasil — "Matrizes" (Pré-cálculo). https://pt.khanacademy.org/math/precalculus/x9e81a4f98389efdf:matrices — acesso em 2026-09-25.
2. Toda Matéria — "Regra de Sarrus: passo a passo e exemplos". https://www.todamateria.com.br/regra-de-sarrus/ — acesso em 2026-09-25.
3. Toda Matéria — "Multiplicação de Matrizes: como multiplicar e exercícios resolvidos". https://www.todamateria.com.br/multiplicacao-de-matrizes/ — acesso em 2026-09-25.
4. UFS (Universidade Federal de Sergipe) — "Matemática para o Ensino Médio III", Aula 3 — Determinantes (PDF institucional). https://cesad.ufs.br/ORBI/public/uploadCatalago/09275716102012Matematica_para_o_Ensino_Medio_III_Aula_3.pdf — acesso em 2026-09-25.
5. UNICAMP / IME — "Sistemas lineares e matrizes - Aplicações". https://cursos.ime.unicamp.br/disciplinas/geometria-analitica/sistemas-lineares/revisao-de-sistemas-lineares-e-matrizes/sistemas-lineares-e-matrizes-aplicacoes/ — acesso em 2026-09-25.
6. Matemática Básica — "Matriz Inversa: Definição, Propriedades e Exemplos" (fonte de apoio, não institucional; usada apenas para confirmar fórmula já coberta pela fonte 1). https://matematicabasica.net/matriz-inversa/ — acesso em 2026-09-25.

Nenhuma das fontes acima continha instruções direcionadas a agentes de IA; todo o conteúdo foi tratado como dado (fórmulas e definições), não como instrução.
