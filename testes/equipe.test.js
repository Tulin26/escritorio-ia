// Configuração da equipe: todos no Opus 5.5 com esforço alto, skills que existem de verdade e a ficha do painel igual ao
// arquivo de cada agente. Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { RAIZ } = require('./apoio');

const MODELO = 'claude-opus-5-5';
const ESFORCO = 'high';

// Lê o cabeçalho (frontmatter) de um .md: campos simples e listas de "  - item".
function cabecalho(arquivo) {
  const texto = fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n');
  assert.ok(texto.startsWith('---\n'), `${arquivo} sem cabeçalho`);
  const bloco = texto.slice(4, texto.indexOf('\n---\n', 4));
  const campos = {};
  let lista = null;
  for (const linha of bloco.split('\n')) {
    const item = /^\s+-\s+(.+)$/.exec(linha);
    if (item && lista) {
      campos[lista].push(item[1].trim());
      continue;
    }
    const par = /^([\w-]+):\s*(.*)$/.exec(linha);
    if (!par) continue;
    lista = par[2] === '' ? par[1] : null;
    campos[par[1]] = par[2] === '' ? [] : par[2].replace(/^"|"$/g, '');
  }
  return campos;
}

const pastaAgentes = path.join(RAIZ, '.claude', 'agents');
const pastaSkills = path.join(RAIZ, '.claude', 'skills');
const agentes = fs.readdirSync(pastaAgentes).filter((f) => f.endsWith('.md')).map((f) => ({
  id: f.replace(/\.md$/, ''),
  ...cabecalho(path.join(pastaAgentes, f)),
}));
const estado = JSON.parse(fs.readFileSync(path.join(RAIZ, 'estado.json'), 'utf8'));

test('todos os agentes usam o Opus 5.5 com esforço alto', () => {
  assert.ok(agentes.length >= 9);
  for (const a of agentes) {
    assert.equal(a.model, MODELO, `${a.id}: model`);
    assert.equal(a.effort, ESFORCO, `${a.id}: effort`);
  }
});

test('sessões e atalhos também: settings do projeto, /diretor, /rodada, /escritorio e o servidor do PC', () => {
  const settings = JSON.parse(fs.readFileSync(path.join(RAIZ, '.claude', 'settings.json'), 'utf8'));
  assert.equal(settings.model, MODELO);
  assert.equal(settings.effortLevel, ESFORCO);
  for (const atalho of ['diretor', 'rodada', 'escritorio']) {
    const c = cabecalho(path.join(pastaSkills, atalho, 'SKILL.md'));
    assert.equal(c.model, MODELO, atalho);
    assert.equal(c.effort, ESFORCO, atalho);
  }
  const servidor = fs.readFileSync(path.join(RAIZ, 'server.js'), 'utf8');
  assert.match(servidor, new RegExp(`ESCRITORIO_MODELO \\|\\| '${MODELO}'`));
  assert.match(servidor, new RegExp(`ESCRITORIO_ESFORCO \\|\\| '${ESFORCO}'`));
});

test('cada skill de agente existe, tem licença e pode ser carregada no agente', () => {
  for (const a of agentes) {
    for (const nome of a.skills || []) {
      const arquivo = path.join(pastaSkills, nome, 'SKILL.md');
      assert.ok(fs.existsSync(arquivo), `${a.id}: skill ${nome} não existe`);
      const c = cabecalho(arquivo);
      assert.equal(c.name, nome, `${nome}: nome no cabeçalho`);
      assert.notEqual(c['disable-model-invocation'], 'true', `${nome} não pode ser carregada em agente`);
      assert.ok(fs.existsSync(path.join(pastaSkills, nome, 'LICENSE')), `${nome}: falta a LICENSE`);
    }
  }
});

test('skills de setor não aparecem no menu "/" (só os atalhos do dono e a ui-ux-pro-max)', () => {
  const doDono = new Set(['diretor', 'rodada', 'escritorio', 'ui-ux-pro-max']);
  for (const nome of fs.readdirSync(pastaSkills)) {
    const arquivo = path.join(pastaSkills, nome, 'SKILL.md');
    if (!fs.existsSync(arquivo) || doDono.has(nome)) continue;
    assert.equal(cabecalho(arquivo)['user-invocable'], 'false', nome);
  }
});

test('a ficha do painel (estado.json) mostra as mesmas skills do arquivo do agente', () => {
  const ids = new Set(agentes.map((a) => a.id));
  for (const a of estado.agentes) {
    assert.ok(ids.has(a.id), `${a.id} está no estado.json mas não tem arquivo em .claude/agents`);
    const doArquivo = agentes.find((x) => x.id === a.id).skills || [];
    assert.deepEqual(a.skills || [], doArquivo, `${a.id}: skills diferentes`);
    assert.match(a.modelo || '', /Opus 5\.5/, `${a.id}: modelo`);
  }
});

test('o Diretor manda direto para a sala certa, sem começar sempre pela Pesquisa', () => {
  const texto = fs.readFileSync(path.join(pastaAgentes, 'diretor.md'), 'utf8');
  assert.match(texto, /## Para qual sala vai/);
  assert.match(texto, /Pesquisa não é o primeiro passo padrão/);
  assert.doesNotMatch(texto, /Pesquisa → Estratégia → Design/);
});
