import { useState } from 'react';
import { missoesDe, nivelDe, situacao, ROTULO_SITUACAO, xpDe } from '../dados.js';
import { spriteAgente } from '../sprites.js';

export default function EquipePainel({ estado, selecionado, onSelecionar, onDetalhes }) {
  const [aba, setAba] = useState('ficha');
  const agentes = estado.agentes || [];
  const ag = agentes.find((a) => a.id === selecionado) || agentes[0];
  const minhas = ag ? missoesDe(estado, ag.id) : [];
  const xp = xpDe(minhas), st = situacao(minhas);
  const ranking = agentes.map((a) => ({ ...a, xp: xpDe(missoesDe(estado, a.id)) })).sort((a, b) => b.xp - a.xp || a.nome.localeCompare(b.nome, 'pt-BR'));
  return (
    <section className="painel-time" aria-label="Informações da equipe">
      <div className="painel-time-abas" role="group" aria-label="Informações da equipe">
        <button type="button" aria-pressed={aba === 'ficha'} onClick={() => setAba('ficha')}>Ficha do agente</button>
        <button type="button" aria-pressed={aba === 'ranking'} onClick={() => setAba('ranking')}>Ranking</button>
      </div>
      {aba === 'ficha' ? ag ? (
        <div className="perfil-agente">
          <div className="perfil-cabecalho"><span className="perfil-sprite" aria-hidden="true" style={{ backgroundImage: `url(${spriteAgente(ag.id)})` }} /><div><span className="sobretitulo">{ag.sala || ag.area}</span><h2>{ag.nome}</h2><span className={`perfil-status ${st}`}>{ROTULO_SITUACAO[st]}</span></div></div>
          <p>{ag.papel || 'Pronto para receber uma missão.'}</p>
          <div className="perfil-progresso"><b>Nível {nivelDe(xp)}</b><span>{xp} XP</span></div>
          <div className="perfil-barra" role="progressbar" aria-label="Progresso para o próximo nível" aria-valuemin={0} aria-valuemax={100} aria-valuenow={xp % 100}><i style={{ width: `${xp % 100}%` }} /></div>
          <p className="perfil-xp">{100 - xp % 100} XP para o próximo nível. Só entregas aprovadas contam.</p>
          <button className="perfil-detalhes" type="button" onClick={() => onDetalhes(ag.id)}>Ver entregas e detalhes <span aria-hidden="true">↗</span></button>
        </div>
      ) : <p className="perfil-vazio">Nenhum agente cadastrado.</p> : (
        <div className="ranking-time"><p>XP conquistado em entregas aprovadas.</p><ol>{ranking.map((a, i) => <li key={a.id}><button type="button" onClick={() => { onSelecionar(a.id); setAba('ficha'); }}><span className="ranking-posicao">{String(i + 1).padStart(2, '0')}</span><span>{a.nome}<small>Nível {nivelDe(a.xp)}</small></span><b>{a.xp} <small>XP</small></b></button></li>)}</ol>{!ranking.length && <p>Nenhum agente cadastrado.</p>}</div>
      )}
    </section>
  );
}
