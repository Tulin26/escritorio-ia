from __future__ import annotations

import services.calculo_service as calc
import services.exatas_bank as exatas_bank
import services.ia_service as ia_service
import services.banks.laboratorio as lab_bank
from flask import Flask


def test_tema_padrao_laboratorio_gira_no_session_state(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})

    primeiro = calc._tema_padrao_laboratorio("Matematica", "1º Ano EM")
    segundo = calc._tema_padrao_laboratorio("Matematica", "1º Ano EM")

    assert primeiro == "equações do 2o grau e fórmula de Bhaskara"
    assert segundo == "progressão aritmética (PA)"


def test_desafio_teorico_nao_parece_calculo():
    desafio = {
        "pergunta": "Qual conceito explica melhor a lei de Newton?",
        "opcoes": ["Inercia", "Velocidade", "Calor", "Volume"],
        "formula": "",
        "subformulas": [],
        "passos_resolucao": [],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Fisica") is False


def test_desafio_numerico_parece_calculo():
    desafio = {
        "pergunta": "Um corpo de massa 4 kg acelera a 3 m/s^2. Qual e a forca resultante?",
        "opcoes": ["12 N", "10 N", "9 N", "15 N"],
        "formula": r"F = m \cdot a",
        "subformulas": [r"F = 4 \cdot 3"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "m = 4 kg, a = 3 m/s^2"},
            {"titulo": "2", "conteudo": "F = 4 * 3 = 12 N"},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante e o produto da massa pela aceleracao do corpo."}],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Fisica") is True


def test_gerar_desafio_exatas_faz_fallback_quando_ia_vem_teorica(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})

    def invocar_enigma_fake(materia, ano_escolar, nivel, tema):
        return {
            "pergunta": "Qual conceito explica melhor a lei de Newton?",
            "opcoes": ["Inercia", "Velocidade", "Calor", "Volume"],
            "correta": 0,
            "formula": "",
            "subformulas": [],
            "passos_resolucao": [],
        }

    def fallback_fake(materia, tema, nivel, contexto="lab"):
        return {
            "pergunta": "Um corpo de massa 4 kg acelera a 3 m/s^2. Qual e a forca resultante?",
            "opcoes": ["12 N", "10 N", "9 N", "15 N"],
            "correta": 0,
            "formula": r"F = m \cdot a",
            "subformulas": [r"F = 4 \cdot 3"],
            "passos_resolucao": [{"titulo": "1", "conteudo": "F = 12 N"}],
        }

    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", invocar_enigma_fake)
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "")
    monkeypatch.setattr(exatas_bank, "gerar_desafio_exatas", fallback_fake)

    resultado = calc.gerar_desafio_exatas("Fisica", "leis de Newton", "1º Ano EM", "Médio")

    assert resultado["pergunta"].startswith("Um corpo de massa 4 kg")
    assert resultado["_origem_geracao"] == "offline"


