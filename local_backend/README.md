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

## API

### Открытие ячейки

`POST /api/cells/{cell_number}/open` — отправляет команду на открытие одной
ячейки. Валидный диапазон номеров: **1..27**.

Пример запроса:

```bash
curl -X POST http://127.0.0.1:8000/api/cells/5/open
```

Успешный ответ (`200 OK`):

```json
{
  "success": true,
  "cell_number": 5,
  "message": "Команда на открытие ячейки №5 отправлена"
}
```

Номер вне диапазона (`400 Bad Request`):

```json
{
  "success": false,
  "message": "Номер ячейки должен быть от 1 до 27"
}
```

Контроллер недоступен (`503 Service Unavailable`):

```json
{
  "success": false,
  "cell_number": 5,
  "message": "Контроллер ячеек недоступен"
}
```

Переключение между реальным контроллером и моком задаётся в
`app/core/config.py` через флаг `use_mock_hardware`.

## Структура

```
local_backend/
  app/
    main.py                FastAPI application factory
    api/
      health_router.py     GET  /api/health
      cells_router.py      POST /api/cells/{cell_number}/open
    services/
      cell_service.py      business logic (validation + dispatch)
    hardware/
      hardware_client.py   facade over postamat_device (+ mock)
    schemas/
      cell_schemas.py      Pydantic models for /api/cells
    core/
      config.py            AppConfig (service name, api prefix, mock toggle)
  requirements.txt
  README.md
```

## Что НЕ входит в этот этап

- SQLite / любая БД
- авторизация
- взаимодействие с внешним сервером
- WebSocket
