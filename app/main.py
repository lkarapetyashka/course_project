import json
from typing import Annotated
from uuid import uuid4

from urllib.parse import urlencode
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import crud, services
from app.models import FinishAttemptRequest, FinishAttemptResponse


app = FastAPI(title="Тренажёр по интегральному исчислению")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def _model_dump(model):
    """
    Небольшая совместимость для разных версий Pydantic.

    В Pydantic v2 используется model_dump().
    В Pydantic v1 использовался dict().
    """
    if hasattr(model, "model_dump"):
        return model.model_dump()

    return model.dict()


def _render_select_topic_with_error(
    request: Request,
    mode: str,
    error: str,
) -> HTMLResponse:
    topics = crud.get_all_topics()

    return templates.TemplateResponse(
        request=request,
        name="select_topic.html",
        context={
            "mode": mode,
            "topics": topics,
            "error": error,
        },
        status_code=400,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )

@app.get("/select-topic/{mode}", response_class=HTMLResponse)
def select_topic(request: Request, mode: str):
    try:
        services.validate_topic_mode(mode)
    except services.ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    topics = crud.get_all_topics()

    return templates.TemplateResponse(
        request=request,
        name="select_topic.html",
        context={
            "mode": mode,
            "topics": topics,
            "error": None,
        },
    )


@app.post("/attempt/start")
def start_attempt(
    request: Request,
    mode: Annotated[str, Form()],
    topic_ids: Annotated[list[int] | None, Form()] = None,
):
    """
    Создание варианта по выбранным темам.

    Так как таблиц attempts больше нет, мы не сохраняем вариант в БД.
    Вместо этого:
        1. выбираем случайные card_id;
        2. передаём их в GET-адрес /attempt/view;
        3. сама страница уже подгружает карточки по этим id.
    """
    try:
        card_ids = services.create_topic_attempt_card_ids(
            mode=mode,
            topic_ids=topic_ids,
        )
    except services.ServiceError as exc:
        return _render_select_topic_with_error(
            request=request,
            mode=mode,
            error=str(exc),
        )

    query = urlencode(
        {
            "mode": mode,
            "cards": ",".join(str(card_id) for card_id in card_ids),
            "run": uuid4().hex,
        }
    )

    return RedirectResponse(
        url=f"/attempt/view?{query}",
        status_code=303,
    )


@app.post("/attempt/errors")
def start_errors_attempt(request: Request):
    """
    Создание варианта из всех карточек wrong_cards.
    """
    try:
        card_ids = services.create_errors_attempt_card_ids()
    except services.NoWrongCardsError:
        return templates.TemplateResponse(
            request=request,
            name="errors_empty.html",
            context={},
        )

    query = urlencode(
        {
            "mode": "errors",
            "cards": ",".join(str(card_id) for card_id in card_ids),
            "run": uuid4().hex,
        }
    )

    return RedirectResponse(
        url=f"/attempt/view?{query}",
        status_code=303,
    )


@app.get("/attempt/view", response_class=HTMLResponse)
@app.get("/attempt/view", response_class=HTMLResponse)
def view_attempt(
    request: Request,
    mode: str,
    cards: str,
    run: str | None = None,
):
    """
    Страница прохождения варианта.

    Пример URL:
        /attempt/view?mode=theory&cards=1,5,9,12
    """
    try:
        card_ids = services.parse_card_ids(cards)
        attempt = services.build_attempt_view_data(
            mode=mode,
            card_ids=card_ids,
            run_id=run,
        )
    except services.ServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attempt_json = json.dumps(
        _model_dump(attempt),
        ensure_ascii=False,
    )

    return templates.TemplateResponse(
        request=request,
        name="attempt.html",
        context={
            "attempt": attempt,
            "attempt_json": attempt_json,
        },
    )


@app.post(
    "/api/finish-attempt",
    response_model=FinishAttemptResponse,
)
def finish_attempt(payload: FinishAttemptRequest):
    """
    Проверяет ответы, обновляет wrong_cards и возвращает результат.
    """
    try:
        return services.finish_attempt(payload)
    except services.ServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc