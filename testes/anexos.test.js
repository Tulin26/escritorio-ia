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

test('tipo não aceito, conteúdo falso, vazio ou corrompido é recusado', () => {
  const recusa = (lista, regex) => assert.throws(() => escritorio.prepararAnexos(lista), regex);
  recusa([anexo('desenho.svg', Buffer.from('<svg onload="alert(1)"/>'))], /não é de um tipo aceito/);
  recusa([anexo('programa.exe', PNG)], /não é de um tipo aceito/);
  recusa([anexo('sem-extensao', PNG)], /não é de um tipo aceito/);
  recusa([anexo('pagina.png', Buffer.from('<html><script>alert(1)</script></html>'))], /não é o que a extensão diz/);
  recusa([anexo('falso.pdf', PNG)], /não é o que a extensão diz/);
  recusa([anexo('binario.txt', Buffer.from([0x41, 0x00, 0x42]))], /não é o que a extensão diz/);
  recusa([{ nome: 'vazio.txt', dados: '' }], /corrompido/);
  recusa([{ nome: 'quebrado.png', dados: 'isto não é base64!' }], /corrompido/);
  recusa('não é lista', /anexos inválidos/);
});

test('limites: 5 anexos e 3 MB no total', () => {
  const seis = Array.from({ length: 6 }, (_, i) => anexo(`f${i}.png`, PNG));
  assert.throws(() => escritorio.prepararAnexos(seis), /no máximo 5/);
  const grande = Buffer.alloc(2 * 1024 * 1024, 'a');
  assert.throws(() => escritorio.prepararAnexos([anexo('a.txt', grande), anexo('b.txt', grande)]), (e) => e.status === 413);
  assert.equal(escritorio.prepararAnexos([anexo('a.txt', grande)]).length, 1);
  assert.deepEqual(escritorio.prepararAnexos(undefined), []);
});

test('pedido guarda os anexos em anexos/<id do pedido>/', () => {
  const estado = { pedidos: [{ id: 'p-007' }], missoes: [] };
  const pedido = escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'posts do dia do pão' }, escritorio.prepararAnexos([anexo('Logo.png', PNG)]));
  assert.equal(pedido.id, 'p-008');
  assert.deepEqual(pedido.anexos, [{ nome: 'logo.png', arquivo: 'anexos/p-008/logo.png', tipo: 'image/png', tamanho: PNG.length }]);
  const semAnexo = escritorio.novoPedido(estado, { projeto: 'Padaria', texto: 'outro pedido' });
  assert.deepEqual(semAnexo.anexos, []);
});

test('o painel só abre anexos citados por um pedido ou missão, dentro de anexos/', () => {
  const estado = {
    pedidos: [{ id: 'p-001', anexos: [{ nome: 'logo.png', arquivo: 'anexos/p-001/logo.png' }] }],
    missoes: [{ id: 'm-001', anexos: ['anexos/p-001/cardapio.pdf'] }],
  };
  assert.deepEqual(escritorio.anexoCitado(estado, 'anexos/p-001/logo.png'), { caminho: 'anexos/p-001/logo.png', tipo: 'image/png' });
  assert.equal(escritorio.anexoCitado(estado, 'anexos\\p-001\\cardapio.pdf').tipo, 'application/pdf');
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
});
