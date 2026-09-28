// Testes do painel online sem publicar nada: o GitHub e a rotina do Claude são simulados aqui dentro.
// (O Git do PC é testado em git.test.js e o servidor do PC inteiro em servidor.test.js.)
// Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');

process.env.GITHUB_TOKEN = 'token-de-teste';
process.env.GITHUB_REPO = 'dono/escritorio-ia';
process.env.PAINEL_SENHA = 'senha-de-teste-123';
process.env.ROTINA_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_teste/fire';
process.env.ROTINA_TOKEN = 'token-da-rotina';

const escritorio = require('../lib/escritorio');
const auth = require('../lib/auth');
const { PNG, CSV, anexo, estadoDeExemplo } = require('./apoio');

const ESTADO_INICIAL = estadoDeExemplo();

// GitHub e rotina de mentira. O "GitHub" é um Git pequeno em memória (arquivos, árvores, commits e o ramo main) que
// responde às duas APIs usadas pelo painel: a de arquivos (contents) e a de dados do Git (commit com vários arquivos).
// "conflitosNaGravacao" simula a equipe gravando no meio: a próxima gravação do painel é recusada e ele tem de ler de novo.
function simularServicos({ conflitosNaGravacao = 0 } = {}) {
  const blobs = new Map();
  const arvores = new Map();
  const commits = new Map();
  let seq = 0;
  const guardar = (mapa, valor, tipo) => { const sha = `${tipo}${++seq}`; mapa.set(sha, valor); return sha; };
  const blob = (conteudo) => guardar(blobs, Buffer.from(conteudo), 'blob');
  const commit = (arquivos, pais, mensagem) => guardar(commits, { tree: guardar(arvores, arquivos, 'tree'), pais, mensagem }, 'commit');
  const arquivosEm = (sha) => arvores.get(commits.get(sha).tree);
  let main = commit(new Map([['estado.json', blob(ESTADO_INICIAL)], ['copy/m-003-matriz-resumo.md', blob('# Resumo')]]), [], 'começo');
  let conflitos = conflitosNaGravacao;
  const chamadas = [];

  const ler = (caminho) => blobs.get(arquivosEm(main).get(caminho));
  const escrever = (caminho, conteudo, mensagem = 'equipe gravou') => {
    const arquivos = new Map(arquivosEm(main));
    arquivos.set(caminho, blob(conteudo));
    main = commit(arquivos, [main], mensagem);
  };
  const equipeGravouNoMeio = () => {
    const e = JSON.parse(ler('estado.json'));
    e.equipeGravou = (e.equipeGravou || 0) + 1;
    escrever('estado.json', JSON.stringify(e, null, 2));
  };
  const historico = () => {
    const lista = [];
    for (let sha = main; sha; sha = commits.get(sha).pais[0]) lista.push({ sha, ...commits.get(sha), arquivos: arquivosEm(sha) });
    return lista;
  };

  global.fetch = async (url, opcoes = {}) => {
    chamadas.push({ url, opcoes });
    const metodo = opcoes.method || 'GET';
    const corpo = opcoes.body ? JSON.parse(opcoes.body) : {};
    const resposta = (status, dados, bruto) => ({
      ok: status < 300, status, statusText: String(status),
      json: async () => dados,
      arrayBuffer: async () => bruto.buffer.slice(bruto.byteOffset, bruto.byteOffset + bruto.length),
    });
    if (url.startsWith('https://api.anthropic.com/')) {
      return resposta(200, { type: 'routine_fire', claude_code_session_url: 'https://claude.ai/code/session_teste' });
    }
    const endereco = new URL(url);
    const rota = decodeURIComponent(endereco.pathname.replace('/repos/dono/escritorio-ia/', ''));
    if (rota.startsWith('contents/')) {
      const caminho = rota.slice('contents/'.length);
      if (metodo === 'GET') {
        const ref = endereco.searchParams.get('ref');
        const versao = ref === 'main' ? main : ref;
        const arquivos = commits.has(versao) ? arquivosEm(versao) : new Map();
        if (!arquivos.has(caminho)) return resposta(404, {});
        const sha = arquivos.get(caminho);
        if (/raw/.test((opcoes.headers || {}).Accept)) return resposta(200, null, blobs.get(sha));
        return resposta(200, { content: blobs.get(sha).toString('base64'), sha });
      }
      if (metodo === 'PUT') {
        if (conflitos > 0) {
          conflitos -= 1;
          equipeGravouNoMeio();
          return resposta(409, {});
        }
        if (corpo.sha !== arquivosEm(main).get(caminho)) return resposta(409, {});
        escrever(caminho, Buffer.from(corpo.content, 'base64'), corpo.message);
        return resposta(200, {});
      }
    }
    if (rota === 'git/ref/heads/main') return resposta(200, { object: { sha: main } });
    if (rota.startsWith('git/commits/') && metodo === 'GET') {
      const sha = rota.slice('git/commits/'.length);
      return resposta(200, { sha, tree: { sha: commits.get(sha).tree } });
    }
    if (rota === 'git/blobs' && metodo === 'POST') return resposta(201, { sha: blob(Buffer.from(corpo.content, corpo.encoding)) });
    if (rota === 'git/trees' && metodo === 'POST') {
      const arquivos = new Map(arvores.get(corpo.base_tree));
      corpo.tree.forEach((item) => arquivos.set(item.path, item.sha));
      return resposta(201, { sha: guardar(arvores, arquivos, 'tree') });
    }
    if (rota === 'git/commits' && metodo === 'POST') {
      return resposta(201, { sha: guardar(commits, { tree: corpo.tree, pais: corpo.parents, mensagem: corpo.message }, 'commit') });
    }
    if (rota === 'git/refs/heads/main' && metodo === 'PATCH') {
      if (conflitos > 0) {
        conflitos -= 1;
        equipeGravouNoMeio();
        return resposta(422, {});
      }
      if (corpo.force || commits.get(corpo.sha).pais[0] !== main) return resposta(422, {}); // só avança, nunca passa por cima
      main = corpo.sha;
      return resposta(200, {});
    }
    return resposta(404, {});
  };
  return {
    chamadas, ler, escrever, historico,
    estado: () => JSON.parse(ler('estado.json')),
    alterarEstado: (mudar) => { const e = JSON.parse(ler('estado.json')); mudar(e); escrever('estado.json', JSON.stringify(e)); },
  };
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
  for (const [rota, metodo] of [['estado', 'GET'], ['arquivo', 'GET'], ['anexo', 'GET'], ['pedido', 'POST'], ['decisao', 'POST'], ['rodada', 'POST']]) {
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
  assert.equal(estado.corpo._git.modo, 'nuvem');
  assert.equal(estado.corpo._git.fixo, true);
  assert.equal(estado.corpo._git.remoto, 'github.com/dono/escritorio-ia');
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
  assert.equal(s.estado().equipeGravou, 1, 'o que a equipe gravou no meio não pode se perder');
  assert.equal(s.chamadas.filter((c) => c.opcoes.method === 'PUT').length, 2);
});

