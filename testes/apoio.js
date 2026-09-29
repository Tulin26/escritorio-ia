// Ajudantes dos testes: pastas temporárias, arquivos de exemplo e um "GitHub de mentira" dentro do PC.
// O GitHub de mentira é um repositório Git vazio (bare) numa pasta temporária: o push vai para lá, nunca para a internet.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const RAIZ = path.join(__dirname, '..');

// PNG de 1x1 pixel e um CSV: o suficiente para passar pela conferência de tipo dos anexos.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
const CSV = Buffer.from('produto,preço,vendas\r\npão francês,0.90,420\r\n', 'utf8');
const anexo = (nome, conteudo) => ({ nome, dados: conteudo.toString('base64') });

// estado.json de exemplo: os agentes vêm do estado.json de verdade e as missões do projeto Matriz são fixas,
// porque o placar de verdade pode ser zerado a qualquer momento (e aí não haveria m-004 para testar).
const missaoDeExemplo = (id, area, agente, arquivo, xp, dep) => ({
  id, projeto: 'matriz', area, agente, titulo: `Missão ${id}`, resumo: `Exemplo | depende de: ${dep}`,
  arquivo, status: 'aprovado', xp, data: '2026-09-28 12:00', comentario: '',
});
function estadoDeExemplo() {
  const real = JSON.parse(fs.readFileSync(path.join(RAIZ, 'estado.json'), 'utf8').replace(/^﻿/, ''));
  return `${JSON.stringify({
    ...real,
    git: { ligado: false }, // o envio automático de verdade pode estar ligado; os testes começam desligados
    numeracao: { missao: 4, pedido: 1 },
    projetos: [{ id: 'matriz', nome: 'Matriz', briefing: 'projetos/matriz.md' }],
    pedidos: [{ id: 'p-001', projeto: 'matriz', projetoNome: 'Matriz', texto: 'eu quero um resumo sobre matrizes', status: 'feito', missao: 'm-001', data: '2026-09-25 15:25' }],
    missoes: [
      missaoDeExemplo('m-001', 'diretor', 'diretor', 'diretor/m-001-matriz-plano.md', 10, '-'),
      missaoDeExemplo('m-002', 'pesquisa', 'pesquisador', 'pesquisa/m-002-matriz-conteudo.md', 20, 'm-001'),
      missaoDeExemplo('m-003', 'copy', 'copywriter', 'copy/m-003-matriz-resumo.md', 30, 'm-002'),
      missaoDeExemplo('m-004', 'revisor', 'revisor', 'revisor/m-004-matriz-revisao.md', 10, 'm-003'),
    ],
  }, null, 2)}\n`;
}

function pastaTemporaria(prefixo) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `escritorio-${prefixo}-`));
}

function apagar(pasta) {
  try {
    fs.rmSync(pasta, { recursive: true, force: true, maxRetries: 3 });
  } catch {
    // no Windows um arquivo ainda aberto pode travar; a pasta temporária some depois
  }
}

// Git sem a configuração do PC (nome, credenciais, assinatura): o teste não depende de nada da máquina.
function ambienteGit(pasta) {
  const vazio = path.join(pasta, 'gitconfig-vazio');
  fs.writeFileSync(vazio, '');
  return { ...process.env, GIT_CONFIG_GLOBAL: vazio, GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' };
}

const temGit = (() => {
  try {
    execFileSync('git', ['--version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
})();

// Cria o GitHub de mentira e um clone dele com um primeiro commit (os arquivos dados), já enviado.
function criarGithubDeMentira(pasta, arquivos = { 'estado.json': '{}\n' }) {
  const env = ambienteGit(pasta);
  const git = (cwd, ...args) => execFileSync('git', args, { cwd, env, encoding: 'utf8' }).trim();
  const remoto = path.join(pasta, 'github-de-mentira.git');
  const escritorio = path.join(pasta, 'escritorio');
  git(pasta, 'init', '--quiet', '--bare', '-b', 'main', remoto);
  fs.mkdirSync(escritorio, { recursive: true });
  for (const [nome, conteudo] of Object.entries(arquivos)) {
    fs.mkdirSync(path.dirname(path.join(escritorio, nome)), { recursive: true });
    fs.writeFileSync(path.join(escritorio, nome), conteudo);
  }
  git(escritorio, 'init', '--quiet', '-b', 'main');
  git(escritorio, 'add', '-A');
  git(escritorio, '-c', 'user.name=Teste', '-c', 'user.email=teste@exemplo', 'commit', '--quiet', '-m', 'começo');
  git(escritorio, 'remote', 'add', 'origin', remoto);
  git(escritorio, 'push', '--quiet', '-u', 'origin', 'main');
  return { env, git, remoto, escritorio };
}

module.exports = { RAIZ, PNG, CSV, anexo, estadoDeExemplo, pastaTemporaria, apagar, ambienteGit, temGit, criarGithubDeMentira };
