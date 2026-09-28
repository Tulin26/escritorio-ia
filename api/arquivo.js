// GET /api/arquivo?id=m-001: conteúdo do .md entregue por uma missão.
const { rota } = require('../lib/nuvem');
const { lerEstado, lerArquivo } = require('../lib/github');
const { caminhoDeEntrega } = require('../lib/escritorio');

module.exports = rota('GET', async (req, res) => {
  const caminho = caminhoDeEntrega(await lerEstado(), String(req.query.id || ''));
  const { texto } = await lerArquivo(caminho);
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.status(200).send(texto);
});
