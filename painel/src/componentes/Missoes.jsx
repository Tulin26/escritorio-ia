import { useState } from 'react';
import { STATUS, nomeAgente } from '../dados.js';

export default function Missoes({ estado, onArquivo }) {
  const [filtro, setFiltro] = useState('');
  const missoes = estado.missoes || [];
  const linhas = missoes.filter((m) => !filtro || m.status === filtro).slice().reverse();
  return (
    <div className="missoes">
      <div className="filtros">
        {[['', 'Todas'], ...STATUS.map((s) => [s, s])].map(([valor, rotulo]) => (
          <button key={rotulo} className="filtro" type="button" aria-pressed={filtro === valor} onClick={() => setFiltro(valor)}>
            {rotulo} ({valor ? missoes.filter((m) => m.status === valor).length : missoes.length})
          </button>
        ))}
      </div>
      <div className="tabela-wrap">
        <table>
          <thead>
            <tr><th>ID</th><th>Título</th><th>Agente</th><th>Projeto</th><th>Status</th><th>XP</th><th>Data</th><th>Arquivo</th></tr>
          </thead>
          <tbody>
            {linhas.length ? linhas.map((m) => (
              <tr key={m.id}>
                <td className="mono">{m.id}</td>
                <td>
                  {m.titulo}{m.exemplo && <span className="tag-exemplo">EXEMPLO</span>}
                  {m.comentario && <div className="comentario">Seu comentário: {m.comentario}</div>}
                </td>
                <td>{nomeAgente(estado, m.agente)}</td>
                <td>{m.projeto || '-'}</td>
                <td><span className={`st ${m.status}`}>{m.status}</span></td>
                <td className="mono">{m.xp}</td>
                <td className="mono">{m.data || '-'}</td>
                <td>{m.arquivo ? <button className="link" type="button" onClick={() => onArquivo(m.id)}>{m.arquivo}</button> : '-'}</td>
              </tr>
            )) : (
              <tr><td colSpan={8} className="comentario">Nenhuma missão com esse filtro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
