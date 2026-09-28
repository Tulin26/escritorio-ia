// Escritório de IA: lógica do painel pixel art (sem dependências)
'use strict';

const STATUS = ['backlog', 'rodando', 'aguardando', 'aprovado', 'refazer'];
const INTERVALO_MS = 3000;

// Pisos quadriculados: [cor 1, cor 2, borda]
const PISOS = {
  roxo: ['#5b3f8c', '#684c9c', '#2a1b47'],
  verde: ['#3d7447', '#488553', '#1c3a22'],
  azul: ['#37569a', '#4263aa', '#1a2b4f'],
  marrom: ['#74502f', '#835c3a', '#3a2716'],
  turquesa: ['#2a8584', '#349796', '#134242'],
};

// Uma sala por área; "mem" (Memória) não tem agente: guarda briefings e entregas aprovadas.
const SALAS = [
  { id: 'dir', agente: 'diretor', nome: 'Diretoria', piso: 'marrom' },
  { id: 'pes', agente: 'pesquisador', nome: 'Pesquisa', piso: 'verde' },
  { id: 'est', agente: 'estrategista', nome: 'Estratégia', piso: 'azul' },
  { id: 'cop', agente: 'copywriter', nome: 'Copy', piso: 'roxo' },
  { id: 'soc', agente: 'social', nome: 'Social', piso: 'turquesa' },
  { id: 'ven', agente: 'vendas', nome: 'Vendas', piso: 'marrom' },
  { id: 'rev', agente: 'revisor', nome: 'Revisão', piso: 'roxo' },
  { id: 'mem', agente: null, nome: 'Memória', piso: 'azul' },
];

const VISUAL = {
  diretor: { cabelo: '#2b1d14', pele: '#e0a878', roupa: '#2f3f73' },
  pesquisador: { cabelo: '#7a4a24', pele: '#f1c29a', roupa: '#3f8a4f' },
  estrategista: { cabelo: '#15131c', pele: '#c98c5e', roupa: '#4a5fc1' },
  copywriter: { cabelo: '#c4662a', pele: '#f3cfa8', roupa: '#9b3fa0' },
  social: { cabelo: '#5c2a6e', pele: '#e8b48c', roupa: '#e0567f' },
  vendas: { cabelo: '#3a2616', pele: '#a8703f', roupa: '#2f9c8a' },
  revisor: { cabelo: '#9a9aa8', pele: '#f0c8a0', roupa: '#5b5f6e' },
};
const VISUAL_PADRAO = { cabelo: '#333', pele: '#e0b090', roupa: '#777' };

let estado = null;
let ultimoJson = '';
let filtroStatus = '';
let filaPendente = false;
let fichaAtual = null;
const refazerAberto = new Set();
const rascunhos = {};

const $ = (id) => document.getElementById(id);

function h(tag, attrs = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style') el.style.cssText = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const f of filhos.flat()) if (f !== null && f !== undefined && f !== false) el.append(f);
  return el;
}

