
# Resumo de Matrizes — Ensino Médio / Vestibular

**Objetivo:** material de estudo/revisão sobre matrizes (matemática), para consulta antes de prova ou como ficha de revisão.
**Público:** estudante do ensino médio ou vestibular/ENEM, sem conhecimento prévio de álgebra linear de faculdade.
**Ângulo usado (hipótese, ver Pendências):** como o pedido original ("eu quero um resumo sobre matrizes") foi ambíguo e o plano `diretor/m-001-matriz-plano.md` foi aprovado sem respostas às perguntas, este documento segue a hipótese registrada no plano: matrizes em matemática, nível ensino médio/vestibular, resumo de 3 a 5 páginas em Markdown, com exemplos resolvidos passo a passo e exercícios com gabarito.
**Nota de formato:** por ser material de estudo (e não uma peça publicitária), este documento não segue o formato de variações A/B/C usado em copy de marketing — é uma única versão, completa, conforme pedido na missão m-003.

Todas as contas deste documento foram refeitas e conferidas durante a produção (ver seção "Conferência das contas" no final, antes do gabarito).

---

## 1. O que é uma matriz

Uma **matriz** é uma tabela retangular de números organizados em linhas e colunas. Ela serve para guardar e organizar dados, e para representar operações (como sistemas de equações) de forma compacta.

Uma matriz com `m` linhas e `n` colunas é dita de **ordem `m x n`** (lê-se "m por n"). Cada número dentro da matriz é chamado de **elemento**, indicado por `a_ij`, em que:

- `i` é o número da **linha** do elemento;
- `j` é o número da **coluna** do elemento.

**Exemplo:**

```
A(2x3) = | 1  2  3 |
         | 4  5  6 |
```

Essa matriz A tem ordem `2 x 3` (2 linhas, 3 colunas). O elemento `a_12` (linha 1, coluna 2) é `2`. O elemento `a_23` (linha 2, coluna 3) é `6`.

> Notação usada neste resumo: letras maiúsculas (A, B, C) para matrizes; letras minúsculas com dois índices (a_ij) para elementos; `A^T` para transposta; `A^-1` para inversa; `det(A)` para determinante; `I` para matriz identidade.

---

## 2. Tipos de matriz

| Tipo | Definição | Exemplo |
|---|---|---|
| Linha | tem apenas 1 linha (ordem `1 x n`) | `[1  2  3]` |
| Coluna | tem apenas 1 coluna (ordem `m x 1`) | coluna com elementos 1 e 2 |
| Quadrada | número de linhas = número de colunas | `[[2,0],[1,3]]` (ordem 2x2) |
| Nula | todos os elementos são zero | `[[0,0],[0,0]]` |
| Diagonal | quadrada, com zeros fora da diagonal principal | `[[2,0,0],[0,5,0],[0,0,-1]]` |
| Identidade (I) | diagonal com todos os elementos da diagonal principal iguais a 1 | `I_3 = [[1,0,0],[0,1,0],[0,0,1]]` |
| Triangular (superior) | quadrada, com zeros abaixo da diagonal principal | `[[1,2,3],[0,4,5],[0,0,6]]` |
| Transposta (A^T) | troca linhas por colunas da matriz original | ver exemplo abaixo |
| Simétrica | matriz quadrada em que `A = A^T` | `[[2,3,1],[3,5,4],[1,4,7]]` |
| Oposta (-A) | troca o sinal de todos os elementos | de `[[1,-2],[3,4]]` para `[[-1,2],[-3,-4]]` |

**Exemplo de transposta, passo a passo.** Seja A (ordem 2x3):

```
A = | 1  2  3 |
    | 4  5  6 |
```

Para transpor, a 1ª linha de A vira a 1ª coluna de A^T, a 2ª linha de A vira a 2ª coluna de A^T:

```
A^T = | 1  4 |
      | 2  5 |
      | 3  6 |
```

A^T tem ordem 3x2 (as ordens sempre se invertem na transposição).

---

