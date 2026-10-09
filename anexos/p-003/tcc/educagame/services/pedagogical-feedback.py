from __future__ import annotations

import re
import unicodedata
from typing import Any

from core.config import exibir_materia, materia_base as _materia_base


def _normalizar(texto: Any) -> str:
    bruto = str(texto or "").lower()
    sem_acentos = unicodedata.normalize("NFKD", bruto)
    return "".join(ch for ch in sem_acentos if not unicodedata.combining(ch))


def _numeros(texto: Any) -> list[str]:
    return re.findall(r"-?\d+(?:[,.]\d+)?", str(texto or ""))


# MELHORIA: "dificuldade" estava na cadeia de fallback do tema, e dificuldade
# nao e tema. Quando a questao chegava sem tema_usado, o rodape do feedback
# saia "Treine mais uma questao sobre Medio" e "sobre Dificil" -- as duas
# vistas na tela. `objeto_conhecimento` entra no lugar (e o campo da BNCC que
# de fato nomeia o assunto), e a materia fecha a fila.
_CAMPOS_DE_TEMA = ("tema_usado", "tema", "assunto", "objeto_conhecimento")


def _tema_curto(dados: dict[str, Any]) -> str:
    for campo in _CAMPOS_DE_TEMA:
        valor = str(dados.get(campo, "") or "").strip()
        if valor:
            return valor
    materia = str(dados.get("materia", "") or "").strip()
    if materia:
        return exibir_materia(_materia_base(materia)) or materia
    return "o mesmo assunto"


def _numeros_float(texto: Any) -> list[float]:
    valores = []
    for bruto in _numeros(texto):
        try:
            valores.append(float(bruto.replace(",", ".")))
        except ValueError:
            continue
    return valores


def _diagnostico_numerico(nums_aluno: list[float], nums_certa: list[float]) -> tuple[str, str] | None:
    """
    MELHORIA: antes, qualquer resposta numerica errada em exatas recebia a
    mesma mensagem generica ("voce provavelmente errou alguma conta").
    Isso compara os proprios numeros da resposta do aluno com os da resposta
    certa pra apontar um tipo de erro especifico sempre que der pra inferir,
    em vez de um texto igual pra qualquer engano.
    """
    if not nums_aluno or not nums_certa:
        return None

    # Caso mais comum em exatas: duas raizes/valores (ex: Bhaskara).
    if len(nums_aluno) == 2 and len(nums_certa) == 2:
        soma_aluno, soma_certa = sum(nums_aluno), sum(nums_certa)
        prod_aluno = nums_aluno[0] * nums_aluno[1]
        prod_certa = nums_certa[0] * nums_certa[1]
        soma_bate = abs(soma_aluno - soma_certa) < 0.05
        prod_bate = abs(prod_aluno - prod_certa) < 0.05
        absolutos_batem = sorted(abs(v) for v in nums_aluno) == sorted(round(abs(v), 2) for v in nums_certa)

        if absolutos_batem and not (soma_bate and prod_bate):
            return (
                "Os valores que você encontrou têm o mesmo tamanho (módulo) dos corretos, mas o sinal de pelo menos um deles está trocado.",
                "Reveja o sinal na f\u00f3rmula (o \u00b1 antes da raiz gera um valor positivo e um negativo). Confira cada raiz separadamente antes de escolher a alternativa.",
            )
        if soma_bate and not prod_bate:
            return (
                "A soma dos seus dois valores bate com a soma dos valores corretos, mas o produto entre eles não bate. O erro provavelmente aconteceu ao calcular a raiz quadrada (o delta) ou ao dividir o resultado final.",
                "Recalcule o delta (b\u00b2 - 4ac) com cuidado antes de tirar a raiz, e s\u00f3 depois divida por 2a. Um erro nessa etapa muda os dois valores de forma diferente.",
            )
        if prod_bate and not soma_bate:
            return (
                "O produto dos seus dois valores bate com o produto dos valores corretos, mas a soma não bate. Isso costuma acontecer quando um dos coeficientes (a, b ou c) foi trocado ou copiado errado do enunciado.",
                "Volte ao enunciado e confirme os valores de a, b e c antes de substituir na fórmula. Um número trocado muda a soma das raízes sem necessariamente estragar o produto.",
            )

    # Um unico valor numerico de resposta.
    if len(nums_aluno) == 1 and len(nums_certa) == 1:
        valor_aluno, valor_certa = nums_aluno[0], nums_certa[0]
        diferenca = abs(valor_aluno - valor_certa)
        if valor_aluno == -valor_certa and valor_certa != 0:
            return (
                "Seu resultado tem o mesmo valor absoluto do correto, só que com o sinal trocado.",
                "Confira o sinal de cada termo antes de somar ou subtrair, e preste atenção ao sinal do resultado final.",
            )
        referencia = abs(valor_certa) if valor_certa != 0 else 1.0
        if diferenca / referencia < 0.15:
            # MELHORIA: "perto" virava sempre "arredondamento ou casa decimal".
            # Medido nos bancos em 13/09/2026: dos 2.744 pares errada x certa
            # que recebiam a frase, 1.969 so tinham INTEIROS -- "22 m/s" contra
            # "20 m/s" nao tem casa decimal para perder. Perto, com inteiros, o
            # caminho estava certo e escorregou uma conta ou um valor.
            if valor_aluno.is_integer() and valor_certa.is_integer():
                return (
                    "Seu resultado está perto do correto, então o caminho provavelmente estava certo: o erro deve estar numa conta intermediária ou num valor copiado do enunciado.",
                    "Refaça as contas intermediárias uma a uma e confira cada número com o enunciado antes de marcar a alternativa.",
                )
            return (
                "Seu resultado está próximo do correto, mas não exatamente igual — pode ter sido um arredondamento feito cedo demais ou uma casa decimal perdida no caminho.",
                "Faça os arredondamentos só no final da conta, nunca nos passos intermediários, e confira uma casa decimal a mais do que a alternativa pede.",
            )
        return (
            "Seu resultado está bem distante do correto, o que sugere um erro na fórmula usada ou na substituição dos valores do enunciado, não só um arredondamento.",
            "Reescreva a fórmula antes de substituir os números, confira cada valor contra o enunciado e refaça a conta passo a passo.",
        )

    return None


