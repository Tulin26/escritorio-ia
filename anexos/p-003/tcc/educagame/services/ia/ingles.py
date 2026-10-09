from __future__ import annotations

import random

from services.ia.base import _passo


def resposta_ingles_offline(tema_final: str) -> dict:
    tema_lower = str(tema_final or "").lower()
    if "reported" in tema_lower or "indirect" in tema_lower:
        dados = {
            "pergunta": "In reported speech, which change is usually needed when direct speech moves into the past?",
            "pergunta_traducao": "No discurso indireto, qual mudanca costuma ser necessaria quando a fala direta vai para o passado?",
            "opcoes": [
                "Adjust verb tense and pronouns to match the new context",
                "Keep every word exactly as it was in direct speech",
                "Remove all time expressions from the sentence",
                "Change every sentence into a question",
            ],
            "opcoes_traducao": [
                "Ajustar o tempo verbal e os pronomes ao novo contexto",
                "Manter todas as palavras exatamente como estavam na fala direta",
                "Remover todas as expressoes de tempo da frase",
                "Transformar toda frase em pergunta",
            ],
            "resultado": "Reported speech usually requires tense, pronoun, and time-expression changes.",
            "resultado_traducao": "O discurso indireto geralmente exige mudancas de tempo verbal, pronomes e expressoes de tempo.",
        }
    elif "idiom" in tema_lower:
        dados = {
            "pergunta": "What should you do first when an English idiom does not make literal sense?",
            "pergunta_traducao": "O que voce deve fazer primeiro quando uma expressao idiomatica em ingles nao faz sentido literal?",
            "opcoes": [
                "Use the context to infer the figurative meaning",
                "Translate each word separately and stop there",
                "Ignore the sentence before and after the idiom",
                "Choose the option with the longest explanation",
            ],
            "opcoes_traducao": [
                "Usar o contexto para inferir o sentido figurado",
                "Traduzir cada palavra separadamente e parar nisso",
                "Ignorar a frase anterior e posterior a expressao",
                "Escolher a alternativa com a explicacao mais longa",
            ],
            "resultado": "Idioms are understood by context and figurative meaning, not by literal translation.",
            "resultado_traducao": "Expressoes idiomaticas sao entendidas pelo contexto e pelo sentido figurado, nao pela traducao literal.",
        }
    else:
        dados = random.choice([
            {
                "pergunta": f"Which strategy best helps you understand a text about {tema_final} in English?",
                "pergunta_traducao": f"Qual estrategia mais ajuda a entender um texto sobre {tema_final} em Ingles?",
                "opcoes": [
                    "Identify familiar words and use context clues",
                    "Translate word by word without checking the overall meaning",
                    "Ignore the title and visual clues",
                    "Answer before reading all the options",
                ],
                "opcoes_traducao": [
                    "Identificar palavras conhecidas e usar pistas de contexto",
                    "Traduzir palavra por palavra sem verificar o sentido geral",
                    "Ignorar o titulo e as pistas visuais",
                    "Responder antes de ler todas as alternativas",
                ],
                "resultado": "The best strategy is to combine vocabulary knowledge with context clues.",
                "resultado_traducao": "A melhor estrategia e combinar vocabulario conhecido com pistas de contexto.",
            },
            {
                "pergunta": f"When reading a short text about {tema_final}, what should you check before choosing an answer?",
                "pergunta_traducao": f"Ao ler um texto curto sobre {tema_final}, o que voce deve verificar antes de escolher uma resposta?",
                "opcoes": [
                    "The main idea, key words, and the command of the question",
                    "Only the first word of each option",
                    "The option that looks most similar to Portuguese",
                    "The answer before reading the text",
                ],
                "opcoes_traducao": [
                    "A ideia principal, palavras-chave e o comando da pergunta",
                    "Apenas a primeira palavra de cada alternativa",
                    "A alternativa que parece mais parecida com portugues",
                    "A resposta antes de ler o texto",
                ],
                "resultado": "Good reading in English connects the command, key words, and main idea.",
                "resultado_traducao": "Uma boa leitura em Ingles conecta o comando, as palavras-chave e a ideia principal.",
            },
        ])

    return {
        "enigma": f"In the temple mist, a hidden clue about {tema_final} waits between the lines.",
        "enigma_traducao": f"Na nevoa do templo, uma pista oculta sobre {tema_final} espera nas entrelinhas.",
        "pergunta": dados["pergunta"],
        "pergunta_traducao": dados["pergunta_traducao"],
        "opcoes": dados["opcoes"],
        "opcoes_traducao": dados["opcoes_traducao"],
        "correta": 0,
        "explicacao": [
            {"tipo": "bold", "conteudo": "Reading in English"},
            {"tipo": "texto", "conteudo": "Read the task carefully and look for the words that control the meaning."},
            {"tipo": "texto", "conteudo": "Then compare the options with the context instead of relying on isolated translation."},
            {"tipo": "resultado", "conteudo": dados["resultado"]},
        ],
        "explicacao_traducao": [
            {"tipo": "bold", "conteudo": "Leitura em Ingles"},
            {"tipo": "texto", "conteudo": "Leia a tarefa com atencao e procure as palavras que controlam o sentido."},
            {"tipo": "texto", "conteudo": "Depois compare as alternativas com o contexto, em vez de depender de traducao isolada."},
            {"tipo": "resultado", "conteudo": dados["resultado_traducao"]},
        ],
        "passos_resolucao": [
            _passo("1st Step: identify the task", "Read the prompt and decide whether it asks for grammar, vocabulary, or interpretation."),
            _passo("2nd Step: use context", "Look at the words around the key expression and eliminate options that do not fit."),
            _passo("Final Answer", dados["resultado"], final=True),
        ],
        "passos_resolucao_traducao": [
            _passo("1o Passo: identificar a tarefa", "Leia o enunciado e perceba se ele pede gramatica, vocabulario ou interpretacao."),
            _passo("2o Passo: usar contexto", "Observe as palavras ao redor da expressao principal e elimine alternativas que nao combinam."),
            _passo("Resultado Final", dados["resultado_traducao"], final=True),
        ],
    }
