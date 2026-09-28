// Salas, visual dos agentes e contas feitas a partir do estado.json.

export const STATUS = ['backlog', 'rodando', 'aguardando', 'aprovado', 'refazer'];

export const ROTULO_STATUS = {
  backlog: 'na fila', rodando: 'trabalhando', aguardando: 'esperando você', aprovado: 'aprovado', refazer: 'refazendo',
};

// Pisos quadriculados: [cor 1, cor 2, borda, parede]
export const PISOS = {
  roxo: ['#5b3f8c', '#684c9c', '#2a1b47', '#3b2a5c'],
  verde: ['#3d7447', '#488553', '#1c3a22', '#2a4f31'],
  azul: ['#37569a', '#4263aa', '#1a2b4f', '#25396a'],
  marrom: ['#74502f', '#835c3a', '#3a2716', '#4f3620'],
  turquesa: ['#2a8584', '#349796', '#134242', '#1d5b5a'],
  vinho: ['#7a3446', '#883d51', '#3a1520', '#55222f'],
  cinza: ['#4a4e5c', '#555a69', '#1f2129', '#34373f'],
  bege: ['#8a7456', '#977f60', '#3f3222', '#5c4b35'],
  rosa: ['#8c3f6e', '#9a4a7b', '#3f1a31', '#5e2a4a'],
  laranja: ['#8a5a2a', '#976433', '#40290f', '#5c3d1c'],
  grafite: ['#2d3340', '#353c4b', '#12151c', '#1f2430'],
};

// Salas do escritório. As de agentes listam quem senta nelas; um agente do estado.json cujo campo "sala" tenha o
// nome de uma sala também entra nela (assim uma sala pode virar um time com vários agentes).
// Salas especiais: reunião (pauta do último pedido), você (sua mesa), recepção (pedidos na fila), memória e Git & GitHub
// (guarda o trabalho no GitHub; quem faz é o servidor do painel, não um agente do Claude).
export const SALAS = [
  { id: 'reu', nome: 'Sala de Reunião', piso: 'bege', tipo: 'reuniao' },
  { id: 'dir', agentes: ['diretor'], nome: 'Diretoria', piso: 'marrom', deco: 'diretoria' },
  { id: 'voc', nome: 'Você', piso: 'cinza', tipo: 'voce' },
  { id: 'rec', nome: 'Recepção', piso: 'bege', tipo: 'recepcao' },
  { id: 'pes', agentes: ['pesquisador'], nome: 'Pesquisa', piso: 'verde', deco: 'pesquisa' },
  { id: 'est', agentes: ['estrategista'], nome: 'Estratégia', piso: 'azul', deco: 'estrategia' },
  { id: 'des', agentes: ['designer'], nome: 'Marca & Design', piso: 'rosa', deco: 'design' },
  { id: 'cop', agentes: ['copywriter'], nome: 'Copy', piso: 'roxo', deco: 'copy' },
  { id: 'soc', agentes: ['social'], nome: 'Social', piso: 'turquesa', deco: 'social' },
  { id: 'tra', agentes: ['trafego'], nome: 'Tráfego & Mídia', piso: 'laranja', deco: 'trafego' },
  { id: 'ven', agentes: ['vendas'], nome: 'Vendas', piso: 'vinho', deco: 'vendas' },
  { id: 'rev', agentes: ['revisor'], nome: 'Revisão', piso: 'roxo', deco: 'revisao' },
  { id: 'git', nome: 'Git & GitHub', piso: 'grafite', tipo: 'git', deco: 'git' },
  { id: 'mem', nome: 'Memória', piso: 'azul', tipo: 'memoria' },
];

export const VISUAL = {
  diretor: { cabelo: '#2b1d14', pele: '#e0a878', roupa: '#2f3f73' },
  pesquisador: { cabelo: '#7a4a24', pele: '#f1c29a', roupa: '#3f8a4f' },
  estrategista: { cabelo: '#15131c', pele: '#c98c5e', roupa: '#4a5fc1' },
  designer: { cabelo: '#e8d44d', pele: '#d9a074', roupa: '#1f1f2e' },
  copywriter: { cabelo: '#c4662a', pele: '#f3cfa8', roupa: '#9b3fa0' },
  social: { cabelo: '#5c2a6e', pele: '#e8b48c', roupa: '#e0567f' },
  trafego: { cabelo: '#1c1410', pele: '#8d5a32', roupa: '#e07a2f' },
  vendas: { cabelo: '#3a2616', pele: '#a8703f', roupa: '#2f9c8a' },
  revisor: { cabelo: '#9a9aa8', pele: '#f0c8a0', roupa: '#5b5f6e' },
  git: { cabelo: '#24292f', pele: '#c68642', roupa: '#f05033' },
};
export const VISUAL_PADRAO = { cabelo: '#333', pele: '#e0b090', roupa: '#777' };

// O que aparece no balão de quem está trabalhando.
export const VERBO = {
  diretor: 'Delegando', pesquisador: 'Pesquisando', estrategista: 'Traçando', designer: 'Desenhando',
  copywriter: 'Escrevendo', social: 'Criando posts', trafego: 'Analisando', vendas: 'Prospectando', revisor: 'Revisando',
};

