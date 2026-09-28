// Painel online: login com uma senha só (variável PAINEL_SENHA do Vercel).
// A sessão é um cookie assinado com a própria senha: trocar a senha derruba todas as sessões abertas.
const crypto = require('crypto');
const { ErroEscritorio } = require('./escritorio');

const COOKIE = 'escritorio_sessao';
const DURACAO_S = 30 * 24 * 60 * 60;

function senhaDoPainel() {
  const senha = process.env.PAINEL_SENHA;
  if (!senha || senha.length < 8) throw new ErroEscritorio(500, 'Falta configurar PAINEL_SENHA (8 caracteres ou mais) no Vercel.');
  return senha;
}

const resumo = (texto) => crypto.createHash('sha256').update(String(texto)).digest();
const assinar = (validade) => crypto.createHmac('sha256', senhaDoPainel()).update(`escritorio:${validade}`).digest('base64url');

function senhaConfere(senha) {
  return crypto.timingSafeEqual(resumo(senha), resumo(senhaDoPainel()));
}

function cookieDeEntrada() {
  const validade = Date.now() + DURACAO_S * 1000;
  return `${COOKIE}=${validade}.${assinar(validade)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${DURACAO_S}`;
}
const cookieDeSaida = () => `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;

function logado(req) {
  const cookies = Object.fromEntries(String(req.headers.cookie || '').split(';').map((c) => {
    const i = c.indexOf('=');
    return [c.slice(0, i).trim(), c.slice(i + 1).trim()];
  }));
  const [validade, assinatura] = String(cookies[COOKIE] || '').split('.');
  if (!validade || !assinatura || Number(validade) < Date.now()) return false;
  const esperada = Buffer.from(assinar(validade));
  const recebida = Buffer.from(assinatura);
  return esperada.length === recebida.length && crypto.timingSafeEqual(esperada, recebida);
}

module.exports = { senhaConfere, cookieDeEntrada, cookieDeSaida, logado };
