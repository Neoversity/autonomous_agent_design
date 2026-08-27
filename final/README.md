# HW3 — Production-ready Multi-Agent System

**Автор:** Антон Бабенко  
**Курс:** Agentic AI / Multi-Agent Systems  
**Мова реалізації:** Python 3.10+  
**Основний framework:** LangGraph  
**LLM:** Gemini 3.6 Flash  
**Vector Store:** ChromaDB  
**Persistence:** SqliteSaver  
**Integration Protocol:** MCP  
**Observability:** LangSmith  

---

# 1. Опис проєкту

У фінальному домашньому завданні реалізовано production-oriented Multi-Agent System для customer support.

Система побудована за supervisor-патерном та складається з кількох спеціалізованих агентів:

- `supervisor` — маршрутизація запитів;
- `billing` — платежі, рахунки, повернення коштів;
- `tech` — технічні проблеми та troubleshooting;
- `researcher` — пошук інформації у knowledge base;
- `general` — fallback для загальних запитів.

Основна мета роботи — не створення агентів з нуля, а інтеграція та перевикористання компонентів з ДЗ1 та ДЗ2 у повноцінну multi-agent систему.

---

# 2. Перевикористання компонентів з ДЗ1 та ДЗ2

## ДЗ1 — ReAct Agent

З першого домашнього завдання були перевикористані концепції:

- Pydantic schemas для tools;
- ReAct-style agent execution;
- `MAX_STEPS`;
- timeout;
- trajectory logging;
- tool-based execution;
- test-driven validation агентної поведінки.

У ДЗ3 ці механізми використовуються насамперед у `tech-agent`.

## ДЗ2 — Plan-and-Execute + RAG + Persistence

З другого домашнього завдання перевикористано:

- planner / executor pattern;
- Plan-and-Execute;
- ChromaDB;
- Agentic RAG;
- `SqliteSaver`;
- state persistence;
- HITL через `interrupt()` та `Command(resume=...)`.

У ДЗ3:

- `billing-agent` реалізований у стилі Plan-and-Execute;
- `researcher-agent` використовує Agentic RAG;
- `SqliteSaver` використовується для persistence та HITL.

---

# 3. Архітектура MAS

```text
                         ┌───────────────┐
                         │     USER      │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  SUPERVISOR   │
                         │ RouteDecision │
                         └───────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       ┌────────────┐     ┌────────────┐     ┌──────────────┐
       │  BILLING   │     │    TECH    │     │  RESEARCHER  │
       │ Plan &     │     │ ReAct-style│     │ Agentic RAG  │
       │ Execute    │     │            │     │ + ChromaDB   │
       └─────┬──────┘     └─────┬──────┘     └──────┬───────┘
             │                  │                   │
             ▼                  ▼                   ▼
        Pydantic /          Pydantic /          search_knowledge
        MCP tools           RAG tools            ChromaDB
```

Supervisor використовує structured output через `RouteDecision`, а маршрутизація у LangGraph виконується через conditional edges.

---

# 4. MAS State

Стан системи містить:

- `messages`
- `current_agent`
- `plan`
- `current_step`
- `results`
- `step_count`
- `trajectory`
- `completed`
- `pending_approval`

Таким чином в одному state поєднано компоненти з ДЗ1 та ДЗ2.

---

# 5. Реалізовані агенти

## 5.1 Supervisor

Supervisor аналізує запит і повертає structured `RouteDecision`.

Категорії:

| Agent | Тип запитів |
|---|---|
| billing | payments, subscriptions, invoices, refunds |
| tech | device issues, firmware, errors |
| researcher | policies, FAQ, knowledge base |
| general | fallback |

## 5.2 Billing Agent

Billing реалізовано у стилі **Plan-and-Execute**.

Flow:

```text
Planner
  ↓
Executor
  ↓
search_tickets
  ↓
get_ticket
  ↓
get_customer
  ↓
Finalizer
```

