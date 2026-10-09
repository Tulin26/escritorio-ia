from __future__ import annotations

_RELATORIOS = {
    "gerar_pdf_boss_rush": ("services.relatorios.pdf_boss_rush", "gerar_pdf_boss_rush"),
    "gerar_pdf_escape_room": ("services.relatorios.pdf_escape_room", "gerar_pdf_escape_room"),
    "gerar_pdf_enem": ("services.relatorios.pdf_enem", "gerar_pdf_enem"),
    "gerar_pdf_guildas": ("services.relatorios.pdf_guildas", "gerar_pdf_guildas"),
    "gerar_pdf_revisao": ("services.relatorios.pdf_revisao", "gerar_pdf_revisao"),
    "gerar_pdf_rpg": ("services.relatorios.pdf_rpg", "gerar_pdf_rpg"),
    "gerar_pdf_relatorio_turma": ("services.relatorios.pdf_turma", "gerar_pdf_relatorio_turma"),
}

__all__ = list(_RELATORIOS)


def __getattr__(name: str):
    if name not in _RELATORIOS:
        raise AttributeError(name)
    modulo_nome, funcao_nome = _RELATORIOS[name]

    def _lazy(*args, **kwargs):
        from importlib import import_module

        funcao = getattr(import_module(modulo_nome), funcao_nome)
        globals()[name] = funcao
        return funcao(*args, **kwargs)

    _lazy.__name__ = name
    _lazy.__doc__ = f"Lazy loader for {modulo_nome}.{funcao_nome}."
    globals()[name] = _lazy
    return _lazy
