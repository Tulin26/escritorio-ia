import { useEffect, useState } from 'react';
import Dialogo from './Dialogo.jsx';
import Markdown from './Markdown.jsx';
import { api } from '../api.js';
import {
  COMO_TRABALHA, ROTULO_SITUACAO, maisRecentes, missoesDe, nivelDe, nomeAgente, situacao, xpDe,
} from '../dados.js';
import { spriteAgente, spriteEstante } from '../sprites.js';

// Uma janela só para as três fichas: agente, memória e arquivo entregue.
export default function Ficha({ ficha, estado, onFechar, onArquivo }) {
  let conteudo = null;
  if (ficha && ficha.tipo === 'agente') conteudo = <FichaAgente id={ficha.id} estado={estado} onArquivo={onArquivo} />;
  if (ficha && ficha.tipo === 'memoria') conteudo = <FichaMemoria estado={estado} onArquivo={onArquivo} />;
  if (ficha && ficha.tipo === 'arquivo') conteudo = <FichaArquivo id={ficha.id} estado={estado} />;
  return (
    <Dialogo aberto={Boolean(conteudo)} onFechar={onFechar} rotulo="fichaTitulo" className={ficha && ficha.tipo === 'arquivo' ? 'larga' : ''}>
      {conteudo}
      <div className="ficha-rodape"><button className="btn neutro" type="button" onClick={onFechar}>Fechar</button></div>
    </Dialogo>
  );
}

function ItemEntrega({ m, onArquivo }) {
  return (
    <li>
      <span className={`st ${m.status}`}>{m.status}</span>
      <button className="link" type="button" onClick={() => onArquivo(m.id)}>{m.id} · {m.titulo}</button>
      <span className="data">{m.data || ''}</span>
    </li>
  );
}

function FichaAgente({ id, estado, onArquivo }) {
  const ag = (estado.agentes || []).find((a) => a.id === id);
  if (!ag) return <div className="ficha-corpo"><p>Agente não encontrado.</p></div>;
  const minhas = missoesDe(estado, id);
  const xp = xpDe(minhas);
  const sit = situacao(minhas);
  const atual = minhas.find((m) => (sit === 'rodando' ? m.status === 'rodando' || m.status === 'refazer' : m.status === 'aguardando'));
  const entregas = minhas.filter((m) => m.arquivo).sort(maisRecentes).slice(0, 5);
  const passos = COMO_TRABALHA[id];
  return (
    <>
      <div className="ficha-topo">
        <span className="boneco grande" style={{ backgroundImage: `url(${spriteAgente(id)})` }} />
        <div>
          <h2 id="fichaTitulo">{ag.nome}</h2>
          <div className="sub">Sala {ag.sala || ag.area} · Lv {nivelDe(xp)} · {xp} XP</div>
          <div className="nivel-barra"><i style={{ transform: `scaleX(${(xp % 100) / 100})` }} /></div>
        </div>
      </div>
      <div className="ficha-corpo">
        <h3>Papel</h3>
        <p>{ag.papel || 'Sem descrição de papel no estado.json.'}</p>
        {passos && (
          <>
            <h3>Como trabalha</h3>
            <ol className="passos">{passos.map((p) => <li key={p}>{p}</li>)}</ol>
          </>
        )}
        <h3>Agora</h3>
        <p>{atual ? `${ROTULO_SITUACAO[sit]}: ${atual.id} · ${atual.titulo}` : 'Livre para uma missão.'}</p>
        <h3>Entregas recentes</h3>
        {entregas.length
          ? <ul className="entregas">{entregas.map((m) => <ItemEntrega key={m.id} m={m} onArquivo={onArquivo} />)}</ul>
          : <p className="origem">Ainda não entregou nada.</p>}
        {ag.origem && <p className="origem">Base no ECC: {ag.origem.replace(/^ECC\s+/, '')}</p>}
      </div>
    </>
  );
}

function FichaMemoria({ estado, onArquivo }) {
  const projetos = estado.projetos || [];
  const aprovadas = (estado.missoes || []).filter((m) => m.status === 'aprovado').sort(maisRecentes).slice(0, 8);
  return (
    <>
      <div className="ficha-topo">
        <span className="estante" style={{ backgroundImage: `url(${spriteEstante()})` }} />
        <div>
          <h2 id="fichaTitulo">Memória</h2>
          <div className="sub">Briefings dos projetos e tudo o que você já aprovou</div>
        </div>
      </div>
      <div className="ficha-corpo">
        <h3>Projetos ({projetos.length})</h3>
        {projetos.length
          ? <ul className="entregas">{projetos.map((p) => <li key={p.id}>{p.nome || p.id}<span className="data">{p.briefing || `projetos/${p.id}.md`}</span></li>)}</ul>
          : <p className="origem">Nenhum projeto ainda. O primeiro briefing nasce quando você der uma missão ao Diretor.</p>}
        <h3>Aprovadas recentemente</h3>
        {aprovadas.length
          ? <ul className="entregas">{aprovadas.map((m) => <ItemEntrega key={m.id} m={m} onArquivo={onArquivo} />)}</ul>
          : <p className="origem">Nada aprovado ainda.</p>}
      </div>
    </>
  );
}

function FichaArquivo({ id, estado }) {
  const m = (estado.missoes || []).find((x) => x.id === id);
  const [texto, setTexto] = useState(null);
  const [erro, setErro] = useState('');
  useEffect(() => {
    let vivo = true;
    api.arquivo(id)
      .then((t) => { if (vivo) setTexto(t); })
      .catch((e) => { if (vivo) setErro(`Não foi possível abrir o arquivo: ${e.message}`); });
    return () => { vivo = false; };
  }, [id]);
  if (!m) return <div className="ficha-corpo"><p>Missão não encontrada.</p></div>;
  return (
    <>
      <div className="ficha-topo">
        <div>
          <h2 id="fichaTitulo">{m.id} · {m.titulo}</h2>
          <div className="sub">{nomeAgente(estado, m.agente)} · {m.status} · {m.arquivo}</div>
        </div>
      </div>
      <div className="ficha-corpo">
        {erro && <p className="aviso">{erro}</p>}
        {!erro && texto === null && <p className="comentario">Carregando…</p>}
        {texto !== null && <Markdown texto={texto} />}
      </div>
    </>
  );
}
