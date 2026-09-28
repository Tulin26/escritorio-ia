import { nivelDe, xpDe } from '../dados.js';

function statusEquipe(auto) {
  if (!auto.ativa) return ['desligado', auto.modo === 'nuvem' ? 'sem rotina' : 'desligada'];
  if (auto.rodando) return ['trabalhando', 'trabalhando'];
  if (auto.ultima && !auto.ultima.ok) return ['erro', 'erro'];
  return ['parado', 'parada'];
}

export default function Topo({ estado, agora, fase, aba, onAba, onNovaMissao, modo, onSair }) {
  const missoes = estado.missoes || [];
  const xp = xpDe(missoes);
  const auto = estado._automacao || {};
  const [classe, texto] = statusEquipe(auto);
  const hora = agora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const emAndamento = missoes.filter((m) => m.status === 'rodando' || m.status === 'refazer').length;
  const aguardando = missoes.filter((m) => m.status === 'aguardando').length;
  return (
    <header className="topo">
      <h1 className="logo">
        <span className="logo-icone" aria-hidden="true" />
        <span>
          Escritório de IA
          <small>
            Time de agentes · orquestrado pelo Diretor · {fase.nome}, {hora}
            {modo === 'nuvem' ? ' · online' : ' · no PC'}
          </small>
        </span>
      </h1>
      <div className="contadores">
        <div className="contador"><span>Agentes</span><b>{(estado.agentes || []).length}</b></div>
        <div className="contador"><span>Entregues</span><b>{missoes.filter((m) => m.status === 'aprovado').length}</b></div>
        <div className="contador"><span>XP</span><b>{xp}</b></div>
        <div className="contador"><span>Em andamento</span><b>{emAndamento}</b></div>
        <div className={`contador${aguardando ? ' chamando' : ''}`}><span>Aguardando você</span><b>{aguardando}</b></div>
        <div className="contador">
          <span>Nível</span><b>{nivelDe(xp)}</b>
          <div className="nivel-barra"><i style={{ transform: `scaleX(${(xp % 100) / 100})` }} /></div>
        </div>
        <div className={`contador equipe equipe-${classe}`} title={auto.rodando ? `Desde ${auto.inicio}: ${auto.motivo}` : ''}>
          <span>Equipe</span><b>{texto}</b>
        </div>
      </div>
      <button className="btn nova" type="button" onClick={onNovaMissao}>+ Nova missão</button>
      <nav className="abas" role="tablist" aria-label="Visões do painel">
        <button className="aba" role="tab" type="button" aria-selected={aba === 'escritorio'} onClick={() => onAba('escritorio')}>Escritório</button>
        <button className="aba" role="tab" type="button" aria-selected={aba === 'missoes'} onClick={() => onAba('missoes')}>Missões</button>
        {modo === 'nuvem' && <button className="aba" type="button" onClick={onSair}>Sair</button>}
      </nav>
    </header>
  );
}
