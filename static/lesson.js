(function () {
  "use strict";

  const toast = document.getElementById("toast");
  const grammarBtn = document.getElementById("mark-grammar");
  const cardsBtn = document.getElementById("add-cards");
  const form = document.getElementById("exercise-form");
  const tabs = document.getElementById("step-tabs");
  const nextBtn = document.getElementById("next-step");
  const prevBtn = document.getElementById("prev-step");
  const nextLesson = document.getElementById("next-lesson");
  let step = (window.LESSON && window.LESSON.startStep) || 0;
  const maxStep = 2;

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

  function showStep(next) {
    step = Math.max(0, Math.min(maxStep, next));
    document.querySelectorAll("[data-step-panel]").forEach((panel) => {
      panel.hidden = Number(panel.getAttribute("data-step-panel")) !== step;
    });
    if (tabs) {
      tabs.querySelectorAll("[data-step]").forEach((chip) => {
        chip.classList.toggle("active", Number(chip.dataset.step) === step);
      });
    }
    if (prevBtn) prevBtn.hidden = step === 0;
    if (nextBtn) nextBtn.hidden = step === maxStep;
  }

  if (tabs) {
    tabs.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-step]");
      if (!chip) return;
      showStep(Number(chip.dataset.step));
    });
  }
  if (nextBtn) nextBtn.addEventListener("click", () => showStep(step + 1));
  if (prevBtn) prevBtn.addEventListener("click", () => showStep(step - 1));
  showStep(step);

  function markCheck(index, done, label) {
    const items = document.querySelectorAll(".checklist .check-item");
    const item = items[index];
    if (!item) return;
    item.classList.toggle("done", done);
    const span = item.querySelector("span");
    if (span && label) span.textContent = label;
  }

  if (grammarBtn) {
    grammarBtn.addEventListener("click", async () => {
      try {
        const result = await api(window.LESSON.grammarUrl, { method: "POST", body: "{}" });
        grammarBtn.disabled = true;
        grammarBtn.textContent = t("already_read");
        markCheck(0, true, t("done"));
        showToast(t("grammar_marked"));
        if (result.completed && nextLesson) nextLesson.hidden = false;
        showStep(1);
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
        cardsBtn.disabled = true;
        cardsBtn.textContent = t("already_in_deck");
        markCheck(1, true, t("done"));
        if (result.progress && result.progress.completed && nextLesson) nextLesson.hidden = false;
        showStep(2);
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (form) {
    const blocks = Array.from(form.querySelectorAll(".exercise"));
    let current = 0;
    function showExercise(index) {
      blocks.forEach((block, i) => {
        block.hidden = i !== index;
      });
    }
    showExercise(current);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
        const answers = {};
        form.querySelectorAll(".exercise").forEach((block) => {
          const index = block.dataset.index;
          const chosen = block.querySelector("input[type='radio']:checked, input[type='text']");
          answers[index] = chosen ? chosen.value : "";
        });
        if (current < blocks.length - 1) {
          current += 1;
          showExercise(current);
          return;
        }
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
        const score = document.getElementById("exercise-score");
        if (score) score.textContent = `${result.correct}/${result.total}`;
        markCheck(2, result.correct === result.total && result.total > 0, `${result.correct}/${result.total}`);
        showToast(t("score", { correct: result.correct, total: result.total }));
        if (result.progress && result.progress.completed && nextLesson) nextLesson.hidden = false;
      } catch (error) {
        showToast(error.message);
      }
    });
  }
})();
