import { useEffect, useRef, useState } from 'react';
import {
  SALAS, PISOS, VERBO, missoesDe, xpDe, nivelDe, situacao, ROTULO_SITUACAO,
} from '../dados.js';
import {
  spriteAgente, spriteMesa, spritePlanta, spriteEstante, spriteGlobo, spriteQuadro, spriteMural,
  spriteRingLight, spriteGrafico, spritePrancheta, spriteRack, spriteTrofeu, spriteEnvelope, spriteDono,
  spriteMesaReuniao, spriteCadeira, spriteBalcao, spriteCavalete, spriteCartela, spritePainelAds, spriteVisitante,
} from '../sprites.js';

const fundo = (url) => ({ backgroundImage: `url(${url})` });
const normalizar = (texto) => String(texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

// Confete da comemoração: deslocamento final (x, y) e cor de cada pedacinho.
const CONFETE = [
  [-34, -30, '#ffd23f'], [-22, -44, '#ff6fb5'], [-6, -52, '#5ad17a'], [10, -48, '#7cc4ff'], [26, -40, '#ffd23f'],
  [36, -24, '#ff6fb5'], [-40, -12, '#7cc4ff'], [42, -8, '#5ad17a'], [-16, -36, '#f2ecdc'], [18, -30, '#f2ecdc'],
];

// Quem senta em cada sala: os agentes fixos da sala, mais qualquer agente do estado.json cujo campo "sala" tenha o
// nome dela. Agente sem sala conhecida ganha uma sala só dele no fim da planta.
function montarSalas(estado) {
  const agentes = estado.agentes || [];
  const existe = (id) => agentes.some((a) => a.id === id);
  const usados = new Set();
  const salas = SALAS.map((s) => {
    if (!s.agentes) return s;
    const ids = s.agentes.filter(existe);
    agentes.forEach((a) => {
      if (!ids.includes(a.id) && !s.agentes.includes(a.id) && normalizar(a.sala) === normalizar(s.nome)) ids.push(a.id);
    });
    ids.forEach((id) => usados.add(id));
    return { ...s, agentes: ids };
  });
  const extras = agentes
    .filter((a) => !usados.has(a.id))
    .map((a) => ({ id: `x-${a.id}`, agentes: [a.id], nome: a.sala || a.nome, piso: 'turquesa', livre: true }));
  return [...salas, ...extras];
}

export default function Escritorio({ estado, fase, agora, festas, reduzido, onAgente, onMemoria, onPedidos, onVoce }) {
  const wrapRef = useRef(null);
  const salas = montarSalas(estado);
  const madrugada = agora.getHours() < 6;
  let indice = 0;

  return (
    <div className={`escritorio fase-${fase.id}`} style={{ '--escuro': fase.escuro, '--lampada': fase.lampada }}>
      <div className="legenda">
        <span><i className="traco chegada" />Pedido chegando</span>
        <span><i className="traco rodando" />Trabalho indo para a sala</span>
        <span><i className="traco aguardando" />Entrega indo para você</span>
      </div>
      <div className="planta-wrap" ref={wrapRef}>
        <div className="planta">
          {salas.map((sala) => {
            const primeiro = indice;
            indice += (sala.agentes || []).length;
            return (
              <Sala
                key={sala.id}
                sala={sala}
                primeiroIndice={primeiro}
                estado={estado}
                fase={fase}
                agora={agora}
                festas={festas}
                madrugada={madrugada}
                onAgente={onAgente}
                onMemoria={onMemoria}
                onPedidos={onPedidos}
                onVoce={onVoce}
              />
            );
          })}
        </div>
        <Linhas wrapRef={wrapRef} estado={estado} salas={salas} reduzido={reduzido} />
      </div>
    </div>
  );
}

function Sala({ sala, primeiroIndice, estado, fase, agora, festas, madrugada, onAgente, onMemoria, onPedidos, onVoce }) {
  const [c1, c2, borda, parede] = PISOS[sala.piso] || PISOS.turquesa;
  const agentes = (sala.agentes || []).map((id) => (estado.agentes || []).find((a) => a.id === id)).filter(Boolean);
  const abrir = () => {
    if (sala.tipo === 'memoria') return onMemoria();
    if (sala.tipo === 'recepcao' || sala.tipo === 'reuniao') return onPedidos();
    if (sala.tipo === 'voce') return onVoce();
    if (agentes[0]) return onAgente(agentes[0].id);
    return undefined;
  };
  return (
    <section
      className={`sala sala-${sala.id}${sala.tipo ? ` sala-${sala.tipo}` : ''}`}
      data-sala={sala.id}
      aria-label={`Sala ${sala.nome}`}
      style={{ gridArea: sala.livre ? undefined : sala.id, '--c1': c1, '--c2': c2, '--borda': borda, '--parede': parede }}
      onClick={abrir}
    >
      <Janela fase={fase} lado="e" />
      {sala.id === 'dir' && <Janela fase={fase} lado="d" />}
      <div className="placa">{sala.nome}</div>
      {sala.id === 'dir' && <div className="tapete" aria-hidden="true" />}
      <Decoracao tipo={sala.deco} estado={estado} agora={agora} />
      <span className="deco-planta e" aria-hidden="true" style={fundo(spritePlanta())} />
      <span className="deco-planta d" aria-hidden="true" style={fundo(spritePlanta())} />
      {sala.tipo === 'memoria' && <Memoria estado={estado} onAbrir={onMemoria} />}
      {sala.tipo === 'reuniao' && <Reuniao estado={estado} onAbrir={onPedidos} />}
      {sala.tipo === 'recepcao' && <Recepcao estado={estado} onAbrir={onPedidos} />}
      {sala.tipo === 'voce' && <Voce estado={estado} onAbrir={onVoce} />}
      {!sala.tipo && agentes.length > 0 && (
        <div className="postos">
          {agentes.map((ag, i) => (
            <Posto key={ag.id} ag={ag} indice={primeiroIndice + i} estado={estado} festa={festas[ag.id]} madrugada={madrugada} onAbrir={onAgente} />
          ))}
        </div>
      )}
      {!sala.tipo && agentes.length === 0 && <div className="mem-info">Sala vazia: nenhum agente no estado.json</div>}
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
    case 'design':
      return (
        <>
          <span className="deco parede cartela" aria-hidden="true" style={fundo(spriteCartela())} />
          <span className="deco chao cavalete" aria-hidden="true" style={fundo(spriteCavalete())} />
        </>
      );
    case 'copy':
      return (
        <>
          <span className="deco parede mural" aria-hidden="true" style={fundo(spriteMural())} />
          <span className="deco chao bolinhas" aria-hidden="true"><i /><i /><i /></span>
        </>
      );
    case 'social':
      return <span className="deco chao ring" aria-hidden="true" style={fundo(spriteRingLight())} />;
    case 'trafego':
      return <span className="deco parede painel-ads" aria-hidden="true" style={fundo(spritePainelAds())} />;
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
      <button type="button" className="mem-info" onClick={(e) => { e.stopPropagation(); onAbrir(); }}>
        {(estado.projetos || []).length} briefing(s)<br />{aprovadas} entrega(s) aprovada(s)
      </button>
    </>
  );
}

// Sala de Reunião: a pauta é o pedido mais recente; quando a equipe está trabalhando, quem está em missão senta à mesa.
function Reuniao({ estado, onAbrir }) {
  const auto = estado._automacao || {};
  const missoes = estado.missoes || [];
  const pedidos = estado.pedidos || [];
  const pauta = pedidos.find((p) => p.status === 'novo') || pedidos[pedidos.length - 1];
  const ativos = [...new Set(missoes.filter((m) => m.status === 'rodando' || m.status === 'refazer').map((m) => m.agente))];
  const emReuniao = auto.rodando || ativos.length > 0;
  const sentados = emReuniao ? ['diretor', ...ativos.filter((id) => id !== 'diretor')].slice(0, 4) : [];
  return (
    <>
      <div className="mesa-reuniao-area" aria-hidden="true">
        <div className="cadeiras">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className="lugar">
              {sentados[i]
                ? <span className="mini-agente" style={fundo(spriteAgente(sentados[i]))} />
                : <span className="cadeira" style={fundo(spriteCadeira())} />}
            </span>
          ))}
        </div>
        <span className="mesa-reuniao" style={fundo(spriteMesaReuniao())} />
      </div>
      <button type="button" className="mem-info pauta" onClick={(e) => { e.stopPropagation(); onAbrir(); }}>
        {emReuniao && <b className="ao-vivo">em reunião</b>}
        {pauta ? `Pauta: ${pauta.projetoNome || pauta.projeto}: ${pauta.texto}` : 'Sem reunião agora'}
      </button>
    </>
  );
}

