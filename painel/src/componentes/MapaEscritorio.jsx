import { useEffect, useMemo, useRef, useState } from 'react';
import { PISOS, missoesDe, nivelDe, situacao, ROTULO_SITUACAO, xpDe } from '../dados.js';
import { salasDoEstado, alturaMapa, fluxosDoEstado, LARGURA_MAPA } from '../mapa.js';
import { spriteAgente, spriteDono, spriteMesa, spritePlanta, spriteEstante, spriteTrofeu, spriteQuadro, spriteGlobo, spriteCavalete, spriteRingLight, spriteGrafico, spriteRack, spriteMural, spriteMesaReuniao, spriteBalcao } from '../sprites.js';

const CORES = { chegada: '#87bad3', rodando: '#dfbc6c', aguardando: '#d989ad', git: '#b2a0df' };

// Arte própria, com os sprites do projeto. O canvas desenha; os botões HTML cuidam do acesso.
function desenharMapa(ctx, salas, estado, imagens, tempo, fase, selecionado, festas, reduzido) {
  const altura = alturaMapa(salas);
  const ret = (x, y, w, h, cor) => { ctx.fillStyle = cor; ctx.fillRect(Math.round(x), Math.round(y), w, h); };
  const imagem = (chave, x, y, w, h, frame) => {
    const img = imagens[chave];
    if (!img?.complete || !img.naturalWidth) return;
    if (frame !== undefined) ctx.drawImage(img, frame * 36, 0, 36, 48, Math.round(x), Math.round(y), w, h);
    else ctx.drawImage(img, Math.round(x), Math.round(y), w, h);
  };
  ctx.imageSmoothingEnabled = false;
  ret(0, 0, LARGURA_MAPA, altura, '#151e28');
  for (let y = 0; y < altura; y += 8) for (let x = 0; x < LARGURA_MAPA; x += 8) {
    ret(x, y, 8, 8, ((x + y) / 8) % 2 ? '#1b2632' : '#1e2a37');
  }
  const janela = (x, y, w) => {
    ret(x, y, w, 17, '#526779');
    ret(x + 2, y + 2, w - 4, 13, fase.astro === 'lua' ? '#233d59' : '#8dbacb');
    ret(x + w / 2, y + 1, 2, 15, '#526779');
    ret(x + 1, y + 16, w + 2, 2, '#b6c0bb');
    if (fase.astro === 'lua') ret(x + 9, y + 4, 3, 3, '#ecd6a4');
  };
  for (const s of salas) {
    const cor = PISOS[s.piso]?.[1] || '#729b96';
    const { x, y, w } = s;
    ret(x + 2, y + 2, w - 4, 132, '#273039');
    for (let ty = 34; ty < 134; ty += 10) for (let tx = 3; tx < w - 4; tx += 10) {
      ret(x + tx, y + ty, Math.min(10, w - tx - 3), 10, ((tx + ty) % 20) ? '#2b363d' : '#303d43');
    }
    ret(x + 2, y + 2, w - 4, 30, '#35414a');
    ret(x + 2, y + 31, w - 4, 3, cor);
    ret(x, y, w, 2, '#0e151d');
    ret(x, y, 3, 134, '#0e151d');
    ret(x + w - 3, y, 3, 134, '#0e151d');
    // Portas e corredor deixam o mapa parecer um escritório contínuo.
    ret(x + 3, y + 133, w / 2 - 19, 3, '#0e151d');
    ret(x + w / 2 + 16, y + 133, w / 2 - 19, 3, '#0e151d');
    ret(x + w / 2 - 16, y + 132, 32, 3, '#78836e');
    janela(x + w - 47, y + 9, 27);
    imagem('planta', x + 9, y + 105, 15, 24);
    if (w > 160) imagem('planta', x + w - 26, y + 105, 15, 24);
    const deco = { pesquisa: 'globo', estrategia: 'quadro', design: 'cavalete', copy: 'mural', social: 'ring', trafego: 'grafico', vendas: 'grafico', revisao: 'quadro', git: 'rack' }[s.deco];
    if (deco) imagem(deco, x + w - 40, y + 60, 25, 32);
    if (s.tipo === 'reuniao') {
      imagem('reuniao', x + 70, y + 62, 172, 54);
      imagem('quadro', x + 15, y + 8, 60, 20);
    }
    if (s.tipo === 'memoria') {
      for (let i = 0; i < 4; i++) imagem('estante', x + 36 + i * 59, y + 48, 40, 62);
    }
    if (s.tipo === 'recepcao') imagem('balcao', x + 32, y + 66, 86, 42);
    if (s.id === 'dir') {
      ret(x + 110, y + 43, 92, 83, '#654445');
      ret(x + 114, y + 47, 84, 75, '#744f4f');
      imagem('trofeu', x + 25, y + 8, 18, 22);
    }
    if (s.tipo === 'voce' || s.tipo === 'git') {
      imagem(s.tipo === 'voce' ? 'dono' : 'ag:git', x + w / 2 - 9, y + 66, 18, 24, 0);
      imagem('mesa', x + w / 2 - 24, y + 80, 48, 32);
    }
    s.agentes.forEach((id, i) => {
      const minhas = missoesDe(estado, id);
      const st = situacao(minhas);
      const colunas = Math.min(3, s.agentes.length);
      const linhas = Math.ceil(s.agentes.length / colunas);
      const cx = x + (w / (colunas + 1)) * (i % colunas + 1);
      const cy = y + 65 + Math.floor(i / colunas) * Math.min(40, 70 / linhas);
      const oscilacao = reduzido ? 0 : Math.sin(tempo * 1.2 + i) * (st === 'livre' ? 5 : 0);
      const frame = festas[id] ? 5 : st === 'rodando' ? 1 + Math.floor(tempo * 4) % 2 : Math.floor(tempo + i) % 7 === 0 ? 3 : 0;
      if (id === selecionado) {
        ret(cx - 27, cy + 31, 54, 2, '#e9c67c');
        ret(cx - 27, cy - 6, 2, 39, '#e9c67c');
        ret(cx + 25, cy - 6, 2, 39, '#e9c67c');
      }
      imagem(`ag:${id}`, cx - 9 + oscilacao, cy - 2, 18, 24, frame);
      imagem('mesa', cx - 24, cy + 12, 48, 30);
      ret(cx - 8, cy + 17, 16, 6, st === 'rodando' ? '#719da9' : '#263a48');
      ret(cx + 26, cy + 2, 4, 4, st === 'rodando' ? CORES.rodando : st === 'aguardando' ? CORES.aguardando : '#89ad91');
      if (festas[id]) {
        for (let k = 0; k < 6; k++) ret(cx + Math.sin(k * 2 + tempo * 2) * 25, cy - 7 - (k * 9 + tempo * 15) % 24, 2, 2, k % 2 ? '#e9c67c' : '#a9cfb3');
      }
    });
  }
  // Copa decorativa ocupa o espaço livre da primeira fileira.
  ret(803, 2, 154, 132, '#3b3734');
  ret(803, 2, 154, 30, '#46413b');
  ret(803, 31, 154, 3, '#967b59');
  ret(818, 52, 61, 22, '#916a4b');
  ret(822, 45, 16, 13, '#d3d8cb');
  ret(844, 49, 12, 10, '#232c34');
  ret(862, 52, 5, 8, '#cabb9c');
  imagem('planta', 926, 99, 18, 30);
  ret(894, 77, 30, 24, '#886b4e');
  const porId = Object.fromEntries(salas.map((s) => [s.id, s]));
  for (const [i, p] of fluxosDoEstado(estado, salas).entries()) {
    const a = porId[p.de], b = porId[p.para];
    if (!a || !b) continue;
    const pontos = [[a.x + a.w / 2, a.y + 134], [a.x + a.w / 2, a.y + 145], [b.x + b.w / 2, a.y + 145], [b.x + b.w / 2, b.y + 145], [b.x + b.w / 2, b.y + 133]];
    ctx.strokeStyle = CORES[p.tipo]; ctx.lineWidth = 2; ctx.setLineDash([4, 5]); ctx.lineDashOffset = reduzido ? 0 : -tempo * 12 - i * 3;
    ctx.beginPath(); pontos.forEach(([x, y], j) => j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
    ctx.setLineDash([]);
  }
}

export default function MapaEscritorio({ estado, fase, festas, reduzido, selecionado, onAgente, onMemoria, onPedidos, onVoce, onGit }) {
  const canvas = useRef(null);
  const [pausado, setPausado] = useState(false);
  const salas = useMemo(() => salasDoEstado(estado), [estado.agentes]);
  const altura = alturaMapa(salas);
  const semMovimento = reduzido || pausado;
  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return undefined;
    let vivo = true, frame, ultimo = 0;
    const imagens = {};
    const fontes = { planta: spritePlanta(), mesa: spriteMesa(), dono: spriteDono(), estante: spriteEstante(), trofeu: spriteTrofeu(), quadro: spriteQuadro(), globo: spriteGlobo(), cavalete: spriteCavalete(), ring: spriteRingLight(), grafico: spriteGrafico(), rack: spriteRack(), mural: spriteMural(), reuniao: spriteMesaReuniao(), balcao: spriteBalcao(), 'ag:git': spriteAgente('git') };
    for (const a of estado.agentes || []) fontes[`ag:${a.id}`] = spriteAgente(a.id);
    const pintar = (t = 0) => desenharMapa(ctx, salas, estado, imagens, semMovimento ? 0 : t / 1000, fase, selecionado, festas, semMovimento);
    Object.entries(fontes).forEach(([chave, src]) => {
      const img = new Image(); imagens[chave] = img;
      img.onload = () => { if (vivo) pintar(); };
      img.src = src;
    });
    const animar = (t) => {
      if (!vivo) return;
      if (!document.hidden && t - ultimo >= 65) { pintar(t); ultimo = t; }
      if (!semMovimento) frame = requestAnimationFrame(animar);
    };
    pintar();
    if (!semMovimento) frame = requestAnimationFrame(animar);
    return () => { vivo = false; cancelAnimationFrame(frame); Object.values(imagens).forEach((img) => { img.onload = null; }); };
  }, [salas, estado, fase.id, festas, selecionado, semMovimento]);
  const abrirSala = (s) => {
    if (s.tipo === 'memoria') return onMemoria();
    if (['recepcao', 'reuniao'].includes(s.tipo)) return onPedidos();
    if (s.tipo === 'voce') return onVoce();
    if (s.tipo === 'git') return onGit();
    if (s.agentes[0]) onAgente(s.agentes[0]);
  };
  return (
    <section className="mapa-escritorio" aria-labelledby="mapa-titulo">
      <div className="mapa-cabecalho">
        <div><span className="sobretitulo">SEU TIME, EM UM SÓ LUGAR</span><h2 id="mapa-titulo">Dentro do escritório</h2></div>
        <button className="controle-movimento" type="button" aria-pressed={pausado} disabled={reduzido} onClick={() => setPausado(!pausado)}>{reduzido ? 'Movimento reduzido' : pausado ? 'Retomar animação' : 'Pausar animação'}</button>
      </div>
      <div className="mapa-rolagem">
        <div className="mapa-palco" style={{ aspectRatio: `${LARGURA_MAPA} / ${altura}` }}>
          <canvas ref={canvas} width={LARGURA_MAPA} height={altura} aria-hidden="true" />
          <div className="mapa-salas">
            {salas.map((s) => (
              <div className="mapa-sala" key={s.id} data-sala={s.id} style={{ left: `${s.x / 9.6}%`, top: `${s.y / altura * 100}%`, width: `${s.w / 9.6}%`, height: `${s.h / altura * 100}%` }}>
                <button className="mapa-placa" type="button" onClick={() => abrirSala(s)} disabled={!s.tipo && !s.agentes.length}>{s.nome}</button>
                {s.agentes.map((id, i) => {
                  const a = estado.agentes.find((ag) => ag.id === id);
                  const ms = missoesDe(estado, id), st = situacao(ms), colunas = Math.min(3, s.agentes.length);
                  return <button type="button" key={id} className={`mapa-agente ${st}${id === selecionado ? ' selecionado' : ''}`} style={{ left: `${100 / (colunas + 1) * (i % colunas + 1)}%`, top: `${(65 + Math.floor(i / colunas) * Math.min(40, 70 / Math.ceil(s.agentes.length / colunas))) / s.h * 100}%` }} aria-pressed={id === selecionado} aria-label={`${a.nome}, nível ${nivelDe(xpDe(ms))}, ${ROTULO_SITUACAO[st]}. Ver ficha`} onClick={() => onAgente(id)}><span>{a.nome} <b>Lv {nivelDe(xpDe(ms))}</b></span></button>;
                })}
                {s.tipo && <button className="mapa-sala-acao" type="button" aria-label={`Abrir ${s.nome}`} onClick={() => abrirSala(s)} />}
              </div>
            ))}
            <span className="mapa-copa" style={{ height: `${160 / altura * 100}%` }}>Copa</span>
          </div>
        </div>
      </div>
      <div className="mapa-legenda"><span><i className="livre" />Livre</span><span><i className="rodando" />Trabalhando</span><span><i className="aguardando" />Aguardando você</span><span className="mapa-dica">Selecione um agente para ver a ficha.</span></div>
      <div className="atalhos-escritorio"><button onClick={onPedidos} type="button">Recepção e pedidos</button><button onClick={onMemoria} type="button">Memória do projeto</button><button onClick={onGit} type="button">Git & GitHub</button></div>
    </section>
  );
}
