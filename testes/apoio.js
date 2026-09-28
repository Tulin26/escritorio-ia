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

module.exports = { RAIZ, PNG, CSV, anexo, pastaTemporaria, apagar, ambienteGit, temGit, criarGithubDeMentira };