// Recepção: cada pedido novo é uma pessoa esperando no balcão até o Diretor atender.
function Recepcao({ estado, onAbrir }) {
  const fila = (estado.pedidos || []).filter((p) => p.status === 'novo');
  return (
    <>
      <div className="recepcao-area" aria-hidden="true">
        <div className="fila-visitantes">
          {fila.slice(0, 3).map((p, i) => <span key={p.id} className="visitante" style={fundo(spriteVisitante(i))} />)}
        </div>
        <span className="balcao" style={fundo(spriteBalcao())}><span className="sino no-balcao" /></span>
      </div>
      <button type="button" className="mem-info" onClick={(e) => { e.stopPropagation(); onAbrir(); }}>
        {fila.length ? `${fila.length} pedido(s) na fila` : 'Ninguém na fila'}
        {fila.length > 3 && <><br />+{fila.length - 3} esperando lá fora</>}
      </button>
    </>
  );
}

// Sua sala: a pilha de envelopes é o que está esperando a sua aprovação.
function Voce({ estado, onAbrir }) {
  const esperando = (estado.missoes || []).filter((m) => m.status === 'aguardando').length;
  return (
    <div className="postos">
      <button type="button" className="agente ocioso dono-posto" aria-label={`Você: ${esperando} entrega(s) esperando aprovação`} onClick={(e) => { e.stopPropagation(); onAbrir(); }}>
        {esperando > 0 && (
          <span className="pilha" aria-hidden="true">
            {Array.from({ length: Math.min(esperando, 5) }, (_, i) => <i key={i} style={{ ...fundo(spriteEnvelope('aguardando')), bottom: `${i * 4}px` }} />)}
          </span>
        )}
        <span className="luz" aria-hidden="true" />
        <span className="boneco dono" style={fundo(spriteDono())} />
        <span className="mesa" style={fundo(spriteMesa())} />
        <span className="etiqueta">Você <b>Dono</b></span>
        <span className={`tarefa ${esperando ? 'aguardando' : 'livre'}`}>{esperando ? `${esperando} esperando você` : 'mesa limpa'}</span>
      </button>
    </div>
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
      {trabalhando && atual && (
        <span className="balao" aria-hidden="true">{VERBO[ag.id] || 'Trabalhando'} {atual.id}<i /><i /><i /></span>
      )}
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
      {sit === 'aguardando' && atual && <span className="tarefa aguardando">entregou! · {atual.id}</span>}
      {festa && (
        <span className="festa" key={festa.chave} aria-hidden="true">
          <span className="mais-xp">+{festa.xp} XP</span>
          {CONFETE.map(([dx, dy, cor], i) => <i key={i} style={{ '--dx': `${dx}px`, '--dy': `${dy}px`, background: cor }} />)}
        </span>
      )}
    </button>
  );
}

