// Painel do Escritório de IA no PC: Node puro, sem dependências.
// Uso: node server.js   →   http://localhost:4321
// Automação: pedidos e decisões feitos no painel acordam o Claude sozinho (claude -p, sem janela), seguindo o rodada.md.
//   ESCRITORIO_AUTOMACAO=0 desliga · ESCRITORIO_MODELO / ESCRITORIO_ESFORCO trocam modelo e esforço · CLAUDE_BIN caminho do claude
// O painel (React) fica em painel/ e é servido já montado a partir de painel/dist.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const escritorio = require('./lib/escritorio');

const ROOT = __dirname;
const ESTADO = path.join(ROOT, 'estado.json');
const LOGS = path.join(ROOT, 'logs');
const PAINEL = path.join(ROOT, 'painel', 'dist');
const PORT = Number(process.env.PORT) || 4321;
const HOST = '127.0.0.1';
const AUTOMACAO = process.env.ESCRITORIO_AUTOMACAO !== '0';
const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const MODELO = process.env.ESCRITORIO_MODELO || 'claude-opus-5-5';
const ESFORCO = process.env.ESCRITORIO_ESFORCO || 'high';
const LIMITE_RODADA_MS = 30 * 60 * 1000;
const { agora } = escritorio;

function lerEstado() {
  const texto = fs.readFileSync(ESTADO, 'utf8').replace(/^﻿/, '');
  return JSON.parse(texto);
}

function salvarEstado(estado) {
  const json = JSON.stringify(estado, null, 2) + '\n';
  const tmp = ESTADO + '.tmp';
  fs.writeFileSync(tmp, json, 'utf8');
  try {
    fs.renameSync(tmp, ESTADO);
  } catch {
    // No Windows o rename pode falhar se outro programa estiver com o arquivo aberto.
    fs.writeFileSync(ESTADO, json, 'utf8');
    fs.rmSync(tmp, { force: true });
  }
}

const p2 = (n) => String(n).padStart(2, '0');
function carimbo() {
  const d = new Date();
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}_${p2(d.getHours())}-${p2(d.getMinutes())}-${p2(d.getSeconds())}`;
}

function enviar(res, status, corpo, tipo = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': tipo, 'Cache-Control': 'no-store' });
  res.end(typeof corpo === 'string' || Buffer.isBuffer(corpo) ? corpo : JSON.stringify(corpo));
}

function lerCorpo(req) {
  return new Promise((resolve, reject) => {
    let dados = '';
    req.on('data', (parte) => {
      dados += parte;
      if (dados.length > 64 * 1024) {
        reject(new Error('corpo grande demais'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(dados));
    req.on('error', reject);
  });
}

// Só aceita POST vindo do próprio painel (evita que outro site no navegador altere o estado).
// A porta 5173 é a do "npm run dev" do painel React, que repassa as chamadas para cá.
function origemValida(req) {
  const origem = req.headers.origin;
  if (!origem) return true;
  const portas = [PORT, 5173];
  return portas.some((p) => [`http://localhost:${p}`, `http://${HOST}:${p}`, `http://[::1]:${p}`].includes(origem));
}

async function lerPedidoJson(req, res) {
  if (!origemValida(req)) return enviar(res, 403, { erro: 'origem não permitida' }), null;
  if (!String(req.headers['content-type'] || '').includes('application/json')) {
    return enviar(res, 415, { erro: 'use application/json' }), null;
  }
  try {
    return JSON.parse(await lerCorpo(req));
  } catch {
    return enviar(res, 400, { erro: 'JSON inválido' }), null;
  }
}

// ---------- Automação: acorda o Claude sem janela ----------
const auto = { rodando: false, pendente: false, inicio: null, motivo: '', ultima: null };

function statusAutomacao(estado) {
  return {
    modo: 'local', ativa: AUTOMACAO, modelo: MODELO, esforco: ESFORCO,
    rodando: auto.rodando, pendente: auto.pendente, inicio: auto.inicio, motivo: auto.motivo, ultima: auto.ultima,
    pendentes: escritorio.trabalhoPendente(estado),
  };
}
const comAutomacao = (estado) => ({ ...estado, _automacao: statusAutomacao(estado) });

function promptRodada() {
  const instrucoes = fs.readFileSync(path.join(ROOT, 'rodada.md'), 'utf8');
  return `Você está rodando no PC do dono (painel local): siga o rodada.md abaixo e pule a seção "Na nuvem".\n\n${instrucoes}`;
}

