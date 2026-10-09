"""
Serviço de geração de questões no estilo ENEM.

Fluxo:
    gerar_questao_enem(area_bncc, dificuldade)
        → tenta IA até 3x
        → valida payload
        → deduplica por histórico de sessão
        → fallback offline se tudo falhar
"""
from __future__ import annotations

import os
import random
import re
import time

from core.text_cleanup import aplicar_acentos_pt, chave_busca
from services import historico_perguntas

# CORRIGIDO: era "services.ai_service" (módulo inexistente) → correto é ia_service
from services.ia_service import gerar_json_ia, obter_ultimo_provedor_ia


def _orcamento_ia_enem_segundos() -> float:
    # MELHORIA: mesmo bug ja corrigido no Oraculo e no Laboratorio. O loop de
    # retry do ENEM (ate 5 tentativas, usado tambem pela Batalha contra
    # Chefes) chamava gerar_json_ia sem "deadline_seconds" — cada tentativa
    # usava o orcamento maximo do zero, podendo somar bem mais que os 60s do
    # timeout do Gunicorn no pior caso.
    valor = os.getenv("ENEM_IA_BUDGET_SECONDS")
    if valor is not None:
        try:
            return max(6.0, min(float(valor), 26.0))
        except (TypeError, ValueError):
            pass
    return 22.0
from services.ia import citacao_alternativas
from services.ia.explicacao_vazia import explicacao_tem_corpo
from services.ia.opcoes_no_enunciado import pergunta_embute_opcoes_com_letra
from services.ia.normalizacao import limpar_rotulos_alternativas

# ── Áreas e disciplinas do ENEM ──────────────────────────────────────────────

AREAS_ENEM: dict[str, list[str]] = {
    "Linguagens e suas Tecnologias": [
        "Portugues", "Literatura", "Artes", "Educacao Fisica", "Ingles",
    ],
    "Matematica e suas Tecnologias": [
        "Matematica",
    ],
    "Ciencias da Natureza e suas Tecnologias": [
        "Biologia", "Fisica", "Quimica",
    ],
    "Ciencias Humanas e Sociais Aplicadas": [
        "Historia", "Geografia", "Filosofia", "Sociologia",
    ],
}

DIFICULDADES = ["Facil", "Medio", "Dificil"]

# MELHORIA: os tres valores acima sao chave -- entram na sessao, no log e
# na comparacao. So que as duas telas mostravam a chave crua, entao o aluno
# lia "Facil" e "Dificil" sem acento na propria lista de escolha. Mesma
# separacao de LABEL_AREA logo abaixo: a chave nao muda, o rotulo muda.
LABEL_DIFICULDADE: dict[str, str] = {"Facil": "Fácil", "Medio": "Médio", "Dificil": "Difícil"}


def exibir_dificuldade(valor: str) -> str:
    return LABEL_DIFICULDADE.get(str(valor or ""), str(valor or ""))

# Abreviações para exibição
LABEL_AREA: dict[str, str] = {
    "Linguagens e suas Tecnologias": "Linguagens",
    "Matematica e suas Tecnologias": "Matemática",
    "Ciencias da Natureza e suas Tecnologias": "Ciências da Natureza",
    "Ciencias Humanas e Sociais Aplicadas": "Ciências Humanas",
}

# ── Histórico de deduplicação — session_state ────────────────────────────────
# MELHORIA: histórico por aluno no session_state em vez de dict global em memória.
# Dict global zerava ao reiniciar o processo; session_state persiste por sessão.

def _get_historico_sessao(chave: tuple) -> list[str]:
    # Guardado FORA do cookie desde 13/09/2026: ver services/historico_perguntas.py.
    # O enunciado do ENEM e o mais longo dos tres modos, e ia inteiro no cookie.
    return historico_perguntas.ler(f"enem_hist_{'_'.join(str(c) for c in chave)}")


def _set_historico_sessao(chave: tuple, historico: list[str]) -> None:
    historico_perguntas.gravar(f"enem_hist_{'_'.join(str(c) for c in chave)}", historico)


# ── Dificuldade adaptativa ────────────────────────────────────────────────────

def inferir_dificuldade_aluno(logs_aluno: list[dict]) -> str:
    """
    Infere o nível de dificuldade adequado com base no histórico recente do aluno.
    Usa os últimos 10 logs para evitar que desempenhos antigos distorçam a sugestão.
    """
    if not logs_aluno or len(logs_aluno) < 5:
        return "Medio"
    recentes = logs_aluno[:10]
    pct = sum(1 for log in recentes if log.get("resultado") == "Acertou") / len(recentes)
    if pct >= 0.75:
        return "Dificil"
    if pct >= 0.45:
        return "Medio"
    return "Facil"


# ── Fallback offline por área ─────────────────────────────────────────────────

