from contextlib import closing

from app.database import get_connection
from app.models import CardFull, CardType, OptionFull, Topic


def _row_to_topic(row) -> Topic:
    return Topic(
        id=row["id"],
        title=row["title"],
        description=row["description"],
    )


def _row_to_option(row) -> OptionFull:
    return OptionFull(
        id=row["id"],
        card_id=row["card_id"],
        option_text=row["option_text"],
        is_correct=bool(row["is_correct"]),
    )


def get_all_topics() -> list[Topic]:
    """
    Возвращает все темы.
    """
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id, title, description
            FROM topics
            ORDER BY id
            """
        ).fetchall()

    return [_row_to_topic(row) for row in rows]


def get_topic_by_id(topic_id: int) -> Topic | None:
    """
    Возвращает одну тему по id.
    """
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT id, title, description
            FROM topics
            WHERE id = ?
            """,
            (topic_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_topic(row)


def count_cards_by_topic_and_type(topic_id: int, card_type: CardType) -> int:
    """
    Считает количество карточек нужного типа по конкретной теме.
    """
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM cards
            WHERE topic_id = ?
              AND card_type = ?
            """,
            (topic_id, card_type),
        ).fetchone()

    return int(row["cnt"])


def get_random_card_ids_by_topic(
    topic_id: int,
    card_type: CardType,
    limit: int,
) -> list[int]:
    """
    Возвращает случайные id карточек по теме и типу.

    Для SQLite используется ORDER BY RANDOM().
    Для учебного локального приложения это нормальный простой вариант.
    """
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM cards
            WHERE topic_id = ?
              AND card_type = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (topic_id, card_type, limit),
        ).fetchall()

    return [int(row["id"]) for row in rows]


def _get_options_by_card_id_using_connection(
    connection,
    card_id: int,
) -> list[OptionFull]:
    rows = connection.execute(
        """
        SELECT id, card_id, option_text, is_correct
        FROM options
        WHERE card_id = ?
        ORDER BY id
        """,
        (card_id,),
    ).fetchall()

    return [_row_to_option(row) for row in rows]


def _get_card_with_options_using_connection(
    connection,
    card_id: int,
) -> CardFull | None:
    row = connection.execute(
        """
        SELECT id, topic_id, card_type, question
        FROM cards
        WHERE id = ?
        """,
        (card_id,),
    ).fetchone()

    if row is None:
        return None

    options = _get_options_by_card_id_using_connection(connection, card_id)

    return CardFull(
        id=row["id"],
        topic_id=row["topic_id"],
        card_type=row["card_type"],
        question=row["question"],
        options=options,
    )


def get_card_with_options(card_id: int) -> CardFull | None:
    """
    Возвращает карточку вместе со всеми вариантами ответа.
    """
    with closing(get_connection()) as connection:
        return _get_card_with_options_using_connection(connection, card_id)


def get_cards_with_options(card_ids: list[int]) -> list[CardFull]:
    """
    Возвращает карточки с вариантами ответа в том же порядке,
    в котором были переданы card_ids.
    """
    result: list[CardFull] = []

    with closing(get_connection()) as connection:
        for card_id in card_ids:
            card = _get_card_with_options_using_connection(connection, card_id)

            if card is not None:
                result.append(card)

    return result


def get_correct_option_ids(card_id: int) -> list[int]:
    """
    Возвращает id правильных вариантов ответа для карточки.
    """
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM options
            WHERE card_id = ?
              AND is_correct = 1
            ORDER BY id
            """,
            (card_id,),
        ).fetchall()

    return [int(row["id"]) for row in rows]


def get_all_option_ids_by_card_id(card_id: int) -> list[int]:
    """
    Возвращает id всех вариантов ответа конкретной карточки.

    Это нужно, чтобы при проверке игнорировать option_id,
    которые не принадлежат данной карточке.
    """
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM options
            WHERE card_id = ?
            ORDER BY id
            """,
            (card_id,),
        ).fetchall()

    return [int(row["id"]) for row in rows]


def get_wrong_card_ids() -> list[int]:
    """
    Возвращает id всех карточек, которые находятся в режиме ошибок.
    """
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT card_id
            FROM wrong_cards
            ORDER BY id
            """
        ).fetchall()

    return [int(row["card_id"]) for row in rows]


def add_wrong_card(card_id: int) -> None:
    """
    Добавляет карточку в wrong_cards.

    INSERT OR IGNORE нужен, потому что card_id UNIQUE.
    Если карточка уже есть в wrong_cards, ошибки не будет.
    """
    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO wrong_cards (card_id)
            VALUES (?)
            """,
            (card_id,),
        )
        connection.commit()


def remove_wrong_card(card_id: int) -> None:
    """
    Удаляет карточку из wrong_cards.
    """
    with closing(get_connection()) as connection:
        connection.execute(
            """
            DELETE FROM wrong_cards
            WHERE card_id = ?
            """,
            (card_id,),
        )
        connection.commit()


def is_wrong_card(card_id: int) -> bool:
    """
    Проверяет, находится ли карточка в wrong_cards.
    """
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT id
            FROM wrong_cards
            WHERE card_id = ?
            """,
            (card_id,),
        ).fetchone()

    return row is not None