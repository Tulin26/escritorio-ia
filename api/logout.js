// POST /api/logout: encerra a sessão deste navegador.
const { rota } = require('../lib/nuvem');
const { cookieDeSaida } = require('../lib/auth');

module.exports = rota('POST', async (req, res) => {
  res.setHeader('Set-Cookie', cookieDeSaida());
  res.status(200).json({ ok: true });
}, { publica: true });