# Rótulos da matriz conferidos com a Matriz de Referência do INEP em
# 16/09/2026. Quatro não existiam ("Competência 6 – Habilidade H24" em Humanas,
# onde a 6 vai de H26 a H30) e sete existiam mas não eram da questão: a queda
# livre estava como biotecnologia (H11), a porcentagem como geometria (H8), a
# charge como língua estrangeira (H7). Cada um passou para a habilidade cuja
# descrição é a do que a questão pede.
_FALLBACK_POR_AREA: dict[str, list[dict]] = {
    "Linguagens e suas Tecnologias": [
        {
            "pergunta": (
                "Em um texto argumentativo, a função do parágrafo de conclusão é:"
            ),
            "alternativas": [
                "Introduzir o tema com dados estatísticos",
                "Apresentar os argumentos centrais pela primeira vez",
                "Retomar a tese e propor encaminhamentos ou síntese",
                "Refutar os contra-argumentos do texto",
                "Descrever o contexto histórico do tema",
            ],
            "correta": "Retomar a tese e propor encaminhamentos ou síntese",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Estrutura do texto dissertativo-argumentativo"},
                {"tipo": "texto", "conteudo": "A conclusão retoma a tese apresentada na introdução e apresenta uma proposta de intervenção ou síntese dos argumentos, encerrando o texto de forma coerente."},
                {"tipo": "resultado", "conteudo": "Resposta: Retomar a tese e propor encaminhamentos ou síntese"},
            ],
            "matriz_enem": "Competência 6 – Habilidade H18",
            "area_bncc": "Linguagens e suas Tecnologias",
            "competencia_bncc": "Produzir argumentos com base em repertório cultural",
            "habilidade_bncc": "Produzir textos dissertativos com coesão e coerência",
        },
        {
            "pergunta": (
                "A charge e o meme são gêneros textuais que utilizam humor e ironia para "
                "criticar situações sociais e políticas. A principal característica que os "
                "diferencia de uma notícia jornalística é:"
            ),
            "alternativas": [
                "O uso obrigatório de dados estatísticos verificáveis",
                "A intenção de informar com imparcialidade e objetividade",
                "O uso de linguagem figurada e recursos visuais para criar sentido crítico",
                "A exigência de registro formal e vocabulário técnico",
                "A reprodução fiel de declarações de autoridades públicas",
            ],
            "correta": "O uso de linguagem figurada e recursos visuais para criar sentido crítico",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Gêneros textuais de crítica social"},
                {"tipo": "texto", "conteudo": "Charges e memes recorrem à ironia, metáforas e imagens para expressar opinião e crítica, diferindo da notícia, que preza pela objetividade e imparcialidade."},
                {"tipo": "resultado", "conteudo": "Resposta: uso de linguagem figurada e recursos visuais para criar sentido crítico"},
            ],
            "matriz_enem": "Competência 7 – Habilidade H22",
            "area_bncc": "Linguagens e suas Tecnologias",
            "competencia_bncc": "Compreender e usar a linguagem em diferentes contextos",
            "habilidade_bncc": "Identificar os efeitos de sentido decorrentes do uso de recursos visuais e verbais",
        },
        {
            "pergunta": (
                "Leia o trecho: 'A língua é viva e está em constante transformação; "
                "palavras surgem, desaparecem e mudam de significado ao longo do tempo.' "
                "Esse fenômeno linguístico é conhecido como:"
            ),
            "alternativas": [
                "Variação diacrônica",
                "Hipercorreção gramatical",
                "Purismo linguístico",
                "Norma culta estática",
                "Desvio fonológico",
            ],
            "correta": "Variação diacrônica",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Variação linguística ao longo do tempo"},
                {"tipo": "texto", "conteudo": "A variação diacrônica refere-se às mudanças que ocorrem na língua ao longo do tempo histórico, como surgimento de neologismos e obsolescência de palavras."},
                {"tipo": "resultado", "conteudo": "Resposta: Variação diacrônica"},
            ],
            "matriz_enem": "Competência 8 – Habilidade H25",
            "area_bncc": "Linguagens e suas Tecnologias",
            "competencia_bncc": "Compreender a língua como fenômeno cultural e histórico",
            "habilidade_bncc": "Reconhecer a variação linguística como fator histórico e social",
        },
    ],
    "Matematica e suas Tecnologias": [
        {
            "pergunta": (
                "Uma loja oferece 20% de desconto em um produto que custa R$ 250,00. "
                "Qual o valor final pago pelo cliente?"
            ),
            "alternativas": [
                "R$ 50,00",
                "R$ 180,00",
                "R$ 200,00",
                "R$ 220,00",
                "R$ 230,00",
            ],
            "correta": "R$ 200,00",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Cálculo de desconto percentual"},
                {"tipo": "texto", "conteudo": "20% de R$ 250,00 = 0,20 × 250 = R$ 50,00 de desconto."},
                {"tipo": "resultado", "conteudo": "Valor final = 250 - 50 = R$ 200,00"},
            ],
            "matriz_enem": "Competência 1 – Habilidade H3",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Construir raciocínio lógico-matemático",
            "habilidade_bncc": "Resolver problemas com porcentagem em contextos cotidianos",
        },
        {
            "pergunta": (
                "Uma torneira perde 1 gota de água por segundo. Se cada gota equivale a "
                "0,05 mL, quantos litros de água são desperdiçados em 24 horas?"
            ),
            "alternativas": [
                "4,32 litros",
                "3,00 litros",
                "43,2 litros",
                "0,432 litros",
                "432 litros",
            ],
            "correta": "4,32 litros",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Cálculo de desperdício de água"},
                {"tipo": "texto", "conteudo": "Gotas por dia: 1 × 60 × 60 × 24 = 86.400 gotas. Volume: 86.400 × 0,05 mL = 4.320 mL = 4,32 litros."},
                {"tipo": "resultado", "conteudo": "Resposta: 4,32 litros"},
            ],
            "matriz_enem": "Competência 3 – Habilidade H12",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Construir raciocínio lógico-matemático",
            "habilidade_bncc": "Resolver problemas envolvendo unidades de medida e conversões",
        },
        {
            "pergunta": (
                "Em um grupo de 40 alunos, 60% são meninas. Das meninas, 25% praticam "
                "esporte. Quantas meninas praticam esporte?"
            ),
            "alternativas": [
                "6",
                "10",
                "15",
                "24",
                "4",
            ],
            "correta": "6",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Porcentagem em duas etapas"},
                {"tipo": "texto", "conteudo": "Meninas: 60% de 40 = 24. Praticam esporte: 25% de 24 = 6 alunas."},
                {"tipo": "resultado", "conteudo": "Resposta: 6 meninas"},
            ],
            "matriz_enem": "Competência 1 – Habilidade H3",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Modelar situações usando linguagem matemática",
            "habilidade_bncc": "Resolver problemas com porcentagem em múltiplas etapas",
        },
    ],
    "Ciencias da Natureza e suas Tecnologias": [
        {
            "pergunta": (
                "A fotossíntese é um processo que ocorre nos cloroplastos e pode ser "
                "resumido pela equação: CO₂ + H₂O → glicose + O₂. "
                "Qual é a principal fonte de energia para esse processo?"
            ),
            "alternativas": [
                "Energia química proveniente do solo",
                "Luz solar captada pela clorofila",
                "Calor liberado pela respiração celular",
                "Gás carbônico do ambiente",
                "Água absorvida pelas raízes",
            ],
            "correta": "Luz solar captada pela clorofila",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Fotossíntese e energia luminosa"},
                {"tipo": "texto", "conteudo": "A clorofila, presente nos cloroplastos, absorve a luz solar para converter CO₂ e H₂O em glicose e oxigênio. A luz é a fonte de energia que impulsiona a reação."},
                {"tipo": "resultado", "conteudo": "Fonte de energia: Luz solar captada pela clorofila"},
            ],
            "matriz_enem": "Competência 3 – Habilidade H9",
            "area_bncc": "Ciencias da Natureza e suas Tecnologias",
            "competencia_bncc": "Investigar fenômenos naturais e tecnológicos",
            "habilidade_bncc": "Explicar processos biológicos com base em conceitos científicos",
        },
        {
            "pergunta": (
                "O aquecimento global é causado principalmente pelo aumento da concentração "
                "de gases na atmosfera que retêm o calor irradiado pela Terra. Esse fenômeno "
                "é chamado de:"
            ),
            "alternativas": [
                "Efeito estufa intensificado",
                "Inversão térmica",
                "Camada de ozônio",
                "Ciclo hidrológico",
                "Eutrofização",
            ],
            "correta": "Efeito estufa intensificado",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Efeito estufa e aquecimento global"},
                {"tipo": "texto", "conteudo": "O efeito estufa é natural e necessário, mas a emissão excessiva de CO₂ e metano pelo ser humano intensifica esse efeito, elevando a temperatura média do planeta."},
                {"tipo": "resultado", "conteudo": "Resposta: Efeito estufa intensificado"},
            ],
            "matriz_enem": "Competência 3 – Habilidade H10",
            "area_bncc": "Ciencias da Natureza e suas Tecnologias",
            "competencia_bncc": "Entender o impacto das atividades humanas no meio ambiente",
            "habilidade_bncc": "Relacionar fenômenos ambientais a causas antrópicas",
        },
        {
            "pergunta": (
                "Dois objetos de massas diferentes são largados do mesmo ponto em queda "
                "livre, sem resistência do ar. Como chegam ao solo?"
            ),
            "alternativas": [
                "O mais pesado chega primeiro",
                "O mais leve chega primeiro",
                "Chegam ao mesmo tempo",
                "Depende do tamanho dos objetos",
                "Depende da temperatura do ambiente",
            ],
            "correta": "Chegam ao mesmo tempo",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Queda livre e massa dos objetos"},
                {"tipo": "texto", "conteudo": "Na ausência de resistência do ar, todos os corpos caem com a mesma aceleração gravitacional (g ≈ 9,8 m/s²), independentemente da massa. Isso foi demonstrado por Galileu."},
                {"tipo": "resultado", "conteudo": "Resposta: chegam ao mesmo tempo"},
            ],
            "matriz_enem": "Competência 6 – Habilidade H20",
            "area_bncc": "Ciencias da Natureza e suas Tecnologias",
            "competencia_bncc": "Compreender leis e princípios das Ciências da Natureza",
            "habilidade_bncc": "Aplicar conceitos de mecânica clássica em situações concretas",
        },
    ],
    "Ciencias Humanas e Sociais Aplicadas": [
        {
            "pergunta": (
                "O processo de globalização intensificado a partir do final do século XX "
                "provocou, entre outros efeitos:"
            ),
            "alternativas": [
                "O isolamento econômico dos países em desenvolvimento",
                "A extinção do comércio internacional",
                "A homogeneização absoluta das culturas mundiais",
                "A maior integração econômica e cultural entre os países",
                "A redução das desigualdades sociais em escala global",
            ],
            "correta": "A maior integração econômica e cultural entre os países",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Globalização e integração mundial"},
                {"tipo": "texto", "conteudo": "A globalização aproximou economias, culturas e mercados, mas também aprofundou desigualdades. Não gerou homogeneidade total nem isolamento, mas sim interdependência entre nações."},
                {"tipo": "resultado", "conteudo": "Efeito principal: maior integração econômica e cultural"},
            ],
            "matriz_enem": "Competência 2 – Habilidade H9",
            "area_bncc": "Ciencias Humanas e Sociais Aplicadas",
            "competencia_bncc": "Analisar processos políticos, históricos e socioculturais",
            "habilidade_bncc": "Interpretar transformações econômicas e sociais contemporâneas",
        },
        {
            "pergunta": (
                "A Revolução Francesa (1789) é considerada um marco da modernidade política "
                "porque inaugurou os princípios de:"
            ),
            "alternativas": [
                "Liberdade, Igualdade e Fraternidade como bases do Estado moderno",
                "Monarquia absoluta e direito divino dos reis",
                "Colonialismo e expansão territorial europeia",
                "Mercantilismo e acúmulo de metais preciosos",
                "Feudalismo e servidão como organização social",
            ],
            "correta": "Liberdade, Igualdade e Fraternidade como bases do Estado moderno",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Revolução Francesa e modernidade política"},
                {"tipo": "texto", "conteudo": "A Revolução Francesa derrubou o Antigo Regime e estabeleceu os ideais iluministas de liberdade, igualdade e fraternidade como fundamentos do Estado liberal moderno."},
                {"tipo": "resultado", "conteudo": "Resposta: Liberdade, Igualdade e Fraternidade"},
            ],
            "matriz_enem": "Competência 5 – Habilidade H23",
            "area_bncc": "Ciencias Humanas e Sociais Aplicadas",
            "competencia_bncc": "Compreender transformações históricas e seus impactos políticos",
            "habilidade_bncc": "Identificar as bases dos Estados modernos e suas revoluções fundadoras",
        },
        {
            "pergunta": (
                "A urbanização acelerada no Brasil, especialmente entre 1950 e 1980, "
                "gerou como consequência direta:"
            ),
            "alternativas": [
                "Redução completa das desigualdades regionais",
                "Crescimento das favelas e déficit habitacional nas grandes cidades",
                "Queda da industrialização no Sudeste do país",
                "Aumento da população rural em todas as regiões",
                "Extinção dos latifúndios no interior do país",
            ],
            "correta": "Crescimento das favelas e déficit habitacional nas grandes cidades",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Urbanização e desigualdade no Brasil"},
                {"tipo": "texto", "conteudo": "O êxodo rural intenso levou massas populacionais às cidades sem infraestrutura adequada, gerando periferias, favelas e déficit habitacional, especialmente no Sudeste industrial."},
                {"tipo": "resultado", "conteudo": "Resposta: crescimento das favelas e déficit habitacional"},
            ],
            "matriz_enem": "Competência 6 – Habilidade H26",
            "area_bncc": "Ciencias Humanas e Sociais Aplicadas",
            "competencia_bncc": "Analisar processos sociais e espaciais do Brasil contemporâneo",
            "habilidade_bncc": "Relacionar urbanização, industrialização e desigualdade social",
        },
    ],
}


