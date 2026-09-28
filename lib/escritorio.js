// Regras do escritório usadas pelo servidor local (server.js) e pelo painel online (api/*.js).
// Tudo aqui trabalha só com o objeto do estado.json: quem lê e grava o arquivo é quem chama.

const p2 = (n) => String(n).padStart(2, '0');

// Data no formato do escritório (AAAA-MM-DD HH:MM). Online o servidor roda em UTC,
// então usa o fuso de ESCRITORIO_FUSO (padrão: horário de Brasília).
function agora() {
  const fuso = process.env.ESCRITORIO_FUSO || (process.env.VERCEL ? 'America/Sao_Paulo' : '');
  if (!fuso) {
    const d = new Date();
    return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`;
  }
  const partes = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: fuso, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date()).map((p) => [p.type, p.value]));
  return `${partes.year}-${partes.month}-${partes.day} ${partes.hour}:${partes.minute}`;
}

const paraId = (texto) => String(texto || '')
  .normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);

// Uma missão em backlog está pronta quando o plano do Diretor do mesmo projeto foi aprovado
// e todas as missões citadas em "depende de" estão aprovadas.
function prontaParaRodar(m, missoes) {
  const planoAprovado = missoes.some((x) => x.area === 'diretor' && x.projeto === m.projeto && x.status === 'aprovado');
  if (!planoAprovado) return false;
  const trecho = /depende de:?([^|]*)/i.exec(m.resumo || '');
  const deps = trecho ? trecho[1].match(/m-\d+/g) || [] : [];
  return deps.every((id) => missoes.some((x) => x.id === id && x.status === 'aprovado'));
}

// Quantas coisas estão esperando a equipe (pedidos novos, refazer, missões liberadas ou interrompidas).
function trabalhoPendente(estado) {
  const missoes = (estado.missoes || []).filter((m) => !m.exemplo);
  return (estado.pedidos || []).filter((p) => p.status === 'novo').length
    + missoes.filter((m) => m.status === 'refazer' || m.status === 'rodando').length
    + missoes.filter((m) => m.status === 'backlog' && prontaParaRodar(m, missoes)).length;
}
const temTrabalho = (estado) => trabalhoPendente(estado) > 0;

class ErroEscritorio extends Error {
  constructor(status, mensagem) {
    super(mensagem);
    this.status = status;
  }
}

// Aprovar ou pedir para refazer uma missão que está "aguardando". Altera o estado e devolve a missão.
function decidir(estado, { id, acao, comentario }) {
  const texto = String(comentario || '').trim().slice(0, 4000);
  if (!['aprovar', 'refazer'].includes(acao)) throw new ErroEscritorio(400, 'ação deve ser aprovar ou refazer');
  if (acao === 'refazer' && !texto) throw new ErroEscritorio(400, 'escreva um comentário para o agente refazer');
  const missao = (estado.missoes || []).find((m) => m.id === id);
  if (!missao) throw new ErroEscritorio(404, `missão ${id} não encontrada`);
  if (missao.status !== 'aguardando') {
    throw new ErroEscritorio(409, `a missão ${id} está "${missao.status}", não "aguardando"`);
  }
  missao.status = acao === 'aprovar' ? 'aprovado' : 'refazer';
  missao.comentario = texto;
  missao.data = agora();
  return missao;
}

// Registra um pedido feito pelo botão "+ Nova missão". Altera o estado e devolve o pedido.
function novoPedido(estado, { projeto, texto }) {
  const descricao = String(texto || '').trim().slice(0, 4000);
  const projetoNome = String(projeto || '').trim().slice(0, 80);
  const id = paraId(projetoNome);
  if (descricao.length < 5) throw new ErroEscritorio(400, 'descreva a missão (pelo menos algumas palavras)');
  if (!id) throw new ErroEscritorio(400, 'diga para qual projeto é a missão');
  estado.pedidos = estado.pedidos || [];
  const maior = estado.pedidos.reduce((n, p) => Math.max(n, Number(String(p.id).replace(/\D/g, '')) || 0), 0);
  const pedido = { id: `p-${String(maior + 1).padStart(3, '0')}`, projeto: id, projetoNome, texto: descricao, status: 'novo', missao: '', data: agora() };
  estado.pedidos.push(pedido);
  return pedido;
}

// Só arquivos .md dentro da pasta do escritório podem ser abertos pelo painel.
function caminhoDeEntrega(estado, id) {
  const missao = (estado.missoes || []).find((m) => m.id === id);
  if (!missao || !missao.arquivo) throw new ErroEscritorio(404, 'Sem arquivo para esta missão.');
  const caminho = String(missao.arquivo).replace(/\\/g, '/').replace(/^\.\//, '');
  if (caminho.startsWith('/') || /^[a-z]:/i.test(caminho) || caminho.split('/').includes('..') || !caminho.toLowerCase().endsWith('.md')) {
    throw new ErroEscritorio(400, 'Caminho de arquivo não permitido.');
  }
  return caminho;
}

module.exports = {
  agora, paraId, prontaParaRodar, trabalhoPendente, temTrabalho, decidir, novoPedido, caminhoDeEntrega, ErroEscritorio,
};
