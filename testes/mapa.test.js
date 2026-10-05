const test = require('node:test');
const assert = require('node:assert/strict');

const carregar = () => import('../painel/src/mapa.js');

test('mapa preserva agentes extras e equipes na mesma sala sem repetir IDs', async () => {
  const { salasDoEstado } = await carregar();
  const agentes = [{ id: 'diretor', nome: 'Diretor' }, { id: 'designer', nome: 'Designer' }, { id: 'ilustrador', nome: 'Ilustrador', sala: 'Marca & Design' }, { id: 'novo', nome: 'Novo', sala: 'Laboratório' }];
  const salas = salasDoEstado({ agentes });
  assert.deepEqual(salas.find((s) => s.id === 'des').agentes, ['designer', 'ilustrador']);
  assert.equal(salas.find((s) => s.id === 'x-novo').nome, 'Laboratório');
  const ids = salas.flatMap((s) => s.agentes);
  assert.equal(new Set(ids).size, agentes.length);
  assert.equal(ids.length, agentes.length);
});

test('salas adicionais ficam dentro do mapa e não sobrepõem as existentes', async () => {
  const { salasDoEstado, alturaMapa, LARGURA_MAPA } = await carregar();
  const salas = salasDoEstado({ agentes: Array.from({ length: 8 }, (_, i) => ({ id: `extra-${i}`, nome: `Agente ${i}` })) });
  const altura = alturaMapa(salas);
  for (const s of salas) {
    assert.ok(s.x >= 0 && s.x + s.w <= LARGURA_MAPA);
    assert.ok(s.y >= 0 && s.y + s.h <= altura);
    for (const outra of salas.filter((a) => a.id !== s.id)) {
      assert.ok(s.x + s.w <= outra.x || outra.x + outra.w <= s.x || s.y + s.h <= outra.y || outra.y + outra.h <= s.y, `${s.id} sobrepõe ${outra.id}`);
    }
  }
  assert.equal(altura, 800);
});

test('fluxos usam status reais, deduplicam rotas e incluem pedidos e Git', async () => {
  const { salasDoEstado, fluxosDoEstado } = await carregar();
  const estado = { agentes: [{ id: 'designer' }, { id: 'copywriter' }], pedidos: [{ status: 'novo' }], _git: { fila: true }, missoes: [{ agente: 'designer', status: 'rodando' }, { agente: 'designer', status: 'refazer' }, { agente: 'copywriter', status: 'aguardando' }, { agente: 'designer', status: 'aprovado' }] };
  const antes = JSON.stringify(estado);
  assert.deepEqual(fluxosDoEstado(estado, salasDoEstado(estado)), [{ de: 'rec', para: 'dir', tipo: 'chegada' }, { de: 'dir', para: 'des', tipo: 'rodando' }, { de: 'cop', para: 'voc', tipo: 'aguardando' }, { de: 'rev', para: 'git', tipo: 'git' }]);
  assert.equal(JSON.stringify(estado), antes);
});

test('escritório vazio mantém as salas de apoio e não inventa atividade', async () => {
  const { salasDoEstado, fluxosDoEstado, alturaMapa } = await carregar();
  const salas = salasDoEstado({});
  assert.equal(alturaMapa(salas), 480);
  assert.ok(salas.some((s) => s.tipo === 'git'));
  assert.deepEqual(fluxosDoEstado({}, salas), []);
});