## 3. Operações com matrizes

### 3.1 Igualdade

Duas matrizes só são iguais se têm a **mesma ordem** e todos os elementos correspondentes são iguais (`a_ij = b_ij` para todo `i, j`).

### 3.2 Adição e subtração

Só é possível somar ou subtrair matrizes de **mesma ordem**. Soma-se (ou subtrai-se) elemento por elemento: `c_ij = a_ij + b_ij` (ou `a_ij - b_ij`).

**Exemplo passo a passo.** A = `[[1,2],[3,4]]`, B = `[[5,6],[7,8]]`.

- `c_11 = 1 + 5 = 6`
- `c_12 = 2 + 6 = 8`
- `c_21 = 3 + 7 = 10`
- `c_22 = 4 + 8 = 12`

A + B = `[[6,8],[10,12]]`

A - B: `[[1-5, 2-6], [3-7, 4-8]] = [[-4,-4],[-4,-4]]`

### 3.3 Multiplicação por escalar (um número)

Multiplica-se **cada elemento** da matriz pelo número.

**Exemplo:** `k = 3`, A = `[[1,2],[3,4]]`. `3A = [[3*1, 3*2],[3*3, 3*4]] = [[3,6],[9,12]]`.

### 3.4 Multiplicação de matrizes

Só existe o produto `A x B` se o **número de colunas de A** for igual ao **número de linhas de B**. Se A tem ordem `m x p` e B tem ordem `p x n`, o produto C = A x B tem ordem `m x n`.

Cada elemento de C é calculado assim: `c_ij` = (linha `i` de A) "vezes" (coluna `j` de B), somando os produtos posição a posição.

**Importante:** a multiplicação de matrizes **não é comutativa** — em geral, `A x B ≠ B x A`.

**Exemplo passo a passo.** A (2x3) = `[[1,2,3],[4,5,6]]`, B (3x2) = `[[7,8],[9,10],[11,12]]`. Como A tem 3 colunas e B tem 3 linhas, o produto existe e terá ordem 2x2.

- `c_11` = linha 1 de A · coluna 1 de B = `1*7 + 2*9 + 3*11 = 7 + 18 + 33 = 58`
- `c_12` = linha 1 de A · coluna 2 de B = `1*8 + 2*10 + 3*12 = 8 + 20 + 36 = 64`
- `c_21` = linha 2 de A · coluna 1 de B = `4*7 + 5*9 + 6*11 = 28 + 45 + 66 = 139`
- `c_22` = linha 2 de A · coluna 2 de B = `4*8 + 5*10 + 6*12 = 32 + 50 + 72 = 154`

A x B = `[[58,64],[139,154]]`

---

## 4. Determinante

O **determinante** é um número associado a uma matriz **quadrada**. Ele serve, entre outras coisas, para saber se a matriz tem inversa.

### 4.1 Determinante de matriz 2x2

Para A = `[[a,b],[c,d]]`: `det(A) = a*d - b*c`.

**Exemplo passo a passo.** A = `[[4,3],[6,2]]`.

`det(A) = 4*2 - 3*6 = 8 - 18 = -10`

### 4.2 Determinante de matriz 3x3 (Regra de Sarrus)

A Regra de Sarrus **só vale para matrizes 3x3** (não funciona para ordens maiores). Passo a passo:

1. Repita as duas primeiras colunas da matriz ao lado direito dela.
2. Some os produtos das três diagonais que descem da esquerda para a direita (↘).
3. Subtraia os produtos das três diagonais que sobem da esquerda para a direita (↗).

**Exemplo.** A = `[[1,2,3],[4,5,6],[7,8,10]]`.

Repetindo as duas primeiras colunas:

```
1  2  3 | 1  2
4  5  6 | 4  5
7  8 10 | 7  8
```

Diagonais ↘ (somar): `1*5*10 = 50`; `2*6*7 = 84`; `3*4*8 = 96`. Soma: `50 + 84 + 96 = 230`.

