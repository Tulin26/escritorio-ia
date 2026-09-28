// Sala Git & GitHub no PC (lib/git.js), testada contra um GitHub de mentira: um repositório Git numa pasta temporária.
// Nada vai para a internet. Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { criarGit, enderecoSeguro } = require('../lib/git');
const { PNG, pastaTemporaria, apagar, ambienteGit, temGit, criarGithubDeMentira } = require('./apoio');

const opcoes = { skip: temGit ? false : 'o Git não está instalado neste PC' };

// Um escritório de teste já clonado do GitHub de mentira, com a sala Git apontando para ele.
function montar(t) {
  const pasta = pastaTemporaria('git');
  t.after(() => apagar(pasta));
  const g = criarGithubDeMentira(pasta, { 'estado.json': '{\n  "pedidos": []\n}\n', 'copy/texto.md': 'linha 1\n' });
  const sala = criarGit(g.escritorio, { env: g.env });
  const noGithub = (...args) => g.git(g.remoto, ...args);
  return { ...g, pasta, sala, noGithub };
}

test('pasta que não é repositório, ou que está dentro de outro, não envia nada', opcoes, async (t) => {
  const pasta = pastaTemporaria('git-fora');
  t.after(() => apagar(pasta));
  const env = ambienteGit(pasta);
  const solta = path.join(pasta, 'solta');
  fs.mkdirSync(solta);
  const r1 = await criarGit(solta, { env }).resumo();
  assert.equal(r1.disponivel, false);
  assert.match(r1.motivo, /não é um repositório Git/);

  const g = criarGithubDeMentira(pasta);
  const dentro = path.join(g.escritorio, 'sub-escritorio');
  fs.mkdirSync(dentro);
  const r2 = await criarGit(dentro, { env }).resumo();
  assert.equal(r2.disponivel, false);
  assert.match(r2.motivo, /dentro de outro repositório/);
  await assert.rejects(criarGit(dentro, { env }).enviar('teste'), /dentro de outro repositório/);
});

test('sem remoto configurado, avisa em vez de tentar', opcoes, async (t) => {
  const { sala, git, escritorio } = montar(t);
  git(escritorio, 'remote', 'remove', 'origin');
  const r = await sala.resumo();
  assert.equal(r.disponivel, false);
  assert.match(r.motivo, /remoto "origin"/);
});

test('envia tudo o que mudou: commit com o motivo, anexos byte a byte e nome padrão', opcoes, async (t) => {
  const { sala, escritorio, noGithub } = montar(t);
  const binario = Buffer.concat([PNG, Buffer.from('\r\n\r\n')]); // CRLF de propósito: não pode virar LF
  fs.mkdirSync(path.join(escritorio, 'anexos', 'p-001'), { recursive: true });
  fs.writeFileSync(path.join(escritorio, 'anexos', 'p-001', 'foto.png'), binario);
  fs.writeFileSync(path.join(escritorio, 'estado.json'), '{\n  "pedidos": [1]\n}\n');

  const antes = await sala.resumo();
  assert.equal(antes.disponivel, true);
  assert.equal(antes.ramo, 'main');
  assert.equal(antes.pendentes, 2);
  assert.deepEqual([...antes.arquivos].sort(), ['anexos/p-001/foto.png', 'estado.json']);

  const ultimo = await sala.enviar('rodada da equipe (novo pedido p-001)');
  assert.equal(ultimo.ok, true);
  assert.match(ultimo.resumo, /2 arquivo\(s\)/);
  assert.equal(noGithub('log', '-1', '--format=%s|%an'), 'Escritório: rodada da equipe (novo pedido p-001)|Escritório de IA');
  const noRemoto = require('child_process').execFileSync('git', ['show', 'main:anexos/p-001/foto.png'], { cwd: path.join(escritorio, '..', 'github-de-mentira.git') });
  assert.deepEqual(noRemoto, binario);

  const depois = await sala.resumo();
  assert.equal(depois.pendentes, 0);
  assert.equal(depois.adiante, 0);
  assert.equal(depois.ultimo.commit, ultimo.commit);
});

test('sem nada novo, não cria commit vazio', opcoes, async (t) => {
  const { sala, noGithub } = montar(t);
  const commits = noGithub('rev-list', '--count', 'main');
  const ultimo = await sala.enviar('você pediu para enviar agora');
  assert.equal(ultimo.ok, true);
  assert.match(ultimo.resumo, /Nada novo/);
  assert.equal(noGithub('rev-list', '--count', 'main'), commits);
});