def test_gerar_desafio_exatas_escala_tem_calculo_com_resolucao(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")

    resultado = calc.gerar_desafio_exatas("Matematica", "escala", "1o Ano EM", "Medio")
    texto_passos = " ".join(passo.get("conteudo", "") for passo in resultado["passos_resolucao"])

    assert "80" in resultado["pergunta"]
    assert "100" in resultado["pergunta"]
    assert resultado["formula"]
    assert "25%" in resultado["opcoes"]
    assert "100 - 80 = 20" in texto_passos
    assert "25" in texto_passos


def test_gerar_desafio_exatas_bhaskara_nao_cai_em_porcentagem(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
    lab_bank._CICLO_OFFLINE.clear()

    resultado = calc.gerar_desafio_exatas(
        "Matematica",
        "equacoes do 2o grau e formula de Bhaskara",
        "1o Ano EM",
        "Medio",
    )

    texto = " ".join([resultado.get("tema_usado", ""), resultado.get("pergunta", ""), resultado.get("formula", "")]).lower()
    assert "porcentagem" not in texto
    assert "2o grau" in texto or "raizes" in texto or "bhaskara" in texto or "x^2" in texto


def test_bhaskara_offline_mostra_substituicao_antes_do_resultado(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
    lab_bank._CICLO_OFFLINE.clear()

    resultado = calc.gerar_desafio_exatas(
        "Matematica",
        "equacoes do 2o grau e formula de Bhaskara",
        "1o Ano EM",
        "Medio",
    )
    passos = resultado["passos_resolucao"]
    texto_passos = "\n".join(passo.get("conteudo", "") for passo in passos)

    assert len(passos) >= 4
    assert any("3" in passo.get("titulo", "") for passo in passos)
    assert r"\sqrt" in texto_passos
    assert r"\pm" in texto_passos
    assert "Resultado Final" in [passo.get("titulo") for passo in passos]


def test_bhaskara_offline_nao_repete_exercicio_recente(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
    lab_bank._CICLO_OFFLINE.clear()

    args = ("Matematica", "equacoes do 2o grau e formula de Bhaskara", "1o Ano EM", "Medio")
    primeira = calc.gerar_desafio_exatas(*args)
    segunda = calc.gerar_desafio_exatas(*args)

    assert primeira["id_offline"] != segunda["id_offline"]
    assert primeira["pergunta"] != segunda["pergunta"]


def test_bhaskara_offline_varia_varias_chamadas_seguidas(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
    lab_bank._CICLO_OFFLINE.clear()

    args = ("Matematica", "equacoes do 2o grau e formula de Bhaskara", "1o Ano EM", "Medio")
    resultados = [calc.gerar_desafio_exatas(*args) for _ in range(10)]

    assert len({resultado["id_offline"] for resultado in resultados}) == len(resultados)
    assert len({resultado["pergunta"] for resultado in resultados}) == len(resultados)


def test_bhaskara_offline_nao_repete_apos_reinicio_usando_sessao_flask(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
    lab_bank._CICLO_OFFLINE.clear()

    args = ("Matematica", "equacoes do 2o grau e formula de Bhaskara", "1o Ano EM", "Medio")
    chave = (args[0], args[1], args[3])
    primeira = calc.gerar_desafio_exatas(*args)

    app = Flask(__name__)
    app.secret_key = "teste"
    with app.test_request_context("/laboratorio/"):
        calc._set_historico(chave, [primeira["id_offline"]])
        calc.runtime.session_state = {}
        lab_bank._CICLO_OFFLINE.clear()

        segunda = calc.gerar_desafio_exatas(*args)

    assert segunda["id_offline"] != primeira["id_offline"]
    assert segunda["pergunta"] != primeira["pergunta"]


def test_banco_offline_gira_questoes_do_mesmo_tema():
    lab_bank._CICLO_OFFLINE.clear()

    primeira = lab_bank.gerar_desafio_laboratorio_offline("Matematica", "funcao exponencial", "Medio")
    segunda = lab_bank.gerar_desafio_laboratorio_offline("Matematica", "funcao exponencial", "Medio")

    assert primeira["tema_usado"] == "funcao exponencial"
    assert segunda["tema_usado"] == "funcao exponencial"
    assert primeira["id_offline"] != segunda["id_offline"]


def test_gerar_desafio_exatas_usa_banco_ef_no_fundamental(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: {})
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "IA indisponivel")

    resultado = calc.gerar_desafio_exatas("Ciencias", "velocidade", "7o Ano", "Medio")

    assert resultado["serie_tipo"] == "EF"
    assert resultado["materia"] == "Ciencias"
    assert resultado["_origem_geracao"] == "offline"
    assert resultado.get("formula")


def test_gerar_desafio_exatas_ef_aceita_ia_curricular(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})

    def invocar_enigma_fake(materia, ano_escolar, nivel, tema):
        return {
            "pergunta": "Um produto custa 80 reais e recebeu desconto de 10%. Qual e o valor do desconto?",
            "opcoes": ["8", "10", "72", "88"],
            "correta": 0,
            "formula": r"D = \frac{p}{100}\cdot V",
            "subformulas": [r"D = \frac{10}{100}\cdot 80"],
            "passos_resolucao": [
                {"titulo": "1", "conteudo": "p = 10 e V = 80"},
                {"titulo": "Resultado Final", "conteudo": "D = 10/100 * 80 = 8", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O desconto e igual a dez por cento do valor original do produto."}],
        }

    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", invocar_enigma_fake)
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "")

    resultado = calc.gerar_desafio_exatas("Matematica", "porcentagem", "6º Ano", "Medio")

    assert resultado["serie_tipo"] == "EF"
    assert resultado["_origem_geracao"] == "ia"
    assert resultado["pergunta"].startswith("Um produto custa")


def test_gerar_desafio_exatas_6o_ano_nao_usa_progressao_aritmetica(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})

    resultado = calc.gerar_desafio_exatas("Matematica", "", "6º Ano", "Medio")
    texto = " ".join(
        str(valor)
        for valor in (
            resultado.get("tema_usado", ""),
            resultado.get("enigma", ""),
            resultado.get("pergunta", ""),
        )
    ).lower()

    assert resultado["serie_tipo"] == "EF"
    assert "progress" not in texto
    assert "pa," not in texto


def test_gerar_desafio_exatas_ef_rejeita_ia_com_conteudo_de_em(monkeypatch):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    monkeypatch.setattr(
        ia_service,
        "invocar_enigma_laboratorio",
        lambda *args, **kwargs: {
            "pergunta": "Em uma PA, a1 = 13, razao = 14 e n = 17. Qual e o termo an?",
            "opcoes": ["223", "251", "265", "237"],
            "correta": 1,
            "formula": r"a_n=a_1+(n-1)r",
            "subformulas": [r"a_n=13+(17-1)14"],
            "passos_resolucao": [{"titulo": "1", "conteudo": "a_n = 237"}],
        },
    )
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "")

    resultado = calc.gerar_desafio_exatas("Matematica", "", "6º Ano", "Medio")
    texto = " ".join(
        str(valor)
        for valor in (
            resultado.get("tema_usado", ""),
            resultado.get("enigma", ""),
            resultado.get("pergunta", ""),
        )
    ).lower()

    assert resultado["serie_tipo"] == "EF"
    assert resultado["_origem_geracao"] == "offline"
    assert "progress" not in texto
    assert "pa," not in texto


def test_desafio_sem_formula_nao_parece_laboratorio_mesmo_com_numeros():
    desafio = {
        "pergunta": "Um produto esta com 15% de desconto. Se o preco original era R$ 80,00, qual e o preco final?",
        "opcoes": ["R$ 76,00", "R$ 72,00", "R$ 60,00", "R$ 68,00"],
        "correta": 1,
        "formula": "",
        "subformulas": [],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "Calcule 15% de 80."},
            {"titulo": "2", "conteudo": "Subtraia do preco original."},
        ],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False


def test_desafio_laboratorio_rejeita_resolucao_matematica_incoerente():
    desafio = {
        "pergunta": "Em uma progressao aritmetica com a1 = 2, razao 3 e n = 5, qual e o 5o termo?",
        "opcoes": ["23", "14", "17", "20"],
        "correta": 0,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "a1 = 2, r = 3 e n = 5."},
            {"titulo": "2", "conteudo": r"a_5 = 2 + (5 - 1)\cdot 3"},
            {"titulo": "Resultado Final", "conteudo": r"a_5 = 2 + 12 = 23", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "O 5o termo da progressao e 23."}],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False


def test_laboratorio_rejeita_bhaskara_com_raiz_complexa():
    desafio = {
        "pergunta": "Resolva 3x^2 + 4x + 2 = 0 usando Bhaskara.",
        "opcoes": ["x = -2/3 +/- i sqrt(2)/3", "x = 1 e 2", "x = -1 e 2", "x = 0"],
        "correta": 0,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "a = 3, b = 4 e c = 2"},
            {"titulo": "2", "conteudo": r"\Delta = 4^2 - 4\cdot 3\cdot 2 = -8"},
            {"titulo": "Resultado Final", "conteudo": r"x = \frac{-2}{3} \pm \frac{i\sqrt{2}}{3}", "final": True},
        ],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False


