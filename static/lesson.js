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

  if (!form) return;

  const blocks = Array.from(form.querySelectorAll(".exercise"));
  const checkBtn = document.getElementById("ka-check");
  const feedback = document.getElementById("ka-feedback");
  const kaTitle = document.getElementById("ka-title");
  const kaDetail = document.getElementById("ka-detail");
  const kaIcon = document.getElementById("ka-icon");
  const kaBar = document.getElementById("ka-bar");
  const kaCount = document.getElementById("ka-count");
  const states = blocks.map((_, index) => {
    const saved = ((window.LESSON && window.LESSON.exerciseResults) || []).find((row) => row.index === index);
    return {
      answered: !!(saved && saved.answered),
      correct: !!(saved && saved.correct),
      expected: saved && saved.expected,
      explanation: saved && saved.explanation,
      given: saved && saved.given,
    };
  });
  let current = 0;
  let phase = "answer";
  let retrying = false;
  let busy = false;

  function currentAnswer(block) {
    if (!block) return "";
    if (block.dataset.type === "fill") {
      const input = block.querySelector("input[type='text']");
      return input ? input.value.trim() : "";
    }
    const selected = block.querySelector(".choice-btn.selected");
    return selected ? selected.dataset.value : "";
  }

  function setChoicesEnabled(block, enabled) {
    block.querySelectorAll(".choice-btn").forEach((btn) => {
      btn.disabled = !enabled;
    });
    const input = block.querySelector("input[type='text']");
    if (input) input.readOnly = !enabled;
  }

  function paintChoices(block, state) {
    const buttons = block.querySelectorAll(".choice-btn");
    buttons.forEach((btn) => {
      btn.classList.remove("is-correct", "is-wrong", "selected");
      const mark = btn.querySelector(".choice-mark");
      if (mark) mark.textContent = "";
      if (state && state.given && btn.dataset.value === state.given) btn.classList.add("selected");
      if (state && state.answered && state.expected && btn.dataset.value === state.expected) {
        btn.classList.add("is-correct");
        if (mark) mark.textContent = "✓";
      }
      if (state && state.answered && !state.correct && state.given && btn.dataset.value === state.given) {
        btn.classList.add("is-wrong");
        if (mark) mark.textContent = "✕";
      }
    });
    if (state && state.given && block.dataset.type === "fill") {
      const input = block.querySelector("input[type='text']");
      if (input) input.value = state.given;
    }
  }

  function updateDots() {
    document.querySelectorAll(".ka-dot").forEach((dot) => {
      const index = Number(dot.dataset.dot);
      const state = states[index];
      dot.classList.toggle("is-current", index === current);
      dot.classList.toggle("is-ok", !!(state && state.answered && state.correct));
      dot.classList.toggle("is-bad", !!(state && state.answered && !state.correct));
    });
    if (kaCount) {
      kaCount.textContent = t("question_progress", { current: current + 1, total: blocks.length });
    }
  }

  function showFeedback(ok, expected, explanation) {
    if (!feedback) return;
    feedback.hidden = false;
    if (kaBar) kaBar.classList.toggle("ok", ok);
    if (kaBar) kaBar.classList.toggle("bad", !ok);
    if (kaIcon) kaIcon.textContent = ok ? "✓" : "✕";
    if (kaTitle) kaTitle.textContent = ok ? t("correct_exclaim") : t("incorrect_exclaim");
    const extra = explanation ? ` ${explanation}` : "";
    if (kaDetail) {
      kaDetail.textContent = ok ? extra.trim() : `${t("answer_expected", { expected })}${extra}`.trim();
    }
    const explain = blocks[current].querySelector(".explain");
    if (explain) {
      explain.hidden = false;
      explain.textContent = extra.trim();
    }
  }

  function hideFeedback() {
    if (feedback) feedback.hidden = true;
    if (kaBar) kaBar.classList.remove("ok", "bad");
    const explain = blocks[current] && blocks[current].querySelector(".explain");
    if (explain) {
      explain.hidden = true;
      explain.textContent = "";
    }
  }

  function showExercise(index) {
    current = index;
    phase = states[index] && states[index].answered && !retrying ? "next" : "answer";
    retrying = false;
    blocks.forEach((block, i) => {
      block.hidden = i !== index;
    });
    const block = blocks[index];
    const state = states[index];
    paintChoices(block, state && state.answered ? state : { given: currentAnswer(block) });
    setChoicesEnabled(block, !(state && state.answered));
    if (state && state.answered) {
      showFeedback(state.correct, state.expected, state.explanation);
      if (checkBtn) {
        const allDone = states.every((item) => item.answered && item.correct);
        checkBtn.textContent = allDone ? t("all_correct") : t(state.correct ? "next_question" : "got_it");
      }
    } else {
      hideFeedback();
      if (checkBtn) checkBtn.textContent = t("check");
    }
    updateDots();
  }

  function nextIndex() {
    const unanswered = states.findIndex((state) => !state.answered);
    if (unanswered !== -1) return unanswered;
    const missed = states.findIndex((state) => state.answered && !state.correct);
    if (missed !== -1) return missed;
    return -1;
  }

  function applyProgress(result) {
    const score = document.getElementById("exercise-score");
    const correct = result.correct || 0;
    const total = result.total || blocks.length;
    if (score) score.textContent = `${correct}/${total}`;
    markCheck(2, !!(result.progress && result.progress.completed), `${correct}/${total}`);
    if (result.progress && result.progress.completed && nextLesson) nextLesson.hidden = false;
  }

  blocks.forEach((block) => {
    block.addEventListener("click", (event) => {
      const btn = event.target.closest(".choice-btn");
      if (!btn || btn.disabled || phase !== "answer") return;
      block.querySelectorAll(".choice-btn").forEach((choice) => choice.classList.remove("selected"));
      btn.classList.add("selected");
    });
  });

  const firstOpen = states.findIndex((state) => !state.answered);
  showExercise(firstOpen === -1 ? 0 : firstOpen);
  if (window.LESSON && window.LESSON.exerciseResults) {
    const answered = states.filter((state) => state.answered).length;
    const correct = states.filter((state) => state.correct).length;
    applyProgress({ correct, total: blocks.length, progress: { completed: answered === blocks.length && correct === blocks.length } });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const block = blocks[current];
    if (phase === "next") {
      if (states.every((state) => state.answered && state.correct)) {
        showToast(t("all_correct"));
        return;
      }
      if (states.every((state) => state.answered) && states.some((state) => !state.correct)) {
        let nextMissed = states.findIndex((state, i) => i > current && !state.correct);
        if (nextMissed === -1) nextMissed = states.findIndex((state) => !state.correct);
        if (nextMissed !== -1) {
          if (nextMissed <= current) showToast(t("try_missed"));
          const nextBlock = blocks[nextMissed];
          states[nextMissed] = { answered: false, correct: false };
          nextBlock.querySelectorAll(".choice-btn").forEach((btn) => {
            btn.classList.remove("selected", "is-correct", "is-wrong");
            const mark = btn.querySelector(".choice-mark");
            if (mark) mark.textContent = "";
          });
          const input = nextBlock.querySelector("input[type='text']");
          if (input) input.value = "";
          retrying = true;
          showExercise(nextMissed);
          return;
        }
      }
      const nxt = nextIndex();
      if (nxt === -1) {
        showToast(t("all_correct"));
        return;
      }
      showExercise(nxt);
      return;
    }

    const answer = currentAnswer(block);
    if (!answer) {
      showToast(block.dataset.type === "fill" ? t("type_answer") : t("choose_answer"));
      return;
    }
    busy = true;
    if (checkBtn) checkBtn.disabled = true;
    try {
      const result = await api(window.LESSON.exercisesUrl, {
        method: "POST",
        body: JSON.stringify({ index: current, answer }),
      });
      const checked = result.checked || {};
      states[current] = {
        answered: true,
        correct: !!checked.correct,
        expected: checked.expected,
        explanation: checked.explanation,
        given: answer,
      };
      paintChoices(block, states[current]);
      setChoicesEnabled(block, false);
      showFeedback(!!checked.correct, checked.expected, checked.explanation);
      phase = "next";
      const allDone = states.every((state) => state.answered && state.correct);
      if (checkBtn) {
        checkBtn.textContent = allDone ? t("all_correct") : t(checked.correct ? "next_question" : "got_it");
      }
      applyProgress(result);
      if (allDone) showToast(t("all_correct"));
    } catch (error) {
      showToast(error.message);
    } finally {
      busy = false;
      if (checkBtn) checkBtn.disabled = false;
    }
  });
})();
