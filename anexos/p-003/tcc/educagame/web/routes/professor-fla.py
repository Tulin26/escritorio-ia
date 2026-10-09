from __future__ import annotations

import io
from collections import Counter

from flask import Blueprint, redirect, render_template, request, send_file, session, url_for

from core.config import exibir_materia
from services.aluno_auth_service import redefinir_senha_do_aluno
from services.aluno_service import MENSAGENS_DA_MATRICULA, registrar_matricula
from services.avisos_de_gravacao import CONFIRMACAO_INVALIDA, FALTAM_DADOS
from services.dados_service import buscar_alunos, buscar_logs, buscar_resumo_turma
from repositories.meta_repo import remover_foco, salvar_foco
from services.metas_service import metas_da_turma, opcoes_de_foco, resumo_da_turma
from services.escola_service import (
    MENSAGENS_DA_ESCOLA,
    MENSAGENS_DAS_PREFERENCIAS,
    atualizar_escola,
    criar_escola,
    excluir_escola,
    listar_escolas,
    salvar_preferencias,
)
from services.professor_service import (
    ABAS,
    ABAS_GESTAO,
    MATERIAS_RPG,
    MODOS_PROFESSOR,
    SERIES_GERAIS,
    aluno_padrao,
    df_logs_revisao,
    filtrar_logs,
    gerar_slug,
    materias_disponiveis,
    metricas_logs,
    metricas_turma,
    nome_arquivo_revisao,
    ranking_alunos,
    resumo_filtrado,
)
from services.relatorios import gerar_pdf_revisao
from services.rpg_config_service import (
    MENSAGENS_DA_AVENTURA,
    excluir_aventura,
    listar_rpg_configs,
    salvar_aventura,
)
from services.usuario_service import (
    PAPEIS,
    agrupar_professores_por_escola,
    criar_conta,
    definir_ativo,
    listar_contas,
    listar_professores_visiveis,
    redefinir_senha_de_conta,
    vincular_escola,
)

professor_bp = Blueprint("professor", __name__)


@professor_bp.before_request
def exigir_papel_professor():
    # MELHORIA: antes o blueprint inteiro ficava aberto sem login nenhum;
    # so a aba "adm" tinha alguma protecao (senha mestra). Agora exige
    # papel professor ou desenvolvedor pra qualquer rota daqui (o gate
    # central em flask_app.py ja garante que ha algum usuario logado).
    if session.get("usuario_role") not in ("professor", "desenvolvedor"):
        return redirect(url_for("home.index"))
    return None


def _escola_atual(escola_id: str | None) -> dict:
    escolas = listar_escolas()
    escola = next((item for item in escolas if str(item.get("id")) == str(escola_id)), None)
    return escola or {
        "id": escola_id,
        "nome": session.get("escola_nome", "EducaGame"),
        "slug": session.get("escola_slug", ""),
        "mostrar_ranking": True,
        "modo_guilda": True,
    }



def _diagnostico_do_sistema() -> dict:
    """Junta o que ja existia espalhado e nao aparecia em lugar nenhum.

    MELHORIA: "o Groq esta funcionando?" so era respondivel lendo o log do
    Render. As tres pecas abaixo ja existiam no codigo -- a checagem de
    configuracao so ia pro log, e o provedor de IA que respondeu por ultimo
    nao era exposto em tela nenhuma.
    """
    from core.diagnostico_config import verificar_configuracao
    from repositories.supabase_client import diagnostico_supabase_seguro
    from services.ia_service import obter_ultimo_erro_ia, obter_ultimo_provedor_ia

    try:
        supabase = diagnostico_supabase_seguro()
    except Exception as erro:  # noqa: BLE001
        supabase = {"erro": str(erro)}

    return {
        "config": verificar_configuracao(),
        "ultimo_provedor_ia": obter_ultimo_provedor_ia() or "",
        "ultimo_erro_ia": obter_ultimo_erro_ia() or "",
        "supabase": supabase,
    }


def _redirect_admin(msg: str = ""):
    return redirect(url_for("professor.tela_professor", aba="adm", msg=msg))


