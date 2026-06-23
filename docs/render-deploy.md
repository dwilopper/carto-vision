# Деплой CartoVision на Render

## Что уже подготовлено в проекте

Для деплоя на `Render` в проект добавлены:

- [render.yaml](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/render.yaml)
- [requirements.txt](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/requirements.txt)
- [app/config.py](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/app/config.py)

Логика настроена так:

- приложение запускается как `FastAPI`-web service;
- Render ставит зависимости из `requirements.txt`;
- база данных и пользовательские файлы сохраняются на `Persistent Disk`;
- при первом запуске приложение само создаст базу и заполнит демо-данные.

## Почему нужен Persistent Disk

В `CartoVision` есть:

- `SQLite` база данных;
- загрузка пользовательских файлов;
- экспорт `PNG/PDF/CSV/GeoJSON`.

Если не использовать постоянный диск, эти данные могут исчезать после redeploy или перезапуска контейнера.  
Поэтому в [render.yaml](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/render.yaml) уже задан диск:

- `mountPath: /var/data`
- `CARTOVISION_STORAGE_DIR=/var/data/cartovision`
- `CARTOVISION_DB_PATH=/var/data/cartovision/app_state.sqlite3`

## Что загрузить в GitHub

В репозиторий нужно отправить проект без локальной базы и без временных файлов.

Главное:

- папку `app`
- папку `data`
- папку `static`
- папку `templates`
- папку `vendor`
- файл `run_app.py`
- файл `requirements.txt`
- файл `render.yaml`
- файл `.gitignore`

## Пошаговый деплой

### 1. Загрузи проект в GitHub

Если репозиторий еще не создан:

```powershell
git init
git add .
git commit -m "Prepare CartoVision for Render"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

### 2. Создай сервис в Render

1. Зайди в `Render Dashboard`.
2. Нажми `New +`.
3. Выбери `Blueprint`.
4. Подключи свой GitHub-репозиторий.
5. Render увидит файл `render.yaml` и сам предложит создать сервис.
6. Подтверди создание.

Важно: из-за `Persistent Disk` этот деплой нужно запускать не на `free`, а на платном web service.  
В конфиге уже выставлен `plan: starter`, потому что диски на Render доступны только для платных web services.

## Что произойдет дальше

Render выполнит:

- `pip install -r requirements.txt`
- запуск команды:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

После сборки приложение будет доступно по публичному URL Render.

## Логин после деплоя

После первого запуска можно войти под встроенными учетками:

- `demo / demo123`
- `admin / admin123`

## Что делать, если нужен свой пароль

После первого входа лучше:

- создать свои учетные записи в коде или базе;
- либо заранее поменять демо-пароли перед публикацией.

## Если Render попросит выбрать диск вручную

Обычно при `Blueprint` он создается по `render.yaml`, но если платформа попросит проверить настройки, убедись, что диск:

- смонтирован в `/var/data`
- имеет размер `1 GB`

## Полезные официальные документы Render

- [Deploy a FastAPI app](https://render.com/docs/deploy-fastapi)
- [Persistent Disks](https://render.com/docs/disks)
- [Blueprint Spec](https://render.com/docs/blueprint-spec)
