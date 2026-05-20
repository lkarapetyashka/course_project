document.addEventListener("DOMContentLoaded", function () {
    const dataElement = document.getElementById("attempt-data-json");

    if (!dataElement) {
        return;
    }

    const attemptData = JSON.parse(dataElement.textContent);

    const storageKey = `integral_trainer_attempt_${attemptData.attempt_key}`;

    const cardElements = Array.from(document.querySelectorAll(".task-card"));
    const cardNumberButtons = Array.from(document.querySelectorAll(".card-number"));

    const prevButton = document.getElementById("prev-card");
    const nextButton = document.getElementById("next-card");
    const finishButton = document.getElementById("finish-attempt");
    const resultPanel = document.getElementById("result-panel");

    const cardById = new Map(
        attemptData.cards.map(card => [Number(card.id), card])
    );

    let currentIndex = 0;
    let answers = {};
    let finished = false;
    let finishResult = null;

    function createEmptyAnswers() {
        const result = {};

        attemptData.card_ids.forEach(cardId => {
            result[Number(cardId)] = [];
        });

        return result;
    }

    function loadState() {
        const rawState = localStorage.getItem(storageKey);

        if (!rawState) {
            return {
                answers: createEmptyAnswers(),
                finished: false,
                result: null
            };
        }

        try {
            const parsed = JSON.parse(rawState);

            return {
                answers: parsed.answers || createEmptyAnswers(),
                finished: Boolean(parsed.finished),
                result: parsed.result || null
            };
        } catch {
            return {
                answers: createEmptyAnswers(),
                finished: false,
                result: null
            };
        }
    }

    function saveState() {
        localStorage.setItem(
            storageKey,
            JSON.stringify({
                answers,
                finished,
                result: finishResult
            })
        );
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function getCardIdByIndex(index) {
        return Number(cardElements[index].dataset.cardId);
    }

    function getSelectedOptionIdsFromCard(cardElement) {
        return Array.from(cardElement.querySelectorAll("input[type='checkbox']"))
            .filter(input => input.checked)
            .map(input => Number(input.value));
    }

    function getOptionText(cardId, optionId) {
        const card = cardById.get(Number(cardId));

        if (!card) {
            return `Вариант ${optionId}`;
        }

        const option = card.options.find(item => Number(item.id) === Number(optionId));

        if (!option) {
            return `Вариант ${optionId}`;
        }

        return option.option_text;
    }

    function optionIdsToTextList(cardId, optionIds) {
        if (!optionIds || optionIds.length === 0) {
            return "<li>Ответ не выбран</li>";
        }

        return optionIds
            .map(optionId => `<li>${escapeHtml(getOptionText(cardId, optionId))}</li>`)
            .join("");
    }

    function showCard(index) {
        if (index < 0 || index >= cardElements.length) {
            return;
        }

        currentIndex = index;

        cardElements.forEach((cardElement, cardIndex) => {
            cardElement.hidden = cardIndex !== currentIndex;
        });

        prevButton.disabled = currentIndex === 0;
        nextButton.disabled = currentIndex === cardElements.length - 1;

        updateCardNumberStates();
    }

    function updateCardNumberStates() {
        const resultByCardId = new Map();

        if (finishResult && finishResult.items) {
            finishResult.items.forEach(item => {
                resultByCardId.set(Number(item.card_id), item.status);
            });
        }

        cardNumberButtons.forEach((button, index) => {
            const cardId = Number(button.dataset.cardId);
            const selected = answers[cardId] || [];

            button.classList.toggle("active", index === currentIndex);

            button.classList.remove(
                "answered",
                "not-answered",
                "correct",
                "incorrect",
                "unanswered"
            );

            if (finished) {
                const status = resultByCardId.get(cardId);

                if (status === "correct") {
                    button.classList.add("correct");
                } else if (status === "incorrect") {
                    button.classList.add("incorrect");
                } else {
                    button.classList.add("unanswered");
                }
            } else {
                if (selected.length > 0) {
                    button.classList.add("answered");
                } else {
                    button.classList.add("not-answered");
                }
            }
        });
    }

    function applyAnswersToPage() {
        cardElements.forEach(cardElement => {
            const cardId = Number(cardElement.dataset.cardId);
            const selectedOptionIds = answers[cardId] || [];

            const checkboxes = cardElement.querySelectorAll("input[type='checkbox']");

            checkboxes.forEach(checkbox => {
                checkbox.checked = selectedOptionIds.includes(Number(checkbox.value));
                checkbox.disabled = finished;
            });
        });
    }

    function bindAnswerSaving() {
        cardElements.forEach(cardElement => {
            const cardId = Number(cardElement.dataset.cardId);
            const checkboxes = cardElement.querySelectorAll("input[type='checkbox']");

            checkboxes.forEach(checkbox => {
                checkbox.addEventListener("change", function () {
                    if (finished) {
                        return;
                    }

                    answers[cardId] = getSelectedOptionIdsFromCard(cardElement);

                    saveState();
                    updateCardNumberStates();
                });
            });
        });
    }

    function showResultPanel() {
        if (!finishResult) {
            resultPanel.hidden = true;
            return;
        }

        resultPanel.hidden = false;

        resultPanel.innerHTML = `
            <h2>Результат</h2>

            <div class="result-grid">
                <div>
                    <strong>${finishResult.total}</strong>
                    <span>Всего</span>
                </div>

                <div>
                    <strong>${finishResult.correct_count}</strong>
                    <span>Правильно</span>
                </div>

                <div>
                    <strong>${finishResult.incorrect_count}</strong>
                    <span>Неправильно</span>
                </div>

                <div>
                    <strong>${finishResult.unanswered_count}</strong>
                    <span>Без ответа</span>
                </div>

                <div>
                    <strong>${finishResult.percent}%</strong>
                    <span>Процент</span>
                </div>
            </div>

            <p class="result-note">
                После завершения варианта ответы изменить нельзя.
                Номера карточек подсвечены: зелёный — верно,
                красный — неверно, серый — нет ответа.
            </p>
        `;
    }

    function showCardFeedback() {
        if (!finishResult || !finishResult.items) {
            return;
        }

        const resultByCardId = new Map(
            finishResult.items.map(item => [Number(item.card_id), item])
        );

        cardElements.forEach(cardElement => {
            const cardId = Number(cardElement.dataset.cardId);
            const resultItem = resultByCardId.get(cardId);
            const feedbackElement = cardElement.querySelector(".card-feedback");

            if (!resultItem || !feedbackElement) {
                return;
            }

            feedbackElement.hidden = false;

            if (resultItem.status === "correct") {
                feedbackElement.className = "card-feedback feedback-correct";
                feedbackElement.innerHTML = `
                    <h3>Верно</h3>
                    <p>Вы выбрали правильный ответ.</p>
                `;
            }

            if (resultItem.status === "incorrect") {
                feedbackElement.className = "card-feedback feedback-incorrect";
                feedbackElement.innerHTML = `
                    <h3>Неверно</h3>

                    <div class="answer-comparison">
                        <div>
                            <h4>Ваш ответ</h4>
                            <ul>
                                ${optionIdsToTextList(cardId, resultItem.selected_option_ids)}
                            </ul>
                        </div>

                        <div>
                            <h4>Правильный ответ</h4>
                            <ul>
                                ${optionIdsToTextList(cardId, resultItem.correct_option_ids)}
                            </ul>
                        </div>
                    </div>
                `;
            }

            if (resultItem.status === "unanswered") {
                feedbackElement.className = "card-feedback feedback-unanswered";
                feedbackElement.innerHTML = `
                    <h3>Нет ответа</h3>

                    <p>Вы не выбрали ни одного варианта.</p>

                    <div class="answer-comparison">
                        <div>
                            <h4>Правильный ответ</h4>
                            <ul>
                                ${optionIdsToTextList(cardId, resultItem.correct_option_ids)}
                            </ul>
                        </div>
                    </div>
                `;
            }

            if (typeof renderMath === "function") {
                renderMath(feedbackElement);
            }
        });
    }

    function applyFinalState() {
        finished = true;

        cardElements.forEach(cardElement => {
            const checkboxes = cardElement.querySelectorAll("input[type='checkbox']");

            checkboxes.forEach(checkbox => {
                checkbox.disabled = true;
            });
        });

        finishButton.disabled = true;
        finishButton.textContent = "Вариант завершён";

        showResultPanel();
        showCardFeedback();
        updateCardNumberStates();

        saveState();
    }

    async function finishAttempt() {
        if (finished) {
            return;
        }

        const confirmed = window.confirm(
            "Завершить вариант? После этого изменить ответы будет нельзя."
        );

        if (!confirmed) {
            return;
        }

        finishButton.disabled = true;
        finishButton.textContent = "Проверяем...";

        try {
            const response = await fetch("/api/finish-attempt", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    mode: attemptData.mode,
                    card_ids: attemptData.card_ids,
                    answers: answers
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Ошибка проверки варианта.");
            }

            finishResult = await response.json();

            applyFinalState();

        } catch (error) {
            alert(error.message);

            finishButton.disabled = false;
            finishButton.textContent = "Завершить вариант";
        }
    }

    function bindNavigation() {
    cardNumberButtons.forEach((button, index) => {
        button.addEventListener("click", function () {
            showCard(index);
        });
    });

    prevButton.addEventListener("click", function () {
        showCard(currentIndex - 1);
    });

    nextButton.addEventListener("click", function () {
        showCard(currentIndex + 1);
    });

    finishButton.addEventListener("click", finishAttempt);

    // Эти ссылки просто уводят пользователя со страницы.
    // Они НЕ должны завершать вариант и НЕ должны отправлять ответы на сервер.
    document.querySelectorAll(".leave-attempt-link").forEach(link => {
        link.addEventListener("click", function () {
            localStorage.removeItem(storageKey);
        });
    });
    }


    const savedState = loadState();

    answers = savedState.answers;
    finished = savedState.finished;
    finishResult = savedState.result;

    bindNavigation();
    bindAnswerSaving();
    applyAnswersToPage();

    if (finished) {
        applyFinalState();
    } else {
        updateCardNumberStates();
    }

    showCard(0);
});