Приклад траєкторії:

```text
supervisor → route
billing → planner
billing → executor
billing → finalizer
```

## 5.3 Tech Agent

Tech-agent використовує ReAct-style execution та компоненти з ДЗ1:

- `MAX_STEPS`;
- timeout;
- tools;
- trajectory logging;
- RAG context.

Для запиту з помилкою `SE-23` система:

- маршрутизувала запит у `tech`;
- знайшла `TKT-002`;
- використала `search_tickets`;
- використала `search_knowledge`;
- сформувала troubleshooting steps.

## 5.4 Researcher Agent

Researcher використовує **Agentic RAG + ChromaDB**.

Для запиту про повернення коштів RAG повернув політику з терміном обробки **3–5 робочих днів**.

Source:

```text
faq://refund-policy
```

---

# 6. ChromaDB

Persistent ChromaDB:

```text
/content/hw3_mas/chroma_db
```

Реалізовано tool:

```python
search_knowledge(query, top_k)
```

Knowledge Base містить документацію щодо:

- refund policy;
- device error SE-23;
- support SLA;
- billing payment failures.

---

# 7. Trajectory Logging

`TrajectoryLogger` з ДЗ1 було розширено полем `agent_name`.

Приклад `trajectory.json`:

```text
Agent: billing
Steps: 4

supervisor → route
billing → planner
billing → executor
billing → finalizer
```

Кожен запис містить:

- `agent_name`;
- `node`;
- `action`;
- `output`;
- `tools`;
- `metadata`;
- timestamp.

---

# 8. SqliteSaver Persistence

LangGraph граф компілюється з `SqliteSaver`.

Persistence database:

```text
agent_state.db
```

Було продемонстровано відновлення state по тому самому `thread_id`.

Результат:

```text
Current agent: billing
Completed: True
Step count: 4
Plan steps: 3
Trajectory steps: 4
```

---

# 9. MCP Server

Реалізовано власний MCP Server:

```text
mcp_server.py
```

Transport:

```text
stdio
```

## MCP Tools

| Tool | Опис | Side effect |
|---|---|---|
| `get_ticket` | отримання ticket | ні |
| `get_customer` | отримання customer | ні |
| `search_tickets` | пошук tickets | ні |
| `get_summary` | статистика support | ні |
| `update_ticket_status` | зміна статусу ticket | так |

`update_ticket_status` вважається ризиковою дією і проходить через HITL.

## MCP Resources

- `faq://general`
- `ticket://{ticket_id}`

## MCP Prompt

- `support_reply(customer_name, issue_summary, tone)`

---

# 10. MCP Unit Tests

Було реалізовано 10 async unit tests.

Результат:

```text
TEST 1 PASS — list_tools
TEST 2 PASS — get_ticket(TKT-001)
TEST 3 PASS — get_ticket(TKT-999) → error
TEST 4 PASS — get_customer(C-100)
TEST 5 PASS — search_tickets(category=billing)
TEST 6 PASS — get_summary
TEST 7 PASS — update_ticket_status(valid)
TEST 8 PASS — update_ticket_status(invalid)
TEST 9 PASS — list_resources
TEST 10 PASS — list_prompts

ALL MCP UNIT TESTS PASSED
```

---

# 11. MCP + LangGraph Integration

MCP Server підключено через `MultiServerMCPClient`.

Було завантажено 5 tools:

```text
get_ticket
get_customer
search_tickets
get_summary
update_ticket_status
```

Також перевірено прямий виклик MCP tools через LangChain-compatible tool interface.

---

# 12. Guardrails

Реалізовано чотири рівні захисту.

| Guardrail | Реалізація | OWASP ASI |
|---|---|---|
| Input | regex prompt injection detection | ASI01 |
| Output | PII redaction | ASI06 |
| Tool | allowlist per agent | ASI03 |
| Rate limit | rolling window per session | ASI08 |