// Caminho em ângulos retos entre duas salas, passando pelos corredores entre elas (sem cruzar salas no meio).
function rota(a, b, gap, desvio) {
  const ax = Math.round(a.x + a.w / 2 + desvio);
  const bx = Math.round(b.x + b.w / 2 + desvio);
  const dy = desvio / 2;
  const colunaDoAlvo = (y1, y2) => {
    const gx = Math.round((b.x >= a.x ? b.x - gap / 2 : b.x + b.w + gap / 2) + desvio / 2);
    return [[gx, y1], [gx, y2], [bx, y2]];
  };
  if (b.y >= a.y + a.h - 1) {
    const y1 = Math.round(a.y + a.h + gap / 2 + dy);
    const y2 = Math.round(b.y - gap / 2 + dy);
    const meio = Math.abs(y2 - y1) < 4 ? [[bx, y1]] : colunaDoAlvo(y1, y2);
    return [[ax, a.y + a.h], [ax, y1], ...meio, [bx, b.y]];
  }
  if (b.y + b.h <= a.y + 1) {
    const y1 = Math.round(a.y - gap / 2 + dy);
    const y2 = Math.round(b.y + b.h + gap / 2 + dy);
    const meio = Math.abs(y2 - y1) < 4 ? [[bx, y1]] : colunaDoAlvo(y1, y2);
    return [[ax, a.y], [ax, y1], ...meio, [bx, b.y + b.h]];
  }
  const y1 = Math.round(Math.max(a.y + a.h, b.y + b.h) + gap / 2 + dy);
  return [[ax, a.y + a.h], [ax, y1], [bx, y1], [bx, b.y + b.h]];
}

