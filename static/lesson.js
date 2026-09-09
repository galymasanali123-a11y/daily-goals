(function () {
  "use strict";

  const toast = document.getElementById("toast");
  const grammarBtn = document.getElementById("mark-grammar");
  const cardsBtn = document.getElementById("add-cards");
  const form = document.getElementById("exercise-form");

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  async function api(path, options) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error(t("not_authenticated"));
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || t("something_wrong"));
    return body;
  }

  if (grammarBtn) {
    grammarBtn.addEventListener("click", async () => {
      try {
        await api(window.LESSON.grammarUrl, { method: "POST", body: "{}" });
        grammarBtn.disabled = true;
        grammarBtn.textContent = t("already_read");
        showToast(t("grammar_marked"));
        const item = document.querySelector(".checklist .check-item");
        if (item) {
          item.classList.add("done");
          const span = item.querySelector("span");
          if (span) span.textContent = t("done");
        }
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (cardsBtn) {
    cardsBtn.addEventListener("click", async () => {
      try {
        const result = await api(window.LESSON.cardsUrl, { method: "POST", body: "{}" });
        showToast(result.added ? t("cards_added", { n: result.added }) : t("cards_already"));
        if (result.added || result.progress) {
          const items = document.querySelectorAll(".checklist .check-item");
          if (items[1]) {
            items[1].classList.add("done");
            const span = items[1].querySelector("span");
            if (span) span.textContent = t("done");
          }
        }
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const answers = {};
      form.querySelectorAll(".exercise").forEach((block) => {
        const index = block.dataset.index;
        const chosen = block.querySelector("input[type='radio']:checked, input[type='text']");
        answers[index] = chosen ? chosen.value : "";
      });
      try {
        const result = await api(window.LESSON.exercisesUrl, {
          method: "POST",
          body: JSON.stringify({ answers }),
        });
        result.results.forEach((item) => {
          const block = form.querySelector(`.exercise[data-index="${item.index}"]`);
          if (!block) return;
          block.classList.toggle("ok", item.correct);
          block.classList.toggle("bad", !item.correct);
          const explain = block.querySelector(".explain");
          if (explain) {
            explain.hidden = false;
            explain.textContent = (item.correct ? t("answer_correct") : t("answer_expected", { expected: item.expected })) + (item.explanation || "");
          }
        });
        showToast(t("score", { correct: result.correct, total: result.total }));
      } catch (error) {
        showToast(error.message);
      }
    });
  }
})();
