# Notas Codex

## Estado da Branch

- Aplicacao principal: `flask_app.py` (Flask, no Render)
- Frontend alternativo: `app.py` (Streamlit, no Streamlit Cloud) -- os dois
  compartilham `core/`, `services/` e `repositories/`
- Dependencias: `requirements_flask.txt` (Flask) e `requirements.txt`
  (Streamlit); as comuns ficam em `requirements_base.txt`
- Dependencias de teste: `requirements-dev.txt`

## Pontos de Atencao

- Chaves e configuracoes sensiveis devem ficar no `.env`.
- Os servicos de IA usam fallback offline quando a resposta externa falha ou vem incoerente.
- O runtime compartilhado em `core/runtime_context.py` evita acoplar repositorios e servicos a uma interface web especifica.