def _erro_no_admin(motivo: str, **parametros):
    return redirect(url_for("professor.tela_professor", aba="adm", erro=motivo, **parametros))


# Na URL vai a chave do motivo, nunca o texto: assim nenhum link monta um
# aviso qualquer na faixa de erro, e dado de aluno (RA) nao para no log de
# acesso. A aba escolhe o mapa -- "nao encontrada" e uma frase para a
# aventura e outra para a escola. Chave desconhecida nao mostra nada.
MENSAGENS_DE_ERRO_POR_ABA = {
    "matricula": MENSAGENS_DA_MATRICULA,
    "rpg": MENSAGENS_DA_AVENTURA,
    "configuracoes": MENSAGENS_DAS_PREFERENCIAS,
    "adm": MENSAGENS_DA_ESCOLA,
}


ABA_PADRAO = "analises"


def aba_escolhida(aba_pedida: str | None, eh_desenvolvedor: bool) -> str:
    """Qual aba a URL conseguiu pedir, depois das duas trancas.

    Fora da rota porque é REGRA, e uma delas é de acesso:

    - **"adm" é só de desenvolvedor.** O `before_request` deste blueprint
      deixa passar professor, então sem esta segunda tranca `?aba=adm`
      digitado na barra de endereços entrava no painel do desenvolvedor.
    - **Aba que não existe cai em "analises"**, em vez de renderizar uma
      página com a tira de abas e nenhum conteúdo, sem dizer por quê.

    Dentro de uma rota de 149 linhas isso só dava para conferir subindo o
    Flask inteiro. Aqui é uma função com uma pergunta só.

    MELHORIA: o original começava com `aba = aba_pedida or "analises"`, e a
    mutação mostrou que essa linha não sustentava nada -- nem `None` nem `""`
    estão na lista de abas, então a checagem de baixo já os pegava. Ausência e
    aba inventada são o mesmo caso, e agora caem no mesmo lugar uma vez só.
    """
    if aba_pedida == "adm" and not eh_desenvolvedor:
        return ABA_PADRAO
    if aba_pedida not in {item["valor"] for item in ABAS}:
        return ABA_PADRAO
    return aba_pedida


def _recorte_do_aluno(alunos: list[dict], logs: list[dict]) -> dict:
    """O que a aba de análises mostra: um aluno, um modo, uma matéria."""
    aluno_id = request.args.get("aluno_id") or aluno_padrao(alunos, session.get("aluno_id", ""))
    modo = request.args.get("modo") or "oraculo"
    logs_aluno = [log for log in logs if str(log.get("aluno_id")) == str(aluno_id)]
    materias = materias_disponiveis(logs_aluno)
    materia = request.args.get("materia") or "todas"
    if materia != "todas" and materia not in materias:
        # matéria que este aluno não tem (link antigo, ou troca de aluno com o
        # filtro montado): mostrar tudo é melhor que mostrar uma tela vazia
        materia = "todas"

    logs_recorte = filtrar_logs(logs, aluno_id, modo, materia)
    metricas = metricas_logs(logs_recorte)
    contagem = Counter(log.get("resultado") for log in logs_recorte)

    return {
        "aluno": next((item for item in alunos if str(item.get("id")) == str(aluno_id)), {}),
        "aluno_id": aluno_id,
        "modo": modo,
        "modo_label": next(
            (item["label"] for item in MODOS_PROFESSOR if item["valor"] == modo), "Oráculo"
        ),
        "materias": materias,
        "materia": materia,
        "metricas": metricas,
        "acertos": contagem.get("Acertou", 0),
        "logs_recorte": logs_recorte,
    }


def _recorte_do_ranking(alunos: list[dict], logs: list[dict]) -> dict:
    serie = request.args.get("serie_ranking") or "Todas as séries"
    return {
        "series_alunos": _series_de(alunos),
        "serie_ranking": serie,
        "ranking": ranking_alunos(alunos, logs, serie),
    }


