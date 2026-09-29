// Repositórios dos projetos: cada projeto pode ganhar uma pasta própria FORA do escritório (padrão:
// <sua pasta de usuário>/projetos/<id>) com um repositório privado só dele no GitHub, para o código do projeto
// não se misturar com o repositório do escritório. Quem cria o repositório no GitHub é o GitHub CLI (gh), com o login
// que você fez uma vez no PC (gh auth login). Só comandos fixos, nada vindo do painel na linha de comando além do id do
// projeto, que é conferido antes.
const { execFile } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { criarGit } = require('./git');
const { agora, ErroEscritorio } = require('./escritorio');

const LIMITE_MS = 120 * 1000;
const CACHE_GH_MS = 30 * 1000;
const ID_VALIDO = /^[a-z0-9][a-z0-9._-]{0,99}$/;
const IDENTIDADE_PADRAO = { nome: 'Escritório de IA', email: 'escritorio-ia@localhost' };

const GITIGNORE = `# Dependências e builds
node_modules/
dist/
build/
.next/
vendor/

# Segredos e configurações locais
.env
.env.*
!.env.example

# Sistema
.DS_Store
Thumbs.db
desktop.ini
`;

const limpar = (texto) => String(texto || '')
  .replace(/https?:\/\/[^\s@/]+@/g, 'https://')
  .split('\n').map((l) => l.replace(/^(error|fatal|hint|remote|x|!)\s*:?\s*/i, '').trim()).filter(Boolean)
  .slice(0, 3).join(' ')
  .slice(0, 400);