def _feedback_conceitual(
    pergunta_norm: str, resposta_aluno: Any, resposta_correta: Any
) -> tuple[str, str] | None:
    """
    MELHORIA: em exatas, resposta NUMERICA errada ja recebia diagnostico
    especifico (ver _diagnostico_numerico), mas toda questao CONCEITUAL caia
    na mesma frase -- "voce escolheu uma alternativa parecida, mas ligada a
    outro conceito". Ela nao diz o que o aluno marcou, nao diz qual era a
    certa e serve igual para qualquer pergunta. Aqui as duas alternativas
    sao citadas pelo nome e a dica sai do comando do enunciado.
    """
    aluno = " ".join(str(resposta_aluno or "").split())
    certa = " ".join(str(resposta_correta or "").split())
    if not aluno or not certa or aluno.lower() == certa.lower():
        return None
    # Alternativa que e so um rotulo ("A", "B") nao nomeia conceito nenhum:
    # citar "voce marcou C, a resposta e A" nao ensina nada.
    if len(aluno) <= 2 or len(certa) <= 2:
        return None

    # MELHORIA: relatorio de QA de 23/09/2026, item 5.4 -- "As duas
    # pertencem ao mesmo assunto..." saia mesmo quando o distrator marcado
    # nao tinha nenhuma relacao com a resposta certa ("Carnaval" numa
    # questao sobre peregrinacao; "se transformar em outro elemento" numa
    # de Quimica). A frase afirmava uma proximidade que nem sempre existe --
    # e medir proximidade de verdade e fragil (ex: "Paralelepipedo" e
    # "Cubo" sao conceitualmente vizinhos e nao compartilham nenhuma
    # palavra). Em vez de arriscar um classificador de semelhanca, a frase
    # deixou de afirmar que as duas sao parecidas: ela so pede pra comparar
    # as duas, o que vale tanto quando sao vizinhas quanto quando nao sao.
    confundiu = (
        f"Você marcou “{_citacao(aluno)}”, mas a resposta é “{_citacao(certa)}”{_fim_de_frase(certa)} "
        "Releia as duas com atenção: o que a resposta certa afirma, e a sua não, "
        "é exatamente o que o enunciado está cobrando."
    )

    if any(t in pergunta_norm for t in ("por que", "porque", "explique", "justifique")):
        evitar = (
            "Em pergunta de causa, teste cada alternativa como explicação: "
            "“isso sozinho produziria o efeito descrito?”. A alternativa que apenas "
            "descreve o fenômeno, sem explicá-lo, costuma ser a armadilha."
        )
    elif any(t in pergunta_norm for t in ("compare", "diferenca", "distingue", "diferencia")):
        evitar = (
            "Em pergunta de comparação, escreva lado a lado o que cada termo tem de "
            "próprio antes de olhar as alternativas. O erro quase sempre está num "
            "atributo que os dois compartilham."
        )
    else:
        evitar = (
            "O enunciado lista as exigências uma a uma. Anote cada exigência e risque "
            "a alternativa que falhar em qualquer uma delas — basta uma para eliminar."
        )
    return confundiu, evitar


