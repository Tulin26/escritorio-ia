"""O conteúdo da política de privacidade, num lugar só.

Por que este módulo existe
--------------------------
Mesmo motivo de core/ajuda.py: o texto mora aqui, sem marcação, e
web/templates/privacidade.html só renderiza. Assim um dia em que a tela do
Streamlit precisar do mesmo texto, ele não nasce escrito duas vezes.

De onde vieram os fatos abaixo
-------------------------------
Nenhuma frase aqui é genérica de modelo de política de privacidade — cada
uma foi conferida contra o código antes de ser escrita:

- Campos do cadastro: services/aluno_auth_service.py (cadastrar_aluno).
- O que vai pro provedor de IA: services/ia/enigma.py
  (_prompts_oraculo/_prompts_laboratorio) só manda matéria, série, nível e
  tema -- nunca nome, e-mail ou identificação do aluno.
- O que vai pro provedor de e-mail: services/aluno_auth_service.py
  (_enviar_email_confirmacao/_enviar_email_redefinicao_senha) manda nome e
  e-mail, só para confirmação de cadastro e redefinição de senha.
- Cookies: um grep em web/templates/ por host externo só encontra
  fonts.googleapis.com, fonts.gstatic.com (Google Fonts) e
  cdn.jsdelivr.net (MathJax) -- nenhum pixel de rastreamento ou anúncio.
- IP: usado só em memória pelo Flask-Limiter (core/rate_limit.py), nunca
  gravado no banco -- confirmado por grep em repositories/ e services/.
- Acesso e exclusão têm mecanismo desde 28/09/2026 -- scripts/dados_do_aluno.py
  e scripts/excluir_aluno.py, por cima de services/dados_pessoais.py. O que
  NÃO existe é autoatendimento pela tela, de propósito (o motivo está no
  módulo do serviço). Este texto continua refletindo isso honestamente: o
  pedido é pelo professor/escola, não self-service.

O que falta preencher
----------------------
CONTATO_PRIVACIDADE abaixo lê PRIVACIDADE_CONTATO_EMAIL do ambiente. Sem
essa variável, a página usa uma frase honesta em vez de inventar um
e-mail -- mas alguém responsável pelo EducaGame precisa decidir esse
contato (e a razão social/CNPJ do item 1, se houver) antes disto valer
como política de privacidade de verdade, e não só como o rascunho técnico
que é hoje.
"""

from __future__ import annotations

import os

ATUALIZADO_EM = "25 de setembro de 2026"


def _contato_privacidade() -> str:
    email = str(os.getenv("PRIVACIDADE_CONTATO_EMAIL") or "").strip()
    if email:
        return f"escreva para {email}"
    return (
        "peça ao professor ou à coordenação da sua escola: quem administra "
        "a conta da escola no EducaGame tem acesso ao painel do professor e "
        "pode encaminhar o pedido"
    )


