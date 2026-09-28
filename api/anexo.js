// GET /api/anexo?caminho=anexos/p-003/logo.png: um arquivo que você mandou junto com um pedido.
const { rota } = require('../lib/nuvem');
const { lerEstado, lerArquivoBruto } = require('../lib/github');
const { anexoCitado, cabecalhosDeAnexo } = require('../lib/escritorio');

module.exports = rota('GET', async (req, res) => {
  const anexo = anexoCitado(await lerEstado(), String(req.query.caminho || ''));
  const conteudo = await lerArquivoBruto(anexo.caminho);
  Object.entries(cabecalhosDeAnexo(anexo)).forEach(([nome, valor]) => res.setHeader(nome, valor));
  res.status(200).send(conteudo);
});
