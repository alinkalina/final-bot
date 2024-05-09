# Друг Женя. Телеграм-бот ассистент

[Ссылка](https://github.com/alinkalina/final-bot) на репозиторий


## Описание

В боте реализован интерфейс запросов к API YandexGPT, Kandinsky и YandexSpeechkit, позволяющий пользователю задавать 
вопросы нейросети, рисовать картинки и запрашивать перевод из текста в голос и из голоса в текст, и всё в формате диалога.
Кроме того, пользователь может настроить голос ассистента и посмотреть свой баланс.


## Инструкция по запуску проекта

- Клонируйте репозиторий
- Добавьте необходимые библиотеки Python, зависимости прописаны в файле [requirements.txt](https://github.com/alinkalina/final-bot/blob/main/requirements.txt)
- Создайте файл `config.py` и поместите в него переменные:
  - `BOT_TOKEN` (str) - Ваш токен Телеграм бота
  - `IAM_TOKEN` (str) - Ваш iam токен для доступа к API GPT
  - `FOLDER_ID` (str) - Ваш folder id для доступа к API GPT
  - `X_KEY` (str) - Ваш x-key для доступа к API Kandinsky
  - `X_SECRET` (str) - Ваш x-secret для доступа к API Kandinsky
- Запустите файл `bot.py`
- Перейдите в бота по [ссылке](https://t.me/alulamalula_final_bot) и нажмите СТАРТ
- Пользуйтесь командами из Меню для работы в боте


## Файлы проекта

- bot.py - обработчики всех команд (message_handler) и функции-колбэки для register_next_step_handler
- database.py - создание таблиц и все функции для запросов и отправки данных в БД
- gpt.py - запросы к API YandexGPT
- kandinsky.py - запросы к API Kandinsky
- speechkit.py - запросы к API YandexSpeechkit
- limitation.py - функция для подсчёта токенов в ответе GPT и функции для проверки превышения лимитов пользователем
- limits.py - лимиты и некоторые константы, связанные с ними
- constants.py - полезные константы (списки, словари)
- _config.py - личные данные (токены, пароли), прописан в .gitignore_
- README.md - описание проекта
- requirements.txt - зависимости
- .gitignore - гитигнор
- logs.txt - файл с логами


## Контакты

Для связи с разработчиком можно использовать следующие контакты:
- [Telegram](https://t.me/alulamalula)