def _recorte_das_metas(escola_id: str | None, alunos: list[dict], logs: list[dict], ativa: bool) -> dict:
    """A aba "Metas e foco": quanto cada aluno ja fez NESTA semana.

    So monta quando a aba esta aberta -- ela le duas tabelas a mais
    (conclusoes e foco), e as outras abas nao precisam delas.
    """
    if not ativa or not escola_id:
        return {"linhas": [], "resumo": {}, "aluno_foco": {}, "opcoes_foco": []}

    linhas = metas_da_turma(escola_id, alunos, logs)
    aluno_id = request.args.get("aluno_id") or aluno_padrao(alunos, session.get("aluno_id", ""))
    aluno_foco = next((a for a in alunos if str(a.get("id")) == str(aluno_id)), {})
    return {
        "linhas": linhas,
        "resumo": resumo_da_turma(linhas),
        "aluno_foco": aluno_foco,
        # Os temas dependem da serie do aluno: o 7o ano nao recebe a lista do
        # Ensino Medio (core.config.get_temas_rpg ja decide isso).
        "opcoes_foco": opcoes_de_foco(str(aluno_foco.get("ano_escolar") or "")),
    }


def _recorte_da_turma(escola_id: str | None) -> dict:
    base = buscar_resumo_turma(escola_id) if escola_id else []
    serie = request.args.get("serie_resumo") or "Todas"
    periodo = request.args.get("periodo_resumo") or "Todos"
    resumo = resumo_filtrado(base, serie, periodo)
    return {
        "series_resumo": _series_de(base),
        "periodos_resumo": _valores_de(base, "periodo"),
        "serie_resumo": serie,
        "periodo_resumo": periodo,
        "resumo": resumo,
        "turma": metricas_turma(resumo),
    }


def _series_de(itens: list[dict]) -> list[str]:
    return _valores_de(itens, "ano_escolar")


def _valores_de(itens: list[dict], campo: str) -> list[str]:
    return sorted({str(item.get(campo, "")).strip() for item in itens if str(item.get(campo, "")).strip()})


def _dados_do_adm(mostrar_adm: bool) -> dict:
    """O painel do desenvolvedor, buscado só quando ele aparece na tela.

    MELHORIA: estes dados alimentam SO o partials/admin_panel.html, que
    renderiza apenas quando aba == "adm". Antes eram buscados em toda carga
    do painel para quem e desenvolvedor -- inclusive no hub, em analises e
    no RPG, onde nada disso aparece na tela. Como cada leitura e uma ida a
    rede (ate o cache mora no Supabase, ver core/runtime_context.py), eram
    duas idas desperdicadas por pagina.
    """
    escolas = listar_escolas() if mostrar_adm else []
    escola_admin_id = request.args.get("escola_admin_id") or (escolas[0].get("id") if escolas else "")
    return {
        "escolas": escolas,
        "escola_admin": next(
            (item for item in escolas if str(item.get("id")) == str(escola_admin_id)), {}
        ),
        "alunos_admin": buscar_alunos(escola_admin_id) if (mostrar_adm and escola_admin_id) else [],
        "diagnostico": _diagnostico_do_sistema() if mostrar_adm else {},
        "contas_admin": listar_contas() if mostrar_adm else [],
    }


def _grupos_de_professores(mostrar: bool) -> list:
    """Mesma regra de alcance do Streamlit, e pelo mesmo motivo: quem ve quais
    professores nao pode ser decidido em cada tela, ou as duas divergem.
    Buscado so quando a aba aparece -- cada leitura e uma ida a rede.
    """
    if not mostrar:
        return []
    return agrupar_professores_por_escola(
        listar_professores_visiveis(
            {"role": session.get("usuario_role"), "escola_id": session.get("escola_id")}
        )
    )


