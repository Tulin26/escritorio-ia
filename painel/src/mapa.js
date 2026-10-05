import { SALAS } from './dados.js';

const normalizar = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
const PLANTA = {
  reu: [0, 0, 2], dir: [2, 0, 2], voc: [4, 0, 1],
  rec: [0, 1, 1], pes: [1, 1, 1], des: [2, 1, 1], est: [3, 1, 1], cop: [4, 1, 1], soc: [5, 1, 1],
  tra: [0, 2, 1], ven: [1, 2, 1], rev: [2, 2, 1], git: [3, 2, 1], mem: [4, 2, 2],
};
export const LARGURA_MAPA = 960;
export const ALTURA_SALA = 160;

// A planta é apenas apresentação: missões e decisões continuam no estado real.
export function salasDoEstado(estado) {
  const agentes = estado.agentes || [];
  const salasFixas = new Map(SALAS.flatMap((s) => (s.agentes || []).map((id) => [id, s.id])));
  const usados = new Set();
  const salas = SALAS.map((s) => {
    const ids = s.agentes ? agentes.filter((a) => salasFixas.get(a.id) === s.id || (!salasFixas.has(a.id) && normalizar(a.sala) === normalizar(s.nome))).map((a) => a.id) : [];
    ids.forEach((id) => usados.add(id));
    const [coluna, linha, largura] = PLANTA[s.id];
    return { ...s, agentes: ids, x: coluna * 160, y: linha * ALTURA_SALA, w: largura * 160, h: ALTURA_SALA };
  });
  agentes.filter((a) => !usados.has(a.id)).forEach((a, i) => {
    salas.push({ id: `x-${a.id}`, nome: a.sala || a.nome, piso: 'turquesa', agentes: [a.id], x: (i % 6) * 160, y: (3 + Math.floor(i / 6)) * ALTURA_SALA, w: 160, h: ALTURA_SALA });
  });
  return salas;
}

export function alturaMapa(salas) {
  return Math.max(480, ...salas.map((s) => s.y + s.h));
}

export function fluxosDoEstado(estado, salas) {
  const salaDe = new Map(salas.flatMap((s) => s.agentes.map((id) => [id, s.id])));
  const pares = [];
  if ((estado.pedidos || []).some((p) => p.status === 'novo')) pares.push({ de: 'rec', para: 'dir', tipo: 'chegada' });
  for (const m of estado.missoes || []) {
    const sala = salaDe.get(m.agente);
    if (!sala) continue;
    if (['rodando', 'refazer'].includes(m.status) && sala !== 'dir') pares.push({ de: 'dir', para: sala, tipo: 'rodando' });
    if (m.status === 'aguardando') pares.push({ de: sala, para: 'voc', tipo: 'aguardando' });
  }
  if (estado._git?.fila) pares.push({ de: 'rev', para: 'git', tipo: 'git' });
  return [...new Map(pares.map((p) => [`${p.de}>${p.para}:${p.tipo}`, p])).values()];
}
