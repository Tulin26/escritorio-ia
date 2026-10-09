import { useEffect, useRef, useState } from 'react';
import Dialogo from './Dialogo.jsx';
import { Miniatura } from './Anexos.jsx';
import { api } from '../api.js';
import { arquivosDoArraste, comCaminho, ignorar } from '../arquivos.js';
import { LIMITES_ANEXOS, ehImagem, extensaoDe, tamanhoLegivel } from '../dados.js';

// Online, foto acima disso é reduzida no navegador antes de subir (lado maior com até LADO_MAXIMO px, em JPEG).
// No PC a foto vai como está.
const REDUZIR_ACIMA = 900 * 1024;
const LADO_MAXIMO = 1920;
// No PC os anexos sobem um a um, alguns ao mesmo tempo.
const ENVIOS_JUNTOS = 4;
// Com uma pasta grande, a lista mostra só os primeiros (o resto vira "e mais N arquivos").
const MOSTRAR_ATE = 40;

// "soltos" são arquivos que você soltou em qualquer lugar do painel ({ chave, arquivos }): entram como anexos.
export default function NovaMissao({ aberto, estado, nuvem, soltos, onUsarSoltos, onFechar, onEnviar }) {
  return (
    <Dialogo aberto={aberto} onFechar={onFechar} rotulo="dlgMissaoTitulo">
      <Formulario estado={estado} nuvem={nuvem} soltos={soltos} onUsarSoltos={onUsarSoltos} onFechar={onFechar} onEnviar={onEnviar} />
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
    if (!blob || blob.size >= arquivo.size) return { blob: arquivo };
    return { blob, trocarExtensao: 'jpg', reduzida: true };
  } catch {
    return { blob: arquivo };
  }
}

const paraBase64 = (blob) => new Promise((ok, erro) => {
  const leitor = new FileReader();
  leitor.onload = () => ok(String(leitor.result).split(',')[1] || '');
  leitor.onerror = () => erro(leitor.error);
  leitor.readAsDataURL(blob);
});

// Prévia de uma imagem escolhida: o endereço temporário só existe enquanto ela aparece na lista.
function MiniaturaLocal({ anexo }) {
  const [src, setSrc] = useState('');
  useEffect(() => {
    if (!ehImagem(anexo.nome)) return undefined;
    const url = URL.createObjectURL(anexo.blob);
    setSrc(url);
    return () => URL.revokeObjectURL(url);
  }, [anexo]);
  if (ehImagem(anexo.nome) && !src) return <span className="miniatura arquivo" aria-hidden="true" />;
  return <Miniatura anexo={anexo} src={src} />;
}

const novoLote = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

