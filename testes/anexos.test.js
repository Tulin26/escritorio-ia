// Regras dos anexos dos pedidos (lib/escritorio.js): o que entra, com que nome e o que o painel pode abrir.
// Rodar: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const escritorio = require('../lib/escritorio');
const { PNG, CSV, anexo } = require('./apoio');

test('nome do anexo vira um nome simples, sem pasta, acento nem espaço', () => {
  const [a, b, c] = escritorio.prepararAnexos([
    anexo('Foto da Vitrine (1).PNG', PNG),
    anexo('../../segredos/../Cardápio 2026.csv', CSV),
    anexo('C:\\Users\\joão\\logo.png', PNG),
  ]);
  assert.equal(a.nome, 'foto-da-vitrine-1.png');
  assert.equal(a.tipo, 'image/png');
  assert.equal(b.nome, 'cardapio-2026.csv');
  assert.equal(b.tipo, 'text/csv');
  assert.equal(c.nome, 'logo.png');
  assert.deepEqual(a.conteudo, PNG);
});

test('dois anexos com o mesmo nome ganham -2, -3', () => {
  const nomes = escritorio.prepararAnexos([anexo('logo.png', PNG), anexo('Logo.png', PNG), anexo('LOGO.PNG', PNG)]).map((a) => a.nome);
  assert.deepEqual(nomes, ['logo.png', 'logo-2.png', 'logo-3.png']);
});

test('qualquer tipo entra; só imagem, PDF e texto de verdade abrem no navegador, o resto é baixado', () => {
  const tipos = escritorio.prepararAnexos([
    anexo('TCC.docx', Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x00, 0x00])),
    anexo('programa.exe', Buffer.from([0x4d, 0x5a, 0x00])),
    anexo('desenho.svg', Buffer.from('<svg onload="alert(1)"/>')),
    anexo('Makefile', Buffer.from('all:\n\techo oi\n')),
    anexo('pagina.png', Buffer.from('<html><script>alert(1)</script></html>')),
    anexo('falso.pdf', PNG),
    { nome: 'vazio.txt', dados: '' },
  ], escritorio.LIMITES_ANEXOS.pc).map((a) => [a.nome, a.tipo]);
  assert.deepEqual(tipos, [
    ['tcc.docx', 'application/octet-stream'],
    ['programa.exe', 'application/octet-stream'],
    ['desenho.svg', 'text/plain'],
    ['makefile', 'text/plain'],
    ['pagina.png', 'application/octet-stream'],
    ['falso.pdf', 'application/octet-stream'],
    ['vazio.txt', 'text/plain'],
  ]);
  const recusa = (lista, regex) => assert.throws(() => escritorio.prepararAnexos(lista), regex);
  recusa([{ nome: 'quebrado.png', dados: 'isto não é base64!' }], /corrompido/);
  recusa('não é lista', /anexos inválidos/);
});

test('arquivo de pasta mantém as subpastas, com nomes seguros e sem sair da pasta do pedido', () => {
  const nomes = escritorio.prepararAnexos([
    anexo('x', CSV),
    { caminho: 'TCC Final/Capítulo 1/Introdução.txt', dados: CSV.toString('base64') },
    { caminho: '../../TCC Final/capítulo 1/introducao.txt', dados: CSV.toString('base64') },
    { caminho: 'C:\\Users\\joão\\TCC\\.gitignore', dados: CSV.toString('base64') },
  ]).map((a) => a.nome);
  assert.deepEqual(nomes, ['x', 'tcc-final/capitulo-1/introducao.txt', 'tcc-final/capitulo-1/introducao-2.txt', 'c/users/joao/tcc/gitignore']);
  assert.equal(escritorio.caminhoDeAnexo('../..'), 'anexo');
  assert.equal(escritorio.comNumero('a.b/makefile', 2), 'a.b/makefile-2');
});

test('limites do painel online (padrão): 5 anexos e 3 MB no total', () => {
  const seis = Array.from({ length: 6 }, (_, i) => anexo(`f${i}.png`, PNG));
  assert.throws(() => escritorio.prepararAnexos(seis), /no máximo 5/);
  const grande = Buffer.alloc(2 * 1024 * 1024, 'a');
  assert.throws(() => escritorio.prepararAnexos([anexo('a.txt', grande), anexo('b.txt', grande)]), (e) => e.status === 413);
  assert.equal(escritorio.prepararAnexos([anexo('a.txt', grande)]).length, 1);
  assert.deepEqual(escritorio.prepararAnexos(undefined), []);
});