@professor_bp.route("/")
def tela_professor():
    escola_id = session.get("escola_id")
    eh_desenvolvedor = session.get("usuario_role") == "desenvolvedor"

    # MELHORIA: sem "aba" na URL mostra o hub em cards (visao geral do
    # painel); com "aba" mostra a secao escolhida direto, igual antes.
    aba_param = request.args.get("aba")
    mostrar_hub = aba_param is None
    aba = aba_escolhida(aba_param, eh_desenvolvedor)

    # O desenvolvedor cai numa escolha de AREA antes do hub de professor:
    # duas portas, Professor e ADM. Entrar como desenvolvedor e cair no
    # painel de professor era o que fazia a conta de manutencao parecer conta
    # de professor -- e deixava o ADM escondido no fim da tira de abas.
    mostrar_hub_desenvolvedor = (
        eh_desenvolvedor and mostrar_hub and request.args.get("area") != "gestao"
    )

    # O desenvolvedor global nao tem turma: as abas de gestao renderizariam
    # vazias, sem dizer por que. O ADM fica de fora porque ele age sobre
    # TODAS as escolas -- e onde se cadastra a primeira, quando nao ha
    # nenhuma para abrir.
    if eh_desenvolvedor and not escola_id and not mostrar_hub_desenvolvedor and aba != "adm":
        return redirect(url_for("home.abrir_escola"))

    alunos = buscar_alunos(escola_id) if escola_id else []
    logs = buscar_logs(escola_id) if escola_id else []
    escola = _escola_atual(escola_id)

    recorte = _recorte_do_aluno(alunos, logs)
    ranking = _recorte_do_ranking(alunos, logs)
    turma = _recorte_da_turma(escola_id)
    metas = _recorte_das_metas(escola_id, alunos, logs, aba == "metas")
    adm = _dados_do_adm(eh_desenvolvedor and aba == "adm")

    configs_rpg = listar_rpg_configs(escola_id) if escola_id else []
    rpg_id = request.args.get("rpg_id") or ""

    grupos_professores = _grupos_de_professores(aba == "professores")

    return render_template(
        "professor.html",
        # O ADM saiu da tira de abas: e outra AREA, nao outra aba do professor.
        abas=list(ABAS_GESTAO),
        aba=aba,
        mostrar_hub=mostrar_hub,
        mostrar_hub_desenvolvedor=mostrar_hub_desenvolvedor,
        escola_aberta=bool(escola_id),
        grupos_professores=grupos_professores,
        professores_sem_escola=sum(
            1 for _nome, contas in grupos_professores for c in contas if c.get("sem_vinculo")
        ),
        alunos=alunos,
        aluno=recorte["aluno"],
        aluno_id=recorte["aluno_id"],
        modos=MODOS_PROFESSOR,
        modo=recorte["modo"],
        modo_label=recorte["modo_label"],
        materias=recorte["materias"],
        materia=recorte["materia"],
        materia_label=exibir_materia(recorte["materia"]) if recorte["materia"] != "todas" else "Todas as matérias",
        metricas=recorte["metricas"],
        acertos=recorte["acertos"],
        erros=recorte["metricas"]["erros"],
        logs_recorte=recorte["logs_recorte"][:20],
        escola=escola,
        escola_nome=escola.get("nome", "EducaGame"),
        configs_rpg=configs_rpg,
        cfg_rpg=next((item for item in configs_rpg if str(item.get("id")) == str(rpg_id)), {}),
        rpg_id=rpg_id,
        series_gerais=SERIES_GERAIS,
        materias_rpg=MATERIAS_RPG,
        series_alunos=ranking["series_alunos"],
        serie_ranking=ranking["serie_ranking"],
        ranking=ranking["ranking"],
        resumo=turma["resumo"],
        series_resumo=turma["series_resumo"],
        periodos_resumo=turma["periodos_resumo"],
        serie_resumo=turma["serie_resumo"],
        periodo_resumo=turma["periodo_resumo"],
        turma=turma["turma"],
        eh_desenvolvedor=eh_desenvolvedor,
        escolas=adm["escolas"],
        escola_admin=adm["escola_admin"],
        alunos_admin=adm["alunos_admin"],
        diagnostico=adm["diagnostico"],
        contas_admin=adm["contas_admin"],
        papeis=PAPEIS,
        metas=metas["linhas"],
        metas_resumo=metas["resumo"],
        aluno_foco=metas["aluno_foco"],
        opcoes_foco=metas["opcoes_foco"],
        mensagem=request.args.get("msg", ""),
        erro=MENSAGENS_DE_ERRO_POR_ABA.get(aba, {}).get(request.args.get("erro", ""), ""),
    )


