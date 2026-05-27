# ML Service

`ml-service` содержит локальную ML-часть проекта: распознавание голосовых сообщений, выделение получателя и текста сообщения, а также сопоставление распознанного имени с получателями из базы бота.

## Назначение

Модуль используется `bot-service` в голосовом сценарии:

1. `SpeechToTextService` преобразует Telegram voice audio в текст.
2. `RuBertSlotFillingService` извлекает из текста получателя и содержание сообщения.
3. `RecipientMatcher` сравнивает извлеченное имя с получателями пользователя и возвращает точное, уверенное или неоднозначное совпадение.

Все runtime-сервисы работают локально и не требуют API-ключей.

## Структура

```text
ml-service/
├── ml_service/
│   ├── __init__.py
│   ├── stt_service.py              # speech-to-text через faster-whisper
│   ├── slot_filling_service.py     # inference token classification модели
│   └── recipient_matcher.py        # fuzzy/lemmatized matching получателей
├── data/
│   └── slot_filling_train.jsonl    # обучающие примеры
├── models/
│   └── rubert-slot-filling/        # локальная обученная модель
├── samples/
│   └── test_voice.mp3              # пример аудио для ручной проверки
├── test/
│   ├── test_slot_filling.py
│   └── test_stt.py
├── requirements.txt
└── train_slot_filling.py
```

## Зависимости

ML-зависимости вынесены в `ml-service/requirements.txt`. При установке из корневого `requirements.txt` они подтягиваются автоматически:

```powershell
pip install -r requirements.txt
```

## Модель Slot Filling

Финальная модель ожидается по пути:

```text
ml-service/models/rubert-slot-filling
```

Этот путь используется ботом по умолчанию через настройку `SLOT_FILLING_MODEL_PATH=../ml-service/models/rubert-slot-filling`.

Обучение запускается из корня проекта:

```powershell
python .\ml-service\train_slot_filling.py
```

Скрипт читает данные из `ml-service/data/slot_filling_train.jsonl` и сохраняет модель в `ml-service/models/rubert-slot-filling`.

## Ручные Проверки

Проверка slot filling:

```powershell
python .\ml-service\test\test_slot_filling.py
```

Проверка speech-to-text:

```powershell
python .\ml-service\test\test_stt.py
```

STT может потребовать локально доступную модель faster-whisper. Если модель не закэширована, библиотека может попытаться скачать ее при первом запуске.

## Интеграция С Ботом

`bot-service/Application.py` добавляет папку `ml-service` в `sys.path` и импортирует сервисы из пакета `ml_service`. Бот не обращается к файлам ML напрямую, а использует только публичные классы пакета:

- `SpeechToTextService`
- `RuBertSlotFillingService`
- `RecipientMatcher`
