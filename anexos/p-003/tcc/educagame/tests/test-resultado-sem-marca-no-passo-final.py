"""A captura 08c do TG, do jeito que a IA a devolve, e a mesma tela sem a marca final.

A 08c de 10/09/2026 mostrava "Acertou" com a resposta errada:

    2º Passo         v = 0 + 3 · 6 = 18
    3º Passo         v = 18 m/s
    Resultado Final  15 m/s          e 15 m/s marcado como certo

Por que nenhuma regra recusou, na versão de então (29c90b9):

  * `resultado-exatas-conflitante` só compara o bloco "resultado" da
    explicação com o passo final -- os dois diziam 15;
  * `alternativa-correta-diverge-do-resultado-final` compara a alternativa
    marcada com esse mesmo resultado -- 15 com 15;
  * `resultado-aritmetico-invalido` confere cada conta por dentro, e
    "0 + 3 · 6 = 18" está certa;
  * `passo-final-diverge-do-calculo-anterior`, a única que olha a conta, só
    comparava o final com o passo IMEDIATAMENTE anterior, e o 3º passo não é
    conta. Corrigido em 8347fc3 (test_passo_final_atras_de_repeticao.py).

Faltava uma forma da MESMA tela: a IA sem `"final": true` no último passo. A
tela não olha a marca -- laboratorio.html escreve o título, e o aluno lê
"Resultado Final" do mesmo jeito --, mas a regra só achava o passo final pela
marca, e sem ela não rodava. Nos dados reais a marca falta de verdade: 1 das
6 questões inteiras do Render e 1 das 29 resoluções de logs_pedagogicos.

Medido antes e depois (17/09/2026), com e sem a marca em todos os passos:
nenhum veredito mudou nas 50.900 questões offline, nas 29 resoluções reais,
nas 6 do Render nem nas 16 recusas reconstruídas. Nas 19 da IA vistas em
16/09, sem a marca, mudou só o MOTIVO de duas questões erradas (os passos dão
32 e 480, marcadas 24 e 600), que já eram recusadas pela legenda.
"""
from __future__ import annotations

import copy

import pytest

import services.calculo_service as calc
import services.ia.enigma as enigma
from services.ia.validacao import (
    _indice_do_passo_final,
    _passo_final_diverge_do_calculo_anterior,
    validar_questao_gerada,
)

BARRA = chr(92)


def questao_da_08c(resultado: str = "15 m/s", marcada: int = 2, marca_final: bool = True) -> dict:
    """A questão da captura, inteira, no formato que o prompt pede à IA."""
    final = {"titulo": "Resultado Final", "conteudo": resultado, "final": True}
    if not marca_final:
        del final["final"]
    return {
        "enigma": "Forças silenciosas disputam o destino do problema em movimento uniformemente variado.",
        "pergunta": (
            "Um carro parte do repouso com aceleração constante de 3 m/s². "
            "Após 6 segundos, qual a velocidade final atingida?"
        ),
        "opcoes": ["18 m/s", "10 m/s", "15 m/s", "12 m/s"],
        "correta": marcada,
        "formula": f"v = v_0 + a {BARRA}cdot t",
        "subformulas": [],
        "legenda_variaveis": (
            "v = velocidade final (m/s), v_0 = velocidade inicial (m/s), "
            "a = aceleração (m/s²), t = tempo (s)"
        ),
        "explicacao": [
            {"tipo": "bold", "conteudo": "Velocidade final no MUV"},
            {"tipo": "texto", "conteudo": "Substitua os valores na equação horária da velocidade."},
            {"tipo": "resultado", "conteudo": resultado},
        ],
        "passos_resolucao": [
            {"titulo": "1º Passo", "conteudo": "v_0 = 0, a = 3, t = 6", "final": False},
            {"titulo": "2º Passo", "conteudo": f"v = 0 + 3 {BARRA}cdot 6 = 18", "final": False},
            {"titulo": "3º Passo", "conteudo": "v = 18 m/s", "final": False},
            final,
        ],
    }


def questao_certa(marca_final: bool = True) -> dict:
    return questao_da_08c("18 m/s", marcada=0, marca_final=marca_final)


# ====================== PELOS CAMINHOS QUE CHAMAM A VALIDAÇÃO ======================


class IAFalsa:
    def __init__(self, resposta: dict):
        self.resposta = resposta

    def __call__(self, system_prompt, user_prompt, **kwargs):
        return copy.deepcopy(self.resposta)


def invocar_laboratorio(monkeypatch, resposta: dict) -> dict:
    monkeypatch.setattr(enigma, "gerar_json_ia", IAFalsa(resposta))
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: "huggingface")
    return enigma.invocar_enigma_laboratorio(
        materia="Fisica", ano_escolar="1º EM", nivel="Médio", tema="movimento uniformemente variado"
    )


@pytest.mark.parametrize("marca_final", [True, False], ids=["com-marca", "sem-marca"])
def test_a_08c_nao_chega_ao_aluno(monkeypatch, capsys, marca_final):
    """invocar_enigma_laboratorio devolve {} -- o calculo_service tenta outro
    provedor ou cai no banco -- e o log diz por quê."""
    questao = invocar_laboratorio(monkeypatch, questao_da_08c(marca_final=marca_final))

    assert questao == {}
    assert "rejeitado no laboratorio: passo-final-diverge-do-calculo-anterior" in capsys.readouterr().out


@pytest.mark.parametrize("marca_final", [True, False], ids=["com-marca", "sem-marca"])
def test_a_mesma_questao_certa_chega(monkeypatch, marca_final):
    questao = invocar_laboratorio(monkeypatch, questao_certa(marca_final))

    assert questao["_origem_geracao"] == "ia"
    assert questao["opcoes"][questao["correta"]] == "18 m/s"


