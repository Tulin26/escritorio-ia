# EducaGame Flask

Aplicacao Flask principal do EducaGame IA.

## Rodar local

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_flask.txt
.\.venv\Scripts\python.exe flask_app.py
```

Abra:

```text
http://localhost:5000
```

Nao ha mais atalho para abrir uma escola pelo endereco. O slug voltou a ser o
codigo de entrada: escolha a escola na lista e digite o codigo dela. As rotas
antigas (`/e/<slug>` e `?escola=<slug>`) levam a lista, sem escolher nada.

## Escopo

- Home com selecao de escola e aluno.
- Oraculo, treino, laboratorio, ENEM, boss rush, escape room, RPG, progresso,
  professor e guildas.
- Registro de logs pedagogicos e ranking.
- Fallback offline para manter a plataforma funcionando quando a IA externa falhar.
