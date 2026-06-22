# CartoVision

Веб-приложение для автоматизированной генерации персонализированных картограмм на основе статистических данных.

## Что умеет приложение

- загружает CSV и Excel-файлы;
- подключает подготовленные демо-источники данных;
- проверяет структуру набора данных;
- очищает данные, удаляет дубликаты и агрегирует записи по территориям;
- поддерживает нормализацию значений;
- строит картограммы по трем методам классификации:
  `равные интервалы`, `квантили`, `естественные разрывы (Jenks)`;
- отображает интерактивную карту на `Leaflet`;
- сохраняет пользовательские сессии;
- экспортирует результаты в `PNG`, `PDF`, `CSV`, `GeoJSON`;
- позволяет администратору добавлять новые источники и GeoJSON-слои.

## Технологический стек

- `Python`
- `FastAPI`
- `SQLite`
- `pandas`
- `Leaflet`
- `Jinja2`
- `Pillow`
- `ReportLab`

## Быстрый запуск

### Вариант 1. Через готовый скрипт

```powershell
.\start_app.ps1
```

После запуска приложение будет доступно по адресу:

`http://127.0.0.1:8000`

### Вариант 2. Напрямую через Python

```powershell
C:\Users\свекла\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run_app.py
```

## Деплой на Render

Для деплоя на `Render` в проект уже добавлены:

- [render.yaml](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/render.yaml)
- [requirements.txt](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/requirements.txt)
- [Инструкция по деплою](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/render-deploy.md)

На Render нужно создавать именно `Blueprint`, а не GitHub Pages, потому что приложению требуется `FastAPI`, `SQLite` и постоянный диск для базы и загрузок.

## Демо-аккаунты

- пользователь:
  `demo / demo123`
- администратор:
  `admin / admin123`

## Сценарий демонстрации на защите

1. Войти под `demo`.
2. Открыть раздел источников данных.
3. Загрузить в рабочую область набор `Socioeconomic Districts 2022-2024`.
4. Выбрать:
   `territory_id`, `territory_name`, показатель `grdp_trln_rub`, фильтр `year = 2024`.
5. Задать метод классификации `Квантили` и палитру.
6. Нажать `Сгенерировать картограмму`.
7. Показать легенду, статистику, историю сессий и экспорт в `PNG/PDF`.

## Структура проекта

- [app](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/app)
  серверная логика и сервисы
- [templates](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/templates)
  HTML-шаблоны
- [static](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/static)
  стили и фронтенд-логика
- [data](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/data)
  демо-данные и геослои
- [storage](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/storage)
  загруженные файлы и экспорты
- [docs](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs)
  материалы для защиты

## Полезные материалы

- [Архитектура](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/architecture.md)
- [Руководство пользователя](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/user-guide.md)
- [Шпаргалка к защите](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/defense-notes.md)
- [Экономическое обоснование для 4 главы](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/economic-justification.md)
- [Word-версия экономического обоснования](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/economic-justification.docx)
- [Полное объяснение проекта на понятном языке](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/project-explained-simple.md)
- [Word-версия полного объяснения проекта](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/project-explained-simple.docx)
- [Глава 3 диплома в Markdown](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/chapter-3.md)
- [Глава 3 диплома в Word](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/chapter-3.docx)
- [Глава 3 диплома в Word (обновленная версия)](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/chapter-3-updated.docx)
- [Тестовые сценарии](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/docs/test-scenarios.md)

## Готовые артефакты

После тестового прогона уже сформированы примерные экспортные материалы:

- [PNG-картограмма](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/storage/exports/session_3/cartogram.png)
- [PDF-отчет](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/storage/exports/session_3/cartogram.pdf)
- [CSV-выгрузка](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/storage/exports/session_3/cartogram.csv)
- [GeoJSON-результат](/C:/Users/свекла/Documents/Codex/2026-04-28-files-mentioned-by-the-user-c/storage/exports/session_3/cartogram.geojson)
