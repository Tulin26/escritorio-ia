// POST /api/pedido { projeto, texto }: nova missão para o Diretor (vira um commit no estado.json).
const { rota, comAutomacao } = require('../lib/nuvem');
const { alterarEstado } = require('../lib/github');
const { novoPedido } = require('../lib/escritorio');

module.exports = rota('POST', async (req, res, corpo) => {
  const { estado, resultado } = await alterarEstado((e) => novoPedido(e, corpo), 'Painel: novo pedido');
  res.status(200).json({ ...comAutomacao(estado), pedido: resultado.id });
});
