// Painel do Escritório de IA: Node puro, sem dependências.
// Uso: node server.js   →   http://localhost:4321
// Automação: pedidos e decisões feitos no painel acordam o Claude sozinho (claude -p, sem janela).
//   ESCRITORIO_AUTOMACAO=0 desliga · ESCRITORIO_MODELO / ESCRITORIO_ESFORCO trocam modelo e esforço · CLAUDE_BIN caminho do claude
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = __dirname;
const ESTADO = path.join(ROOT, 'estado.json');
const LOGS = path.join(ROOT, 'logs');
const PORT = Number(process.env.PORT) || 4321;
const HOST = '127.0.0.1';
const AUTOMACAO = process.env.ESCRITORIO_AUTOMACAO !== '0';
const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const MODELO = process.env.ESCRITORIO_MODELO || 'claude-opus-5-5';
const ESFORCO = process.env.ESCRITORIO_ESFORCO || 'high';
const LIMITE_RODADA_MS = 30 * 60 * 1000;

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
function agora() {
  const d = new Date();
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`;
}
function carimbo() {
  const d = new Date();
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}_${p2(d.getHours())}-${p2(d.getMinutes())}-${p2(d.getSeconds())}`;
}

function enviar(res, status, corpo, tipo = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': tipo, 'Cache-Control': 'no-store' });
  res.end(typeof corpo === 'string' ? corpo : JSON.stringify(corpo));
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
function origemValida(req) {
  const origem = req.headers.origin;
  if (!origem) return true;
  return [`http://localhost:${PORT}`, `http://${HOST}:${PORT}`, `http://[::1]:${PORT}`].includes(origem);
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

function statusAutomacao() {
  return { ativa: AUTOMACAO, modelo: MODELO, esforco: ESFORCO, rodando: auto.rodando, pendente: auto.pendente, inicio: auto.inicio, motivo: auto.motivo, ultima: auto.ultima };
}
const comAutomacao = (estado) => ({ ...estado, _automacao: statusAutomacao() });

// Uma missão em backlog está pronta quando o plano do Diretor do mesmo projeto foi aprovado
// e todas as missões citadas em "depende de" estão aprovadas.
function prontaParaRodar(m, missoes) {
  const planoAprovado = missoes.some((x) => x.area === 'diretor' && x.projeto === m.projeto && x.status === 'aprovado');
  if (!planoAprovado) return false;
  const trecho = /depende de:?([^|]*)/i.exec(m.resumo || '');
  const deps = trecho ? trecho[1].match(/m-\d+/g) || [] : [];
  return deps.every((id) => missoes.some((x) => x.id === id && x.status === 'aprovado'));
}

function temTrabalho(estado) {
  const missoes = (estado.missoes || []).filter((m) => !m.exemplo);
  return (estado.pedidos || []).some((p) => p.status === 'novo')
    || missoes.some((m) => m.status === 'refazer' || m.status === 'rodando')
    || missoes.some((m) => m.status === 'backlog' && prontaParaRodar(m, missoes));
}

const PROMPT_RODADA = `Você está rodando sozinho, sem ninguém no terminal, como a sessão principal do Escritório de IA (a pasta atual).
Ninguém vai responder perguntas: não pergunte nada; quando faltar informação, escreva as perguntas dentro da entrega.

1. Leia CLAUDE.md e estado.json.
2. Para cada pedido em estado.json > "pedidos" com status "novo":
   - Se não existir projetos/<projeto>.md, crie a partir de projetos/_modelo.md com o que o pedido diz e marque o resto como [PREENCHER]. Registre o projeto em estado.json > "projetos" como { "id", "nome", "briefing" }.
   - Chame o agente "diretor" passando o texto do pedido e o id do projeto. Se faltar informação, o plano deve listar as perguntas; o dono responde pelo botão Refazer do painel.
   - Marque o pedido com status "feito" e grave em "missao" o id da missão de plano criada.
3. Para cada missão com status "refazer": chame o agente dono da área passando o id da missão (ele lê o "comentario").
4. Para cada missão com status "rodando": sobrou de uma rodada interrompida; chame o agente dono para terminar.
5. Para cada missão em "backlog": rode só se a missão de plano do Diretor do mesmo projeto estiver "aprovado" e todas as missões citadas em "depende de" estiverem "aprovado". Missões independentes podem rodar em paralelo.
6. Ignore missões com "exemplo": true.

Regras: nunca publique, envie, agende, compre nem altere nada fora desta pasta; nunca marque "aprovado"; mantenha o estado.json válido.
Termine com um resumo curto, em português, do que foi feito.`;

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
  if (temTrabalho(estado)) iniciarRodada(motivo);
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
  let filho;
  try {
    filho = spawn(CLAUDE_BIN, args, { cwd: ROOT, windowsHide: true });
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
  filho.stdin.end(PROMPT_RODADA);
}

// ---------- Rotas ----------
async function decidir(req, res) {
  const pedido = await lerPedidoJson(req, res);
  if (!pedido) return;
  const { id, acao } = pedido;
  const comentario = String(pedido.comentario || '').trim().slice(0, 4000);
  if (!['aprovar', 'refazer'].includes(acao)) return enviar(res, 400, { erro: 'ação deve ser aprovar ou refazer' });
  if (acao === 'refazer' && !comentario) return enviar(res, 400, { erro: 'escreva um comentário para o agente refazer' });

  const estado = lerEstado();
  const missao = (estado.missoes || []).find((m) => m.id === id);
  if (!missao) return enviar(res, 404, { erro: `missão ${id} não encontrada` });
  if (missao.status !== 'aguardando') {
    return enviar(res, 409, { erro: `a missão ${id} está "${missao.status}", não "aguardando"` });
  }

  missao.status = acao === 'aprovar' ? 'aprovado' : 'refazer';
  missao.comentario = comentario;
  missao.data = agora();
  salvarEstado(estado);
  if (!missao.exemplo) agendarRodada(acao === 'aprovar' ? `aprovou ${id}` : `pediu para refazer ${id}`);
  enviar(res, 200, comAutomacao(estado));
}

const paraId = (texto) => String(texto || '')
  .normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);

async function novoPedido(req, res) {
  const corpo = await lerPedidoJson(req, res);
  if (!corpo) return;
  const texto = String(corpo.texto || '').trim().slice(0, 4000);
  const projetoNome = String(corpo.projeto || '').trim().slice(0, 80);
  const projeto = paraId(projetoNome);
  if (texto.length < 5) return enviar(res, 400, { erro: 'descreva a missão (pelo menos algumas palavras)' });
  if (!projeto) return enviar(res, 400, { erro: 'diga para qual projeto é a missão' });

  const estado = lerEstado();
  estado.pedidos = estado.pedidos || [];
  const maior = estado.pedidos.reduce((n, p) => Math.max(n, Number(String(p.id).replace(/\D/g, '')) || 0), 0);
  const novo = { id: `p-${String(maior + 1).padStart(3, '0')}`, projeto, projetoNome, texto, status: 'novo', missao: '', data: agora() };
  estado.pedidos.push(novo);
  salvarEstado(estado);
  agendarRodada(`novo pedido ${novo.id}`);
  enviar(res, 200, comAutomacao(estado));
}

async function rodarAgora(req, res) {
  if (!origemValida(req)) return enviar(res, 403, { erro: 'origem não permitida' });
  if (!AUTOMACAO) return enviar(res, 409, { erro: 'a automação está desligada (ESCRITORIO_AUTOMACAO=0)' });
  if (auto.rodando) return enviar(res, 409, { erro: 'o Claude já está trabalhando' });
  if (!temTrabalho(lerEstado())) return enviar(res, 200, { ...comAutomacao(lerEstado()), aviso: 'Não há nada pendente para o Claude fazer.' });
  iniciarRodada('você pediu para rodar agora');
  enviar(res, 200, comAutomacao(lerEstado()));
}

function entregarArquivo(res, id) {
  const missao = (lerEstado().missoes || []).find((m) => m.id === id);
  if (!missao || !missao.arquivo) return enviar(res, 404, 'Sem arquivo para esta missão.', 'text/plain; charset=utf-8');
  const alvo = path.resolve(ROOT, missao.arquivo);
  if (!alvo.startsWith(ROOT + path.sep) || path.extname(alvo).toLowerCase() !== '.md') {
    return enviar(res, 400, 'Caminho de arquivo não permitido.', 'text/plain; charset=utf-8');
  }
  if (!fs.existsSync(alvo)) return enviar(res, 404, `Arquivo não encontrado: ${missao.arquivo}`, 'text/plain; charset=utf-8');
  enviar(res, 200, fs.readFileSync(alvo, 'utf8'), 'text/plain; charset=utf-8');
}

// Arquivos do painel servidos pelo servidor (lista fechada: nada além disso sai da pasta).
const ESTATICOS = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/index.html': ['index.html', 'text/html; charset=utf-8'],
  '/style.css': ['style.css', 'text/css; charset=utf-8'],
  '/app.js': ['app.js', 'text/javascript; charset=utf-8'],
};

async function atender(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  try {
    if (req.method === 'GET' && ESTATICOS[url.pathname]) {
      const [arquivo, tipo] = ESTATICOS[url.pathname];
      return enviar(res, 200, fs.readFileSync(path.join(ROOT, arquivo), 'utf8'), tipo);
    }
    if (req.method === 'GET' && url.pathname === '/api/estado') return enviar(res, 200, comAutomacao(lerEstado()));
    if (req.method === 'GET' && url.pathname === '/api/arquivo') return entregarArquivo(res, url.searchParams.get('id'));
    if (req.method === 'POST' && url.pathname === '/api/decisao') return await decidir(req, res);
    if (req.method === 'POST' && url.pathname === '/api/pedido') return await novoPedido(req, res);
    if (req.method === 'POST' && url.pathname === '/api/rodada') return await rodarAgora(req, res);
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
