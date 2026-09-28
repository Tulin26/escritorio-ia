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

// ---------- Anexos dos pedidos ----------
// Arquivos que o dono manda junto com o pedido. Ficam em anexos/<id do pedido>/ e a equipe lê com a ferramenta Read,
// que abre imagens, PDFs e texto. Por isso só esses tipos entram (planilha: salve como CSV).
const TIPOS_ANEXO = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp',
  pdf: 'application/pdf', txt: 'text/plain', md: 'text/markdown', csv: 'text/csv', json: 'application/json',
};
// Limites por pedido. No PC o servidor é seu e aceita bem mais (25 MB por arquivo fica longe dos 100 MB que o GitHub
// recusa). Online, 3 MB no total: em base64 vira uns 4 MB, abaixo do limite de 4,5 MB por chamada do Vercel.
const LIMITES_ANEXOS = {
  pc: { quantidade: 10, porArquivo: 25 * 1024 * 1024, bytes: 50 * 1024 * 1024 },
  nuvem: { quantidade: 5, porArquivo: 3 * 1024 * 1024, bytes: 3 * 1024 * 1024 },
};
const emMB = (bytes) => `${Math.round(bytes / (1024 * 1024))} MB`;

// O começo de cada arquivo precisa bater com o tipo: um .png tem de ser mesmo um PNG.
const ASSINATURAS = {
  png: (b) => b.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])),
  jpg: (b) => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff,
  gif: (b) => b.subarray(0, 4).toString('latin1') === 'GIF8',
  webp: (b) => b.subarray(0, 4).toString('latin1') === 'RIFF' && b.subarray(8, 12).toString('latin1') === 'WEBP',
  pdf: (b) => b.subarray(0, 5).toString('latin1') === '%PDF-',
};
ASSINATURAS.jpeg = ASSINATURAS.jpg;
const ehTexto = (b) => !b.subarray(0, 8192).includes(0);

const extensaoDe = (nome) => {
  const i = nome.lastIndexOf('.');
  return i > 0 ? nome.slice(i + 1).toLowerCase() : '';
};

// Nome simples e seguro (sem pastas, acentos nem espaços), mantendo a extensão.
function nomeDeAnexo(original) {
  const nome = String(original || '').split(/[\\/]/).pop().trim();
  const ext = extensaoDe(nome);
  const base = paraId(ext ? nome.slice(0, -(ext.length + 1)) : nome).slice(0, 50).replace(/-+$/, '') || 'anexo';
  return { nome: `${base}.${ext}`, ext };
}

// Confere a lista que veio do painel ({ nome, dados em base64 }) e devolve os arquivos prontos para gravar.
// O tipo é decidido pela extensão (o que o navegador diz não conta) e conferido pelo conteúdo.
// Sem "limites", vale o do painel online (o menor); o server.js do PC passa LIMITES_ANEXOS.pc.
function prepararAnexos(lista, limites = LIMITES_ANEXOS.nuvem) {
  if (lista === undefined || lista === null) return [];
  if (!Array.isArray(lista)) throw new ErroEscritorio(400, 'anexos inválidos');
  if (lista.length > limites.quantidade) throw new ErroEscritorio(400, `mande no máximo ${limites.quantidade} anexos por pedido`);
  const usados = new Set();
  let total = 0;
  return lista.map((item) => {
    const { nome: sugerido, ext } = nomeDeAnexo(item && item.nome);
    const rotulo = String((item && item.nome) || 'sem nome').slice(0, 80);
    if (!TIPOS_ANEXO[ext]) {
      throw new ErroEscritorio(400, `o anexo "${rotulo}" não é de um tipo aceito (imagem, PDF, TXT, MD, CSV ou JSON)`);
    }
    const dados = String((item && item.dados) || '');
    if (!dados || !/^[A-Za-z0-9+/]+={0,2}$/.test(dados)) throw new ErroEscritorio(400, `o anexo "${rotulo}" chegou corrompido`);
    const conteudo = Buffer.from(dados, 'base64');
    total += conteudo.length;
    if (!conteudo.length) throw new ErroEscritorio(400, `o anexo "${rotulo}" está vazio`);
    if (conteudo.length > limites.porArquivo) throw new ErroEscritorio(413, `o anexo "${rotulo}" passa de ${emMB(limites.porArquivo)}`);
    if (total > limites.bytes) throw new ErroEscritorio(413, `os anexos passam de ${emMB(limites.bytes)} no total; mande arquivos menores`);
    const confere = ASSINATURAS[ext] || ehTexto;
    if (!confere(conteudo)) throw new ErroEscritorio(400, `o anexo "${rotulo}" não é o que a extensão diz (.${ext})`);
    // Dois arquivos com o mesmo nome no mesmo pedido: foto.jpg, foto-2.jpg…
    let nome = sugerido;
    for (let n = 2; usados.has(nome); n++) nome = sugerido.replace(/\.[^.]+$/, `-${n}$&`);
    usados.add(nome);
    return { nome, tipo: TIPOS_ANEXO[ext], tamanho: conteudo.length, conteudo };
  });
}

