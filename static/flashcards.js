(function () {
  "use strict";

  const topicToggle = document.getElementById("topic-toggle");
  const topicFilter = document.getElementById("topic-filter");
  const emptyCards = document.getElementById("empty-cards");
  const importDeckCard = document.getElementById("import-deck-card");
  const importDeckForm = document.getElementById("import-deck-form");
  const importDeckCode = document.getElementById("import-deck-code");
  const allCaughtUp = document.getElementById("all-caught-up");
  const studyArea = document.getElementById("study-area");
  const studyProgress = document.getElementById("study-progress");
  const studyTopic = document.getElementById("study-topic");
  const studyQuestion = document.getElementById("study-question");
  const studyAnswer = document.getElementById("study-answer");
  const studyExample = document.getElementById("study-example");
  const revealBtn = document.getElementById("reveal-btn");
  const studyActions = document.getElementById("study-actions");
  const toast = document.getElementById("toast");
  const countsBox = document.getElementById("anki-counts");
  const srsForm = document.getElementById("srs-form");
  const enableNotify = document.getElementById("enable-notify");

  const params = new URLSearchParams(window.location.search);
  let allCards = [];
  let selectedTopic = params.get("topic") || "All";
  let queue = [];
  let queueTotal = 0;
  let revealed = false;
  let topicFilterExpanded = false;
  let settings = { new_per_day: 20, reviews_per_day: 200, notify_enabled: 1, notify_hour: 9 };
  let wakeTimer = null;

  function showToast(message) {
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
      throw new Error("not authenticated");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || "Something went wrong.");
    }
    return response.json();
  }

  function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderTopicFilter(topics) {
    const chips = ["All", ...topics];
    if (selectedTopic !== "All" && !topics.includes(selectedTopic)) {
      chips.push(selectedTopic);
    }
    topicFilter.innerHTML = chips
      .map((topic) => `<span class="topic-chip ${topic === selectedTopic ? "active" : ""}" data-topic="${escapeHTML(topic)}">${escapeHTML(topic)}</span>`)
      .join("");
    updateTopicToggleLabel();
  }

  function updateTopicToggleLabel() {
    if (!topicToggle) return;
    const arrow = topicFilterExpanded ? "▴" : "▾";
    topicToggle.textContent = `📂 Topic: ${selectedTopic} ${arrow}`;
  }

  function setTopicFilterExpanded(expanded) {
    topicFilterExpanded = expanded;
    topicFilter.style.display = expanded ? "" : "none";
    updateTopicToggleLabel();
  }

  if (topicToggle) {
    topicToggle.addEventListener("click", () => {
      setTopicFilterExpanded(!topicFilterExpanded);
    });
  }

  topicFilter.addEventListener("click", (event) => {
    const chip = event.target.closest(".topic-chip");
    if (!chip) return;
    selectedTopic = chip.dataset.topic;
    renderTopicFilter([...new Set(allCards.map((card) => card.topic))].sort());
    buildQueue();
    // Picking a topic collapses the list again -- a quick switch, not a permanent panel.
    setTopicFilterExpanded(false);
  });

  function renderCounts(counts) {
    if (!countsBox || !counts) return;
    countsBox.hidden = false;
    document.getElementById("count-new").textContent = `${counts.new || 0} new`;
    document.getElementById("count-learn").textContent = `${counts.learning || 0} learn`;
    document.getElementById("count-review").textContent = `${counts.review || 0} review`;
  }

  function applyPreviews(card) {
    const previews = (card && card.previews) || {};
    studyActions.querySelectorAll("[data-preview]").forEach((el) => {
      el.textContent = previews[el.dataset.preview] || "";
    });
  }

  function fillSettings(data) {
    if (!data) return;
    settings = { ...settings, ...data };
    const newInput = document.getElementById("new-per-day");
    const reviewInput = document.getElementById("reviews-per-day");
    const hourInput = document.getElementById("notify-hour");
    const notifySelect = document.getElementById("notify-enabled");
    if (newInput) newInput.value = settings.new_per_day;
    if (reviewInput) reviewInput.value = settings.reviews_per_day;
    if (hourInput) hourInput.value = settings.notify_hour;
    if (notifySelect) notifySelect.value = String(settings.notify_enabled);
  }

  function maybeNotify(dueCount) {
    if (!dueCount || !settings.notify_enabled) return;
    const today = new Date().toISOString().slice(0, 10);
    try {
      if (localStorage.getItem("card-nudge-date") === today) return;
    } catch (error) {}
    const hour = new Date().getHours();
    if (hour < Number(settings.notify_hour || 0)) return;
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    try {
      new Notification("Карточки на сегодня", {
        body: `${dueCount} карточек ждут повторения.`,
        icon: "/static/icons/icon-192.png",
      });
      localStorage.setItem("card-nudge-date", today);
    } catch (error) {}
  }

  function scheduleWake(waitingAt) {
    clearTimeout(wakeTimer);
    if (!waitingAt || !waitingAt.length) return;
    const soonest = waitingAt
      .map((value) => new Date(value).getTime())
      .filter((value) => !Number.isNaN(value))
      .sort((a, b) => a - b)[0];
    if (!soonest) return;
    const delay = Math.max(1000, soonest - Date.now() + 400);
    wakeTimer = setTimeout(() => load(), Math.min(delay, 10 * 60 * 1000));
  }

  function buildQueue() {
    const dueCards = allCards.filter((card) => card.due_today);
    queue = selectedTopic === "All" ? dueCards : dueCards.filter((card) => card.topic === selectedTopic);
    queueTotal = queue.length;
    showNextCard();
  }

  function showNextCard() {
    revealed = false;
    studyAnswer.style.display = "none";
    studyExample.style.display = "none";
    revealBtn.style.display = "";
    studyActions.style.display = "none";

    if (allCards.length === 0) {
      emptyCards.style.display = "";
      importDeckCard.style.display = "";
      studyArea.style.display = "none";
      allCaughtUp.style.display = "none";
      return;
    }
    emptyCards.style.display = "none";
    importDeckCard.style.display = "none";

    if (queue.length === 0) {
      studyArea.style.display = "none";
      allCaughtUp.style.display = "";
      return;
    }
    allCaughtUp.style.display = "none";
    studyArea.style.display = "";

    const card = queue[0];
    studyProgress.textContent = `${queueTotal - queue.length + 1} of ${queueTotal}`;
    studyTopic.textContent = card.topic;
    studyQuestion.textContent = card.question;
    studyAnswer.textContent = card.answer;
    studyExample.textContent = card.example || "";
    applyPreviews(card);
  }

  revealBtn.addEventListener("click", () => {
    revealed = true;
    studyAnswer.style.display = "";
    if (queue[0] && queue[0].example) studyExample.style.display = "";
    revealBtn.style.display = "none";
    studyActions.style.display = "grid";
  });

  async function submitReview(confidence) {
    if (!revealed || queue.length === 0) return;
    const card = queue[0];
    try {
      await api(`/api/cards/${card.id}/review`, { method: "POST", body: JSON.stringify({ confidence }) });
    } catch (error) {
      showToast(error.message);
      return;
    }
    await load();
  }

  studyActions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-confidence]");
    if (!button) return;
    submitReview(parseInt(button.dataset.confidence, 10));
  });

  document.addEventListener("keydown", (event) => {
    if (!revealed) {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        revealBtn.click();
      }
      return;
    }
    const map = { 1: 1, 2: 2, 3: 3, 4: 4 };
    if (map[event.key]) submitReview(map[event.key]);
  });

  importDeckForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = importDeckCode.value.trim();
    if (!code) return;
    try {
      const result = await api("/api/import-shared-deck", { method: "POST", body: JSON.stringify({ code }) });
      showToast(`Added ${result.card_count} cards from ${result.label}.`);
      importDeckCode.value = "";
      await load();
    } catch (error) {
      showToast(error.message);
    }
  });

  if (srsForm) {
    srsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const saved = await api("/api/srs-settings", {
          method: "POST",
          body: JSON.stringify({
            new_per_day: document.getElementById("new-per-day").value,
            reviews_per_day: document.getElementById("reviews-per-day").value,
            notify_hour: document.getElementById("notify-hour").value,
            notify_enabled: document.getElementById("notify-enabled").value,
          }),
        });
        fillSettings(saved);
        showToast("Лимиты сохранены.");
        await load();
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (enableNotify) {
    enableNotify.addEventListener("click", async () => {
      if (!("Notification" in window)) {
        showToast("Этот браузер не умеет уведомления.");
        return;
      }
      const permission = await Notification.requestPermission();
      showToast(permission === "granted" ? "Напоминания разрешены." : "Разрешение не выдано.");
    });
  }

  async function load() {
    try {
      const data = await api("/api/cards");
      allCards = data.cards;
      fillSettings(data.settings);
      renderCounts(data.counts);
      renderTopicFilter(data.topics);
      buildQueue();
      scheduleWake(data.waiting_at);
      maybeNotify(data.due_count);
    } catch (error) {
      showToast(error.message);
    }
  }

  load();
})();
