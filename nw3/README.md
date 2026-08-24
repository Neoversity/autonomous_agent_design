EnergyAgent — Практичне завдання №1

Опис проєкту

EnergyAgent — агентна система для аналізу домашньої енергосистеми, побудована на LangGraph.

Система демонструє:

доменні tools з Pydantic v2;

ReAct-патерн;

Plan-and-Execute;

checkpointing через SqliteSaver;

Agentic RAG з ChromaDB;

Human-in-the-Loop для ризикових операцій;

pytest-тестування;

JSON-логування траєкторії.

Доменні tools

У проєкті реалізовано такі інструменти:

get_energy_status — отримання поточного стану інвертора;

calculate_safe_load — розрахунок безпечного додаткового навантаження;

check_battery_safety — перевірка безпечності розряду батареї;

set_inverter_power_limit — зміна ліміту потужності інвертора;

search_energy_knowledge — пошук рекомендацій у ChromaDB.

Кожен tool використовує Pydantic v2 схеми з BaseModel, Field та field_validator.

Результати tools повертаються у JSON-форматі:

{
  "status": "success",
  "data": {}
}

або:

{
  "status": "error",
  "error": "Опис помилки"
}

ReAct Agent

ReAct-агент реалізований у LangGraph за схемою:

LLM -> Tools -> LLM

Додані захисні механізми:

max_steps = 10;

timeout = 120 секунд;

детекція повторних tool-викликів;

JSON-логування траєкторії.

Приклад задачі:

Перевір inverter_1 і визнач, скільки додаткового навантаження можна безпечно підключити при резерві 500 Вт.

Результат:

900 Вт

Plan-and-Execute

Реалізовано окремий LangGraph:

planner -> executor -> replanner

Structured Output реалізований через:

Plan;

ReplanDecision;

with_structured_output().

Planner формує послідовність кроків, executor виконує їх через ReAct-агента, а replanner перевіряє прогрес і за необхідності змінює план.

Checkpointing

Для збереження стану використовується SqliteSaver.

Файл:

energy_agent_checkpoints.sqlite

Продемонстровано:

збереження стану між кроками;

get_state();

переривання через interrupt_before;

відновлення виконання через invoke(None, config=...).

Приклад:

10 -> step_one -> 11 -> interrupt -> resume -> step_two -> 22

Agentic RAG

База знань реалізована через ChromaDB.

Кількість документів: 10

RAG tool:

search_energy_knowledge

Агент самостійно вирішує, коли необхідно звертатися до бази знань.

Приклад:

Який мінімальний SOC батареї рекомендується?

Agentic RAG знаходить правило про рекомендований мінімальний SOC 20%.

Human-in-the-Loop

Ризиковим інструментом є:

set_inverter_power_limit

Перед виконанням використовується:

interrupt_before=["execute_change"]

Продемонстровано два сценарії.

Approve

Зміна ліміту:

6000 W -> 5000 W

Reject

Запит на зміну до 4000 W був відхилений.

Після відхилення фактичний ліміт залишився:

5000 W

Тестування

Тести запускаються командою:

pytest -v test_energy_agent.py

Результат:

11 passed

Тести охоплюють:

Pydantic validation;

некоректні параметри;

domain tools;

базові компоненти ReAct-агента.

Основні файли

Task_001_Бабенко_EnergyAgent.ipynb

energy_agent_core.py

test_energy_agent.py

trajectory.json

energy_agent_checkpoints.sqlite

README.md

Запуск

Відкрити notebook у Google Colab.

Встановити необхідні залежності.

Додати GOOGLE_API_KEY у Colab Secrets.

Запускати комірки послідовно.

Для перевірки тестів виконати:

pytest -v test_energy_agent.py

Висновок

У межах практичної роботи реалізовано повний цикл побудови автономної агентної системи: від формалізованих tools і ReAct-циклу до Plan-and-Execute, persistence, Agentic RAG та Human-in-the-Loop.

Система демонструє контрольовану поведінку агента, збереження стану, роботу з базою знань, валідацію входів та людське підтвердження ризикових дій.
