# Voice to Employee Email

Проект реализует Telegram-бота для отправки голосовых поручений получателям из пользовательской базы. Пользователь управляет получателями через inline-кнопки, отправляет голосовое сообщение, а приложение локально распознает речь, выделяет адресата и текст сообщения, сопоставляет адресата с сохраненными получателями и отправляет подтвержденный текст через Telegram.

## Состав Проекта

Проект разделен на два рабочих модуля:

- [`bot-service`](bot-service/README.md) - Telegram-бот на aiogram, SQLite-хранилище, inline-обработчики, бизнес-логика диалогов и отправка сообщений.
- [`ml-service`](ml-service/README.md) - локальные ML-сервисы: speech-to-text, slot filling, сопоставление получателей, данные и скрипт обучения модели.

## Структура

```text
voice-to-employee-email/
├── bot-service/
│   ├── Application.py              # точка входа Telegram-бота
│   ├── config.py                   # настройки из .env и окружения
│   ├── database/                   # SQLite-схема
│   ├── handlers/                   # inline-сценарии aiogram
│   ├── repositories/               # доступ к БД и модели данных
│   ├── services/                   # бизнес-логика бота
│   └── README.md                   # документация бота
├── ml-service/
│   ├── ml_service/                 # Python-пакет ML-сервисов
│   ├── data/                       # обучающие данные slot filling
│   ├── models/                     # локальные веса моделей
│   ├── samples/                    # тестовые аудио
│   ├── test/                       # ручные проверки ML-сервисов
│   ├── train_slot_filling.py       # обучение slot filling
│   └── README.md                   # документация ML-части
├── .github/workflows/ci.yml        # CI pipeline
├── requirements.txt                # общий файл зависимостей
└── README.md                       # обзор проекта
```

## Основной Сценарий

1. Пользователь открывает меню бота и добавляет получателя по `chat_id` и ФИО.
2. Пользователь нажимает `Отправить` и записывает голосовое сообщение.
3. `SpeechToTextService` распознает аудио в текст.
4. `RuBertSlotFillingService` выделяет получателя и сообщение.
5. `RecipientMatcher` сопоставляет имя с получателями из SQLite.
6. При низкой уверенности бот предлагает выбрать получателя inline-кнопкой.
7. Пользователь подтверждает отправку.
8. Бот отправляет сообщение в формате `отправитель: текст`.

## Быстрый Запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .\bot-service\.env.example .\bot-service\.env
```

В `bot-service/.env` нужно указать токен Telegram-бота:

```env
BOT_TOKEN=123456:replace-with-telegram-bot-token
```

Запуск:

```powershell
python .\bot-service\Application.py
```

Подробности настройки, переменных окружения и пользовательского интерфейса описаны в [`bot-service/README.md`](bot-service/README.md).

## ML-Часть

ML-модуль работает локально и не требует внешнего API-ключа для выполнения inference. Slot filling использует локальную папку модели, а STT использует `faster-whisper`.

Подробности по структуре ML-пакета, обучению и ручным проверкам описаны в [`ml-service/README.md`](ml-service/README.md).

## CI

GitHub Actions pipeline находится в [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Он проверяет:

- синтаксис Python-файлов в `bot-service` и `ml-service`;
- импорт приложения и основных пакетов;
- smoke-тест SQLite-слоя, временных состояний бота и `RecipientMatcher`.