function svg(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// ---------- Sprites pixel art desenhados em canvas ----------

// Desenha vários quadros lado a lado e devolve um data URL (folha de sprites).
function folhaSprites(quadros, paleta, escala) {
  const alt = quadros[0].length;
  const larg = quadros[0][0].length;
  const canvas = document.createElement('canvas');
  canvas.width = larg * quadros.length * escala;
  canvas.height = alt * escala;
  const ctx = canvas.getContext('2d');
  quadros.forEach((linhas, q) => {
    linhas.forEach((linha, y) => {
      [...linha].forEach((ch, x) => {
        const cor = paleta[ch];
        if (!cor) return;
        ctx.fillStyle = cor;
        ctx.fillRect((q * larg + x) * escala, y * escala, escala, escala);
      });
    });
  });
  return canvas.toDataURL();
}

const cacheSprites = new Map();
function sprite(chave, gerar) {
  if (!cacheSprites.has(chave)) cacheSprites.set(chave, gerar());
  return cacheSprites.get(chave);
}

// Boneco 12x16: H cabelo, S pele, E olho, m boca, C roupa, P calça, B sapato
const CORPO = [
  '....HHHH....',
  '...HHHHHH...',
  '..HHHHHHHH..',
  '..HSSSSSSH..',
  '..SSESSESS..',
  '..SSSSSSSS..',
  '...SSmmSS...',
  '....SSSS....',
  '..CCCCCCCC..',
  '.CCCCCCCCCC.',
  '.SCCCCCCCCS.',
  '.SCCCCCCCCS.',
  '..PPPPPPPP..',
  '..PPP..PPP..',
  '..PPP..PPP..',
  '..BBB..BBB..',
];
const trocarLinhas = (base, trocas) => base.map((linha, i) => trocas[i] || linha);
// Quadro 0 parado; quadros 1 e 2 são as mãos alternando no teclado.
const QUADROS_AGENTE = [
  CORPO,
  trocarLinhas(CORPO, { 9: '.SCCCCCCCCC.', 10: '.CCCCCCCCCS.', 11: '.CCCCCCCCCC.' }),
  trocarLinhas(CORPO, { 9: '.CCCCCCCCCS.', 10: '.SCCCCCCCCC.', 11: '.CCCCCCCCCC.' }),
];
// Dono: terno com camisa (W) e gravata (T)
const DONO = trocarLinhas(CORPO, { 8: '..CCWTTWCC..', 9: '.CCCWTTWCCC.', 10: '.SCCCTTCCCS.' });

function paletaPessoa(v) {
  return { H: v.cabelo, S: v.pele, E: '#1a1420', m: '#b8505a', C: v.roupa, W: '#f2ecdc', T: '#d83a3a', P: '#2c2838', B: '#141018' };
}
const spriteAgente = (id) => sprite('ag:' + id, () => folhaSprites(QUADROS_AGENTE, paletaPessoa(VISUAL[id] || VISUAL_PADRAO), 3));
const spriteDono = () => sprite('dono', () => folhaSprites([DONO], paletaPessoa({ cabelo: '#3b2718', pele: '#d9a074', roupa: '#2a2f45' }), 4));

// Mesa 24x11 com monitor (G desligado / g ligado) e caneca
const MESA = [
  'KKKKKKKK................',
  'KGGGGGGK................',
  'KGGGGGGK................',
  'KKKKKKKK..........CC....',
  '...KK.............CCc...',
  'LLLLLLLLLLLLLLLLLLLLLLLL',
  'WWWWWWWWWWWWWWWWWWWWWWWW',
  'WWWWWWWWWWWWWWWWWWWWWWWW',
  'DDDDDDDDDDDDDDDDDDDDDDDD',
  'DD....................DD',
  'DD....................DD',
];
const MESA_LIGADA = MESA.map((l) => l.replace(/G/g, 'g'));
const spriteMesa = () => sprite('mesa', () => folhaSprites([MESA, MESA_LIGADA], {
  K: '#0f0d16', G: '#1b2233', g: '#7fd4ff', C: '#f2ecdc', c: '#f2ecdc', L: '#c08a55', W: '#9a6a3e', D: '#5e3f22',
}, 3));

const PLANTA = [
  '...G..G...',
  '..GGG.GG..',
  '.GGgGGgGG.',
  'GGgGGGGgGG',
  '.GGGgGGGG.',
  '..GGGGGG..',
  '...GGGG...',
  '..PPPPPP..',
  '..PpPPpP..',
  '..PPPPPP..',
  '...PPPP...',
];
const spritePlanta = () => sprite('planta', () => folhaSprites([PLANTA], { G: '#4caf50', g: '#2e7d32', P: '#b5651d', p: '#8a4b16' }, 3));

// Estante 16x14: F madeira, livros coloridos (r y b g p) separados por k
const ESTANTE = [
  'FFFFFFFFFFFFFFFF',
  'FrrkyybkgpprkybF',
  'FrrkyybkgpprkybF',
  'FrrkyybkgpprkybF',
  'FFFFFFFFFFFFFFFF',
  'FbbgkpprkyybgpkF',
  'FbbgkpprkyybgpkF',
  'FbbgkpprkyybgpkF',
  'FFFFFFFFFFFFFFFF',
  'FyykbgpprkbbgyyF',
  'FyykbgpprkbbgyyF',
  'FyykbgpprkbbgyyF',
  'FFFFFFFFFFFFFFFF',
  'FF............FF',
];
const spriteEstante = () => sprite('estante', () => folhaSprites([ESTANTE], {
  F: '#6b4423', r: '#e04848', y: '#f2c14e', b: '#4d7fe0', g: '#4caf50', p: '#b05ed8', k: '#3b2414',
}, 3));

// ---------- Cálculos a partir do estado.json ----------
const missoesDe = (agenteId) => (estado.missoes || []).filter((m) => m.agente === agenteId);
const xpDe = (lista) => lista.filter((m) => m.status === 'aprovado').reduce((t, m) => t + (Number(m.xp) || 0), 0);
const nivelDe = (xp) => 1 + Math.floor(xp / 100);
const nomeAgente = (id) => ((estado.agentes || []).find((a) => a.id === id) || {}).nome || id;

function situacao(lista) {
  if (lista.some((m) => m.status === 'rodando' || m.status === 'refazer')) return 'rodando';
  if (lista.some((m) => m.status === 'aguardando')) return 'aguardando';
  return 'livre';
}
const ROTULO_SITUACAO = { rodando: 'trabalhando', aguardando: 'esperando sua aprovação', livre: 'livre' };

// ---------- Render ----------
function aplicar(dados, forcarFila) {
  estado = dados;
  ultimoJson = JSON.stringify(dados);
  renderTopo();
  renderAutomacao();
  renderPlanta();
  renderFila(forcarFila);
  renderPedidos();
  renderMissoes();
  if (fichaAtual && fichaAtual.tipo === 'agente') fichaAgente(fichaAtual.id);
  if (fichaAtual && fichaAtual.tipo === 'memoria') fichaMemoria();
}

function renderTopo() {
  const missoes = estado.missoes || [];
  const xp = xpDe(missoes);
  $('cEntregues').textContent = missoes.filter((m) => m.status === 'aprovado').length;
  $('cXp').textContent = xp;
  $('cNivel').textContent = nivelDe(xp);
  $('cNivelBarra').style.width = `${xp % 100}%`;
  const hora = new Date().toLocaleTimeString('pt-BR');
  $('subtitulo').textContent = `${(estado.projetos || []).length} projeto(s) · ${missoes.length} missão(ões) · atualizado ${hora}`;
}

function renderPlanta() {
  const agentes = estado.agentes || [];
  const conhecidos = new Set(SALAS.map((s) => s.agente).filter(Boolean));
  const extras = agentes
    .filter((a) => !conhecidos.has(a.id))
    .map((a) => ({ id: 'x-' + a.id, agente: a.id, nome: a.sala || a.nome, piso: 'turquesa', livre: true }));
  $('planta').replaceChildren(...[...SALAS, ...extras].map(montarSala));
  requestAnimationFrame(desenharLinhas);
}

function montarSala(s) {
  const [c1, c2, borda] = PISOS[s.piso];
  const ag = s.agente ? (estado.agentes || []).find((a) => a.id === s.agente) : null;
  const nomeSala = (ag && ag.sala) || s.nome;
  const el = h('section', {
    class: `sala sala-${s.id}`,
    'data-sala': s.id,
    'data-agente': s.agente || '',
    role: 'button',
    tabindex: '0',
    'aria-label': `Sala ${nomeSala}. Abrir ficha`,
    style: `${s.livre ? '' : `grid-area:${s.id};`} --c1:${c1}; --c2:${c2}; --borda:${borda}`,
  });
  el.append(h('div', { class: 'placa' }, nomeSala));
  if (s.id === 'dir') el.append(h('div', { class: 'tapete', 'aria-hidden': 'true' }));
  el.append(
    h('span', { class: 'deco-planta e', 'aria-hidden': 'true', style: `background-image:url(${spritePlanta()})` }),
    h('span', { class: 'deco-planta d', 'aria-hidden': 'true', style: `background-image:url(${spritePlanta()})` }),
  );

  if (s.id === 'mem') {
    const aprovadas = (estado.missoes || []).filter((m) => m.status === 'aprovado').length;
    el.append(
      h('div', { class: 'estantes', 'aria-hidden': 'true' },
        ...[0, 1, 2, 3].map(() => h('span', { class: 'estante', style: `background-image:url(${spriteEstante()})` }))),
      h('div', { class: 'mem-info' }, `${(estado.projetos || []).length} briefing(s)`, h('br'), `${aprovadas} entrega(s) aprovada(s)`),
    );
  } else if (ag) {
    el.append(h('div', { class: 'postos' }, posto(ag)));
  } else {
    el.append(h('div', { class: 'mem-info' }, 'Sala sem agente no estado.json'));
  }

  el.addEventListener('click', () => {
    if (s.id === 'mem') fichaMemoria();
    else if (ag) fichaAgente(ag.id);
  });
  el.addEventListener('keydown', (e) => {
    if (e.target === el && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      el.click();
    }
  });
  return el;
}

function posto(ag) {
  const minhas = missoesDe(ag.id);
  const sit = situacao(minhas);
  const lv = nivelDe(xpDe(minhas));
  const trabalhando = sit === 'rodando';
  const btn = h('button', {
      class: 'agente', type: 'button',
      'aria-label': `${ag.nome}, nível ${lv}, ${ROTULO_SITUACAO[sit]}. Abrir ficha`,
    },
    trabalhando ? h('span', { class: 'balao', 'aria-hidden': 'true' }, h('i'), h('i'), h('i')) : null,
    h('span', { class: 'boneco' + (trabalhando ? ' digitando' : ''), style: `background-image:url(${spriteAgente(ag.id)})` }),
    h('span', { class: 'mesa' + (trabalhando ? ' ligada' : ''), style: `background-image:url(${spriteMesa()})` }),
    h('span', { class: 'etiqueta' }, `${ag.nome} `, h('b', {}, `Lv ${lv}`)));
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    fichaAgente(ag.id);
  });
  return btn;
}

