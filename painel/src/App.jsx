import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api.js';
import { arquivosDoArraste } from './arquivos.js';
import { faseDoDia, nivelDe, xpDe } from './dados.js';
import { useMovimentoReduzido, useRelogio } from './ganchos.js';
import Topo from './componentes/Topo.jsx';
import MapaEscritorio from './componentes/MapaEscritorio.jsx';
import EquipePainel from './componentes/EquipePainel.jsx';
import Lado from './componentes/Lado.jsx';
import Missoes from './componentes/Missoes.jsx';
import Letreiro from './componentes/Letreiro.jsx';
import Ficha from './componentes/Ficha.jsx';
import NovaMissao from './componentes/NovaMissao.jsx';
import Login from './componentes/Login.jsx';

// Quanto esperar entre uma leitura do estado e outra (a aba escondida lê bem menos).
const INTERVALO = { local: 3000, nuvem: 5000, escondida: 30000 };
const DURACAO_FESTA_MS = 2400;

export default function App() {
  const [sessao, setSessao] = useState(null);
  const [estado, setEstado] = useState(null);
  const [erro, setErro] = useState('');
  const [aba, setAba] = useState('escritorio');
  const [selecionado, setSelecionado] = useState('diretor');
  const [ficha, setFicha] = useState(null);
  const [novaAberta, setNovaAberta] = useState(false);
  const [festas, setFestas] = useState({});
  const [nivelNovo, setNivelNovo] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [soltos, setSoltos] = useState(null);
  const [arrastandoArquivo, setArrastandoArquivo] = useState(false);
  const ultimoJson = useRef('');
  const anterior = useRef(null);
  // O aviso some com fade: o texto fica até o fim da transição.
  const textoAviso = useRef('');
  if (aviso) textoAviso.current = aviso.texto;
  const agora = useRelogio();
  const reduzido = useMovimentoReduzido();
  const fase = faseDoDia(agora.getHours());

  useEffect(() => {
    api.sessao().then(setSessao).catch(() => setSessao({ modo: 'local', logado: true }));
  }, []);

  const mostrarAviso = useCallback((texto) => {
    const chave = Date.now();
    setAviso({ texto, chave });
    setTimeout(() => setAviso((a) => (a && a.chave === chave ? null : a)), 6000);
  }, []);

  // Compara o estado novo com o anterior: missão que virou "aprovado" faz o agente comemorar.
  const comemorar = useCallback((antes, depois) => {
    if (!antes) return;
    const statusAntes = new Map((antes.missoes || []).map((m) => [m.id, m.status]));
    const aprovadas = (depois.missoes || []).filter((m) => m.status === 'aprovado' && statusAntes.has(m.id) && statusAntes.get(m.id) !== 'aprovado');
    if (aprovadas.length) {
      const chave = Date.now();
      const porAgente = {};
      aprovadas.forEach((m) => { porAgente[m.agente] = { xp: ((porAgente[m.agente] || {}).xp || 0) + (Number(m.xp) || 0), chave }; });
      setFestas((f) => ({ ...f, ...porAgente }));
      setTimeout(() => setFestas((f) => Object.fromEntries(Object.entries(f).filter(([, v]) => v.chave !== chave))), DURACAO_FESTA_MS);
    }
    const nivel = nivelDe(xpDe(depois.missoes || []));
    if (nivel > nivelDe(xpDe(antes.missoes || []))) {
      const chave = Date.now();
      setNivelNovo({ nivel, chave });
      setTimeout(() => setNivelNovo((n) => (n && n.chave === chave ? null : n)), 3600);
    }
  }, []);

  const aplicar = useCallback((dados) => {
    const { aviso: avisoServidor, pedido, ...novo } = dados;
    if (avisoServidor) mostrarAviso(avisoServidor);
    const json = JSON.stringify(novo);
    if (json === ultimoJson.current) return;
    ultimoJson.current = json;
    comemorar(anterior.current, novo);
    anterior.current = novo;
    setEstado(novo);
  }, [comemorar, mostrarAviso]);

  const carregar = useCallback(async () => {
    try {
      aplicar(await api.estado());
      setErro('');
    } catch (e) {
      if (e.status === 401) setSessao({ modo: 'nuvem', logado: false });
      else setErro(`Não consegui ler o estado do escritório (${e.message}).`);
    }
  }, [aplicar]);

  useEffect(() => {
    if (!sessao || !sessao.logado) return undefined;
    let vivo = true;
    let espera;
    const ciclo = async () => {
      await carregar();
      if (!vivo) return;
      const intervalo = document.hidden ? INTERVALO.escondida : INTERVALO[sessao.modo] || INTERVALO.local;
      espera = setTimeout(ciclo, intervalo);
    };
    const voltou = () => {
      if (document.hidden) return;
      clearTimeout(espera);
      ciclo();
    };
    ciclo();
    document.addEventListener('visibilitychange', voltou);
    return () => {
      vivo = false;
      clearTimeout(espera);
      document.removeEventListener('visibilitychange', voltou);
    };
  }, [sessao, carregar]);

  const nuvem = sessao && sessao.modo === 'nuvem';
  const pronto = Boolean(sessao && sessao.logado && estado);

  // Arrastar arquivos para qualquer lugar do painel: aparece o aviso "solte aqui" e, ao soltar, abre uma nova missão
  // com eles anexados. Dentro do formulário da nova missão quem cuida é o próprio formulário.
  useEffect(() => {
    if (!pronto) return undefined;
    const temArquivos = (e) => e.dataTransfer && [...e.dataTransfer.types].includes('Files');
    let saida;
    const sobre = (e) => {
      if (!temArquivos(e)) return;
      e.preventDefault(); // sem isso o navegador abre o arquivo no lugar do painel
      clearTimeout(saida);
      setArrastandoArquivo(true);
    };
    const saiu = () => {
      clearTimeout(saida);
      saida = setTimeout(() => setArrastandoArquivo(false), 120);
    };
    const soltou = (e) => {
      if (!temArquivos(e)) return;
      e.preventDefault();
      clearTimeout(saida);
      setArrastandoArquivo(false);
      if (!e.dataTransfer.files.length) return;
      // Pastas soltas no painel: entra nelas e pega tudo o que tiver dentro.
      arquivosDoArraste(e.dataTransfer).then((arquivos) => {
        setSoltos({ chave: Date.now(), arquivos });
        setNovaAberta(true);
      }, (erro) => mostrarAviso(`Não consegui ler o que foi solto: ${erro.message}`));
    };
    window.addEventListener('dragenter', sobre);
    window.addEventListener('dragover', sobre);
    window.addEventListener('dragleave', saiu);
    window.addEventListener('drop', soltou);
    return () => {
      clearTimeout(saida);
      window.removeEventListener('dragenter', sobre);
      window.removeEventListener('dragover', sobre);
      window.removeEventListener('dragleave', saiu);
      window.removeEventListener('drop', soltou);
    };
  }, [pronto]);

  async function decidir(id, acao, comentario) {
    aplicar(await api.decisao(id, acao, comentario));
    if (nuvem) {
      mostrarAviso(acao === 'aprovar'
        ? `Você aprovou ${id}. Quando terminar de revisar, clique em "Chamar a equipe".`
        : `Ajuste pedido em ${id}. Clique em "Chamar a equipe" para refazerem.`);
    }
  }

  async function chamarEquipe() {
    aplicar(await api.rodada());
  }

  async function novoPedido(projeto, texto, envio, chamarAgora) {
    aplicar(await api.pedido(projeto, texto, envio));
    if (!chamarAgora) return;
    try {
      await chamarEquipe();
    } catch (e) {
      mostrarAviso(`O pedido foi salvo, mas não consegui chamar a equipe: ${e.message}`);
    }
  }

  async function ligarGit(ligado) {
    aplicar(await api.ligarGit(ligado));
    mostrarAviso(ligado
      ? 'Envio automático ligado: o que mudar nesta pasta vai para o GitHub depois de cada rodada e decisão.'
      : 'Envio automático desligado: nada sai do PC até você clicar em "Enviar agora".');
  }

  async function enviarGit() {
    aplicar(await api.enviarGit());
  }

  // Repositório próprio de um projeto: criar (pasta + GitHub) ou enviar o que mudou nele.
  async function repoProjeto(acao, id) {
    aplicar(await (acao === 'criar' ? api.criarRepo(id) : api.enviarRepo(id)));
  }

  async function sair() {
    await api.logout().catch(() => {});
    ultimoJson.current = '';
    anterior.current = null;
    setEstado(null);
    setSessao({ modo: 'nuvem', logado: false });
  }

  if (!sessao) return <div className="carregando">Abrindo o escritório…</div>;
  if (!sessao.logado) {
    return <Login onEntrar={async (senha) => { await api.login(senha); setSessao({ modo: 'nuvem', logado: true }); }} />;
  }
  if (!estado) return <div className="carregando">{erro || 'Abrindo o escritório…'}</div>;

  const abrirArquivo = (id) => setFicha({ tipo: 'arquivo', id });
  // Clicar na sua sala leva até a sua mesa de aprovações (no celular ela fica embaixo do escritório).
  const irParaSuaMesa = () => {
    const alvo = document.getElementById('sua-mesa');
    if (!alvo) return;
    alvo.scrollIntoView({ behavior: reduzido ? 'auto' : 'smooth', block: 'start' });
    alvo.focus({ preventScroll: true });
  };
  return (
    <>
      <a className="pular-conteudo" href="#conteudo">Pular para o conteúdo</a>
      <Topo
        estado={estado}
        agora={agora}
        fase={fase}
        aba={aba}
        onAba={setAba}
        onNovaMissao={() => setNovaAberta(true)}
        modo={sessao.modo}
        onSair={sair}
      />
      {erro && <div className="erro" role="alert">{erro}</div>}
      <div className="corpo">
        <main id="conteudo" tabIndex={-1}>
          {aba === 'escritorio' ? (
            <MapaEscritorio
              estado={estado}
              fase={fase}
              agora={agora}
              festas={festas}
              reduzido={reduzido}
              selecionado={selecionado}
              onAgente={setSelecionado}
              onMemoria={() => setFicha({ tipo: 'memoria' })}
              onPedidos={() => setFicha({ tipo: 'pedidos' })}
              onVoce={irParaSuaMesa}
              onGit={() => setFicha({ tipo: 'git' })}
            />
          ) : (
            <Missoes estado={estado} onArquivo={abrirArquivo} />
          )}
        </main>
        <div className="coluna-equipe">
          <EquipePainel estado={estado} selecionado={selecionado} onSelecionar={setSelecionado} onDetalhes={(id) => setFicha({ tipo: 'agente', id })} />
          <Lado estado={estado} onDecidir={decidir} onChamar={chamarEquipe} onArquivo={abrirArquivo} />
        </div>
      </div>
      <Letreiro estado={estado} />
      <Ficha
        ficha={ficha}
        estado={estado}
        onFechar={() => setFicha(null)}
        onArquivo={abrirArquivo}
        onLigarGit={ligarGit}
        onEnviarGit={enviarGit}
        onRepo={repoProjeto}
      />
      <NovaMissao
        aberto={novaAberta}
        estado={estado}
        nuvem={nuvem}
        soltos={soltos}
        onUsarSoltos={() => setSoltos(null)}
        onFechar={() => setNovaAberta(false)}
        onEnviar={novoPedido}
      />
      {arrastandoArquivo && !novaAberta && (
        <div className="soltar-arquivos" aria-hidden="true">
          <span>Solte os arquivos para criar uma nova missão com eles</span>
        </div>
      )}
      {nivelNovo && <div className="nivel-novo" key={nivelNovo.chave} role="status">Nível {nivelNovo.nivel}!</div>}
      <div className={`aviso-flutuante${aviso ? ' visivel' : ''}`} role="status" aria-live="polite">{textoAviso.current}</div>
    </>
  );
}
