import hashlib

from app import crud
from app.models import (
    AttemptMode,
    AttemptViewData,
    CardCheckResult,
    CardFull,
    CardPublic,
    CardType,
    FinishAttemptRequest,
    FinishAttemptResponse,
    OptionPublic,
)


CARDS_PER_TOPIC = 10


class ServiceError(Exception):
    """
    Базовая ошибка уровня бизнес-логики.
    """


class InvalidModeError(ServiceError):
    pass


class NoTopicsSelectedError(ServiceError):
    pass


class TopicNotFoundError(ServiceError):
    pass


class NotEnoughCardsError(ServiceError):
    pass


class NoWrongCardsError(ServiceError):
    pass


class EmptyAttemptError(ServiceError):
    pass


class CardNotFoundError(ServiceError):
    pass


def _unique_ints(values: list[int]) -> list[int]:
    """
    Убирает повторы, сохраняя порядок.
    """
    result: list[int] = []
    seen: set[int] = set()

    for value in values:
        value = int(value)

        if value not in seen:
            result.append(value)
            seen.add(value)

    return result


def validate_topic_mode(mode: str) -> CardType:
    """
    Для выбора тем разрешены только theory и practice.
    Режим errors темы не использует.
    """
    if mode not in ("theory", "practice"):
        raise InvalidModeError("Недопустимый режим. Используйте theory или practice.")

    return mode  # type: ignore[return-value]


def validate_attempt_mode(mode: str) -> AttemptMode:
    """
    Для уже созданного варианта возможны theory, practice и errors.
    """
    if mode not in ("theory", "practice", "errors"):
        raise InvalidModeError("Недопустимый режим варианта.")

    return mode  # type: ignore[return-value]


def get_mode_title(mode: AttemptMode) -> str:
    if mode == "theory":
        return "Теория интегрального исчисления"

    if mode == "practice":
        return "Практические задания"

    return "Отработка неверно решённых карточек"


def create_topic_attempt_card_ids(
    mode: str,
    topic_ids: list[int] | None,
) -> list[int]:
    """
    Создаёт список id карточек для режима theory или practice.

    Важный момент:
    так как таблицы attempts теперь нет, мы не сохраняем вариант в БД.
    Мы просто генерируем список card_id и потом передаём его в URL.

    (Для каждой выбранной темы требуется минимум 10 карточек.)
    Если карточек меньше, лучше сразу показать ошибку,
    чем составлять неполный вариант незаметно для пользователя.
    """
    card_type = validate_topic_mode(mode)

    if not topic_ids:
        raise NoTopicsSelectedError("Выберите хотя бы одну тему.")

    unique_topic_ids = _unique_ints(topic_ids)
    result_card_ids: list[int] = []

    for topic_id in unique_topic_ids:
        topic = crud.get_topic_by_id(topic_id)

        if topic is None:
            raise TopicNotFoundError(f"Тема с id={topic_id} не найдена.")

        cards_count = crud.count_cards_by_topic_and_type(
            topic_id=topic_id,
            card_type=card_type,
        )

        # if cards_count < CARDS_PER_TOPIC:
        #     raise NotEnoughCardsError(
        #         f"По теме «{topic.title}» найдено карточек: {cards_count}. "
        #         f"Нужно минимум {CARDS_PER_TOPIC} карточек типа «{card_type}»."
        #     )

        random_card_ids = crud.get_random_card_ids_by_topic(
            topic_id=topic_id,
            card_type=card_type,
            limit=CARDS_PER_TOPIC,
        )

        result_card_ids.extend(random_card_ids)

    if not result_card_ids:
        raise EmptyAttemptError("Не удалось составить вариант.")

    return result_card_ids


def create_errors_attempt_card_ids() -> list[int]:
    """
    Создаёт список карточек для режима отработки ошибок.

    Берутся все карточки из wrong_cards.
    """
    card_ids = crud.get_wrong_card_ids()

    if not card_ids:
        raise NoWrongCardsError("Сейчас нет карточек для отработки ошибок.")

    return card_ids


def parse_card_ids(raw_card_ids: str) -> list[int]:
    """
    Преобразует строку из URL вида:
        1,5,10,12

    в список:
        [1, 5, 10, 12]
    """
    if not raw_card_ids.strip():
        raise EmptyAttemptError("Список карточек пуст.")

    try:
        card_ids = [
            int(part)
            for part in raw_card_ids.split(",")
            if part.strip()
        ]
    except ValueError as exc:
        raise EmptyAttemptError("Некорректный список карточек.") from exc

    card_ids = _unique_ints(card_ids)

    if not card_ids:
        raise EmptyAttemptError("Список карточек пуст.")

    return card_ids