@pytest.mark.parametrize("marca_final", [True, False], ids=["com-marca", "sem-marca"])
def test_a_checagem_extra_do_calculo_service_tambem_recusa(marca_final):
    assert calc._desafio_parece_calculo_laboratorio(questao_da_08c(marca_final=marca_final), "Fisica") is False
    assert calc._desafio_parece_calculo_laboratorio(questao_certa(marca_final), "Fisica") is True


@pytest.mark.parametrize("contexto", ["oraculo", "laboratorio"])
@pytest.mark.parametrize("marca_final", [True, False], ids=["com-marca", "sem-marca"])
def test_o_motivo_e_o_do_passo_final(contexto, marca_final):
    _, aceita, motivo = validar_questao_gerada(questao_da_08c(marca_final=marca_final), "Fisica", contexto)

    assert not aceita
    assert motivo == "passo-final-diverge-do-calculo-anterior"


# ====================== QUAL PASSO É O FINAL ======================


def passo(titulo: str, conteudo: str = "x = 1", **extra) -> dict:
    return {"titulo": titulo, "conteudo": conteudo, **extra}


@pytest.mark.parametrize(
    "passos, esperado, rotulo",
    [
        ([passo("1º Passo"), passo("Resultado Final", final=True)], 1, "a marca manda"),
        ([passo("1º Passo", final=True), passo("Resultado Final")], 0, "a marca manda mesmo fora do fim"),
        ([passo("Resultado", final=True), passo("Resultado Final", final=True)], 1, "duas marcas: a última"),
        ([passo("1º Passo"), passo("Resultado Final")], 1, "sem marca: o título da tela"),
        ([passo("1º Passo"), passo("Resultado")], 1, "só 'Resultado'"),
        ([passo("1º Passo"), passo("Resposta final")], 1, "'Resposta final'"),
        ([passo("1º Passo"), passo("RESULTADO FINAL", final=False)], 1, "maiúsculas e final=False"),
        ([passo("1º Passo"), passo("3º Passo")], None, "sem marca e sem título de resultado"),
        ([passo("Resultado Final"), passo("2º Passo")], None, "o título não está no último passo"),
        ([passo("1º Passo"), passo("Resultados parciais")], None, "'Resultados' não é o resultado"),
        ([passo("1º Passo"), {"conteudo": "x = 1"}], None, "sem título"),
        ([], None, "sem passos"),
    ],
)
def test_o_passo_final(passos, esperado, rotulo):
    assert _indice_do_passo_final(passos) == esperado, rotulo


def sem_marca(*conteudos: str, titulo_final: str = "Resultado Final") -> dict:
    lista = [{"titulo": f"{i + 1}º Passo", "conteudo": c} for i, c in enumerate(conteudos)]
    lista[-1]["titulo"] = titulo_final
    return {"passos_resolucao": lista}


@pytest.mark.parametrize(
    "conteudos, rotulo",
    [
        (("v = 0 + 3 * 6 = 18", "15 m/s"), "final logo depois da conta"),
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s", "15 m/s"), "final atrás da repetição"),
        (("d = 12 * 5", "d = 50"), "conta sem '='"),
    ],
)
def test_sem_marca_o_final_errado_e_pego(conteudos, rotulo):
    assert _passo_final_diverge_do_calculo_anterior(sem_marca(*conteudos)), rotulo


@pytest.mark.parametrize(
    "dados, rotulo",
    [
        (sem_marca("v = 0 + 3 * 6 = 18", "18 m/s"), "final certo"),
        (sem_marca("v = 0 + 3 * 6 = 18", "v = 18 m/s", "18 m/s"), "final certo atrás da repetição"),
        (sem_marca("v = 0 + 3 * 6 = 18", "15 m/s", titulo_final="3º Passo"), "último passo sem título de resultado"),
        (sem_marca("15 m/s"), "resultado sem conta antes"),
    ],
)
def test_sem_marca_na_duvida_nao_recusa(dados, rotulo):
    """Sem a marca e sem o título, não dá para saber que o último passo é a
    resposta: a regra continua sem rodar, como antes."""
    assert not _passo_final_diverge_do_calculo_anterior(dados), rotulo


# ====================== OS BANCOS SEM A MARCA ======================


def _questoes_com_passos():
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    for materia in em.MATERIAS:
        yield from em.listar_questoes_em(materia)
    for materia in ef.MATERIAS:
        yield from ef.listar_questoes_ef(materia)
    for materia in rp.MATERIAS:
        yield from rp.listar_questoes_rpg(materia)
    for materia in lab.MATERIAS_LAB_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EM")
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EF")


def test_tirar_a_marca_nao_muda_a_regra_nas_questoes_do_banco():
    """Os bancos marcam sempre o passo "Resultado Final". Sem a marca, a regra
    tem de chegar ao mesmo passo -- e ao mesmo veredito, que é aceitar."""
    comparadas = 0
    for questao in _questoes_com_passos():
        passos = questao.get("passos_resolucao") or []
        if not any(isinstance(p, dict) and p.get("final") for p in passos):
            continue
        despida = copy.deepcopy(questao)
        for p in despida["passos_resolucao"]:
            if isinstance(p, dict):
                p.pop("final", None)
        comparadas += 1
        assert not _passo_final_diverge_do_calculo_anterior(questao), questao
        assert not _passo_final_diverge_do_calculo_anterior(despida), despida

    assert comparadas > 1000
