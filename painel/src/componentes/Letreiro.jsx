import { ROTULO_STATUS, maisRecentes, nomeAgente } from '../dados.js';

// Letreiro do rodapé: as últimas novidades do escritório passando da direita para a esquerda.
export default function Letreiro({ estado }) {
  const recentes = (estado.missoes || []).filter((m) => !m.exemplo).slice().sort(maisRecentes).slice(0, 6);
  const frases = recentes.length
    ? recentes.map((m) => `${(m.data || '').slice(11) || '--:--'} ${nomeAgente(estado, m.agente)}: ${m.titulo} (${ROTULO_STATUS[m.status] || m.status})`)
    : ['Clique num agente para ver a ficha. Use "+ Nova missão" para dar trabalho ao Diretor.'];
  return (
    <footer className="letreiro" aria-label="Novidades do escritório">
      <span>{frases.join('   ///   ')}</span>
    </footer>
  );
}
