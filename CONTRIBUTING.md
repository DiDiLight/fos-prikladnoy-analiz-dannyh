# Правила внесения изменений

Каждое изменение должно улучшать проверяемость результатов обучения, прозрачность оценивания или воспроизводимость КИМ.

## Рабочий процесс

1. Создайте ветку `feature/<short-name>` или `fix/<short-name>`.
2. Вносите одно логически завершённое изменение за коммит.
3. Используйте сообщения вида `docs: уточнить рубрику EDA` или `fix: исправить ссылку на датасет`.
4. Установите окружение из `requirements-lock.txt`.
5. Выполните валидатор, smoke-test и тесты воспроизводимости.
6. Если менялись зависимости, пересоберите lock-файл и повторите установку в чистое окружение.
7. В Pull Request укажите затронутые компетенции, индикаторы, КИМ и изменение баллов.
8. Получите рецензию хотя бы одного участника, не являющегося автором изменения.

Команды для PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\validate_repository.py
.\.venv\Scripts\python.exe scripts\smoke_test.py
.\.venv\Scripts\python.exe -m unittest discover -s examples\synthetic-case\tests -v
```

Команды для Windows `cmd.exe`:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements-lock.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\validate_repository.py
.venv\Scripts\python.exe scripts\smoke_test.py
.venv\Scripts\python.exe -m unittest discover -s examples\synthetic-case\tests -v
```

## Обновление зависимостей

`requirements.txt` содержит только прямые зависимости и остаётся удобным для чтения. Точные прямые и транзитивные версии хранятся только в `requirements-lock.txt`.

Lock-файл пересобирается `uv 0.11.33` для Python 3.12 сразу с маркерами Windows, Linux и macOS:

```powershell
py -3.12 -m pip install uv==0.11.33
$env:UV_CACHE_DIR=".venv\uv-cache"
py -3.12 -m uv pip compile --universal --python-version 3.12 --output-file requirements-lock.txt requirements.txt
```

После изменения lock-файла обязательна установка в новое виртуальное окружение и полный набор проверок из раздела выше.

## Требования к КИМ

- результат наблюдаем и связан с индикатором;
- условия, входные материалы и формат сдачи однозначны;
- критерии соответствуют заданию и целевому уровню;
- баллы совпадают с [итоговой системой](docs/assessment-system.md);
- правила внешних ресурсов и генеративного ИИ сформулированы явно;
- примерные данные и код не нарушают лицензии и конфиденциальность.

## Именование

- папки модулей: `M1-task-formulation`, `M2-data-understanding` и далее;
- КИМ: `kim-01-project-brief.md`, `kim-02-eda.md`;
- рубрики: `rubric-01.md`;
- приложения: `appendix-01-name.ext`.

## Изменение баллов

Изменение максимального балла требует одновременного обновления:

1. КИМ и рубрики;
2. корневой модели измерения;
3. `docs/assessment-system.md`;
4. проверки суммы 100 баллов;
5. описания Pull Request.
