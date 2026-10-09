"""O tema de estudo aparece com acento na tela, e continua chave por baixo.

Visto em 29/09/2026 na aba "Metas e foco" do professor: o seletor de tema
mostrava "equacoes do 2o grau e formula de Bhaskara". O tema é CHAVE
(`core/config.py::TEMAS_RPG`) -- vai assim para o prompt da IA e para a
tabela `foco_do_aluno` --, e as telas novas o imprimiam cru.

A regra do projeto, a mesma de `MATERIAS_COM_ACENTO` e `LABEL_DIFICULDADE`:
**a chave fica como está e a tela ganha um rótulo.** O rótulo aqui é o
próprio dicionário de acentos (`aplicar_acentos_pt`), que já sabia converter
284 dos 286 temas -- inclusive "2o" em "2º". Faltavam duas palavras, medidas
uma a uma nos 286: "avancada" (de "ecologia avancada") e o "pré" de
"pré-história".

Medido o alcance das duas no corpus real antes de ligar: 700 textos dos
bancos mudam, TODOS só em acento -- são moldes do RPG e do Escape Room com o
tema injetado, que chegavam ao aluno como "pre-história". Nenhum texto da IA.

O limite deste arquivo, dito de frente: nenhum teste aqui descobre uma
palavra que o dicionário não conhece -- isso pede um corretor ortográfico. Os
dois buracos acima foram achados lendo as 257 palavras sem acento que sobram
nos rótulos. Quem acrescentar tema novo em `TEMAS_RPG` precisa olhar o rótulo
dele uma vez.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import TEMAS_RPG
from core.text_cleanup import _PALAVRAS_PT, aplicar_acentos_pt

TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"


@pytest.mark.parametrize(
    ("chave", "rotulo"),
    [
        # O caso do print.
        ("equacoes do 2o grau e formula de Bhaskara", "equações do 2º grau e fórmula de Bhaskara"),
        # As duas palavras que faltavam no dicionário.
        ("ecologia avancada", "ecologia avançada"),
        ("pre-historia", "pré-história"),
        ("Pre-historia", "Pré-história"),
        # E o que já funcionava continua funcionando.
        ("Revolucao Francesa", "Revolução Francesa"),
        ("progressao aritmetica (PA)", "progressão aritmética (PA)"),
    ],
)
def test_o_rotulo_do_tema_tem_acento(chave, rotulo):
    assert aplicar_acentos_pt(chave) == rotulo


def test_o_filtro_esta_registrado_no_app(client):
    from flask import render_template_string

    with client.application.app_context():
        saida = render_template_string("{{ t|tema_label }}", t="equacoes do 2o grau e formula de Bhaskara")

    assert saida == "equações do 2º grau e fórmula de Bhaskara"


def test_nenhuma_palavra_que_o_dicionario_conhece_sobra_sem_acento_nos_temas():
    # Pega o dicionário CONHECENDO a palavra e mesmo assim deixando passar
    # (limite de palavra, ordem de troca, regra de verbo). Não pega palavra
    # que o dicionário não conhece -- ver o docstring.
    temas = {tema for etapas in TEMAS_RPG.values() for lista in etapas.values() for tema in lista}
    sobras = {}
    for tema in temas:
        rotulo = aplicar_acentos_pt(tema).lower()
        restantes = [
            palavra for palavra in _PALAVRAS_PT
            if " " not in palavra and f" {palavra} " in f" {rotulo.replace(',', ' ').replace('(', ' ')} "
        ]
        if restantes:
            sobras[tema] = restantes

    assert sobras == {}, f"temas com palavra conhecida ainda sem acento: {sobras}"


# --------------------------------------------------------------------------
# Nas telas: o TEXTO ganha rótulo, o VALUE continua chave


def test_o_seletor_do_professor_mostra_rotulo_e_envia_chave():
    texto = (TEMPLATES / "professor.html").read_text(encoding="utf-8")

    # O value vai para salvar_foco e dali para o banco e para o prompt:
    # acentuá-lo gravaria um tema que o gerador não sorteia nunca.
    assert '<option value="{{ opcao.materia }}|{{ tema }}">{{ tema|tema_label }}</option>' in texto


@pytest.mark.parametrize(
    ("template", "trecho"),
    [
        ("professor.html", "{{ foco.materia|materia_label }}: {{ foco.tema|tema_label }}</span>"),
        ("professor.html", "<strong>{{ foco.materia|materia_label }}:</strong> {{ foco.tema|tema_label }}"),
        ("progresso.html", "<strong>{{ foco.materia|materia_label }}:</strong> {{ foco.tema|tema_label }}"),
    ],
)
def test_todo_lugar_que_mostra_o_foco_usa_o_rotulo(template, trecho):
    assert trecho in (TEMPLATES / template).read_text(encoding="utf-8")


def test_o_botao_de_treinar_manda_o_tema_cru_para_o_oraculo():
    # O botão "Treinar este tema no Oráculo" posta o tema para a rota do
    # Oráculo, que o põe no prompt. Tem de ser a chave, igual à lista do
    # gerador.
    texto = (TEMPLATES / "progresso.html").read_text(encoding="utf-8")

    assert '<input type="hidden" name="tema" value="{{ foco.tema }}">' in texto
    assert 'value="{{ foco.tema|tema_label }}"' not in texto


def test_o_texto_de_ajuda_do_foco_nao_mostra_hifen_duplo():
    # "--" é travessão de comentário de código; na tela é "—".
    texto = (TEMPLATES / "professor.html").read_text(encoding="utf-8")
    inicio = texto.index("Foco de estudo do aluno")
    trecho = texto[inicio:inicio + 600]

    assert " -- " not in trecho
    assert "Oráculo — o app continua" in trecho
