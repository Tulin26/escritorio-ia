from __future__ import annotations

import re
import os
import time

from core.answer_equivalence import tem_opcoes_equivalentes
from core.config import eh_ensino_medio, normalizar_materia
from core.text_cleanup import chave_busca as _normalizar_busca
from core.runtime_context import get_runtime
from services import historico_perguntas
from services.ia.normalizacao import normalizar_payload_questao
from services.ia.questoes import embaralhar_opcoes_questao

runtime = get_runtime()


def _orcamento_ia_laboratorio_segundos() -> float:
    valor = os.getenv("LAB_IA_BUDGET_SECONDS")
    if valor is not None:
        try:
            return max(6.0, min(float(valor), 26.0))
        except (TypeError, ValueError):
            pass
    try:
        return max(6.0, min(float(runtime.secrets.get("LAB_IA_BUDGET_SECONDS", 22.0)), 26.0))
    except Exception:
        return 22.0

_TEMAS_LAB_SUPORTADOS = {
    "Matematica": {
        "EF": ["porcentagem e desconto", "áreas de figuras planas", "geometria plana"],
        "EM": [
            "equações do 2o grau e fórmula de Bhaskara",
            "progressão aritmética (PA)",
            "trigonometria",
            "geometria plana",
            "porcentagem",
        ],
    },
    "Fisica": {
        "EF": ["velocidade e movimento", "forças e atrito", "energia e suas formas", "eletricidade básica"],
        "EM": [
            "cinemática: MRU e MRUV",
            "leis de Newton",
            "trabalho, energia e potência",
            "circuitos elétricos",
            "lei de Ohm",
        ],
    },
    "Quimica": {
        "EF": ["soluções", "ácidos e bases", "mol e massa molar", "termoquímica"],
        "EM": ["soluções", "estequiometria", "mol e massa molar", "reações ácido-base e pH", "termoquímica"],
    },
}


def _etapa_laboratorio(ano_escolar: str) -> str:
    return "EM" if eh_ensino_medio(ano_escolar) else "EF"


def _tema_padrao_laboratorio(materia: str, ano_escolar: str) -> str:
    materia_norm = normalizar_materia(materia or "Matematica")
    etapa = _etapa_laboratorio(ano_escolar)
    temas = _TEMAS_LAB_SUPORTADOS.get(materia_norm, {}).get(etapa, [])
    if not temas:
        return "conteudo geral"

    # O indice fica em memoria de processo para alternar questoes repetidas.
    # sem reiniciar sempre pelo primeiro tema.
    chave_ss = f"lab_ciclo_{materia_norm}_{etapa}"
    idx = int(runtime.session_state.get(chave_ss, 0) or 0)
    tema = temas[idx % len(temas)]
    runtime.session_state[chave_ss] = (idx + 1) % len(temas)
    return tema


def _get_historico(chave: tuple) -> list[str]:
    # Guardado FORA do cookie desde 13/09/2026: ver services/historico_perguntas.py.
    return historico_perguntas.ler(f"calc_hist_{'__'.join(str(c) for c in chave)}")


def _set_historico(chave: tuple, historico: list[str]) -> None:
    historico_perguntas.gravar(f"calc_hist_{'__'.join(str(c) for c in chave)}", historico)


def _extrair_numeros(texto: str) -> list[str]:
    return re.findall(r"-?\d+(?:[.,]\d+)?", str(texto or ""))


def _texto_tem_raiz_complexa(texto: str) -> bool:
    texto_norm = str(texto or "").lower()
    return bool(
        re.search(r"(?:\\sqrt|sqrt|√)\s*\{\s*-", texto_norm)
        or re.search(r"(?:\\sqrt|sqrt|√)\s*\(\s*-", texto_norm)
        or re.search(r"\b[+-]?\s*i\s*(?:\\sqrt|sqrt|√|\d)", texto_norm)
        or "complex" in texto_norm
    )


def _texto_desafio(dados: dict) -> str:
    return " ".join(
        [
            str(dados.get("tema_usado", "") or ""),
            str(dados.get("enigma", "") or ""),
            str(dados.get("pergunta", "") or ""),
            str(dados.get("formula", "") or ""),
            " ".join(str(item or "") for item in dados.get("subformulas", []) or []),
            " ".join(str(item or "") for item in dados.get("opcoes", []) or []),
            " ".join(
                str((item or {}).get("conteudo", "") if isinstance(item, dict) else item)
                for item in dados.get("passos_resolucao", []) or []
            ),
        ]
    )