@professor_bp.route("/rpg/salvar", methods=["POST"])
def salvar_rpg_config_route():
    # MELHORIA: redirecionava sempre com "Aventura salva.", sem olhar o
    # retorno -- e tambem sem escola na sessao, quando nada era gravado.
    config_id = request.form.get("config_id", "")
    ok, motivo = salvar_aventura(
        session.get("escola_id"),
        config_id,
        {
            "titulo": request.form.get("titulo", "").strip(),
            "heroi_nome": request.form.get("heroi_nome", "").strip(),
            "poderes": request.form.get("poderes", "").strip(),
            "materia": request.form.get("materia", "Matemática"),
            "serie": request.form.get("serie", "9º Ano"),
            "cenario": request.form.get("cenario", "").strip(),
            "objetivo_final": request.form.get("objetivo_final", "").strip(),
            "descricao": request.form.get("descricao", "").strip(),
        },
    )
    if not ok:
        # A aventura que estava aberta continua aberta: voltar em "Criar nova
        # aventura" faria a proxima tentativa criar uma copia.
        return redirect(url_for("professor.tela_professor", aba="rpg", erro=motivo, rpg_id=config_id or None))
    return redirect(url_for("professor.tela_professor", aba="rpg", msg="Aventura salva."))


@professor_bp.route("/rpg/excluir", methods=["POST"])
def excluir_rpg_config_route():
    # MELHORIA: dizia "Aventura excluida." mesmo sem config_id no formulario
    # ou com o banco recusando -- e apagava aventura de qualquer escola, pelo
    # id do campo hidden. Agora so a da escola da sessao.
    config_id = request.form.get("config_id", "")
    ok, motivo = excluir_aventura(session.get("escola_id"), config_id)
    if not ok:
        return redirect(url_for("professor.tela_professor", aba="rpg", erro=motivo, rpg_id=config_id or None))
    return redirect(url_for("professor.tela_professor", aba="rpg", msg="Aventura excluida."))


@professor_bp.route("/foco/salvar", methods=["POST"])
def salvar_foco_route():
    """Anota o tema que este aluno precisa desenvolver.

    Materia e tema vem juntos num campo so ("Matematica|progressao
    aritmetica"): o tema pertence a uma materia, e deixar os dois em selects
    separados abriria a porta para gravar um par que nao existe.
    """
    escolha = str(request.form.get("materia_tema") or "")
    materia, _, tema = escolha.partition("|")
    ok, motivo = salvar_foco(
        aluno_id=request.form.get("aluno_id", ""),
        escola_id=session.get("escola_id"),
        materia=materia,
        tema=tema,
        observacao=request.form.get("observacao", ""),
        definido_por=str(session.get("usuario_nome") or session.get("usuario_username") or ""),
    )
    destino = {"aba": "metas", "aluno_id": request.form.get("aluno_id") or None}
    if not ok:
        return redirect(url_for("professor.tela_professor", erro=motivo, **destino))
    return redirect(url_for("professor.tela_professor", msg="Foco anotado.", **destino))


@professor_bp.route("/foco/remover", methods=["POST"])
def remover_foco_route():
    remover_foco(request.form.get("aluno_id", ""), request.form.get("materia", ""))
    return redirect(
        url_for(
            "professor.tela_professor",
            aba="metas",
            aluno_id=request.form.get("aluno_id") or None,
            msg="Foco removido.",
        )
    )


