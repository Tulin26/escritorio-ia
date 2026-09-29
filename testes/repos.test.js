// Repositórios dos projetos (lib/repos.js), com um GitHub CLI de mentira (testes/gh-de-mentira.js).
// Nada vai para a internet. Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { criarRepos } = require('../lib/repos');
const { pastaTemporaria, apagar, ambienteGit, temGit } = require('./apoio');

const opcoes = { skip: temGit ? false : 'o Git não está instalado neste PC' };
const GH = [process.execPath, path.join(__dirname, 'gh-de-mentira.js')];

function montar(t, extra = {}) {
  const pasta = pastaTemporaria('repos');
  t.after(() => apagar(pasta));
  const env = { ...ambienteGit(pasta), GH_DE_MENTIRA: pasta, ...extra };
  const escritorio = path.join(pasta, 'escritorio');
  fs.mkdirSync(path.join(escritorio, 'projetos'), { recursive: true });
  fs.writeFileSync(path.join(escritorio, 'projetos', 'loja-x.md'), '# Briefing do projeto: Loja X\n\n- **O que é:** site da Loja X\n');
  const estado = { projetos: [{ id: 'loja-x', nome: 'Loja X', briefing: 'projetos/loja-x.md' }] };
  const repos = criarRepos({ raiz: escritorio, pastaProjetos: path.join(pasta, 'projetos'), gh: GH, env });
  const git = (cwd, ...a) => execFileSync('git', a, { cwd, env, encoding: 'utf8' }).trim();
  return { pasta, escritorio, estado, repos, git };
}

test('cria a pasta do projeto fora do escritório e o repositório privado, e depois envia mudanças', opcoes, async (t) => {
  const { pasta, estado, repos, git } = montar(t);
  const antes = await repos.resumo(estado);
  assert.equal(antes.gh.pronto, true);
  assert.equal(antes.gh.conta, 'tester');
  assert.equal(antes.projetos[0].repo, null);

  const repo = await repos.criar(estado, 'loja-x');
  assert.equal(repo.pasta, path.join(pasta, 'projetos', 'loja-x'));
  assert.equal(repo.url, 'https://github.com/tester/loja-x');
  assert.equal(repo.nome, 'tester/loja-x');
  assert.equal(repo.privado, true);
  assert.match(fs.readFileSync(path.join(repo.pasta, 'README.md'), 'utf8'), /# Loja X\n\nsite da Loja X/);
  assert.ok(fs.existsSync(path.join(repo.pasta, '.gitignore')));
  const remoto = path.join(pasta, 'loja-x.git');
  assert.match(git(remoto, 'log', '--oneline', 'main'), /Começo do projeto/);

  estado.projetos[0].repo = repo;
  fs.writeFileSync(path.join(repo.pasta, 'index.html'), '<h1>Loja X</h1>\n');
  const status = (await repos.resumo(estado)).projetos[0].git;
  assert.equal(status.disponivel, true);
  assert.equal(status.pendentes, 1);
  const ultimo = await repos.enviar(estado, 'loja-x');
  assert.equal(ultimo.ok, true);
  assert.match(git(remoto, 'show', 'main:index.html'), /Loja X/);

  await assert.rejects(repos.criar(estado, 'loja-x'), /já tem repositório/);
});

test('sem login no GitHub CLI, não cria nada e explica o que fazer', opcoes, async (t) => {
  const { pasta, estado, repos } = montar(t, { GH_SEM_LOGIN: '1' });
  const r = await repos.resumo(estado);
  assert.equal(r.gh.pronto, false);
  assert.match(r.gh.motivo, /gh auth login/);
  await assert.rejects(repos.criar(estado, 'loja-x'), /gh auth login/);
  assert.equal(fs.existsSync(path.join(pasta, 'projetos', 'loja-x')), false);
});

test('GitHub CLI não instalado e projeto desconhecido', opcoes, async (t) => {
  const { escritorio, estado } = montar(t);
  const semGh = criarRepos({ raiz: escritorio, gh: ['gh-que-nao-existe-123'] });
  const r = await semGh.statusGh();
  assert.equal(r.pronto, false);
  assert.match(r.motivo, /winget install/);
  await assert.rejects(semGh.criar(estado, 'nao-existe'), /não encontrado/);
});
