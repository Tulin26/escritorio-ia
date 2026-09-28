// POST /api/rodada: chama a equipe (dispara a rotina do Claude na nuvem) quando há trabalho pendente.
// Online as decisões não chamam a equipe sozinhas: você revisa tudo e chama uma vez, poupando o limite diário de rotinas.
const { rota, comAutomacao, statusNuvem } = require('../lib/nuvem');
const { lerEstado, alterarEstado } = require('../lib/github');
const { chamarRotina } = require('../lib/rotina');
const { agora, trabalhoPendente, ErroEscritorio } = require('../lib/escritorio');

module.exports = rota('POST', async (req, res) => {
  const atual = await lerEstado();
  if (statusNuvem(atual).rodando) throw new ErroEscritorio(409, 'A equipe já está trabalhando. Espere a rodada terminar.');
  const pendentes = trabalhoPendente(atual);
  if (!pendentes) return res.status(200).json({ ...comAutomacao(atual), aviso: 'Não há nada pendente para a equipe fazer.' });

  const motivo = `Rodada pedida pelo painel online: ${pendentes} item(ns) esperando a equipe.`;
  const sessao = await chamarRotina(motivo);
  const { estado } = await alterarEstado((e) => {
    e.rodadaNuvem = { rodando: true, inicio: agora(), iniciadaEm: new Date().toISOString(), motivo, sessao };
  }, 'Painel: equipe chamada');
  res.status(200).json(comAutomacao(estado));
});
