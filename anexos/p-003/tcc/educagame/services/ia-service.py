from __future__ import annotations

from services.ia.providers import (
    gerar_json_ia,
    obter_ultimo_erro_ia,
    obter_ultimo_provedor_ia,
)
from services.ia.questoes import embaralhar_opcoes_questao as _embaralhar_opcoes_questao
from services.ia.validacao import _questao_fisica_quimica_conceitual, _resultado_exatas_conflitante
# MELHORIA: invocar_enigma/invocar_enigma_laboratorio e os helpers abaixo
# vivem de fato em services.ia.enigma; ficam re-exportados aqui so por
# compatibilidade com quem ja importa de services.ia_service (rpg_service,
# calculo_service, rotas Flask, testes). Nao mover a implementacao de volta
# pra ca: isso reintroduziria o import circular que existia antes (enigma.py
# chamando de volta pra ia_service.py via getattr dinamico).
from services.ia.enigma import (
    _exemplo_curto_nao_exatas,
    _explicacao_direta_nao_exatas,
    _montar_questao_offline,
    _questao_resposta_composta_inconsistente,
    _resolver_tema_questao,
    invocar_enigma,
    invocar_enigma_laboratorio,
)


# gerar_json_ia mora em services/ia/providers.py, ao lado do chamar_ia que
# ele repassa. Fica re-exportado aqui porque rpg_service e enem_service o
# importam deste modulo.