// Linhas tracejadas da Diretoria até as salas com missões em andamento
function desenharLinhas() {
  const camada = $('linhas');
  const wrap = $('plantaWrap');
  if (!estado || $('vistaEscritorio').hidden) return camada.replaceChildren();
  const base = wrap.getBoundingClientRect();
  camada.setAttribute('viewBox', `0 0 ${base.width} ${base.height}`);
  const rel = (el) => {
    const r = el.getBoundingClientRect();
    return { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
  };
  const dirEl = wrap.querySelector('[data-sala="dir"]');
  if (!dirEl) return camada.replaceChildren();
  const d = rel(dirEl);

  const alvos = [];
  wrap.querySelectorAll('.sala').forEach((el) => {
    const agId = el.dataset.agente;
    if (!agId || el.dataset.sala === 'dir') return;
    const minhas = missoesDe(agId);
    const tipos = [];
    if (minhas.some((m) => m.status === 'rodando' || m.status === 'refazer')) tipos.push('rodando');
    if (minhas.some((m) => m.status === 'aguardando')) tipos.push('aguardando');
    tipos.forEach((tipo, i) => alvos.push({ r: rel(el), tipo, desvio: tipos.length > 1 ? (i ? 8 : -8) : 0 }));
  });

  const gap = parseFloat(getComputedStyle($('planta')).rowGap) || 18;
  const n = alvos.length;
  const partes = alvos.flatMap((a, i) => {
    const sx = Math.round(d.x + d.w / 2 + (i - (n - 1) / 2) * 12);
    const sy = Math.round(d.y + d.h);
    const tx = Math.round(a.r.x + a.r.w / 2 + a.desvio);
    const ty = Math.round(a.r.y);
    const my = Math.round(sy + gap / 2 + ((i % 3) - 1) * 4);
    return [
      svg('path', { class: `linha ${a.tipo}`, d: `M${sx} ${sy} V${my} H${tx} V${ty}` }),
      svg('rect', { class: `ponta ${a.tipo}`, x: tx - 5, y: ty - 5, width: 10, height: 10 }),
    ];
  });
  camada.replaceChildren(...partes);
}

// ---------- Fila de aprovação ----------
function renderFila(forcar) {
  const lista = $('fila');
  const ativo = document.activeElement;
  if (!forcar && ativo && ativo.tagName === 'TEXTAREA' && lista.contains(ativo)) {
    filaPendente = true; // não atrapalha quem está digitando; atualiza no próximo ciclo
    return;
  }
  filaPendente = false;
  const fila = (estado.missoes || []).filter((m) => m.status === 'aguardando');
  $('qtdFila').textContent = fila.length;
  for (const id of [...refazerAberto]) if (!fila.some((m) => m.id === id)) refazerAberto.delete(id);
  lista.replaceChildren(...(fila.length ? fila.map(cartao) : [h('p', { class: 'vazio' }, 'Nada esperando por você agora.')]));
}

function cartao(m) {
  const aviso = h('div', { class: 'aviso', role: 'status' });
  const aberto = refazerAberto.has(m.id);
  const bAprovar = h('button', { class: 'btn aprovar', type: 'button' }, 'Aprovar');
  const bRefazer = h('button', { class: 'btn refazer', type: 'button', 'aria-expanded': String(aberto) }, 'Refazer');
  bAprovar.addEventListener('click', () => decidir(m.id, 'aprovar', '', [bAprovar, bRefazer], aviso));
  bRefazer.addEventListener('click', () => {
    if (aberto) refazerAberto.delete(m.id);
    else refazerAberto.add(m.id);
    renderFila(true);
    const campo = $('coment-' + m.id);
    if (campo) campo.focus();
  });
  return h('article', { class: 'card' },
    h('h3', {}, m.titulo, m.exemplo ? h('span', { class: 'tag-exemplo' }, 'EXEMPLO') : null),
    h('div', { class: 'meta' }, nomeAgente(m.agente), ' · ', h('span', { class: 'xp' }, `+${m.xp} XP`), ' · ', m.data),
    m.resumo ? h('p', {}, m.resumo) : null,
    m.arquivo
      ? h('p', { class: 'caminho' }, h('button', { class: 'link', type: 'button', onclick: () => fichaArquivo(m.id) }, m.arquivo))
      : h('p', { class: 'meta' }, 'Sem arquivo .md'),
    h('div', { class: 'botoes' }, bAprovar, bRefazer),
    aberto ? caixaRefazer(m, aviso, [bAprovar, bRefazer]) : null,
    aviso);
}

function caixaRefazer(m, aviso, outrosBotoes) {
  const campo = h('textarea', { id: 'coment-' + m.id, placeholder: 'Ex.: deixe mais curto e cite o horário de funcionamento' });
  campo.value = rascunhos[m.id] || '';
  campo.addEventListener('input', () => { rascunhos[m.id] = campo.value; });
  const enviar = h('button', { class: 'btn refazer', type: 'button' }, 'Enviar para refazer');
  const cancelar = h('button', { class: 'btn neutro', type: 'button' }, 'Cancelar');
  enviar.addEventListener('click', () => {
    const comentario = campo.value.trim();
    if (!comentario) {
      aviso.textContent = 'Escreva o que o agente deve mudar.';
      campo.focus();
      return;
    }
    decidir(m.id, 'refazer', comentario, [enviar, cancelar, ...outrosBotoes], aviso);
  });
  cancelar.addEventListener('click', () => {
    refazerAberto.delete(m.id);
    renderFila(true);
  });
  return h('div', { class: 'caixa-refazer' },
    h('label', { for: campo.id }, 'O que o agente deve mudar?'), campo,
    h('div', { class: 'botoes' }, enviar, cancelar));
}

async function decidir(id, acao, comentario, botoes, aviso) {
  botoes.forEach((b) => { b.disabled = true; });
  aviso.textContent = '';
  try {
    const r = await fetch('/api/decisao', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, acao, comentario }),
    });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || r.statusText);
    refazerAberto.delete(id);
    delete rascunhos[id];
    aplicar(dados, true);
  } catch (e) {
    aviso.textContent = e.message;
    botoes.forEach((b) => { b.disabled = false; });
  }
}

