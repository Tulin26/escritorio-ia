import unicodedata

import pandas as pd
import streamlit as st

from services.aluno_auth_service import redefinir_senha_do_aluno
# MELHORIA: gerar_slug vivia duplicada aqui e em services/professor_service.
# Mesma logica escrita de dois jeitos -- duas copias divergem na primeira
# vez que alguem mexe numa so, e o slug e o que identifica a escola na URL.
from services.professor_service import gerar_slug
from services.dados_service import buscar_alunos
from services.usuario_service import (
    PAPEIS,
    criar_conta,
    definir_ativo,
    listar_contas,
    redefinir_senha_de_conta,
    vincular_escola,
)
from services.escola_service import (
    MENSAGENS_DA_ESCOLA,
    criar_escola,
    listar_escolas,
    atualizar_escola,
    excluir_escola,
)

# MELHORIA: cadastrar, editar e excluir escola diziam "com sucesso" sem olhar
# o retorno. As gravacoes nunca levantam excecao (devolvem None), entao o
# `except` que procurava "unique" no texto do erro nunca rodava -- e, quando
# rodasse, mostraria o erro do banco cru. Agora o motivo vem da gravacao
# (repositories/gravacao.py) e o texto de MENSAGENS_DA_ESCOLA.
#
# O st.success vinha logo antes do st.rerun(), que recomeca a tela na hora: a
# mensagem sumia antes de alguem ler. Ela atravessa o rerun guardada na
# sessao, uma chave por secao.
_CHAVE_ESCOLA_CRIADA = "escola_criada"
_CHAVE_ESCOLA_ATUALIZADA = "escola_atualizada"
_CHAVE_ESCOLA_EXCLUIDA = "escola_excluida"


def _sucesso_depois_do_rerun(chave: str, texto: str) -> None:
    st.session_state[chave] = texto
    st.rerun()


def _mostrar_sucesso_guardado(chave: str) -> None:
    texto = st.session_state.pop(chave, None)
    if texto:
        st.success(texto)


def usuario_e_desenvolvedor() -> bool:
    """O papel na sessao e a unica credencial do ADM.

    MELHORIA: a Chave Mestra e anterior a tabela de usuarios. A migracao
    20260803120100_usuarios.sql diz isso na primeira linha -- ela "substitui a
    senha mestra unica por uma tabela real, com senha em hash". A troca parou
    no meio, e o resultado era pedir DUAS credenciais para a mesma pessoa:
    login como desenvolvedor e, dentro do painel, a chave.

    O argumento para manter a chave era que a tela de escolher escola oferece
    o ADM ANTES de qualquer login, e "la nao ha usuario para consultar". Isso
    estava errado: a conta de desenvolvedor e global -- `conta_pode_entrar`
    devolve True para ela sem olhar escola --, entao da para autenticar antes
    de escolher unidade. E o que a tela inicial faz agora, e a chave saiu.
    """
    usuario = st.session_state.get("usuario") or {}
    if not isinstance(usuario, dict):
        return False
    return str(usuario.get("role", "")) == "desenvolvedor"


def tela_administrador():
    """A tela e uma lista de secoes; cada uma cuida de si.

    MELHORIA: eram 233 linhas numa funcao so -- portao, cadastro, listagem,
    edicao e exclusao de escola, empilhados. Tres secoes ja moravam fora
    (_secao_contas, _secao_senha_de_aluno, _secao_diagnostico) e o resto
    ficou para tras porque nao havia como fotografar tela de Streamlit.
    A bancada (tests/apoio_streamlit.py) resolveu isso.
    """
    st.title("🏗️ Painel do Desenvolvedor")

    _portao_do_painel()

    st.success("🔓 Modo Desenvolvedor Ativo")

    _secao_cadastrar_escola()
    escolas = _secao_unidades_ativas()
    _secao_editar_escola(escolas)
    _secao_excluir_escola(escolas)

    st.divider()
    _secao_contas(escolas)

    st.divider()
    _secao_senha_de_aluno(escolas)

    st.divider()
    _secao_diagnostico()

    st.divider()


