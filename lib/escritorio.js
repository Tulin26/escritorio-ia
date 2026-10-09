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
// Arquivos (e pastas inteiras) que o dono manda junto com o pedido. Ficam em anexos/<id do pedido>/, com as subpastas.
// Qualquer tipo entra. O tipo guardado só decide como o painel mostra o arquivo: imagem e PDF de verdade (conferidos
// pelo conteúdo) abrem no navegador, texto abre como texto puro e o resto é baixado.
const TIPOS_ANEXO = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp',
  pdf: 'application/pdf', txt: 'text/plain', md: 'text/markdown', csv: 'text/csv', json: 'application/json',
};
const BINARIO = 'application/octet-stream';
const TIPOS_CONHECIDOS = new Set([...Object.values(TIPOS_ANEXO), BINARIO]);
// No PC não há limite: o painel manda arquivo por arquivo. Online o Vercel aceita no máximo 4,5 MB por chamada:
// 3 MB em arquivos viram uns 4 MB em base64.
const LIMITES_ANEXOS = {
  pc: { quantidade: Infinity, porArquivo: Infinity, bytes: Infinity },
  nuvem: { quantidade: 5, porArquivo: 3 * 1024 * 1024, bytes: 3 * 1024 * 1024 },
};
// O GitHub recusa arquivo acima de 100 MB: os maiores que isto ficam só no PC (fora do envio), para o push não travar.
const LIMITE_GITHUB = 95 * 1024 * 1024;
const emMB = (bytes) => `${Math.round(bytes / (1024 * 1024))} MB`;

// O começo de cada arquivo precisa bater com o tipo para abrir no navegador: um .png tem de ser mesmo um PNG.
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

// Tipo de um anexo pelo nome e pelo começo do conteúdo (bastam os primeiros 8 KB).
function tipoDeAnexo(nome, inicio) {
  const ext = extensaoDe(nome);
  const confere = ASSINATURAS[ext];
  if (confere) return confere(inicio) ? TIPOS_ANEXO[ext] : BINARIO;
  if (!ehTexto(inicio)) return BINARIO;
  return TIPOS_ANEXO[ext] || 'text/plain';
}

// Nome simples e seguro (sem acentos nem espaços), mantendo a extensão.
function nomeSeguro(original) {
  const nome = String(original || '').trim();
  const ext = paraId(extensaoDe(nome)).slice(0, 10);
  const base = paraId(ext ? nome.slice(0, nome.lastIndexOf('.')) : nome).slice(0, 50).replace(/-+$/, '') || 'anexo';
  return ext ? `${base}.${ext}` : base;
}

// Caminho dentro da pasta do pedido: mantém as subpastas (cada parte com nome seguro) e nunca sai dela ("..", "C:\").
function caminhoDeAnexo(original) {
  const partes = String(original || '').split(/[\\/]+/).map((p) => p.trim()).filter((p) => p && p !== '.' && p !== '..');
  if (!partes.length) return 'anexo';
  const arquivo = nomeSeguro(partes.pop());
  return [...partes.map((p) => paraId(p) || 'pasta'), arquivo].join('/');
}

// Dois arquivos com o mesmo nome no mesmo pedido: foto.jpg, foto-2.jpg…
const comNumero = (caminho, n) => (n < 2 ? caminho : caminho.replace(/(\.[^./]+)?$/, `-${n}$1`));