function agendarRodada(motivo) {
  if (!AUTOMACAO) return;
  if (auto.rodando) {
    auto.pendente = true;
    return;
  }
  let estado;
  try {
    estado = lerEstado();
  } catch {
    return;
  }
  if (escritorio.temTrabalho(estado)) iniciarRodada(motivo);
}

function iniciarRodada(motivo) {
  auto.rodando = true;
  auto.pendente = false;
  auto.inicio = agora();
  auto.motivo = motivo;
  fs.mkdirSync(LOGS, { recursive: true });
  const nomeLog = `logs/rodada-${carimbo()}.txt`;
  const log = fs.createWriteStream(path.join(ROOT, nomeLog));
  log.write(`Rodada iniciada em ${auto.inicio} (motivo: ${motivo}, modelo: ${MODELO}, esforço: ${ESFORCO})\n\n`);

  let encerrada = false;
  const terminar = (ok, erro) => {
    if (encerrada) return;
    encerrada = true;
    if (erro) log.write(`\n[erro] ${erro}\n`);
    log.end();
    auto.rodando = false;
    auto.ultima = { inicio: auto.inicio, fim: agora(), ok, erro: erro || '', log: nomeLog, motivo };
    console.log(`[automação] rodada ${ok ? 'concluída' : 'com erro'} (${nomeLog})`);
    if (auto.pendente) setImmediate(() => agendarRodada('decisões durante a rodada'));
  };

  // Rodada sem terminal: só lê, grava dentro da pasta (acceptEdits), pesquisa na web e chama os agentes.
  const args = [
    '-p',
    '--model', MODELO,
    '--effort', ESFORCO,
    '--permission-mode', 'acceptEdits',
    '--allowedTools', 'Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Agent,Task',
    '--disallowedTools', 'Bash,PowerShell',
    '--output-format', 'text',
  ];
  // No Windows o Claude instalado pelo npm é um claude.cmd, que só abre pelo cmd (shell). A linha de comando é
  // montada aqui, com aspas no que tem espaço ou vírgula; nenhum argumento vem do painel.
  const aspas = (a) => (/[\s,;&|<>^]/.test(a) ? `"${a}"` : a);
  let filho;
  try {
    filho = process.platform === 'win32'
      ? spawn([CLAUDE_BIN, ...args].map(aspas).join(' '), { cwd: ROOT, windowsHide: true, shell: true })
      : spawn(CLAUDE_BIN, args, { cwd: ROOT, windowsHide: true });
  } catch (e) {
    return terminar(false, `não consegui iniciar o Claude: ${e.message}`);
  }
  console.log(`[automação] rodada iniciada (${motivo})`);
  const limite = setTimeout(() => {
    log.write('\n[erro] passou de 30 minutos; rodada interrompida.\n');
    filho.kill();
  }, LIMITE_RODADA_MS);
  filho.stdout.on('data', (d) => log.write(d));
  filho.stderr.on('data', (d) => log.write(d));
  filho.on('error', (e) => {
    clearTimeout(limite);
    terminar(false, `não consegui iniciar o Claude (${e.message}). Confira se o comando "claude" funciona no terminal.`);
  });
  filho.on('close', (codigo) => {
    clearTimeout(limite);
    terminar(codigo === 0, codigo === 0 ? '' : `o Claude terminou com código ${codigo}; veja ${nomeLog}`);
  });
  filho.stdin.end(promptRodada());
}

// ---------- Rotas ----------
function responderErro(res, e) {
  if (e instanceof escritorio.ErroEscritorio) return enviar(res, e.status, { erro: e.message });
  throw e;
}

async function decidir(req, res) {
  const pedido = await lerPedidoJson(req, res);
  if (!pedido) return;
  const estado = lerEstado();
  let missao;
  try {
    missao = escritorio.decidir(estado, pedido);
  } catch (e) {
    return responderErro(res, e);
  }
  salvarEstado(estado);
  if (!missao.exemplo) agendarRodada(missao.status === 'aprovado' ? `aprovou ${missao.id}` : `pediu para refazer ${missao.id}`);
  enviar(res, 200, comAutomacao(estado));
}

async function novoPedido(req, res) {
  const corpo = await lerPedidoJson(req, res);
  if (!corpo) return;
  const estado = lerEstado();
  let pedido;
  try {
    pedido = escritorio.novoPedido(estado, corpo);
  } catch (e) {
    return responderErro(res, e);
  }
  salvarEstado(estado);
  agendarRodada(`novo pedido ${pedido.id}`);
  enviar(res, 200, comAutomacao(estado));
}

