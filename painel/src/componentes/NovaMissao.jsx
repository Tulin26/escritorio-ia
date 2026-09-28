import { useEffect, useRef, useState } from 'react';
import Dialogo from './Dialogo.jsx';
import { Miniatura } from './Anexos.jsx';
import { EXTENSOES_ANEXO, LIMITE_ANEXOS, ehImagem, extensaoDe, tamanhoLegivel } from '../dados.js';

// Foto acima disso é reduzida no navegador antes de subir (lado maior com até LADO_MAXIMO px, em JPEG).
const REDUZIR_ACIMA = 900 * 1024;
const LADO_MAXIMO = 1920;

export default function NovaMissao({ aberto, estado, nuvem, onFechar, onEnviar }) {
  return (
    <Dialogo aberto={aberto} onFechar={onFechar} rotulo="dlgMissaoTitulo">
      <Formulario estado={estado} nuvem={nuvem} onFechar={onFechar} onEnviar={onEnviar} />
    </Dialogo>
  );
}

async function reduzirImagem(arquivo) {
  try {
    const bitmap = await createImageBitmap(arquivo);
    const escala = Math.min(1, LADO_MAXIMO / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * escala);
    canvas.height = Math.round(bitmap.height * escala);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff'; // PNG transparente vira fundo branco no JPEG
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    if (bitmap.close) bitmap.close();
    const blob = await new Promise((ok) => canvas.toBlob(ok, 'image/jpeg', 0.85));
    if (!blob || blob.size >= arquivo.size) return { blob: arquivo, nome: arquivo.name };
    return { blob, nome: `${arquivo.name.replace(/\.[^.]+$/, '')}.jpg`, reduzida: true };
  } catch {
    return { blob: arquivo, nome: arquivo.name };
  }
}

const paraBase64 = (blob) => new Promise((ok, erro) => {
  const leitor = new FileReader();
  leitor.onload = () => ok(String(leitor.result).split(',')[1] || '');
  leitor.onerror = () => erro(leitor.error);
  leitor.readAsDataURL(blob);
});