# ── Matriz de Referência do ENEM ──────────────────────────────────────────────
#
# MELHORIA: o cabeçalho da questão mostrava "Competência 3 – Habilidade 31", e
# a Matriz de Referência do INEP tem 30 habilidades por área, cada uma dentro
# de UMA competência. Em 16/09/2026, 7 dos 10 rótulos vistos da IA eram
# impossíveis -- "Habilidade 42" em Matemática, "Competência 3 – Habilidade
# H30" em Linguagens, onde a 3 vai de H9 a H11 --, e 4 dos 15 do próprio banco
# de reserva também. A IA escolhe a competência e numera a habilidade como se
# fosse um item dela (competência 4 -> H41, H42, H43): a competência fica, e a
# habilidade só aparece quando é mesmo daquela competência.
_HABILIDADES_POR_COMPETENCIA: dict[str, list[tuple[int, int]]] = {
    "Linguagens e suas Tecnologias": [(1, 4), (5, 8), (9, 11), (12, 14), (15, 17), (18, 20), (21, 24), (25, 27), (28, 30)],
    "Matematica e suas Tecnologias": [(1, 5), (6, 9), (10, 14), (15, 18), (19, 23), (24, 26), (27, 30)],
    "Ciencias da Natureza e suas Tecnologias": [(1, 4), (5, 7), (8, 12), (13, 16), (17, 19), (20, 23), (24, 27), (28, 30)],
    "Ciencias Humanas e Sociais Aplicadas": [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 30)],
}

