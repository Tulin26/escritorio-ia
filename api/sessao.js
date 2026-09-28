// GET /api/sessao: o painel pergunta se precisa mostrar a tela de senha.
const { rota } = require('../lib/nuvem');
const { logado } = require('../lib/auth');

module.exports = rota('GET', async (req, res) => {
  res.status(200).json({ modo: 'nuvem', logado: logado(req) });
}, { publica: true });