def _desafio_inadequado_ef(dados: dict) -> bool:
    texto = _normalizar_busca(_texto_desafio(dados))
    proibidos = (
        "progressao aritmetica",
        "progressao geometrica",
        " pg ",
        "bhaskara",
        "2o grau",
        "2 grau",
        "segundo grau",
        "trigonometr",
        "logarit",
        "matriz",
        "matrizes",
        "determinante",
    )
    if any(token in texto for token in proibidos):
        return True
    return bool(re.search(r"\bpa\b", texto))


def _bhaskara_inadequada_laboratorio(dados: dict) -> bool:
    texto = " ".join(
        [
            str(dados.get("pergunta", "") or ""),
            str(dados.get("formula", "") or ""),
            " ".join(str(item or "") for item in dados.get("subformulas", []) or []),
            " ".join(
                str((item or {}).get("conteudo", "") if isinstance(item, dict) else item)
                for item in dados.get("passos_resolucao", []) or []
            ),
            " ".join(str(item or "") for item in dados.get("opcoes", []) or []),
        ]
    )
    texto_norm = texto.lower()
    assunto_bhaskara = any(token in texto_norm for token in ("bhaskara", "2o grau", "2º grau", "quadratic"))
    if not assunto_bhaskara:
        return False
    if _texto_tem_raiz_complexa(texto):
        return True

    formula = str(dados.get("formula", "") or "").replace(" ", "").lower()
    # MELHORIA: o b^2 era procurado so na formula principal. O proprio prompt do
    # Laboratorio pede "x = (-b +- raiz de Delta)/2a" na formula e "Delta = b^2 -
    # 4ac" em subformulas -- e essa Bhaskara, certa, era recusada aqui (Render,
    # 08/09/2026: "2x^2 + 5x - 3 = 0", "nao-parece-calculo").
    # A subformula so conta quando a formula tira a raiz DE Delta: uma raiz
    # escrita por extenso sem o quadrado ("\sqrt{b - 4ac}") continua errada.
    auxiliares = " ".join(str(item or "") for item in dados.get("subformulas", []) or []).replace(" ", "").lower()
    if ("sqrt" in formula or "\\sqrt" in formula) and not any(token in formula for token in ("b^2", "b²")):
        raiz_de_delta = any(token in formula for token in ("\\delta", "δ"))
        delta_com_b2 = any(token in auxiliares for token in ("b^2", "b²"))
        if not (raiz_de_delta and delta_com_b2):
            return True
    return False


def _desafio_parece_calculo_laboratorio(desafio: dict, materia: str) -> bool:
    from services.ia.validacao import validar_questao_gerada

    materia_norm = normalizar_materia(materia or "Matematica")
    pergunta = str(desafio.get("pergunta", "") or "")
    formula = str(desafio.get("formula", "") or "").strip()
    subformulas = desafio.get("subformulas", []) or []
    passos = desafio.get("passos_resolucao", []) or []
    opcoes = desafio.get("opcoes", []) or []

    if not isinstance(opcoes, list) or len(opcoes) < 2:
        return False

    _, questao_valida, _motivo_validacao = validar_questao_gerada(desafio, materia_norm, contexto="laboratorio")
    if not questao_valida:
        return False

    if not formula or "=" not in formula:
        return False

    subformulas_validas = [str(item).strip() for item in subformulas if str(item).strip()]
    passos_texto = [
        str((item or {}).get("conteudo", "")).strip() if isinstance(item, dict) else str(item).strip()
        for item in passos
    ]
    passos_texto = [texto for texto in passos_texto if texto]

    if not subformulas_validas and not passos_texto:
        return False

    numeros_pergunta = _extrair_numeros(pergunta)
    numeros_opcoes = sum(len(_extrair_numeros(str(opcao))) for opcao in opcoes)
    numeros_substituicao = sum(len(_extrair_numeros(texto)) for texto in (subformulas_validas + passos_texto))
    total_numeros = len(numeros_pergunta) + numeros_opcoes + numeros_substituicao

    if len(numeros_pergunta) < 2 or numeros_substituicao < 2:
        return False

    if materia_norm == "Matematica" and _bhaskara_inadequada_laboratorio(desafio):
        return False
    if materia_norm == "Matematica" and tem_opcoes_equivalentes([str(opcao) for opcao in opcoes], pergunta):
        return False

    if materia_norm in {"Fisica", "Quimica"}:
        # MELHORIA: aqui ficou a lista ANTIGA de unidades procuradas como pedaco
        # de texto, a que services/ia/validacao.py ja trocou por token conferido
        # contra core/unidades.py. Sem " w" e sem pH, ela barrava questao certa
        # que a validacao tinha acabado de aceitar: "Qual e a potencia
        # dissipada?" com "72 W" (Render, 11/09/2026), e um pH respondido por
        # aluno, com alternativas "10" e "11". Agora e a mesma checagem.
        from core.unidades import UNIDADES_FISICA, UNIDADES_QUIMICA
        from services.ia.validacao import _alternativas_carregam_unidade

        unidades = UNIDADES_FISICA if materia_norm == "Fisica" else UNIDADES_QUIMICA
        tem_unidade = _alternativas_carregam_unidade([str(opcao) for opcao in opcoes], pergunta, unidades)
        return len(numeros_pergunta) >= 2 and total_numeros >= 4 and tem_unidade

    return total_numeros >= 4


