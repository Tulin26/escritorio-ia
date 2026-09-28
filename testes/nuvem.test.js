// Testes do painel online sem publicar nada: o GitHub e a rotina do Claude são simulados aqui dentro.
// Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

process.env.GITHUB_TOKEN = 'token-de-teste';
process.env.GITHUB_REPO = 'dono/escritorio-ia';
process.env.PAINEL_SENHA = 'senha-de-teste-123';
process.env.ROTINA_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_teste/fire';
process.env.ROTINA_TOKEN = 'token-da-rotina';

const escritorio = require('../lib/escritorio');
const auth = require('../lib/auth');

const ESTADO_INICIAL = fs.readFileSync(path.join(__dirname, '..', 'estado.json'), 'utf8');

// GitHub e rotina de mentira: guarda o estado.json em memória e registra cada chamada.
function simularServicos({ conflitosNaGravacao = 0 } = {}) {
  const repo = { 'estado.json': ESTADO_INICIAL, 'copy/m-003-matriz-resumo.md': '# Resumo' };
  let versao = 1;
  let conflitos = conflitosNaGravacao;
  const chamadas = [];
  global.fetch = async (url, opcoes = {}) => {
    chamadas.push({ url, opcoes });
    const resposta = (status, corpo) => ({ ok: status < 300, status, statusText: String(status), json: async () => corpo });
    if (url.startsWith('https://api.anthropic.com/')) {
      return resposta(200, { type: 'routine_fire', claude_code_session_url: 'https://claude.ai/code/session_teste' });
    }
    const caminho = decodeURIComponent(new URL(url).pathname.replace('/repos/dono/escritorio-ia/contents/', ''));
    if (!opcoes.method || opcoes.method === 'GET') {
      if (!(caminho in repo)) return resposta(404, {});
      return resposta(200, { content: Buffer.from(repo[caminho]).toString('base64'), sha: `sha${versao}` });
    }
    const corpo = JSON.parse(opcoes.body);
    if (conflitos > 0) {
      conflitos -= 1;
      versao += 1; // alguém gravou antes
      return resposta(409, {});
    }
    if (corpo.sha !== `sha${versao}`) return resposta(409, {});
    repo[caminho] = Buffer.from(corpo.content, 'base64').toString('utf8');
    versao += 1;
    return resposta(200, {});
  };
  return { repo, chamadas, estado: () => JSON.parse(repo['estado.json']) };
}

function requisicao({ metodo = 'GET', corpo, cookie, origem, query = {} } = {}) {
  return {
    method: metodo,
    body: corpo,
    query,
    headers: {
      host: 'escritorio.vercel.app',
      ...(metodo === 'POST' ? { 'content-type': 'application/json' } : {}),
      ...(cookie ? { cookie } : {}),
      ...(origem ? { origin: origem } : {}),
    },
  };
}

function resposta() {
  const r = { statusCode: 200, headers: {}, corpo: undefined };
  r.status = (s) => { r.statusCode = s; return r; };
  r.json = (c) => { r.corpo = c; return r; };
  r.send = (c) => { r.corpo = c; return r; };
  r.setHeader = (k, v) => { r.headers[k.toLowerCase()] = v; };
  return r;
}

async function chamar(rota, opcoes) {
  const res = resposta();
  await require(`../api/${rota}`)(requisicao(opcoes), res);
  return res;
}

const cookieValido = () => auth.cookieDeEntrada().split(';')[0];

test('regras: pedido novo e decisão validam o que chega', () => {
  const estado = JSON.parse(ESTADO_INICIAL);
  assert.throws(() => escritorio.novoPedido(estado, { projeto: 'x', texto: 'oi' }), /descreva/);
  assert.throws(() => escritorio.novoPedido(estado, { projeto: '', texto: 'quero um site novo' }), /projeto/);
  const pedido = escritorio.novoPedido(estado, { projeto: 'Canto do Cupim', texto: 'quero um site novo' });
  assert.equal(pedido.projeto, 'canto-do-cupim');
  assert.match(pedido.id, /^p-\d{3}$/);
  assert.throws(() => escritorio.decidir(estado, { id: 'm-999', acao: 'aprovar' }), /não encontrada/);
  assert.throws(() => escritorio.decidir(estado, { id: 'm-001', acao: 'apagar' }), /aprovar ou refazer/);
});

test('regras: só abre entregas .md dentro da pasta', () => {
  const estado = { missoes: [{ id: 'a', arquivo: '../segredo.md' }, { id: 'b', arquivo: 'C:/x.md' }, { id: 'c', arquivo: 'copy/ok.txt' }, { id: 'd', arquivo: 'copy/ok.md' }] };
  for (const id of ['a', 'b', 'c']) assert.throws(() => escritorio.caminhoDeEntrega(estado, id), /não permitido/);
  assert.equal(escritorio.caminhoDeEntrega(estado, 'd'), 'copy/ok.md');
});

