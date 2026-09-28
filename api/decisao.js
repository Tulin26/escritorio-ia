// POST /api/decisao { id, acao: "aprovar" | "refazer", comentario }: sua decisão sobre uma entrega.
const { rota, comAutomacao } = require('../lib/nuvem');
const { alterarEstado } = require('../lib/github');
const { decidir } = require('../lib/escritorio');

module.exports = rota('POST', async (req, res, corpo) => {
  const verbo = corpo.acao === 'aprovar' ? 'aprovou' : 'pediu para refazer';
  const { estado } = await alterarEstado((e) => decidir(e, corpo), `Painel: ${verbo} ${String(corpo.id || '').slice(0, 20)}`);
  res.status(200).json(comAutomacao(estado));
});