def gerar_desafio_exatas(materia: str, tema: str, ano_escolar: str, nivel: str):
    from services.exatas_bank import gerar_desafio_exatas as gerar_desafio_exatas_base
    from services.ia_service import invocar_enigma_laboratorio, obter_ultimo_erro_ia, obter_ultimo_provedor_ia
    from services.banks.laboratorio import gerar_desafio_laboratorio_offline

    etapa = _etapa_laboratorio(ano_escolar)
    tema_resolvido = str(tema or "").strip() or _tema_padrao_laboratorio(materia, ano_escolar)
    chave = (str(materia or ""), tema_resolvido, str(nivel or ""))
    historico = _get_historico(chave)
    desafio = None
    provedores_rejeitados: set[str] = set()
    inicio_ia = time.monotonic()
    orcamento_ia = _orcamento_ia_laboratorio_segundos()

    for _ in range(5):
        restante_ia = orcamento_ia - (time.monotonic() - inicio_ia)
        if restante_ia < 4.0:
            print("[IA] Laboratorio atingiu limite de tempo. usando offline...")
            break
        try:
            candidato = invocar_enigma_laboratorio(
                materia,
                ano_escolar,
                nivel,
                tema_resolvido,
                pular_provedores=provedores_rejeitados,
                deadline_seconds=restante_ia,
            ) or {}
        except TypeError:
            candidato = invocar_enigma_laboratorio(materia, ano_escolar, nivel, tema_resolvido) or {}
        aviso_ia = obter_ultimo_erro_ia()
        provedor = str(candidato.get("_provedor_ia") or obter_ultimo_provedor_ia() or "").strip().lower()
        if not candidato.get("_origem_geracao"):
            candidato["_origem_geracao"] = "offline" if aviso_ia else "ia"
        assinatura = str(candidato.get("pergunta", "")).strip()
        desafio = candidato
        if etapa == "EF" and _desafio_inadequado_ef(candidato):
            if provedor:
                provedores_rejeitados.add(provedor)
                print(f"[IA] {provedor} rejeitado no laboratorio: conteudo-inadequado-ef")
            continue
        if assinatura and assinatura not in historico and _desafio_parece_calculo_laboratorio(candidato, materia):
            _set_historico(chave, (historico + [assinatura])[-12:])
            if etapa == "EF":
                candidato["serie_tipo"] = "EF"
            return embaralhar_opcoes_questao(normalizar_payload_questao(candidato))
        if provedor and assinatura:
            # MELHORIA: quando "assinatura" esta vazia, o candidato ja veio
            # rejeitado por invocar_enigma_laboratorio (que ja logou o motivo
            # especifico e o trecho da pergunta). So logamos aqui de novo
            # quando ha conteudo real que passou na validacao interna mas
            # falhou nos checks extras deste laboratorio (formula ausente etc.),
            # evitando duplicar a mesma rejeicao duas vezes no log.
            provedores_rejeitados.add(provedor)
            motivo = "repetido" if assinatura in historico else "nao-parece-calculo"
            from services.ia.enigma import questao_para_log

            print(
                f"[IA] {provedor} rejeitado no laboratorio (checagem extra): {motivo} "
                f"| pergunta='{assinatura[:120]}' | questao={questao_para_log(candidato)}"
            )
        elif provedor:
            provedores_rejeitados.add(provedor)
        if aviso_ia and not assinatura:
            break

    if etapa == "EF":
        fallback = gerar_desafio_laboratorio_offline(
            materia,
            tema_resolvido,
            nivel,
            evitar_ids=historico,
            serie_tipo="EF",
        )
    else:
        try:
            fallback = gerar_desafio_exatas_base(
                materia,
                tema_resolvido,
                nivel,
                contexto="lab",
                evitar_ids=historico,
            )
        except TypeError:
            fallback = gerar_desafio_exatas_base(materia, tema_resolvido, nivel, contexto="lab")
    fallback["_origem_geracao"] = "offline"
    assinatura_final = str(fallback.get("id_offline") or fallback.get("pergunta", "")).strip()
    if assinatura_final:
        _set_historico(chave, (historico + [assinatura_final])[-12:])
    return embaralhar_opcoes_questao(normalizar_payload_questao(fallback))


def __getattr__(name: str):
    raise AttributeError(name)
