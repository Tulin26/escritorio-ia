import { useState } from 'react';
import Dialogo from './Dialogo.jsx';

export default function NovaMissao({ aberto, estado, nuvem, onFechar, onEnviar }) {
  return (
    <Dialogo aberto={aberto} onFechar={onFechar} rotulo="dlgMissaoTitulo">
      <Formulario estado={estado} nuvem={nuvem} onFechar={onFechar} onEnviar={onEnviar} />
    </Dialogo>
  );
}

function Formulario({ estado, nuvem, onFechar, onEnviar }) {
  const [projeto, setProjeto] = useState('');
  const [texto, setTexto] = useState('');
  const [chamar, setChamar] = useState(true);
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const nomes = new Set();
  (estado.projetos || []).forEach((p) => nomes.add(p.nome || p.id));
  (estado.pedidos || []).forEach((p) => nomes.add(p.projetoNome || p.projeto));

  async function enviar(e) {
    e.preventDefault();
    if (!projeto.trim()) return setAviso('Diga para qual projeto é a missão.');
    if (texto.trim().length < 5) return setAviso('Descreva o que você quer.');
    setOcupado(true);
    setAviso('');
    try {
      await onEnviar(projeto.trim(), texto.trim(), nuvem && chamar);
      onFechar();
    } catch (err) {
      setAviso(err.message);
      setOcupado(false);
    }
  }

  return (
    <form onSubmit={enviar} noValidate>
      <div className="ficha-topo">
        <div>
          <h2 id="dlgMissaoTitulo">Nova missão</h2>
          <div className="sub">O Diretor recebe, divide o trabalho e manda o plano para a sua aprovação.</div>
        </div>
      </div>
      <div className="ficha-corpo form-missao">
        <label htmlFor="mProjeto">Projeto</label>
        <input id="mProjeto" list="listaProjetos" autoComplete="off" autoFocus placeholder="Ex.: Canto do Cupim" value={projeto} onChange={(e) => setProjeto(e.target.value)} />
        <datalist id="listaProjetos">{[...nomes].filter(Boolean).map((n) => <option key={n} value={n} />)}</datalist>
        <label htmlFor="mTexto">O que você quer?</label>
        <textarea
          id="mTexto"
          rows={6}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Ex.: Quero aumentar os pedidos pelo WhatsApp em 30 dias. É um restaurante em [cidade], público de trabalhadores da região, sem verba para anúncios."
        />
        <p className="dica">Quanto mais detalhe (cidade, público, prazo, verba), melhor o plano. Se faltar algo, o Diretor pergunta no próprio plano.</p>
        {nuvem && (
          <label className="marcar">
            <input type="checkbox" checked={chamar} onChange={(e) => setChamar(e.target.checked)} />
            Chamar a equipe agora
          </label>
        )}
        {aviso && <div className="aviso" role="status">{aviso}</div>}
      </div>
      <div className="ficha-rodape botoes-fim">
        <button type="button" className="btn neutro" onClick={onFechar}>Cancelar</button>
        <button type="submit" className="btn aprovar" disabled={ocupado}>{ocupado ? 'Enviando…' : 'Enviar ao Diretor'}</button>
      </div>
    </form>
  );
}