// ---------- Automação (Claude chamado pelo servidor) e pedidos ----------
function renderAutomacao() {
  const a = estado._automacao || {};
  const caixa = $('cClaudeBox');
  let classe = 'parado';
  let texto = 'parado';
  if (!a.ativa) { classe = 'desligado'; texto = 'desligado'; }
  else if (a.rodando) { classe = 'trabalhando'; texto = 'trabalhando'; }
  else if (a.ultima && !a.ultima.ok) { classe = 'erro'; texto = 'erro'; }
  caixa.className = `contador claude ${classe}`;
  $('cClaude').textContent = texto;
  caixa.title = a.rodando ? `Desde ${a.inicio}: ${a.motivo}` : (a.ultima ? `Última rodada: ${a.ultima.fim} (${a.ultima.motivo})` : '');

  const aviso = $('automacaoAviso');
  if (a.ativa && !a.rodando && a.ultima && !a.ultima.ok) {
    const botao = h('button', { class: 'btn neutro', type: 'button' }, 'Tentar de novo');
    botao.addEventListener('click', () => rodarAgora(botao));
    aviso.replaceChildren(h('div', { class: 'alerta-auto' },
      h('p', {}, `A última rodada do Claude deu erro: ${a.ultima.erro}`),
      h('p', { class: 'comentario' }, `Detalhes em ${a.ultima.log}`),
      h('div', { class: 'botoes' }, botao)));
  } else if (a.rodando) {
    aviso.replaceChildren(h('div', { class: 'alerta-auto info' },
      `O Claude (${a.modelo}, esforço ${a.esforco}) está trabalhando desde ${a.inicio}: ${a.motivo}. As entregas aparecem na fila quando ficarem prontas.`));
  } else {
    aviso.replaceChildren();
  }
}

