# local_backend

Локальный backend постамата на FastAPI. На этом этапе — только каркас и health-check.

## Установка

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Запуск

Из каталога `local_backend/`:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Проверка

```bash
curl http://127.0.0.1:8000/api/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "local_backend"
}
```

Документация Swagger UI: <http://127.0.0.1:8000/docs>.

## Структура

```
local_backend/
  app/
    main.py                FastAPI application factory
    api/
      health_router.py     GET /api/health
      cells_router.py      placeholder for /api/cells
    services/
      cell_service.py      placeholder, business logic
    hardware/
      hardware_client.py   placeholder, hardware facade
    schemas/
      cell_schemas.py      placeholder, Pydantic models
    core/
      config.py            AppConfig (service name, api prefix)
  requirements.txt
  README.md
```

## Что НЕ входит в этот этап

- SQLite / любая БД
- авторизация
- взаимодействие с внешним сервером
- WebSocket
- реальная работа с железом (`hardware/` и `services/` — пока заглушки)
