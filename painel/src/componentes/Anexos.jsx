import { useState } from 'react';
import { urlAnexo } from '../api.js';
import { ehImagem, extensaoDe, tamanhoLegivel } from '../dados.js';

// Anexos de um pedido (ou de uma missão): imagem vira miniatura; PDF e texto viram um cartãozinho com a extensão.
// Clicar abre o arquivo numa aba nova. Aceita a lista do pedido ({ nome, arquivo, tamanho }) ou só caminhos (missão).
export default function Anexos({ anexos, grande = false }) {
  const lista = (anexos || [])
    .map((a) => (typeof a === 'string' ? { arquivo: a, nome: a.split('/').pop() } : a))
    .filter((a) => a && a.arquivo);
  if (!lista.length) return null;
  return (
    <ul className={`anexos-lista${grande ? ' grande' : ''}`} aria-label="Anexos">
      {lista.map((a) => (
        <li key={a.arquivo}>
          <a
            className="anexo"
            href={urlAnexo(a.arquivo)}
            target="_blank"
            rel="noopener noreferrer"
            title={a.tamanho ? `${a.nome} · ${tamanhoLegivel(a.tamanho)}` : a.nome}
            onClick={(e) => e.stopPropagation()}
          >
            <Miniatura anexo={a} />
            <span className="anexo-nome">{a.nome}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

// Se a imagem não carregar (arquivo sumiu, sem internet), mostra o cartãozinho no lugar.
export function Miniatura({ anexo, src }) {
  const [falhou, setFalhou] = useState(false);
  if (ehImagem(anexo.nome) && !falhou) {
    return <img className="miniatura" src={src || urlAnexo(anexo.arquivo)} alt="" loading="lazy" onError={() => setFalhou(true)} />;
  }
  return <span className={`miniatura arquivo ext-${extensaoDe(anexo.nome) || 'x'}`} aria-hidden="true">{extensaoDe(anexo.nome) || '?'}</span>;
}