const ROTULO_PEDIDO = { novo: 'na fila', feito: 'virou plano' };

function renderPedidos() {
  const pedidos = (estado.pedidos || []).slice(-5).reverse();
  $('pedidos').replaceChildren(...(pedidos.length
    ? pedidos.map((p) => h('div', { class: 'pedido' },
        h('div', { class: 'topo-pedido' },
          h('span', {}, `${p.id} · ${p.projetoNome || p.projeto} · ${p.data}`),
          h('span', { class: `estado-pedido ${p.status}` }, `${ROTULO_PEDIDO[p.status] || p.status}${p.missao ? ' ' + p.missao : ''}`)),
        h('div', { class: 'texto', title: p.texto }, p.texto)))
    : [h('p', { class: 'vazio' }, 'Nenhum pedido ainda. Use o botão "+ Nova missão" no topo.')]));

  const nomes = new Set();
  (estado.projetos || []).forEach((p) => nomes.add(p.nome || p.id));
  (estado.pedidos || []).forEach((p) => nomes.add(p.projetoNome || p.projeto));
  $('listaProjetos').replaceChildren(...[...nomes].filter(Boolean).map((n) => h('option', { value: n })));
}

async function rodarAgora(botao) {
  botao.disabled = true;
  try {
    const r = await fetch('/api/rodada', { method: 'POST' });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || r.statusText);
    if (dados.aviso) mostrarErro(dados.aviso);
    delete dados.aviso;
    aplicar(dados, false);
  } catch (e) {
    mostrarErro(e.message);
    botao.disabled = false;
  }
}

