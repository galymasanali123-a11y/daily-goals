(function () {
  "use strict";

  const goalsList = document.getElementById("goals-list");
  const statDone = document.getElementById("stat-done");
  const statStreak = document.getElementById("stat-streak");
  const addForm = document.getElementById("add-goal-form");
  const addInput = document.getElementById("add-goal-input");
  const historyStrip = document.getElementById("history-strip");
  const toast = document.getElementById("toast");

  let editingId = null;

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

  function goalRowHTML(goal, index, total) {
    const doneClass = goal.done ? "done" : "";
    const check = goal.done ? "✓" : "";
    return `
      <div class="goal-row" data-id="${goal.id}">
        <div class="reorder-col">
          <button class="reorder-btn" data-dir="up" title="Move up" ${index === 0 ? "disabled" : ""}>▲</button>
          <button class="reorder-btn" data-dir="down" title="Move down" ${index === total - 1 ? "disabled" : ""}>▼</button>
        </div>
        <button class="goal-toggle ${doneClass}">
          <span class="checkbox">${check}</span>
          <span class="goal-text">${escapeHTML(goal.text)}</span>
        </button>
        <button class="icon-btn edit-btn" title="Edit">✎</button>
        <button class="icon-btn delete-btn" title="Delete">✕</button>
      </div>`;
  }

  function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderState(state) {
    statDone.textContent = `${state.done_count}/${state.total_count}`;
    statStreak.textContent = `🔥 ${state.streak}`;

    if (state.goals.length === 0) {
      goalsList.innerHTML = '<div class="empty-state">No goals yet — add one below to get started.</div>';
      return;
    }
    goalsList.innerHTML = state.goals.map((goal, index) => goalRowHTML(goal, index, state.goals.length)).join("");
  }

  function renderHistory(data) {
    const maxCount = Math.max(data.total_goals, 1, ...data.days.map((day) => day.count));
    const today = new Date().toISOString().slice(0, 10);
    historyStrip.innerHTML = data.days
      .map((day) => {
        const heightPct = Math.max(6, Math.round((day.count / maxCount) * 100));
        const isToday = day.date === today;
        const hasActivity = day.count > 0;
        const label = new Date(day.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" }).slice(0, 2);
        return `
          <div class="history-day" title="${day.date}: ${day.count} done">
            <div class="history-bar ${hasActivity ? "has-activity" : ""} ${isToday ? "is-today" : ""}" style="height:${heightPct}%"></div>
            <div class="history-label">${label}</div>
          </div>`;
      })
      .join("");
  }

  async function refreshHistory() {
    try {
      renderHistory(await api("/api/history"));
    } catch (error) {
      // history is a nice-to-have; a silent failure here shouldn't block the rest of the app
    }
  }

  goalsList.addEventListener("click", async (event) => {
    const row = event.target.closest(".goal-row");
    if (!row) return;
    const goalId = row.dataset.id;

    if (event.target.closest(".goal-toggle")) {
      if (editingId === goalId) return;
      try {
        renderState(await api(`/api/toggle/${goalId}`, { method: "POST" }));
        refreshHistory();
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".delete-btn")) {
      if (!confirm("Delete this goal?")) return;
      try {
        renderState(await api(`/api/goals/${goalId}/delete`, { method: "POST" }));
        refreshHistory();
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
      <button class="icon-btn save-edit-btn" title="Save">✓</button>
      <button class="icon-btn cancel-edit-btn" title="Cancel">✕</button>
    `;
    row.insertBefore(wrapper, editBtn);
    const input = wrapper.querySelector("input");
    input.focus();
    input.select();

    async function save() {
      const newText = input.value.trim();
      if (!newText) {
        showToast("Goal text can't be empty.");
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
      refreshHistory();
    } catch (error) {
      showToast(error.message);
    }
  });

  refreshHistory();
})();