def make_attempt_key(mode: AttemptMode, card_ids: list[int], run_id: str | None = None) -> str:
    """
    Создаёт стабильный ключ варианта

    Он нужен для localStorage:
    если пользователь обновит страницу с тем же набором card_id,
    браузер сможет восстановить выбранные ответы и результат

    run_id нужен, чтобы при новом входе в вариант браузер
    не подхватывал старое завершённое состояние
    """
    raw = f"{mode}:{','.join(str(card_id) for card_id in card_ids)}:{run_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _to_public_card(card: CardFull) -> CardPublic:
    """
    Превращает полную карточку в публичную.

    Главное отличие:
    публичная карточка не содержит is_correct.
    """
    return CardPublic(
        id=card.id,
        topic_id=card.topic_id,
        card_type=card.card_type,
        question=card.question,
        options=[
            OptionPublic(
                id=option.id,
                option_text=option.option_text,
            )
            for option in card.options
        ],
    )


def build_attempt_view_data(
    mode: str,
    card_ids: list[int],
    run_id: str | None = None,
) -> AttemptViewData:
    """
    Готовит данные для страницы прохождения варианта.
    """
    attempt_mode = validate_attempt_mode(mode)

    if not card_ids:
        raise EmptyAttemptError("В варианте нет карточек.")

    cards = crud.get_cards_with_options(card_ids)

    found_card_ids = {card.id for card in cards}
    missing_card_ids = [
        card_id
        for card_id in card_ids
        if card_id not in found_card_ids
    ]

    if missing_card_ids:
        raise CardNotFoundError(
            f"Не найдены карточки с id: {missing_card_ids}."
        )

    if attempt_mode in ("theory", "practice"):
        for card in cards:
            if card.card_type != attempt_mode:
                raise InvalidModeError(
                    f"Карточка id={card.id} имеет тип {card.card_type}, "
                    f"но вариант запущен в режиме {attempt_mode}."
                )

    return AttemptViewData(
        mode=attempt_mode,
        title=get_mode_title(attempt_mode),
        attempt_key=make_attempt_key(attempt_mode, card_ids, run_id),
        card_ids=card_ids,
        cards=[_to_public_card(card) for card in cards],
    )


def finish_attempt(payload: FinishAttemptRequest) -> FinishAttemptResponse:
    """
    Проверяет завершённый вариант.

    Проверка ответа:
        выбранные option_id == правильные option_id

    Если ответ правильный:
        карточка удаляется из wrong_cards.

    Если ответ неправильный:
        карточка добавляется в wrong_cards.
    """
    mode = validate_attempt_mode(payload.mode)
    card_ids = _unique_ints(payload.card_ids)

    if not card_ids:
        raise EmptyAttemptError("Нельзя завершить пустой вариант.")

    cards = crud.get_cards_with_options(card_ids)

    if len(cards) != len(card_ids):
        found_ids = {card.id for card in cards}
        missing_ids = [
            card_id
            for card_id in card_ids
            if card_id not in found_ids
        ]
        raise CardNotFoundError(f"Не найдены карточки: {missing_ids}.")

    if mode in ("theory", "practice"):
        for card in cards:
            if card.card_type != mode:
                raise InvalidModeError(
                    f"Карточка id={card.id} не относится к режиму {mode}."
                )

    items: list[CardCheckResult] = []
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    for card in cards:
        correct_option_ids = sorted(
            option.id
            for option in card.options
            if option.is_correct
        )

        allowed_option_ids = {
            option.id
            for option in card.options
        }

        raw_selected_ids = payload.answers.get(card.id, [])

        selected_option_ids = sorted({
            int(option_id)
            for option_id in raw_selected_ids
            if int(option_id) in allowed_option_ids
        })

        if not selected_option_ids:
            status = "unanswered"
            unanswered_count += 1
        elif set(selected_option_ids) == set(correct_option_ids):
            status = "correct"
            correct_count += 1
            crud.remove_wrong_card(card.id)
        else:
            status = "incorrect"
            incorrect_count += 1
            crud.add_wrong_card(card.id)

        items.append(
            CardCheckResult(
                card_id=card.id,
                status=status,
                selected_option_ids=selected_option_ids,
                correct_option_ids=correct_option_ids,
            )
        )

    total = len(cards)

    percent = round(correct_count / total * 100, 2) if total else 0.0

    return FinishAttemptResponse(
        total=total,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        percent=percent,
        items=items,
    )