function abrirNovaMissao() {
  $('mAviso').textContent = '';
  $('mEnviar').disabled = false;
  $('dlgMissao').showModal();
  ($('mProjeto').value ? $('mTexto') : $('mProjeto')).focus();
}

async function enviarNovaMissao(e) {
  e.preventDefault();
  const projeto = $('mProjeto').value.trim();
  const texto = $('mTexto').value.trim();
  if (!projeto) { $('mAviso').textContent = 'Diga para qual projeto é a missão.'; $('mProjeto').focus(); return; }
  if (texto.length < 5) { $('mAviso').textContent = 'Descreva o que você quer.'; $('mTexto').focus(); return; }
  $('mEnviar').disabled = true;
  try {
    const r = await fetch('/api/pedido', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projeto, texto }),
    });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || r.statusText);
    $('mTexto').value = '';
    $('dlgMissao').close();
    aplicar(dados, false);
  } catch (err) {
    $('mAviso').textContent = err.message;
    $('mEnviar').disabled = false;
  }
}

// ---------- Aba Missões ----------
function renderMissoes() {
  const missoes = estado.missoes || [];
  const opcoes = [['', 'Todas'], ...STATUS.map((s) => [s, s])];
  $('filtros').replaceChildren(...opcoes.map(([valor, rotulo]) => {
    const qtd = valor ? missoes.filter((m) => m.status === valor).length : missoes.length;
    return h('button', {
      class: 'filtro', type: 'button', 'aria-pressed': String(filtroStatus === valor),
      onclick: () => { filtroStatus = valor; renderMissoes(); },
    }, `${rotulo} (${qtd})`);
  }));
  const linhas = missoes.filter((m) => !filtroStatus || m.status === filtroStatus).slice().reverse();
  $('tabelaMissoes').replaceChildren(...(linhas.length
    ? linhas.map((m) => h('tr', {},
        h('td', { class: 'mono' }, m.id),
        h('td', {}, m.titulo, m.exemplo ? h('span', { class: 'tag-exemplo' }, 'EXEMPLO') : null,
          m.comentario ? h('div', { class: 'comentario' }, 'Seu comentário: ' + m.comentario) : null),
        h('td', {}, nomeAgente(m.agente)),
        h('td', {}, m.projeto || '-'),
        h('td', {}, h('span', { class: 'st ' + m.status }, m.status)),
        h('td', { class: 'mono' }, String(m.xp)),
        h('td', { class: 'mono' }, m.data || '-'),
        h('td', {}, m.arquivo ? h('button', { class: 'link', type: 'button', onclick: () => fichaArquivo(m.id) }, m.arquivo) : '-')))
    : [h('tr', {}, h('td', { colspan: '8', class: 'comentario' }, 'Nenhuma missão com esse filtro.'))]));
}

