from typing import Literal

from pydantic import BaseModel, Field


CardType = Literal["theory", "practice"]
AttemptMode = Literal["theory", "practice", "errors"]
ResultStatus = Literal["correct", "incorrect", "unanswered"]


class Topic(BaseModel):
    id: int
    title: str
    description: str | None = None


class OptionFull(BaseModel):
    """
    Полная модель варианта ответа.

    Используется на сервере, потому что серверу нужно знать,
    правильный вариант или нет.
    """
    id: int
    card_id: int
    option_text: str
    is_correct: bool


class OptionPublic(BaseModel):
    """
    Безопасная модель варианта ответа для передачи в шаблон и JS.

    Здесь специально нет поля is_correct, чтобы правильные ответы
    не попадали на страницу до завершения варианта.
    """
    id: int
    option_text: str


class CardFull(BaseModel):
    """
    Полная карточка.

    Используется внутри сервера для проверки ответов.
    """
    id: int
    topic_id: int | None = None
    card_type: CardType
    question: str
    options: list[OptionFull]


class CardPublic(BaseModel):
    """
    Карточка для отображения пользователю.

    В ней нет информации о правильных вариантах.
    """
    id: int
    topic_id: int | None = None
    card_type: CardType
    question: str
    options: list[OptionPublic]


class AttemptViewData(BaseModel):
    """
    Данные для страницы прохождения варианта.

    Вариант не хранится в БД, поэтому список card_ids передаётся
    на клиент и используется при завершении.
    """
    mode: AttemptMode
    title: str
    attempt_key: str
    card_ids: list[int]
    cards: list[CardPublic]


class FinishAttemptRequest(BaseModel):
    """
    То, что браузер отправляет серверу при завершении варианта.

    answers имеет вид:
    {
        1: [10, 11],
        2: [15],
        3: []
    }

    где ключ — id карточки,
    значение — список выбранных option_id.
    """
    mode: AttemptMode
    card_ids: list[int] = Field(default_factory=list)
    answers: dict[int, list[int]] = Field(default_factory=dict)


class CardCheckResult(BaseModel):
    card_id: int
    status: ResultStatus
    selected_option_ids: list[int]
    correct_option_ids: list[int]


class FinishAttemptResponse(BaseModel):
    total: int
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    percent: float
    items: list[CardCheckResult]