async function rodarAgora(req, res) {
  if (!origemValida(req)) return enviar(res, 403, { erro: 'origem não permitida' });
  if (!AUTOMACAO) return enviar(res, 409, { erro: 'a automação está desligada (ESCRITORIO_AUTOMACAO=0)' });
  if (auto.rodando) return enviar(res, 409, { erro: 'o Claude já está trabalhando' });
  if (!escritorio.temTrabalho(lerEstado())) return enviar(res, 200, { ...comAutomacao(lerEstado()), aviso: 'Não há nada pendente para a equipe fazer.' });
  iniciarRodada('você pediu para rodar agora');
  enviar(res, 200, comAutomacao(lerEstado()));
}

function entregarArquivo(res, id) {
  let caminho;
  try {
    caminho = escritorio.caminhoDeEntrega(lerEstado(), id);
  } catch (e) {
    return enviar(res, e.status || 500, e.message, 'text/plain; charset=utf-8');
  }
  const alvo = path.resolve(ROOT, caminho);
  if (!alvo.startsWith(ROOT + path.sep)) return enviar(res, 400, 'Caminho de arquivo não permitido.', 'text/plain; charset=utf-8');
  if (!fs.existsSync(alvo)) return enviar(res, 404, `Arquivo não encontrado: ${caminho}`, 'text/plain; charset=utf-8');
  enviar(res, 200, fs.readFileSync(alvo, 'utf8'), 'text/plain; charset=utf-8');
}

// Arquivos do painel montado (painel/dist): só nomes simples na raiz ou em assets/, nada fora da pasta.
const TIPOS = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.json': 'application/json',
};
function entregarPainel(res, pathname) {
  const nome = pathname === '/' ? 'index.html' : pathname.slice(1);
  if (!/^(assets\/)?[\w.-]+$/.test(nome) || !TIPOS[path.extname(nome)]) return false;
  const alvo = path.join(PAINEL, nome);
  if (!fs.existsSync(alvo)) {
    if (nome !== 'index.html') return false;
    enviar(res, 503, 'O painel ainda não foi montado. Na pasta do escritório rode: npm run painel', 'text/plain; charset=utf-8');
    return true;
  }
  const cache = nome.startsWith('assets/') ? 'public, max-age=31536000, immutable' : 'no-store';
  res.writeHead(200, { 'Content-Type': TIPOS[path.extname(nome)], 'Cache-Control': cache });
  res.end(fs.readFileSync(alvo));
  return true;
}

async function atender(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  try {
    if (req.method === 'GET' && url.pathname === '/api/sessao') return enviar(res, 200, { modo: 'local', logado: true });
    if (req.method === 'GET' && url.pathname === '/api/estado') return enviar(res, 200, comAutomacao(lerEstado()));
    if (req.method === 'GET' && url.pathname === '/api/arquivo') return entregarArquivo(res, url.searchParams.get('id'));
    if (req.method === 'POST' && url.pathname === '/api/decisao') return await decidir(req, res);
    if (req.method === 'POST' && url.pathname === '/api/pedido') return await novoPedido(req, res);
    if (req.method === 'POST' && url.pathname === '/api/rodada') return await rodarAgora(req, res);
    if (req.method === 'GET' && entregarPainel(res, url.pathname)) return;
    enviar(res, 404, { erro: 'não encontrado' });
  } catch (erro) {
    const msg = erro instanceof SyntaxError ? `estado.json com JSON inválido: ${erro.message}` : erro.message;
    enviar(res, 500, { erro: msg });
  }
}

// No Windows, "localhost" pode apontar para o IPv6 (::1); por isso escuta nos dois endereços locais.
// Os dois são só da própria máquina: ninguém da rede acessa o painel.
const servidor6 = http.createServer(atender);
servidor6.on('error', (e) => console.log(`[aviso] IPv6 (::1) indisponível: ${e.code}. Use http://127.0.0.1:${PORT}`));
servidor6.listen(PORT, '::1');

const servidor = http.createServer(atender);
servidor.on('error', (e) => {
  console.log(e.code === 'EADDRINUSE'
    ? `[erro] A porta ${PORT} já está em uso. Feche o outro "node server.js" ou use outra porta: $env:PORT=4322; node server.js`
    : `[erro] ${e.message}`);
  process.exit(1);
});
servidor.listen(PORT, HOST, () => {
  console.log(`Painel do Escritório de IA em http://localhost:${PORT}  (Ctrl+C para parar)`);
  console.log(AUTOMACAO
    ? `Automação ligada: o Claude (${MODELO}, esforço ${ESFORCO}) é chamado sozinho quando há trabalho.`
    : 'Automação desligada.');
  agendarRodada('trabalho pendente ao ligar o servidor');
});