def _citacao(alternativa: str) -> str:
    """A alternativa para ir entre aspas, sem o ponto final dela.

    MELHORIA: a frase fecha com ponto depois das aspas, e a alternativa que ja
    terminava em ponto saia “John said (that) he was tired.”. -- ate 195 pares
    nos bancos (13/09/2026). Interrogacao e exclamacao ficam: sao do que o aluno leu.
    """
    return str(alternativa or "").rstrip(" .")


def _fim_de_frase(alternativa: str) -> str:
    return "" if _citacao(alternativa).endswith(("?", "!")) else "."


def _quase_iguais(resposta_aluno: Any, resposta_correta: Any) -> bool:
    """Texto sem numero que muda num detalhe: "obedecer às" x "obedecer as".

    Com numero quem fala e o diagnostico numerico: "x = 3 e x = 5" x
    "x = 3 e x = -5" e sinal trocado, nao "quase igual".
    """
    import difflib

    a, b = _normalizar(resposta_aluno), _normalizar(resposta_correta)
    if len(a) <= 2 or len(b) <= 2 or re.search(r"\d", a + b):
        return False
    if " ".join(str(resposta_aluno).split()) == " ".join(str(resposta_correta).split()):
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.9


# Questao do ENEM gerada pela IA chega so com a AREA; as do banco ja trazem a
# materia (services/enem_service.py::_converter_questao_para_enem). A materia
# escolhida decide o diagnostico: numerico em Matematica; citacao das duas
# alternativas nas outras -- Natureza vai para Ciencias porque mistura Fisica
# com Biologia, e "46 cromossomos" x "23 cromossomos" nao e erro de formula.
_MATERIA_DA_AREA_ENEM = {
    "matematica e suas tecnologias": "Matematica",
    "ciencias da natureza e suas tecnologias": "Ciencias",
    "linguagens e suas tecnologias": "Portugues",
    "ciencias humanas e sociais aplicadas": "Historia",
}


