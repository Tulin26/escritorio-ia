// Conversa com o servidor: server.js no PC ou api/*.js no Vercel. As rotas são as mesmas nos dois.

async function pedir(url, opcoes = {}) {
  const r = await fetch(url, { cache: 'no-store', credentials: 'same-origin', ...opcoes });
  const tipo = r.headers.get('content-type') || '';
  const dados = tipo.includes('application/json') ? await r.json() : await r.text();
  if (!r.ok) {
    const erro = new Error((dados && dados.erro) || (typeof dados === 'string' && dados) || r.statusText);
    erro.status = r.status;
    throw erro;
  }
  return dados;
}

const enviar = (url, corpo) => pedir(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(corpo || {}),
});

export const api = {
  sessao: () => pedir('/api/sessao'),
  estado: () => pedir('/api/estado'),
  arquivo: (id) => pedir(`/api/arquivo?id=${encodeURIComponent(id)}`),
  pedido: (projeto, texto) => enviar('/api/pedido', { projeto, texto }),
  decisao: (id, acao, comentario) => enviar('/api/decisao', { id, acao, comentario }),
  rodada: () => enviar('/api/rodada'),
  login: (senha) => enviar('/api/login', { senha }),
  logout: () => enviar('/api/logout'),
};
