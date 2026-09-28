import { useState } from 'react';
import { nomeAgente } from '../dados.js';
import { spriteDono } from '../sprites.js';

export default function Lado({ estado, onDecidir, onChamar, onArquivo }) {
  const fila = (estado.missoes || []).filter((m) => m.status === 'aguardando');
  return (
    <aside className="lado" aria-labelledby="donoTitulo">
      <div className="dono">
        <span className="avatar" role="img" aria-label="Seu avatar" style={{ backgroundImage: `url(${spriteDono()})` }} />
        <div>
          <h2 id="donoTitulo">Você – Dono do negócio</h2>
          <span className="selo">Aprova cada passo</span>
        </div>
      </div>
      <p className="regra">Nenhum agente gasta verba, publica ou envia mensagem sem o seu ok.</p>

      <Equipe auto={estado._automacao || {}} onChamar={onChamar} />

      <h2 className="fila-titulo">Sua mesa: aguardando aprovação ({fila.length})</h2>
      {fila.length
        ? fila.map((m, i) => <Cartao key={m.id} missao={m} ordem={i} estado={estado} onDecidir={onDecidir} onArquivo={onArquivo} />)
        : <p className="vazio">Nada esperando por você agora.</p>}

      <Pedidos estado={estado} />
    </aside>
  );
}

function Equipe({ auto, onChamar }) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const nuvem = auto.modo === 'nuvem';
  const pendentes = auto.pendentes || 0;

  async function chamar() {
    setOcupado(true);
    setErro('');
    try {
      await onChamar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setOcupado(false);
    }
  }

  let texto;
  if (!auto.ativa) {
    texto = nuvem
      ? 'A rotina do Claude ainda não foi configurada no Vercel (veja o README).'
      : 'A automação está desligada (ESCRITORIO_AUTOMACAO=0).';
  } else if (auto.rodando) {
    texto = `Trabalhando desde ${auto.inicio}. As entregas aparecem na sua mesa quando ficarem prontas.`;
  } else if (auto.ultima && !auto.ultima.ok) {
    texto = `A última rodada deu erro: ${auto.ultima.erro}`;
  } else if (pendentes) {
    texto = `${pendentes} item(ns) esperando a equipe.`;
  } else {
    texto = auto.ultima && auto.ultima.resumo ? `Última rodada: ${auto.ultima.resumo}` : 'Nada esperando a equipe.';
  }

  const podeChamar = auto.ativa && !auto.rodando && pendentes > 0;
  return (
    <section className={`caixa-equipe${auto.rodando ? ' ativa' : ''}${auto.ultima && !auto.ultima.ok && !auto.rodando ? ' com-erro' : ''}`}>
      <h2 className="fila-titulo equipe-titulo">Equipe {nuvem ? 'na nuvem' : 'no PC'}</h2>
      <p>{texto}</p>
      {!auto.rodando && auto.ultima && !auto.ultima.ok && auto.ultima.log && <p className="comentario">Detalhes em {auto.ultima.log}</p>}
      {auto.sessao && (auto.rodando || (auto.ultima && !auto.ultima.ok)) && (
        <p><a className="link" href={auto.sessao} target="_blank" rel="noopener noreferrer">Acompanhar a rodada no claude.ai</a></p>
      )}
      {podeChamar && (
        <div className="botoes">
          <button className="btn chamar" type="button" disabled={ocupado} onClick={chamar}>
            {ocupado ? 'Chamando…' : `${nuvem ? 'Chamar a equipe' : 'Rodar agora'} (${pendentes})`}
          </button>
        </div>
      )}
      {erro && <div className="aviso" role="status">{erro}</div>}
    </section>
  );
}

function Cartao({ missao: m, ordem, estado, onDecidir, onArquivo }) {
  const [refazer, setRefazer] = useState(false);
  const [comentario, setComentario] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState('');

  async function decidir(acao) {
    if (acao === 'refazer' && !comentario.trim()) {
      setAviso('Escreva o que o agente deve mudar.');
      return;
    }
    setOcupado(true);
    setAviso('');
    try {
      await onDecidir(m.id, acao, acao === 'refazer' ? comentario.trim() : '');
    } catch (e) {
      setAviso(e.message);
      setOcupado(false);
    }
  }

  const idCampo = `coment-${m.id}`;
  return (
    <article className="card" style={{ animationDelay: `${Math.min(ordem, 6) * 50}ms` }}>
      <h3>{m.titulo}{m.exemplo && <span className="tag-exemplo">EXEMPLO</span>}</h3>
      <div className="meta">{nomeAgente(estado, m.agente)} · <span className="xp">+{m.xp} XP</span> · {m.data}</div>
      {m.resumo && <p className="resumo">{m.resumo}</p>}
      {m.arquivo
        ? <p className="caminho"><button className="link" type="button" onClick={() => onArquivo(m.id)}>Ler a entrega ({m.arquivo})</button></p>
        : <p className="meta">Sem arquivo .md</p>}
      <div className="botoes">
        <button className="btn aprovar" type="button" disabled={ocupado} onClick={() => decidir('aprovar')}>Aprovar</button>
        <button className="btn refazer" type="button" disabled={ocupado} aria-expanded={refazer} onClick={() => setRefazer(!refazer)}>Refazer</button>
      </div>
      {refazer && (
        <div className="caixa-refazer">
          <label htmlFor={idCampo}>O que o agente deve mudar?</label>
          <textarea
            id={idCampo}
            autoFocus
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="Ex.: deixe mais curto e cite o horário de funcionamento"
          />
          <div className="botoes">
            <button className="btn refazer" type="button" disabled={ocupado} onClick={() => decidir('refazer')}>Enviar para refazer</button>
            <button className="btn neutro" type="button" onClick={() => setRefazer(false)}>Cancelar</button>
          </div>
        </div>
      )}
      {aviso && <div className="aviso" role="status">{aviso}</div>}
    </article>
  );
}

const ROTULO_PEDIDO = { novo: 'na fila', feito: 'virou plano' };

function Pedidos({ estado }) {
  const pedidos = (estado.pedidos || []).slice(-5).reverse();
  return (
    <>
      <h2 className="fila-titulo pedidos-titulo">Seus pedidos</h2>
      {pedidos.length
        ? pedidos.map((p) => (
          <div className="pedido" key={p.id}>
            <div className="topo-pedido">
              <span>{p.id} · {p.projetoNome || p.projeto} · {p.data}</span>
              <span className={`estado-pedido ${p.status}`}>{ROTULO_PEDIDO[p.status] || p.status}{p.missao ? ` ${p.missao}` : ''}</span>
            </div>
            <div className="texto" title={p.texto}>{p.texto}</div>
          </div>
        ))
        : <p className="vazio">Nenhum pedido ainda. Use o botão "+ Nova missão" no topo.</p>}
    </>
  );
}