def gerar_feedback_pedagogico(
    *,
    dados: dict[str, Any] | None,
    materia: str,
    resposta_aluno: Any,
    resposta_correta: Any,
) -> dict[str, str]:
    """Gera um feedback curto, orientado ao aprendizado, sem depender da IA."""
    dados = dados or {}
    materia = _MATERIA_DA_AREA_ENEM.get(_normalizar(_materia_base(materia)).strip(), materia)
    materia_norm = _normalizar(_materia_base(materia))
    pergunta_norm = _normalizar(dados.get("pergunta", ""))
    resp_aluno_norm = _normalizar(resposta_aluno)
    resp_certa_norm = _normalizar(resposta_correta)
    tema = _tema_curto(dados)

    if materia_norm in {"matematica", "fisica", "quimica"}:
        nums_aluno = _numeros(resposta_aluno)
        nums_certa = _numeros(resposta_correta)
        if nums_aluno and nums_certa and nums_aluno != nums_certa:
            diagnostico = _diagnostico_numerico(_numeros_float(resposta_aluno), _numeros_float(resposta_correta))
            if diagnostico:
                confundiu, evitar = diagnostico
            else:
                confundiu = "Você provavelmente errou alguma conta, substituição de valores ou unidade no caminho da resolução."
                evitar = "Antes de escolher a alternativa, reescreva os dados do enunciado, substitua na fórmula e confira se a unidade final faz sentido."
        else:
            conceitual = _feedback_conceitual(pergunta_norm, resposta_aluno, resposta_correta)
            if conceitual:
                confundiu, evitar = conceitual
            else:
                confundiu = "Você parece ter escolhido uma alternativa parecida, mas ligada a outro conceito ou outra etapa da resolução."
                evitar = "Identifique primeiro o que a pergunta pede, depois escolha a fórmula ou regra. Evite comparar alternativas antes de montar o raciocínio."
    elif materia_norm in {"portugues", "lingua portuguesa", "historia", "geografia", "filosofia", "sociologia", "ensino religioso"}:
        if any(palavra in pergunta_norm for palavra in ("texto", "interpret", "opinia", "infer")):
            confundiu = "Você confundiu uma informação comprovada pelo enunciado com uma interpretação pessoal ou uma alternativa apenas parecida."
            evitar = "Volte ao texto e procure a frase que comprova a resposta. Se não houver evidência no enunciado, desconfie da alternativa."
        else:
            confundiu = "Você pode ter confundido o conceito central com uma ideia próxima, mas que não responde exatamente ao que foi pedido."
            evitar = "Leia o comando da questão primeiro e grife mentalmente o verbo principal: identificar, comparar, explicar ou concluir."
        evitar_e_do_assunto = True
    elif materia_norm == "ingles":
        confundiu = "Você provavelmente confundiu vocabulário, tempo verbal ou uma pista de contexto da frase."
        evitar = "Procure palavras-chave de tempo e sentido antes de responder. Em inglês, pequenos marcadores como always, yesterday e will mudam a regra."
        evitar_e_do_assunto = True
    else:
        confundiu = "Você escolheu uma alternativa que parece plausível, mas não responde exatamente ao foco da pergunta."
        evitar = "Separe o tema da questão da pergunta final. Primeiro entenda o assunto; depois confirme o que a alternativa precisa provar."
        evitar_e_do_assunto = False

    # MELHORIA: `_feedback_conceitual` nomeia o que o aluno marcou e o que era
    # a resposta -- mas so era alcancada em exatas. Todas as outras materias
    # caiam num texto de gaveta que serve para qualquer questao: "voce
    # escolheu uma alternativa que parece plausivel, mas nao responde
    # exatamente ao foco da pergunta". Visto na tela numa questao de Educacao
    # Fisica sobre ATP e fosfocreatina, onde nao dizia nem o que o aluno
    # marcou nem por que estava errado.
    #
    # O "confundiu" dela e sempre melhor: cita as duas alternativas pelo nome.
    # O "evitar" so entra onde a materia nao tinha conselho proprio -- "volte
    # ao texto e procure a frase que comprova" (humanas) e "marcadores como
    # always, yesterday e will" (ingles) sao especificos demais para trocar
    # por um conselho geral.
    if materia_norm not in {"matematica", "fisica", "quimica"}:
        conceitual = _feedback_conceitual(pergunta_norm, resposta_aluno, resposta_correta)
        if conceitual:
            confundiu = conceitual[0]
            if not evitar_e_do_assunto:
                evitar = conceitual[1]

    # MELHORIA: "muito parecida" disparava quando as 8 primeiras letras
    # batiam. Medido nos bancos em 13/09/2026: 2.946 pares, 58% deles com
    # alternativas pouco parecidas ("moléculas de amônia" x "moléculas
    # apolares") -- a frase apagava a citação das duas e, em 13 pares, o
    # diagnóstico numérico. Agora só texto sem número que muda num detalhe, e
    # continua citando as duas.
    if _quase_iguais(resposta_aluno, resposta_correta):
        aluno_txt = " ".join(str(resposta_aluno).split())
        certa_txt = " ".join(str(resposta_correta).split())
        confundiu = (
            f"Você marcou “{_citacao(aluno_txt)}”, quase igual à resposta “{_citacao(certa_txt)}”{_fim_de_frase(certa_txt)} "
            "A diferença está num detalhe: releia as duas palavra por palavra antes de marcar."
        )

    return {
        "confundiu": confundiu,
        "evitar": evitar,
        "treino": f"Treine mais uma questão sobre {tema} para fixar o raciocínio enquanto o erro ainda está fresco.",
    }
