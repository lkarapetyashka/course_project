function renderMath(rootElement = document.body) {
    if (typeof renderMathInElement !== "function") {
        return;
    }

    renderMathInElement(rootElement, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "$", right: "$", display: false },
            { left: "\\(", right: "\\)", display: false }
        ],
        throwOnError: false
    });
}

document.addEventListener("DOMContentLoaded", function () {
    renderMath(document.body);
});