Diagonais ↗ (subtrair): `3*5*7 = 105`; `1*6*8 = 48`; `2*4*10 = 80`. Soma: `105 + 48 + 80 = 233`.

`det(A) = 230 - 233 = -3`

### 4.3 Propriedades úteis

- Se uma linha ou coluna é toda formada por zeros, `det = 0`.
- Se duas linhas (ou colunas) são iguais ou proporcionais, `det = 0`.
- Trocar duas linhas de lugar inverte o sinal do determinante.
- `det(A^T) = det(A)` (transpor não muda o determinante).

---

## 5. Matriz inversa

A inversa de uma matriz quadrada A, quando existe, é a matriz `A^-1` tal que `A x A^-1 = A^-1 x A = I` (matriz identidade).

**Condição de existência:** A só tem inversa se `det(A) ≠ 0`. Nesse caso, A é chamada de **inversível** (ou não singular). Se `det(A) = 0`, a matriz não tem inversa.

**Fórmula para matriz 2x2.** Para A = `[[a,b],[c,d]]` com `det(A) ≠ 0`:

`A^-1 = (1 / det(A)) * [[d, -b], [-c, a]]`

**Exemplo passo a passo**, reaproveitando A = `[[4,3],[6,2]]`, cujo `det(A) = -10` (calculado na seção 4.1):

`A^-1 = (1/-10) * [[2, -3], [-6, 4]] = [[-0.2, 0.3], [0.6, -0.4]]`

**Conferência** (multiplicando A por A^-1, o resultado deve ser a identidade):

- `linha 1 de A · coluna 1 de A^-1 = 4*(-0.2) + 3*0.6 = -0.8 + 1.8 = 1`
- `linha 1 de A · coluna 2 de A^-1 = 4*0.3 + 3*(-0.4) = 1.2 - 1.2 = 0`
- `linha 2 de A · coluna 1 de A^-1 = 6*(-0.2) + 2*0.6 = -1.2 + 1.2 = 0`
- `linha 2 de A · coluna 2 de A^-1 = 6*0.3 + 2*(-0.4) = 1.8 - 0.8 = 1`

Resultado: `[[1,0],[0,1]] = I`. Confere.

> Este resumo cobre apenas a inversa de matrizes 2x2. O cálculo da inversa 3x3 (por cofatores/adjunta) é conteúdo mais avançado e não entrou aqui — ver Pendências.

---

## 6. Aplicações (introdução)

- **Sistemas lineares:** um sistema de equações pode ser escrito na forma matricial `A * X = B` e resolvido por escalonamento ou, quando `det(A) ≠ 0`, por `X = A^-1 * B`.

  **Exemplo passo a passo.** Sistema: `2x + y = 5` e `x - y = 1`.

  Forma matricial: `[[2,1],[1,-1]] * [x, y] = [5, 1]`.

  Resolvendo por substituição: da 2ª equação, `x = 1 + y`. Substituindo na 1ª: `2*(1+y) + y = 5` → `2 + 2y + y = 5` → `3y = 3` → `y = 1`. Logo `x = 1 + 1 = 2`.

  Conferência: `2*2 + 1 = 5` (ok); `2 - 1 = 1` (ok).

- **Computação gráfica:** matrizes representam translação, rotação e escala de imagens e objetos 2D/3D (aqui fica só como citação — o cálculo de rotação é conteúdo de faculdade).
- **Outras aplicações** citadas com frequência: criptografia simples e organização de dados em planilhas.

---

## 7. Erros comuns

- Tentar somar/subtrair matrizes de ordens diferentes (não é possível).
- Multiplicar matrizes sem checar se o número de colunas da 1ª é igual ao número de linhas da 2ª.
- Achar que `A x B = B x A` (em geral é falso).
- Usar a Regra de Sarrus em matrizes que não são 3x3 (ela só vale para 3x3).
- Calcular a inversa de uma matriz com `det(A) = 0` (não existe inversa nesse caso).

---

## 8. Exercícios