# MELHORIA: so com as faixas no prompt, o rotulo passou a existir, mas nao a
# combinar com a questao. Em Linguagens a IA escolhia quase sempre a
# Competencia 2 -- a de lingua estrangeira -- para questoes de ironia e de
# persuasao em portugues: 4 dos 5 rotulos de Linguagens vistos em 16/09/2026,
# e o quinto era a Competencia 1, a do uso das tecnologias. O assunto de cada
# competencia, resumido do enunciado do INEP, vai junto das faixas.
_TEMAS_DAS_COMPETENCIAS: dict[str, list[str]] = {
    "Linguagens e suas Tecnologias": [
        "uso das tecnologias da comunicação e informação",
        "língua estrangeira moderna",
        "linguagem corporal",
        "arte",
        "texto literário e seu contexto",
        "organização dos textos e funções da linguagem",
        "opiniões, argumentação e persuasão",
        "língua portuguesa: variação e norma-padrão",
        "natureza e impacto das tecnologias da comunicação e informação",
    ],
    "Matematica e suas Tecnologias": [
        "números e operações",
        "geometria",
        "grandezas e medidas",
        "variação de grandezas e proporcionalidade",
        "álgebra e modelagem",
        "gráficos e tabelas",
        "estatística e probabilidade",
    ],
    "Ciencias da Natureza e suas Tecnologias": [
        "ciência e tecnologia como construção humana",
        "tecnologias das ciências naturais no cotidiano",
        "ambiente: degradação e conservação",
        "organismos, ambiente e saúde",
        "métodos e procedimentos científicos",
        "física",
        "química",
        "biologia",
    ],
    "Ciencias Humanas e Sociais Aplicadas": [
        "cultura e identidade",
        "espaço geográfico e relações de poder",
        "instituições, conflitos e movimentos sociais",
        "técnica, tecnologia e trabalho",
        "cidadania e democracia",
        "sociedade e natureza no espaço",
    ],
}
_COMPETENCIA_NO_ROTULO = re.compile(r"(?i:\bcompet[eê]ncia(?:\s+de\s+[áa]rea)?)\s*(\d+)|\bC\s?(\d+)\b")
_HABILIDADE_NO_ROTULO = re.compile(r"(?i:\bhabilidade)\s*H?\s*(\d+)|\bH\s?(\d+)\b")


def _numero_no_rotulo(achado: re.Match | None) -> int | None:
    return int(achado.group(1) or achado.group(2)) if achado else None


def _rotulo_da_matriz(rotulo: str, area: str) -> str:
    """O rótulo "Competência N – Habilidade HN" com o que existe na matriz da área.

    Rótulo que não fala de competência nem de habilidade ("Questão autoral –
    Matemática") fica como está. Habilidade de outra competência sai; a
    habilidade sozinha ganha a competência a que pertence.
    """
    texto = str(rotulo or "")
    faixas = _HABILIDADES_POR_COMPETENCIA.get(area)
    competencia = _numero_no_rotulo(_COMPETENCIA_NO_ROTULO.search(texto))
    habilidade = _numero_no_rotulo(_HABILIDADE_NO_ROTULO.search(texto))
    if not faixas or (competencia is None and habilidade is None):
        return texto
    if competencia is None:
        competencia = next(
            (numero for numero, (inicio, fim) in enumerate(faixas, 1) if inicio <= habilidade <= fim),
            0,
        )
    if not 1 <= competencia <= len(faixas):
        return ""
    inicio, fim = faixas[competencia - 1]
    if habilidade is not None and inicio <= habilidade <= fim:
        return f"Competência {competencia} – Habilidade H{habilidade}"
    return f"Competência {competencia}"


def _regra_da_matriz(area: str) -> str:
    """A linha do prompt com o assunto e as habilidades de cada competência."""
    faixas = _HABILIDADES_POR_COMPETENCIA.get(area)
    if not faixas:
        return ""
    lista = "; ".join(
        f"Competência {numero} ({tema}): H{inicio} a H{fim}"
        for numero, ((inicio, fim), tema) in enumerate(zip(faixas, _TEMAS_DAS_COMPETENCIAS[area]), 1)
    )
    return (
        '\n- "matriz_enem" segue a Matriz de Referência do ENEM desta área. Escolha a competência pelo '
        f"assunto da questão e uma habilidade dela: {lista}."
    )


# ── Geração via IA ────────────────────────────────────────────────────────────

