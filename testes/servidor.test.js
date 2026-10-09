// Painel do PC inteiro (server.js) rodando numa CÓPIA do escritório, numa pasta temporária, com um GitHub de mentira
// (repositório Git local) no lugar do GitHub de verdade e um Claude de mentira no lugar do Claude. Nada sai do PC.
// Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');
const {
  RAIZ, PNG, CSV, anexo, estadoDeExemplo, pastaTemporaria, apagar, temGit, criarGithubDeMentira,
} = require('./apoio');

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

// A cópia leva só o que o servidor usa; o estado.json é o de exemplo (agentes de verdade, missões do projeto Matriz).
function copiaDoEscritorio() {
  return {
    'server.js': fs.readFileSync(path.join(RAIZ, 'server.js')),
    'rodada.md': fs.readFileSync(path.join(RAIZ, 'rodada.md')),
    'estado.json': estadoDeExemplo(),
    '.gitignore': fs.readFileSync(path.join(RAIZ, '.gitignore')),
    '.gitattributes': fs.readFileSync(path.join(RAIZ, '.gitattributes')),
    ...Object.fromEntries(fs.readdirSync(path.join(RAIZ, 'lib')).map((f) => [`lib/${f}`, fs.readFileSync(path.join(RAIZ, 'lib', f))])),
  };
}

const portaLivre = () => new Promise((resolve) => {
  const s = net.createServer();
  s.listen(0, '127.0.0.1', () => {
    const { port } = s.address();
    s.close(() => resolve(port));
  });
});

