# Happy-path curl-сценарий (free-form testing)

Все запросы идут через `api-gateway` (`http://localhost:18080` локально, `https://api.mokryakov.local` в k8s).
Заменяй `$GW`, `$ACCESS`, `$TEST_ID`, `$ATTEMPT_ID`, `$REPORT_ID` на свои значения.

```bash
export GW=http://localhost:18080
```

## 1. Регистрация менеджера (создатель тестов)

```bash
curl -s -X POST $GW/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "manager@example.com",
    "password": "manager-pass-12345",
    "full_name": "Иван Менеджер",
    "department": "ИТ",
    "position": "тимлид",
    "role": "manager"
  }' | jq .
```

## 2. Логин

```bash
TOKENS=$(curl -s -X POST $GW/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"manager@example.com","password":"manager-pass-12345"}')
ACCESS=$(echo "$TOKENS" | jq -r .access_token)
REFRESH=$(echo "$TOKENS" | jq -r .refresh_token)
```

## 3. Создание теста (свободные вопросы + правильные ответы)

```bash
TEST=$(curl -s -X POST $GW/api/v1/tests \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Базовая ИБ",
    "description": "Минимальные знания по информационной безопасности",
    "questions": [
      {
        "order": 0,
        "text": "Что такое 2FA и зачем она нужна?",
        "correct_answer": "Двухфакторная аутентификация: подтверждение входа вторым фактором (одноразовый код, push, аппаратный токен) дополнительно к паролю; защищает аккаунт при утечке пароля."
      },
      {
        "order": 1,
        "text": "Опишите политику обработки персональных данных",
        "correct_answer": "Обрабатываются только необходимые данные, доступ — по принципу наименьших привилегий, передача наружу — только обезличенно и через утверждённые каналы."
      }
    ]
  }')
TEST_ID=$(echo "$TEST" | jq -r .id)
echo "test_id=$TEST_ID"
```

## 4. Регистрация и логин сотрудника

```bash
curl -s -X POST $GW/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"alice@example.com",
    "password":"alice-pass-12345",
    "full_name":"Алиса Сотрудник",
    "role":"employee"
  }'

# узнаём её user_id
EMP_TOKENS=$(curl -s -X POST $GW/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"alice-pass-12345"}')
EMP=$(echo "$EMP_TOKENS" | jq -r .access_token)
EMP_ID=$(curl -s "$GW/api/v1/users/me" -H "Authorization: Bearer $EMP" | jq -r .user_id)
```

## 5. Назначение теста сотруднику (от имени менеджера)

```bash
curl -s -X POST $GW/api/v1/assignments \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d "{
    \"test_id\": \"$TEST_ID\",
    \"user_ids\": [\"$EMP_ID\"]
  }" | jq .
```

## 6. Сотрудник видит назначенные тесты

```bash
curl -s "$GW/api/v1/assignments/me" -H "Authorization: Bearer $EMP" | jq .
```

## 7. Старт попытки, свободные ответы, сабмит

```bash
ATT=$(curl -s -X POST "$GW/api/v1/tests/$TEST_ID/start" \
  -H "Authorization: Bearer $EMP")
ATTEMPT_ID=$(echo "$ATT" | jq -r .id)

QUESTIONS=$(curl -s "$GW/api/v1/tests/$TEST_ID" -H "Authorization: Bearer $EMP" | jq -c .questions)

curl -s -X POST "$GW/api/v1/attempts/$ATTEMPT_ID/answers" \
  -H "Authorization: Bearer $EMP" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --argjson q "$QUESTIONS" '{
    answers: [
      {question_id: $q[0].id, free_text: "Двухфакторная аутентификация — второй фактор для входа"},
      {question_id: $q[1].id, free_text: "Только обезличенные данные обрабатываются вне периметра"}
    ]
  }')"

RES=$(curl -s -X POST "$GW/api/v1/attempts/$ATTEMPT_ID/submit" \
  -H "Authorization: Bearer $EMP")
echo "$RES" | jq .
REPORT_ID=$(echo "$RES" | jq -r .report_id)
```

## 8. Сотрудник смотрит результат и историю

```bash
# Детально по попытке (per-question scores + feedback)
curl -s "$GW/api/v1/attempts/$ATTEMPT_ID" -H "Authorization: Bearer $EMP" | jq .

# История прохождений
curl -s "$GW/api/v1/attempts/me/history" -H "Authorization: Bearer $EMP" | jq .

# Отчёт
curl -s "$GW/api/v1/reports/$REPORT_ID" -H "Authorization: Bearer $EMP" | jq .
```

## 9. Менеджер: список прохождений и PDF

```bash
# Все прохождения по тесту
curl -s "$GW/api/v1/attempts?test_id=$TEST_ID" -H "Authorization: Bearer $ACCESS" | jq .

# PDF отчёт
curl -s "$GW/api/v1/reports/$REPORT_ID/download?format=pdf" \
  -H "Authorization: Bearer $ACCESS" -o report.pdf
```

## 10. Админ: деактивация пользователя и сброс пароля

```bash
# Деактивация (soft delete)
curl -s -X DELETE "$GW/api/v1/users/$EMP_ID" -H "Authorization: Bearer $ADMIN" | jq .

# Реактивация
curl -s -X PATCH "$GW/api/v1/users/$EMP_ID" \
  -H "Authorization: Bearer $ADMIN" \
  -H 'Content-Type: application/json' \
  -d '{"is_active": true}' | jq .

# Сброс пароля (admin only)
curl -s -X POST "$GW/api/v1/auth/admin/reset-password" \
  -H "Authorization: Bearer $ADMIN" \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\": \"$EMP_ID\", \"new_password\": \"new-strong-password-123\"}" | jq .
```
