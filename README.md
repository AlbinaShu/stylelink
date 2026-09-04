# AI·StyleLink — Backend

Backend для приложения AI·StyleLink — сервиса персональных рекомендаций одежды и образов.

Стек:

* Python 3
* FastAPI
* PostgreSQL
* SQLAlchemy 2
* Alembic
* JWT
* Pydantic Settings
* Gmail SMTP
* Docker

AI-генерация образов пока не подключена. Backend подготовлен для дальнейшей интеграции AI.

---

## Структура проекта

```text
stylelink/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── alembic.ini
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
├── frontend/
└── README.md
```

Все серверные файлы находятся в директории `backend`.

---

# Запуск проекта

## 1. Перейти в backend

После открытия проекта:

```bash
cd backend
```

Проверить, что вы находитесь в директории backend:

```bash
pwd
```

---

## 2. Создать виртуальное окружение

Если `.venv` ещё не существует:

```bash
python3 -m venv .venv
```

Активировать окружение:

```bash
source .venv/bin/activate
```

После активации в терминале должен появиться префикс:

```text
(.venv)
```

---

## 3. Установить зависимости

```bash
python -m pip install -r requirements.txt
```

Для работы с паролями используется:

```text
bcrypt==4.0.1
```

Эта версия зафиксирована для совместимости с используемым `passlib`.

---

# PostgreSQL

Проект использует PostgreSQL.

По умолчанию PostgreSQL запускается в Docker-контейнере:

```text
stylelink-postgres
```

Порт:

```text
5433
```

Проверить состояние контейнера:

```bash
docker ps
```

Проверить готовность PostgreSQL:

```bash
docker exec stylelink-postgres pg_isready
```

Ожидаемый результат:

```text
/var/run/postgresql:5432 - accepting connections
```

### Если контейнер уже существует

Если контейнер `stylelink-postgres` уже создан и запущен, повторно выполнять:

```bash
docker compose up -d
```

не обязательно.

Если Docker Compose пытается создать второй контейнер с таким же именем и появляется ошибка `name conflict`, необходимо использовать уже существующий контейнер `stylelink-postgres`.

---

# Переменные окружения

В директории `backend` должен находиться файл:

```text
.env
```

Пример структуры:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/stylelink

JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=...

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM=your_email@gmail.com
```

Файл `.env` не следует добавлять в Git.

Для настройки можно использовать:

```text
.env.example
```

---

# Миграции базы данных

Для применения миграций используется Alembic.

Применить все существующие миграции:

```bash
alembic upgrade head
```

Проверить текущую миграцию:

```bash
alembic current
```

Создать новую миграцию:

```bash
alembic revision --autogenerate -m "description"
```

После создания миграции:

```bash
alembic upgrade head
```

---

# Запуск FastAPI

Запускать приложение рекомендуется через Python из активного виртуального окружения:

```bash
python -m uvicorn app.main:app --reload
```

После запуска API будет доступно по адресу:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# Swagger

Основное тестирование API выполняется через Swagger:

```text
http://127.0.0.1:8000/docs
```

После авторизации JWT можно использовать кнопку:

```text
Authorize
```

Токен передаётся как:

```text
Bearer <access_token>
```

Swagger сохраняет авторизацию между запросами.

---

# API

Все основные endpoints находятся под префиксом:

```text
/api/v1
```

## Аутентификация

### Запрос кода подтверждения email

```http
POST /api/v1/auth/email/request-code
```

Отправляет код подтверждения на email.

### Подтверждение email

```http
POST /api/v1/auth/email/verify
```

Проверяет код подтверждения.

### Определение пользователя

```http
POST /api/v1/auth/identify
```

Проверяет наличие пользователя и определяет дальнейший сценарий авторизации.

### Регистрация

```http
POST /api/v1/auth/register
```

Создаёт нового пользователя.

### Вход

```http
POST /api/v1/auth/login
```

Авторизует пользователя и возвращает JWT access token.

### Выход

```http
POST /api/v1/auth/logout
```

Отзывает текущий JWT-токен.

После logout использованный токен больше не должен приниматься API.

### Запрос кода восстановления пароля

```http
POST /api/v1/auth/password-reset/request-code
```

Отправляет код восстановления пароля.

### Проверка кода восстановления

```http
POST /api/v1/auth/password-reset/verify
```

Проверяет код восстановления.

### Подтверждение нового пароля

```http
POST /api/v1/auth/password-reset/confirm
```

Устанавливает новый пароль пользователя.

---

# Пользователь

### Получение текущего пользователя

```http
GET /api/v1/users/current_user
```

Возвращает данные авторизованного пользователя.

Требуется JWT.

### Изменение пользователя

```http
PATCH /api/v1/users/current
```

Изменяет данные текущего пользователя.

Требуется JWT.

---

# Профиль

### Получение профиля

```http
GET /api/v1/profile
```

Возвращает профиль текущего пользователя.

Требуется JWT.

### Изменение профиля

```http
PUT /api/v1/profile
```

Создаёт или обновляет профиль пользователя.

Требуется JWT.

---

# Генерации

### Создание генерации

```http
POST /api/v1/generations
```

Создаёт запрос на генерацию образа.

На текущем этапе данные сохраняются в базе данных.

AI-генерация будет подключена позднее.

Требуется JWT.

### Получение генераций

```http
GET /api/v1/generations
```

Возвращает генерации текущего пользователя.

Требуется JWT.

### Получение образов генерации

```http
GET /api/v1/generations/{generation_id}/outfits
```

Возвращает образы, связанные с конкретной генерацией.

Также возвращаются товары, входящие в каждый образ.

Требуется JWT.

---

# Outfits

Отдельный endpoint для получения образов через:

```text
/api/v1/outfits/generation/{generation_id}
```

не используется.

Основной endpoint:

```http
GET /api/v1/generations/{generation_id}/outfits
```

---

# Безопасность

Авторизация построена на JWT.

Access token содержит:

* `sub` — идентификатор пользователя
* `jti` — уникальный идентификатор токена
* `exp` — срок действия токена

При logout `jti` текущего токена сохраняется в таблице отозванных токенов.

После этого API отклоняет данный токен даже до истечения его срока действия.

---

# Email

Для отправки email используется Gmail SMTP.

Основные настройки:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM=your_email@gmail.com
```

Для Gmail рекомендуется использовать App Password, а не обычный пароль аккаунта.

Email используется для:

* подтверждения email;
* восстановления пароля.

---

# База данных

Основные сущности:

* User
* Profile
* Generation
* Outfit
* OutfitItem
* RevokedToken

Связи между сущностями реализованы через SQLAlchemy.

Изменения структуры базы данных выполняются через Alembic.

---

# Рекомендуемый порядок запуска

Каждый раз при запуске проекта:

### 1. Перейти в backend

```bash
cd backend
```

### 2. Активировать окружение

```bash
source .venv/bin/activate
```

### 3. Проверить PostgreSQL

```bash
docker exec stylelink-postgres pg_isready
```

### 4. Применить миграции

```bash
alembic upgrade head
```

### 5. Запустить сервер

```bash
python -m uvicorn app.main:app --reload
```

### 6. Открыть Swagger

```text
http://127.0.0.1:8000/docs
```

После этого API можно полностью тестировать через Swagger.

---

# Тестирование

Рекомендуемый порядок проверки API:

1. Регистрация / подтверждение email
2. Login
3. Получение текущего пользователя
4. Получение и изменение профиля
5. Создание генерации
6. Получение списка генераций
7. Получение outfits конкретной генерации
8. Logout
9. Проверка, что старый JWT больше не работает
10. Password reset

AI-интеграция и платежи не входят в текущий этап тестирования backend.

---

# Текущий статус

Backend готов к локальному запуску и ручному тестированию через Swagger.

Реализовано:

* регистрация;
* email verification;
* login;
* JWT authorization;
* logout с отзывом токена;
* password reset;
* пользователь;
* профиль;
* генерации;
* outfits;
* PostgreSQL;
* SQLAlchemy;
* Alembic;
* Gmail SMTP.

В дальнейшем планируется добавить:

* AI-генерацию образов;
* рекомендации одежды;
* интеграцию с маркетплейсами;
* подписки;
* дополнительные функции профиля и рекомендаций.
