// Sala Git & GitHub no PC: guarda a pasta do escritório no GitHub (commit + push) usando só comandos fixos do git,
// sem terminal e sem nada vindo do painel na linha de comando. Quem decide quando enviar é o server.js: pelo botão
// "Enviar agora" ou, com o envio automático ligado, depois de cada rodada e de cada decisão sua.
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const { agora } = require('./escritorio');

const LIMITE_MS = 90 * 1000; // cada comando do git (push lento, internet ruim)
const CACHE_MS = 4000; // o painel pergunta o status a cada 3 s; o git status não precisa rodar tanto
const IDENTIDADE_PADRAO = { nome: 'Escritório de IA', email: 'escritorio-ia@localhost' };

// Tira usuário e senha/token de um endereço antes de mostrar no painel.
function enderecoSeguro(url) {
  const texto = String(url || '').trim();
  if (/^([a-z]:[\\/]|\/|\.)/i.test(texto)) return texto; // pasta no próprio PC (ex.: o GitHub de mentira dos testes)
  try {
    const u = new URL(texto);
    u.username = '';
    u.password = '';
    return `${u.host}${u.pathname}`.replace(/\.git$/, '');
  } catch {
    // git@github.com:dono/repo.git
    return texto.replace(/^[^@\s]+@/, '').replace(':', '/').replace(/\.git$/, '');
  }
}

// Mensagem de erro do git em uma linha curta, sem endereços com senha.
const limparSaida = (texto) => String(texto || '')
  .replace(/https?:\/\/[^\s@/]+@/g, 'https://')
  .split('\n').map((l) => l.replace(/^(error|fatal|hint|remote):\s*/i, '').trim()).filter(Boolean)
  .slice(0, 3).join(' ')
  .slice(0, 400);

const ehConflito = (codigo) => /^(DD|AU|UD|UA|DU|AA|UU)$/.test(codigo);
const mesmaPasta = (a, b) => {
  const real = (p) => {
    try {
      return fs.realpathSync.native(p);
    } catch {
      return path.resolve(p);
    }
  };
  const [x, y] = [real(a), real(b)];
  return process.platform === 'win32' ? x.toLowerCase() === y.toLowerCase() : x === y;
};

