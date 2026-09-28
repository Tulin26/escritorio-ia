import { useEffect, useRef, useState } from 'react';
import {
  SALAS, PISOS, missoesDe, xpDe, nivelDe, situacao, ROTULO_SITUACAO,
} from '../dados.js';
import {
  spriteAgente, spriteMesa, spritePlanta, spriteEstante, spriteGlobo, spriteQuadro, spriteMural,
  spriteRingLight, spriteGrafico, spritePrancheta, spriteRack, spriteTrofeu, spriteEnvelope,
} from '../sprites.js';

const fundo = (url) => ({ backgroundImage: `url(${url})` });

// Confete da comemoração: deslocamento final (x, y) e cor de cada pedacinho.
const CONFETE = [
  [-34, -30, '#ffd23f'], [-22, -44, '#ff6fb5'], [-6, -52, '#5ad17a'], [10, -48, '#7cc4ff'], [26, -40, '#ffd23f'],
  [36, -24, '#ff6fb5'], [-40, -12, '#7cc4ff'], [42, -8, '#5ad17a'], [-16, -36, '#f2ecdc'], [18, -30, '#f2ecdc'],
];

export default function Escritorio({ estado, fase, agora, festas, reduzido, onAgente, onMemoria }) {
  const wrapRef = useRef(null);
  const conhecidos = new Set(SALAS.map((s) => s.agente).filter(Boolean));
  const extras = (estado.agentes || [])
    .filter((a) => !conhecidos.has(a.id))
    .map((a) => ({ id: `x-${a.id}`, agente: a.id, nome: a.sala || a.nome, piso: 'turquesa', deco: null, livre: true }));
  const hora = agora.getHours();
  const madrugada = hora < 6;

  return (
    <div className={`escritorio fase-${fase.id}`} style={{ '--escuro': fase.escuro, '--lampada': fase.lampada }}>
      <div className="legenda">
        <span><i className="traco rodando" />Trabalho indo para a sala</span>
        <span><i className="traco aguardando" />Entrega esperando você</span>
      </div>
      <div className="planta-wrap" ref={wrapRef}>
        <div className="planta">
          {[...SALAS, ...extras].map((sala, i) => (
            <Sala
              key={sala.id}
              sala={sala}
              indice={i}
              estado={estado}
              fase={fase}
              agora={agora}
              festas={festas}
              madrugada={madrugada}
              onAgente={onAgente}
              onMemoria={onMemoria}
            />
          ))}
        </div>
        <Linhas wrapRef={wrapRef} estado={estado} reduzido={reduzido} />
      </div>
    </div>
  );
}

function Sala({ sala, indice, estado, fase, agora, festas, madrugada, onAgente, onMemoria }) {
  const [c1, c2, borda, parede] = PISOS[sala.piso] || PISOS.turquesa;
  const ag = sala.agente ? (estado.agentes || []).find((a) => a.id === sala.agente) : null;
  const nome = (ag && ag.sala) || sala.nome;
  const abrir = () => (sala.id === 'mem' ? onMemoria() : ag && onAgente(ag.id));
  return (
    <section
      className={`sala sala-${sala.id}`}
      data-sala={sala.id}
      data-agente={sala.agente || ''}
      aria-label={`Sala ${nome}`}
      style={{ gridArea: sala.livre ? undefined : sala.id, '--c1': c1, '--c2': c2, '--borda': borda, '--parede': parede }}
      onClick={abrir}
    >
      <Janela fase={fase} lado="e" />
      {sala.id === 'dir' && <Janela fase={fase} lado="d" />}
      <div className="placa">{nome}</div>
      {sala.id === 'dir' && <div className="tapete" aria-hidden="true" />}
      <Decoracao tipo={sala.deco} estado={estado} agora={agora} />
      <span className="deco-planta e" aria-hidden="true" style={fundo(spritePlanta())} />
      <span className="deco-planta d" aria-hidden="true" style={fundo(spritePlanta())} />
      {sala.id === 'mem' && <Memoria estado={estado} onAbrir={onMemoria} />}
      {sala.id !== 'mem' && ag && (
        <div className="postos">
          <Posto ag={ag} indice={indice} estado={estado} festa={festas[ag.id]} madrugada={madrugada} onAbrir={onAgente} />
        </div>
      )}
      {sala.id !== 'mem' && !ag && <div className="mem-info">Sala sem agente no estado.json</div>}
    </section>
  );
}

function Janela({ fase, lado }) {
  return (
    <span className={`janela ${lado}`} aria-hidden="true">
      <span className={`astro ${fase.astro}`} />
      {fase.id === 'dia' && <span className="nuvem" />}
      <span className="caixilho" />
    </span>
  );
}