**1.** Dadas A = `[[2,-1],[0,3]]` e B = `[[1,4],[-2,5]]`, calcule A + B e A - B.

**2.** Encontre a transposta de A = `[[3,0,-1],[5,2,4]]`.

**3.** Dadas A = `[[2,1],[0,3]]` e B = `[[1,-1],[4,2]]`, calcule A x B.

**4.** Dada A = `[[5,2],[3,4]]`: (a) calcule `det(A)`; (b) calcule `A^-1`.

**5.** Calcule `det(A)` de A = `[[2,0,1],[1,3,-1],[0,2,4]]` usando a Regra de Sarrus.

### Gabarito

**1.** A + B = `[[3,3],[-2,8]]`; A - B = `[[1,-5],[2,-2]]`.

**2.** A^T = `[[3,5],[0,2],[-1,4]]` (ordem 3x2).

**3.** A x B = `[[6,0],[12,6]]` (cálculo: `c_11=2*1+1*4=6`; `c_12=2*(-1)+1*2=0`; `c_21=0*1+3*4=12`; `c_22=0*(-1)+3*2=6`).

**4.** (a) `det(A) = 5*4 - 2*3 = 20 - 6 = 14`. (b) `A^-1 = (1/14)*[[4,-2],[-3,5]] = [[2/7, -1/7], [-3/14, 5/14]]`.

**5.** `det(A) = 30` (cálculo: diagonais ↘: `2*3*4=24`, `0*(-1)*0=0`, `1*1*2=2`, soma `26`; diagonais ↗: `1*3*0=0`, `2*(-1)*2=-4`, `0*1*4=0`, soma `-4`; `det = 26 - (-4) = 30`).

---

## Conferência das contas

Todas as contas deste resumo (exemplos das seções 3, 4, 5 e 6, e os 5 exercícios do gabarito) foram recalculadas do zero durante a escrita, e as dos exercícios 4 e 5 foram conferidas por dois métodos (Sarrus e cofatores, no caso do determinante 3x3; multiplicação A x A^-1, no caso da inversa). Nenhuma diferença foi encontrada em relação à pesquisa aprovada em `pesquisa/m-002-matriz-conteudo.md`. Ainda assim, como pede o plano, a missão de revisão (m-004) deve refazer essas contas de forma independente.

---

## Pendências `[PREENCHER]`

Este resumo foi produzido a partir de uma **hipótese**, porque o pedido original era ambíguo e ninguém respondeu às perguntas do plano (`diretor/m-001-matriz-plano.md`). Se alguma destas respostas for diferente do presumido, o conteúdo deve ser refeito:

1. **Sentido de "matriz":** presumimos matrizes em matemática (álgebra linear básica). Se o pedido era sobre matriz SWOT, matriz de empresa (matriz x filial) ou outra matriz de negócios (BCG, Eisenhower, risco), este documento não serve e precisa ser todo reescrito.
2. **Nível:** presumimos ensino médio/vestibular. Se o nível real é faculdade, faltam tópicos (inversa 3x3 por cofatores, posto de matriz, autovalores, dependência linear).
3. **Uso:** presumimos estudo/revisão pessoal. Se o resumo vai virar post, apostila paga ou produto, isso é uma ação de publicação/venda e exige aprovação explícita antes de qualquer divulgação — nada aqui deve ser publicado sem esse passo.
4. **Aprofundamento de aplicações:** as aplicações da seção 6 são introdutórias, como recomendado pela pesquisa. Se o objetivo era aprofundar (ex.: computação gráfica com fórmulas de rotação), este resumo precisa de uma seção adicional.

Fonte do conteúdo: pesquisa aprovada em `pesquisa/m-002-matriz-conteudo.md` (Khan Academy Brasil, Toda Matéria, UFS/cesad, UNICAMP/IME). Os 5 exercícios da seção 8 e o gabarito são inéditos (compostos para este resumo), inspirados no mesmo nível dos exemplos da pesquisa, e todas as contas foram refeitas e conferidas nesta entrega.