@professor_bp.route("/matricula", methods=["POST"])
def matricular_aluno():
    # MELHORIA: redirecionava sempre com "Aluno matriculado.", sem olhar o
    # retorno -- RA repetido, Supabase fora do ar e escola ausente na sessao
    # terminavam todos em sucesso na tela, com o aluno fora do banco.
    ok, motivo = registrar_matricula(
        escola_id=session.get("escola_id"),
        nome=request.form.get("nome", ""),
        ra_identificacao=request.form.get("ra_identificacao", ""),
        ano_escolar=request.form.get("serie", "6º Ano"),
        periodo=request.form.get("periodo", "Manhã"),
        ensino_religioso=bool(request.form.get("ensino_religioso")),
    )
    if not ok:
        return redirect(url_for("professor.tela_professor", aba="matricula", erro=motivo))
    return redirect(url_for("professor.tela_professor", aba="matricula", msg="Aluno matriculado."))


@professor_bp.route("/configuracoes", methods=["POST"])
def salvar_configuracoes():
    # MELHORIA: "Preferencias salvas." saia sem olhar o retorno.
    ok, motivo = salvar_preferencias(
        session.get("escola_id"),
        mostrar_ranking=bool(request.form.get("mostrar_ranking")),
        modo_guilda=bool(request.form.get("modo_guilda")),
    )
    if not ok:
        return redirect(url_for("professor.tela_professor", aba="configuracoes", erro=motivo))
    return redirect(url_for("professor.tela_professor", aba="configuracoes", msg="Preferencias salvas."))


@professor_bp.route("/adm/escola/criar", methods=["POST"])
def admin_criar_escola():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    nome = request.form.get("nome", "").strip()
    slug = gerar_slug(request.form.get("slug") or nome)
    if not nome or not slug:
        return _erro_no_admin(FALTAM_DADOS)

    # MELHORIA: a falha era sempre "Verifique a conexao com o Supabase." --
    # inclusive para slug repetido, que se resolve trocando o slug.
    criada, motivo = criar_escola(
        nome=nome,
        slug=slug,
        cor_tema=request.form.get("cor_tema", "#003366"),
        mostrar_ranking=bool(request.form.get("mostrar_ranking")),
        modo_guilda=bool(request.form.get("modo_guilda")),
    )
    if criada is None:
        return _erro_no_admin(motivo)
    return _redirect_admin("Escola criada.")


@professor_bp.route("/adm/escola/editar", methods=["POST"])
def admin_editar_escola():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    escola_id = request.form.get("escola_id", "")
    nome = request.form.get("nome", "").strip()
    slug = gerar_slug(request.form.get("slug", ""))
    # MELHORIA: o Streamlit ja recusava; aqui um slug apagado ia para o banco,
    # e escola sem slug nao abre (services/escola_service.py::codigo_confere).
    if not nome or not slug:
        return _erro_no_admin(FALTAM_DADOS, escola_admin_id=escola_id)

    atualizada, motivo = atualizar_escola(
        escola_id,
        {
            "nome": nome,
            "slug": slug,
            "cor_tema": request.form.get("cor_tema", "#003366"),
            "mostrar_ranking": bool(request.form.get("mostrar_ranking")),
            "modo_guilda": bool(request.form.get("modo_guilda")),
        },
    )
    if atualizada is None:
        return _erro_no_admin(motivo, escola_admin_id=escola_id)
    return _redirect_admin("Escola atualizada.")


@professor_bp.route("/adm/aluno/senha", methods=["POST"])
def admin_redefinir_senha_aluno():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    aluno_id = request.form.get("aluno_id", "").strip()
    escola_admin_id = request.form.get("escola_admin_id", "").strip()
    ok, erro, senha = redefinir_senha_do_aluno(aluno_id)
    if not ok:
        return _redirect_admin(erro)

    nome = ""
    for item in buscar_alunos(escola_admin_id) or []:
        if str(item.get("id")) == aluno_id:
            nome = str(item.get("nome") or "")
            break

    # A senha vai na mensagem porque e a UNICA vez que ela existe legivel: o
    # banco guarda so o hash. Quem redefiniu precisa anotar antes de sair.
    return _redirect_admin(f"Senha de {nome or 'aluno'} redefinida para: {senha}")