function Formulario({ estado, nuvem, soltos, onUsarSoltos, onFechar, onEnviar }) {
  const limites = nuvem ? LIMITES_ANEXOS.nuvem : LIMITES_ANEXOS.pc;
  const [projeto, setProjeto] = useState('');
  const [texto, setTexto] = useState('');
  const [anexos, setAnexos] = useState([]);
  const [arrastando, setArrastando] = useState(false);
  const [preparando, setPreparando] = useState(false);
  const [progresso, setProgresso] = useState(null);
  const [chamar, setChamar] = useState(true);
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const entrada = useRef(null);
  const entradaPasta = useRef(null);
  const lista = useRef(anexos);
  lista.current = anexos;

  // "Escolher pasta": o atributo não é padrão, então entra direto no elemento.
  useEffect(() => {
    if (entradaPasta.current) entradaPasta.current.setAttribute('webkitdirectory', '');
  }, []);

  // Arquivos soltos no painel (fora deste formulário) viram anexos; a chave evita usar a mesma leva duas vezes.
  const levasUsadas = useRef(new Set());
  useEffect(() => {
    if (!soltos || levasUsadas.current.has(soltos.chave)) return;
    levasUsadas.current.add(soltos.chave);
    onUsarSoltos();
    adicionar(soltos.arquivos);
  }, [soltos]); // eslint-disable-line react-hooks/exhaustive-deps

  const nomes = new Set();
  (estado.projetos || []).forEach((p) => nomes.add(p.nome || p.id));
  (estado.pedidos || []).forEach((p) => nomes.add(p.projetoNome || p.projeto));
  const total = anexos.reduce((t, a) => t + a.blob.size, 0);

  async function adicionar(itens) {
    const escolhidos = [...itens].map(comCaminho).filter((i) => i && i.arquivo && !ignorar(i.caminho));
    if (!escolhidos.length) return;
    setAviso('');
    setPreparando(true);
    const problemas = [];
    const novos = [];
    // A mesma pasta escolhida duas vezes não repete arquivo.
    const ja = new Set(lista.current.map((a) => `${a.nome}|${a.original}`));
    let soma = lista.current.reduce((t, a) => t + a.blob.size, 0);
    for (const { arquivo, caminho } of escolhidos) {
      if (ja.has(`${caminho}|${arquivo.size}`)) continue;
      ja.add(`${caminho}|${arquivo.size}`);
      if (lista.current.length + novos.length >= limites.quantidade) {
        problemas.push(`online, no máximo ${limites.quantidade} anexos por pedido (no PC não há limite)`);
        break;
      }
      const reduzir = nuvem && ['jpg', 'jpeg', 'png', 'webp'].includes(extensaoDe(arquivo.name)) && arquivo.size > REDUZIR_ACIMA;
      const pronto = reduzir ? await reduzirImagem(arquivo) : { blob: arquivo };
      if (pronto.blob.size > limites.porArquivo) {
        problemas.push(`"${caminho}" passa de ${tamanhoLegivel(limites.porArquivo)} (limite do painel online)`);
        continue;
      }
      if (soma + pronto.blob.size > limites.bytes) {
        problemas.push(`"${caminho}" passaria do limite de ${tamanhoLegivel(limites.bytes)} do painel online`);
        continue;
      }
      soma += pronto.blob.size;
      novos.push({
        id: `${Date.now()}-${Math.random()}`,
        blob: pronto.blob,
        nome: pronto.trocarExtensao ? caminho.replace(/(\.[^./]+)?$/, `.${pronto.trocarExtensao}`) : caminho,
        original: arquivo.size,
        reduzida: pronto.reduzida,
      });
    }
    setAnexos((atual) => [...atual, ...novos]);
    setPreparando(false);
    if (problemas.length) setAviso(`Não entrou: ${problemas.join('; ')}.`);
  }

  const remover = (id) => setAnexos((atual) => atual.filter((a) => a.id !== id));

  // Colar uma imagem (Ctrl+V) em qualquer campo do formulário também anexa.
  function colar(e) {
    const arquivos = [...(e.clipboardData ? e.clipboardData.files : [])];
    if (!arquivos.length) return;
    e.preventDefault();
    adicionar(arquivos);
  }

  // No PC: cada arquivo sobe sozinho (sem limite de quantidade nem tamanho) e o pedido leva só o número do lote.
  async function subirLote() {
    const lote = novoLote();
    let feitos = 0;
    let proximo = 0;
    setProgresso({ feitos, total: anexos.length });
    const trabalhar = async () => {
      while (proximo < anexos.length) {
        const a = anexos[proximo++];
        try {
          await api.enviarAnexo(lote, a.nome, a.blob);
        } catch (e) {
          throw new Error(`Não consegui enviar "${a.nome}": ${e.message}`);
        }
        feitos += 1;
        setProgresso({ feitos, total: anexos.length });
      }
    };
    await Promise.all(Array.from({ length: Math.min(ENVIOS_JUNTOS, anexos.length) }, trabalhar));
    return lote;
  }

  async function enviar(e) {
    e.preventDefault();
    if (!projeto.trim()) return setAviso('Diga para qual projeto é a missão.');
    if (texto.trim().length < 5) return setAviso('Descreva o que você quer.');
    setOcupado(true);
    setAviso('');
    try {
      let envio = {};
      if (anexos.length && nuvem) {
        envio = { anexos: await Promise.all(anexos.map(async (a) => ({ caminho: a.nome, dados: await paraBase64(a.blob) }))) };
      } else if (anexos.length) {
        envio = { lote: await subirLote() };
      }
      await onEnviar(projeto.trim(), texto.trim(), envio, nuvem && chamar);
      onFechar();
    } catch (err) {
      setAviso(err.message);
      setOcupado(false);
      setProgresso(null);
    }
  }

  // O formulário inteiro aceita arquivos e pastas arrastados (e segura o evento, para o painel não abrir outra missão).
  const arrastar = (e) => {
    if (!e.dataTransfer || ![...e.dataTransfer.types].includes('Files')) return;
    e.preventDefault();
    e.stopPropagation();
    setArrastando(true);
  };
  const sair = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setArrastando(false);
  };
  const soltar = (e) => {
    if (!e.dataTransfer || !e.dataTransfer.files.length) return;
    e.preventDefault();
    e.stopPropagation();
    setArrastando(false);
    arquivosDoArraste(e.dataTransfer).then(adicionar, (erro) => setAviso(`Não consegui ler o que foi solto: ${erro.message}`));
  };

  const textoDoBotao = progresso ? `Enviando ${progresso.feitos} de ${progresso.total}…` : 'Enviando…';

  return (
    <form onSubmit={enviar} onPaste={colar} onDragEnter={arrastar} onDragOver={arrastar} onDragLeave={sair} onDrop={soltar} noValidate>
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
        <div className={`area-anexos${arrastando ? ' arrastando' : ''}`}>
          <input
            ref={entrada}
            id="mAnexos"
            className="entrada-anexos"
            tabIndex={-1}
            type="file"
            multiple
            onChange={(e) => { adicionar(e.target.files); e.target.value = ''; }}
          />
          <input
            ref={entradaPasta}
            className="entrada-anexos"
            tabIndex={-1}
            type="file"
            multiple
            aria-label="Escolher pasta"
            onChange={(e) => { adicionar(e.target.files); e.target.value = ''; }}
          />
          <button type="button" className="btn neutro" disabled={preparando || ocupado} onClick={() => entrada.current && entrada.current.click()}>
            {preparando ? 'Preparando…' : 'Escolher arquivos'}
          </button>
          <button type="button" className="btn neutro" disabled={preparando || ocupado} onClick={() => entradaPasta.current && entradaPasta.current.click()}>
            Escolher pasta
          </button>
          <span className="comentario">{arrastando ? 'Pode soltar!' : 'ou arraste arquivos e pastas aqui (ou cole uma imagem)'}</span>
        </div>
        {anexos.length > 0 && (
          <>
            <p className="dica">
              {anexos.length} {anexos.length === 1 ? 'arquivo' : 'arquivos'} · {tamanhoLegivel(total)}{' '}
              {anexos.length > 1 && !ocupado && (
                <button type="button" className="btn neutro" onClick={() => setAnexos([])}>Tirar todos</button>
              )}
            </p>
            <ul className="anexos-escolhidos">
              {anexos.slice(0, MOSTRAR_ATE).map((a) => (
                <li key={a.id}>
                  <MiniaturaLocal anexo={a} />
                  <span className="anexo-info">
                    <b>{a.nome}</b>
                    <span className="comentario">{tamanhoLegivel(a.blob.size)}{a.reduzida ? ' · foto reduzida' : ''}</span>
                  </span>
                  <button type="button" className="tirar" aria-label={`Tirar ${a.nome}`} disabled={ocupado} onClick={() => remover(a.id)}>×</button>
                </li>
              ))}
            </ul>
            {anexos.length > MOSTRAR_ATE && <p className="dica">… e mais {anexos.length - MOSTRAR_ATE} arquivos.</p>}
          </>
        )}
        <p className="dica">
          {nuvem
            ? <>Qualquer tipo de arquivo. No painel online: até {limites.quantidade} arquivos e {tamanhoLegivel(limites.bytes)} no total (limite do Vercel); fotos grandes são reduzidas. No PC não há limite.</>
            : <>Qualquer tipo de arquivo, quantos quiser, ou uma pasta inteira (com as subpastas). Sem limite de tamanho.</>}
          {' '}A equipe lê o que conseguir abrir (texto, PDF, imagens; Word: salve também em PDF). Os anexos ficam na pasta anexos/ (e no GitHub, menos arquivos acima de 95 MB).
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
        <button type="button" className="btn neutro" onClick={onFechar} disabled={ocupado}>Cancelar</button>
        <button type="submit" className="btn aprovar" disabled={ocupado || preparando}>{ocupado ? textoDoBotao : 'Enviar ao Diretor'}</button>
      </div>
    </form>
  );
}