def _portao_do_painel() -> None:
    """Quem nao e desenvolvedor para aqui. A saida e st.stop().

    MELHORIA: aqui existia uma segunda porta -- a Chave Mestra, uma senha
    unica combinada entre pessoas, que abria o ADM para quem NAO era
    desenvolvedor. Ela era a porta mais fraca da casa, e numa casa a porta
    mais fraca e que define a tranca: nao adianta o papel ser exigido em
    _pagina_permitida e em app.py se uma senha compartilhada entra do mesmo
    jeito.

    A senha unica e anterior a tabela de usuarios; a migracao
    20260803120100_usuarios.sql veio "substituir a senha mestra unica por uma
    tabela real, com senha em hash". Agora a substituicao esta completa, aqui
    e na tela inicial (st/ui/home_st.py::_renderizar_adm_inicio).

    Se ninguem souber a senha do desenvolvedor, a reserva e rodar
    `scripts/seed_usuarios.py`, que faz upsert da conta -- exige a chave do
    Supabase, e nao uma senha combinada por mensagem.
    """
    if not usuario_e_desenvolvedor():
        st.error("Esta área é restrita ao desenvolvedor. Entre com a conta de desenvolvedor.")
        st.stop()


def _secao_cadastrar_escola() -> None:
    # fora do expander: ele volta fechado depois do rerun
    _mostrar_sucesso_guardado(_CHAVE_ESCOLA_CRIADA)
    with st.expander("➕ Cadastrar Nova Escola", expanded=False):
        with st.form("nova_escola", clear_on_submit=True):
            nome = st.text_input("Nome da Instituição")

            slug_sugerido = gerar_slug(nome) if nome else ""
            slug = st.text_input(
                "Código de Acesso (Slug)",
                value=slug_sugerido,
                help="Use letras minúsculas, números e hífen. Exemplo: saleata",
            )

            slug = gerar_slug(slug)

            cor = st.color_picker("Cor do Tema", "#003366")
            mostrar_ranking = st.checkbox("Mostrar ranking", value=True)
            modo_guilda = st.checkbox("Modo guilda", value=True)

            st.caption(f"Slug final: `{slug or 'aguardando-nome'}`")

            confirmar = st.form_submit_button("Confirmar Cadastro")

            if confirmar:
                if not nome.strip() or not slug:
                    st.warning("Preencha o nome da instituição e um slug válido.")
                else:
                    criada, motivo = criar_escola(
                        nome=nome.strip(),
                        slug=slug,
                        cor_tema=cor,
                        mostrar_ranking=mostrar_ranking,
                        modo_guilda=modo_guilda,
                    )
                    if criada is not None:
                        _sucesso_depois_do_rerun(
                            _CHAVE_ESCOLA_CRIADA, f"✅ Unidade '{nome.strip()}' criada com sucesso!"
                        )
                    else:
                        st.error(MENSAGENS_DA_ESCOLA[motivo])