@professor_bp.route("/adm/escola/excluir", methods=["POST"])
def admin_excluir_escola():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    escola_id = request.form.get("escola_id", "")
    slug = request.form.get("slug", "")
    if request.form.get("confirmar_slug") != slug or request.form.get("confirmar_texto") != "APAGAR":
        return _erro_no_admin(CONFIRMACAO_INVALIDA, escola_admin_id=escola_id)

    excluida, motivo = excluir_escola(escola_id)
    if excluida is None:
        return _erro_no_admin(motivo, escola_admin_id=escola_id)
    return _redirect_admin("Escola excluida.")


@professor_bp.route("/pdf")
def baixar_pdf_professor():
    escola_id = session.get("escola_id")
    if not escola_id:
        return redirect(url_for("professor.tela_professor"))

    escola = _escola_atual(escola_id)
    alunos = buscar_alunos(escola_id)
    logs = buscar_logs(escola_id)
    aluno_id = request.args.get("aluno_id") or aluno_padrao(alunos, session.get("aluno_id", ""))
    modo = request.args.get("modo") or "oraculo"
    materia = request.args.get("materia") or "todas"
    aluno = next((item for item in alunos if str(item.get("id")) == str(aluno_id)), {})
    logs_recorte = filtrar_logs(logs, aluno_id, modo, materia)
    df = df_logs_revisao(logs_recorte)

    modo_label = next((item["label"] for item in MODOS_PROFESSOR if item["valor"] == modo), "Oráculo")
    materia_label = materia if materia != "todas" else "Todas as matérias"
    pdf = gerar_pdf_revisao(
        aluno.get("nome", "Aluno"),
        df,
        escola,
        "America/Sao_Paulo",
        materia_filtro=materia_label,
        serie_aluno=aluno.get("ano_escolar", ""),
        organizacao="materia",
        criterio_label=f"{modo_label} - {materia_label}",
    )

    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nome_arquivo_revisao(aluno.get("nome", "Aluno"), materia_label, modo_label),
    )


# ====================== CONTAS DE LOGIN ======================
#
# MELHORIA: "usuarios" era a unica tabela sem tela. Dava para viver assim
# enquanto a conta nao tinha escola; depois que o vinculo passou a decidir em
# que unidade ela entra, vincular professor virou UPDATE na mao no Supabase --
# e a conta nasce SEM vinculo, ou seja, nasce sem conseguir entrar.
#
# As regras moram em services/usuario_service.py, e nao aqui, porque a mesma
# tela existe no Streamlit.


@professor_bp.route("/adm/conta/criar", methods=["POST"])
def admin_criar_conta():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    ok, erro, senha = criar_conta(
        username=request.form.get("username", ""),
        papel=request.form.get("papel", ""),
        escola_id=request.form.get("escola_id", ""),
        senha=request.form.get("senha", ""),
    )
    if not ok:
        return _redirect_admin(erro)
    # A senha vai na mensagem porque e a UNICA vez que ela existe legivel: o
    # banco guarda so o hash.
    return _redirect_admin(f"Conta criada. Senha: {senha}")


@professor_bp.route("/adm/conta/escola", methods=["POST"])
def admin_vincular_conta_escola():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    ok, erro = vincular_escola(request.form.get("usuario_id", ""), request.form.get("escola_id", ""))
    return _redirect_admin(erro if not ok else "Vinculo atualizado.")


@professor_bp.route("/adm/conta/ativo", methods=["POST"])
def admin_ativar_conta():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    ativo = request.form.get("ativo") == "1"
    ok, erro = definir_ativo(request.form.get("usuario_id", ""), ativo)
    if not ok:
        return _redirect_admin(erro)
    return _redirect_admin("Conta ativada." if ativo else "Conta desativada.")


@professor_bp.route("/adm/conta/senha", methods=["POST"])
def admin_redefinir_senha_conta():
    if session.get("usuario_role") != "desenvolvedor":
        return _redirect_admin("Acesso restrito ao modo desenvolvedor.")

    ok, erro, senha = redefinir_senha_de_conta(request.form.get("usuario_id", ""))
    if not ok:
        return _redirect_admin(erro)
    return _redirect_admin(f"Senha redefinida para: {senha}")
