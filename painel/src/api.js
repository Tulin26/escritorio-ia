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

// Endereço de um anexo (imagem, PDF ou texto) para miniaturas e links.
export const urlAnexo = (caminho) => `/api/anexo?caminho=${encodeURIComponent(caminho)}`;

export const api = {
  sessao: () => pedir('/api/sessao'),
  estado: () => pedir('/api/estado'),
  arquivo: (id) => pedir(`/api/arquivo?id=${encodeURIComponent(id)}`),
  pedido: (projeto, texto, anexos) => enviar('/api/pedido', { projeto, texto, anexos }),
  decisao: (id, acao, comentario) => enviar('/api/decisao', { id, acao, comentario }),
  rodada: () => enviar('/api/rodada'),
  ligarGit: (ligado) => enviar('/api/git', { ligado }),
  enviarGit: () => enviar('/api/git/enviar'),
  criarRepo: (id) => enviar('/api/projeto/repo', { id }),
  enviarRepo: (id) => enviar('/api/projeto/repo/enviar', { id }),
  login: (senha) => enviar('/api/login', { senha }),
  logout: () => enviar('/api/logout'),
};
