const OFFICES = [
  { id: "morning", label: "Morning", time: "7:30" },
  { id: "midday", label: "Midday", time: "11:30" },
  { id: "evening", label: "Evening", time: "17:30" },
  { id: "compline", label: "Compline", time: "22:00" },
];

const WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

const THEME_COLORS = {
  chapel: "#1a1612",
  clear: "#f4f1ea",
  spacegray: "#181c24",
};

const state = {
  date: todayInChicago(),
  office: "morning",
  data: null,
  theme: migrateTheme(localStorage.getItem("do-theme") || "chapel"),
  size: localStorage.getItem("do-size") || "md",
  useSeason: localStorage.getItem("do-season") === "1",
};

function migrateTheme(theme) {
  return ["parchment", "cream", "solarized"].includes(theme) ? "spacegray" : theme;
}

async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  return res.json();
}

async function boot() {
  const [lectionary, midday, compline, bible, audio, sentences, corpus, daily, echoes, benedictions] = await Promise.all([
    loadJSON("data/lectionary.json"),
    loadJSON("data/midday.json"),
    loadJSON("data/compline.json"),
    loadJSON("data/bsb.json"),
    loadJSON("data/audio.json").catch(() => ({})),
    loadJSON("data/sentences.json"),
    loadJSON("data/confessions/corpus.json"),
    loadJSON("data/confessions/westminster_daily.json"),
    loadJSON("data/confessions/echoes.json"),
    loadJSON("data/confessions/benedictions.json"),
  ]);
  state.data = {
    lectionary,
    midday,
    compline,
    bible,
    audio,
    sentences,
    corpus,
    daily,
    echoes,
    benedictions: benedictions.items,
  };
  readAppearanceQuery();
  readHash();
  bind();
  applyAppearance();
  render();
}

function readAppearanceQuery() {
  const params = new URLSearchParams(location.search);
  if (["chapel", "clear", "spacegray", "solarized", "cream", "parchment"].includes(params.get("theme"))) {
    state.theme = migrateTheme(params.get("theme"));
  }
  if (["sm", "md", "lg"].includes(params.get("size"))) {
    state.size = params.get("size");
  }
  if (params.get("season") === "1") state.useSeason = true;
  if (params.get("season") === "0") state.useSeason = false;
}

function readHash() {
  const raw = location.hash.replace(/^#/, "");
  if (!raw) return;
  const [datePart, officePart] = raw.split("/");
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    state.date = parseISODate(datePart);
  }
  if (OFFICES.some((o) => o.id === officePart)) {
    state.office = officePart;
  }
}

function writeHash() {
  const next = `#${iso(state.date)}/${state.office}`;
  if (location.hash !== next) {
    history.replaceState(null, "", next);
  }
}

function bind() {
  document.getElementById("prev-day").addEventListener("click", () => shiftDay(-1));
  document.getElementById("next-day").addEventListener("click", () => shiftDay(1));
  document.getElementById("today").addEventListener("click", () => {
    state.date = todayInChicago();
    render();
  });
  document.getElementById("date-input").addEventListener("change", (event) => {
    if (event.target.value) {
      state.date = parseISODate(event.target.value);
      render();
    }
  });
  document.getElementById("office-nav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-office]");
    if (!button) return;
    state.office = button.dataset.office;
    render();
  });
  window.addEventListener("hashchange", () => {
    readHash();
    render();
  });
  document.querySelectorAll("[data-theme]").forEach((button) => {
    button.addEventListener("click", () => {
      state.theme = button.dataset.theme;
      localStorage.setItem("do-theme", state.theme);
      applyAppearance();
    });
  });
  document.querySelectorAll("[data-size]").forEach((button) => {
    button.addEventListener("click", () => {
      state.size = button.dataset.size;
      localStorage.setItem("do-size", state.size);
      applyAppearance();
    });
  });
  document.getElementById("season-toggle").addEventListener("click", () => {
    state.useSeason = !state.useSeason;
    localStorage.setItem("do-season", state.useSeason ? "1" : "0");
    applyAppearance();
  });
}

function applyAppearance() {
  const root = document.documentElement;
  if (localStorage.getItem("do-theme") !== state.theme) {
    localStorage.setItem("do-theme", state.theme);
  }
  root.dataset.theme = state.theme;
  root.dataset.size = state.size;
  root.classList.toggle("use-season", state.useSeason);
  const info = liturgicalDay(state.date);
  root.dataset.color = info.color || "green";
  document.querySelectorAll("[data-theme]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.theme === state.theme);
  });
  document.querySelectorAll("[data-size]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.size === state.size);
  });
  const seasonBtn = document.getElementById("season-toggle");
  seasonBtn.setAttribute("aria-pressed", state.useSeason ? "true" : "false");
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute("content", THEME_COLORS[state.theme] || THEME_COLORS.chapel);
}

