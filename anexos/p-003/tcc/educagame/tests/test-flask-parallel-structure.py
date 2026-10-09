from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flask_app_principal_registra_blueprints():
    flask_app = (ROOT / "flask_app.py").read_text(encoding="utf-8")

    assert "def criar_app" in flask_app
    assert "app.run" in flask_app
    assert 'os.getenv("PORT"' in flask_app
    assert "register_blueprint" in flask_app

    # MELHORIA: aqui se exigia que app.py NAO existisse -- os dois frontends
    # viviam em branches separadas, com copias proprias de core/ e services/,
    # e foi assim que a main apagou duas vezes codigo que so o Streamlit
    # usava. Agora eles convivem no mesmo repositorio; o que precisa valer e
    # que os pontos de entrada nao se confundem.
    assert "streamlit" not in flask_app.lower()
    if (ROOT / "app.py").exists():
        app_streamlit = (ROOT / "app.py").read_text(encoding="utf-8")
        assert "import streamlit" in app_streamlit
        assert "flask" not in app_streamlit.lower()


def test_oraculo_flask_reaproveita_servicos_do_projeto():
    rota = (ROOT / "web" / "routes" / "oraculo_fla.py").read_text(encoding="utf-8")
    helpers = (ROOT / "web" / "routes" / "flask_helpers_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "oraculo.html").read_text(encoding="utf-8")

    assert "invocar_enigma" in rota
    assert "buscar_aluno_por_id" in helpers
    assert "registrar_log" in rota
    assert "oraculo-flask" in rota
    assert "Gerar novo desafio" in template
    assert 'name="materia" value="{{ enigma.get' in template

    # MELHORIA: aqui havia `assert "A IA" in helpers` e `"retornou" in
    # helpers`. Isso amarrava a FRASE do aviso ao arquivo em que ela morava --
    # e ela mudou de lugar (core/origem_questao.py, agora compartilhada com o
    # Streamlit) e de redação, porque "A IA não retornou..." conta o problema
    # sem dizer ao aluno o que fazer. O teste reprovava a melhoria.
    #
    # O que importa é que o helper CONTINUE produzindo o aviso: isso é
    # comportamento, e sobrevive à próxima reescrita do texto.
    from web.routes.flask_helpers_fla import aviso_offline

    assert aviso_offline({"_origem_geracao": "offline"}), "o Oráculo perdeu o aviso de origem"
    assert not aviso_offline({"_origem_geracao": "ia"})


def test_oraculo_flask_nao_pede_ano_escolar_manual():
    template = (ROOT / "web" / "templates" / "oraculo.html").read_text(encoding="utf-8")
    partial = (ROOT / "web" / "templates" / "partials" / "student_selector.html").read_text(encoding="utf-8")

    assert 'name="ano_escolar"' not in template
    assert "Ano escolar carregado do aluno" in partial


def test_mods_escondem_formulario_de_resposta_apos_resultado():
    templates = [
        ROOT / "web" / "templates" / "oraculo.html",
        ROOT / "web" / "templates" / "treino.html",
        ROOT / "web" / "templates" / "laboratorio.html",
        ROOT / "web" / "templates" / "escape_room.html",
        ROOT / "web" / "templates" / "enem.html",
        ROOT / "web" / "templates" / "boss_rush.html",
        ROOT / "web" / "templates" / "rpg.html",
    ]

    for template_path in templates:
        template = template_path.read_text(encoding="utf-8")
        assert 'partials/options_form.html' not in template or "{% if not resultado %}" in template or "{% if not estado.resultado %}" in template


def test_oraculo_mostra_apenas_botao_novo_desafio_apos_resultado():
    template = (ROOT / "web" / "templates" / "oraculo.html").read_text(encoding="utf-8")

    assert "{% if not resultado %}" in template
    assert "Nova questão" in template
    assert "Gerar novo desafio" in template
    assert "compact-form" in template


def test_laboratorio_mostra_apenas_botao_novo_experimento_apos_resultado():
    template = (ROOT / "web" / "templates" / "laboratorio.html").read_text(encoding="utf-8")

    assert "{% if not resultado %}" in template
    assert "{% if not desafio or resultado %} single{% endif %}" in template
    assert "Gerar novo experimento" in template
    assert "compact-form" in template


def test_rpg_esconde_painel_campanha_durante_estado_ativo():
    template = (ROOT / "web" / "templates" / "rpg.html").read_text(encoding="utf-8")

    assert "{% elif not estado %}" in template
    assert "Iniciar nova aventura" in template


def test_rpg_resultado_quebra_resposta_do_aluno_e_correta():
    template = (ROOT / "web" / "templates" / "rpg.html").read_text(encoding="utf-8")

    assert "<strong>Sua resposta:</strong>" in template
    assert "<strong>Resposta correta:</strong>" in template
    assert "Sua resposta: {{ estado.resultado.resposta_aluno }}. Correta:" not in template


def test_rpg_prepara_passos_de_exatas_para_mathjax():
    from web.routes.rpg_fla import _preparar_desafio

    desafio = _preparar_desafio(
        {
            "pergunta": "Um corpo percorre 20 m em 4 s. Qual e a velocidade media?",
            "formula": r"v = \frac{d}{t}",
            "subformulas": [],
            "passos_resolucao": [
                {"titulo": "Resultado Final", "conteudo": r"v = \frac{20 m}{4 s} = 5 m/s", "final": True},
            ],
        },
        "Fisica",
    )

    assert desafio["formula_latex"] == r"v = \frac{d}{t}"
    assert desafio["passos_template"][0]["conteudo_latex"]
    assert r"\mathrm{m}" in desafio["passos_template"][0]["conteudo_latex"]


def test_templates_flask_tem_home_e_oraculo():
    assert (ROOT / "web" / "templates" / "home.html").exists()
    assert (ROOT / "web" / "templates" / "oraculo.html").exists()
    assert (ROOT / "web" / "templates" / "laboratorio.html").exists()
    assert (ROOT / "web" / "templates" / "treino.html").exists()
    assert (ROOT / "web" / "templates" / "enem.html").exists()
    assert (ROOT / "web" / "templates" / "progresso.html").exists()
    assert (ROOT / "web" / "templates" / "professor.html").exists()
    assert (ROOT / "web" / "templates" / "boss_rush.html").exists()
    assert (ROOT / "web" / "templates" / "escape_room.html").exists()
    assert (ROOT / "web" / "templates" / "partials" / "student_selector.html").exists()
    assert (ROOT / "web" / "routes" / "flask_helpers_fla.py").exists()
    assert (ROOT / "web" / "static" / "css" / "flask.css").exists()


def test_laboratorio_flask_usa_nome_correto_e_servico_exatas():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "laboratorio_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "laboratorio.html").read_text(encoding="utf-8")

    assert "laboratorio_bp" in app
    assert "gerar_desafio_exatas" in rota
    assert "laboratorio-flask" in rota
    assert "Laboratório de Exatas" in template
    assert "name=\"ano_escolar\"" not in template
    assert "Onde isso aparece no dia a dia" not in template
    assert "materia_selecionada" in rota
    assert "materia.valor == materia_selecionada" in template
    assert "nivel_selecionado" in template


def test_laboratorio_flask_formata_pergunta_com_equacao():
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas
    from web.routes.laboratorio_fla import _preparar_desafio_para_template

    pergunta = "No tema equacoes do 2o grau e formula de Bhaskara, quais são as raízes de 1x^2 - 7x + 12 = 0?"
    resultado = formatar_pergunta_exatas(pergunta)

    assert "2º grau" in resultado["texto"]
    assert "fórmula" in resultado["texto"]
    assert "1x" not in resultado["latex"]
    assert "x^2" in resultado["latex"]
    assert resultado["latex"].endswith("?")
    assert resultado["sufixo"] == ""

    desafio = _preparar_desafio_para_template(
        {
            "pergunta": pergunta,
            "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
            "subformulas": [],
            "passos_resolucao": [
                {
                    "titulo": "1",
                    "conteudo": r"Substituir os valores na formula de Bhaskara: x = \frac{-4 \pm \sqrt{4}}{2}",
                }
            ],
        }
    )

    passo = desafio["passos_template"][0]
    assert passo["conteudo_texto"] == "Substituir os valores na fórmula de Bhaskara"
    assert r"\frac" in passo["conteudo_latex"]


def test_formatar_pergunta_exatas_nao_deixa_pontuacao_solitaria():
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    pergunta = "Quais sao as raizes de x^2 - 44x + 483 = 0?"
    resultado = formatar_pergunta_exatas(pergunta)

    assert resultado["latex"].endswith("?")
    assert resultado["sufixo"] == ""

    com_sufixo = formatar_pergunta_exatas(
        "Para calibrar um simulador, e preciso resolver 3x^2 - 6x - 1584 = 0. Qual alternativa apresenta as duas raizes?"
    )

    assert com_sufixo["latex"] == "3x^2 - 6 x - 1584 = 0"
    # MELHORIA: o enunciado agora passa por aplicar_acentos_pt, entao o
    # sufixo chega acentuado ao aluno em vez de "raizes".
    assert com_sufixo["sufixo"] == "Qual alternativa apresenta as duas raízes?"


def test_formatar_pergunta_exatas_preserva_sufixo_textual():
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    equacao = formatar_pergunta_exatas("Resolva x^2 - 5x + 6 = 0 usando Bhaskara.")
    ph = formatar_pergunta_exatas("Se [H+] = 10^{-3} mol/L, qual e o pH da solucao?")

    assert equacao["texto"] == "Resolva"
    assert equacao["latex"] == "x^2 - 5 x + 6 = 0"
    assert equacao["sufixo"] == "usando Bhaskara."
    assert ph["texto"] == "Se"
    assert ph["latex"] == r"[H^+] = 10^{-3}\,\mathrm{mol/L}"
    assert ph["sufixo"] == "qual é o pH da solução?"


def test_laboratorio_flask_quebra_atribuicoes_delta_em_linhas():
    from web.routes.laboratorio_fla import _preparar_desafio_para_template

    desafio = _preparar_desafio_para_template(
        {
            "pergunta": "Um carro vai de 0 m/s a 25 m/s em 5 s. Qual e a aceleracao?",
            "formula": r"a = \frac{\Delta v}{\Delta t}",
            "subformulas": [],
            "opcoes": ["5 m/s^2", "10 m/s^2", "20 m/s^2", "25 m/s^2"],
            "passos_resolucao": [
                {
                    "titulo": "1º Passo",
                    "conteudo": r"Identificar os valores: \Delta v = 25 m/s - 0 m/s = 25 m/s \Delta t = 5 s",
                },
                {
                    "titulo": "2º Passo",
                    "conteudo": r"a = 25 m/s / 5 s = 5 m/s^2",
                },
            ],
        }
    )

    primeiro_passo = desafio["passos_template"][0]["conteudo_latex"]
    segundo_passo = desafio["passos_template"][1]["conteudo_latex"]

    assert r"\begin{aligned}" in primeiro_passo
    assert r"\\ \Delta t" in primeiro_passo
    assert "ext" not in primeiro_passo
    assert r"\mathrm{m/s}" in segundo_passo


def test_laboratorio_flask_aceita_raizes_em_ordem_trocada():
    from core.answer_equivalence import respostas_equivalentes

    assert respostas_equivalentes("x' = -3 e x'' = -2", "x' = -2 e x'' = -3")


def test_templates_flask_usam_partials_compartilhados():
    oraculo = (ROOT / "web" / "templates" / "oraculo.html").read_text(encoding="utf-8")
    laboratorio = (ROOT / "web" / "templates" / "laboratorio.html").read_text(encoding="utf-8")
    treino = (ROOT / "web" / "templates" / "treino.html").read_text(encoding="utf-8")

    for template in (oraculo, laboratorio, treino):
        assert 'partials/student_context.html' in template
        assert 'partials/student_selector.html' in template
        assert 'partials/options_form.html' in template
        assert 'partials/result_card.html' in template


def test_treino_flask_cria_sessao_com_multiplas_questoes():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "treino_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "treino.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")

    assert "treino_bp" in app
    assert "invocar_enigma" in rota
    assert "registrar_log_com_tempo" in rota
    assert "treino-flask" in rota
    assert "proxima_questao" in rota
    assert "Treino Rápido" in template
    assert "url_for('treino.tela_treino')" in base
    assert 'name="ano_escolar"' not in template


def test_enem_flask_reaproveita_servico_enem_e_logs():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "enem_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "enem.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")

    assert "enem_bp" in app
    assert "gerar_questao_enem" in rota
    assert "montar_sequencia_questoes" in rota
    assert "registrar_log_com_tempo" in rota
    assert "enem-flask" in rota
    assert "Simulado ENEM" in template
    assert "url_for('enem.tela_enem')" in base
    assert 'name="ano_escolar"' not in template


def test_progresso_flask_usa_logs_e_ranking():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "progresso_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "progresso.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")

    assert "progresso_bp" in app
    assert "buscar_logs" in rota
    assert "buscar_ranking" in rota
    assert "Ranking e progresso" in template
    assert "Histórico recente" in template
    assert "url_for('progresso.tela_progresso')" in base


def test_perfil_flask_tem_badges_e_metricas_do_aluno():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "perfil_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "perfil.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    home = (ROOT / "web" / "templates" / "home.html").read_text(encoding="utf-8")

    assert "perfil_bp" in app
    assert "calcular_badges" in rota
    assert "streak_acertos" in rota
    assert "buscar_logs" in rota
    assert "Perfil do Aluno" in template
    assert "badge-grid" in template
    assert "url_for('perfil.tela_perfil')" in base
    assert "url_for('perfil.tela_perfil')" in home


def test_seletor_de_aluno_filtra_materias_por_etapa_no_frontend():
    partial = (ROOT / "web" / "templates" / "partials" / "student_selector.html").read_text(encoding="utf-8")
    oraculo = (ROOT / "web" / "templates" / "oraculo.html").read_text(encoding="utf-8")
    laboratorio = (ROOT / "web" / "templates" / "laboratorio.html").read_text(encoding="utf-8")

    assert "filtrarMaterias" in partial
    assert "select[name=\"materia\"], select[name=\"materias_salas\"]" in partial
    assert 'data-ef="{{ 1 if materia.permitida_ef else 0 }}"' in oraculo
    assert 'data-em="{{ 1 if materia.permitida_em else 0 }}"' in laboratorio


def test_feedback_pedagogico_flask_aparece_nos_resultados():
    partial = (ROOT / "web" / "templates" / "partials" / "result_card.html").read_text(encoding="utf-8")
    rpg_template = (ROOT / "web" / "templates" / "rpg.html").read_text(encoding="utf-8")

    assert "Feedback pedagógico" in partial
    assert "resultado.feedback.confundiu" in partial
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "treino_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "oraculo_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "laboratorio_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "enem_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "boss_rush_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "escape_room_fla.py").read_text(encoding="utf-8")
    assert "gerar_feedback_pedagogico" in (ROOT / "web" / "routes" / "rpg_fla.py").read_text(encoding="utf-8")
    assert "estado.resultado.feedback.confundiu" in rpg_template


def test_texto_explicacao_oraculo_aplica_acentos_do_banco_offline():
    from web.routes.flask_helpers_fla import texto_explicacao

    explicacao = texto_explicacao(
        [
            {"tipo": "bold", "conteudo": "Conceito em foco (EM13MAT101)"},
            {"tipo": "texto", "conteudo": "Em razoes e proporcoes, o ponto principal e representar relacoes, padroes e propriedades para interpretar uma situacao."},
            {"tipo": "texto", "conteudo": "No Oraculo, a questao prioriza compreensao teorica; contas e formulas ficam para o Laboratorio de Exatas."},
            {"tipo": "resultado", "conteudo": "A alternativa correta explica o conceito, nao apenas um procedimento de calculo."},
        ]
    )

    assert "razões e proporções" in explicacao
    assert "relações, padrões e propriedades" in explicacao
    assert "situação" in explicacao
    assert "Oráculo" in explicacao
    assert "questão prioriza compreensão teórica" in explicacao
    assert "não apenas um procedimento de cálculo" in explicacao


def test_texto_explicacao_formata_notacao_matematica_crua():
    from web.routes.flask_helpers_fla import texto_explicacao

    explicacao = texto_explicacao(
        [
            {
                "tipo": "texto",
                "conteudo": "Se a^b = c, entao log_a(c) = b.",
            }
        ]
    )

    assert "a elevado a b = c" in explicacao
    assert "log base a de c = b" in explicacao
    assert "a^b" not in explicacao
    assert "log_a" not in explicacao


def test_texto_explicacao_remove_rotulo_questao_autoral():
    from web.routes.flask_helpers_fla import texto_explicacao

    explicacao = texto_explicacao(
        [
            {"tipo": "bold", "conteudo": "Questao autoral (EM13MAT101)"},
            {"tipo": "texto", "conteudo": "Use a variacao percentual."},
        ]
    )

    assert "autoral" not in explicacao.lower()
    assert "Habilidade BNCC: EM13MAT101" in explicacao
    assert "varia" in explicacao


def test_resultado_usa_bloco_de_explicacao_sem_pre():
    partial = (ROOT / "web" / "templates" / "partials" / "result_card.html").read_text(encoding="utf-8")
    rpg = (ROOT / "web" / "templates" / "rpg.html").read_text(encoding="utf-8")

    assert "result-explanation" in partial
    assert "<pre>{{ explicacao_texto }}</pre>" not in partial
    assert "result-explanation" in rpg


def test_pontuacao_flask_por_dificuldade():
    from web.routes.flask_helpers_fla import perda_pontuacao_por_dificuldade, pontuacao_por_dificuldade

    assert pontuacao_por_dificuldade("FÃ¡cil") == 10
    assert pontuacao_por_dificuldade("Medio") == 20
    assert pontuacao_por_dificuldade("DifÃ­cil") == 30
    assert perda_pontuacao_por_dificuldade("FÃ¡cil") == 5
    assert perda_pontuacao_por_dificuldade("Medio") == 10
    assert perda_pontuacao_por_dificuldade("Dificil") == 15


def test_registrar_pontuacao_flask_calcula_mas_nao_soma(monkeypatch):
    """O banco soma (gatilho no INSERT do log); o app so calcula para a tela.

    Somar aqui tambem era contagem em dobro: 510 pontos numa conta que valia
    355, medido em 13/09/2026.
    """
    from web.routes import flask_helpers_fla as helpers

    limpezas = []
    monkeypatch.setattr(helpers, "limpar_caches_de_pontos", lambda: limpezas.append(True))

    assert helpers.registrar_pontuacao_acerto("aluno-1", False, "Médio") == -10
    assert helpers.registrar_pontuacao_acerto("aluno-1", True, "Difícil") == 30
    assert limpezas == [True, True], "o ranking em cache mostraria o total velho"
    assert not hasattr(helpers, "somar_pontos_aluno"), "voltou a somar no app"


def test_sem_aluno_nao_ha_pontos_nem_cache_a_renovar(monkeypatch):
    from web.routes import flask_helpers_fla as helpers

    limpezas = []
    monkeypatch.setattr(helpers, "limpar_caches_de_pontos", lambda: limpezas.append(True))

    assert helpers.registrar_pontuacao_acerto(None, True, "Médio") == 0
    assert limpezas == []


def test_home_nao_mostra_selecao_de_aluno_nem_ranking():
    rota = (ROOT / "web" / "routes" / "home_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "home.html").read_text(encoding="utf-8")

    assert "Selecionar aluno" not in template
    assert "Ranking rapido" not in template
    assert "Ranking rápido" not in template
    assert "item.pontos_totais" not in template
    assert "buscar_alunos" not in rota
    assert "buscar_ranking" not in rota


def test_professor_flask_usa_dados_da_escola():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "professor_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "professor.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    home = (ROOT / "web" / "routes" / "home_fla.py").read_text(encoding="utf-8")

    assert "professor_bp" in app
    assert "buscar_alunos" in rota
    assert "buscar_logs" in rota
    assert "gerar_pdf_revisao" in rota
    assert "baixar_pdf_professor" in rota
    assert "Desempenho dos Alunos" in template
    assert "Baixar PDF" in template
    assert "url_for('professor.tela_professor')" in base
    # MELHORIA: desde a area de login por papel, quem entra como aluno so
    # ve a grade de jogos em home.html — o link pro painel do professor
    # saiu de la. home.index() e quem redireciona professor/desenvolvedor
    # direto pro painel, entao a referencia relevante agora e essa rota.
    assert "professor.tela_professor" in home


def test_professor_flask_tem_abas_de_gestao_e_servico_dedicado():
    rota = (ROOT / "web" / "routes" / "professor_fla.py").read_text(encoding="utf-8")
    servico = (ROOT / "services" / "professor_service.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "professor.html").read_text(encoding="utf-8")

    assert "import pandas" not in rota
    assert "import pandas" in servico
    for aba in ("analises", "rpg", "matricula", "ranking", "resumo", "configuracoes", "adm"):
        assert f'"{aba}"' in servico
    assert "teacher-tabs" in template
    assert "salvar_rpg_config_route" in rota
    assert "matricular_aluno" in rota


def test_rpg_flask_nao_guarda_estado_inteiro_no_cookie_de_sessao():
    rota = (ROOT / "web" / "routes" / "rpg_fla.py").read_text(encoding="utf-8")

    assert "session[_estado_key" not in rota
    assert "_RPG_ESTADOS_LOCAIS" in rota
    assert "salvar_progresso_rpg" in rota


def test_render_flask_usa_dependencias_proprias():
    requirements = (ROOT / "requirements_flask.txt").read_text(encoding="utf-8").lower()
    runtime = (ROOT / "core" / "runtime_context.py").read_text(encoding="utf-8")
    procfile = (ROOT / "Procfile").read_text(encoding="utf-8")
    render_yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "flask" in requirements
    assert "gunicorn" in requirements
    assert "get_runtime" in runtime
    assert (ROOT / "requirements.txt").exists()

    # MELHORIA: requirements.txt era so um ponteiro para requirements_flask.txt.
    # Com os dois frontends no mesmo repositorio ele passou a ser o do
    # Streamlit Cloud, que le esse nome por convencao fixa; o Flask tem o
    # proprio arquivo e os dois herdam requirements_base.txt -- uma copia so
    # da lista compartilhada, que antes vivia duplicada e saia do lugar.
    requirements_st = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "streamlit" in requirements_st
    assert "requirements_base.txt" in requirements_st
    assert "requirements_base.txt" in requirements

    assert "gunicorn flask_app:app" in procfile
    assert "pip install -r requirements_flask.txt" in render_yaml
    assert "gunicorn flask_app:app" in render_yaml
    assert "healthCheckPath: /healthz" in render_yaml


def test_importar_flask_app_funciona_com_runtime_neutro():
    import importlib
    import sys

    sys.modules.pop("flask_app", None)

    modulo = importlib.import_module("flask_app")

    assert hasattr(modulo, "app")


def test_estados_grandes_do_flask_ficam_fora_do_cookie(monkeypatch):
    from flask import session

    from web.routes import flask_helpers_fla
    from flask_app import app

    # MELHORIA: o estado de fluxo (treino/oraculo/laboratorio) foi migrado do
    # dict em memoria de processo para o Supabase (ver repositories/database_repo.py).
    # O teste original validava o mecanismo antigo de "*_ref" na sessao; agora
    # simulamos o Supabase com um dict simples para testar o mesmo objetivo
    # (payload grande nao vai pro cookie, e o roundtrip salvar/reler funciona)
    # sem depender de rede real.
    armazenamento_fake: dict[str, dict] = {}

    def _salvar_fake(chave, estado):
        armazenamento_fake[chave] = estado
        return True

    def _carregar_fake(chave):
        return armazenamento_fake.get(chave)

    monkeypatch.setattr(flask_helpers_fla, "salvar_estado_temporario", _salvar_fake)
    monkeypatch.setattr(flask_helpers_fla, "carregar_estado_temporario", _carregar_fake)

    payload = {
        "pergunta": " ".join(f"pergunta-{i}-com-contexto-variado" for i in range(600)),
        "opcoes": [
            " ".join(f"opcao-{idx}-{i}-texto-variado" for i in range(120))
            for idx in range(4)
        ],
        "explicacao": [
            {"tipo": "texto", "conteudo": " ".join(f"explicacao-{i}-{j}" for j in range(120))}
            for i in range(4)
        ],
    }

    with app.test_request_context("/"):
        flask_helpers_fla.salvar_estado_flask("treino_flask", payload)
        serializer = app.session_interface.get_signing_serializer(app)
        cookie_bytes = len(serializer.dumps(dict(session)).encode("utf-8"))

        assert cookie_bytes < 1024
        assert "treino_flask" not in session
        assert session.get("_estado_sid")
        assert flask_helpers_fla.obter_estado_flask("treino_flask") == payload


def test_home_flask_tem_healthcheck_e_nao_404_quando_slug_falta():
    rota = (ROOT / "web" / "routes" / "home_fla.py").read_text(encoding="utf-8")

    assert "@home_bp.route(\"/healthz\")" in rota
    # Sem slug na sessao a home mostra a lista de escolas; nao ha mais
    # escola padrao por ambiente para "resolver" isso por baixo.
    assert "selecionar_escola.html" in rota
    assert "), 200" in rota


def test_boss_rush_flask_usa_servico_enem_com_vidas():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "boss_rush_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "boss_rush.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    home = (ROOT / "web" / "templates" / "home.html").read_text(encoding="utf-8")

    assert "boss_rush_bp" in app
    assert "gerar_questao_enem" in rota
    assert "vidas" in rota
    assert "boss_rush_enem-flask" in rota
    assert "Batalha contra Chefes ENEM" in template
    assert "url_for('boss_rush.tela_boss_rush')" in base
    assert "url_for('boss_rush.tela_boss_rush')" in home


def test_escape_room_flask_usa_enigmas_em_salas():
    app = (ROOT / "flask_app.py").read_text(encoding="utf-8")
    rota = (ROOT / "web" / "routes" / "escape_room_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "escape_room.html").read_text(encoding="utf-8")
    base = (ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    home = (ROOT / "web" / "templates" / "home.html").read_text(encoding="utf-8")

    assert "escape_room_bp" in app
    assert "invocar_enigma" in rota
    assert "escape_room-flask" in rota
    assert "pistas" in rota
    assert "Escape Room" in template
    assert "url_for('escape_room.tela_escape_room')" in base
    assert "url_for('escape_room.tela_escape_room')" in home


def test_escape_room_flask_permite_materia_por_sala():
    from web.routes.escape_room_fla import _materias_das_salas

    rota = (ROOT / "web" / "routes" / "escape_room_fla.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "escape_room.html").read_text(encoding="utf-8")

    # MELHORIA: o contrato era um nome SÓ para os seis campos
    # ("materias_salas") lido por posição com getlist. Campo que não chega ao
    # servidor sumia da lista e deslocava todas as salas seguintes -- achado
    # 3.3 do relatório de QA de 23/09/2026. Agora cada sala tem o campo dela.
    assert 'name="materia_sala_{{ numero }}"' in template
    assert 'name="materias_salas"' not in template
    assert "data-room-index" in template
    assert '_materias_enviadas(total)' in rota

    materias = _materias_das_salas(
        ["Matematica", "Historia", "Biologia", "Ingles", "Quimica"],
        5,
        "Matematica",
    )

    assert materias == ["Matematica", "Historia", "Biologia", "Ingles", "Quimica"]