def _prompt_enem(area: str, dificuldade: str) -> tuple[str, str]:
    system = (
        "Você é um gerador de questões no estilo ENEM para o Ensino Médio brasileiro. "
        "Responda SOMENTE com JSON válido, sem texto adicional. "
        "As questões devem ter contexto, ser interdisciplinares quando possível e "
        "exigir interpretação e raciocínio, não apenas memorização. "
        "Use linguagem acessível e situações do cotidiano ou da cultura brasileira. "
        "NUNCA escreva as alternativas dentro do campo pergunta (nada como 'A) ... B) ... C) ...'): "
        "as opções vão somente no array alternativas, e o enunciado nunca deve citar letra de alternativa."
    )
    user = f"""
Gere uma questão ENEM de nível {dificuldade} para a área: {area}

Formato OBRIGATÓRIO (JSON):
{{
  "pergunta": "enunciado completo com contexto situacional",
  "alternativas": ["alternativa A completa", "B", "C", "D", "E"],
  "correta": "texto exato de uma das alternativas",
  "explicacao": [
    {{"tipo": "bold", "conteudo": "título curto da explicação"}},
    {{"tipo": "texto", "conteudo": "explicação pedagógica clara"}},
    {{"tipo": "resultado", "conteudo": "por que a alternativa correta está certa"}}
  ],
  "area_bncc": "{area}",
  "competencia_bncc": "competência avaliada",
  "habilidade_bncc": "habilidade específica avaliada",
  "matriz_enem": "Competência N – Habilidade HN"
}}

Regras:
- Exatamente 5 alternativas (A a E)
- O campo "correta" deve ser o texto idêntico de uma das alternativas
- Nível {dificuldade}: {"questão direta, enunciado claro" if dificuldade == "Facil" else "requer análise e relacionamento de conceitos" if dificuldade == "Medio" else "requer síntese, crítica e raciocínio complexo"}
- NÃO use LaTeX
- Evite questões de pura memorização
- Não invente nome próprio (empresa, lei, acordo, obra, povo indígena, prática religiosa) e não atribua um fato real a lugar, autor ou data de que você não tenha certeza; na dúvida, escreva de forma genérica{_regra_da_matriz(area)}
"""
    if area == "Matematica e suas Tecnologias":
        user += """

Regras extras para Matematica:
- A alternativa correta precisa bater exatamente com o calculo do enunciado.
- Se usar dinheiro, escreva sempre no formato "R$ 123,45".
- Nao invente justificativa para uma alternativa que contradiz o calculo.
- Em problema de combustivel: litros = distancia / consumo; custo = litros * preco. Se o enunciado disser ida e volta, dobre a distancia.
"""
    return system, user


def _normalizar_decimal_pt(valor: str) -> float | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _valores_monetarios(texto: str) -> list[float]:
    valores = []
    for match in re.findall(r"R\$\s*([0-9]+(?:\.[0-9]{3})*(?:,[0-9]{1,2})?)", str(texto or "")):
        valor = _normalizar_decimal_pt(match)
        if valor is not None:
            valores.append(valor)
    return valores


def _primeiro_numero_antes(texto: str, padrao: str) -> float | None:
    match = re.search(rf"([0-9]+(?:[,.][0-9]+)?)\s*{padrao}", str(texto or ""), flags=re.IGNORECASE)
    return _normalizar_decimal_pt(match.group(1)) if match else None


def _valor_monetario_da_resposta(texto: str) -> float | None:
    valores = _valores_monetarios(texto)
    return valores[0] if valores else None


def _quase_igual(valor: float, esperado: float, tolerancia: float = 0.02) -> bool:
    return abs(valor - esperado) <= tolerancia


def _validar_matematica_combustivel(q: dict) -> bool:
    pergunta = str(q.get("pergunta", "") or "")
    texto = pergunta.lower()
    if "gasolina" not in texto and "combust" not in texto:
        return True

    distancia = _primeiro_numero_antes(pergunta, r"km")
    consumo = _primeiro_numero_antes(pergunta, r"(?:km/l|km por litro|km\/litro)")
    precos = _valores_monetarios(pergunta)
    preco_litro = precos[-1] if precos else None
    correta_valor = _valor_monetario_da_resposta(str(q.get("correta", "")))

    if distancia is None or consumo is None or preco_litro is None or correta_valor is None:
        return False

    multiplicador = 2 if "ida e volta" in texto else 1
    esperado = round((distancia * multiplicador / consumo) * preco_litro, 2)
    return _quase_igual(correta_valor, esperado)


def _validar_matematica(q: dict) -> bool:
    alternativas = [str(alt) for alt in (q.get("alternativas", []) or [])]
    if len(set(alternativas)) != len(alternativas):
        return False
    if not _validar_matematica_combustivel(q):
        return False
    return True


def _validar_questao(q: dict) -> bool:
    """Valida se o payload da questão está completo e consistente."""
    if not q or not isinstance(q, dict):
        return False
    if not q.get("pergunta"):
        return False
    alts = q.get("alternativas", [])
    # Aceita 4 (algumas respostas da IA vêm no formato escolar comum)
    # ou 5 alternativas (padrao ENEM).
    if len(alts) < 4:
        return False
    correta = q.get("correta", "")
    if not correta or correta not in alts:
        return False
    area = q.get("area_bncc", "")
    if area == "Matematica e suas Tecnologias" and not _validar_matematica(q):
        return False
    # MELHORIA: nada aqui checava se a explicacao tinha conteudo de
    # verdade -- so o titulo ("Calculo da energia necessaria") passava
    # direto, visto ao vivo em producao em 28/09/2026. Mesmo criterio do
    # Oraculo/Escape Room/RPG/Treino/Laboratorio (services/ia/validacao.py).
    if not explicacao_tem_corpo(q.get("explicacao")):
        return False
    # MELHORIA: achado 3.1 do relatorio de QA (Batalha 7/Chefe 3): a IA as
    # vezes devolve o enunciado com as proprias opcoes ja escritas e
    # rotuladas ("A) adubos inorganicos; B) plantar leguminosas..."), numa
    # ordem que nao bate com a lista embaralhada exibida na tela -- o aluno
    # que le a letra no enunciado e marca por ela erra sem erro de conteudo.
    if pergunta_embute_opcoes_com_letra(q.get("pergunta")):
        return False
    return True


def _normalizar_alternativas_rotuladas(q: dict) -> dict:
    dados = dict(q or {})
    alternativas_originais = [str(alt) for alt in (dados.get("alternativas", []) or [])]
    alternativas_limpas = limpar_rotulos_alternativas(alternativas_originais)
    dados["alternativas"] = alternativas_limpas

    correta = str(dados.get("correta", ""))
    if correta in alternativas_originais:
        dados["correta"] = alternativas_limpas[alternativas_originais.index(correta)]
    elif correta in alternativas_limpas:
        dados["correta"] = correta
    else:
        correta_limpa = limpar_rotulos_alternativas(alternativas_originais + [correta])[-1]
        dados["correta"] = correta_limpa

    return dados


# MELHORIA: a IA escreve a explicacao na ordem em que ELA pos as
# alternativas ("... que corresponde a alternativa B"), e o embaralhamento vem
# depois. A explicacao passava a apontar para a letra errada: na captura 07c do
# TG (10/09/2026) a certa era a C e o texto dizia "a alternativa A esta
# correta". Numa amostra de 16/09/2026, 5 das 10 explicacoes da IA citavam a
# letra -- sempre a da certa, na ordem original. A regex e a troca vivem em
# services.ia.citacao_alternativas para serem reaproveitadas pelo
# embaralhamento generico (Oraculo, Escape Room, RPG, Laboratorio).
_LETRAS_DAS_ALTERNATIVAS = citacao_alternativas.LETRAS_DAS_ALTERNATIVAS
_CITACAO_DE_ALTERNATIVA = citacao_alternativas.CITACAO_DE_ALTERNATIVA
_trocar_letras_citadas = citacao_alternativas.trocar_letras_citadas


