# Python-библиотеки и программные средства

| Название | Назначение | Связанные КИМ | Доступ | Версия курса | Лицензия | Дата проверки |
|---|---|---|---|---|---|---|
| Python | язык и стандартная библиотека | все | [документация](https://docs.python.org/3/) | 3.12–3.14 | PSF License | 2026-07-21 |
| JupyterLab | интерактивные ноутбуки | КИМ-2–6 | [документация](https://jupyterlab.readthedocs.io/) | `>=4,<5` | BSD-3-Clause | 2026-07-21 |
| NumPy | массивы и численные операции | КИМ-2–6 | [документация](https://numpy.org/doc/stable/) | `>=2,<3` | BSD-3-Clause | 2026-07-21 |
| pandas | табличные данные и аудит качества | КИМ-2–6 | [документация](https://pandas.pydata.org/docs/) | `>=2.2,<4` | BSD-3-Clause | 2026-07-21 |
| SciPy | статистические методы | КИМ-2, КИМ-5 | [документация](https://docs.scipy.org/doc/scipy/) | `>=1.14,<2` | BSD-3-Clause | 2026-07-21 |
| statsmodels | статистические модели и диагностика | КИМ-2, КИМ-5 | [документация](https://www.statsmodels.org/stable/) | `>=0.14,<1` | BSD-3-Clause | 2026-07-21 |
| Matplotlib | базовая визуализация | КИМ-2, КИМ-6 | [документация](https://matplotlib.org/stable/) | `>=3.9,<4` | PSF-based | 2026-07-21 |
| Seaborn | статистическая визуализация | КИМ-2, КИМ-6 | [документация](https://seaborn.pydata.org/) | `>=0.13,<1` | BSD-3-Clause | 2026-07-21 |
| scikit-learn | пайплайны, модели и оценка | КИМ-3–6 | [документация](https://scikit-learn.org/stable/) | `>=1.5,<2` | BSD-3-Clause | 2026-07-21 |

Единый список диапазонов находится в корневом [`requirements.txt`](../../../requirements.txt). Преподаватель фиксирует точные версии в начале семестра и публикует проверенный lock-файл либо экспорт окружения.

Для [авторского синтетического кейса](../../../examples/synthetic-case/README.md) проверенное окружение закреплено отдельным [`requirements.txt`](../../../examples/synthetic-case/requirements.txt), а облегчённый набор для CI — в [`requirements-test.txt`](../../../examples/synthetic-case/requirements-test.txt).
