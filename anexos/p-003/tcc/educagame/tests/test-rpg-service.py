"""
Testes unitários para services/rpg_service.py — funções puras.

Execute com: pytest tests/test_rpg_service.py -v
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCalcularResultadoDesafio:
    """Testa o cálculo de HP e XP após um desafio RPG."""

    def _importar(self):
        from services import rpg_service
        return rpg_service

    def test_acerto_concede_xp(self):
        rpg = self._importar()
        estado = {"hp": 100, "xp": 0, "fase_atual": 1, "total_fases": 5}
        novo = rpg.aplicar_resultado_desafio(estado, acertou=True)
        assert novo["xp"] > 0

    def test_erro_reduz_hp(self):
        rpg = self._importar()
        estado = {"hp": 100, "xp": 0, "fase_atual": 1, "total_fases": 5}
        novo = rpg.aplicar_resultado_desafio(estado, acertou=False)
        assert novo["hp"] < 100

    def test_hp_nao_fica_negativo(self):
        rpg = self._importar()
        estado = {"hp": 5, "xp": 0, "fase_atual": 1, "total_fases": 5}
        novo = rpg.aplicar_resultado_desafio(estado, acertou=False)
        assert novo["hp"] >= 0

    def test_xp_nao_fica_negativo(self):
        rpg = self._importar()
        estado = {"hp": 100, "xp": 0, "fase_atual": 1, "total_fases": 5}
        novo = rpg.aplicar_resultado_desafio(estado, acertou=False)
        assert novo["xp"] >= 0


class TestNarrativaRpg:
    def _importar(self):
        from services import rpg_service
        return rpg_service

    def test_opcoes_consideram_jornada_anterior(self):
        rpg = self._importar()
        jornada = rpg.criar_jornada_inicial()
        escolha = {
            "rota": "Galeria dos Ecos",
            "recurso": "Mapa parcial da masmorra",
            "foco_aprendizado": "interpretacao de pistas",
            "impacto_destino": "Conhecimento",
        }
        jornada = rpg.registrar_escolha_jornada(jornada, escolha, 1)

        opcoes = rpg._criar_opcoes(2, "Quimica", jornada, [{"rota": "Galeria dos Ecos", "status": "Sucesso"}])
        texto = " ".join(f"{opcao['texto']} {opcao['consequencia_imediata']}" for opcao in opcoes)

        assert "Galeria dos Ecos" in texto
        assert "Mapa parcial da masmorra" in texto
        assert "interpretação de pistas" in texto

    def test_jornada_inicial_tem_story_state_immersivo(self):
        rpg = self._importar()

        jornada = rpg.criar_jornada_inicial("Matematica", "Laboratorio Amaldicoado")
        story = jornada["story_state"]
        opcoes = rpg._criar_opcoes(1, "Matematica", jornada, [])
        texto_opcoes = " ".join(opcao["texto"] for opcao in opcoes).lower()

        assert "antagonista" in story
        assert "objetivo" in story
        assert "ameaca" in story
        assert "compasso" in story["reliquia"].lower()
        assert "aplicar a valida" not in texto_opcoes
        assert "desenvolver uma estrategia" not in texto_opcoes

    def test_continuar_aventura_conta_consequencias_anteriores(self):
        rpg = self._importar()
        with patch.object(rpg, "gerar_json_ia", return_value=None):
            cena = self._continuar_aventura_com_memoria(rpg)

        assert "fase" in cena["local_atual"].lower()
        assert "marcas reais na masmorra" in cena["narracao"]
        assert "Mapa parcial da masmorra" in cena["narracao"]
        assert "Galeria dos Ecos" in cena["narracao"]

    def test_continuar_aventura_usa_ia_para_narrativa_quando_disponivel(self):
        rpg = self._importar()
        # A IA responde sobre as rotas que recebeu, entao o teste cobre todas
        # em vez de fixar uma: assim ele verifica que o texto da IA substitui
        # o do molde, sem depender de QUAIS rotas o sorteio escolheu.
        dados_ia = {
            "local_atual": "Observatorio do Cobre Vivo",
            "narracao": "As marcas da Galeria dos Ecos brilham no mapa, e a equipe percebe que a proxima porta reage ao modo como investigaram as pistas de Quimica.",
            "opcoes": [
                {
                    "rota": rota["rota"],
                    "texto": "Regular as valvulas de cobre usando a pista encontrada na galeria.",
                    "consequencia_imediata": "Se funcionar, a equipe transforma a pista anterior em passagem segura.",
                }
                for rota in rpg.ROTAS
            ],
        }

        with patch.object(rpg, "gerar_json_ia", return_value=dados_ia):
            cena = self._continuar_aventura_com_memoria(rpg)

        assert cena["_origem_narrativa"] == "ia"
        assert cena["local_atual"] == "Observatório do Cobre Vivo"
        assert "marcas da Galeria dos Ecos" in cena["narracao"]
        assert "próxima porta" in cena["narracao"]
        assert "Química" in cena["narracao"]
        assert any("válvulas de cobre" in opcao["texto"] for opcao in cena["opcoes"])

    def test_narrativa_ia_generica_cai_no_fallback(self):
        rpg = self._importar()
        dados_ia = {
            "local_atual": "Sala de Reflexao",
            "narracao": "É importante considerar os recursos disponíveis e planejar o próximo passo.",
            "opcoes": [{"rota": "Torre do Debate", "texto": "Avancar.", "consequencia_imediata": "Planejar."}],
        }

        with patch.object(rpg, "gerar_json_ia", return_value=dados_ia):
            cena = self._continuar_aventura_com_memoria(rpg)

        assert cena.get("_origem_narrativa") != "ia"
        assert "marcas reais na masmorra" in cena["narracao"]

    def test_normaliza_ortografia_da_cena_rpg(self):
        rpg = self._importar()

        cena = rpg.normalizar_textos_cena(
            {
                "local_atual": "Sala de Reacao",
                "narracao": "O grupo confia mais na interpretacao de pistas e encontra uma nova area com equipamentos quimicos.",
                "opcoes": [
                    {
                        "texto": "Cruzar a area protegida antes da proxima decisao.",
                        "consequencia_imediata": "A confianca ajuda a avancar.",
                        "rota": "Camara Rubra",
                        "foco_aprendizado": "resolucao sob pressao",
                    }
                ],
            }
        )

        assert cena["local_atual"] == "Sala de Reação"
        assert "interpretação de pistas" in cena["narracao"]
        assert "área" in cena["narracao"]
        assert "químicos" in cena["narracao"]
        assert "próxima decisão" in cena["opcoes"][0]["texto"]
        assert "confiança" in cena["opcoes"][0]["consequencia_imediata"]
        assert cena["opcoes"][0]["rota"] == "Câmara Rubra"

    def test_desafio_academico_de_exatas_usa_gerador_de_calculo(self, monkeypatch):
        rpg = self._importar()
        from services import calculo_service

        chamadas = []

        def gerar_fake(materia, tema, ano_escolar, nivel):
            chamadas.append((materia, tema, ano_escolar, nivel))
            return {
                "enigma": "Porta numerica",
                "pergunta": "Um corpo percorre 20 m em 4 s. Qual e a velocidade media?",
                "opcoes": ["5 m/s", "4 m/s", "10 m/s", "2 m/s"],
                "correta": 0,
                "formula": r"v = \frac{d}{t}",
                "subformulas": [],
                "legenda_variaveis": "v: velocidade, d: distancia, t: tempo.",
                "passos_resolucao": [
                    {"titulo": "1o Passo", "conteudo": "d = 20 m, t = 4 s"},
                    {"titulo": "Resultado Final", "conteudo": r"v = \frac{20 m}{4 s} = 5 m/s", "final": True},
                ],
                "_origem_geracao": "offline",
            }

        monkeypatch.setattr(calculo_service, "gerar_desafio_exatas", gerar_fake)

        desafio = rpg.gerar_desafio_academico(
            {"materia": "Fisica", "serie": "1o Ano EM", "nivel": "Medio"},
            "Ponte das Engrenagens",
            "A cena",
            [],
            None,
            None,
        )

        assert chamadas
        assert desafio["formula"] == r"v = \frac{d}{t}"
        assert desafio["passos_resolucao"]
        assert desafio["tema_usado"]

    def test_desafio_matematica_em_varia_temas_e_mistura_teoria(self, monkeypatch):
        rpg = self._importar()
        from services import calculo_service

        def gerar_fake(materia, tema, ano_escolar, nivel):
            return {
                "enigma": f"Porta numerica de {tema}",
                "pergunta": f"Calcule algo sobre {tema}.",
                "opcoes": ["1", "2", "3", "4"],
                "correta": 0,
                "formula": "x = 1",
                "subformulas": [],
                "legenda_variaveis": "x: valor.",
                "passos_resolucao": [{"titulo": "Resultado Final", "conteudo": "x = 1", "final": True}],
                "_origem_geracao": "offline",
            }

        monkeypatch.setattr(calculo_service, "gerar_desafio_exatas", gerar_fake)
        jornada = rpg.criar_jornada_inicial("Matematica", "Masmorra do 3o EM")
        jornada = rpg.registrar_escolha_jornada(
            jornada,
            {
                "rota": "Ponte das Engrenagens",
                "recurso": "Chave mecanica",
                "foco_aprendizado": "planejamento e logica",
                "impacto_destino": "Estrategia",
            },
            1,
        )
        usados = []
        desafios = []

        for _ in range(6):
            desafio = rpg.gerar_desafio_academico(
                {"materia": "Matematica", "serie": "3o Ano EM", "nivel": "Medio"},
                "Ponte das Engrenagens",
                "A cena",
                usados,
                jornada,
                {"rota": "Ponte das Engrenagens"},
            )
            desafios.append(desafio)
            usados.append(desafio["tema_usado"])

        temas = {desafio["tema_usado"] for desafio in desafios}
        assert len(temas) > 1
        assert any(not desafio.get("passos_resolucao") and not desafio.get("formula") for desafio in desafios)
        assert any(desafio.get("passos_resolucao") and desafio.get("formula") for desafio in desafios)
        assert any("bhaskara" not in tema.lower() and "2o grau" not in tema.lower() for tema in temas)

    def test_desafio_teorico_exatas_do_rpg_tenta_ia_antes_do_offline(self, monkeypatch):
        rpg = self._importar()
        chamadas = []

        def ia_fake(materia, serie, nivel, tema):
            chamadas.append((materia, serie, nivel, tema))
            return {
                "enigma": "Painel vivo",
                "pergunta": "Qual conceito explica uma PG?",
                "opcoes": ["Razao multiplicativa.", "Soma aleatoria.", "Massa molar.", "Fonte historica."],
                "correta": 0,
                "explicacao": [{"tipo": "texto", "conteudo": "PG usa razao multiplicativa."}],
                "_origem_geracao": "ia",
            }

        monkeypatch.setattr(rpg, "invocar_enigma", ia_fake)
        monkeypatch.setattr(rpg, "obter_ultimo_erro_ia", lambda: "")
        jornada = rpg.criar_jornada_inicial("Matematica", "Masmorra do 3o EM")

        desafio = rpg.gerar_desafio_academico(
            {"materia": "Matematica", "serie": "3o Ano EM", "nivel": "Medio"},
            "Ponte das Engrenagens",
            "A cena",
            [],
            jornada,
            {"rota": "Ponte das Engrenagens"},
        )

        assert chamadas
        assert desafio["_origem_geracao"] == "ia"
        assert desafio["pergunta"] == "Qual conceito explica uma PG?"
        assert desafio["formula"] == ""
        assert desafio["passos_resolucao"] == []

    def test_desafio_teorico_exatas_do_rpg_cai_no_offline_se_ia_falhar(self, monkeypatch):
        rpg = self._importar()

        monkeypatch.setattr(
            rpg,
            "invocar_enigma",
            lambda *args, **kwargs: {
                "pergunta": "Questao offline rejeitada",
                "opcoes": ["A", "B", "C", "D"],
                "correta": 0,
                "_origem_geracao": "offline",
            },
        )
        monkeypatch.setattr(rpg, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
        jornada = rpg.criar_jornada_inicial("Matematica", "Masmorra do 3o EM")

        desafio = rpg.gerar_desafio_academico(
            {"materia": "Matematica", "serie": "3o Ano EM", "nivel": "Medio"},
            "Ponte das Engrenagens",
            "A cena",
            [],
            jornada,
            {"rota": "Ponte das Engrenagens"},
        )

        assert desafio["_origem_geracao"] == "offline"
        assert desafio["pergunta"] != "Questao offline rejeitada"
        assert desafio["aviso_ia"]

    @pytest.mark.parametrize("materia,serie", [("Fisica", "2o Ano EM"), ("Quimica", "3o Ano EM")])
    def test_desafio_exatas_rpg_tambem_mistura_teoria_e_calculo(self, materia, serie, monkeypatch):
        rpg = self._importar()
        from services import calculo_service

        def gerar_fake(materia_arg, tema, ano_escolar, nivel):
            return {
                "enigma": f"Porta numerica de {tema}",
                "pergunta": f"Calcule algo sobre {tema}.",
                "opcoes": ["1 unidade", "2 unidades", "3 unidades", "4 unidades"],
                "correta": 0,
                "formula": "x = 1",
                "subformulas": [],
                "legenda_variaveis": "x: valor.",
                "passos_resolucao": [{"titulo": "Resultado Final", "conteudo": "x = 1", "final": True}],
                "_origem_geracao": "offline",
            }

        monkeypatch.setattr(calculo_service, "gerar_desafio_exatas", gerar_fake)
        jornada = rpg.criar_jornada_inicial(materia, f"Masmorra de {materia}")
        jornada = rpg.registrar_escolha_jornada(
            jornada,
            {
                "rota": "Forja das Evidencias",
                "recurso": "Martelo de prova",
                "foco_aprendizado": "validacao de conclusoes",
                "impacto_destino": "Coragem",
            },
            1,
        )
        usados = []
        desafios = []

        for _ in range(4):
            desafio = rpg.gerar_desafio_academico(
                {"materia": materia, "serie": serie, "nivel": "Medio"},
                "Forja das Evidencias",
                "A cena",
                usados,
                jornada,
                {"rota": "Forja das Evidencias"},
            )
            desafios.append(desafio)
            usados.append(desafio["tema_usado"])

        assert len({desafio["tema_usado"] for desafio in desafios}) > 1
        assert any(not desafio.get("passos_resolucao") and not desafio.get("formula") for desafio in desafios)
        assert any(desafio.get("passos_resolucao") and desafio.get("formula") for desafio in desafios)

    def test_desafio_rpg_humanas_nao_exibe_etapas_fake(self, monkeypatch):
        rpg = self._importar()

        monkeypatch.setattr(rpg, "obter_ultimo_erro_ia", lambda: "IA indisponivel")
        monkeypatch.setattr(
            rpg,
            "invocar_enigma",
            lambda *args, **kwargs: {
                "pergunta": "Qual leitura historica melhor explica a fonte?",
                "opcoes": ["Comparar fonte e contexto.", "Chutar.", "Ignorar a fonte.", "Trocar o tema."],
                "correta": 0,
                "explicacao": [
                    {"tipo": "texto", "conteudo": "Historia exige contexto e evidencias."},
                    {"tipo": "resultado", "conteudo": "A resposta correta compara fonte e contexto."},
                ],
                "_origem_geracao": "offline",
            },
        )

        desafio = rpg.gerar_desafio_academico(
            {"materia": "Historia", "serie": "1o Ano EM", "nivel": "Medio"},
            "Arquivo das Runas",
            "A cena",
            [],
            None,
            None,
        )

        assert desafio["passos_resolucao"] == []
        assert "históricos" in " ".join(bloco["conteudo"] for bloco in desafio["explicacao"])

    def _continuar_aventura_com_memoria(self, rpg):
        jornada = rpg.criar_jornada_inicial()
        ultima = {
            "texto": "Investigar os simbolos antigos gravados nas paredes.",
            "rota": "Galeria dos Ecos",
            "recurso": "Mapa parcial da masmorra",
            "foco_aprendizado": "interpretacao de pistas",
            "impacto_destino": "Conhecimento",
        }
        jornada = rpg.registrar_escolha_jornada(jornada, ultima, 1)
        historico = [{"rota": "Galeria dos Ecos", "status": "Sucesso", "acao": ultima["texto"]}]

        cena = rpg.continuar_aventura(
            {"materia": "Quimica", "titulo": "Torre dos Elementos"},
            historico,
            ultima["texto"],
            "acertou",
            {"sucesso": True},
            jornada,
            ultima,
        )
        return cena