def _embaralhar_alternativas_questao(q: dict) -> dict:
    dados = dict(q or {})
    alternativas = [str(alt) for alt in (dados.get("alternativas", []) or [])]
    correta = str(dados.get("correta", ""))
    if len(alternativas) < 2 or correta not in alternativas:
        return dados

    itens = [
        {"alternativa": alternativa, "correta": alternativa == correta, "posicao": posicao}
        for posicao, alternativa in enumerate(alternativas)
    ]
    random.shuffle(itens)
    dados["alternativas"] = [item["alternativa"] for item in itens]
    dados["correta"] = next((item["alternativa"] for item in itens if item["correta"]), correta)

    # Se o proprio enunciado ou uma alternativa ja fala em "alternativa A", a
    # letra da explicacao pode ser da historia, e nao da lista: fica como esta.
    if _CITACAO_DE_ALTERNATIVA.search(" ".join([str(dados.get("pergunta", ""))] + alternativas)):
        return dados
    nova_letra = {
        _LETRAS_DAS_ALTERNATIVAS[item["posicao"]]: _LETRAS_DAS_ALTERNATIVAS[nova]
        for nova, item in enumerate(itens)
        if max(nova, item["posicao"]) < len(_LETRAS_DAS_ALTERNATIVAS)
    }
    for campo in ("explicacao", "passos_resolucao"):
        if campo in dados:
            dados[campo] = _corrigir_bloco_textual(
                dados[campo], lambda texto: _trocar_letras_citadas(texto, nova_letra)
            )
    return dados


_CORRECOES_TEXTO_ENEM = {
    r"\breducir\b": "reduzir",
    r"\bReducir\b": "Reduzir",
    r"\bredusir\b": "reduzir",
    r"\bRedusir\b": "Reduzir",
    r"\baumentar a evapotranspiraçao\b": "aumentar a evapotranspiração",
    r"\bevapotraspiração\b": "evapotranspiração",
    r"\bevapotraspiracao\b": "evapotranspiração",
    r"\bformaçao\b": "formação",
    r"\bformacao\b": "formação",
    r"\bpopulaçao\b": "população",
    r"\bpopulacao\b": "população",
    r"\bregiao\b": "região",
    r"\bfertilidade\b": "fertilidade",
    r"\batraves\b": "através",
    r"\bacao\b": "ação",
    r"\bAcao\b": "Ação",
    r"\bsolo para torná-lo\b": "solo para torná-lo",
    r"\bconsumo de combustivel\b": "consumo de combustível",
    r"\bcombustivel\b": "combustível",
    r"\bcalculo\b": "cálculo",
    r"\bdistancia\b": "distância",
    r"\bpreco\b": "preço",
    r"\bfamilia\b": "família",
    r"\bveiculo\b": "veículo",
}


def _corrigir_texto_enem(texto: str) -> str:
    valor = aplicar_acentos_pt(str(texto or ""))
    for padrao, substituto in _CORRECOES_TEXTO_ENEM.items():
        valor = re.sub(padrao, substituto, valor)
    valor = re.sub(r"\s+([,.;:!?])", r"\1", valor)
    # MELHORIA: o espaco entrava depois de QUALQUER pontuacao seguida de algo
    # que nao fosse espaco. Medido em 15/09/2026 nos 2.235 textos do ENEM: 70
    # questoes com espaco antes da aspa ou do parentese que fecha ("Leia o
    # trecho: 'A lingua e viva. '") e 9 com numero partido ("86. 400 gotas",
    # "8: 30 a. m.", "proporcao 1: 1"). O espaco so falta quando a pontuacao
    # encosta na PALAVRA seguinte -- e o ponto, so antes de maiuscula, onde a
    # frase recomeca: "a.m." e "www.gov.br" ficam como estao.
    valor = re.sub(r"([;!?])(?=[A-Za-zÀ-ÿ])", r"\1 ", valor)
    valor = re.sub(r"(?<!\d):(?=[A-Za-zÀ-ÿ])", ": ", valor)
    valor = re.sub(r"\.(?=[A-ZÀ-Ý])", ". ", valor)
    valor = re.sub(r"(?<!\d),(?=[A-Za-zÀ-ÿ])", ", ", valor)
    return re.sub(r"\s+", " ", valor).strip()


def _corrigir_bloco_textual(valor, corrigir=_corrigir_texto_enem):
    return citacao_alternativas.corrigir_bloco_textual(valor, corrigir)


def _normalizar_textos_questao(q: dict) -> dict:
    dados = dict(q or {})
    for campo in ("pergunta", "correta", "competencia_bncc", "habilidade_bncc", "matriz_enem"):
        if campo in dados:
            dados[campo] = _corrigir_texto_enem(dados[campo])
    dados["alternativas"] = [_corrigir_texto_enem(alt) for alt in (dados.get("alternativas", []) or [])]
    dados["explicacao"] = _corrigir_bloco_textual(dados.get("explicacao", []))
    return dados


def _gerar_via_ia(area: str, dificuldade: str, pular_provedores=None, deadline_seconds=None) -> dict | None:
    """Tenta gerar questão via IA. Retorna dict ou None se falhar."""
    system, user = _prompt_enem(area, dificuldade)
    dados = gerar_json_ia(
        system, user, max_tokens=900, pular_provedores=pular_provedores, deadline_seconds=deadline_seconds
    )
    provedor = obter_ultimo_provedor_ia()
    if isinstance(dados, dict):
        dados = _normalizar_alternativas_rotuladas(dados)
        dados = _normalizar_textos_questao(dados)
        dados.setdefault("area_bncc", area)
        dados.setdefault("competencia_bncc", "")
        dados.setdefault("habilidade_bncc", "")
        dados.setdefault("matriz_enem", "")
        dados["matriz_enem"] = _rotulo_da_matriz(dados["matriz_enem"], area)
    if _validar_questao(dados):
        dados["dificuldade"] = dificuldade
        dados["_origem"] = "ia"
        if provedor:
            dados["_provedor_ia"] = provedor
        return _embaralhar_alternativas_questao(dados)
    if provedor:
        print(f"[IA] {provedor} rejeitado no enem: payload-invalido")
    return None


