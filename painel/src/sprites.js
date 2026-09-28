// Sprites em pixel art desenhados num canvas a partir de "mapas" de caracteres.
// Cada caractere é um pixel; a paleta diz a cor. O resultado é uma imagem (data URL) guardada em cache.
import { VISUAL, VISUAL_PADRAO } from './dados.js';

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

const cache = new Map();
function sprite(chave, gerar) {
  if (!cache.has(chave)) cache.set(chave, gerar());
  return cache.get(chave);
}

function escurecer(hex, fator) {
  const n = parseInt(hex.slice(1), 16);
  const canal = (d) => Math.round(((n >> d) & 255) * fator).toString(16).padStart(2, '0');
  return `#${canal(16)}${canal(8)}${canal(0)}`;
}

// ---------- Pessoas (12x16) ----------
// H cabelo, S pele, e pálpebra, E olho, m boca, C roupa, P calça, B sapato, u caneca
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
const trocar = (base, trocas) => base.map((linha, i) => trocas[i] || linha);

// Quadros da folha de cada agente (a ordem importa: o CSS anda de 36 em 36 px).
export const QUADRO = { parado: 0, digitaA: 1, digitaB: 2, pisca: 3, cafe: 4, comemora: 5 };
const QUADROS_AGENTE = [
  CORPO,
  trocar(CORPO, { 9: '.SCCCCCCCCC.', 10: '.CCCCCCCCCS.', 11: '.CCCCCCCCCC.' }),
  trocar(CORPO, { 9: '.CCCCCCCCCS.', 10: '.SCCCCCCCCC.', 11: '.CCCCCCCCCC.' }),
  trocar(CORPO, { 4: '..SSeSSeSS..' }),
  trocar(CORPO, {
    5: '..SSSSSSSSuu', 6: '...SSmmSSSuu', 7: '....SSSS..S.', 8: '..CCCCCCCCS.',
    9: '.CCCCCCCCCC.', 10: '.SCCCCCCCCC.', 11: '.SCCCCCCCCC.',
  }),
  trocar(CORPO, {
    2: 'S.HHHHHHHH.S', 3: 'C.HSSSSSSH.C', 4: 'C.SSESSESS.C', 5: 'C.SSSSSSSS.C',
    6: '.C.SmmmmS.C.', 7: '..C.SSSS.C..', 9: '..CCCCCCCC..', 10: '..CCCCCCCC..', 11: '..CCCCCCCC..',
  }),
];
const DONO = trocar(CORPO, { 8: '..CCWTTWCC..', 9: '.CCCWTTWCCC.', 10: '.SCCCTTCCCS.' });

function paletaPessoa(v) {
  return {
    H: v.cabelo, S: v.pele, e: escurecer(v.pele, 0.7), E: '#1a1420', m: '#b8505a', C: v.roupa,
    W: '#f2ecdc', T: '#d83a3a', P: '#2c2838', B: '#141018', u: '#f2ecdc',
  };
}
export const spriteAgente = (id) => sprite(`ag:${id}`, () => folhaSprites(QUADROS_AGENTE, paletaPessoa(VISUAL[id] || VISUAL_PADRAO), 3));

// Visitantes da Recepção (cada pedido na fila é uma pessoa esperando)
const VISITANTES = [
  { cabelo: '#6b3a1e', pele: '#e8b48c', roupa: '#3a7bd5' },
  { cabelo: '#111111', pele: '#8d5a32', roupa: '#d5a13a' },
  { cabelo: '#c9c9c9', pele: '#f1c29a', roupa: '#5a8f4e' },
];
export const spriteVisitante = (i) => sprite(`vis:${i % VISITANTES.length}`, () => folhaSprites(QUADROS_AGENTE, paletaPessoa(VISITANTES[i % VISITANTES.length]), 3));
export const spriteDono = () => sprite('dono', () => folhaSprites([DONO], paletaPessoa({ cabelo: '#3b2718', pele: '#d9a074', roupa: '#2a2f45' }), 4));

