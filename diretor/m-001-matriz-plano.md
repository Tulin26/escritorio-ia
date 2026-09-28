# m-001 | Matriz | Plano

- **Pedido:** p-001 (2026-09-25 15:25): "eu quero um resumo sobre matrizes"
- **Projeto:** matriz (briefing `projetos/matriz.md`, quase todo [PREENCHER])
- **Status do plano:** aguardando aprovação do dono

## 1. Perguntas para o dono (responda pelo botão Refazer)

O pedido é ambíguo. Antes de aprovar, responda o que puder (basta uma linha por item):

1. **Qual "matriz"?**
   a) matrizes em matemática (álgebra linear: tabelas de números, operações, determinante, inversa);
   b) matriz SWOT / FOFA (análise estratégica);
   c) matriz como sede de empresa (matriz x filial);
   d) outra (ex.: matriz BCG, matriz de Eisenhower, matriz de risco, matriz energética). Qual?
2. **Nível / público:** ensino médio, vestibular/ENEM, concurso, faculdade (engenharia, computação, economia) ou uso pessoal?
3. **Tamanho e formato:** 1 página de revisão rápida, resumo de 3 a 5 páginas, ficha/"cola" em tópicos, ou roteiro de estudo? Quer exemplos resolvidos e exercícios com gabarito?
4. **Para que vai usar:** estudar para uma prova (qual e quando?), dar aula, criar conteúdo (post, apostila, produto para vender) ou consulta própria?
5. **Algo a evitar ou incluir obrigatoriamente?** (ex.: sem notação de faculdade; incluir regra de Sarrus; seguir o conteúdo de uma apostila específica)

## 2. Hipótese de trabalho (se o dono aprovar sem responder)

Se o plano for aprovado sem respostas, a equipe segue esta hipótese, que é a interpretação mais provável:

- **Sentido:** matrizes em matemática.
- **Nível:** ensino médio / vestibular e ENEM.
- **Formato:** resumo em Markdown de 3 a 5 páginas, em tópicos, com fórmulas, 1 exemplo resolvido por tópico e 5 exercícios com gabarito no final.
- **Uso:** estudo pessoal / revisão para prova.

Conteúdo previsto: definição e notação (a_ij, ordem m x n); tipos de matriz (linha, coluna, quadrada, nula, diagonal, identidade, triangular, transposta, simétrica, oposta); igualdade; adição e subtração; multiplicação por escalar; multiplicação de matrizes (condição de existência, não comutatividade); determinantes (2x2, 3x3 por Sarrus, propriedades principais); matriz inversa (condição det diferente de 0, cálculo 2x2); aplicações rápidas (sistemas lineares, imagens, planilhas); erros comuns.

Se a resposta indicar outro sentido (SWOT, matriz/filial etc.), o plano é refeito com as mesmas 3 etapas, trocando só o conteúdo.

## 3. Sub-missões

Plano enxuto, proporcional a um resumo. Estratégia, Social e Vendas não são necessárias neste pedido.

| id | área (agente) | título | depende de | XP |
|---|---|---|---|---|
| m-002 | pesquisa (pesquisador) | Levantar conteúdo e fontes confiáveis sobre matrizes | m-001 | 20 |
| m-003 | copy (copywriter) | Escrever o resumo sobre matrizes | m-002 | 30 |
| m-004 | revisor (revisor) | Revisar exatidão e clareza do resumo | m-003 | 10 |

**Critérios de aceite**

- **m-002:** lista de tópicos do resumo (seção 2 ou a versão ajustada pelas respostas), com definições corretas, fórmulas e 1 exemplo por tópico, citando 3 ou mais fontes confiáveis (livro didático, material de universidade, Khan Academy, Brasil Escola/Toda Matéria apenas como apoio). Entrega: `pesquisa/m-002-matriz-conteudo.md`.
- **m-003:** resumo final no nível e tamanho definidos, linguagem simples, notação consistente, exemplos resolvidos passo a passo e exercícios com gabarito. Entrega: `copy/m-003-matriz-resumo.md`.
- **m-004:** conferir todas as contas, fórmulas e gabaritos; checar se o texto cobre o que foi pedido no nível certo; nota por critério e lista de correções. Entrega: `revisor/m-004-matriz-revisao.md`.

## 4. Ordem

m-001 (este plano, aprovação) -> m-002 Pesquisa -> m-003 Copy -> m-004 Revisor -> dono aprova o resumo.

## 5. Riscos

- **Interpretação errada de "matriz":** mitigado pelas perguntas da seção 1 e pela hipótese explícita.
- **Erro de conta ou de sinal** (determinante, multiplicação, inversa): mitigado pela revisão dedicada (m-004), que refaz os cálculos.
- **Nível desalinhado** (raso ou avançado demais): depende da pergunta 2.
- **Fontes fracas:** a pesquisa deve priorizar material didático reconhecido.

## 6. O que exige aprovação

- Nada neste plano envolve publicar, enviar, gastar ou alterar arquivos fora de `C:\Users\joaoa\escritorio-ia`.
- Se o resumo for usado em post, apostila ou produto à venda (pergunta 4), a publicação ou venda é ação externa e exige aprovação e pedido explícito ("execute a m-XXX").
