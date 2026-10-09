import { useState } from 'react';
import { urlAnexo } from '../api.js';
import { ehImagem, extensaoDe, tamanhoLegivel } from '../dados.js';

// Com uma pasta inteira anexada, mostra só os primeiros e um botão para ver o resto.
const MOSTRAR_ATE = 12;

// Anexos de um pedido (ou de uma missão): imagem vira miniatura; o resto vira um cartãozinho com a extensão.
// Clicar abre o arquivo numa aba nova (ou baixa, se não for imagem, PDF nem texto).
// Aceita a lista do pedido ({ nome, arquivo, tamanho }) ou só caminhos (missão); um caminho terminado em "/" é uma pasta.
export default function Anexos({ anexos, grande = false }) {
  const [tudo, setTudo] = useState(false);
  const lista = (anexos || [])
    .map((a) => (typeof a === 'string' ? { arquivo: a, nome: a.replace(/\/$/, '').split('/').pop() + (a.endsWith('/') ? '/' : '') } : a))
    .filter((a) => a && a.arquivo);
  if (!lista.length) return null;
  const visiveis = tudo ? lista : lista.slice(0, MOSTRAR_ATE);
  return (
    <ul className={`anexos-lista${grande ? ' grande' : ''}`} aria-label="Anexos">
      {visiveis.map((a) => (
        <li key={a.arquivo}>
          {a.arquivo.endsWith('/') ? (
            <span className="anexo" title={a.arquivo}>
              <span className="miniatura arquivo ext-x" aria-hidden="true">pasta</span>
              <span className="anexo-nome">{a.nome}</span>
            </span>
          ) : (
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
          )}
        </li>
      ))}
      {lista.length > MOSTRAR_ATE && (
        <li>
          <button type="button" className="btn neutro" onClick={(e) => { e.stopPropagation(); setTudo(!tudo); }}>
            {tudo ? 'Mostrar menos' : `+ ${lista.length - MOSTRAR_ATE} arquivos`}
          </button>
        </li>
      )}
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