def _fallback_matematica_variantes() -> list[dict]:
    return [
        {
            "pergunta": "Uma familia fara uma viagem de ida e volta de 240 km em cada trecho. O carro faz 12 km/l e a gasolina custa R$ 4,50 por litro. Qual sera o gasto total com gasolina?",
            "alternativas": ["R$ 90,00", "R$ 120,00", "R$ 150,00", "R$ 180,00", "R$ 210,00"],
            "correta": "R$ 180,00",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Consumo de combustivel"},
                {"tipo": "texto", "conteudo": "A distancia total é 240 km de ida + 240 km de volta = 480 km. Como o carro faz 12 km/l, serao usados 480 / 12 = 40 litros."},
                {"tipo": "resultado", "conteudo": "O custo total é 40 litros x R$ 4,50 = R$ 180,00."},
            ],
            "matriz_enem": "Competencia 4 - Habilidade H16",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Modelar problemas de proporcionalidade",
            "habilidade_bncc": "Resolver problemas envolvendo grandezas proporcionais e dinheiro",
        },
        {
            "pergunta": "Um estudante vai percorrer 300 km de carro. O veiculo consome 15 km/l e o litro da gasolina custa R$ 5,20. Qual sera o custo com gasolina para esse trajeto?",
            "alternativas": ["R$ 78,00", "R$ 96,00", "R$ 104,00", "R$ 120,00", "R$ 156,00"],
            "correta": "R$ 104,00",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Proporcionalidade no consumo"},
                {"tipo": "texto", "conteudo": "Para saber os litros usados, dividimos a distancia pelo consumo: 300 / 15 = 20 litros."},
                {"tipo": "resultado", "conteudo": "O custo é 20 x R$ 5,20 = R$ 104,00."},
            ],
            "matriz_enem": "Competencia 4 - Habilidade H16",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Modelar problemas de proporcionalidade",
            "habilidade_bncc": "Calcular custos em situacoes cotidianas",
        },
        {
            "pergunta": "Um produto de R$ 320,00 recebeu desconto de 15%. Qual valor sera pago apos o desconto?",
            "alternativas": ["R$ 48,00", "R$ 252,00", "R$ 272,00", "R$ 288,00", "R$ 305,00"],
            "correta": "R$ 272,00",
            "explicacao": [
                {"tipo": "bold", "conteudo": "Desconto percentual"},
                {"tipo": "texto", "conteudo": "O desconto é 15% de 320, isto é, 0,15 x 320 = 48 reais."},
                {"tipo": "resultado", "conteudo": "O valor final é R$ 320,00 - R$ 48,00 = R$ 272,00."},
            ],
            "matriz_enem": "Competencia 1 - Habilidade H3",
            "area_bncc": "Matematica e suas Tecnologias",
            "competencia_bncc": "Resolver problemas com porcentagem",
            "habilidade_bncc": "Calcular descontos e valores finais",
        },
    ]


def _converter_questao_para_enem(questao: dict, area: str, matriz: str) -> dict:
    alternativas = [str(opcao) for opcao in (questao.get("opcoes", []) or [])]
    correta_idx = int(questao.get("correta", 0) or 0)
    correta = alternativas[correta_idx] if 0 <= correta_idx < len(alternativas) else (alternativas[0] if alternativas else "")
    extras = [
        "Nao há dados suficientes para essa conclusao.",
        "A situacao invalida todos os conceitos apresentados.",
        "O enunciado exige apenas memorizacao, sem análise.",
    ]
    for extra in extras:
        if len(alternativas) >= 5:
            break
        if extra not in alternativas:
            alternativas.append(extra)

    return {
        "id_offline": questao.get("id_offline", ""),
        "pergunta": questao.get("pergunta", ""),
        "alternativas": alternativas,
        "correta": correta,
        "explicacao": questao.get("explicacao", []),
        "matriz_enem": matriz,
        "area_bncc": area,
        # A materia de origem: sem ela o feedback recebia a AREA ("Matematica e
        # suas Tecnologias") e perdia o diagnostico numerico.
        "materia": questao.get("materia", ""),
        "competencia_bncc": questao.get("competencia_bncc", ""),
        "habilidade_bncc": questao.get("habilidade_bncc", ""),
        # MELHORIA: o ENEM e a Batalha nunca pedem formula/passo a passo da
        # IA (o prompt em _prompt_enem nem tem esses campos, de proposito --
        # imita a prova de verdade, que nao entrega formula) -- mas Matematica
        # e Ciencias da Natureza caem aqui, reaproveitando o banco do
        # Laboratorio, que TEM formula, subformulas e passos_resolucao em
        # LaTeX. Sem podar aqui, isso vazava pro cartao de resultado do ENEM
        # (e ainda obrigava carregar o MathJax so pra essas duas telas).
        # Conferido: nenhuma das 1320 explicacoes do banco do Laboratorio
        # referencia "passo"/"acima"/"abaixo" -- o texto continua fazendo
        # sentido sozinho sem a formula.
        "formula": "",
        "subformulas": [],
        "legenda_variaveis": "",
        "passos_resolucao": [],
    }


def _questoes_distintas(questoes: list[dict]) -> list[dict]:
    """Mantem so uma copia de cada pergunta, preservando a ordem.

    MELHORIA: o banco EM guarda 80 variacoes CONSECUTIVAS do mesmo tema
    (ver QUESTOES_POR_TEMA_EM), entao fatiar as primeiras N questoes
    pegava N copias de um tema so. "listar_questoes_em('Portugues')[:80]"
    rendia 2 perguntas distintas em vez das 50 disponiveis -- por isso o
    fallback de Linguagens e de Ciencias Humanas tinha 11 questoes
    distintas apesar de montar uma lista de 320. Filtrar por texto usa o
    banco inteiro sem depender da ordem interna dele.
    """
    vistas: set[str] = set()
    distintas = []
    for questao in questoes:
        chave = str(questao.get("pergunta", "")).strip()
        if chave and chave not in vistas:
            vistas.add(chave)
            distintas.append(questao)
    return distintas


