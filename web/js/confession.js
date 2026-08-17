const CONFESSION_NAMES = {
  wcf: "the Westminster Confession of Faith",
  wsc: "the Westminster Shorter Catechism",
  wlc: "the Westminster Larger Catechism",
  hc: "the Heidelberg Catechism",
  belgic: "the Belgic Confession",
  standards: "the Westminster Standards",
};

const BOOK_ALIAS = {
  Genesis: "gen",
  Exodus: "exod",
  Leviticus: "lev",
  Numbers: "num",
  Deuteronomy: "deut",
  Joshua: "josh",
  Judges: "judg",
  Ruth: "ruth",
  "1 Samuel": "1sam",
  "2 Samuel": "2sam",
  "1 Kings": "1kgs",
  "2 Kings": "2kgs",
  "1 Chronicles": "1chr",
  "2 Chronicles": "2chr",
  Ezra: "ezra",
  Nehemiah: "neh",
  Esther: "esth",
  Job: "job",
  Psalm: "ps",
  Proverbs: "prov",
  Ecclesiastes: "eccl",
  "Song of Solomon": "song",
  Isaiah: "isa",
  Jeremiah: "jer",
  Lamentations: "lam",
  Ezekiel: "ezek",
  Daniel: "dan",
  Hosea: "hos",
  Joel: "joel",
  Amos: "amos",
  Obadiah: "obad",
  Jonah: "jonah",
  Micah: "mic",
  Nahum: "nah",
  Habakkuk: "hab",
  Zephaniah: "zeph",
  Haggai: "hag",
  Zechariah: "zech",
  Malachi: "mal",
  Matthew: "matt",
  Mark: "mark",
  Luke: "luke",
  John: "john",
  Acts: "acts",
  Romans: "rom",
  "1 Corinthians": "1cor",
  "2 Corinthians": "2cor",
  Galatians: "gal",
  Ephesians: "eph",
  Philippians: "phil",
  Colossians: "col",
  "1 Thessalonians": "1thess",
  "2 Thessalonians": "2thess",
  "1 Timothy": "1tim",
  "2 Timothy": "2tim",
  Titus: "titus",
  Philemon: "phlm",
  Hebrews: "heb",
  James: "jas",
  "1 Peter": "1pet",
  "2 Peter": "2pet",
  "1 John": "1john",
  "2 John": "2john",
  "3 John": "3john",
  Jude: "jude",
  Revelation: "rev",
};

function lessonChapters(bible, refs) {
  const found = new Set();
  for (const ref of refs) {
    try {
      const passage = resolveReference(bible, ref);
      const alias = BOOK_ALIAS[passage.book];
      if (!alias) continue;
      for (const verse of passage.verses) {
        found.add(`${alias}:${verse.chapter}`);
      }
    } catch {
      // ignore unparsable refs
    }
  }
  return found;
}

function echoForLessons(bible, echoes, refs) {
  const chapters = lessonChapters(bible, refs);
  if (!chapters.size) return null;
  for (const echo of echoes) {
    const hit = echo.refs.some((item) => chapters.has(`${item.book}:${item.chapter}`));
    if (hit) return echo;
  }
  return null;
}

function resolveConfessionItem(corpus, item) {
  if (item.source === "wcf") {
    const chapter = corpus.wcf.chapters.find((ch) => ch.chapter === item.chapter);
    const section = chapter.sections.find((sec) => sec.section === item.section);
    return {
      source: "wcf",
      label: `Westminster Confession ${item.chapter}.${item.section}`,
      heading: `Chapter ${item.chapter}. ${chapter.title}`,
      body: section.text,
    };
  }
  if (item.source === "wsc" || item.source === "wlc" || item.source === "hc") {
    const pack = corpus[item.source];
    const entry = pack.items.find((q) => q.number === item.number);
    return {
      source: item.source,
      label: `${pack.title} Q${entry.number}`,
      heading: `Q${entry.number}. ${entry.question}`,
      body: entry.answer,
    };
  }
  if (item.source === "belgic") {
    const entry = corpus.belgic.items.find((a) => a.article === item.article);
    return {
      source: "belgic",
      label: `Belgic Confession Article ${entry.article}`,
      heading: `Article ${entry.article}. ${entry.title}`,
      body: entry.text,
    };
  }
  throw new Error("Unknown confession item");
}

function readingName(items, isEcho) {
  const sources = new Set(items.map((item) => item.source));
  if (isEcho) return CONFESSION_NAMES[items[0].source];
  if (sources.size > 1 && [...sources].every((src) => ["wsc", "wlc", "wcf"].includes(src))) {
    return CONFESSION_NAMES.standards;
  }
  return CONFESSION_NAMES[items[0].source];
}

function eveningSequential(corpus, d) {
  const hcCount = corpus.hc.items.length;
  const cycle = hcCount + corpus.belgic.items.length;
  const start = new Date(d.getFullYear(), 0, 0);
  const doy = Math.round((d - start) / 86400000);
  const index = (doy - 1) % cycle;
  if (index < hcCount) {
    return resolveConfessionItem(corpus, { source: "hc", number: index + 1 });
  }
  return resolveConfessionItem(corpus, { source: "belgic", article: index - hcCount + 1 });
}

function confessionFor(store, d, officeId, lessons) {
  if (officeId !== "morning" && officeId !== "evening") return null;
  const echo = echoForLessons(store.bible, store.echoes, lessons);
  if (echo) {
    const item = resolveConfessionItem(store.corpus, { source: echo.source, ...echo.cite });
    return {
      mode: "echo",
      name: readingName([item], true),
      echoLabel: echo.echo,
      matched: echo.scripture,
      items: [item],
    };
  }
  if (officeId === "morning") {
    const key = iso(d).slice(5);
    const plan = store.daily[key] || store.daily["02-28"];
    const items = plan.items.map((item) => resolveConfessionItem(store.corpus, item));
    return { mode: "daily", name: readingName(items, false), items };
  }
  const item = eveningSequential(store.corpus, d);
  return { mode: "daily", name: readingName([item], false), items: [item] };
}

function benedictionFor(store, d, officeId) {
  const items = store.benedictions;
  const start = new Date(d.getFullYear(), 0, 0);
  const doy = Math.round((d - start) / 86400000);
  let index = (doy - 1) % items.length;
  if (officeId === "evening") index = (index + 3) % items.length;
  return items[index];
}