test('pedido com anexos vira um commit só, com os arquivos em anexos/<id>/', async () => {
  const s = simularServicos({ conflitosNaGravacao: 1 });
  const commitsAntes = s.historico().length;
  const r = await chamar('pedido', {
    metodo: 'POST', cookie: cookieValido(),
    corpo: { projeto: 'Padaria', texto: 'posts com o logo e as vendas', anexos: [anexo('Logo da Padaria.png', PNG), anexo('vendas.csv', CSV)] },
  });
  assert.equal(r.statusCode, 200);
  const pedido = s.estado().pedidos.find((p) => p.id === r.corpo.pedido);
  assert.deepEqual(pedido.anexos.map((a) => a.arquivo), [`anexos/${pedido.id}/logo-da-padaria.png`, `anexos/${pedido.id}/vendas.csv`]);
  assert.deepEqual(s.ler(pedido.anexos[0].arquivo), PNG);
  assert.deepEqual(s.ler(pedido.anexos[1].arquivo), CSV);
  assert.equal(s.estado().equipeGravou, 1, 'o que a equipe gravou no meio não pode se perder');
  const [ultimo] = s.historico();
  assert.equal(ultimo.mensagem, 'Painel: novo pedido com 2 anexo(s)');
  assert.ok(ultimo.arquivos.has('estado.json') && ultimo.arquivos.has(pedido.anexos[0].arquivo), 'estado e anexos no mesmo commit');
  assert.equal(s.historico().length, commitsAntes + 2, 'um commit da equipe no meio e um do painel');
  const blobs = s.chamadas.filter((c) => c.url.endsWith('/git/blobs'));
  assert.equal(blobs.length, 4, 'cada anexo sobe uma vez só; o estado.json sobe a cada tentativa');
});

