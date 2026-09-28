import { useEffect, useState } from 'react';
import Dialogo from './Dialogo.jsx';
import Markdown from './Markdown.jsx';
import Anexos from './Anexos.jsx';
import { api } from '../api.js';
import {
  COMO_TRABALHA, ROTULO_SITUACAO, maisRecentes, missoesDe, nivelDe, nomeAgente, situacao, xpDe,
} from '../dados.js';
import { spriteAgente, spriteEstante } from '../sprites.js';

// Uma janela só para as fichas: agente, memória, pedidos, Git & GitHub e arquivo entregue.
export default function Ficha({ ficha, estado, onFechar, onArquivo, onLigarGit, onEnviarGit }) {
  let conteudo = null;
  if (ficha && ficha.tipo === 'agente') conteudo = <FichaAgente id={ficha.id} estado={estado} onArquivo={onArquivo} />;
  if (ficha && ficha.tipo === 'memoria') conteudo = <FichaMemoria estado={estado} onArquivo={onArquivo} />;
  if (ficha && ficha.tipo === 'arquivo') conteudo = <FichaArquivo id={ficha.id} estado={estado} />;
  if (ficha && ficha.tipo === 'pedidos') conteudo = <FichaPedidos estado={estado} onArquivo={onArquivo} />;
  if (ficha && ficha.tipo === 'git') conteudo = <FichaGit estado={estado} onLigar={onLigarGit} onEnviar={onEnviarGit} />;
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

const ROTULO_PEDIDO = { novo: 'na fila', feito: 'virou plano' };

function FichaPedidos({ estado, onArquivo }) {
  const pedidos = (estado.pedidos || []).slice().reverse();
  const missoes = estado.missoes || [];
  return (
    <>
      <div className="ficha-topo">
        <div>
          <h2 id="fichaTitulo">Pedidos e reuniões</h2>
          <div className="sub">Tudo o que você pediu ao Diretor, do mais novo para o mais antigo</div>
        </div>
      </div>
      <div className="ficha-corpo">
        {pedidos.length ? (
          <ul className="entregas">
            {pedidos.map((p) => {
              const plano = missoes.find((m) => m.id === p.missao);
              return (
                <li key={p.id} className="pedido-item">
                  <span className={`estado-pedido ${p.status}`}>{ROTULO_PEDIDO[p.status] || p.status}</span>
                  <b>{p.id} · {p.projetoNome || p.projeto}</b>
                  <span className="data">{p.data}</span>
                  <p>{p.texto}</p>
                  <Anexos anexos={p.anexos} grande />
                  {plano && plano.arquivo && (
                    <button className="link" type="button" onClick={() => onArquivo(plano.id)}>Ver o plano {plano.id} ({plano.status})</button>
                  )}
                </li>
              );
            })}
          </ul>
        ) : <p className="origem">Nenhum pedido ainda. Use o botão "+ Nova missão" no topo.</p>}
      </div>
    </>
  );
}

// Git & GitHub: o botão de ligar (envio automático) e o "Enviar agora". No painel online não há o que ligar:
// cada pedido e decisão já vira um commit no GitHub.
function FichaGit({ estado, onLigar, onEnviar }) {
  const g = estado._git || {};
  const auto = estado._automacao || {};
  const nuvem = g.modo === 'nuvem';
  const [ocupado, setOcupado] = useState('');
  const [aviso, setAviso] = useState('');
  const falta = (g.pendentes || 0) + (g.adiante || 0);

  async function fazer(tipo, acao) {
    setOcupado(tipo);
    setAviso('');
    try {
      await acao();
    } catch (e) {
      setAviso(e.message);
    } finally {
      setOcupado('');
    }
  }

  let motivoBloqueio = '';
  if (!g.disponivel) motivoBloqueio = g.motivo;
  else if (g.enviando) motivoBloqueio = 'Enviando agora…';
  else if (auto.rodando) motivoBloqueio = 'A equipe está trabalhando: dá para enviar quando a rodada terminar.';
  else if (!falta) motivoBloqueio = 'Nada novo para enviar: o GitHub já tem tudo desta pasta.';

  return (
    <>
      <div className="ficha-topo">
        <span className="boneco grande" style={{ backgroundImage: `url(${spriteAgente('git')})` }} />
        <div>
          <h2 id="fichaTitulo">Git &amp; GitHub</h2>
          <div className="sub">Guarda o trabalho do escritório no GitHub{g.remoto ? ` · ${g.remoto}` : ''}{g.ramo ? ` (${g.ramo})` : ''}</div>
        </div>
      </div>
      <div className="ficha-corpo ficha-git">
        {nuvem ? (
          <>
            <h3>No painel online</h3>
            <p>Aqui não há nada para ligar: cada pedido, anexo e decisão já vira um commit no GitHub na hora, e a equipe da nuvem
              salva tudo no fim de cada rodada. O botão de ligar e o "Enviar agora" ficam no painel do PC.</p>
          </>
        ) : (
          <>
            <h3>Envio automático</h3>
            <button
              type="button"
              role="switch"
              aria-checked={Boolean(g.ligado)}
              className={`interruptor${g.ligado ? ' ligado' : ''}`}
              disabled={Boolean(ocupado) || (!g.disponivel && !g.ligado)}
              onClick={() => fazer('ligar', () => onLigar(!g.ligado))}
            >
              <span className="trilho" aria-hidden="true"><span className="pino" /></span>
              <span>{g.ligado ? 'Ligado' : 'Desligado'}</span>
            </button>
            <p className="comentario">
              {g.ligado
                ? 'Depois de cada rodada da equipe e de cada decisão sua, o que mudou nesta pasta vai sozinho para o GitHub.'
                : 'Nada sai deste PC até você clicar em "Enviar agora" (ou ligar o envio automático).'}
            </p>

            {!g.disponivel && <p className="aviso">Não dá para enviar: {g.motivo}</p>}

            <h3>Esperando envio</h3>
            {g.pendentes ? (
              <ul className="arquivos-git">
                {(g.arquivos || []).map((a) => <li key={a}>{a}</li>)}
                {g.pendentes > (g.arquivos || []).length && <li className="comentario">e mais {g.pendentes - g.arquivos.length} arquivo(s)</li>}
              </ul>
            ) : <p className="comentario">{g.disponivel ? 'Nenhum arquivo mudou desde o último envio.' : '-'}</p>}
            {g.adiante > 0 && <p className="comentario">{g.adiante} commit(s) feitos no PC ainda não estão no GitHub.</p>}

            <h3>Último envio</h3>
            {g.ultimo ? (
              <p className={g.ultimo.ok ? '' : 'aviso'}>
                {g.ultimo.data} · {g.ultimo.ok ? g.ultimo.resumo : `Erro: ${g.ultimo.erro}`}
                {g.ultimo.commit && <span className="comentario"> (commit {g.ultimo.commit})</span>}
              </p>
            ) : <p className="comentario">Nenhum envio desde que o painel foi aberto.</p>}

            <div className="botoes">
              <button
                className="btn enviar-git"
                type="button"
                disabled={Boolean(ocupado) || Boolean(motivoBloqueio)}
                onClick={() => fazer('enviar', onEnviar)}
              >
                {ocupado === 'enviar' || g.enviando ? 'Enviando…' : `Enviar agora${falta ? ` (${g.pendentes || g.adiante})` : ''}`}
              </button>
            </div>
            {motivoBloqueio && g.disponivel && <p className="comentario">{motivoBloqueio}</p>}
            {aviso && <div className="aviso" role="status">{aviso}</div>}
          </>
        )}
        <h3>Como trabalha</h3>
        <ol className="passos">{(COMO_TRABALHA.git || []).map((p) => <li key={p}>{p}</li>)}</ol>
        <p className="origem">Vai tudo o que mudou na pasta: entregas, anexos e o estado.json. Se o repositório for público,
          qualquer pessoa vê; deixe-o privado se houver dados de clientes.</p>
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