Приклади:

- prompt injection → blocked;
- researcher → `update_ticket_status` → blocked;
- email/phone → redacted;
- 4-й запит при demo limit 3/60s → blocked.

---

# 13. HITL — Human-in-the-loop

Для ризикових tools використовується:

```python
interrupt()
Command(resume=...)
```

Було продемонстровано 3 сценарії:

## APPROVE

```text
TKT-001: open → closed
```

## REJECT

```text
TKT-001: open → open
```

## EDIT

```text
TKT-001: open → resolved
```

Підсумок:

```text
ALL HITL SCENARIOS PASSED
```

---

# 14. Scenario-based Evals

Реалізовано 5 сценаріїв.

| ID | Scenario | Результат |
|---|---|---|
| EVAL-01 | Simple billing | PASS |
| EVAL-02 | Multi-step tech | PASS |
| EVAL-03 | RAG-heavy | PASS |
| EVAL-04 | Cross-agent | PASS |
| EVAL-05 | HITL-flow | PASS |

Результат:

```text
PASS RATE: 5/5 (100.0%)
```

Файл:

```text
eval_results.json
```

---

# 15. Red Teaming

Було реалізовано 5 adversarial scenarios.

| ID | Attack | Захист | Result |
|---|---|---|---|
| RT-01 | Prompt injection | Input guardrail | PASS |
| RT-02 | PII leak | Output guardrail | PASS |
| RT-03 | Scope confusion | Tool allowlist | PASS |
| RT-04 | Tool misuse | HITL | PASS |
| RT-05 | Ukrainian jailbreak | Input guardrail | PASS |

Підсумок:

```text
RED TEAM PASS RATE: 5/5 (100.0%)
```

Файл:

```text
red_team_results.json
```

---

# 16. Observability — LangSmith

Для tracing використовується LangSmith.

Project:

```text
hw3-mas-customer-support
```

Було успішно створено LangSmith trace:

```text
HW3 LangSmith Connection Test
```

Trace містить:

```text
Input:
LangSmith observability test

Output:
LangSmith connection works

Latency:
~0.05 s
```

Це підтверджує працездатність LangSmith integration.

Під час фінального full MAS traced-run було досягнуто free-tier quota Gemini:

```text
RESOURCE_EXHAUSTED
GenerateRequestsPerDayPerProjectPerModel-FreeTier
limit: 20
model: gemini-3.6-flash
```

Тому full MAS trace з LLM hierarchy можна повторити після reset quota.

---

# 17. OWASP Top 10 for Agentic Applications 2026

| ASI | Ризик | Актуальний? | Мітигація | Що залишилось |
|---|---|---|---|---|
| ASI01 | Agent Goal Hijack | Так | Input guardrail з prompt-injection patterns | Regex не покриває всі semantic jailbreaks |
| ASI02 | Tool Misuse and Exploitation | Так | Tool allowlist + Pydantic validation + HITL | Tool може мати логічну вразливість усередині implementation |
| ASI03 | Identity and Privilege Abuse | Так | Per-agent tool permissions | Немає production OAuth / scoped service tokens |
| ASI04 | Agentic Supply Chain Vulnerabilities | Так | MCP server як окремий процес | Не реалізовано automated dependency scanning |
| ASI05 | RCE / Sandbox Escape | Частково | Tools не використовують `eval()` / shell execution | MCP server не запускається у container sandbox |
| ASI06 | Memory Poisoning | Так | Curated ChromaDB KB + PII output filtering | Немає cryptographic verification KB documents |
| ASI07 | Insecure Inter-Agent Communication | Так | Typed LangGraph state + centralized routing | State не підписаний криптографічно |
| ASI08 | Cascading Failures | Так | RateLimiter + MAX_STEPS + timeout | Немає distributed circuit breaker |
| ASI09 | Human-Agent Trust Exploitation | Так | HITL approval gate + approve/reject/edit | Людина все ще може підтвердити небезпечну операцію |
| ASI10 | Rogue Agents | Так | LangSmith tracing + evals + red-team | Немає runtime anomaly detection |

