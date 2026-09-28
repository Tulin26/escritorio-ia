// Painel online (Vercel): o que as rotas de api/ têm em comum.
const { ErroEscritorio, trabalhoPendente } = require('./escritorio');
const { logado } = require('./auth');

// Uma rodada da nuvem que passou disso sem avisar que terminou é considerada perdida.
const LIMITE_RODADA_MS = 45 * 60 * 1000;

// Mesmo formato do _automacao do servidor local, para o painel React tratar os dois do mesmo jeito.
function statusNuvem(estado) {
  const r = estado.rodadaNuvem || {};
  const inicio = Date.parse(r.iniciadaEm || '');
  const rodando = Boolean(r.rodando) && Number.isFinite(inicio) && Date.now() - inicio < LIMITE_RODADA_MS;
  let ultima = null;
  if (r.rodando && !rodando) {
    ultima = { fim: '', ok: false, erro: 'a rodada passou de 45 minutos sem avisar que terminou; abra a sessão para ver o que houve', motivo: r.motivo, sessao: r.sessao };
  } else if (r.fim) {
    ultima = { fim: r.fim, ok: r.ok !== false, erro: r.erro || '', motivo: r.motivo, sessao: r.sessao, resumo: r.resumo || '' };
  }
  return {
    modo: 'nuvem',
    ativa: Boolean(process.env.ROTINA_URL && process.env.ROTINA_TOKEN),
    rodando,
    inicio: rodando ? r.inicio : null,
    motivo: rodando ? r.motivo : '',
    sessao: r.sessao || '',
    ultima,
    pendentes: trabalhoPendente(estado),
  };
}
const comAutomacao = (estado) => ({ ...estado, _automacao: statusNuvem(estado) });

function mesmaOrigem(req) {
  const origem = req.headers.origin;
  if (!origem) return true;
  try {
    return new URL(origem).host === (req.headers['x-forwarded-host'] || req.headers.host);
  } catch {
    return false;
  }
}

// Envolve cada rota: método, origem, login e erros num formato só ({ erro }).
function rota(metodo, tratar, { publica = false } = {}) {
  return async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');
    try {
      if (req.method !== metodo) throw new ErroEscritorio(405, 'método não permitido');
      if (metodo === 'POST') {
        if (!mesmaOrigem(req)) throw new ErroEscritorio(403, 'origem não permitida');
        if (!String(req.headers['content-type'] || '').includes('application/json')) throw new ErroEscritorio(415, 'use application/json');
      }
      if (!publica && !logado(req)) throw new ErroEscritorio(401, 'Entre com a senha do painel.');
      await tratar(req, res, req.body || {});
    } catch (e) {
      if (!(e instanceof ErroEscritorio)) console.error(e);
      res.status(e.status || 500).json({ erro: e instanceof ErroEscritorio ? e.message : 'Erro inesperado no servidor do painel.' });
    }
  };
}

module.exports = { rota, statusNuvem, comAutomacao };
