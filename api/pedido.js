// POST /api/pedido { projeto, texto, anexos? }: nova missão para o Diretor (vira um commit no estado.json).
// Com anexos ([{ nome, dados em base64 }]), os arquivos vão para anexos/<id do pedido>/ no mesmo commit.
const { rota, comAutomacao } = require('../lib/nuvem');
const { alterarEstado, alterarEstadoComArquivos } = require('../lib/github');
const { novoPedido, prepararAnexos } = require('../lib/escritorio');

module.exports = rota('POST', async (req, res, corpo) => {
  const anexos = prepararAnexos(corpo.anexos);
  const { estado, resultado } = anexos.length
    ? await alterarEstadoComArquivos((e) => {
      const pedido = novoPedido(e, corpo, anexos);
      return { resultado: pedido, arquivos: pedido.anexos.map((a, i) => ({ caminho: a.arquivo, conteudo: anexos[i].conteudo })) };
    }, `Painel: novo pedido com ${anexos.length} anexo(s)`)
    : await alterarEstado((e) => novoPedido(e, corpo), 'Painel: novo pedido');
  res.status(200).json({ ...comAutomacao(estado), pedido: resultado.id });
});