test('se o GitHub andou (painel online), traz antes e envia por cima', opcoes, async (t) => {
  const { sala, pasta, git, remoto, escritorio, noGithub } = montar(t);
  // Outro "PC" (a nuvem) grava no GitHub um arquivo diferente.
  const nuvem = path.join(pasta, 'nuvem');
  git(pasta, 'clone', '--quiet', remoto, nuvem);
  fs.writeFileSync(path.join(nuvem, 'copy', 'da-nuvem.md'), 'feito na nuvem\n');
  git(nuvem, 'add', '-A');
  git(nuvem, '-c', 'user.name=Nuvem', '-c', 'user.email=n@x', 'commit', '--quiet', '-m', 'Rodada da equipe na nuvem');
  git(nuvem, 'push', '--quiet', 'origin', 'main');

  fs.writeFileSync(path.join(escritorio, 'estado.json'), '{\n  "pedidos": ["do PC"]\n}\n');
  const ultimo = await sala.enviar('aprovou m-001');
  assert.equal(ultimo.ok, true);
  assert.equal(noGithub('log', '--format=%s', '-2'), 'Escritório: aprovou m-001\nRodada da equipe na nuvem');
  assert.equal(fs.readFileSync(path.join(escritorio, 'copy', 'da-nuvem.md'), 'utf8'), 'feito na nuvem\n');
});

test('conflito com o GitHub: desfaz, não perde nada e explica o que fazer', opcoes, async (t) => {
  const { sala, pasta, git, remoto, escritorio, noGithub } = montar(t);
  const nuvem = path.join(pasta, 'nuvem');
  git(pasta, 'clone', '--quiet', remoto, nuvem);
  fs.writeFileSync(path.join(nuvem, 'copy', 'texto.md'), 'linha 1 (versão da nuvem)\n');
  git(nuvem, '-c', 'user.name=Nuvem', '-c', 'user.email=n@x', 'commit', '--quiet', '-am', 'nuvem');
  git(nuvem, 'push', '--quiet', 'origin', 'main');
  const noRemotoAntes = noGithub('rev-parse', 'main');

  fs.writeFileSync(path.join(escritorio, 'copy', 'texto.md'), 'linha 1 (versão do PC)\n');
  await assert.rejects(sala.enviar('rodada'), /batem de frente/);
  assert.equal(noGithub('rev-parse', 'main'), noRemotoAntes, 'o GitHub não pode mudar');
  assert.equal(git(escritorio, 'log', '-1', '--format=%s'), 'Escritório: rodada', 'o commit do PC continua no PC');
  assert.equal(fs.readFileSync(path.join(escritorio, 'copy', 'texto.md'), 'utf8'), 'linha 1 (versão do PC)\n');
  const r = await sala.resumo();
  assert.equal(r.disponivel, true, 'nada de rebase pela metade');
  assert.equal(r.adiante, 1);
  assert.equal(r.ultimo.ok, false);
});

test('não envia duas vezes ao mesmo tempo', opcoes, async (t) => {
  const { sala, escritorio } = montar(t);
  fs.writeFileSync(path.join(escritorio, 'novo.md'), 'x\n');
  const primeiro = sala.enviar('um');
  await assert.rejects(sala.enviar('dois'), (e) => e.ocupado === true);
  assert.equal((await primeiro).ok, true);
});

test('conferir antes: se falhar, nada é enviado', opcoes, async (t) => {
  const { sala, escritorio, noGithub } = montar(t);
  fs.writeFileSync(path.join(escritorio, 'estado.json'), '{ quebrado');
  const commits = noGithub('rev-list', '--count', 'main');
  await assert.rejects(sala.enviar('rodada', { conferir: () => { throw new Error('JSON inválido'); } }), /JSON inválido/);
  assert.equal(noGithub('rev-list', '--count', 'main'), commits);
  assert.equal((await sala.resumo()).pendentes, 1);
});

test('endereço do GitHub aparece sem usuário nem token', () => {
  assert.equal(enderecoSeguro('https://joao:ghp_segredo@github.com/Tulin26/escritorio-ia.git'), 'github.com/Tulin26/escritorio-ia');
  assert.equal(enderecoSeguro('git@github.com:Tulin26/escritorio-ia.git'), 'github.com/Tulin26/escritorio-ia');
  assert.equal(enderecoSeguro('C:\\testes\\github-de-mentira.git'), 'C:\\testes\\github-de-mentira.git');
});