# MELHORIA: o terceiro argumento de _converter_questao_para_enem vira
# "matriz_enem", que o ENEM e a Batalha mostram no cabecalho da questao, ao
# lado da dificuldade. Era "Banco autoral offline - <area>": o aluno lia o
# nome interno do banco (as 2.220 questoes, medido em 15/09/2026). A questao
# do ENEM de verdade mostra "Competencia 3 – Habilidade H15"; estas nao tem
# habilidade mapeada, entao dizem o que sao.
def _fallback_autoral_por_area(area: str) -> list[dict]:
    from services.banks.em import listar_questoes_em
    from services.banks.laboratorio import listar_questoes_laboratorio

    if area == "Matematica e suas Tecnologias":
        return [
            _converter_questao_para_enem(questao, area, "Questão autoral – Matemática")
            for questao in _questoes_distintas(listar_questoes_laboratorio("Matematica"))
        ]

    if area == "Ciencias da Natureza e suas Tecnologias":
        questoes = _questoes_distintas(
            listar_questoes_laboratorio("Fisica")
            + listar_questoes_laboratorio("Quimica")
            + listar_questoes_em("Biologia")
        )
        return [
            _converter_questao_para_enem(questao, area, "Questão autoral – Ciências da Natureza")
            for questao in questoes
        ]

    materias_por_area = {
        "Linguagens e suas Tecnologias": ["Portugues", "Ingles", "Arte", "Educacao Fisica"],
        "Ciencias Humanas e Sociais Aplicadas": ["Historia", "Geografia", "Filosofia", "Sociologia"],
    }
    questoes = []
    for materia in materias_por_area.get(area, []):
        questoes.extend(_questoes_distintas(listar_questoes_em(materia)))
    return [
        _converter_questao_para_enem(questao, area, f"Questão autoral – {LABEL_AREA.get(area, area)}")
        for questao in questoes
    ]


def _chave_repeticao(pergunta) -> str:
    """A pergunta reduzida ao que nao muda na normalizacao.

    MELHORIA: o historico guarda a pergunta JA normalizada ("A função ... tem
    vértice"), e o filtro abaixo comparava com a pergunta CRUA do banco ("A
    funcao ... tem vertice"). Nunca casava, e a mesma questao voltava no mesmo
    simulado -- visto em 13/09/2026, questoes 1 e 2 identicas em Matematica.

    Medido no banco de reserva inteiro: o filtro so enxergava a repeticao em 23
    das 446 perguntas de Matematica (5%) e em 147 das 983 de Ciencias da
    Natureza; em 20 simulados de 30 questoes, 8 repeticoes so em Matematica.
    Sem acento, caixa, pontuacao e espaco -- `_corrigir_texto_enem` tambem mexe
    no espaco em volta da pontuacao --, cru e normalizado casam nas 2.235
    perguntas, sem nenhuma colisao entre perguntas diferentes. So tirar o
    acento ainda deixaria 53 de fora.
    """
    return re.sub(r"[^a-z0-9]", "", chave_busca(str(pergunta or "")))


def _fallback(area: str, dificuldade: str, historico: list[str] | None = None) -> dict:
    """Retorna uma questão offline para a área especificada."""
    banco = list(_FALLBACK_POR_AREA.get(area, [])) + _fallback_autoral_por_area(area)
    if not banco:
        # Usa qualquer área disponível se a solicitada não tiver fallback
        banco = list(random.choice(list(_FALLBACK_POR_AREA.values())))
    if area == "Matematica e suas Tecnologias":
        banco = list(banco) + _fallback_matematica_variantes()

    ja_vistas = {_chave_repeticao(item) for item in (historico or [])}
    opcoes = [item for item in banco if _chave_repeticao(item.get("pergunta", "")) not in ja_vistas]
    q = _normalizar_textos_questao(dict(random.choice(opcoes or banco)))
    q["dificuldade"] = dificuldade
    q["matriz_enem"] = _rotulo_da_matriz(q.get("matriz_enem", ""), area)
    q["_origem"] = "offline"
    return _embaralhar_alternativas_questao(q)


# ── API pública ───────────────────────────────────────────────────────────────

def gerar_questao_enem(area_bncc: str, dificuldade: str = "Medio") -> dict:
    """
    Gera uma questão ENEM para a área e dificuldade indicadas.

    Tenta IA até 3 vezes com deduplicação de pergunta por session_state.
    Usa fallback offline se todas as tentativas falharem.
    """
    chave = (area_bncc, dificuldade)
    historico = _get_historico_sessao(chave)
    # A mesma chave dos dois lados: ver _chave_repeticao.
    ja_vistas = {_chave_repeticao(item) for item in historico}
    questao = None
    provedores_rejeitados: set[str] = set()
    inicio_ia = time.monotonic()
    orcamento_ia = _orcamento_ia_enem_segundos()

    for _ in range(5):
        restante_ia = orcamento_ia - (time.monotonic() - inicio_ia)
        if restante_ia < 4.0:
            print("[IA] ENEM atingiu limite de tempo. usando offline...")
            break
        candidato = _gerar_via_ia(
            area_bncc, dificuldade, pular_provedores=provedores_rejeitados, deadline_seconds=restante_ia
        )
        if candidato is None:
            provedor = obter_ultimo_provedor_ia()
            if provedor:
                provedores_rejeitados.add(str(provedor).strip().lower())
                continue
            break
        assinatura = str(candidato.get("pergunta", "")).strip()
        questao = candidato
        if assinatura and _chave_repeticao(assinatura) not in ja_vistas:
            _set_historico_sessao(chave, (historico + [assinatura])[-8:])
            return candidato
        provedor = str(candidato.get("_provedor_ia") or obter_ultimo_provedor_ia() or "").strip().lower()
        if provedor:
            provedores_rejeitados.add(provedor)
            print(f"[IA] {provedor} rejeitado no enem: repetido")

    # Se IA funcionou mas só gerou repetições, usa o último candidato
    if questao is not None:
        assinatura = str(questao.get("pergunta", "")).strip()
        if assinatura:
            _set_historico_sessao(chave, (historico + [assinatura])[-8:])
        return questao

    # Fallback offline
    fallback = _fallback(area_bncc, dificuldade, historico)
    assinatura = str(fallback.get("pergunta", "")).strip()
    if assinatura and _chave_repeticao(assinatura) not in ja_vistas:
        _set_historico_sessao(chave, (historico + [assinatura])[-8:])
    return fallback


def sortear_areas(n: int = 4) -> list[str]:
    """Retorna n áreas sorteadas aleatoriamente (sem repetição)."""
    todas = list(AREAS_ENEM.keys())
    return random.sample(todas, min(n, len(todas)))


def montar_sequencia_questoes(
    areas_selecionadas: list[str],
    total_questoes: int,
    dificuldade: str = "Medio",
) -> list[tuple[str, str]]:
    """
    Distribui as questões entre as áreas selecionadas de forma equilibrada.

    Retorna lista de tuplas (area, dificuldade) para geração lazy.
    """
    if not areas_selecionadas:
        areas_selecionadas = list(AREAS_ENEM.keys())

    sequencia: list[tuple[str, str]] = []
    for i in range(total_questoes):
        area = areas_selecionadas[i % len(areas_selecionadas)]
        sequencia.append((area, dificuldade))

    random.shuffle(sequencia)
    return sequencia