function criarGit(raiz, { remoto = 'origin', env = {} } = {}) {
  const ambiente = { ...process.env, GIT_TERMINAL_PROMPT: '0', ...env };
  const sala = { enviando: false, ultimo: null };
  let cache = null;

  function git(args, { permitirErro = false, extra = {} } = {}) {
    return new Promise((resolve, reject) => {
      execFile('git', args, {
        cwd: raiz, env: { ...ambiente, ...extra }, timeout: LIMITE_MS, windowsHide: true, maxBuffer: 16 * 1024 * 1024,
      }, (erro, saida, saidaErro) => {
        if (erro && !permitirErro) {
          const e = new Error(erro.code === 'ENOENT'
            ? 'o Git não está instalado (ou o comando "git" não funciona no terminal)'
            : limparSaida(saidaErro) || limparSaida(erro.message) || `o git terminou com erro (${args[0]})`);
          e.semGit = erro.code === 'ENOENT';
          return reject(e);
        }
        resolve({ ok: !erro, saida: String(saida), erro: String(saidaErro) });
      });
    });
  }

  // Lê como está a pasta: se dá para enviar, para onde e o que está esperando.
  async function lerStatus() {
    const vazio = { disponivel: false, motivo: '', ramo: '', remoto: '', pendentes: 0, arquivos: [], adiante: 0 };
    let topo;
    try {
      topo = (await git(['rev-parse', '--show-toplevel'])).saida.trim();
    } catch (e) {
      return { ...vazio, motivo: e.semGit ? e.message : 'esta pasta não é um repositório Git (baixe o escritório com git clone)' };
    }
    if (!mesmaPasta(topo, raiz)) {
      return { ...vazio, motivo: 'a pasta do escritório está dentro de outro repositório Git; por segurança, nada é enviado' };
    }
    const ramo = (await git(['symbolic-ref', '--quiet', '--short', 'HEAD'], { permitirErro: true })).saida.trim();
    if (!ramo) return { ...vazio, motivo: 'o Git está num commit solto, fora de um ramo; volte para o main no terminal' };
    const url = (await git(['remote', 'get-url', remoto], { permitirErro: true })).saida.trim();
    if (!url) return { ...vazio, ramo, motivo: `não há um remoto "${remoto}" configurado (o endereço do GitHub)` };

    const bruto = (await git(['status', '--porcelain=v1', '-z', '--untracked-files=all'])).saida.split('\0');
    const arquivos = [];
    let conflito = false;
    for (let i = 0; i < bruto.length; i++) {
      const linha = bruto[i];
      if (linha.length < 4) continue;
      const codigo = linha.slice(0, 2);
      if (ehConflito(codigo)) conflito = true;
      arquivos.push(linha.slice(3));
      if (codigo[0] === 'R' || codigo[0] === 'C') i++; // renomeado: o próximo item é o nome antigo
    }
    let adiante = 0;
    const rastreio = `refs/remotes/${remoto}/${ramo}`;
    if ((await git(['rev-parse', '--verify', '--quiet', rastreio], { permitirErro: true })).ok) {
      adiante = Number((await git(['rev-list', '--count', `${rastreio}..HEAD`])).saida.trim()) || 0;
    }
    const base = { disponivel: true, motivo: '', ramo, remoto: enderecoSeguro(url), pendentes: arquivos.length, arquivos: arquivos.slice(0, 20), adiante };
    if (conflito) return { ...base, disponivel: false, motivo: 'há um conflito do Git pela metade nesta pasta; resolva no terminal (git status)' };
    return base;
  }

  // Status com cache curto, mais o que a sala está fazendo e como foi o último envio.
  async function resumo() {
    if (!cache || Date.now() - cache.quando > CACHE_MS) {
      try {
        cache = { quando: Date.now(), status: await lerStatus() };
      } catch (e) {
        cache = { quando: Date.now(), status: { disponivel: false, motivo: e.message, ramo: '', remoto: '', pendentes: 0, arquivos: [], adiante: 0 } };
      }
    }
    return { ...cache.status, enviando: sala.enviando, ultimo: sala.ultimo };
  }

  const invalidar = () => { cache = null; };

  // Se o PC não tem nome e e-mail configurados no Git, o commit sai assinado como "Escritório de IA".
  async function identidade() {
    const nome = (await git(['config', 'user.name'], { permitirErro: true })).saida.trim();
    const email = (await git(['config', 'user.email'], { permitirErro: true })).saida.trim();
    const n = nome || IDENTIDADE_PADRAO.nome;
    const e = email || IDENTIDADE_PADRAO.email;
    return { GIT_AUTHOR_NAME: n, GIT_AUTHOR_EMAIL: e, GIT_COMMITTER_NAME: n, GIT_COMMITTER_EMAIL: e };
  }

  // Commit de tudo o que mudou na pasta + push para o mesmo ramo no GitHub. Se o GitHub tiver commits novos
  // (ex.: decisões feitas no painel online), eles entram antes e os do PC vão por cima (rebase).
  // "conferir" roda antes de tudo: se lançar erro, nada é enviado.
  async function enviar(motivo, { conferir } = {}) {
    if (sala.enviando) {
      const e = new Error('o Git já está enviando; espere terminar');
      e.ocupado = true;
      throw e;
    }
    sala.enviando = true;
    const inicio = Date.now();
    try {
      if (conferir) await conferir();
      invalidar();
      const s = await lerStatus();
      if (!s.disponivel) throw new Error(s.motivo);
      const extra = await identidade();
      const mensagem = `Escritório: ${String(motivo || 'envio').replace(/[\u0000-\u001f\u007f]+/g, ' ').trim()}`.slice(0, 150);
      if (s.pendentes) {
        await git(['add', '-A']);
        await git(['commit', '--quiet', '-m', mensagem], { extra });
      }
      const rastreio = `refs/remotes/${remoto}/${s.ramo}`;
      const existe = (await git(['ls-remote', '--heads', remoto, `refs/heads/${s.ramo}`], { extra })).saida.trim();
      if (existe) {
        await git(['fetch', '--quiet', remoto, `+refs/heads/${s.ramo}:${rastreio}`], { extra });
        const atras = Number((await git(['rev-list', '--count', `HEAD..${rastreio}`])).saida.trim()) || 0;
        if (atras) {
          const rebase = await git(['rebase', '--quiet', '--autostash', rastreio], { permitirErro: true, extra });
          if (!rebase.ok) {
            await git(['rebase', '--abort'], { permitirErro: true, extra });
            throw new Error('o GitHub tem mudanças que batem de frente com as do PC (provavelmente no estado.json). '
              + 'Nada foi perdido: seus commits continuam no PC. Resolva no terminal com "git pull --rebase" e depois clique em Enviar agora.');
          }
        }
      }
      const faltando = existe
        ? Number((await git(['rev-list', '--count', `${rastreio}..HEAD`])).saida.trim()) || 0
        : 1;
      if (!faltando) {
        sala.ultimo = { data: agora(), ok: true, erro: '', commit: '', resumo: 'Nada novo: o GitHub já tem tudo.', segundos: segundosDesde(inicio) };
        return sala.ultimo;
      }
      await git(['push', '--quiet', remoto, `HEAD:refs/heads/${s.ramo}`], { extra });
      const commit = (await git(['rev-parse', '--short', 'HEAD'])).saida.trim();
      const arquivos = s.pendentes ? `${s.pendentes} arquivo(s)` : 'commits que estavam no PC';
      sala.ultimo = {
        data: agora(), ok: true, erro: '', commit,
        resumo: `Enviado para ${s.remoto} (${s.ramo}): ${arquivos}.`, segundos: segundosDesde(inicio),
      };
      return sala.ultimo;
    } catch (e) {
      sala.ultimo = { data: agora(), ok: false, erro: e.message, commit: '', resumo: '', segundos: segundosDesde(inicio) };
      throw e;
    } finally {
      sala.enviando = false;
      invalidar();
    }
  }

  return { resumo, enviar, invalidar, get enviando() { return sala.enviando; } };
}

const segundosDesde = (inicio) => Math.round((Date.now() - inicio) / 100) / 10;

module.exports = { criarGit, enderecoSeguro };