// ---------- Fichas ----------
function mostrarFicha(topo, corpo) {
  $('fichaTopo').replaceChildren(...topo);
  $('fichaCorpo').replaceChildren(...corpo);
  if (!$('ficha').open) $('ficha').showModal();
}

function itemEntrega(m) {
  return h('li', {},
    h('span', { class: 'st ' + m.status }, m.status),
    h('button', { class: 'link', type: 'button', onclick: () => fichaArquivo(m.id) }, `${m.id} · ${m.titulo}`),
    h('span', { class: 'data' }, m.data || ''));
}

function fichaAgente(id) {
  const ag = (estado.agentes || []).find((a) => a.id === id);
  if (!ag) return;
  fichaAtual = { tipo: 'agente', id };
  const minhas = missoesDe(id);
  const xp = xpDe(minhas);
  const sit = situacao(minhas);
  const atual = minhas.find((m) => (sit === 'rodando' ? m.status === 'rodando' || m.status === 'refazer' : m.status === 'aguardando'));
  const entregas = minhas.filter((m) => m.arquivo).sort((a, b) => String(b.data).localeCompare(String(a.data))).slice(0, 5);
  mostrarFicha(
    [
      h('span', { class: 'boneco grande', style: `background-image:url(${spriteAgente(id)})` }),
      h('div', {},
        h('h2', { id: 'fichaTitulo' }, ag.nome),
        h('div', { class: 'sub' }, `Sala ${ag.sala || ag.area} · Lv ${nivelDe(xp)} · ${xp} XP`),
        h('div', { class: 'nivel-barra' }, h('i', { style: `width:${xp % 100}%` }))),
    ],
    [
      h('h3', {}, 'Papel'),
      h('p', {}, ag.papel || 'Sem descrição de papel no estado.json.'),
      ag.origem ? h('p', { class: 'origem' }, 'Base no ECC: ' + ag.origem.replace(/^ECC\s+/, '')) : null,
      h('h3', {}, 'Agora'),
      h('p', {}, atual ? `${ROTULO_SITUACAO[sit]}: ${atual.id} · ${atual.titulo}` : 'Livre para uma missão.'),
      h('h3', {}, 'Entregas recentes'),
      entregas.length ? h('ul', { class: 'entregas' }, ...entregas.map(itemEntrega)) : h('p', { class: 'origem' }, 'Ainda não entregou nada.'),
    ]);
}

