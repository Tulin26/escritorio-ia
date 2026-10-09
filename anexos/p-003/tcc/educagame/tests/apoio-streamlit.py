"""Um Streamlit de mentira que ANOTA o que a tela pediu para desenhar.

Por que isto existe: as telas do Streamlit nao devolvem valor nenhum -- elas
desenham. Nao da para fotografar entrada -> saida como se fez com
invocar_enigma e invocar_enigma_laboratorio, e foi por isso que a
refatoracao delas ficou parada: sem rede, extrair funcao seria apostar.

A saida de uma tela e a SEQUENCIA de chamadas que ela faz ao Streamlit.
Este modulo grava essa sequencia. Com ela, vale a mesma receita das outras
duas: fotografar antes, refatorar, conferir que a fotografia bate.

Uso:

    with StreamlitFalso() as fake:
        renderizar_tela_rpg(...)
    fake.roteiro()   # ['markdown: ...', 'button: Continuar -> False', ...]

O `st.rerun()` e o `st.stop()` interrompem a execucao de verdade no
Streamlit; aqui levantam ParouAqui, que o gerenciador de contexto captura --
assim o roteiro termina no mesmo ponto em que terminaria na tela.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any


class ParouAqui(BaseException):
    """st.rerun() ou st.stop(): a execucao da tela termina aqui.

    MELHORIA: herdava de Exception, e o Streamlit de verdade nao faz assim --
    RerunException e StopException descendem de BaseException, justamente para
    NAO serem engolidas pelos `except Exception` espalhados pelas telas.

    A diferenca aparecia na fotografia. Este trecho existia em admin_st.py
    (ate a exclusao passar a olhar o retorno da gravacao):

        try:
            excluir_escola(...)
            st.success("Escola excluida com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir escola: {e}")

    Com ParouAqui(Exception), o duble registrava um "Erro ao excluir escola:
    rerun" logo depois do sucesso -- uma linha que a tela de verdade nunca
    produz. Rede que inventa comportamento e pior que rede nenhuma: ela
    trancaria a fotografia num defeito inexistente.
    """


class _EstadoDeSessao(dict):
    """st.session_state aceita ["chave"] e .chave -- os dois."""

    def __getattr__(self, nome: str) -> Any:
        try:
            return self[nome]
        except KeyError as erro:
            raise AttributeError(nome) from erro

    def __setattr__(self, nome: str, valor: Any) -> None:
        self[nome] = valor

    # MELHORIA: `del st.session_state.confirmar_exclusao` (aventura do RPG)
    # levantava AttributeError aqui -- o valor mora na chave, nao em __dict__.
    def __delattr__(self, nome: str) -> None:
        try:
            del self[nome]
        except KeyError as erro:
            raise AttributeError(nome) from erro


class _Bloco:
    """columns / container / expander / spinner: servem de context manager."""

    def __init__(self, fake: "StreamlitFalso", rotulo: str):
        self._fake = fake
        self._rotulo = rotulo

    def __enter__(self):
        self._fake._anotar(f"abre {self._rotulo}")
        return self

    def __exit__(self, *_):
        self._fake._anotar(f"fecha {self._rotulo}")
        return False

    # dentro de uma coluna a tela chama col.markdown(...), col.button(...)
    def __getattr__(self, nome: str):
        return getattr(self._fake, nome)


class StreamlitFalso:
    """Substitui o modulo `streamlit` e grava tudo que a tela pediu.

    respostas: o que cada widget deve devolver, por rotulo. Widget sem
    resposta combinada devolve o padrao inocuo (False para botao, a primeira
    opcao para selectbox), que e o caminho "o usuario nao clicou em nada".
    """

    def __init__(self, respostas: dict[str, Any] | None = None,
                 sessao: dict[str, Any] | None = None,
                 parametros: dict[str, Any] | None = None):
        self.respostas = dict(respostas or {})
        self.session_state = _EstadoDeSessao(sessao or {})
        # MELHORIA: st.query_params caia no __getattr__ generico, que devolve
        # uma FUNCAO de saida -- e a tela faz st.query_params.get(...), entao
        # quebrava por causa da bancada. E dict porque e o que a tela usa
        # dele: .get, .clear e atribuicao por chave.
        self.query_params: dict[str, Any] = dict(parametros or {})
        self._roteiro: list[str] = []
        self._modulos_originais: dict[str, Any] = {}

    # ------------------------------------------------------------ registro

    def _anotar(self, linha: str) -> None:
        self._roteiro.append(linha)

    def roteiro(self) -> list[str]:
        return list(self._roteiro)

    def _resposta(self, rotulo: str, padrao: Any) -> Any:
        return self.respostas.get(rotulo, padrao)

    @staticmethod
    def _resumir(valor: Any, limite: int = 90) -> str:
        texto = " ".join(str(valor or "").split())
        return texto[:limite] + ("..." if len(texto) > limite else "")

    # ------------------------------------------------------------- saida

    def _saida(self, tipo: str):
        def escrever(conteudo: Any = "", *_args, **_kwargs):
            self._anotar(f"{tipo}: {self._resumir(conteudo)}")
        return escrever

    def __getattr__(self, nome: str):
        # qualquer chamada de saida que nao foi prevista vira uma linha do
        # roteiro em vez de AttributeError -- assim a tela nunca quebra por
        # causa da bancada, e a chamada nova aparece na fotografia.
        if nome.startswith("_"):
            raise AttributeError(nome)
        return self._saida(nome)

    markdown = property(lambda self: self._saida("markdown"))
    write = property(lambda self: self._saida("write"))
    info = property(lambda self: self._saida("info"))
    warning = property(lambda self: self._saida("warning"))
    error = property(lambda self: self._saida("error"))
    success = property(lambda self: self._saida("success"))
    caption = property(lambda self: self._saida("caption"))
    latex = property(lambda self: self._saida("latex"))
    subheader = property(lambda self: self._saida("subheader"))
    header = property(lambda self: self._saida("header"))
    title = property(lambda self: self._saida("title"))
    divider = property(lambda self: self._saida("divider"))

    def balloons(self, *_args, **_kwargs):
        self._anotar("balloons")

    # ------------------------------------------------------------ widgets

    def button(self, rotulo: str = "", *_args, **kwargs) -> bool:
        valor = bool(self._resposta(kwargs.get("key") or rotulo, False))
        self._anotar(f"button: {self._resumir(rotulo)} -> {valor}")
        return valor

    def download_button(self, rotulo: str = "", *_args, **kwargs) -> bool:
        valor = bool(self._resposta(kwargs.get("key") or rotulo, False))
        self._anotar(f"download_button: {self._resumir(rotulo)} -> {valor}")
        return valor

    @staticmethod
    def _opcoes_de(posicional, kwargs) -> list:
        # o Streamlit aceita as opcoes de dois jeitos, e a tela usa os dois:
        # st.selectbox("rotulo", lista) e st.selectbox("rotulo", options=lista)
        bruto = posicional if posicional else kwargs.get("options")
        return list(bruto or [])

    def selectbox(self, rotulo: str = "", opcoes=(), *_args, **kwargs):
        opcoes = self._opcoes_de(opcoes, kwargs)
        escolhido = self._resposta(kwargs.get("key") or rotulo, opcoes[0] if opcoes else None)
        self._anotar(
            f"selectbox: {self._resumir(rotulo)} ({len(opcoes)} opcoes) -> {self._resumir(escolhido, 50)}"
        )
        return escolhido

    def select_slider(self, rotulo: str = "", opcoes=(), *_args, **kwargs):
        # MELHORIA: caia no __getattr__ generico e devolvia None. A tela de
        # treino usa o valor logo em seguida (dificuldade e numero de
        # questoes), entao o None viajava para dentro do estado da sessao.
        # O padrao aqui e o `value=`, e nao a primeira opcao: e assim que o
        # Streamlit se comporta, e as telas contam com isso.
        opcoes = self._opcoes_de(opcoes, kwargs)
        padrao = kwargs.get("value", opcoes[0] if opcoes else None)
        escolhido = self._resposta(kwargs.get("key") or rotulo, padrao)
        self._anotar(f"select_slider: {self._resumir(rotulo)} -> {self._resumir(escolhido, 40)}")
        return escolhido

    def radio(self, rotulo: str = "", opcoes=(), *_args, **kwargs):
        opcoes = self._opcoes_de(opcoes, kwargs)
        escolhido = self._resposta(kwargs.get("key") or rotulo, opcoes[0] if opcoes else None)
        self._anotar(f"radio: {self._resumir(rotulo)} -> {self._resumir(escolhido, 50)}")
        return escolhido

    def text_input(self, rotulo: str = "", valor: str = "", *_args, **kwargs) -> str:
        # MELHORIA: o padrao so era lido da posicao. A tela chama
        # st.text_input("Slug", value=escola["slug"]) -- por KEYWORD --, entao
        # o campo ja preenchido voltava vazio, e o roteiro registrava a tela
        # reclamando "slug obrigatorio" onde ela na verdade mostra o valor.
        # checkbox e toggle ja faziam kwargs.get("value", ...); este faltou.
        padrao = kwargs.get("value", valor)
        resposta = self._resposta(kwargs.get("key") or rotulo, padrao)
        self._anotar(f"text_input: {self._resumir(rotulo)} -> {self._resumir(resposta, 40)}")
        return resposta

    def text_area(self, rotulo: str = "", valor: str = "", *_args, **kwargs) -> str:
        # MELHORIA: caia no __getattr__ generico e devolvia None. A aventura do
        # RPG le o cenario daqui e o exige preenchido -- com None, toda
        # gravacao pela bancada virava "preencha o cenario".
        padrao = kwargs.get("value", valor)
        resposta = self._resposta(kwargs.get("key") or rotulo, padrao)
        self._anotar(f"text_area: {self._resumir(rotulo)} -> {self._resumir(resposta, 40)}")
        return resposta

    # MELHORIA: estes tres devolvem VALOR que a tela usa em seguida -- cor,
    # marcado/desmarcado, quantidade. Deixar para o fallback generico (que
    # devolve None) faria a tela seguir com None onde espera um valor, e o
    # erro apareceria longe daqui.
    def color_picker(self, rotulo: str = "", valor: str = "#000000", *_args, **kwargs) -> str:
        resposta = self._resposta(kwargs.get("key") or rotulo, valor)
        self._anotar(f"color_picker: {self._resumir(rotulo)} -> {resposta}")
        return resposta

    def checkbox(self, rotulo: str = "", valor: bool = False, *_args, **kwargs) -> bool:
        resposta = bool(self._resposta(kwargs.get("key") or rotulo, kwargs.get("value", valor)))
        self._anotar(f"checkbox: {self._resumir(rotulo)} -> {resposta}")
        return resposta

    def toggle(self, rotulo: str = "", valor: bool = False, *_args, **kwargs) -> bool:
        resposta = bool(self._resposta(kwargs.get("key") or rotulo, kwargs.get("value", valor)))
        self._anotar(f"toggle: {self._resumir(rotulo)} -> {resposta}")
        return resposta

    def number_input(self, rotulo: str = "", *_args, **kwargs):
        padrao = kwargs.get("value", kwargs.get("min_value", 0))
        resposta = self._resposta(kwargs.get("key") or rotulo, padrao)
        self._anotar(f"number_input: {self._resumir(rotulo)} -> {resposta}")
        return resposta

    def dataframe(self, dados=None, *_args, **_kwargs):
        try:
            linhas = len(dados)
        except Exception:  # noqa: BLE001
            linhas = "?"
        self._anotar(f"dataframe: {linhas} linhas")

    # ------------------------------------------------------------- layout

    def tabs(self, titulos, *_args, **_kwargs):
        rotulos = [str(t) for t in (titulos or [])]
        self._anotar("tabs: " + " | ".join(rotulos))
        return [_Bloco(self, f"tab[{r}]") for r in rotulos]

    def columns(self, quantas, *_args, **_kwargs):
        n = quantas if isinstance(quantas, int) else len(list(quantas))
        self._anotar(f"columns: {n}")
        return [_Bloco(self, f"col{i}") for i in range(n)]

    def container(self, *_args, **_kwargs):
        return _Bloco(self, "container")

    def expander(self, rotulo: str = "", *_args, **_kwargs):
        return _Bloco(self, f"expander[{self._resumir(rotulo, 40)}]")

    def spinner(self, texto: str = "", *_args, **_kwargs):
        return _Bloco(self, f"spinner[{self._resumir(texto, 40)}]")

    def form(self, chave: str = "", *_args, **_kwargs):
        return _Bloco(self, f"form[{chave}]")

    def form_submit_button(self, rotulo: str = "", *_args, **kwargs) -> bool:
        valor = bool(self._resposta(kwargs.get("key") or rotulo, False))
        self._anotar(f"form_submit_button: {self._resumir(rotulo)} -> {valor}")
        return valor

    # ------------------------------------------------- controle de fluxo

    def rerun(self, *_args, **_kwargs):
        self._anotar("rerun")
        raise ParouAqui("rerun")

    def stop(self, *_args, **_kwargs):
        self._anotar("stop")
        raise ParouAqui("stop")

    # ------------------------------------------------------ instalacao

    def __enter__(self) -> "StreamlitFalso":
        modulo = ModuleType("streamlit")
        for nome in dir(type(self)):
            if not nome.startswith("__"):
                setattr(modulo, nome, getattr(self, nome))
        modulo.session_state = self.session_state
        # Como o session_state: e atributo de INSTANCIA, entao nao vem pelo
        # dir(type(self)) do laco acima.
        modulo.query_params = self.query_params
        # MELHORIA: o __getattr__ da INSTANCIA transforma chamada nao prevista
        # numa linha do roteiro, em vez de AttributeError -- mas o dublê e
        # instalado como MODULO, e a copia acima so leva o que existe em
        # dir(type(self)). Na pratica o fallback nunca valia: a primeira tela
        # a usar um widget novo (foi o color_picker) quebrava por causa da
        # bancada, nao por causa do codigo em teste. PEP 562: modulo tambem
        # aceita __getattr__.
        modulo.__getattr__ = lambda nome: getattr(self, nome)
        self._modulos_originais["streamlit"] = sys.modules.get("streamlit")
        sys.modules["streamlit"] = modulo
        self._modulo = modulo
        return self

    def __exit__(self, tipo, valor, _tb):
        original = self._modulos_originais.get("streamlit")
        if original is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = original
        # ParouAqui e o fim normal de uma tela, nao um erro
        return isinstance(valor, ParouAqui)