---

# 18. Що залишилось немітигованим

## 1. Semantic Prompt Injection

Input guardrail використовує regex patterns. Це добре працює для відомих атак, але не гарантує виявлення складної semantic injection без відомих ключових фраз.

У production потрібен окремий classifier або LLM-based injection detector.

## 2. Authentication / Authorization

Tool Guardrail обмежує tools на рівні application logic, але MCP server не використовує реальні OAuth scopes або service identities.

У production кожен агент повинен мати:

- scoped token;
- minimal privileges;
- audit identity;
- credential rotation.

## 3. MCP Sandbox Isolation

MCP server запускається як окремий subprocess, але не ізольований Docker/container sandbox.

У production доцільно використовувати:

- Docker;
- read-only filesystem;
- network allowlist;
- seccomp/AppArmor;
- resource limits.

---

# 19. Production Improvements

Наступні кроки для production:

1. Docker isolation для MCP server.
2. OAuth/scoped credentials.
3. LLM-based prompt injection detector.
4. Persistent distributed rate limiter (Redis).
5. Circuit breaker для tools.
6. LangSmith alerts.
7. Automated regression evals у CI/CD.
8. Dependency vulnerability scanning.
9. Production database замість mock data.
10. Secret manager замість environment secrets.
11. Structured audit log для HITL.
12. Retry/backoff для LLM API rate limits.

---

# 20. Структура проєкту

```text
hw3_mas/
│
├── mas_langgraph.py
├── mas_mcp_integration.py
├── tools.py
├── trajectory.py
├── rag.py
├── mcp_server.py
├── mcp_client.py
├── test_mcp_server.py
├── test_mcp_integration.py
├── test_mcp_tool_call.py
├── demo_mas_mcp.py
├── guardrails.py
├── secure_mas_demo.py
├── hitl.py
├── demo_hitl.py
├── evals.py
├── eval_results.json
├── red_team.py
├── red_team_results.json
├── trajectory.json
├── agent_state.db
├── hitl_state.db
├── chroma_db/
└── README.md
```

---

# 21. Фінальні результати

| Компонент | Статус |
|---|---|
| LangGraph Supervisor MAS | ✅ |
| Billing Plan-and-Execute | ✅ |
| Tech ReAct | ✅ |
| Researcher Agentic RAG | ✅ |
| ChromaDB | ✅ |
| SqliteSaver persistence | ✅ |
| TrajectoryLogger | ✅ |
| MCP Server | ✅ |
| MCP Tools | ✅ |
| MCP Resources | ✅ |
| MCP Prompt | ✅ |
| MCP unit tests | ✅ 10/10 |
| MCP + LangGraph integration | ✅ |
| Input Guardrail | ✅ |
| Output Guardrail | ✅ |
| Tool Guardrail | ✅ |
| Rate Limit | ✅ |
| HITL Approve | ✅ |
| HITL Reject | ✅ |
| HITL Edit | ✅ |
| Scenario Evals | ✅ 5/5 |
| Red Teaming | ✅ 5/5 |
| LangSmith Connection | ✅ |
| OWASP ASI Matrix | ✅ |

---

# 22. Висновок

У роботі створено production-oriented Multi-Agent System на базі LangGraph.

Фінальна система поєднує:

- Supervisor MAS;
- ReAct;
- Plan-and-Execute;
- Agentic RAG;
- persistence;
- MCP;
- HITL;
- multi-layer guardrails;
- scenario-based evals;
- red-teaming;
- observability;
- OWASP security analysis.

Основний висновок роботи: production agentic system — це не лише якість LLM reasoning, а й контрольоване orchestration, обмеження privileges, persistence, observability, testing та human approval для критичних операцій.
