// Painel do Escritório de IA no PC: Node puro, sem dependências.
// Uso: node server.js   →   http://localhost:4321
// Automação: pedidos e decisões feitos no painel acordam o Claude sozinho (claude -p, sem janela), seguindo o rodada.md.
//   ESCRITORIO_AUTOMACAO=0 desliga · ESCRITORIO_MODELO / ESCRITORIO_ESFORCO trocam modelo e esforço · CLAUDE_BIN caminho do claude
// Sala Git & GitHub: com o envio automático ligado (estado.json > git.ligado), o servidor faz commit e push desta pasta
//   depois de cada rodada e de cada decisão. ESCRITORIO_GIT_REMOTO troca o remoto (padrão: origin).
// O painel (React) fica em painel/ e é servido já montado a partir de painel/dist.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const escritorio = require('./lib/escritorio');
const { criarGit } = require('./lib/git');

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
const LIMITE_CORPO = 64 * 1024;
// Pedido com anexos: os arquivos chegam em base64 (um terço maior), mais uma folga para o texto.
const LIMITE_CORPO_PEDIDO = Math.ceil(escritorio.LIMITES_ANEXOS.pc.bytes * 4 / 3) + 1024 * 1024;
const ESPERA_ENVIO_MS = 4000; // junta cliques seguidos num commit só
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