test('login: senha certa abre a sessão; cookie alterado ou vencido não vale', async () => {
  simularServicos();
  const errada = await chamar('login', { metodo: 'POST', corpo: { senha: 'chute' } });
  assert.equal(errada.statusCode, 401);
  const certa = await chamar('login', { metodo: 'POST', corpo: { senha: 'senha-de-teste-123' } });
  assert.equal(certa.statusCode, 200);
  const cookie = certa.headers['set-cookie'];
  assert.match(cookie, /HttpOnly; Secure; SameSite=Strict/);
  assert.equal(auth.logado({ headers: { cookie: cookie.split(';')[0] } }), true);
  assert.equal(auth.logado({ headers: { cookie: `${cookie.split(';')[0]}x` } }), false);
  const vencido = `escritorio_sessao=${Date.now() - 1000}.qualquer`;
  assert.equal(auth.logado({ headers: { cookie: vencido } }), false);
});

test('sem login, nenhuma rota de dados responde', async () => {
  simularServicos();
  for (const [rota, metodo] of [['estado', 'GET'], ['arquivo', 'GET'], ['pedido', 'POST'], ['decisao', 'POST'], ['rodada', 'POST']]) {
    const r = await chamar(rota, { metodo, corpo: {} });
    assert.equal(r.statusCode, 401, rota);
  }
});

test('POST vindo de outro site é recusado', async () => {
  simularServicos();
  const r = await chamar('pedido', { metodo: 'POST', cookie: cookieValido(), origem: 'https://site-malicioso.com', corpo: { projeto: 'x', texto: 'teste teste' } });
  assert.equal(r.statusCode, 403);
});

test('estado e entrega são lidos do GitHub', async () => {
  simularServicos();
  const estado = await chamar('estado', { cookie: cookieValido() });
  assert.equal(estado.statusCode, 200);
  assert.equal(estado.corpo._automacao.modo, 'nuvem');
  assert.equal(estado.corpo._automacao.ativa, true);
  const arquivo = await chamar('arquivo', { cookie: cookieValido(), query: { id: 'm-003' } });
  assert.equal(arquivo.corpo, '# Resumo');
});

test('novo pedido vira commit; se a equipe gravou no meio, tenta de novo', async () => {
  const s = simularServicos({ conflitosNaGravacao: 1 });
  const r = await chamar('pedido', { metodo: 'POST', cookie: cookieValido(), origem: 'https://escritorio.vercel.app', corpo: { projeto: 'Padaria', texto: 'posts para outubro' } });
  assert.equal(r.statusCode, 200);
  const ultimo = s.estado().pedidos.at(-1);
  assert.equal(ultimo.projeto, 'padaria');
  assert.equal(ultimo.status, 'novo');
  assert.equal(s.chamadas.filter((c) => c.opcoes.method === 'PUT').length, 2);
});

test('decisão do dono é gravada no GitHub', async () => {
  const s = simularServicos();
  const estado = JSON.parse(s.repo['estado.json']);
  estado.missoes.find((m) => m.id === 'm-004').status = 'aguardando';
  s.repo['estado.json'] = JSON.stringify(estado);
  const r = await chamar('decisao', { metodo: 'POST', cookie: cookieValido(), corpo: { id: 'm-004', acao: 'refazer', comentario: 'mais curto' } });
  assert.equal(r.statusCode, 200);
  const m = s.estado().missoes.find((x) => x.id === 'm-004');
  assert.equal(m.status, 'refazer');
  assert.equal(m.comentario, 'mais curto');
});

test('chamar a equipe dispara a rotina uma vez e marca a rodada', async () => {
  const s = simularServicos();
  const estado = JSON.parse(s.repo['estado.json']);
  estado.pedidos.push({ id: 'p-099', projeto: 'x', projetoNome: 'X', texto: 'teste', status: 'novo', missao: '', data: '' });
  s.repo['estado.json'] = JSON.stringify(estado);

  const r = await chamar('rodada', { metodo: 'POST', cookie: cookieValido(), corpo: {} });
  assert.equal(r.statusCode, 200);
  const disparo = s.chamadas.find((c) => c.url === process.env.ROTINA_URL);
  assert.ok(disparo, 'a rotina não foi chamada');
  assert.equal(disparo.opcoes.headers.Authorization, 'Bearer token-da-rotina');
  assert.equal(disparo.opcoes.headers['anthropic-beta'], 'experimental-cc-routine-2026-04-01');
  assert.match(JSON.parse(disparo.opcoes.body).text, /item\(ns\) esperando/);
  assert.equal(s.estado().rodadaNuvem.rodando, true);
  assert.equal(s.estado().rodadaNuvem.sessao, 'https://claude.ai/code/session_teste');
  assert.equal(r.corpo._automacao.rodando, true);

  const deNovo = await chamar('rodada', { metodo: 'POST', cookie: cookieValido(), corpo: {} });
  assert.equal(deNovo.statusCode, 409);
  assert.equal(s.chamadas.filter((c) => c.url === process.env.ROTINA_URL).length, 1);
});

test('rodada que passou de 45 minutos aparece como erro e libera um novo chamado', () => {
  const { statusNuvem } = require('../lib/nuvem');
  const antiga = new Date(Date.now() - 50 * 60 * 1000).toISOString();
  const status = statusNuvem({ missoes: [], pedidos: [], rodadaNuvem: { rodando: true, iniciadaEm: antiga, motivo: 'x' } });
  assert.equal(status.rodando, false);
  assert.equal(status.ultima.ok, false);
});