// Como cada agente trabalha, em 3 passos (aparece na ficha de cada um).
export const COMO_TRABALHA = {
  diretor: [
    'Recebe o seu pedido, lê o briefing do projeto e os anexos (cria o briefing se ainda não existir).',
    'Manda direto para a sala que entrega o que você pediu: post vai para Social, texto para Copy, tela para Design. A Pesquisa só entra se faltar dado de fora.',
    'Manda o plano para a sua mesa. Nenhuma sala começa antes de você aprovar.',
  ],
  pesquisador: [
    'Pesquisa na internet mercado, concorrentes, público, preços e palavras-chave.',
    'Separa fato, inferência e recomendação, sempre com link e data da fonte.',
    'Termina com uma decisão recomendada, não só um resumo.',
  ],
  estrategista: [
    'Lê a pesquisa aprovada e define para quem, qual promessa e por que você e não a concorrência.',
    'Escolhe o ângulo da campanha, os canais e a meta de cada etapa do funil.',
    'Lista as peças que Copy, Social e Vendas vão produzir, em ordem de prioridade.',
  ],
  designer: [
    'Define a identidade visual e desenha telas de site, app e landing page com a skill UI UX Pro Max.',
    'Entrega briefs de criação com medidas certas para cada rede e prompts prontos para gerar imagens.',
    'Não usa imagem de terceiros sem licença e confere se o texto sobre a imagem dá para ler.',
  ],
  trafego: [
    'Planeja campanhas pagas (Meta e Google): objetivo, público, orçamento, estrutura e metas.',
    'Analisa os números que você trouxer: saúde da conta, 7 e 30 dias, melhores e piores anúncios, criativos cansados.',
    'Nunca mexe na conta nem gasta: tudo vira proposta com valores exatos para você aprovar e executar.',
  ],
  copywriter: [
    'Monta o perfil de voz da marca a partir de textos reais do briefing.',
    'Escreve 2 ou 3 variações de cada peça e indica a recomendada.',
    'Nunca inventa preço, prazo ou depoimento: o que falta vira [PREENCHER].',
  ],
  social: [
    'Transforma a estratégia em posts, carrosséis e roteiros de vídeo curtos.',
    'Adapta o formato para cada rede e monta o calendário com datas sugeridas.',
    'Não publica nada: você posta depois de aprovar.',
  ],
  vendas: [
    'Monta listas de prospects só com dados públicos de empresas.',
    'Escreve rascunhos de mensagens, propostas e follow-ups no seu tom.',
    'Nunca envia: cada mensagem tem código, destinatário e texto exato para você aprovar.',
  ],
  revisor: [
    'Confere as entregas das outras salas antes de chegarem até você.',
    'Dá nota de 1 a 5 em precisão, completude, clareza, ação e concisão, refazendo contas e checando fontes.',
    'Aponta erros e riscos com a correção sugerida. Quem decide é você.',
  ],
  git: [
    'Junta tudo o que mudou na pasta do escritório: entregas, anexos e o estado.json.',
    'Faz um commit com o motivo (ex.: "rodada da equipe", "aprovou m-004") e traz antes o que chegou do painel online.',
    'Envia para o GitHub. Ligado, faz isso sozinho depois de cada rodada e decisão; desligado, só quando você clicar em Enviar agora.',
  ],
};

// Anexos: o que o painel aceita (o servidor confere de novo) e como mostrar o tamanho.
export const EXTENSOES_ANEXO = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'md', 'csv', 'json'];
// No PC cabe bem mais; online o Vercel aceita no máximo uns 4 MB por envio (mesmos números de lib/escritorio.js).
export const LIMITES_ANEXOS = {
  pc: { quantidade: 10, porArquivo: 25 * 1024 * 1024, bytes: 50 * 1024 * 1024 },
  nuvem: { quantidade: 5, porArquivo: 3 * 1024 * 1024, bytes: 3 * 1024 * 1024 },
};
export const extensaoDe = (nome) => {
  const i = String(nome || '').lastIndexOf('.');
  return i > 0 ? nome.slice(i + 1).toLowerCase() : '';
};
export const ehImagem = (nome) => ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(extensaoDe(nome));
export function tamanhoLegivel(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  const mb = bytes / 1024 / 1024;
  return Number.isInteger(mb) ? `${mb} MB` : `${mb.toFixed(1).replace('.', ',')} MB`;
}

export const missoesDe = (estado, agenteId) => (estado.missoes || []).filter((m) => m.agente === agenteId);
export const xpDe = (lista) => lista.filter((m) => m.status === 'aprovado').reduce((t, m) => t + (Number(m.xp) || 0), 0);
export const nivelDe = (xp) => 1 + Math.floor(xp / 100);
export const nomeAgente = (estado, id) => ((estado.agentes || []).find((a) => a.id === id) || {}).nome || id;

export function situacao(lista) {
  if (lista.some((m) => m.status === 'rodando' || m.status === 'refazer')) return 'rodando';
  if (lista.some((m) => m.status === 'aguardando')) return 'aguardando';
  return 'livre';
}
export const ROTULO_SITUACAO = { rodando: 'trabalhando', aguardando: 'esperando sua aprovação', livre: 'livre' };

// Ordena datas "AAAA-MM-DD HH:MM" da mais nova para a mais antiga.
export const maisRecentes = (a, b) => String(b.data || '').localeCompare(String(a.data || ''));

// Fases do dia pela hora local: cor do céu nas janelas, quanto as salas escurecem e se as luminárias acendem.
export function faseDoDia(hora) {
  if (hora < 5) return { id: 'madrugada', nome: 'madrugada', escuro: 0.46, lampada: 1, astro: 'lua' };
  if (hora < 7) return { id: 'amanhecer', nome: 'amanhecer', escuro: 0.16, lampada: 0.4, astro: 'sol' };
  if (hora < 17) return { id: 'dia', nome: 'dia', escuro: 0, lampada: 0, astro: 'sol' };
  if (hora < 19) return { id: 'entardecer', nome: 'fim de tarde', escuro: 0.2, lampada: 0.6, astro: 'sol' };
  return { id: 'noite', nome: 'noite', escuro: 0.38, lampada: 1, astro: 'lua' };
}