test('no PC não há limite de quantidade nem de tamanho', () => {
  const pc = escritorio.LIMITES_ANEXOS.pc;
  const muitos = Array.from({ length: 300 }, (_, i) => anexo(`f${i}.png`, PNG));
  assert.equal(escritorio.prepararAnexos(muitos, pc).length, 300);
  const grande = Buffer.alloc(30 * 1024 * 1024, 'a');
  assert.equal(escritorio.prepararAnexos([anexo('a.txt', grande), anexo('b.txt', grande)], pc).length, 2, '60 MB no PC passa');
  assert.throws(() => escritorio.prepararAnexos([anexo('a.txt', grande)]), /passa de 3 MB/, 'online continua 3 MB');
});

test('pedido guarda os anexos em anexos/<id do pedido>/', () => {
  const estado = { pedidos: [{ id: 'p-007' }], missoes: [] };
  const pedido = escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'posts do dia do pão' }, escritorio.prepararAnexos([anexo('Logo.png', PNG)]));
  assert.equal(pedido.id, 'p-008');
  assert.deepEqual(pedido.anexos, [{ nome: 'logo.png', arquivo: 'anexos/p-008/logo.png', tipo: 'image/png', tamanho: PNG.length }]);
  const semAnexo = escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'outro pedido' });
  assert.deepEqual(semAnexo.anexos, []);
});

test('placar zerado: o próximo pedido continua a numeração guardada, sem repetir id', () => {
  const estado = { numeracao: { missao: 4, pedido: 1 }, pedidos: [], missoes: [] };
  assert.equal(escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'posts do dia do pão' }).id, 'p-002');
  assert.equal(escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'mais um pedido' }).id, 'p-003');
});

test('o painel só abre anexos citados por um pedido ou missão, dentro de anexos/', () => {
  const estado = {
    pedidos: [{ id: 'p-001', anexos: [
      { nome: 'logo.png', arquivo: 'anexos/p-001/logo.png', tipo: 'image/png' },
      { nome: 'tcc/cap-1/texto.txt', arquivo: 'anexos/p-001/tcc/cap-1/texto.txt', tipo: 'text/plain' },
    ] }],
    missoes: [{ id: 'm-001', anexos: ['anexos/p-001/cardapio.pdf', 'anexos/p-001/tcc/cap-2/'] }],
  };
  assert.deepEqual(escritorio.anexoCitado(estado, 'anexos/p-001/logo.png'), { caminho: 'anexos/p-001/logo.png', tipo: 'image/png' });
  // Citado só pela missão: o tipo não foi conferido, então só baixa.
  assert.equal(escritorio.anexoCitado(estado, 'anexos\\p-001\\cardapio.pdf').tipo, 'application/octet-stream');
  assert.equal(escritorio.anexoCitado(estado, 'anexos/p-001/tcc/cap-1/texto.txt').tipo, 'text/plain', 'arquivo de subpasta citado pelo pedido');
  assert.equal(escritorio.anexoCitado(estado, 'anexos/p-001/tcc/cap-2/fig.png').tipo, 'application/octet-stream', 'dentro de pasta citada pela missão');
  assert.throws(() => escritorio.anexoCitado(estado, 'anexos/p-001/outra/fig.png'), /não encontrado/);
  for (const ruim of ['estado.json', '../estado.json', 'anexos/p-001/../../estado.json', '/etc/passwd', 'anexos/p-001/Logo.png', 'anexos/p-001/']) {
    assert.throws(() => escritorio.anexoCitado(estado, ruim), /não permitido/, ruim);
  }
  assert.throws(() => escritorio.anexoCitado(estado, 'anexos/p-002/logo.png'), /não encontrado/);
});

test('cabeçalhos do anexo: tipo fixo, sem adivinhar e isolado (fora o PDF)', () => {
  const png = escritorio.cabecalhosDeAnexo({ caminho: 'anexos/p-001/logo.png', tipo: 'image/png' });
  assert.equal(png['Content-Type'], 'image/png');
  assert.equal(png['X-Content-Type-Options'], 'nosniff');
  assert.match(png['Content-Security-Policy'], /sandbox/);
  assert.match(png['Content-Disposition'], /^inline; filename="logo.png"$/);
  const csv = escritorio.cabecalhosDeAnexo({ caminho: 'anexos/p-001/v.csv', tipo: 'text/csv' });
  assert.equal(csv['Content-Type'], 'text/plain; charset=utf-8');
  const pdf = escritorio.cabecalhosDeAnexo({ caminho: 'anexos/p-001/c.pdf', tipo: 'application/pdf' });
  assert.equal(pdf['Content-Security-Policy'], undefined);
  const docx = escritorio.cabecalhosDeAnexo({ caminho: 'anexos/p-001/tcc/tcc.docx', tipo: 'application/octet-stream' });
  assert.match(docx['Content-Disposition'], /^attachment; filename="tcc.docx"$/);
  assert.match(docx['Content-Security-Policy'], /sandbox/);
});
