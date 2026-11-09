Учебный проект, демонстрирующий системы **Retrieval-Augmented Generation (RAG)**
на базе фреймворка [Haystack](https://haystack.deepset.ai/).

RAG-система сочетает **поиск** релевантных документов и **генерацию** ответа
языковой моделью, что позволяет получать развёрнутые ответы, опирающиеся
на собственную базу знаний.

В проекте реализованы **два независимых пайплайна** и **графический интерфейс**:

| Компонент | Файл | Описание |
|-----------|------|----------|
| Генеративный RAG-чат | `chat_pipeline.py` | Векторный поиск + LLM через Ollama |
| Экстрактивный QA | `extractive_qa_pipeline.py` | BM25 + извлечение ответа из документов |
| GUI-чат | `gui.py` | Чат-интерфейс на Flet (поверх `chat_pipeline`) |
| CLI-пример | `main.py` | Запуск генеративного RAG из консоли |
| Утилиты | `helpers.py` | Чтение документов из файла |

---

## 📂 Структура проекта

```
haystack-rag-app/
├── main.py                     # CLI-точка входа (генеративный RAG)
├── gui.py                      # GUI-чат на Flet
├── chat_pipeline.py            # RAG: эмбеддинги + векторный поиск + Ollama
├── extractive_qa_pipeline.py   # Экстрактивный QA: BM25 + ExtractiveReader
├── helpers.py                  # Чтение документов, утилиты
├── requirements.txt
├── README.md
└── data/
    └── test.txt                # База знаний: одна строка — один документ
```

---

## ⚙️ Требования

- **Python 3.10+**
- **Ollama** — локальный сервер LLM (для генеративного RAG-чата)
  - Скачать: <https://ollama.com/download>
  - После установки загрузите модель, используемую в `chat_pipeline.py`:
    ```bash
    ollama pull gemma3:1b
    ```
  - Сервер должен быть доступен по адресу `http://127.0.0.1:11434`
    (запускается автоматически после установки, либо вручную командой `ollama serve`).

> Экстрактивный пайплайн (`extractive_qa_pipeline.py`) **не требует** Ollama —
> он работает только на локальных моделях Hugging Face.

---

## 🚀 Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/Lordounos/haystack-rag-app_gui.git
   cd haystack-rag-app
   ```

2. **Создайте виртуальное окружение:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux / macOS
   # venv\Scripts\activate       # Windows
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Подготовьте данные:**
   Поместите файл с базой знаний в `data/test.txt`.
   Формат: **одна строка = один документ**.
   ```
   Xiaomi 14 Pro стоит 89990 рублей.
   Samsung Galaxy S24 стоит 79990 рублей.
   iPhone 15 Pro стоит 119990 рублей.
   ```

5. **(Для RAG-чата) Запустите Ollama и загрузите модель:**
   ```bash
   ollama pull gemma3:1b
   ollama serve    # если сервер ещё не запущен
   ```

---

## 🖥️ Использование

### GUI-чат (рекомендуется)

Запускает тёмный чат-интерфейс на Flet, работающий поверх генеративного RAG-пайплайна:

```bash
python gui.py
```

Откроется окно чата. Введите вопрос о смартфонах — например,
*«Сколько стоит Xiaomi 14 Pro?»* — и получите ответ, сгенерированный
моделью с опорой на документы из `data/test.txt`.

### Консольный RAG-чат

```bash
python main.py
```

Запускает пайплайн из `chat_pipeline.py` на захардкоженном вопросе и
печатает ответ в консоль. Удобно для отладки пайплайна без GUI.

### Экстрактивный QA

```bash
python extractive_qa_pipeline.py
```

Находит и возвращает **фрагмент** документа, содержащий ответ.
Не использует LLM — ответ извлекается напрямую из текста.

---

## 🧠 Как работают пайплайны

### Генеративный RAG (`chat_pipeline.py`, `gui.py`, `main.py`)

```
Вопрос
  │
  ▼
SentenceTransformersTextEmbedder   (all-MiniLM-L6-v2)
  │  вектор запроса
  ▼
InMemoryEmbeddingRetriever         (top_k = 3)
  │  релевантные документы
  ▼
ChatPromptBuilder                  (вставляет контекст в шаблон)
  │  промпт с контекстом
  ▼
OllamaChatGenerator                (gemma3:1b)
  │
  ▼
Ответ пользователю
```

### Экстрактивный QA (`extractive_qa_pipeline.py`)

```
Вопрос
  │
  ▼
InMemoryBM25Retriever   (лексический поиск, top_k = 3)
  │  документы-кандидаты
  ▼
ExtractiveReader        (выделяет span с ответом)
  │
  ▼
Фрагмент ответа
```

---

## 🔧 Настройка

- **Модель генерации** — `chat_pipeline.py`, строка `OllamaChatGenerator(model=...)`.
- **Эмбеддинг-модель** — переменная `embedder_model` в `chat_pipeline.py`.
- **Количество документов из ретривера** — `top_k` в `InMemoryEmbeddingRetriever`.
- **Промпт** — шаблон `template` в `chat_pipeline.py`.
- **База знаний** — `data/test.txt` (одна строка = один документ).

---

## 🩹 Известные замечания

- `ExtractiveReader` в `extractive_qa_pipeline.py` по умолчанию инициализируется
  sentence-embedding моделью (`all-MiniLM-L6-v2`), которая **не является QA-моделью**.
  Для корректной работы замените её на question-answering модель, например:
  ```python
  reader = ExtractiveReader(model="deepset/roberta-base-squad2")
  ```
- `helpers.read_from_file` сохраняет `\n` в конце документов; при необходимости
  добавьте `line.strip()`.
- Инициализация пайплайна в `chat_pipeline.py` происходит на уровне модуля —
  при импорте (`gui.py`, `main.py`) эмбеддер и документы загружаются сразу.

---

## 📦 Зависимости

Основные пакеты (см. `requirements.txt`):

- `haystack-ai<3` — фреймворк
- `ollama-haystack` — интеграция с Ollama
- `sentence-transformers>=4.1.0`, `transformers[torch,sentencepiece]` — модели HF
- `flet` — GUI
- `python-dotenv`, `huggingface_hub[hf_xet]`

---

## 🤝 Вклад

Будем рады вашим предложениям!
Открывайте **issue** или отправляйте **pull request** для улучшений и исправления ошибок.
```

