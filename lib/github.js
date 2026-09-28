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
    },
  });
}

async function lerArquivo(caminho) {
  const { repo, branch } = config();
  const r = await github(`/repos/${repo}/contents/${codificar(caminho)}?ref=${encodeURIComponent(branch)}`);
  if (r.status === 404) throw new ErroEscritorio(404, `Arquivo não encontrado: ${caminho}`);
  if (r.status === 401 || r.status === 403) throw new ErroEscritorio(502, 'O GitHub recusou o GITHUB_TOKEN: confira se ele vale para este repositório.');
  if (!r.ok) throw new ErroEscritorio(502, `O GitHub respondeu ${r.status} ao ler ${caminho}.`);
  const dados = await r.json();
  return { texto: Buffer.from(dados.content || '', 'base64').toString('utf8'), sha: dados.sha };
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

module.exports = { lerArquivo, lerEstado, alterarEstado };
