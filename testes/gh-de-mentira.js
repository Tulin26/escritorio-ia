// GitHub CLI de mentira para os testes: responde como o "gh" e cria o "repositório no GitHub" como um repositório
// vazio (bare) na pasta GH_DE_MENTIRA. Nada vai para a internet. GH_SEM_LOGIN=1 finge que não há login.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const pasta = process.env.GH_DE_MENTIRA;
const git = (cwd, ...a) => execFileSync('git', a, { cwd, encoding: 'utf8' }).trim();
const opcao = (nome) => args[args.indexOf(nome) + 1];

if (args[0] === '--version') {
  console.log('gh version 0.0.0 (de mentira)');
} else if (args[0] === 'api' && args[1] === 'user') {
  if (process.env.GH_SEM_LOGIN === '1') {
    console.error('To get started with GitHub CLI, please run:  gh auth login');
    process.exit(4);
  }
  console.log('tester');
} else if (args[0] === 'repo' && args[1] === 'create') {
  const nome = args[2];
  const remoto = path.join(pasta, `${nome}.git`);
  if (fs.existsSync(remoto)) {
    console.error('GraphQL: Name already exists on this account (createRepository)');
    process.exit(1);
  }
  if (!args.includes('--private')) { console.error('o teste espera --private'); process.exit(1); }
  const fonte = opcao('--source');
  git(pasta, 'init', '--quiet', '--bare', '-b', 'main', remoto);
  git(fonte, 'remote', 'add', opcao('--remote'), remoto);
  git(fonte, 'push', '--quiet', '-u', opcao('--remote'), 'HEAD:refs/heads/main');
  console.log(`https://github.com/tester/${nome}`);
} else if (args[0] === 'repo' && args[1] === 'view') {
  const nome = path.basename(git(process.cwd(), 'remote', 'get-url', 'origin')).replace(/\.git$/, '');
  console.log(`https://github.com/tester/${nome} tester/${nome}`);
} else {
  console.error(`gh de mentira: comando não esperado: ${args.join(' ')}`);
  process.exit(1);
}
