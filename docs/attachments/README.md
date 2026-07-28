# Офисные версии документов

| Файл | Основной источник | Назначение |
|---|---|---|
| [rpd-draft.docx](rpd-draft.docx) | [docs/rpd.md](../rpd.md) | редактируемая версия рабочей программы |
| [entry-profile.docx](entry-profile.docx) | [docs/entry-profile.md](../entry-profile.md) | входные дисциплины, компетенции и диагностика |
| [course-presentation.pptx](course-presentation.pptx) | [README.md](../../README.md), [модель компетенций](../competency-model.md), [РПД](../rpd.md) | краткая презентация концепции курса |

Markdown является основной версией комплекта. Перед публикацией офисные файлы сверяются по названию дисциплины, направлению и семестру, индикаторам, уровню `BD-1`, распределению 100 баллов и итоговой шкале. Эту проверку частично выполняет [`scripts/validate_repository.py`](../../scripts/validate_repository.py); внешний вид DOCX и PPTX дополнительно просматривается после рендеринга.
