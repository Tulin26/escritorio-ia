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
};

// Uma sala por área; "mem" (Memória) não tem agente: guarda briefings e entregas aprovadas.
export const SALAS = [
  { id: 'dir', agente: 'diretor', nome: 'Diretoria', piso: 'marrom', deco: 'diretoria' },
  { id: 'pes', agente: 'pesquisador', nome: 'Pesquisa', piso: 'verde', deco: 'pesquisa' },
  { id: 'est', agente: 'estrategista', nome: 'Estratégia', piso: 'azul', deco: 'estrategia' },
  { id: 'cop', agente: 'copywriter', nome: 'Copy', piso: 'roxo', deco: 'copy' },
  { id: 'soc', agente: 'social', nome: 'Social', piso: 'turquesa', deco: 'social' },
  { id: 'ven', agente: 'vendas', nome: 'Vendas', piso: 'vinho', deco: 'vendas' },
  { id: 'rev', agente: 'revisor', nome: 'Revisão', piso: 'roxo', deco: 'revisao' },
  { id: 'mem', agente: null, nome: 'Memória', piso: 'azul', deco: 'memoria' },
];

export const VISUAL = {
  diretor: { cabelo: '#2b1d14', pele: '#e0a878', roupa: '#2f3f73' },
  pesquisador: { cabelo: '#7a4a24', pele: '#f1c29a', roupa: '#3f8a4f' },
  estrategista: { cabelo: '#15131c', pele: '#c98c5e', roupa: '#4a5fc1' },
  copywriter: { cabelo: '#c4662a', pele: '#f3cfa8', roupa: '#9b3fa0' },
  social: { cabelo: '#5c2a6e', pele: '#e8b48c', roupa: '#e0567f' },
  vendas: { cabelo: '#3a2616', pele: '#a8703f', roupa: '#2f9c8a' },
  revisor: { cabelo: '#9a9aa8', pele: '#f0c8a0', roupa: '#5b5f6e' },
};
export const VISUAL_PADRAO = { cabelo: '#333', pele: '#e0b090', roupa: '#777' };

// Como cada agente trabalha, em 3 passos (aparece na ficha de cada um).
export const COMO_TRABALHA = {
  diretor: [
    'Recebe o seu pedido e lê o briefing do projeto (cria o briefing se ainda não existir).',
    'Divide o trabalho em 3 a 7 missões, uma por sala, com ordem, dependências e critério de aceite.',
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
};

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