function Decoracao({ tipo, estado, agora }) {
  switch (tipo) {
    case 'diretoria': {
      const nivel = Math.min(5, nivelDe(xpDe(estado.missoes || [])));
      const hh = String(agora.getHours()).padStart(2, '0');
      const mm = String(agora.getMinutes()).padStart(2, '0');
      return (
        <>
          <span className="trofeus" aria-hidden="true">
            {Array.from({ length: nivel }, (_, i) => <i key={i} style={fundo(spriteTrofeu())} />)}
          </span>
          <span className="relogio" aria-hidden="true">{hh}<b>:</b>{mm}</span>
        </>
      );
    }
    case 'pesquisa':
      return (
        <>
          <span className="deco parede estante-parede" aria-hidden="true" style={fundo(spriteEstante())} />
          <span className="deco chao globo" aria-hidden="true" style={fundo(spriteGlobo())} />
        </>
      );
    case 'estrategia':
      return <span className="deco parede quadro" aria-hidden="true" style={fundo(spriteQuadro())} />;
    case 'copy':
      return (
        <>
          <span className="deco parede mural" aria-hidden="true" style={fundo(spriteMural())} />
          <span className="deco chao bolinhas" aria-hidden="true"><i /><i /><i /></span>
        </>
      );
    case 'social':
      return <span className="deco chao ring" aria-hidden="true" style={fundo(spriteRingLight())} />;
    case 'vendas':
      return (
        <>
          <span className="deco parede grafico" aria-hidden="true" style={fundo(spriteGrafico())} />
          <span className="deco chao sino" aria-hidden="true" />
        </>
      );
    case 'revisao':
      return <span className="deco parede prancheta" aria-hidden="true" style={fundo(spritePrancheta())} />;
    default:
      return null;
  }
}

function Memoria({ estado, onAbrir }) {
  const aprovadas = (estado.missoes || []).filter((m) => m.status === 'aprovado').length;
  return (
    <>
      <div className="estantes" aria-hidden="true">
        {[0, 1, 2].map((i) => <span key={i} className="estante" style={fundo(spriteEstante())} />)}
        <span className="rack" style={fundo(spriteRack())}><i /><i /><i /><i /></span>
      </div>
      <button
        type="button"
        className="mem-info"
        onClick={(e) => { e.stopPropagation(); onAbrir(); }}
      >
        {(estado.projetos || []).length} briefing(s)<br />{aprovadas} entrega(s) aprovada(s)
      </button>
    </>
  );
}

function Posto({ ag, indice, estado, festa, madrugada, onAbrir }) {
  const minhas = missoesDe(estado, ag.id);
  const sit = situacao(minhas);
  const lv = nivelDe(xpDe(minhas));
  const trabalhando = sit === 'rodando';
  const dorme = madrugada && sit === 'livre' && !festa;
  const atual = minhas.find((m) => (trabalhando ? m.status === 'rodando' || m.status === 'refazer' : m.status === 'aguardando'));
  let modo = trabalhando ? 'digitando' : 'ocioso';
  if (dorme) modo = 'dormindo';
  if (festa) modo = 'comemorando';

  return (
    <button
      type="button"
      className={`agente ${modo}`}
      aria-label={`${ag.nome}, nível ${lv}, ${ROTULO_SITUACAO[sit]}. Abrir ficha`}
      onClick={(e) => { e.stopPropagation(); onAbrir(ag.id); }}
    >
      {trabalhando && <span className="balao" aria-hidden="true"><i /><i /><i /></span>}
      {sit === 'aguardando' && !festa && <span className="entregou" aria-hidden="true" style={fundo(spriteEnvelope('aguardando'))} />}
      {dorme && <span className="zzz" aria-hidden="true">z<b>z</b></span>}
      <span className="luz" aria-hidden="true" />
      {/* O atraso negativo espalha as piscadas e os cafés: cada agente tem o seu ritmo. */}
      <span className="boneco" style={{ ...fundo(spriteAgente(ag.id)), animationDelay: `${-(indice * 2.3)}s, ${-(indice * 0.7)}s` }} />
      <span className={`mesa${trabalhando ? ' ligada' : ''}`} style={fundo(spriteMesa())}>
        {trabalhando && <span className="tela" />}
        {!madrugada && <span className="vapor" aria-hidden="true"><i /><i /></span>}
      </span>
      <span className="etiqueta">{ag.nome} <b>Lv {lv}</b></span>
      {atual && <span className={`tarefa ${sit}`}>{trabalhando ? 'trabalhando' : 'entregou!'} · {atual.id}</span>}
      {festa && (
        <span className="festa" key={festa.chave} aria-hidden="true">
          <span className="mais-xp">+{festa.xp} XP</span>
          {CONFETE.map(([dx, dy, cor], i) => <i key={i} style={{ '--dx': `${dx}px`, '--dy': `${dy}px`, background: cor }} />)}
        </span>
      )}
    </button>
  );
}

