// Arquivos escolhidos para um pedido, soltos ou de dentro de pastas: { arquivo (File), caminho ("tcc/cap-1/texto.pdf") }.

// Fora do pedido: a pasta interna do Git (histórico, não conteúdo) e o lixo que o sistema cria sozinho.
const LIXO = new Set(['thumbs.db', 'desktop.ini', '.ds_store']);
export const ignorar = (caminho) => {
  const partes = caminho.split('/');
  return partes.includes('.git') || LIXO.has(partes[partes.length - 1].toLowerCase());
};

// File de um <input> (com "Escolher pasta" ele traz webkitRelativePath) ou item já pronto.
export const comCaminho = (item) => (item instanceof File ? { arquivo: item, caminho: item.webkitRelativePath || item.name } : item);

// Arrastar e soltar: o navegador entrega a pasta, não o que tem dentro; aqui entra nas pastas e subpastas.
// Os itens só valem durante o evento de soltar: a lista é lida antes do primeiro "await".
export async function arquivosDoArraste(dataTransfer) {
  const entradas = [...(dataTransfer.items || [])]
    .filter((i) => i.kind === 'file')
    .map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null));
  if (!entradas.length || entradas.some((e) => !e)) return [...dataTransfer.files].map(comCaminho);
  const saida = [];
  async function visitar(entrada, prefixo) {
    if (entrada.isFile) {
      const arquivo = await new Promise((ok, erro) => entrada.file(ok, erro));
      saida.push({ arquivo, caminho: prefixo + arquivo.name });
      return;
    }
    const leitor = entrada.createReader();
    // readEntries devolve aos poucos (uns 100 de cada vez): lê até vir vazio.
    for (;;) {
      const parte = await new Promise((ok, erro) => leitor.readEntries(ok, erro));
      if (!parte.length) break;
      for (const filho of parte) await visitar(filho, `${prefixo}${entrada.name}/`);
    }
  }
  for (const entrada of entradas) await visitar(entrada, '');
  return saida;
}
