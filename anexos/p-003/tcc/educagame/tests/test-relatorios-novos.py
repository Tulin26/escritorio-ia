from services.relatorios import gerar_pdf_boss_rush, gerar_pdf_escape_room, gerar_pdf_guildas, gerar_pdf_rpg
from services.relatorios.commons import preparar_texto_pdf


def _assert_pdf(bytes_pdf: bytes):
    assert isinstance(bytes_pdf, bytes)
    assert bytes_pdf.startswith(b"%PDF")
    assert len(bytes_pdf) > 1000


def test_gerar_pdf_boss_rush():
    pdf = gerar_pdf_boss_rush(
        nome_aluno="Lucas",
        dados_escola={"nome": "Escola Teste"},
        historico=[
            {
                "boss": "Boss 1 - Linguagens",
                "area_label": "Linguagens",
                "pergunta": "Pergunta exemplo?",
                "resposta_aluno": "A",
                "correta": "B",
                "acertou": False,
                "tempo": 12.5,
                "explicacao": [{"tipo": "texto", "conteudo": "Explicacao curta."}],
            }
        ],
    )

    _assert_pdf(pdf)


def test_gerar_pdf_guildas():
    pdf = gerar_pdf_guildas(
        "Escola Teste",
        [
            {
                "guilda": "1 Ano EM - Manha",
                "alunos": 10,
                "participantes_semana": 8,
                "questoes_semana": 20,
                "acertos_semana": 15,
                "erros_semana": 5,
                "pontos_semana": 185,
                "taxa_acerto": 75,
            },
            {
                "guilda": "2 Ano EM - Manha",
                "alunos": 9,
                "participantes_semana": 7,
                "questoes_semana": 18,
                "acertos_semana": 11,
                "erros_semana": 7,
                "pontos_semana": 138,
                "taxa_acerto": 61,
            },
        ],
    )

    _assert_pdf(pdf)


def test_gerar_pdf_escape_room():
    pdf = gerar_pdf_escape_room(
        nome_aluno="Lucas",
        dados_escola={"nome": "Escola Teste"},
        historico=[
            {
                "sala": 1,
                "materia": "Matematica",
                "tema": "Frações",
                "pergunta": "Pergunta exemplo?",
                "resposta_aluno": "A",
                "resposta_correta": "A",
                "acertou": True,
                "tempo": 9.5,
                "explicacao": [{"tipo": "texto", "conteudo": "Explicacao curta."}],
            }
        ],
    )

    _assert_pdf(pdf)


def test_texto_pdf_formata_notacao_matematica_em_todos_relatorios():
    texto = preparar_texto_pdf(r"Use v = 20 m/s^2, x_1 e \Delta = b^2 - 4ac")

    assert "m/s^2" not in texto
    assert "x_1" not in texto
    assert "b^2" not in texto
    assert "m/s²" in texto
    assert "x₁" in texto
    assert "b²" in texto


def test_gerar_pdf_rpg_com_equacao_quadratica():
    pdf = gerar_pdf_rpg(
        nome_aluno="Lucas",
        titulo_aventura="Aventura Matematica",
        historico_desafios=[
            {
                "fase": 2,
                "pergunta": "Quais sao as raizes de x^2 - 5x + 6 = 0?",
                "resposta_aluno": "x' = 2 e x'' = 3",
                "resposta_correta": "x' = 2 e x'' = 3",
                "acertou": True,
                "explicacao": [{"tipo": "texto", "conteudo": "A equacao x^2 - 5x + 6 tem raizes 2 e 3."}],
            }
        ],
        dados_escola={"nome": "Escola Teste"},
        hp_final=100,
        xp_final=50,
    )

    _assert_pdf(pdf)