// Linhas tracejadas da Diretoria até as salas com trabalho, com um envelope andando por elas.
function Linhas({ wrapRef, estado, reduzido }) {
  const [desenho, setDesenho] = useState({ largura: 0, altura: 0, itens: [] });
  const estadoRef = useRef(estado);
  estadoRef.current = estado;
  const assinatura = (estado.missoes || []).map((m) => `${m.agente}:${m.status}`).join('|');

  // useEffect (e não useLayoutEffect): só aqui o ref da planta, que é do componente pai, já está preenchido.
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return undefined;
    const medir = () => {
      const base = wrap.getBoundingClientRect();
      const rel = (el) => {
        const r = el.getBoundingClientRect();
        return { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
      };
      const dirEl = wrap.querySelector('[data-sala="dir"]');
      if (!dirEl) return setDesenho({ largura: base.width, altura: base.height, itens: [] });
      const d = rel(dirEl);
      const alvos = [];
      wrap.querySelectorAll('.sala').forEach((el) => {
        const agId = el.dataset.agente;
        if (!agId || el.dataset.sala === 'dir') return;
        const minhas = missoesDe(estadoRef.current, agId);
        const tipos = [];
        if (minhas.some((m) => m.status === 'rodando' || m.status === 'refazer')) tipos.push('rodando');
        if (minhas.some((m) => m.status === 'aguardando')) tipos.push('aguardando');
        tipos.forEach((tipo, i) => alvos.push({ r: rel(el), tipo, desvio: tipos.length > 1 ? (i ? 8 : -8) : 0 }));
      });
      const gap = parseFloat(getComputedStyle(wrap.querySelector('.planta')).rowGap) || 18;
      const n = alvos.length;
      const itens = alvos.map((a, i) => {
        const sx = Math.round(d.x + d.w / 2 + (i - (n - 1) / 2) * 12);
        const sy = Math.round(d.y + d.h);
        const tx = Math.round(a.r.x + a.r.w / 2 + a.desvio);
        const ty = Math.round(a.r.y);
        const my = Math.round(sy + gap / 2 + ((i % 3) - 1) * 4);
        // Sala mais abaixo: a linha desce pelo corredor à esquerda dela, sem cruzar as salas do meio.
        const pontos = [[sx, sy], [sx, my]];
        if (ty - sy > gap * 2) {
          const gx = Math.round(a.r.x - gap / 2 + (i % 2) * 3);
          const my2 = Math.round(ty - gap / 2);
          pontos.push([gx, my], [gx, my2], [tx, my2]);
        } else {
          pontos.push([tx, my]);
        }
        pontos.push([tx, ty]);
        const comprimento = pontos.slice(1).reduce((t, [x, y], k) => t + Math.abs(x - pontos[k][0]) + Math.abs(y - pontos[k][1]), 0);
        const caminho = `M${pontos.map(([x, y]) => `${x} ${y}`).join(' L')}`;
        return { tipo: a.tipo, tx, ty, d: caminho, dur: Math.max(1.6, comprimento / 90).toFixed(2) };
      });
      setDesenho({ largura: base.width, altura: base.height, itens });
    };
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(wrap);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(medir);
    return () => ro.disconnect();
  }, [wrapRef, assinatura]);

  const { largura, altura, itens } = desenho;
  return (
    <svg className="linhas" viewBox={`0 0 ${largura || 1} ${altura || 1}`} aria-hidden="true">
      {itens.map((it) => (
        <g key={`${it.d}-${it.tipo}`}>
          <path className={`linha ${it.tipo}`} d={it.d} />
          <rect className={`ponta ${it.tipo}`} x={it.tx - 5} y={it.ty - 5} width={10} height={10} />
          {!reduzido && (
            <image className="envelope" href={spriteEnvelope(it.tipo)} width={16} height={12} x={-8} y={-6}>
              <animateMotion
                dur={`${it.dur}s`}
                repeatCount="indefinite"
                path={it.d}
                keyPoints={it.tipo === 'aguardando' ? '1;0' : '0;1'}
                keyTimes="0;1"
                calcMode="linear"
              />
            </image>
          )}
        </g>
      ))}
    </svg>
  );
}
