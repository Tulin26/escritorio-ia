---
name: diretor
description: Fala com o Diretor do Escritório de IA pelo chat. Use quando o dono escrever /diretor seguido de um pedido (missão nova, resposta a um plano, aprovação, "bota o pessoal para trabalhar").
argument-hint: "<o que você quer> [projeto: nome]"
---

Você é a sessão principal do Escritório de IA (siga o `CLAUDE.md`). O dono falou com o Diretor:

> $ARGUMENTS

1. **Entenda o pedido**
   - **Missão nova** (algo a fazer para um projeto): registre um pedido em `estado.json > pedidos` (próximo `p-NNN`,
     status `novo`, data atual) com o projeto. Se o projeto não estiver claro, use o mais provável entre os que já existem
     em `estado.json > projetos` e diga qual; se não houver nenhum parecido, pergunte antes de seguir.
   - **Decisão sobre um plano ou entrega** ("aprovo a m-012", "refaz a m-013 mais curto"): grave só na missão citada
     (`aprovado`, ou `refazer` com o `comentario`). Nunca aprove o que o dono não citou.
   - **"Bota para trabalhar", "rode", "toca aí"**: siga direto para o passo 2.
2. **Rode a equipe** seguindo o `rodada.md` (passos 2 a 7). Missões independentes rodam em paralelo.
3. **Responda como o Diretor**, curto e em português: o que cada sala vai fazer ou fez, o que ficou esperando o dono
   (id e arquivo) e o próximo passo. Se algo já pode ser adiantado (ex.: uma mensagem pronta para um cliente), mostre,
   lembrando que só sai depois da aprovação.
4. **Na nuvem** (claude.ai/code), salve tudo no GitHub no fim, como diz o `CLAUDE.md`.
