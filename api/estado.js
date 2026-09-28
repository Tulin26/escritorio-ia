// GET /api/estado: estado.json atual (lido do GitHub) com o status da equipe na nuvem.
const { rota, comAutomacao } = require('../lib/nuvem');
const { lerEstado } = require('../lib/github');

module.exports = rota('GET', async (req, res) => {
  res.status(200).json(comAutomacao(await lerEstado()));
});
