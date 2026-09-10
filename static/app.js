(function () {
  "use strict";

  const goalsList = document.getElementById("goals-list");
  const syncedList = document.getElementById("synced-list");
  const statDone = document.getElementById("stat-done");
  const statStreak = document.getElementById("stat-streak");
  const addForm = document.getElementById("add-goal-form");
  const addInput = document.getElementById("add-goal-input");
  const historyStrip = document.getElementById("history-strip");
  const digestCard = document.getElementById("digest-card");
  const digestBody = document.getElementById("digest-body");
  const toast = document.getElementById("toast");
  if (!goalsList || !addForm) return;

  let pageAlive = true;
  function onPage() {
    return pageAlive && goalsList.isConnected;
  }

  let editingId = null;

  function showToast(message) {
    if (!onPage() || !toast || !message) return;
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
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || t("something_wrong"));
    }
    return response.json();
  }

  function goalRowHTML(goal, index, total) {
    const doneClass = goal.done ? "done" : "";
    const check = goal.done ? "✓" : "";
    return `
      <div class="goal-row" data-id="${goal.id}">
        <div class="reorder-col">
          <button class="reorder-btn" data-dir="up" title="${t("move_up")}" ${index === 0 ? "disabled" : ""}>▲</button>
          <button class="reorder-btn" data-dir="down" title="${t("move_down")}" ${index === total - 1 ? "disabled" : ""}>▼</button>
        </div>
        <button class="goal-toggle ${doneClass}">
          <span class="checkbox">${check}</span>
          <span class="goal-text">${escapeHTML(goal.text)}</span>
        </button>
        <button class="icon-btn edit-btn" title="${t("edit")}">✎</button>
        <button class="icon-btn delete-btn" title="${t("delete")}">✕</button>
      </div>`;
  }

  function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function syncedRowHTML(task) {
    const doneClass = task.done ? "done" : "";
    const check = task.done ? "✓" : "";
    const prefix = task.time ? `${task.time} ` : "";
    return `
      <div class="goal-row synced-row" data-id="${task.id}">
        <button class="goal-toggle synced-toggle ${doneClass}">
          <span class="checkbox">${check}</span>
          <span class="goal-text">${escapeHTML(prefix + task.text)}</span>
        </button>
      </div>`;
  }

  function renderState(state) {
    if (!onPage() || !state) return;
    statDone.textContent = `${state.done_count}/${state.total_count}`;
    statStreak.textContent = `🔥 ${state.streak}`;

    if (state.goals.length === 0) {
      goalsList.innerHTML = `<div class="empty-state">${t("no_goals")}</div>`;
    } else {
      goalsList.innerHTML = state.goals.map((goal, index) => goalRowHTML(goal, index, state.goals.length)).join("");
    }

    // The synced-tasks card only exists in the DOM if there was at least one at page load;
    // if it's there, keep it live too. (A brand-new sync while the page is open needs a reload to appear.)
    if (syncedList && state.synced_tasks) {
      syncedList.innerHTML = state.synced_tasks.map(syncedRowHTML).join("");
    }

    if (state.history) renderHistory(state.history);
    if (state.digest) renderDigest(state.digest);
    touchNavCache();
  }

  const WEEKDAYS = {
    en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    ru: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
  };

  function localToday() {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
  }

  function weekdayLabel(dateStr, fallback) {
    if (fallback) return fallback;
    const date = new Date(dateStr + "T00:00:00");
    if (Number.isNaN(date.getTime())) return "";
    const names = WEEKDAYS[window.LANG] || WEEKDAYS.en;
    return names[(date.getDay() + 6) % 7];
  }

  function renderHistory(data) {
    if (!historyStrip || !data || !data.days) return;
    const maxCount = Math.max(data.total_goals || 1, 1, ...data.days.map((day) => day.count || 0));
    const today = localToday();
    historyStrip.innerHTML = data.days
      .map((day) => {
        const heightPct = day.height || Math.max(6, Math.round((day.count / maxCount) * 100));
        const isToday = day.date === today;
        const hasActivity = day.count > 0;
        const label = weekdayLabel(day.date, day.label);
        return `
          <div class="history-day" title="${escapeHTML(t("history_done", { date: day.date, count: day.count }))}">
            <div class="history-bar ${hasActivity ? "has-activity" : ""} ${isToday ? "is-today" : ""}" style="height:${heightPct}%"></div>
            <div class="history-label">${label}</div>
          </div>`;
      })
      .join("");
  }

  async function refreshHistory() {
    try {
      const data = await api("/api/history");
      if (onPage()) renderHistory(data);
    } catch (error) {
      // history is a nice-to-have; a silent failure here shouldn't block the rest of the app
    }
  }

  function renderDigest(digest) {
    if (!digestCard || !digestBody) return;
    const nothingYet = digest.streak === 0 && digest.goals_completed === 0 && digest.reviews_completed === 0 && !digest.weakest_topic;
    if (nothingYet) {
      digestCard.hidden = true;
      return;
    }
    let html = `
      <div class="digest-row"><span>${t("day_streak")}</span><span class="digest-value">🔥 ${digest.streak}</span></div>
      <div class="digest-row"><span>${t("goals_completed")}</span><span class="digest-value">${digest.goals_completed}</span></div>
      <div class="digest-row"><span>${t("flashcards_reviewed")}</span><span class="digest-value">${digest.reviews_completed}</span></div>
    `;
    if (digest.weakest_topic) {
      html += `<div class="digest-weak-topic">${t("weakest_topic", { topic: escapeHTML(digest.weakest_topic.topic), ease: digest.weakest_topic.avg_ease })}</div>`;
    }
    digestBody.innerHTML = html;
    digestCard.hidden = false;
  }

  function touchNavCache() {
    if (typeof window.__DG_NAV_REMEMBER === "function") window.__DG_NAV_REMEMBER();
  }

  if (syncedList) {
    syncedList.addEventListener("click", async (event) => {
      const row = event.target.closest(".synced-row");
      if (!row || !event.target.closest(".synced-toggle")) return;
      try {
        renderState(await api(`/api/synced-tasks/${row.dataset.id}/toggle`, { method: "POST" }));
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  goalsList.addEventListener("click", async (event) => {
    const row = event.target.closest(".goal-row");
    if (!row) return;
    const goalId = row.dataset.id;

    if (event.target.closest(".goal-toggle")) {
      if (editingId === goalId) return;
      try {
        renderState(await api(`/api/toggle/${goalId}`, { method: "POST" }));
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".delete-btn")) {
      if (!confirm(t("delete_goal_confirm"))) return;
      try {
        renderState(await api(`/api/goals/${goalId}/delete`, { method: "POST" }));
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".reorder-btn")) {
      const button = event.target.closest(".reorder-btn");
      if (button.disabled) return;
      try {
        renderState(await api(`/api/goals/${goalId}/move`, {
          method: "POST",
          body: JSON.stringify({ direction: button.dataset.dir }),
        }));
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".edit-btn")) {
      startEdit(row, goalId);
    }
  });

  function startEdit(row, goalId) {
    editingId = goalId;
    const textEl = row.querySelector(".goal-text");
    const currentText = textEl.textContent;
    const toggleBtn = row.querySelector(".goal-toggle");
    const editBtn = row.querySelector(".edit-btn");
    const deleteBtn = row.querySelector(".delete-btn");

    toggleBtn.style.display = "none";
    editBtn.style.display = "none";
    deleteBtn.style.display = "none";

    const wrapper = document.createElement("div");
    wrapper.style.cssText = "flex:1; display:flex; gap:6px;";
    wrapper.innerHTML = `
      <input type="text" class="goal-edit-input" value="${currentText.replace(/"/g, "&quot;")}">
      <button class="icon-btn save-edit-btn" title="${t("save")}">✓</button>
      <button class="icon-btn cancel-edit-btn" title="${t("cancel")}">✕</button>
    `;
    row.insertBefore(wrapper, editBtn);
    const input = wrapper.querySelector("input");
    input.focus();
    input.select();

    async function save() {
      const newText = input.value.trim();
      if (!newText) {
        showToast(t("goal_empty_error"));
        return;
      }
      try {
        renderState(await api(`/api/goals/${goalId}/edit`, {
          method: "POST",
          body: JSON.stringify({ text: newText }),
        }));
      } catch (error) {
        showToast(error.message);
      } finally {
        editingId = null;
      }
    }

    function cancel() {
      editingId = null;
      wrapper.remove();
      toggleBtn.style.display = "";
      editBtn.style.display = "";
      deleteBtn.style.display = "";
    }

    wrapper.querySelector(".save-edit-btn").addEventListener("click", save);
    wrapper.querySelector(".cancel-edit-btn").addEventListener("click", cancel);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") save();
      if (event.key === "Escape") cancel();
    });
  }

  addForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = addInput.value.trim();
    if (!text) return;
    try {
      renderState(await api("/api/goals", { method: "POST", body: JSON.stringify({ text }) }));
      addInput.value = "";
    } catch (error) {
      showToast(error.message);
    }
  });

  if (historyStrip && historyStrip.children.length === 0) {
    refreshHistory().then(function () {
      if (onPage() && historyStrip) historyStrip.classList.add("is-ready");
    });
  } else if (historyStrip) {
    window.setTimeout(function () {
      if (onPage() && historyStrip) historyStrip.classList.add("is-ready");
    }, 420);
  }

  window._pageCleanup = function () {
    pageAlive = false;
  };
})();
