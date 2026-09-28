// Painel online: acorda a equipe disparando a rotina do Claude Code na nuvem (claude.ai/code/routines).
// Configuração (variáveis do Vercel): ROTINA_URL (termina em /fire) e ROTINA_TOKEN (gerado na tela da rotina).
const { ErroEscritorio } = require('./escritorio');

// Cabeçalho beta exigido pelo /fire enquanto as rotinas estão em research preview.
const BETA = process.env.ROTINA_BETA || 'experimental-cc-routine-2026-04-01';

async function chamarRotina(motivo) {
  const url = process.env.ROTINA_URL;
  const token = process.env.ROTINA_TOKEN;
  if (!url || !token) throw new ErroEscritorio(500, 'Falta configurar ROTINA_URL e ROTINA_TOKEN no Vercel.');
  const r = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'anthropic-beta': BETA,
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: motivo }),
  });
  const dados = await r.json().catch(() => ({}));
  if (!r.ok) {
    const detalhe = (dados.error && dados.error.message) || r.statusText;
    const dica = r.status === 429 ? ' Pode ser o limite diário de rotinas do plano; tente mais tarde.' : '';
    throw new ErroEscritorio(502, `A rotina do Claude não aceitou o chamado (${r.status}: ${detalhe}).${dica}`);
  }
  return dados.claude_code_session_url || '';
}

module.exports = { chamarRotina };