def _secao_unidades_ativas() -> list[dict]:
    """Lista as escolas na tela E devolve a lista: as secoes abaixo usam.

    Devolver [] quando a consulta falha e deliberado -- as secoes de editar
    e excluir mostram 'cadastre uma escola primeiro' em vez de quebrarem.
    """
    st.divider()
    st.subheader("📋 Unidades Ativas")

    try:
        escolas = listar_escolas()

        if escolas:
            df_esc = pd.DataFrame(escolas)
            colunas_exibir = [
                col
                for col in [
                    "nome",
                    "slug",
                    "cor_tema",
                    "mostrar_ranking",
                    "modo_guilda",
                    "created_at",
                ]
                if col in df_esc.columns
            ]
            st.dataframe(
                df_esc[colunas_exibir],
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Nenhuma escola cadastrada.")
    except Exception as e:
        st.error(f"Erro ao listar unidades: {e}")
        escolas = []

    return escolas


def _secao_editar_escola(escolas: list[dict]) -> None:
    st.divider()
    st.subheader("✏️ Editar Escola")
    _mostrar_sucesso_guardado(_CHAVE_ESCOLA_ATUALIZADA)

    if escolas:
        opcoes = {f"{e.get('nome')} ({e.get('slug')})": e for e in escolas}
        escolha = st.selectbox("Selecione a escola", list(opcoes.keys()))
        escola = opcoes[escolha]

        with st.form("editar_escola"):
            novo_nome = st.text_input("Nome", value=escola.get("nome", ""))

            novo_slug = st.text_input(
                "Slug",
                value=escola.get("slug", ""),
                help="Cuidado: alterar o slug muda o código de acesso da escola.",
            )
            novo_slug = gerar_slug(novo_slug)

            nova_cor = st.color_picker(
                "Cor do tema",
                value=escola.get("cor_tema") or "#003366",
            )
            mostrar_ranking_edit = st.checkbox(
                "Mostrar ranking",
                value=bool(escola.get("mostrar_ranking", True)),
            )
            modo_guilda_edit = st.checkbox(
                "Modo guilda",
                value=bool(escola.get("modo_guilda", True)),
            )

            st.caption(f"Slug final: `{novo_slug}`")

            salvar = st.form_submit_button("💾 Salvar alterações")

            if salvar:
                if not novo_nome.strip() or not novo_slug:
                    st.warning("Nome e slug são obrigatórios.")
                else:
                    atualizada, motivo = atualizar_escola(
                        escola["id"],
                        {
                            "nome": novo_nome.strip(),
                            "slug": novo_slug,
                            "cor_tema": nova_cor,
                            "mostrar_ranking": mostrar_ranking_edit,
                            "modo_guilda": modo_guilda_edit,
                        },
                    )
                    if atualizada is not None:
                        _sucesso_depois_do_rerun(_CHAVE_ESCOLA_ATUALIZADA, "✅ Escola atualizada com sucesso!")
                    else:
                        st.error(MENSAGENS_DA_ESCOLA[motivo])
    else:
        st.info("Cadastre uma escola primeiro para poder editar.")


def _secao_excluir_escola(escolas: list[dict]) -> None:
    st.divider()
    st.subheader("🗑️ Excluir Escola")
    # fora do expander: ele volta fechado depois do rerun
    _mostrar_sucesso_guardado(_CHAVE_ESCOLA_EXCLUIDA)

    if escolas:
        with st.expander("Área de exclusão", expanded=False):
            # MELHORIA: o aviso listava alunos, logs e RPGs, mas nao a conta
            # de professor -- que passou a ir junto quando usuarios.escola_id
            # ganhou ON DELETE CASCADE. Aviso que nao acompanha o que a acao
            # faz e pior que aviso nenhum: ele da confianca errada.
            st.warning(
                "Atenção: isso apagará também alunos, logs, RPGs, dados vinculados "
                "e **a conta de professor desta escola**. Não há como desfazer."
            )

            opcoes_excluir = {
                f"{e.get('nome')} ({e.get('slug')})": e for e in escolas
            }

            escolha_excluir = st.selectbox(
                "Selecione a escola para excluir",
                list(opcoes_excluir.keys()),
                key="select_excluir_escola",
            )

            escola_excluir = opcoes_excluir[escolha_excluir]
            slug_excluir = escola_excluir.get("slug", "")

            confirmacao = st.text_input(
                f"Digite exatamente o slug '{slug_excluir}' para confirmar:"
            )

            frase_confirmacao = st.text_input(
                "Digite APAGAR para confirmar a exclusão definitiva:"
            )

            if st.button("🗑️ Excluir definitivamente"):
                if confirmacao != slug_excluir:
                    st.error("Slug de confirmação incorreto.")
                elif frase_confirmacao != "APAGAR":
                    st.error("Confirmação final incorreta. Digite APAGAR.")
                else:
                    excluida, motivo = excluir_escola(escola_excluir["id"])
                    if excluida is not None:
                        _sucesso_depois_do_rerun(_CHAVE_ESCOLA_EXCLUIDA, "🗑️ Escola excluída com sucesso!")
                    else:
                        st.error(MENSAGENS_DA_ESCOLA[motivo])


def _secao_senha_de_aluno(escolas: list[dict]) -> None:
    """MELHORIA: a recuperacao por e-mail nao serve para quem nao tem e-mail
    cadastrado -- boa parte da turma. Para esses, a unica saida era mexer no
    Supabase na mao."""
    st.subheader("🔑 Senha de aluno")
    if not escolas:
        st.caption("Cadastre uma escola primeiro.")
        return

    opcoes_escola = {f"{e.get('nome')} ({e.get('slug')})": e for e in escolas}
    escolhida = st.selectbox(
        "Escola", list(opcoes_escola.keys()), key="select_escola_senha_aluno"
    )
    escola = opcoes_escola[escolhida]

    try:
        alunos = buscar_alunos(escola.get("id")) or []
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível listar os alunos: {erro}")
        return

    if not alunos:
        st.caption("Nenhum aluno nesta escola.")
        return

    opcoes_aluno = {
        f"{a.get('nome')} - {a.get('ano_escolar', '')}".strip(" -"): a for a in alunos
    }
    aluno = opcoes_aluno[
        st.selectbox("Aluno", list(opcoes_aluno.keys()), key="select_aluno_senha")
    ]

    st.caption(
        "A nova senha aparece uma única vez: o banco guarda só o hash. "
        "Anote antes de sair da tela."
    )
    if st.button("Gerar nova senha", key="btn_gerar_senha_aluno"):
        ok, erro, senha = redefinir_senha_do_aluno(aluno.get("id"))
        if not ok:
            st.error(erro)
        else:
            st.success(f"Senha de {aluno.get('nome')} redefinida.")
            st.code(senha, language=None)


def _secao_diagnostico() -> None:
    """MELHORIA: "o Groq esta funcionando?" so era respondivel lendo o log da
    plataforma. As pecas ja existiam no codigo, sem tela nenhuma."""
    from core.diagnostico_config import verificar_configuracao
    from repositories.supabase_client import diagnostico_supabase_seguro
    from services.ia_service import obter_ultimo_erro_ia, obter_ultimo_provedor_ia

    st.subheader("🩺 Diagnóstico do sistema")

    try:
        supabase = diagnostico_supabase_seguro()
    except Exception as erro:  # noqa: BLE001
        supabase = {"erro": str(erro)}

    coluna_ia, coluna_banco = st.columns(2)
    coluna_ia.metric(
        "Último provedor de IA", obter_ultimo_provedor_ia() or "nenhuma questão ainda"
    )
    coluna_banco.metric("Papel da chave", supabase.get("jwt_role") or "-")
    st.caption(f"Projeto Supabase: {supabase.get('projeto_ref') or 'ausente'}")

    aviso_ia = obter_ultimo_erro_ia()
    if aviso_ia:
        st.caption(f"Último aviso da IA: {aviso_ia}")

    achados = verificar_configuracao()
    if not achados:
        st.success("Configuração OK: banco e IA configurados.")
    for nivel, mensagem in achados:
        (st.error if nivel == "erro" else st.warning)(mensagem)


def _secao_contas(escolas: list[dict]) -> None:
    """MELHORIA: "usuarios" era a unica tabela sem tela. Dava para viver assim
    enquanto a conta nao tinha escola; depois que o vinculo passou a decidir em
    que unidade ela entra (services/auth_service.py::conta_pode_entrar),
    vincular professor virou UPDATE na mao no Supabase -- e a conta nasce SEM
    vinculo, ou seja, nasce sem conseguir entrar em lugar nenhum.

    As regras moram em services/usuario_service.py, e nao aqui, porque a mesma
    tela existe no Flask.
    """
    st.subheader("👤 Contas de login")
    st.caption(
        "Conta de professor só entra na escola a que está vinculada. Sem vínculo, "
        "ela não entra em lugar nenhum — o desenvolvedor é global de propósito."
    )

    try:
        contas = listar_contas()
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível listar as contas: {erro}")
        return

    if contas:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Usuário": c.get("username", ""),
                        "Papel": c.get("role", ""),
                        "Escola": c.get("escola_nome") or "—",
                        "Situação": (
                            "não entra: sem escola"
                            if c.get("sem_vinculo")
                            else ("ativa" if c.get("ativo", True) else "desativada")
                        ),
                    }
                    for c in contas
                ]
            ),
            width="stretch",
            hide_index=True,
        )

        rotulos = {f"{c.get('username')} ({c.get('role')})": c for c in contas}
        conta = rotulos[st.selectbox("Conta", list(rotulos.keys()), key="select_conta_adm")]

        opcoes_escola = {"— sem escola —": ""}
        opcoes_escola.update({f"{e.get('nome')}": str(e.get("id")) for e in escolas})
        atual = next(
            (rotulo for rotulo, valor in opcoes_escola.items() if valor == conta.get("escola_id", "")),
            "— sem escola —",
        )
        escolhida = st.selectbox(
            "Escola desta conta",
            list(opcoes_escola.keys()),
            index=list(opcoes_escola.keys()).index(atual),
            key="select_escola_da_conta",
        )

        col_vinculo, col_ativo, col_senha = st.columns(3)

        if col_vinculo.button("Salvar vínculo", key="btn_vincular_conta"):
            ok, erro = vincular_escola(conta.get("id"), opcoes_escola[escolhida])
            (st.success if ok else st.error)("Vínculo atualizado." if ok else erro)
            if ok:
                st.rerun()

        ativa = bool(conta.get("ativo", True))
        if col_ativo.button("Desativar" if ativa else "Ativar", key="btn_ativar_conta"):
            ok, erro = definir_ativo(conta.get("id"), not ativa)
            (st.success if ok else st.error)(
                ("Conta desativada." if ativa else "Conta ativada.") if ok else erro
            )
            if ok:
                st.rerun()

        if col_senha.button("Gerar nova senha", key="btn_senha_conta"):
            ok, erro, senha = redefinir_senha_de_conta(conta.get("id"))
            if ok:
                # A senha aparece uma vez so: o banco guarda apenas o hash.
                st.success(f"Senha de {conta.get('username')}: {senha}")
                st.caption("Anote antes de sair da tela.")
            else:
                st.error(erro)
    else:
        st.caption("Nenhuma conta cadastrada.")

    with st.expander("➕ Criar conta", expanded=False):
        with st.form("nova_conta", clear_on_submit=True):
            username = st.text_input("Usuário (sem espaço, tudo minúsculo)")
            papel = st.selectbox("Papel", list(PAPEIS), index=list(PAPEIS).index("professor"))
            opcoes_nova = {"— sem escola —": ""}
            opcoes_nova.update({f"{e.get('nome')}": str(e.get("id")) for e in escolas})
            escola_nova = st.selectbox("Escola (obrigatória para professor)", list(opcoes_nova.keys()))
            senha_nova = st.text_input("Senha (em branco = gerada e mostrada uma vez)")

            if st.form_submit_button("Criar conta"):
                ok, erro, senha = criar_conta(
                    username, papel, opcoes_nova[escola_nova], senha_nova
                )
                if ok:
                    st.success(f"Conta criada. Senha: {senha}")
                    st.caption("Anote antes de sair da tela.")
                else:
                    st.error(erro)
