
# Практична робота №2
## Автономні агенти та Multi-Agent Systems

### Варіант 3 — DevOps Assistant: Infrastructure Monitoring

## 1. Мета роботи

Реалізувати мультиагентну систему для моніторингу інфраструктури,
аналізу логів та формування безпечних remediation-рекомендацій.

У роботі використано:

- LangGraph
- CrewAI
- FastMCP
- LangSmith
- Guardrails
- Human-in-the-Loop
- pytest

---

## 2. Архітектура MAS

Система складається з чотирьох ролей:

### coordinator
Координує workflow, перевіряє prompt injection та визначає маршрут обробки.

### monitor_agent
Перевіряє стан сервісу через MCP tool `check_service`.

### log_analyzer
Аналізує ERROR/WARNING логи через `search_logs`
та формує root cause.

### action_agent
Пропонує remediation-дію.
Ризикові операції `restart_service` та `scale_service`
не виконуються без Human-in-the-Loop approval.

Схема:

User Request
→ Coordinator
→ Monitor Agent
→ Log Analyzer
→ Action Agent
→ HITL
→ MCP Tool

---

## 3. MCP Server

Реалізовано FastMCP сервер з інструментами:

- `check_service(name)`
- `search_logs(service, level, minutes)`
- `restart_service(name)`
- `scale_service(name, replicas)`

MCP tools інтегровані через `langchain-mcp-adapters`.

---

## 4. Демонстраційний сценарій

Інцидент:

`API gateway response time > 5s`

Результат роботи LangGraph MAS:

- api-gateway має degraded status;
- response time ≈ 6200 ms;
- виявлено upstream timeout;
- виявлено high request queue;
- рекомендовано масштабувати сервіс до 4 replicas;
- scale потребує Human-in-the-Loop approval.

---

## 5. Guardrails

### Input guardrail
Виявлення prompt injection:

- ignore previous instructions
- system prompt extraction
- jailbreak/bypass patterns

### Tool guardrail
Реалізовано allowlist по агентах.

Наприклад:

- `monitor_agent` → тільки `check_service`
- `log_analyzer` → тільки `search_logs`
- `action_agent` → `check_service`, `restart_service`, `scale_service`

### Argument validation

Для `scale_service`:

`1 <= replicas <= 10`

Для `search_logs`:

- level: INFO / WARNING / ERROR
- minutes: 1–60

### Output guardrail

Редагування:

- email
- phone
- API keys
- tokens
- passwords

---

## 6. Human-in-the-Loop

Ризикова операція масштабування реалізована через LangGraph interrupt/checkpointer.

Перевірено два сценарії:

1. Approve → scale виконується.
2. Reject → scale не виконується.

---

## 7. Basic Red-Teaming

Перевірено:

- Prompt injection → BLOCKED
- System prompt extraction → BLOCKED
- Unauthorized risky tool → BLOCKED
- Invalid scale argument → BLOCKED

---

## 8. Тестування

Реалізовано pytest-тести:

### MCP tests

- check_service
- search_logs
- scale_service validation

### Guardrail tests

- prompt injection detection
- safe prompt
- tool allowlist
- scale validation
- log validation
- sensitive data redaction

Результат:

`9 passed`

---

## 9. LangGraph vs CrewAI

| Критерій | LangGraph | CrewAI |
|---|---|---|
| Архітектура | Явний граф станів | Agents + Tasks |
| Routing | Повний контроль кодом | Частково делегований framework/LLM |
| Debugging | Легко відслідковувати node transitions | Менше контролю над внутрішнім execution |
| Guardrails | Легко додавати перед node/tool | Потребує додаткових wrapper-ів |
| HITL | Природно через interrupt/checkpointer | Потребує окремої approval-логіки |
| LLM-виклики | Може працювати детерміновано без LLM | Зазвичай LLM викликається для task/agent |
| Token/API usage | У demo — 0 Gemini calls | Запуск обмежено free-tier quota |

CrewAI реалізація була створена успішно:

- 4 agents
- 3 tasks
- sequential process

Під час `kickoff_async()` Google Gemini API повернув
`429 RESOURCE_EXHAUSTED`,
оскільки було досягнуто free-tier quota для моделі.

---

## 10. Tracing

Для observability використано LangSmith.

Проєкт:

`Task_002_DevOps_MAS`

Trace:

`Task_002_Trace_Direct`

Trace містить:

Input:
- service: api-gateway
- alert: response time > 5s

Output:
- root cause: High load and upstream timeout
- recommended action: scale to 4 replicas
- hitl_required: true

---

## 11. Аналітичні питання

### 1. Чому action_agent варто відокремити від monitor/log agents?

Розділення відповідальності зменшує ризик випадкового виконання небезпечної дії.
Monitor та log agents мають read-only доступ,
тоді як action_agent працює з risky tools.
Це спрощує аудит, tool allowlist і HITL.

### 2. Як захиститися від cascading failure?

Перед restart/scale необхідно:

- перевірити стан залежних сервісів;
- використовувати replicas limits;
- вводити cooldown;
- застосовувати rate limits;
- вимагати HITL для risky actions;
- не дозволяти одному агенту безконтрольно виконувати remediation.

### 3. Audit logging: LangGraph vs CrewAI

LangGraph дає більш явний контроль,
оскільки кожен node та state transition можна логувати окремо.
CrewAI простіше налаштувати,
але частина execution логіки прихована всередині framework.

LangSmith дозволяє централізовано зберігати traces,
inputs, outputs та execution metadata.

---

## 12. Файли проєкту

- `Task_002_Бабенко_Варіант_3.ipynb`
- `mcp_server.py`
- `guardrails.py`
- `test_devops.py`
- `README.md`
- screenshot / trace evidence from LangSmith

---

## 13. Висновок

У роботі реалізовано multi-agent DevOps Assistant
на основі LangGraph,
FastMCP,
guardrails,
Human-in-the-Loop
та LangSmith tracing.

Система розділяє monitoring,
log analysis
та remediation,
що забезпечує контроль доступу до risky tools
і зменшує ризик небезпечних автоматичних дій.