function fichaMemoria() {
  fichaAtual = { tipo: 'memoria' };
  const projetos = estado.projetos || [];
  const aprovadas = (estado.missoes || []).filter((m) => m.status === 'aprovado')
    .sort((a, b) => String(b.data).localeCompare(String(a.data))).slice(0, 8);
  mostrarFicha(
    [
      h('span', { class: 'estante', style: `background-image:url(${spriteEstante()})` }),
      h('div', {},
        h('h2', { id: 'fichaTitulo' }, 'Memória'),
        h('div', { class: 'sub' }, 'Briefings dos projetos e tudo o que você já aprovou')),
    ],
    [
      h('h3', {}, `Projetos (${projetos.length})`),
      projetos.length
        ? h('ul', { class: 'entregas' }, ...projetos.map((p) => h('li', {}, p.nome || p.id, h('span', { class: 'data' }, p.briefing || `projetos/${p.id}.md`))))
        : h('p', { class: 'origem' }, 'Nenhum projeto ainda. O primeiro briefing nasce quando você der uma missão ao Diretor.'),
      h('h3', {}, 'Aprovadas recentemente'),
      aprovadas.length ? h('ul', { class: 'entregas' }, ...aprovadas.map(itemEntrega)) : h('p', { class: 'origem' }, 'Nada aprovado ainda.'),
    ]);
}

async function fichaArquivo(id) {
  const m = (estado.missoes || []).find((x) => x.id === id);
  if (!m) return;
  fichaAtual = { tipo: 'arquivo', id };
  const pre = h('pre', {}, 'carregando…');
  mostrarFicha(
    [h('div', {},
      h('h2', { id: 'fichaTitulo' }, `${m.id} · ${m.titulo}`),
      h('div', { class: 'sub' }, `${nomeAgente(m.agente)} · ${m.status} · ${m.arquivo}`))],
    [pre]);
  try {
    const r = await fetch('/api/arquivo?id=' + encodeURIComponent(id), { cache: 'no-store' });
    pre.textContent = await r.text();
  } catch (e) {
    pre.textContent = 'Não foi possível abrir o arquivo: ' + e.message;
  }
}

// ---------- Abas, erros e atualização automática ----------
function trocarAba(aba) {
  document.querySelectorAll('.aba').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.aba === aba)));
  $('vistaEscritorio').hidden = aba !== 'escritorio';
  $('vistaMissoes').hidden = aba !== 'missoes';
  requestAnimationFrame(desenharLinhas);
}

function mostrarErro(msg) {
  $('erro').textContent = msg || '';
  $('erro').hidden = !msg;
}

async function carregar() {
  try {
    const r = await fetch('/api/estado', { cache: 'no-store' });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || r.statusText);
    mostrarErro('');
    if (JSON.stringify(dados) === ultimoJson) {
      if (filaPendente) renderFila(false);
      return;
    }
    aplicar(dados, false);
  } catch (e) {
    mostrarErro(`Não consegui ler o estado.json (${e.message}). Confira se o "node server.js" está rodando.`);
  }
}

async function ciclo() {
  await carregar();
  setTimeout(ciclo, INTERVALO_MS);
}

document.querySelectorAll('.aba').forEach((b) => b.addEventListener('click', () => trocarAba(b.dataset.aba)));
$('fecharFicha').addEventListener('click', () => $('ficha').close());
$('bNovaMissao').addEventListener('click', abrirNovaMissao);
$('mCancelar').addEventListener('click', () => $('dlgMissao').close());
$('formMissao').addEventListener('submit', enviarNovaMissao);
$('ficha').addEventListener('close', () => { fichaAtual = null; });
$('avatarDono').style.backgroundImage = `url(${spriteDono()})`;
new ResizeObserver(() => desenharLinhas()).observe($('plantaWrap'));
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => desenharLinhas());
ciclo();