// ---------- Móveis e decoração ----------
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
export const spriteMesa = () => sprite('mesa', () => folhaSprites([MESA, MESA.map((l) => l.replace(/G/g, 'g'))], {
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
export const spritePlanta = () => sprite('planta', () => folhaSprites([PLANTA], { G: '#4caf50', g: '#2e7d32', P: '#b5651d', p: '#8a4b16' }, 3));

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
export const spriteEstante = () => sprite('estante', () => folhaSprites([ESTANTE], {
  F: '#6b4423', r: '#e04848', y: '#f2c14e', b: '#4d7fe0', g: '#4caf50', p: '#b05ed8', k: '#3b2414',
}, 3));

const GLOBO = [
  '...kkkk...',
  '..kbbggk..',
  '.kbggbbgk.',
  '.kbbbggbk.',
  '.kggbbbbk.',
  '..kbbggk..',
  '...kkkk...',
  '....ff....',
  '...ffff...',
  '..FFFFFF..',
];
export const spriteGlobo = () => sprite('globo', () => folhaSprites([GLOBO], {
  k: '#1b2a4a', b: '#4d7fe0', g: '#4caf50', f: '#8a5a2b', F: '#6b4423',
}, 3));

// Quadro branco com gráfico de barras (Estratégia)
const QUADRO_BRANCO = [
  'KKKKKKKKKKKKKKKKKK',
  'KWWWWWWWWWWWWWWWWK',
  'KWWWWWWWWWWrrWWWWK',
  'KWWWWWWWWWWrrWWWWK',
  'KWWWWWWbbWWrrWWWWK',
  'KWWWWWWbbWWrrWWWWK',
  'KWWggWWbbWWrrWWWWK',
  'KWWggWWbbWWrrWWWWK',
  'KWkkkkkkkkkkkkkkWK',
  'KKKKKKKKKKKKKKKKKK',
  '....K........K....',
  '...KK........KK...',
];
export const spriteQuadro = () => sprite('quadro', () => folhaSprites([QUADRO_BRANCO], {
  K: '#2b2f3a', W: '#eef2f7', r: '#e04848', b: '#4d7fe0', g: '#4caf50', k: '#8a93a6',
}, 3));

// Mural de cortiça com post-its (Copy)
const MURAL = [
  'FFFFFFFFFFFFFFFF',
  'FccYYYccccPPPccF',
  'FccYyYccccPpPccF',
  'FccYYYccccPPPccF',
  'FccccccGGGcccccF',
  'FcBBBccGgGcccccF',
  'FcBbBccGGGcccccF',
  'FcBBBcccccccWWcF',
  'FccccccccccWWWcF',
  'FFFFFFFFFFFFFFFF',
];
export const spriteMural = () => sprite('mural', () => folhaSprites([MURAL], {
  F: '#6b4423', c: '#c9975b', Y: '#f2c14e', y: '#d9a52f', P: '#ff8fc8', p: '#e06aa8',
  G: '#8ee07a', g: '#5fb84e', B: '#7cc4ff', b: '#4d9be0', W: '#f2ecdc',
}, 3));

// Ring light com celular no tripé (Social)
const RING_LIGHT = [
  '...LLLLLL...',
  '..L......L..',
  '.L..pppp..L.',
  '.L..pSSp..L.',
  '.L..pSSp..L.',
  '.L..pppp..L.',
  '..L......L..',
  '...LLLLLL...',
  '.....kk.....',
  '.....kk.....',
  '.....kk.....',
  '....k..k....',
  '...k....k...',
  '..k......k..',
];
export const spriteRingLight = () => sprite('ring', () => folhaSprites([RING_LIGHT], {
  L: '#fff6c9', p: '#1b1b24', S: '#7cc4ff', k: '#2c2838',
}, 3));

// Gráfico de vendas subindo (Vendas)
const GRAFICO = [
  'KKKKKKKKKKKKKKKK',
  'KWWWWWWWWWWWWWgK',
  'KWWWWWWWWWWWWgWK',
  'KWWWWWWWWWWWgWWK',
  'KWWWWWWWggWgWWWK',
  'KWWWWWWgWWgWWWWK',
  'KWWWggWWWWWWWWWK',
  'KWWgWWWWWWWWWWWK',
  'KWgWWWWWWWWWWWWK',
  'KKKKKKKKKKKKKKKK',
];
export const spriteGrafico = () => sprite('grafico', () => folhaSprites([GRAFICO], {
  K: '#2b2f3a', W: '#eef2f7', g: '#2fae5a',
}, 3));

// Prancheta com checklist (Revisão)
const PRANCHETA = [
  '....kkkk....',
  '.FFFkSSkFFF.',
  '.FWWWWWWWWF.',
  '.FWgWkkkkWF.',
  '.FWWWWWWWWF.',
  '.FWgWkkkkWF.',
  '.FWWWWWWWWF.',
  '.FWrWkkkkWF.',
  '.FWWWWWWWWF.',
  '.FWWWWWWWWF.',
  '.FFFFFFFFFF.',
];
export const spritePrancheta = () => sprite('prancheta', () => folhaSprites([PRANCHETA], {
  F: '#8a5a2b', W: '#f2ecdc', k: '#5b5f6e', S: '#c0c4d0', g: '#4caf50', r: '#e04848',
}, 3));

// Servidor (Memória): as luzes piscando são desenhadas no CSS
const RACK = [
  'KKKKKKKKKK',
  'KddddddddK',
  'KdkkkkkkdK',
  'KddddddddK',
  'KdkkkkkkdK',
  'KddddddddK',
  'KdkkkkkkdK',
  'KddddddddK',
  'KdkkkkkkdK',
  'KddddddddK',
  'KKKKKKKKKK',
];
export const spriteRack = () => sprite('rack', () => folhaSprites([RACK], { K: '#0f0d16', d: '#3a3f55', k: '#232738' }, 3));

const TROFEU = [
  'YYYYYY',
  'YyYYyY',
  '.YYYY.',
  '..YY..',
  '..YY..',
  '.BBBB.',
];
export const spriteTrofeu = () => sprite('trofeu', () => folhaSprites([TROFEU], { Y: '#f2c14e', y: '#fff1a8', B: '#6b4423' }, 3));

// Mesa comprida da Sala de Reunião e as cadeiras em volta
const MESA_REUNIAO = [
  '.KKKKKKKKKKKKKKKKKKKKKKKKKKKKKK.',
  'KLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLK',
  'KLllllllllllllllllllllllllllllLK',
  'KLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLK',
  '.KWWWWWWWWWWWWWWWWWWWWWWWWWWWWK.',
  '..DD........................DD..',
  '..DD........................DD..',
];
export const spriteMesaReuniao = () => sprite('mesa-reuniao', () => folhaSprites([MESA_REUNIAO], {
  K: '#0f0d16', L: '#c08a55', l: '#d9a56b', W: '#9a6a3e', D: '#5e3f22',
}, 3));

const CADEIRA = [
  '.kkkk.',
  '.kCCk.',
  '.kCCk.',
  'kkkkkk',
  'k....k',
];
export const spriteCadeira = () => sprite('cadeira', () => folhaSprites([CADEIRA], { k: '#2c2838', C: '#a3161f' }, 3));

// Balcão da Recepção
const BALCAO = [
  'KKKKKKKKKKKKKKKKKKKKKKKKKKKK',
  'KTTTTTTTTTTTTTTTTTTTTTTTTTTK',
  'KWWWWWWWWWWWWWWWWWWWWWWWWWWK',
  'KWwwwwwwwwwwwwwwwwwwwwwwwwWK',
  'KWWWWWWWWWWWWWWWWWWWWWWWWWWK',
  'KWwwwwwwwwwwwwwwwwwwwwwwwwWK',
  'KWWWWWWWWWWWWWWWWWWWWWWWWWWK',
  'KKKKKKKKKKKKKKKKKKKKKKKKKKKK',
];
export const spriteBalcao = () => sprite('balcao', () => folhaSprites([BALCAO], {
  K: '#0f0d16', T: '#e8d4b0', W: '#9a6a3e', w: '#7d5530',
}, 3));

// Cavalete com tela pintada (Marca & Design)
const CAVALETE = [
  '....kkkk....',
  '.kkkkkkkkkk.',
  '.kWWWWWWWWk.',
  '.kWrrWWbbWk.',
  '.kWrrWWbbWk.',
  '.kWWWyyWWWk.',
  '.kWWWyyWWWk.',
  '.kWggggggWk.',
  '.kkkkkkkkkk.',
  '...k....k...',
  '..k......k..',
  '.k........k.',
];
export const spriteCavalete = () => sprite('cavalete', () => folhaSprites([CAVALETE], {
  k: '#6b4423', W: '#f2ecdc', r: '#e04848', b: '#4d7fe0', y: '#f2c14e', g: '#4caf50',
}, 3));

// Cartela de cores na parede (Marca & Design)
const CARTELA = [
  'KKKKKKKKKKKKKKKK',
  'KrrKyyKggKbbKppK',
  'KrrKyyKggKbbKppK',
  'KrrKyyKggKbbKppK',
  'KKKKKKKKKKKKKKKK',
];
export const spriteCartela = () => sprite('cartela', () => folhaSprites([CARTELA], {
  K: '#1f1f2e', r: '#ff6f59', y: '#ffd23f', g: '#5ad17a', b: '#7cc4ff', p: '#ff6fb5',
}, 3));

// Painel de anúncios com a linha de resultado subindo (Tráfego & Mídia)
const PAINEL_ADS_MIOLO = [
  'dddddddddddddood',
  'dddddddddooooddd',
  'dddddooooddddddd',
  'dddooddddddddddd',
  'dooddddddddddddd',
  'dgdgdgdgdgdgdgdd',
  'dgdgdgdgdgdgdgdd',
];
const PAINEL_ADS = [
  'K'.repeat(18), ...PAINEL_ADS_MIOLO.map((l) => `K${l}K`), 'K'.repeat(18),
  '....K........K....',
  '...KK........KK...',
];
export const spritePainelAds = () => sprite('painel-ads', () => folhaSprites([PAINEL_ADS], {
  K: '#2b2f3a', d: '#141a2e', o: '#ff9f43', g: '#2fae5a',
}, 3));

// Envelope que anda pelas linhas: amarelo (trabalho indo para a sala) ou rosa (entrega voltando)
const ENVELOPE = [
  'kkkkkkkk',
  'kkWWWWkk',
  'kWkWWkWk',
  'kWWkkWWk',
  'kWWWWWWk',
  'kkkkkkkk',
];
const COR_ENVELOPE = { aguardando: '#ffc6e3', rodando: '#fff1b0', chegada: '#c6e6ff' };
export const spriteEnvelope = (tipo) => sprite(`env:${tipo}`, () => folhaSprites([ENVELOPE], {
  k: '#2a1830', W: COR_ENVELOPE[tipo] || COR_ENVELOPE.rodando,
}, 2));

// ---------- Sala Git & GitHub ----------
// Nuvem com a seta subindo (o trabalho indo para o GitHub), na parede
const NUVEM_ENVIO = [
  '.......WWWW.......',
  '.....WWWWWWWW.....',
  '....WWWWooWWWW....',
  '..WWWWWooooWWWWW..',
  '.WWWWWooooooWWWWW.',
  'WWWWWooooooooWWWWW',
  'WWWWWWWWooWWWWWWWW',
  'WWWWWWWWooWWWWWWWW',
  'wWWWWWWWooWWWWWWWw',
  '.wwwwwwwwwwwwwwww.',
];
export const spriteNuvemEnvio = () => sprite('nuvem-envio', () => folhaSprites([NUVEM_ENVIO], {
  W: '#eef2f7', w: '#b9c6d8', o: '#f05033',
}, 3));

// Caixa de papelão: anda pela linha Revisão → Git e empilha na sala enquanto espera o envio
const CAIXA = [
  '.kkkkkk.',
  'kTTttTTk',
  'kkkkkkkk',
  'kCCttCCk',
  'kCCttCCk',
  'kCCCCCCk',
  'kkkkkkkk',
];
const PALETA_CAIXA = { k: '#3a2412', T: '#e0a868', t: '#f2e2b8', C: '#c98b4a' };
export const spriteCaixa = () => sprite('caixa', () => folhaSprites([CAIXA], PALETA_CAIXA, 2));

// Caixinha na mão do visitante da Recepção: o pedido dele veio com anexos
const CAIXINHA = [
  'kkkkkkk',
  'kTTtTTk',
  'kCCtCCk',
  'kCCtCCk',
  'kkkkkkk',
];
export const spriteCaixinha = () => sprite('caixinha', () => folhaSprites([CAIXINHA], PALETA_CAIXA, 2));
