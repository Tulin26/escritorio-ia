# Escritório de IA

Painel em pixel art para organizar missões de vários projetos, com uma equipe de agentes por área
(Diretor, Pesquisa, Estratégia, Copy, Social, Vendas e Revisão). Nada é publicado, enviado ou gasto sem aprovação no painel.

## Requisitos

- [Node.js](https://nodejs.org) 18 ou mais novo (sem dependências, sem `npm install`)
- [Claude Code](https://claude.com/claude-code) instalado e logado (o comando `claude` precisa funcionar no terminal)

## Como rodar

```powershell
cd caminho\para\escritorio-ia
node server.js
```

Abra http://localhost:4321 no navegador e deixe a janela do terminal aberta.

## Como usar

1. Clique em **+ Nova missão**, escolha o projeto e descreva o que você quer.
2. O Diretor monta o plano, que aparece em **Aguardando sua aprovação**.
3. Clique em **Aprovar** para seguir, ou em **Refazer** com um comentário para pedir mudanças.
4. Cada aprovação faz a próxima etapa andar. As entregas ficam nas pastas de cada área, em `.md`.

## Estrutura

| Caminho | O que é |
|---|---|
| `server.js` | servidor do painel e automação das rodadas |
| `index.html`, `style.css`, `app.js` | painel |
| `estado.json` | agentes, projetos, pedidos e missões |
| `.claude/agents/` | instruções de cada agente |
| `CLAUDE.md` | regras do escritório |
| `projetos/` | briefing de cada projeto (`_modelo.md` é o modelo) |
| `diretor/`, `pesquisa/`, `estrategia/`, `copy/`, `social/`, `vendas/`, `revisor/` | entregas de cada área |

## Configuração opcional

| Variável | Padrão | Para quê |
|---|---|---|
| `PORT` | `4321` | porta do painel |
| `ESCRITORIO_AUTOMACAO` | ligada | `0` desliga as rodadas automáticas |
| `ESCRITORIO_MODELO` | `claude-opus-5-5` | modelo usado nas rodadas |
| `ESCRITORIO_ESFORCO` | `high` | nível de esforço das rodadas |

Exemplo: `$env:PORT=4322; node server.js`

Os agentes foram adaptados do projeto open source [ECC](https://github.com/affaan-m/ECC).