// gh: comando do GitHub CLI. Nos testes vira [node, gh-de-mentira.js].
function criarRepos({ raiz, pastaProjetos, gh = ['gh'], env = {} } = {}) {
  const base = pastaProjetos || process.env.ESCRITORIO_PROJETOS || path.join(os.homedir(), 'projetos');
  const ambiente = { ...process.env, GIT_TERMINAL_PROMPT: '0', GH_PROMPT_DISABLED: '1', ...env };
  const salas = new Map(); // pasta -> criarGit(pasta)
  let criando = '';
  let cacheGh = null;

  function rodar(bin, args, { cwd = raiz, permitirErro = false, extra = {} } = {}) {
    return new Promise((resolve, reject) => {
      execFile(bin, args, {
        cwd, env: { ...ambiente, ...extra }, timeout: LIMITE_MS, windowsHide: true, maxBuffer: 8 * 1024 * 1024,
      }, (erro, saida, saidaErro) => {
        if (erro && !permitirErro) {
          const e = new Error(limpar(saidaErro) || limpar(erro.message) || `${args[0]} terminou com erro`);
          e.naoInstalado = erro.code === 'ENOENT';
          return reject(e);
        }
        resolve({ ok: !erro, saida: String(saida), erro: String(saidaErro), naoInstalado: Boolean(erro && erro.code === 'ENOENT') });
      });
    });
  }
  const rodarGh = (args, opcoes) => rodar(gh[0], [...gh.slice(1), ...args], opcoes);
  const rodarGit = (cwd, args, opcoes = {}) => rodar('git', args, { ...opcoes, cwd });

  // O GitHub CLI está instalado e com login? (guardado por 30 s: o painel pergunta a cada 3 s)
  async function statusGh() {
    if (cacheGh && Date.now() - cacheGh.quando < CACHE_GH_MS) return cacheGh.status;
    let status;
    const versao = await rodarGh(['--version'], { permitirErro: true });
    if (versao.naoInstalado) {
      status = { pronto: false, conta: '', motivo: 'o GitHub CLI (gh) não está instalado. No PowerShell: winget install --id GitHub.cli, depois gh auth login, e reinicie o painel.' };
    } else {
      const conta = await rodarGh(['api', 'user', '--jq', '.login'], { permitirErro: true });
      status = conta.ok && conta.saida.trim()
        ? { pronto: true, conta: conta.saida.trim(), motivo: '' }
        : { pronto: false, conta: '', motivo: 'o GitHub CLI não está com login. No PowerShell: gh auth login (escolha GitHub.com e HTTPS).' };
    }
    cacheGh = { quando: Date.now(), status };
    return status;
  }

  const sala = (pasta) => {
    if (!salas.has(pasta)) salas.set(pasta, criarGit(pasta, { env }));
    return salas.get(pasta);
  };

  // O que o painel mostra: cada projeto do estado.json, com ou sem repositório, e o status do gh.
  async function resumo(estado) {
    const projetos = [];
    for (const p of (estado && estado.projetos) || []) {
      const item = { id: p.id, nome: p.nome || p.id, repo: p.repo || null, git: null, criando: criando === p.id };
      if (p.repo && p.repo.pasta) {
        item.git = fs.existsSync(p.repo.pasta)
          ? await sala(p.repo.pasta).resumo()
          : { disponivel: false, motivo: `a pasta ${p.repo.pasta} não existe mais neste PC`, pendentes: 0, adiante: 0, arquivos: [] };
      }
      projetos.push(item);
    }
    return { gh: await statusGh(), pasta: base, projetos };
  }

  function acharProjeto(estado, id) {
    const projeto = ((estado && estado.projetos) || []).find((p) => p.id === id);
    if (!projeto) throw new ErroEscritorio(404, `projeto "${id}" não encontrado no estado.json`);
    return projeto;
  }

  async function identidade(cwd) {
    const nome = (await rodarGit(cwd, ['config', 'user.name'], { permitirErro: true })).saida.trim() || IDENTIDADE_PADRAO.nome;
    const email = (await rodarGit(cwd, ['config', 'user.email'], { permitirErro: true })).saida.trim() || IDENTIDADE_PADRAO.email;
    return { GIT_AUTHOR_NAME: nome, GIT_AUTHOR_EMAIL: email, GIT_COMMITTER_NAME: nome, GIT_COMMITTER_EMAIL: email };
  }

  // README inicial a partir do briefing do projeto (só o título e a linha "O que é").
  function readme(projeto) {
    let oQueE = '';
    try {
      const briefing = fs.readFileSync(path.join(raiz, projeto.briefing || `projetos/${projeto.id}.md`), 'utf8');
      const linha = briefing.split('\n').find((l) => /\*\*O que é:\*\*/.test(l));
      if (linha) oQueE = linha.replace(/^.*\*\*O que é:\*\*\s*/, '').trim();
    } catch {
      // sem briefing: README só com o nome
    }
    return `# ${projeto.nome || projeto.id}\n\n${oQueE ? `${oQueE}\n\n` : ''}`
      + 'Repositório do projeto, criado pelo Escritório de IA. O briefing e as entregas da equipe ficam no escritório; '
      + 'o código e os arquivos do projeto ficam aqui.\n';
  }

  // Cria a pasta, o primeiro commit e o repositório privado no GitHub, e devolve o que gravar em projetos[].repo.
  async function criar(estado, id) {
    if (criando) throw new ErroEscritorio(409, `já estou criando o repositório de "${criando}"; espere terminar`);
    const projeto = acharProjeto(estado, id);
    if (projeto.repo && projeto.repo.url) throw new ErroEscritorio(409, `o projeto "${id}" já tem repositório: ${projeto.repo.url}`);
    if (!ID_VALIDO.test(projeto.id)) throw new ErroEscritorio(400, `o id "${projeto.id}" não serve como nome de repositório (use letras minúsculas, números e hífens)`);
    const gh = await statusGh();
    if (!gh.pronto) throw new ErroEscritorio(409, `não dá para criar: ${gh.motivo}`);

    const pasta = path.join(base, projeto.id);
    const dentroDoEscritorio = path.resolve(pasta).toLowerCase().startsWith(path.resolve(raiz).toLowerCase() + path.sep);
    if (dentroDoEscritorio) throw new ErroEscritorio(400, 'a pasta dos projetos não pode ficar dentro da pasta do escritório');

    criando = projeto.id;
    try {
      fs.mkdirSync(pasta, { recursive: true });
      if (fs.existsSync(path.join(pasta, '.git'))) {
        const remoto = (await rodarGit(pasta, ['remote', 'get-url', 'origin'], { permitirErro: true })).saida.trim();
        if (remoto) throw new ErroEscritorio(409, `a pasta ${pasta} já é um repositório ligado a ${remoto}; nada foi mudado`);
      } else {
        const init = await rodarGit(pasta, ['init', '--quiet', '-b', 'main'], { permitirErro: true });
        if (!init.ok) { // Git antigo, sem -b
          await rodarGit(pasta, ['init', '--quiet']);
          await rodarGit(pasta, ['symbolic-ref', 'HEAD', 'refs/heads/main']);
        }
      }
      if (!fs.existsSync(path.join(pasta, 'README.md'))) fs.writeFileSync(path.join(pasta, 'README.md'), readme(projeto), 'utf8');
      if (!fs.existsSync(path.join(pasta, '.gitignore'))) fs.writeFileSync(path.join(pasta, '.gitignore'), GITIGNORE, 'utf8');
      const extra = await identidade(pasta);
      await rodarGit(pasta, ['add', '-A']);
      const temCommit = (await rodarGit(pasta, ['rev-parse', '--verify', '--quiet', 'HEAD'], { permitirErro: true })).ok;
      const mudou = (await rodarGit(pasta, ['status', '--porcelain'])).saida.trim();
      if (!temCommit || mudou) await rodarGit(pasta, ['commit', '--quiet', '-m', 'Começo do projeto (Escritório de IA)'], { extra });

      const descricao = `${projeto.nome || projeto.id} · criado pelo Escritório de IA`.slice(0, 300);
      await rodarGh(['repo', 'create', projeto.id, '--private', '--source', pasta, '--remote', 'origin', '--push', '--description', descricao],
        { cwd: pasta, extra });
      const vista = await rodarGh(['repo', 'view', '--json', 'url,nameWithOwner', '--jq', '.url + " " + .nameWithOwner'], { cwd: pasta, permitirErro: true });
      const [url = '', nome = ''] = vista.saida.trim().split(' ');
      salas.delete(pasta);
      return { pasta, url: url || `https://github.com/${gh.conta}/${projeto.id}`, nome: nome || `${gh.conta}/${projeto.id}`, privado: true, criado: agora() };
    } catch (e) {
      if (e instanceof ErroEscritorio) throw e;
      throw new ErroEscritorio(502, `não deu para criar o repositório: ${e.message}`);
    } finally {
      criando = '';
    }
  }

  // Commit + push da pasta do projeto (mesma lógica do envio do escritório).
  async function enviar(estado, id) {
    const projeto = acharProjeto(estado, id);
    if (!projeto.repo || !projeto.repo.pasta) throw new ErroEscritorio(409, `o projeto "${id}" ainda não tem repositório`);
    if (!fs.existsSync(projeto.repo.pasta)) throw new ErroEscritorio(409, `a pasta ${projeto.repo.pasta} não existe mais neste PC`);
    try {
      return await sala(projeto.repo.pasta).enviar(`projeto ${projeto.nome || projeto.id}`);
    } catch (e) {
      throw new ErroEscritorio(e.ocupado ? 409 : 502, `não deu para enviar: ${e.message}`);
    }
  }

  return { resumo, criar, enviar, statusGh, get criando() { return criando; }, pastaProjetos: base };
}

module.exports = { criarRepos };