def secoes_da_privacidade() -> list[dict]:
    contato = _contato_privacidade()
    return [
        {
            "id": "o-que-e",
            "titulo": "O que é isto",
            "paragrafos": [
                "Esta página explica, em linguagem direta, quais dados o EducaGame "
                "coleta, para quê, com quem compartilha e como pedir acesso ou "
                "exclusão — conforme a Lei Geral de Proteção de Dados (Lei "
                "13.709/2018, a LGPD).",
                "O EducaGame é usado dentro do contexto de uma escola: quem cria a "
                "conta de aluno o faz vinculado a uma escola específica, com um "
                "código combinado com o professor.",
            ],
        },
        {
            "id": "dados-que-coletamos",
            "titulo": "Quais dados coletamos",
            "paragrafos": [
                "No cadastro: nome completo, RA/identificação, e-mail, senha "
                "(nunca guardada em texto puro — só um hash, ver a seção "
                "Segurança), série/ano e período.",
                "Durante o uso: as respostas dadas em cada questão, se estavam "
                "certas ou erradas, o tempo de resposta, a pontuação e o "
                "progresso nos modos de jogo (RPG, guildas, rankings).",
                "Não pedimos nem guardamos CPF, endereço, telefone, dado de "
                "geolocalização ou dado de pagamento — o EducaGame não cobra do "
                "aluno.",
            ],
        },
        {
            "id": "por-que-coletamos",
            "titulo": "Por que coletamos",
            "paragrafos": [
                "Para o EducaGame funcionar: autenticar o login, mostrar o "
                "histórico de estudo, calcular pontuação e ranking, e para o "
                "professor acompanhar o desempenho da turma no painel dele.",
                "Não usamos os dados para publicidade, não vendemos dado "
                "nenhum, e não existe rastreamento de navegação fora do "
                "EducaGame.",
            ],
        },
        {
            "id": "com-quem-compartilhamos",
            "titulo": "Com quem compartilhamos",
            "paragrafos": [
                "Supabase, que hospeda o banco de dados, e Render, que hospeda "
                "a aplicação: por serem quem guarda e serve os dados, têm "
                "acesso técnico a tudo que está no banco.",
                "Os provedores de IA que geram as questões (Groq, Gemini ou "
                "OpenRouter, dependendo de qual está disponível no momento) "
                "recebem só matéria, série, "
                "nível e tema da questão — nunca nome, e-mail, RA ou qualquer "
                "outro dado que identifique o aluno.",
                "O provedor de e-mail (usado para confirmar o cadastro e para "
                "redefinir senha esquecida) recebe nome e e-mail, só para "
                "enviar essas duas mensagens.",
                "Não compartilhamos dado com ninguém além destes, e não "
                "existe venda ou cessão de dado a terceiros para qualquer "
                "outro fim.",
            ],
        },
        {
            "id": "cookies",
            "titulo": "Cookies",
            "paragrafos": [
                "O EducaGame usa um único cookie técnico, o de sessão: ele "
                "guarda que você está logado e expira sozinho por "
                "inatividade. Não há cookie de rastreamento, de publicidade "
                "nem de redes sociais.",
                "As fontes de texto da tela vêm do Google Fonts e as fórmulas "
                "matemáticas do MathJax (via cdn.jsdelivr.net) — os dois são "
                "carregados de um servidor externo, prática comum da maioria "
                "dos sites, e nenhum dos dois é usado aqui para rastrear "
                "quem acessa.",
            ],
        },
        {
            "id": "por-quanto-tempo",
            "titulo": "Por quanto tempo guardamos",
            "paragrafos": [
                "Hoje o EducaGame ainda não tem exclusão automática por "
                "prazo: o dado fica guardado enquanto a conta existir, ou até "
                "que alguém peça a exclusão (ver a próxima seção). Isto é uma "
                "lacuna que pretendemos fechar com um pedido de exclusão feito "
                "pelo próprio aluno; até lá, o caminho é o de baixo.",
            ],
        },
        {
            "id": "seus-direitos",
            "titulo": "Seus direitos",
            "paragrafos": [
                "A LGPD garante a você (ou, se for menor de idade, ao seu "
                "responsável) o direito de confirmar o que existe, acessar, "
                "corrigir, pedir a exclusão, e revogar consentimento a "
                "qualquer momento.",
                f"Para exercer qualquer um desses direitos hoje, {contato}.",
            ],
        },
        {
            "id": "criancas-e-adolescentes",
            "titulo": "Sobre dado de criança e adolescente",
            "paragrafos": [
                "A maior parte de quem usa o EducaGame é menor de idade. A "
                "conta nasce dentro do contexto da escola, com um código que "
                "o professor fornece — o cadastro não é aberto ao público "
                "em geral.",
                "Tratamos esse dado com o cuidado que a LGPD exige para "
                "criança e adolescente (Art. 14): coletamos só o necessário "
                "para o uso pedagógico, não usamos para publicidade, e "
                "esperamos que a escola, como parte da relação dela com "
                "famílias e responsáveis, tenha o consentimento adequado "
                "para o uso de uma ferramenta como esta em sala de aula.",
            ],
        },
        {
            "id": "seguranca",
            "titulo": "Segurança",
            "paragrafos": [
                "A senha é guardada como hash (scrypt), nunca em texto "
                "legível — nem quem administra o sistema consegue ver a sua "
                "senha.",
                "A conexão com o EducaGame é sempre por HTTPS, o cookie de "
                "sessão só trafega por essa conexão segura, e a sessão expira "
                "sozinha por inatividade — pensado para o caso comum do "
                "laboratório de informática com computador compartilhado.",
            ],
        },
        {
            "id": "mudancas",
            "titulo": "Mudanças nesta política",
            "paragrafos": [
                f"Esta versão foi publicada em {ATUALIZADO_EM}. Se o texto "
                "mudar de um jeito que afete o que fazemos com o seu dado, "
                "a data acima muda junto.",
            ],
        },
    ]