async function subirServidor(t, pasta, env) {
  const porta = await portaLivre();
  const filho = spawn(process.execPath, ['server.js'], { cwd: pasta, env: { ...env, PORT: String(porta) }, windowsHide: true });
  let saida = '';
  filho.stdout.on('data', (d) => { saida += d; });
  filho.stderr.on('data', (d) => { saida += d; });
  t.after(() => filho.kill());
  for (let i = 0; i < 100 && !saida.includes('Painel do Escritório de IA em'); i++) await espera(100);
  assert.match(saida, /Painel do Escritório de IA em/, `o servidor não subiu:\n${saida}`);
  const url = `http://127.0.0.1:${porta}`;
  const pedir = async (caminho, { corpo, origem, metodo } = {}) => {
    const r = await fetch(url + caminho, {
      method: metodo || (corpo !== undefined ? 'POST' : 'GET'),
      headers: { ...(corpo !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(origem ? { Origin: origem } : {}) },
      body: corpo !== undefined ? (typeof corpo === 'string' ? corpo : JSON.stringify(corpo)) : undefined,
    });
    const tipo = r.headers.get('content-type') || '';
    const dados = tipo.includes('json') ? await r.json() : Buffer.from(await r.arrayBuffer());
    return { status: r.status, dados, headers: r.headers };
  };
  return { url, pedir, saida: () => saida };
}

// Espera o GitHub de mentira receber um commit cuja mensagem bate com o padrão.
async function esperarCommit(noGithub, padrao, limiteMs = 20000) {
  const fim = Date.now() + limiteMs;
  while (Date.now() < fim) {
    const log = noGithub('log', '--format=%s', 'main');
    if (padrao.test(log)) return log;
    await espera(250);
  }
  throw new Error(`o GitHub de mentira não recebeu ${padrao}; log:\n${noGithub('log', '--format=%s', 'main')}`);
}

const opcoes = { skip: temGit ? false : 'o Git não está instalado neste PC', timeout: 90000 };

test('painel do PC: pedido com anexos, Enviar agora, botão de ligar e envio depois da decisão', opcoes, async (t) => {
  const pasta = pastaTemporaria('servidor');
  t.after(() => apagar(pasta));
  const g = criarGithubDeMentira(pasta, copiaDoEscritorio());
  const noGithub = (...args) => g.git(g.remoto, ...args);
  const { url, pedir } = await subirServidor(t, g.escritorio, { ...g.env, ESCRITORIO_AUTOMACAO: '0' });

  // Começo: Git disponível, desligado, nada para enviar.
  let r = await pedir('/api/estado');
  assert.equal(r.status, 200);
  assert.equal(r.dados._git.modo, 'local');
  assert.equal(r.dados._git.disponivel, true, r.dados._git.motivo);
  assert.equal(r.dados._git.ligado, false);
  assert.equal(r.dados._git.pendentes, 0);

  // Pedido com dois anexos: arquivos no disco, pedido no estado, fila para o GitHub.
  r = await pedir('/api/pedido', { corpo: { projeto: 'Padaria Pão Quente', texto: 'posts com o logo', anexos: [anexo('Logo.png', PNG), anexo('vendas.csv', CSV)] } });
  assert.equal(r.status, 200, JSON.stringify(r.dados));
  const pedido = r.dados.pedidos.find((p) => p.id === r.dados.pedido);
  assert.deepEqual(pedido.anexos.map((a) => a.arquivo), [`anexos/${pedido.id}/logo.png`, `anexos/${pedido.id}/vendas.csv`]);
  assert.deepEqual(fs.readFileSync(path.join(g.escritorio, 'anexos', pedido.id, 'logo.png')), PNG);
  assert.deepEqual(fs.readFileSync(path.join(g.escritorio, 'anexos', pedido.id, 'vendas.csv')), CSV);
  assert.equal(r.dados._git.pendentes, 3);
  assert.equal(r.dados._git.fila, true);

  // O painel abre o anexo; nada fora da lista.
  r = await pedir(`/api/anexo?caminho=${encodeURIComponent(pedido.anexos[0].arquivo)}`);
  assert.equal(r.status, 200);
  assert.deepEqual(r.dados, PNG);
  assert.equal(r.headers.get('content-type'), 'image/png');
  assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
  assert.equal((await pedir('/api/anexo?caminho=estado.json')).status, 400);
  assert.equal((await pedir('/api/anexo?caminho=anexos%2Fp-001%2F..%2F..%2Fserver.js')).status, 400);

  // Outro site não cria pedido nem manda anexo; JSON gigante é recusado (anexo grande vai arquivo por arquivo).
  assert.equal((await pedir('/api/pedido', { corpo: { projeto: 'x', texto: 'teste teste' }, origem: 'https://site-malicioso.com' })).status, 403);
  assert.equal((await pedir('/api/anexo/enviar?lote=lote-malicioso&caminho=a.txt', { corpo: 'oi', origem: 'https://site-malicioso.com' })).status, 403);
  assert.equal((await pedir('/api/pedido', { corpo: JSON.stringify({ projeto: 'x', texto: 'x'.repeat(70 * 1024 * 1024) }) })).status, 413);

  // Pasta inteira, arquivo por arquivo: qualquer tipo, subpastas mantidas, nome repetido ganha -2.
  const lote = 'lote-de-teste-1';
  const DOCX = Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00]);
  const subir = (caminho, conteudo) => fetch(`${url}/api/anexo/enviar?lote=${lote}&caminho=${encodeURIComponent(caminho)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: conteudo,
  }).then((x) => x.json());
  assert.deepEqual(await subir('TCC/Capítulo 1/Texto.docx', DOCX), { caminho: 'tcc/capitulo-1/texto.docx', tamanho: DOCX.length });
  assert.equal((await subir('TCC/capitulo 1/texto.docx', DOCX)).caminho, 'tcc/capitulo-1/texto-2.docx');
  assert.equal((await subir('TCC/../../../figuras/logo.png', PNG)).caminho, 'tcc/figuras/logo.png');
  assert.equal((await pedir('/api/pedido', { corpo: { projeto: 'TCC', texto: 'revisar o tcc', lote: '../../server' } })).status, 400);
  assert.equal((await pedir('/api/pedido', { corpo: { projeto: 'TCC', texto: 'revisar o tcc', lote: 'lote-que-nao-existe' } })).status, 400);
  r = await pedir('/api/pedido', { corpo: { projeto: 'TCC', texto: 'revisar o tcc inteiro', lote } });
  assert.equal(r.status, 200, JSON.stringify(r.dados));
  const doTcc = r.dados.pedidos.find((p) => p.id === r.dados.pedido);
  assert.deepEqual(doTcc.anexos.map((a) => [a.arquivo, a.tipo]).sort(), [
    [`anexos/${doTcc.id}/tcc/capitulo-1/texto-2.docx`, 'application/octet-stream'],
    [`anexos/${doTcc.id}/tcc/capitulo-1/texto.docx`, 'application/octet-stream'],
    [`anexos/${doTcc.id}/tcc/figuras/logo.png`, 'image/png'],
  ]);
  assert.deepEqual(fs.readFileSync(path.join(g.escritorio, 'anexos', doTcc.id, 'tcc', 'capitulo-1', 'texto.docx')), DOCX);
  assert.equal(fs.existsSync(path.join(g.escritorio, '.envio', lote)), false, 'o lote saiu de .envio/');
  r = await pedir(`/api/anexo?caminho=${encodeURIComponent(`anexos/${doTcc.id}/tcc/capitulo-1/texto.docx`)}`);
  assert.equal(r.status, 200);
  assert.match(r.headers.get('content-disposition'), /^attachment; filename="texto.docx"$/);
  r = await pedir(`/api/anexo?caminho=${encodeURIComponent(`anexos/${doTcc.id}/tcc/figuras/logo.png`)}`);
  assert.equal(r.headers.get('content-type'), 'image/png');

  // Enviar agora (com o envio automático desligado).
  r = await pedir('/api/git/enviar', { corpo: {} });
  assert.equal(r.status, 200, JSON.stringify(r.dados));
  assert.match(r.dados.aviso, /Enviado para/);
  assert.equal(r.dados._git.pendentes, 0);
  assert.equal(noGithub('log', '-1', '--format=%s'), 'Escritório: você pediu para enviar agora');
  assert.equal(noGithub('show', `main:${pedido.anexos[1].arquivo}`), CSV.toString('utf8').trim(), 'o CSV chega com o CRLF original');

  // Ligar: a própria mudança do estado.json já sobe sozinha.
  r = await pedir('/api/git', { corpo: { ligado: true } });
  assert.equal(r.status, 200);
  assert.equal(r.dados.git.ligado, true);
  await esperarCommit(noGithub, /^Escritório: envio automático ligado$/m);

  // Decisão do dono com o Git ligado: vai para o GitHub alguns segundos depois.
  const estado = JSON.parse(fs.readFileSync(path.join(g.escritorio, 'estado.json'), 'utf8'));
  estado.missoes.find((m) => m.id === 'm-004').status = 'aguardando';
  fs.writeFileSync(path.join(g.escritorio, 'estado.json'), JSON.stringify(estado, null, 2) + '\n');
  r = await pedir('/api/decisao', { corpo: { id: 'm-004', acao: 'aprovar' } });
  assert.equal(r.status, 200);
  await esperarCommit(noGithub, /^Escritório: aprovou m-004$/m);
  const noRemoto = JSON.parse(noGithub('show', 'main:estado.json'));
  assert.equal(noRemoto.missoes.find((m) => m.id === 'm-004').status, 'aprovado');

  // Desligar: nada mais sai sozinho.
  r = await pedir('/api/git', { corpo: { ligado: false } });
  assert.equal(r.dados.git.ligado, false);
  const commits = noGithub('rev-list', '--count', 'main');
  await pedir('/api/pedido', { corpo: { projeto: 'Padaria', texto: 'mais um pedido' } });
  await espera(6000);
  assert.equal(noGithub('rev-list', '--count', 'main'), commits);
  assert.equal((await pedir('/api/estado')).dados._git.pendentes, 1);

  // O botão de ligar só aceita sim ou não.
  assert.equal((await pedir('/api/git', { corpo: { ligado: 'sim' } })).status, 400);
});

// O Claude de mentira faz o papel da equipe: transforma o pedido novo num plano do Diretor, com os anexos.
const CLAUDE_FALSO = `#!/usr/bin/env node
const fs = require('fs');
process.stdin.resume();
process.stdin.on('end', () => {
  const e = JSON.parse(fs.readFileSync('estado.json', 'utf8'));
  for (const p of e.pedidos.filter((x) => x.status === 'novo')) {
    const id = 'm-' + String(e.missoes.length + 1).padStart(3, '0');
    const arquivo = 'diretor/' + id + '-' + p.projeto + '-plano.md';
    fs.mkdirSync('diretor', { recursive: true });
    fs.writeFileSync(arquivo, '# Plano\\n\\nAnexos: ' + (p.anexos || []).map((a) => a.arquivo).join(', ') + '\\n');
    e.missoes.push({ id, projeto: p.projeto, area: 'diretor', agente: 'diretor', titulo: 'Plano', resumo: '| depende de: -', arquivo, status: 'aguardando', xp: 10, data: p.data, comentario: '', anexos: (p.anexos || []).map((a) => a.arquivo) });
    p.status = 'feito';
    p.missao = id;
  }
  fs.writeFileSync('estado.json', JSON.stringify(e, null, 2) + '\\n');
});
`;

test('painel do PC: com o Git ligado, o fim de cada rodada da equipe vai para o GitHub', {
  ...opcoes,
  skip: opcoes.skip || (process.platform === 'win32' ? 'no Windows o Claude de mentira precisaria de um .cmd; o resto é testado acima' : false),
}, async (t) => {
  const pasta = pastaTemporaria('rodada');
  t.after(() => apagar(pasta));
  const arquivos = copiaDoEscritorio();
  const estado = JSON.parse(arquivos['estado.json']);
  estado.git = { ligado: true };
  estado.missoes.forEach((m) => { if (m.status === 'backlog') m.status = 'aprovado'; }); // sem trabalho pendente ao ligar
  arquivos['estado.json'] = JSON.stringify(estado, null, 2) + '\n';
  const g = criarGithubDeMentira(pasta, arquivos);
  const noGithub = (...args) => g.git(g.remoto, ...args);
  const claude = path.join(pasta, 'claude-falso.js');
  fs.writeFileSync(claude, CLAUDE_FALSO, { mode: 0o755 });
  const { pedir, saida } = await subirServidor(t, g.escritorio, { ...g.env, CLAUDE_BIN: claude });

  const r = await pedir('/api/pedido', { corpo: { projeto: 'Padaria', texto: 'posts com o logo', anexos: [anexo('logo.png', PNG)] } });
  assert.equal(r.status, 200);
  // Os motivos se juntam num commit só: "Escritório: novo pedido p-002 com 1 anexo(s); rodada da equipe".
  const log = await esperarCommit(noGithub, /^Escritório: novo pedido p-\d+ com 1 anexo\(s\); rodada da equipe$/m).catch((e) => {
    throw new Error(`${e.message}\n--- servidor ---\n${saida()}`);
  });
  assert.ok(log);
  const noRemoto = JSON.parse(noGithub('show', 'main:estado.json'));
  const plano = noRemoto.missoes.at(-1);
  assert.equal(plano.status, 'aguardando');
  assert.deepEqual(plano.anexos, [`anexos/${r.dados.pedido}/logo.png`]);
  assert.match(noGithub('show', `main:${plano.arquivo}`), /anexos\/p-\d+\/logo\.png/);
});