// Registra um pedido feito pelo botão "+ Nova missão". Altera o estado e devolve o pedido.
// Os anexos (já conferidos por prepararAnexos) ganham o caminho anexos/<id>/<nome>; quem chama grava os arquivos.
function novoPedido(estado, { projeto, texto }, anexos = []) {
  const descricao = String(texto || '').trim().slice(0, 4000);
  const projetoNome = String(projeto || '').trim().slice(0, 80);
  const id = paraId(projetoNome);
  if (descricao.length < 5) throw new ErroEscritorio(400, 'descreva a missão (pelo menos algumas palavras)');
  if (!id) throw new ErroEscritorio(400, 'diga para qual projeto é a missão');
  estado.pedidos = estado.pedidos || [];
  const maior = estado.pedidos.reduce((n, p) => Math.max(n, Number(String(p.id).replace(/\D/g, '')) || 0), 0);
  const idPedido = `p-${String(maior + 1).padStart(3, '0')}`;
  const pedido = {
    id: idPedido, projeto: id, projetoNome, texto: descricao, status: 'novo', missao: '', data: agora(),
    anexos: anexos.map((a) => ({ nome: a.nome, arquivo: `anexos/${idPedido}/${a.nome}`, tipo: a.tipo, tamanho: a.tamanho })),
  };
  estado.pedidos.push(pedido);
  return pedido;
}

// Só abre anexos que algum pedido (ou missão) cita, e só dentro de anexos/. Devolve o caminho e o tipo.
function anexoCitado(estado, caminho) {
  const limpo = String(caminho || '').replace(/\\/g, '/');
  if (!/^anexos\/p-\d+\/[a-z0-9][a-z0-9._-]*$/.test(limpo) || limpo.split('/').includes('..')) {
    throw new ErroEscritorio(400, 'Caminho de anexo não permitido.');
  }
  const citados = [
    ...(estado.pedidos || []).flatMap((p) => (p.anexos || []).map((a) => a && a.arquivo)),
    ...(estado.missoes || []).flatMap((m) => m.anexos || []),
  ];
  const tipo = TIPOS_ANEXO[extensaoDe(limpo)];
  if (!tipo || !citados.includes(limpo)) throw new ErroEscritorio(404, 'Anexo não encontrado.');
  return { caminho: limpo, tipo };
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

// Cabeçalhos para mostrar um anexo no navegador sem risco: tipo fixo pela extensão, sem "adivinhar" o conteúdo e,
// fora o PDF (o leitor de PDF do navegador não abre em modo isolado), numa página isolada que não roda nada.
function cabecalhosDeAnexo({ caminho, tipo }) {
  const texto = tipo.startsWith('text/');
  const cabecalhos = {
    'Content-Type': texto ? 'text/plain; charset=utf-8' : tipo,
    'Content-Disposition': `inline; filename="${caminho.split('/').pop()}"`,
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'private, max-age=86400',
  };
  if (tipo !== 'application/pdf') cabecalhos['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox";
  return cabecalhos;
}

module.exports = {
  agora, paraId, prontaParaRodar, trabalhoPendente, temTrabalho, decidir, novoPedido, caminhoDeEntrega, ErroEscritorio,
  prepararAnexos, anexoCitado, cabecalhosDeAnexo, TIPOS_ANEXO, LIMITES_ANEXOS,
};
