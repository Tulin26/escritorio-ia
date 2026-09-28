// Painel online: o estado.json e as entregas moram no repositório do GitHub.
// Configuração (variáveis do Vercel): GITHUB_TOKEN, GITHUB_REPO (ex.: Tulin26/escritorio-ia), GITHUB_BRANCH (padrão: main).
const { ErroEscritorio } = require('./escritorio');

function config() {
  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPO;
  if (!token || !repo) throw new ErroEscritorio(500, 'Falta configurar GITHUB_TOKEN e GITHUB_REPO no Vercel.');
  return { token, repo, branch: process.env.GITHUB_BRANCH || 'main' };
}

const codificar = (caminho) => caminho.split('/').map(encodeURIComponent).join('/');

async function github(caminho, opcoes = {}) {
  const { token } = config();
  return fetch(`https://api.github.com${caminho}`, {
    ...opcoes,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'escritorio-ia',
      ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}),
      ...(opcoes.headers || {}),
    },
  });
}

async function githubJson(caminho, acao, opcoes) {
  const r = await github(caminho, opcoes);
  conferirResposta(r, acao);
  return r.json();
}

function conferirResposta(r, acao) {
  if (r.status === 401 || r.status === 403) throw new ErroEscritorio(502, 'O GitHub recusou o GITHUB_TOKEN: confira se ele vale para este repositório.');
  if (!r.ok) throw new ErroEscritorio(502, `O GitHub respondeu ${r.status} ao ${acao}.`);
}

// "ref" escolhe a versão (um commit); sem ela, lê o ramo configurado.
async function lerArquivo(caminho, ref) {
  const { repo, branch } = config();
  const r = await github(`/repos/${repo}/contents/${codificar(caminho)}?ref=${encodeURIComponent(ref || branch)}`);
  if (r.status === 404) throw new ErroEscritorio(404, `Arquivo não encontrado: ${caminho}`);
  conferirResposta(r, `ler ${caminho}`);
  const dados = await r.json();
  return { texto: Buffer.from(dados.content || '', 'base64').toString('utf8'), sha: dados.sha };
}

// Arquivo binário (anexo), byte a byte. O formato "raw" funciona também para arquivos acima de 1 MB.
async function lerArquivoBruto(caminho) {
  const { repo, branch } = config();
  const r = await github(`/repos/${repo}/contents/${codificar(caminho)}?ref=${encodeURIComponent(branch)}`, {
    headers: { Accept: 'application/vnd.github.raw+json' },
  });
  if (r.status === 404) throw new ErroEscritorio(404, `Anexo não encontrado: ${caminho}`);
  conferirResposta(r, `ler ${caminho}`);
  return Buffer.from(await r.arrayBuffer());
}

// Devolve false quando outra gravação chegou antes (sha antigo): quem chamou lê de novo e tenta outra vez.
async function gravarArquivo(caminho, texto, sha, mensagem) {
  const { repo, branch } = config();
  const r = await github(`/repos/${repo}/contents/${codificar(caminho)}`, {
    method: 'PUT',
    body: JSON.stringify({ message: mensagem, content: Buffer.from(texto, 'utf8').toString('base64'), sha, branch }),
  });
  if (r.status === 409 || r.status === 422) return false;
  if (!r.ok) throw new ErroEscritorio(502, `O GitHub respondeu ${r.status} ao gravar ${caminho}.`);
  return true;
}

const lerJson = (texto) => JSON.parse(texto.replace(/^﻿/, ''));

async function lerEstado() {
  return lerJson((await lerArquivo('estado.json')).texto);
}

// Lê o estado mais recente, aplica a mudança e grava como um commit. Se a equipe gravou no meio, repete.
async function alterarEstado(mudar, mensagem) {
  for (let tentativa = 0; tentativa < 4; tentativa++) {
    const { texto, sha } = await lerArquivo('estado.json');
    const estado = lerJson(texto);
    const resultado = mudar(estado);
    if (await gravarArquivo('estado.json', JSON.stringify(estado, null, 2) + '\n', sha, mensagem)) return { estado, resultado };
  }
  throw new ErroEscritorio(409, 'O estado.json mudou várias vezes seguidas. Espere alguns segundos e tente de novo.');
}

// Pedido com anexos: os arquivos e o estado.json entram num commit só (API de dados do Git), então a equipe nunca vê
// um pedido sem os arquivos dele. "mudar" altera o estado e devolve { resultado, arquivos: [{ caminho, conteudo }] }.
// Se alguém gravou no meio (o ramo andou), lê tudo de novo e repete.
async function alterarEstadoComArquivos(mudar, mensagem) {
  const { repo, branch } = config();
  const ramo = `/repos/${repo}/git/refs/heads/${codificar(branch)}`;
  const blobs = new Map(); // o mesmo anexo não sobe duas vezes quando precisa repetir
  const blob = async (conteudo) => {
    if (!blobs.has(conteudo)) {
      const criado = await githubJson(`/repos/${repo}/git/blobs`, 'gravar um anexo', {
        method: 'POST', body: JSON.stringify({ content: conteudo.toString('base64'), encoding: 'base64' }),
      });
      blobs.set(conteudo, criado.sha);
    }
    return blobs.get(conteudo);
  };
  for (let tentativa = 0; tentativa < 4; tentativa++) {
    const base = (await githubJson(`/repos/${repo}/git/ref/heads/${codificar(branch)}`, 'ler o ramo')).object.sha;
    const commit = await githubJson(`/repos/${repo}/git/commits/${base}`, 'ler o último commit');
    const estado = lerJson((await lerArquivo('estado.json', base)).texto);
    const { resultado, arquivos } = mudar(estado);
    const todos = [...arquivos, { caminho: 'estado.json', conteudo: Buffer.from(JSON.stringify(estado, null, 2) + '\n', 'utf8') }];
    const tree = await Promise.all(todos.map(async (a) => ({ path: a.caminho, mode: '100644', type: 'blob', sha: await blob(a.conteudo) })));
    const arvore = await githubJson(`/repos/${repo}/git/trees`, 'montar o commit', {
      method: 'POST', body: JSON.stringify({ base_tree: commit.tree.sha, tree }),
    });
    const novo = await githubJson(`/repos/${repo}/git/commits`, 'criar o commit', {
      method: 'POST', body: JSON.stringify({ message: mensagem, tree: arvore.sha, parents: [base] }),
    });
    const r = await github(ramo, { method: 'PATCH', body: JSON.stringify({ sha: novo.sha, force: false }) });
    if (r.status === 409 || r.status === 422) continue;
    conferirResposta(r, 'gravar o commit');
    return { estado, resultado };
  }
  throw new ErroEscritorio(409, 'O estado.json mudou várias vezes seguidas. Espere alguns segundos e tente de novo.');
}

module.exports = { lerArquivo, lerArquivoBruto, lerEstado, alterarEstado, alterarEstadoComArquivos };
