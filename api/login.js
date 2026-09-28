// POST /api/login { senha }: confere a senha do painel e abre a sessão (cookie de 30 dias).
const { rota } = require('../lib/nuvem');
const { senhaConfere, cookieDeEntrada } = require('../lib/auth');
const { ErroEscritorio } = require('../lib/escritorio');

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = rota('POST', async (req, res, corpo) => {
  if (!senhaConfere(String(corpo.senha || ''))) {
    await espera(800); // atrasa quem tenta adivinhar a senha
    throw new ErroEscritorio(401, 'Senha errada.');
  }
  res.setHeader('Set-Cookie', cookieDeEntrada());
  res.status(200).json({ ok: true });
}, { publica: true });
