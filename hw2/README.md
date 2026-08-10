# Домашнє завдання №2
## Plan-and-Execute з Memory, Agentic RAG та Human-in-the-Loop

Автор: Антон Бабенко

---

## 1. Опис проєкту

У роботі реалізовано AI-агента з архітектурою Plan-and-Execute на базі LangGraph.

Агент спочатку формує повний план виконання задачі, після чого виконує його послідовно. Після кожного виконаного кроку replanner оцінює актуальність плану та приймає рішення: продовжити виконання, перепланувати залишкові кроки або завершити задачу.

Реалізовано:

1. Plan-and-Execute: planner → executor → replanner.
2. Persistence через SqliteSaver.
3. Agentic RAG через ChromaDB.
4. Human-in-the-Loop через interrupt()/Command(resume=...).

---

## 2. Використані технології

- Python
- Google Colab
- LangGraph
- LangChain
- Gemini API
- Pydantic
- SQLite / SqliteSaver
- ChromaDB

---

## 3. Архітектура Plan-and-Execute

Основний граф:

START → planner → executor → replanner → executor / END

### Planner

Planner отримує запит користувача та формує структурований план.

Використовується Pydantic-модель `Plan`:

- `goal`
- `steps`

Structured output:

`planner_llm = llm.with_structured_output(Plan)`

### Executor

Executor виконує один крок плану за одну ітерацію.

Доступні tools:

- calculator
- get_weather
- convert_currency
- search_hotels
- search_knowledge

### Replanner

Replanner аналізує результати виконаних кроків та повертає `ReplanDecision`.

Можливі рішення:

- continue
- replan
- finish

---

## 4. Демонстрація Plan-and-Execute

Тестова задача:

Порахуй 120 * 3 + 45 і потім конвертуй результат за курсом 1.08.

Planner сформував два кроки:

1. Використати calculator.
2. Використати convert_currency.

Результати:

- Крок 1: calculator: 405
- Крок 2: convert_currency: 405.0 × 1.08 = 437.40
- Completed: True

---

## 5. Persistence та SqliteSaver

Для persistence використовується файловий SQLite checkpointer:

`agent_state.db`

З'єднання створюється через `sqlite3.connect()` та передається у `SqliteSaver`.

Граф компілюється з checkpointer, тому стан зберігається після виконання вузлів.

---

## 6. Відновлення стану

Тестова задача:

Порахуй 50 * 4, а потім конвертуй результат за курсом 1.1.

Граф було зупинено після першого executor.

На момент зупинки:

- Thread ID: persistence-demo-001
- Current step: 1
- Крок 1: calculator: 200
- Completed: False

Після закриття старого SQLite-з'єднання було створено нове з'єднання до того самого `agent_state.db`.

Стан відновився з того самого `thread_id`.

Після продовження:

- Крок 1: calculator: 200
- Крок 2: convert_currency: 200.0 × 1.1 = 220.00
- Completed: True

Таким чином агент продовжив виконання з checkpoint, а не почав задачу заново.

---

## 7. Незалежність thread_id

Продемонстровано дві сесії:

- persistence-demo-001
- persistence-demo-002

Перша сесія містила завершений стан.

Друга сесія з новим thread_id мала порожній стан.

Це демонструє незалежність різних сесій.

---

## 8. Agentic RAG

Для локальної бази знань використано ChromaDB.

База створена через PersistentClient та зберігається у директорії:

`chroma_db`

У базу завантажено 10 документів туристичної тематики.

Тематика документів:

- правила перебування у Шенгенській зоні;
- Париж;
- транспорт;
- Лувр;
- квитки;
- сезони;
- безпека;
- бюджет;
- готелі;
- страхування.

---

## 9. search_knowledge

Створено LangChain tool:

`search_knowledge`

Tool повертає топ-3 релевантних документи.

Для покращення українськомовного пошуку реалізовано hybrid search:

1. semantic search через ChromaDB;
2. keyword reranking.

На запит про правила перебування українців у Шенгенській зоні першим повертається документ про:

- біометричний паспорт;
- безвіз;
- правило 90 днів протягом 180-денного періоду.

---

## 10. Автономний вибір RAG

Агент самостійно вибирає потрібний tool.

Для запиту про правила короткострокового перебування громадян України у Шенгенській зоні агент вибрав:

`search_knowledge`

Для математичного запиту:

`Порахуй 250 * 4 + 100`

агент вибрав:

`calculator`

Результат:

`1100`

Таким чином продемонстровано Agentic RAG: база знань використовується тільки тоді, коли вона справді потрібна.

---

## 11. Human-in-the-Loop

Для HITL створено ризиковий tool:

`book_hotel`

Перед виконанням бронювання викликається `interrupt()`.

Граф зупиняється та показує:

- назву готелю;
- дату заїзду;
- кількість ночей;
- загальну вартість.

Для HITL використовується SqliteSaver.

---

## 12. Approve flow

Початкові параметри:

- Paris Demo Hotel
- 2026-09-15
- 3 ночі
- 360 EUR

Після `Command(resume={"approved": True})`:

- Approved: True
- бронювання виконано.

Результат:

ЗАБРОНЬОВАНО: Paris Demo Hotel, заїзд 2026-09-15, 3 ночей, вартість 360.00 EUR

---

## 13. Reject flow

Окрема HITL-сесія:

- Paris Expensive Hotel
- 4 ночі
- 1200 EUR

Людина відхилила дію з причиною:

`Занадто висока вартість`

Результат:

- Approved: False
- бронювання не виконувалося.

---

## 14. Edit flow

Додатково реалізовано зміну параметрів перед виконанням.

Початково:

- 4 ночі
- 500 EUR

Після edit:

- 3 ночі
- 320 EUR

Результат:

Параметри змінено оператором. ЗАБРОНЬОВАНО: Paris Demo Hotel, заїзд 2026-09-25, 3 ночей, вартість 320.00 EUR

---

## 15. Аналіз результатів

Plan-and-Execute дозволяє розбивати складні задачі на послідовність кроків та контролювати виконання кожного кроку.

SqliteSaver забезпечує persistence та дозволяє відновити роботу після перезапуску процесу.

Thread ID дозволяє підтримувати незалежні сесії.

Agentic RAG дозволяє LLM самостійно вирішувати, коли потрібна база знань, а коли треба використати інший tool.

HITL дозволяє зупиняти виконання перед ризиковими діями та передавати остаточне рішення людині.

У роботі також мінімізовано кількість LLM-запитів: локальні перевірки, persistence, ChromaDB та HITL виконуються без Gemini.

---

## 16. Запуск

Встановлення залежностей:

pip install langgraph langgraph-checkpoint-sqlite langchain langchain-core langchain-google-genai chromadb "pydantic>=2.0"

У Google Colab API-ключ Gemini зберігається у Secret:

`GOOGLE_API_KEY`

Notebook виконується послідовно зверху вниз.

---

## 17. Артефакти

До роботи входять:

- HW2_Babenko_Plan_Execute.ipynb
- README.md
- agent_state.db
- chroma_db/

---

## Висновок

У роботі реалізовано:

- Plan-and-Execute граф;
- planner;
- executor;
- replanner;
- structured outputs;
- 4+ tools;
- SqliteSaver;
- persistence;
- відновлення після restart;
- незалежні thread_id;
- ChromaDB з 10 документами;
- search_knowledge;
- Agentic RAG;
- HITL interrupt;
- approve;
- reject;
- edit.