// Linhas tracejadas com um envelope andando: pedido da Recepção para a Diretoria, trabalho da Diretoria para a sala
// e entrega da sala para você.
function Linhas({ wrapRef, estado, salas, reduzido }) {
  const [desenho, setDesenho] = useState({ largura: 0, altura: 0, itens: [] });
  const estadoRef = useRef(estado);
  estadoRef.current = estado;
  const salaDe = {};
  salas.forEach((s) => (s.agentes || []).forEach((id) => { salaDe[id] = s.id; }));
  const salaDeRef = useRef(salaDe);
  salaDeRef.current = salaDe;
  const assinatura = [
    ...(estado.missoes || []).map((m) => `${m.agente}:${m.status}`),
    ...(estado.pedidos || []).map((p) => p.status),
    Object.entries(salaDe).join(','),
  ].join('|');

  // useEffect (e não useLayoutEffect): só aqui o ref da planta, que é do componente pai, já está preenchido.
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return undefined;
    const medir = () => {
      const base = wrap.getBoundingClientRect();
      const caixa = (id) => {
        const el = wrap.querySelector(`[data-sala="${id}"]`);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
      };
      const atual = estadoRef.current;
      const pares = [];
      if ((atual.pedidos || []).some((p) => p.status === 'novo')) pares.push({ de: 'rec', para: 'dir', tipo: 'chegada' });
      const vistos = new Set();
      (atual.missoes || []).forEach((m) => {
        const sala = salaDeRef.current[m.agente];
        if (!sala) return;
        let par = null;
        if ((m.status === 'rodando' || m.status === 'refazer') && sala !== 'dir') par = { de: 'dir', para: sala, tipo: 'rodando' };
        if (m.status === 'aguardando') par = { de: sala, para: 'voc', tipo: 'aguardando' };
        if (par && !vistos.has(`${par.de}>${par.para}`)) {
          vistos.add(`${par.de}>${par.para}`);
          pares.push(par);
        }
      });
      const gap = parseFloat(getComputedStyle(wrap.querySelector('.planta')).rowGap) || 18;
      const itens = pares.map((p, i) => {
        const a = caixa(p.de);
        const b = caixa(p.para);
        if (!a || !b) return null;
        const pontos = rota(a, b, gap, ((i % 5) - 2) * 4);
        const comprimento = pontos.slice(1).reduce((t, [x, y], k) => t + Math.abs(x - pontos[k][0]) + Math.abs(y - pontos[k][1]), 0);
        const [tx, ty] = pontos[pontos.length - 1];
        return {
          chave: `${p.de}>${p.para}`, tipo: p.tipo, tx, ty,
          d: `M${pontos.map(([x, y]) => `${x} ${y}`).join(' L')}`,
          dur: Math.max(1.6, comprimento / 90).toFixed(2),
        };
      }).filter(Boolean);
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
        <g key={`${it.chave}-${it.d}`}>
          <path className={`linha ${it.tipo}`} d={it.d} />
          <rect className={`ponta ${it.tipo}`} x={it.tx - 5} y={it.ty - 5} width={10} height={10} />
          {!reduzido && (
            <image className="envelope" href={spriteEnvelope(it.tipo)} width={16} height={12} x={-8} y={-6}>
              <animateMotion dur={`${it.dur}s`} repeatCount="indefinite" path={it.d} />
            </image>
          )}
        </g>
      ))}
    </svg>
  );
}