test('anexo recusado não grava nada no GitHub', async () => {
  const s = simularServicos();
  for (const anexos of [[anexo('x.svg', Buffer.from('<svg/>'))], [anexo('falso.png', Buffer.from('<html>'))], Array(6).fill(anexo('a.png', PNG))]) {
    const r = await chamar('pedido', { metodo: 'POST', cookie: cookieValido(), corpo: { projeto: 'X', texto: 'pedido com anexo ruim', anexos } });
    assert.equal(r.statusCode, 400);
    assert.ok(r.corpo.erro);
  }
  assert.equal(s.chamadas.filter((c) => ['PUT', 'POST', 'PATCH'].includes(c.opcoes.method)).length, 0);
});

test('anexo é lido do GitHub com cabeçalhos seguros; caminho fora da lista é recusado', async () => {
  simularServicos();
  const criado = await chamar('pedido', { metodo: 'POST', cookie: cookieValido(), corpo: { projeto: 'X', texto: 'pedido com logo', anexos: [anexo('logo.png', PNG)] } });
  const caminho = `anexos/${criado.corpo.pedido}/logo.png`;
  const r = await chamar('anexo', { cookie: cookieValido(), query: { caminho } });
  assert.equal(r.statusCode, 200);
  assert.deepEqual(Buffer.from(r.corpo), PNG);
  assert.equal(r.headers['content-type'], 'image/png');
  assert.equal(r.headers['x-content-type-options'], 'nosniff');
  assert.match(r.headers['content-security-policy'], /sandbox/);
  assert.match(r.headers['cache-control'], /private/);
  for (const [ruim, status] of [['estado.json', 400], [`${caminho}/../../../estado.json`, 400], ['anexos/p-999/logo.png', 404]]) {
    const recusado = await chamar('anexo', { cookie: cookieValido(), query: { caminho: ruim } });
    assert.equal(recusado.statusCode, status, ruim);
  }
});

test('decisão do dono é gravada no GitHub', async () => {
  const s = simularServicos();
  s.alterarEstado((estado) => { estado.missoes.find((m) => m.id === 'm-004').status = 'aguardando'; });
  const r = await chamar('decisao', { metodo: 'POST', cookie: cookieValido(), corpo: { id: 'm-004', acao: 'refazer', comentario: 'mais curto' } });
  assert.equal(r.statusCode, 200);
  const m = s.estado().missoes.find((x) => x.id === 'm-004');
  assert.equal(m.status, 'refazer');
  assert.equal(m.comentario, 'mais curto');
});

test('chamar a equipe dispara a rotina uma vez e marca a rodada', async () => {
  const s = simularServicos();
  s.alterarEstado((estado) => { estado.pedidos.push({ id: 'p-099', projeto: 'x', projetoNome: 'X', texto: 'teste', status: 'novo', missao: '', data: '' }); });

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