function shiftDay(delta) {
  state.date = addDays(state.date, delta);
  render();
}

function lookup() {
  const key = iso(state.date).slice(5);
  const day = state.data.lectionary.days[key];
  const weekday = WEEKDAY_KEYS[(state.date.getDay() + 6) % 7];
  return {
    day,
    midday: state.data.midday.lessons[weekday] || [],
    compline: state.data.compline.lessons[weekday] || [],
    weekday,
    audio: (state.data.audio[iso(state.date)] || {}),
  };
}

function sentenceFor(d, officeId) {
  const list = state.data.sentences?.sentences;
  if (!list?.length || (officeId !== "morning" && officeId !== "evening")) {
    return null;
  }
  let index = d.getDay();
  if (officeId === "evening") {
    index = (index + 1) % list.length;
  }
  return list[index];
}

function confessionStore() {
  return {
    bible: state.data.bible,
    corpus: state.data.corpus,
    daily: state.data.daily,
    echoes: state.data.echoes,
    benedictions: state.data.benedictions,
  };
}

function currentOfficeId() {
  if (iso(state.date) !== iso(todayInChicago())) return null;
  const hour = currentHourInChicago();
  if (hour < 11) return "morning";
  if (hour < 17) return "midday";
  if (hour < 22) return "evening";
  return "compline";
}

function render() {
  writeHash();
  const info = liturgicalDay(state.date);
  const found = lookup();
  document.getElementById("civil-date").textContent = info.civil;
  document.getElementById("season").textContent = info.spoken;
  const feast = document.getElementById("feast");
  if (info.feast) {
    feast.hidden = false;
    feast.textContent = info.feast.replace(/^the feast of /i, "").replace(/^the /i, "");
  } else {
    feast.hidden = true;
  }
  document.getElementById("date-input").value = iso(state.date);

  const nowOffice = currentOfficeId();
  const nav = document.getElementById("office-nav");
  nav.innerHTML = OFFICES.map((office) => {
    const active = office.id === state.office ? "is-active" : "";
    const now = office.id === nowOffice ? "is-now" : "";
    return `<button type="button" class="office-tab ${active} ${now}" data-office="${office.id}">
      <span class="office-tab__name">${office.label}</span>
      <span class="office-tab__time">${office.time}</span>
    </button>`;
  }).join("");

  document.getElementById("office").innerHTML = renderOffice(state.office, found, info);
  updateDock(state.office, found, info);
  applyAppearance();
}

function renderOffice(id, found, info) {
  const meta = OFFICES.find((o) => o.id === id);
  let psalms = null;
  let lessons = [];
  let emptyNote = "";

  if (id === "morning") {
    psalms = found.day?.psalms_morning;
    lessons = found.day?.morning_lessons || [];
  } else if (id === "evening") {
    psalms = found.day?.psalms_evening;
    lessons = found.day?.evening_lessons || [];
  } else if (id === "midday") {
    lessons = found.midday;
    if (!lessons.length) {
      emptyNote = "The Trinity Mission midday card has no Sunday lessons.";
    }
  } else if (id === "compline") {
    lessons = found.compline;
  }

  const sentence = sentenceFor(state.date, id);
  const store = confessionStore();
  const confession = confessionFor(store, state.date, id, lessons);
  const benediction = (id === "morning" || id === "evening")
    ? benedictionFor(store, state.date, id)
    : null;
  const psalmBlock = psalms
    ? renderPassage("Psalms", psalms, true)
    : "";
  const lessonBlocks = lessons
    .map((ref, i) => renderPassage(lessonLabel(i), ref, false))
    .join("");
  const opening = sentence
    ? `<section class="opening">
        <p class="silence">Let's begin our time together in silence.</p>
        <p class="sentence">${escapeHtml(sentence.bsb)} <cite>${escapeHtml(sentence.references.join("; "))}</cite></p>
      </section>`
    : "";
  const confessionRef = confession
    ? `<p><strong>Confession</strong> ${escapeHtml(confession.items.map((item) => item.label).join(" · "))}${
        confession.mode === "echo" ? " · Confessional Echo" : ""
      }</p>`
    : "";

  return `
    <header class="office-head">
      <p class="eyebrow">${meta.label} Prayer</p>
      <h2>${info.civil}</h2>
      <p class="lede">${info.spoken}${info.feast ? `, ${info.feast}` : ""}</p>
    </header>
    ${opening}
    <section class="refs">
      ${psalms ? `<p><strong>Psalms</strong> ${psalms}</p>` : ""}
      ${lessons.length ? `<p><strong>Lessons</strong> ${lessons.join(" · ")}</p>` : ""}
      ${confessionRef}
      ${found.day?.liturgical_name && (id === "morning" || id === "evening")
        ? `<p><strong>Table</strong> ${found.day.liturgical_name}</p>`
        : ""}
    </section>
    ${emptyNote ? `<p class="empty">${emptyNote}</p>` : psalmBlock + lessonBlocks}
    ${!emptyNote && (lessons.length || psalms) ? `<p class="response">The Word of the Lord.<br>Thanks be to God.</p>` : ""}
    ${confession ? renderConfession(confession) : ""}
    ${benediction ? renderBenediction(benediction) : ""}
  `;
}

