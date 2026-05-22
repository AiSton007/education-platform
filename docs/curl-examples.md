# Happy-path curl-сценарий

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
echo "$ACCESS"
```

## 3. Создание теста (менеджером)

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
        "type": "single",
        "text": "Что такое 2FA?",
        "weight": 1,
        "options": [
          {"order":0,"text":"Двойной пароль","is_correct":false},
          {"order":1,"text":"Второй фактор аутентификации","is_correct":true}
        ]
      },
      {
        "order": 1,
        "type": "multiple",
        "text": "Какие пароли НЕЛЬЗЯ использовать?",
        "weight": 1,
        "options": [
          {"order":0,"text":"qwerty","is_correct":true},
          {"order":1,"text":"GxR!82Wm@","is_correct":false},
          {"order":2,"text":"password","is_correct":true}
        ]
      },
      {
        "order": 2,
        "type": "free_text",
        "text": "Опишите политику обработки персональных данных вашего отдела",
        "weight": 2
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

EMP_TOKENS=$(curl -s -X POST $GW/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"alice-pass-12345"}')
EMP=$(echo "$EMP_TOKENS" | jq -r .access_token)
```

## 5. Старт попытки и ответы

```bash
ATT=$(curl -s -X POST "$GW/api/v1/tests/$TEST_ID/start" \
  -H "Authorization: Bearer $EMP")
ATTEMPT_ID=$(echo "$ATT" | jq -r .id)

# Берём вопросы и опции из публичной выдачи (без is_correct).
QUESTIONS=$(curl -s "$GW/api/v1/tests/$TEST_ID" -H "Authorization: Bearer $EMP" | jq -c .questions)

# Пример: пусть первая опция верная, вторая — неверная и т.д. — для краткости вручную:
curl -s -X POST "$GW/api/v1/attempts/$ATTEMPT_ID/answers" \
  -H "Authorization: Bearer $EMP" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --argjson q "$QUESTIONS" '{
    answers: [
      {question_id: $q[0].id, selected_option_ids: [$q[0].options[1].id]},
      {question_id: $q[1].id, selected_option_ids: [$q[1].options[0].id, $q[1].options[2].id]},
      {question_id: $q[2].id, free_text: "Только обезличенные данные обрабатываются вне периметра."}
    ]
  }')"
```

## 6. Сабмит — оркестрация LLM + отчёт

```bash
RES=$(curl -s -X POST "$GW/api/v1/attempts/$ATTEMPT_ID/submit" \
  -H "Authorization: Bearer $EMP")
echo "$RES" | jq .
REPORT_ID=$(echo "$RES" | jq -r .report_id)
```

## 7. Чтение отчёта

```bash
curl -s "$GW/api/v1/reports/$REPORT_ID" -H "Authorization: Bearer $EMP" | jq .
curl -s "$GW/api/v1/reports/$REPORT_ID/download?format=html" -H "Authorization: Bearer $EMP" -o report.html
```

## 8. Refresh-токен

```bash
curl -s -X POST $GW/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d "{\"refresh_token\":\"$REFRESH\"}" | jq .
```

## 9. Профиль через `/me`

```bash
curl -s "$GW/api/v1/users/me" -H "Authorization: Bearer $EMP" | jq .
```