// Confere a lista que veio do painel ({ nome ou caminho, dados em base64 }) e devolve os arquivos prontos para gravar.
// "nome" é um arquivo solto (fica na raiz do pedido); "caminho" é um arquivo de pasta (mantém as subpastas).
// Sem "limites", vale o do painel online (o menor); o server.js do PC passa LIMITES_ANEXOS.pc.
function prepararAnexos(lista, limites = LIMITES_ANEXOS.nuvem) {
  if (lista === undefined || lista === null) return [];
  if (!Array.isArray(lista)) throw new ErroEscritorio(400, 'anexos inválidos');
  if (lista.length > limites.quantidade) throw new ErroEscritorio(400, `mande no máximo ${limites.quantidade} anexos por pedido`);
  const usados = new Set();
  let total = 0;
  return lista.map((item) => {
    const rotulo = String((item && (item.caminho || item.nome)) || 'sem nome').slice(0, 80);
    const dados = String((item && item.dados) || '');
    if (dados && !/^[A-Za-z0-9+/]+={0,2}$/.test(dados)) throw new ErroEscritorio(400, `o anexo "${rotulo}" chegou corrompido`);
    const conteudo = Buffer.from(dados, 'base64');
    total += conteudo.length;
    if (conteudo.length > limites.porArquivo) throw new ErroEscritorio(413, `o anexo "${rotulo}" passa de ${emMB(limites.porArquivo)}`);
    if (total > limites.bytes) throw new ErroEscritorio(413, `os anexos passam de ${emMB(limites.bytes)} no total; mande arquivos menores`);
    const sugerido = item && item.caminho
      ? caminhoDeAnexo(item.caminho)
      : nomeSeguro(String((item && item.nome) || '').split(/[\\/]/).pop());
    let nome = sugerido;
    for (let n = 2; usados.has(nome); n++) nome = comNumero(sugerido, n);
    usados.add(nome);
    return { nome, tipo: tipoDeAnexo(nome, conteudo.subarray(0, 8192)), tamanho: conteudo.length, conteudo };
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
  // Quando o placar é zerado, os pedidos antigos vão para historico/ e "numeracao" guarda o último número já usado.
  const usado = Number((estado.numeracao || {}).pedido) || 0;
  const maior = estado.pedidos.reduce((n, p) => Math.max(n, Number(String(p.id).replace(/\D/g, '')) || 0), usado);
  const idPedido = `p-${String(maior + 1).padStart(3, '0')}`;
  const pedido = {
    id: idPedido, projeto: id, projetoNome, texto: descricao, status: 'novo', missao: '', data: agora(),
    anexos: anexos.map((a) => ({ nome: a.nome, arquivo: `anexos/${idPedido}/${a.nome}`, tipo: a.tipo, tamanho: a.tamanho })),
  };
  estado.pedidos.push(pedido);
  return pedido;
}

// Só abre anexos que algum pedido (ou missão) cita, e só dentro de anexos/. Devolve o caminho e o tipo.
// Uma missão pode citar uma pasta inteira do pedido (terminando em "/"): vale para os arquivos dentro dela.
// O tipo vem do pedido, que conferiu o conteúdo ao receber; sem ele, o arquivo só é baixado, nunca aberto.
function anexoCitado(estado, caminho) {
  const limpo = String(caminho || '').replace(/\\/g, '/');
  if (!/^anexos\/p-\d+(\/[a-z0-9][a-z0-9._-]*)+$/.test(limpo) || limpo.split('/').includes('..')) {
    throw new ErroEscritorio(400, 'Caminho de anexo não permitido.');
  }
  const doPedido = (estado.pedidos || []).flatMap((p) => p.anexos || []).find((a) => a && a.arquivo === limpo);
  const daMissao = (estado.missoes || []).flatMap((m) => m.anexos || [])
    .some((c) => typeof c === 'string' && (c === limpo || (c.endsWith('/') && limpo.startsWith(c))));
  if (!doPedido && !daMissao) throw new ErroEscritorio(404, 'Anexo não encontrado.');
  const tipo = doPedido && TIPOS_CONHECIDOS.has(doPedido.tipo) ? doPedido.tipo : BINARIO;
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

// Cabeçalhos para mostrar um anexo no navegador sem risco: tipo fixo, sem "adivinhar" o conteúdo e, fora o PDF
// (o leitor de PDF do navegador não abre em modo isolado), numa página isolada que não roda nada.
// O que não é imagem, PDF nem texto (Word, planilha, ZIP, programa…) é só baixado.
function cabecalhosDeAnexo({ caminho, tipo }) {
  const texto = tipo.startsWith('text/');
  const cabecalhos = {
    'Content-Type': texto ? 'text/plain; charset=utf-8' : tipo,
    'Content-Disposition': `${tipo === BINARIO ? 'attachment' : 'inline'}; filename="${caminho.split('/').pop()}"`,
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'private, max-age=86400',
  };
  if (tipo !== 'application/pdf') cabecalhos['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox";
  return cabecalhos;
}

module.exports = {
  agora, paraId, prontaParaRodar, trabalhoPendente, temTrabalho, decidir, novoPedido, caminhoDeEntrega, ErroEscritorio,
  prepararAnexos, anexoCitado, cabecalhosDeAnexo, caminhoDeAnexo, tipoDeAnexo, comNumero, TIPOS_ANEXO, LIMITES_ANEXOS,
  LIMITE_GITHUB,
};