def test_laboratorio_rejeita_bhaskara_com_raizes_equivalentes_nas_opcoes():
    desafio = {
        "pergunta": "Encontre as raizes da equacao x^2 + 5x + 6 = 0.",
        "opcoes": [
            "x' = -4 e x'' = -1",
            "x' = -2 e x'' = -3",
            "x' = -3 e x'' = -2",
            "x' = -1 e x'' = -6",
        ],
        "correta": 1,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "a = 1, b = 5 e c = 6"},
            {"titulo": "2", "conteudo": r"\Delta = 5^2 - 4\cdot 1\cdot 6 = 1"},
            {"titulo": "Resultado Final", "conteudo": r"x' = -2 e x'' = -3", "final": True},
        ],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False


def test_laboratorio_rejeita_raizes_equivalentes_em_formato_parenteses():
    desafio = {
        "pergunta": "Encontre as soluções da equação quadrática 2x^2 + 5x - 3 = 0 utilizando a fórmula de Bhaskara.",
        "opcoes": ["(0.5, -3)", "(-1, 1.5)", "(-3, 0.5)", "(1, -1.5)"],
        "correta": 0,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "a = 2, b = 5 e c = -3"},
            {"titulo": "2", "conteudo": r"\Delta = 5^2 - 4\cdot 2\cdot (-3) = 49"},
            {"titulo": "Resultado Final", "conteudo": "x = 0.5 e x = -3", "final": True},
        ],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False


def test_laboratorio_rejeita_formula_de_bhaskara_sem_b_ao_quadrado():
    desafio = {
        "pergunta": "Resolva 1x^2 - 7x + 12 = 0 usando Bhaskara.",
        "opcoes": ["3 e 4", "2 e 6", "1 e 12", "4 e 5"],
        "correta": 0,
        "formula": r"x = \frac{-b \pm \sqrt{b - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"titulo": "1", "conteudo": "a = 1, b = -7 e c = 12"},
            {"titulo": "2", "conteudo": r"\Delta = (-7)^2 - 4\cdot 1\cdot 12 = 1"},
        ],
    }

    assert calc._desafio_parece_calculo_laboratorio(desafio, "Matematica") is False
