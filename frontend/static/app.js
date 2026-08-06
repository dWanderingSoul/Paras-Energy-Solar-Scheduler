const API = "";
let editorKey = localStorage.getItem("editorKey") || null;
let currentView = "calendar";
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth() + 1; // 1-12
let selectedDate = null;
let selectedTaskId = null;
let trackerRange = "weekly"; // or "monthly"

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---------- Nav ----------
$("#nav-calendar").onclick = () => switchView("calendar");
$("#nav-tracker").onclick = () => switchView("tracker");

function switchView(view) {
  currentView = view;
  $$(".nav-btn.active").forEach(b => b.classList.remove("active"));
  $(view === "calendar" ? "#nav-calendar" : "#nav-tracker").classList.add("active");
  $$(".view").forEach(v => v.classList.remove("active"));
  $(view === "calendar" ? "#view-calendar" : "#view-tracker").classList.add("active");
  if (view === "tracker" && !$("#tracker-task-list").dataset.loaded) loadTrackerTasks();
}

// ---------- Editor unlock ----------
$("#unlock-btn").onclick = () => {
  const key = prompt("Enter editor key:");
  if (key) {
    editorKey = key;
    localStorage.setItem("editorKey", key);
    $("#editor-status").textContent = "Editor mode";
  }
};
if (editorKey) $("#editor-status").textContent = "Editor mode";

// ---------- Calendar ----------
async function renderCalendar() {
  const label = new Date(calYear, calMonth - 1, 1).toLocaleString("default", { month: "long", year: "numeric" });
  $("#month-label").textContent = label;

  const summary = await fetch(`${API}/api/calendar/month/${calYear}/${calMonth}`).then(r => r.json());

  const grid = $("#calendar-grid");
  grid.innerHTML = "";
  ["Mo","Tu","We","Th","Fr","Sa","Su"].forEach(d => {
    const el = document.createElement("div");
    el.className = "cal-weekday";
    el.textContent = d;
    grid.appendChild(el);
  });

  const firstDay = new Date(calYear, calMonth - 1, 1);
  const startOffset = (firstDay.getDay() + 6) % 7; // Monday=0
  const daysInMonth = new Date(calYear, calMonth, 0).getDate();

  for (let i = 0; i < startOffset; i++) {
    const el = document.createElement("div");
    el.className = "cal-day empty";
    grid.appendChild(el);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${calYear}-${String(calMonth).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
    const info = summary[dateStr];
    const el = document.createElement("div");
    el.className = "cal-day";
    el.dataset.date = dateStr;
    if (info) {
      el.classList.add("has-tasks");
      if (info.done === info.total) el.classList.add("all-done");
    }
    if (dateStr === selectedDate) el.classList.add("selected");
    el.innerHTML = `<span>${day}</span>` + (info ? `<span class="badge">${info.done}/${info.total}</span>` : "");
    el.onclick = () => selectDate(dateStr);
    grid.appendChild(el);
  }
}

async function selectDate(dateStr) {
  selectedDate = dateStr;
  renderCalendar();
  $("#daily-title").textContent = `Daily Activities — ${dateStr}`;
  const data = await fetch(`${API}/api/calendar/${dateStr}`).then(r => r.json());
  const list = $("#daily-list");
  list.innerHTML = "";
  if (data.occurrences.length === 0) {
    list.innerHTML = `<li><em>No scheduled tasks for this date.</em></li>`;
    return;
  }
  data.occurrences.forEach(occ => list.appendChild(occurrenceRow(occ, () => selectDate(dateStr))));
}

$("#prev-month").onclick = () => { calMonth--; if (calMonth < 1) { calMonth = 12; calYear--; } renderCalendar(); };
$("#next-month").onclick = () => { calMonth++; if (calMonth > 12) { calMonth = 1; calYear++; } renderCalendar(); };

// ---------- Task Tracker ----------
async function loadTrackerTasks() {
  const tasks = await fetch(`${API}/api/tracker/tasks`).then(r => r.json());
  const list = $("#tracker-task-list");
  list.dataset.loaded = "1";
  list.innerHTML = "";
  tasks.forEach(t => {
    const li = document.createElement("li");
    li.innerHTML = `<div class="task-cat">${t.category}</div><div class="task-name">${t.task_name}</div>`;
    li.onclick = () => selectTask(t.id, t.task_name, li);
    list.appendChild(li);
  });
}

function selectTask(taskId, name, liEl) {
  selectedTaskId = taskId;
  $$("#tracker-task-list li.selected").forEach(el => el.classList.remove("selected"));
  liEl.classList.add("selected");
  $("#tracker-title").textContent = name;
  loadTrackerDetail();
}

$("#range-weekly").onclick = () => setRange("weekly");
$("#range-monthly").onclick = () => setRange("monthly");
function setRange(r) {
  trackerRange = r;
  $("#range-weekly").classList.toggle("active", r === "weekly");
  $("#range-monthly").classList.toggle("active", r === "monthly");
  if (selectedTaskId) loadTrackerDetail();
}

async function loadTrackerDetail() {
  if (!selectedTaskId) return;
  // "from the date I clicked on the task tracker" - defaults to today,
  // but reuses the calendar's selected date if one was picked there.
  const fromDate = selectedDate || new Date().toISOString().slice(0, 10);
  const data = await fetch(
    `${API}/api/tracker/task/${selectedTaskId}/${trackerRange}?from_date=${fromDate}`
  ).then(r => r.json());

  $("#progress-summary").innerHTML = `
    <div class="progress-stat"><div class="num">${data.progress_percent}%</div><div class="label">Progress</div></div>
    <div class="progress-stat"><div class="num">${data.completed}/${data.total}</div><div class="label">Completed</div></div>
    <div class="progress-stat missing"><div class="num">${data.missing}</div><div class="label">Missing</div></div>
  `;

  const list = $("#tracker-occurrences");
  list.innerHTML = "";
  data.occurrences.forEach(occ => list.appendChild(occurrenceRow(occ, loadTrackerDetail)));
}

// ---------- Shared occurrence row (checkbox to mark done) ----------
function occurrenceRow(occ, onChanged) {
  const li = document.createElement("li");
  li.innerHTML = `
    <div class="task-row">
      <div>
        <div class="task-cat">${occ.task.category} — ${occ.scheduled_date}</div>
        <div class="task-name">${occ.task.task_name}</div>
        <div class="task-detail">${occ.detail || occ.task.activity}</div>
      </div>
      <input type="checkbox" class="done-toggle" ${occ.is_done ? "checked" : ""} />
    </div>
  `;
  const checkbox = li.querySelector(".done-toggle");
  checkbox.onchange = async () => {
    if (!editorKey) {
      alert("Unlock editing first (top right) to mark tasks done.");
      checkbox.checked = !checkbox.checked;
      return;
    }
    const res = await fetch(`${API}/api/tracker/occurrence/${occ.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Editor-Key": editorKey },
      body: JSON.stringify({ is_done: checkbox.checked }),
    });
    if (res.status === 401) {
      alert("Editor key incorrect. Try unlocking again.");
      localStorage.removeItem("editorKey");
      editorKey = null;
      checkbox.checked = !checkbox.checked;
      return;
    }
    onChanged();
  };
  return li;
}

// ---------- Init ----------
renderCalendar();