function renderConfession(block) {
  const echo = block.mode === "echo"
    ? `<p class="confession__echo">Confessional Echo for ${escapeHtml(block.matched)}</p>`
    : "";
  const items = block.items.map((item) => `
    <article class="confession-item">
      <h3>${escapeHtml(item.label)}</h3>
      <p class="confession__question">${escapeHtml(item.heading)}</p>
      <p class="verse">${escapeHtml(item.body)}</p>
    </article>
  `).join("");
  return `
    <section class="confession">
      <p class="eyebrow">Daily Confession</p>
      <p class="confession__cue">A reading from ${escapeHtml(block.name)}.</p>
      ${echo}
      ${items}
    </section>
  `;
}

function renderBenediction(item) {
  return `
    <section class="benediction">
      <p class="eyebrow">Benediction</p>
      <p class="benediction__text">${escapeHtml(item.text)}</p>
      <cite>${escapeHtml(item.source)}</cite>
    </section>
  `;
}

function updateDock(id, found, info) {
  const meta = OFFICES.find((o) => o.id === id);
  const dock = document.getElementById("dock");
  const audio = document.getElementById("dock-audio");
  const src = found.audio[id];
  document.getElementById("dock-title").textContent = `Welcome to ${meta.label === "Compline" ? "Compline" : `${meta.label} Prayer`}`;
  document.getElementById("dock-meta").textContent = `${info.civil} · audio`;
  if (!src) {
    dock.classList.add("is-empty");
    audio.removeAttribute("src");
    audio.load();
    return;
  }
  dock.classList.remove("is-empty");
  const absolute = new URL(src, window.location.href).href;
  if (audio.src !== absolute) {
    audio.src = src;
  }
}

function lessonLabel(index) {
  return ["First Lesson", "Second Lesson", "Third Lesson"][index] || `Lesson ${index + 1}`;
}

function renderPassage(title, ref, psalms) {
  let passage;
  try {
    passage = resolveReference(state.data.bible, ref, psalms);
  } catch (err) {
    return `<article class="passage"><h3>${title}</h3><p class="empty">${ref}: ${err.message}</p></article>`;
  }
  const groups = [];
  for (const verse of passage.verses) {
    const last = groups[groups.length - 1];
    if (!last || last.chapter !== verse.chapter) {
      groups.push({ chapter: verse.chapter, book: verse.book, verses: [verse] });
    } else {
      last.verses.push(verse);
    }
  }
  const body = groups.map((group) => {
    const heading = group.book === "Psalm" ? `Psalm ${group.chapter}` : `${group.book} ${group.chapter}`;
    const verses = group.verses
      .map((v) => `<p class="verse"><sup>${v.verse}</sup>${formatVerseHtml(v.text)}</p>`)
      .join("");
    return `<h4>${heading}</h4>${verses}`;
  }).join("");
  return `<article class="passage"><h3>${title} <span>${escapeHtml(ref)}</span></h3>${body}</article>`;
}

function formatVerseHtml(text) {
  const parts = String(text).split(/(\s*Selah\.?)/i);
  return parts.map((part) => {
    if (/^\s*Selah\.?$/i.test(part)) {
      return `<span class="selah">Selah</span>`;
    }
    return escapeHtml(part);
  }).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

boot().catch((err) => {
  document.getElementById("office").innerHTML = `<p class="empty">${err.message}</p>`;
});
