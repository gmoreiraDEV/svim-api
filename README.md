# SVIM API

API em FastAPI para criação de threads, execução do agente LLM via LangGraph e gestão de user profiles.

## ✅ Requisitos

- Python 3.11+ (testado localmente com 3.13)
- Postgres

## 🚀 Setup local

1) Instale dependências:
```
pip install -r requirements.txt
```

2) Configure o `.env`:
```
ENV=development
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres

OPENROUTER_API_KEY=sk-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MAX_TOKENS=2048

DEFAULT_MODEL_NAME=google/gemini-2.5-flash
DEFAULT_USE_TAVILY=false

# opcional
TAVILY_API_KEY=
DEBUG_AGENT_LOGS=false
```

3) Rode a API:
```
uvicorn app.main:app --reload
```

## 🗃️ Migrações

As migrações SQL ficam em `app/db/migrations` e são executadas no startup da aplicação.

## 🔌 Rotas principais

### Threads

- `POST /threads`  
Cria uma thread e retorna `thread_id`.

- `POST /threads/search`  
Lista threads recentes. Payload:
```json
{ "limit": 50 }
```

- `GET /threads/{thread_id}`  
Retorna histórico da thread.

- `POST /threads/{thread_id}/runs/wait`  
Executa o agente e responde quando finalizar.

- `POST /threads/{thread_id}/runs/stream`  
Executa o agente via SSE.

Payload para as rotas de run:
```json
{
  "input": {
    "messages": [
      { "role": "user", "content": "Olá!" }
    ]
  },
  "config": {
    "configurable": {
      "model_name": "google/gemini-2.5-flash",
      "use_tavily": false
    }
  }
}
```

### User Profiles

- `POST /user-profiles`  
Cria/atualiza um perfil (upsert).
```json
{
  "customer_profile": 123,
  "name": "João",
  "phone": "+5511999999999"
}
```

- `GET /user-profiles/{customer_profile}`  
Lê um perfil.

- `PATCH /user-profiles/{customer_profile}/thread`  
Vincula uma thread ao perfil.
```json
{ "thread_id": "45d67d68-31f5-4a11-b437-9610dc6a00b4" }
```

- `GET /user-profiles/{customer_profile}/threads?limit=50`  
Lista threads associadas a um perfil.

## ⚙️ Deploy

O `railway.json` já contém o comando de start para deploy via Railway:
```
uvicorn app.main:app --bind "[::]:$PORT"
```