function lerCorpo(req, limite) {
  return new Promise((resolve, reject) => {
    const partes = [];
    let tamanho = 0;
    req.on('data', (parte) => {
      tamanho += parte.length;
      if (tamanho > limite) {
        // Recusa, mas deixa o resto chegar (e ser jogado fora) para o navegador receber a resposta 413.
        const e = new Error('corpo grande demais');
        e.grande = true;
        partes.length = 0;
        reject(e);
        return;
      }
      partes.push(parte);
    });
    // Junta os pedaços antes de virar texto: um acento cortado ao meio entre dois pedaços não estraga.
    req.on('end', () => resolve(Buffer.concat(partes).toString('utf8')));
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

async function lerPedidoJson(req, res, limite = LIMITE_CORPO) {
  if (!origemValida(req)) return enviar(res, 403, { erro: 'origem não permitida' }), null;
  if (!String(req.headers['content-type'] || '').includes('application/json')) {
    return enviar(res, 415, { erro: 'use application/json' }), null;
  }
  try {
    return JSON.parse(await lerCorpo(req, limite));
  } catch (e) {
    return enviar(res, e.grande ? 413 : 400, { erro: e.grande ? 'os anexos passam do limite; mande arquivos menores' : 'JSON inválido' }), null;
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

// ---------- Sala Git & GitHub ----------
const git = criarGit(ROOT, { remoto: process.env.ESCRITORIO_GIT_REMOTO || 'origin' });
const gitLigado = (estado) => Boolean(estado && estado.git && estado.git.ligado);

async function statusGit(estado) {
  const r = await git.resumo();
  // "fila": tem trabalho indo (ou esperando para ir) para o GitHub; o painel desenha a linha Revisão → Git.
  return { modo: 'local', ...r, ligado: gitLigado(estado), fila: r.disponivel && (r.enviando || r.pendentes > 0 || r.adiante > 0) };
}

// O que o painel recebe: o estado.json mais o status da equipe e do Git (campos com _ não são gravados).
const completar = async (estado) => ({ ...estado, _automacao: statusAutomacao(estado), _git: await statusGit(estado) });

let esperaEnvio = null;
const motivosEnvio = [];

// Com o envio automático ligado, junta os motivos e envia alguns segundos depois do último.
// Se a equipe estiver trabalhando, espera: o fim da rodada chama de novo.
function agendarEnvio(motivo) {
  let estado;
  try {
    estado = lerEstado();
  } catch {
    return;
  }
  if (!gitLigado(estado)) return;
  if (!motivosEnvio.includes(motivo)) motivosEnvio.push(motivo);
  clearTimeout(esperaEnvio);
  esperaEnvio = setTimeout(() => {
    if (auto.rodando || git.enviando) return;
    enviarAoGithub().catch((e) => console.log(`[git] envio automático falhou: ${e.message}`));
  }, ESPERA_ENVIO_MS);
}

async function enviarAoGithub(pedidoDoDono) {
  clearTimeout(esperaEnvio);
  const motivos = motivosEnvio.splice(0);
  if (pedidoDoDono) motivos.unshift(pedidoDoDono);
  const texto = motivos.length > 3 ? `${motivos.slice(0, 3).join('; ')} e mais ${motivos.length - 3}` : motivos.join('; ');
  // estado.json quebrado não sobe: o painel online e a nuvem dependem dele.
  const conferir = () => {
    try {
      lerEstado();
    } catch (e) {
      throw new Error(`o estado.json está com JSON inválido, então nada foi enviado (${e.message})`);
    }
  };
  try {
    const ultimo = await git.enviar(texto || 'envio', { conferir });
    console.log(`[git] ${ultimo.resumo}`);
    return ultimo;
  } finally {
    if (auto.pendente && !auto.rodando) setImmediate(() => agendarRodada('pedidos feitos durante o envio ao GitHub'));
  }
}

function promptRodada() {
  const instrucoes = fs.readFileSync(path.join(ROOT, 'rodada.md'), 'utf8');
  return `Você está rodando no PC do dono (painel local): siga o rodada.md abaixo e pule a seção "Na nuvem".\n\n${instrucoes}`;
}

function agendarRodada(motivo) {
  if (!AUTOMACAO) return;
  // Com o Git no meio de um envio (que pode trazer arquivos do GitHub), a rodada espera ele terminar.
  if (auto.rodando || git.enviando) {
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
    agendarEnvio('rodada da equipe');
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
  const verbo = missao.status === 'aprovado' ? `aprovou ${missao.id}` : `pediu para refazer ${missao.id}`;
  if (!missao.exemplo) agendarRodada(verbo);
  agendarEnvio(verbo);
  enviar(res, 200, await completar(estado));
}

async function novoPedido(req, res) {
  const corpo = await lerPedidoJson(req, res, LIMITE_CORPO_PEDIDO);
  if (!corpo) return;
  const estado = lerEstado();
  let pedido;
  let anexos;
  try {
    anexos = escritorio.prepararAnexos(corpo.anexos, escritorio.LIMITES_ANEXOS.pc);
    pedido = escritorio.novoPedido(estado, corpo, anexos);
  } catch (e) {
    return responderErro(res, e);
  }
  // Primeiro os anexos, depois o estado: a equipe nunca vê um pedido cujos arquivos ainda não existem.
  pedido.anexos.forEach((a, i) => {
    const alvo = path.join(ROOT, a.arquivo);
    fs.mkdirSync(path.dirname(alvo), { recursive: true });
    fs.writeFileSync(alvo, anexos[i].conteudo);
  });
  salvarEstado(estado);
  git.invalidar();
  const motivo = `novo pedido ${pedido.id}${pedido.anexos.length ? ` com ${pedido.anexos.length} anexo(s)` : ''}`;
  agendarRodada(motivo);
  agendarEnvio(motivo);
  enviar(res, 200, { ...(await completar(estado)), pedido: pedido.id });
}

async function rodarAgora(req, res) {
  if (!origemValida(req)) return enviar(res, 403, { erro: 'origem não permitida' });
  if (!AUTOMACAO) return enviar(res, 409, { erro: 'a automação está desligada (ESCRITORIO_AUTOMACAO=0)' });
  if (auto.rodando) return enviar(res, 409, { erro: 'o Claude já está trabalhando' });
  if (git.enviando) return enviar(res, 409, { erro: 'o Git está enviando para o GitHub; tente de novo em alguns segundos' });
  if (!escritorio.temTrabalho(lerEstado())) return enviar(res, 200, { ...(await completar(lerEstado())), aviso: 'Não há nada pendente para a equipe fazer.' });
  iniciarRodada('você pediu para rodar agora');
  enviar(res, 200, await completar(lerEstado()));
}

// POST /api/git { ligado }: liga ou desliga o envio automático para o GitHub.
async function ligarGit(req, res) {
  const corpo = await lerPedidoJson(req, res);
  if (!corpo) return;
  if (typeof corpo.ligado !== 'boolean') return enviar(res, 400, { erro: 'diga ligado: true ou false' });
  if (corpo.ligado) {
    const r = await git.resumo();
    if (!r.disponivel) return enviar(res, 409, { erro: `não dá para ligar o Git: ${r.motivo}` });
  }
  const estado = lerEstado();
  estado.git = { ...(estado.git || {}), ligado: corpo.ligado };
  salvarEstado(estado);
  git.invalidar();
  if (corpo.ligado) agendarEnvio('envio automático ligado');
  else clearTimeout(esperaEnvio);
  enviar(res, 200, await completar(estado));
}

// POST /api/git/enviar: commit e push agora, com o envio automático ligado ou não.
async function enviarGitAgora(req, res) {
  if (!(await lerPedidoJson(req, res))) return;
  if (auto.rodando) return enviar(res, 409, { erro: 'A equipe está trabalhando. Espere a rodada terminar para enviar.' });
  let ultimo;
  try {
    ultimo = await enviarAoGithub('você pediu para enviar agora');
  } catch (e) {
    return enviar(res, e.ocupado ? 409 : 502, { erro: `Não deu para enviar: ${e.message}` });
  }
  enviar(res, 200, { ...(await completar(lerEstado())), aviso: ultimo.resumo });
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

// Anexo de um pedido (imagem, PDF ou texto), só se algum pedido ou missão cita o caminho.
function entregarAnexo(res, caminho) {
  let anexo;
  try {
    anexo = escritorio.anexoCitado(lerEstado(), caminho);
  } catch (e) {
    return enviar(res, e.status || 500, e.message, 'text/plain; charset=utf-8');
  }
  const alvo = path.resolve(ROOT, anexo.caminho);
  if (!alvo.startsWith(path.join(ROOT, 'anexos') + path.sep)) return enviar(res, 400, 'Caminho de anexo não permitido.', 'text/plain; charset=utf-8');
  if (!fs.existsSync(alvo)) return enviar(res, 404, `Anexo não encontrado: ${anexo.caminho}`, 'text/plain; charset=utf-8');
  res.writeHead(200, escritorio.cabecalhosDeAnexo(anexo));
  res.end(fs.readFileSync(alvo));
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
    if (req.method === 'GET' && url.pathname === '/api/estado') return enviar(res, 200, await completar(lerEstado()));
    if (req.method === 'GET' && url.pathname === '/api/arquivo') return entregarArquivo(res, url.searchParams.get('id'));
    if (req.method === 'GET' && url.pathname === '/api/anexo') return entregarAnexo(res, url.searchParams.get('caminho'));
    if (req.method === 'POST' && url.pathname === '/api/decisao') return await decidir(req, res);
    if (req.method === 'POST' && url.pathname === '/api/pedido') return await novoPedido(req, res);
    if (req.method === 'POST' && url.pathname === '/api/rodada') return await rodarAgora(req, res);
    if (req.method === 'POST' && url.pathname === '/api/git') return await ligarGit(req, res);
    if (req.method === 'POST' && url.pathname === '/api/git/enviar') return await enviarGitAgora(req, res);
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