function Formulario({ estado, nuvem, onFechar, onEnviar }) {
  const [projeto, setProjeto] = useState('');
  const [texto, setTexto] = useState('');
  const [anexos, setAnexos] = useState([]);
  const [arrastando, setArrastando] = useState(false);
  const [preparando, setPreparando] = useState(false);
  const [chamar, setChamar] = useState(true);
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const entrada = useRef(null);
  const lista = useRef(anexos);
  lista.current = anexos;

  // As prévias das imagens são endereços temporários do navegador: libera tudo ao fechar.
  useEffect(() => () => lista.current.forEach((a) => a.previa && URL.revokeObjectURL(a.previa)), []);

  const nomes = new Set();
  (estado.projetos || []).forEach((p) => nomes.add(p.nome || p.id));
  (estado.pedidos || []).forEach((p) => nomes.add(p.projetoNome || p.projeto));
  const total = anexos.reduce((t, a) => t + a.blob.size, 0);

  async function adicionar(arquivos) {
    const escolhidos = [...arquivos];
    if (!escolhidos.length) return;
    setAviso('');
    setPreparando(true);
    const problemas = [];
    const novos = [];
    let soma = total;
    for (const arquivo of escolhidos) {
      if (lista.current.length + novos.length >= LIMITE_ANEXOS.quantidade) {
        problemas.push(`no máximo ${LIMITE_ANEXOS.quantidade} anexos por pedido`);
        break;
      }
      const ext = extensaoDe(arquivo.name);
      if (!EXTENSOES_ANEXO.includes(ext)) {
        problemas.push(`"${arquivo.name}" não é de um tipo aceito`);
        continue;
      }
      if (!arquivo.size) {
        problemas.push(`"${arquivo.name}" está vazio`);
        continue;
      }
      const pronto = ['jpg', 'jpeg', 'png', 'webp'].includes(ext) && arquivo.size > REDUZIR_ACIMA
        ? await reduzirImagem(arquivo)
        : { blob: arquivo, nome: arquivo.name };
      if (soma + pronto.blob.size > LIMITE_ANEXOS.bytes) {
        problemas.push(`"${arquivo.name}" passaria do limite de ${tamanhoLegivel(LIMITE_ANEXOS.bytes)} no total`);
        continue;
      }
      soma += pronto.blob.size;
      novos.push({
        id: `${Date.now()}-${Math.random()}`,
        ...pronto,
        previa: ehImagem(pronto.nome) ? URL.createObjectURL(pronto.blob) : '',
      });
    }
    setAnexos((atual) => [...atual, ...novos]);
    setPreparando(false);
    if (problemas.length) setAviso(`Não entrou: ${problemas.join('; ')}.`);
  }

  function remover(id) {
    setAnexos((atual) => atual.filter((a) => {
      if (a.id === id && a.previa) URL.revokeObjectURL(a.previa);
      return a.id !== id;
    }));
  }

  // Colar uma imagem (Ctrl+V) em qualquer campo do formulário também anexa.
  function colar(e) {
    const arquivos = [...(e.clipboardData ? e.clipboardData.files : [])];
    if (!arquivos.length) return;
    e.preventDefault();
    adicionar(arquivos);
  }

  async function enviar(e) {
    e.preventDefault();
    if (!projeto.trim()) return setAviso('Diga para qual projeto é a missão.');
    if (texto.trim().length < 5) return setAviso('Descreva o que você quer.');
    setOcupado(true);
    setAviso('');
    try {
      const prontos = await Promise.all(anexos.map(async (a) => ({ nome: a.nome, dados: await paraBase64(a.blob) })));
      await onEnviar(projeto.trim(), texto.trim(), prontos, nuvem && chamar);
      onFechar();
    } catch (err) {
      setAviso(err.message);
      setOcupado(false);
    }
  }

  return (
    <form onSubmit={enviar} onPaste={colar} noValidate>
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

        <label htmlFor="mAnexos">Anexos (opcional)</label>
        <div
          className={`area-anexos${arrastando ? ' arrastando' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => { e.preventDefault(); setArrastando(false); adicionar(e.dataTransfer.files); }}
        >
          <input
            ref={entrada}
            id="mAnexos"
            className="entrada-anexos"
            tabIndex={-1}
            type="file"
            multiple
            accept={EXTENSOES_ANEXO.map((x) => `.${x}`).join(',')}
            onChange={(e) => { adicionar(e.target.files); e.target.value = ''; }}
          />
          <button type="button" className="btn neutro" disabled={preparando || anexos.length >= LIMITE_ANEXOS.quantidade} onClick={() => entrada.current && entrada.current.click()}>
            {preparando ? 'Preparando…' : 'Escolher arquivos'}
          </button>
          <span className="comentario">ou arraste para cá (ou cole uma imagem)</span>
        </div>
        {anexos.length > 0 && (
          <ul className="anexos-escolhidos">
            {anexos.map((a) => (
              <li key={a.id}>
                <Miniatura anexo={a} src={a.previa} />
                <span className="anexo-info">
                  <b>{a.nome}</b>
                  <span className="comentario">{tamanhoLegivel(a.blob.size)}{a.reduzida ? ' · foto reduzida' : ''}</span>
                </span>
                <button type="button" className="tirar" aria-label={`Tirar ${a.nome}`} onClick={() => remover(a.id)}>×</button>
              </li>
            ))}
          </ul>
        )}
        <p className="dica">
          Fotos, prints, logo, PDF, TXT, MD, CSV ou JSON (planilha: salve como CSV). Até {LIMITE_ANEXOS.quantidade} arquivos e{' '}
          {tamanhoLegivel(LIMITE_ANEXOS.bytes)} no total{anexos.length ? ` (usando ${tamanhoLegivel(total)})` : ''}; fotos grandes são reduzidas.
          A equipe lê tudo, e os anexos ficam guardados na pasta anexos/ (e no GitHub).
        </p>
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
        <button type="submit" className="btn aprovar" disabled={ocupado || preparando}>{ocupado ? 'Enviando…' : 'Enviar ao Diretor'}</button>
      </div>
    </form>
  );
}
