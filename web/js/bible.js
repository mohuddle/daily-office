const ABBREV = {
  Gen: "Genesis",
  Exod: "Exodus",
  Lev: "Leviticus",
  Num: "Numbers",
  Deut: "Deuteronomy",
  Josh: "Joshua",
  Judg: "Judges",
  Ruth: "Ruth",
  "1 Sam": "1 Samuel",
  "2 Sam": "2 Samuel",
  "1 Kgs": "1 Kings",
  "2 Kgs": "2 Kings",
  "1 Chr": "1 Chronicles",
  "2 Chr": "2 Chronicles",
  Ezra: "Ezra",
  Neh: "Nehemiah",
  Esth: "Esther",
  Job: "Job",
  Ps: "Psalm",
  Psalm: "Psalm",
  Psalms: "Psalm",
  Prov: "Proverbs",
  Eccl: "Ecclesiastes",
  Song: "Song of Solomon",
  Isa: "Isaiah",
  Jer: "Jeremiah",
  Lam: "Lamentations",
  Ezek: "Ezekiel",
  Dan: "Daniel",
  Hos: "Hosea",
  Joel: "Joel",
  Amos: "Amos",
  Obad: "Obadiah",
  Jonah: "Jonah",
  Mic: "Micah",
  Nah: "Nahum",
  Hab: "Habakkuk",
  Zeph: "Zephaniah",
  Hag: "Haggai",
  Zech: "Zechariah",
  Mal: "Malachi",
  Matt: "Matthew",
  Mark: "Mark",
  Luke: "Luke",
  John: "John",
  Acts: "Acts",
  Rom: "Romans",
  "1 Cor": "1 Corinthians",
  "2 Cor": "2 Corinthians",
  Gal: "Galatians",
  Eph: "Ephesians",
  Phil: "Philippians",
  Col: "Colossians",
  "1 Thess": "1 Thessalonians",
  "2 Thess": "2 Thessalonians",
  "1 Tim": "1 Timothy",
  "2 Tim": "2 Timothy",
  Titus: "Titus",
  Phlm: "Philemon",
  Philemon: "Philemon",
  Heb: "Hebrews",
  Jas: "James",
  "1 Pet": "1 Peter",
  "2 Pet": "2 Peter",
  "1 John": "1 John",
  "2 John": "2 John",
  "3 John": "3 John",
  Jude: "Jude",
  Rev: "Revelation",
  Genesis: "Genesis",
  Exodus: "Exodus",
  Leviticus: "Leviticus",
  Numbers: "Numbers",
  Deuteronomy: "Deuteronomy",
  Joshua: "Joshua",
  Judges: "Judges",
  "1 Samuel": "1 Samuel",
  "2 Samuel": "2 Samuel",
  "1 Kings": "1 Kings",
  "2 Kings": "2 Kings",
  "1 Chronicles": "1 Chronicles",
  "2 Chronicles": "2 Chronicles",
  Nehemiah: "Nehemiah",
  Esther: "Esther",
  Proverbs: "Proverbs",
  Ecclesiastes: "Ecclesiastes",
  "Song of Solomon": "Song of Solomon",
  Isaiah: "Isaiah",
  Jeremiah: "Jeremiah",
  Lamentations: "Lamentations",
  Ezekiel: "Ezekiel",
  Daniel: "Daniel",
  Hosea: "Hosea",
  Obadiah: "Obadiah",
  Micah: "Micah",
  Nahum: "Nahum",
  Habakkuk: "Habakkuk",
  Zephaniah: "Zephaniah",
  Haggai: "Haggai",
  Zechariah: "Zechariah",
  Malachi: "Malachi",
  Matthew: "Matthew",
  Romans: "Romans",
  "1 Corinthians": "1 Corinthians",
  "2 Corinthians": "2 Corinthians",
  Galatians: "Galatians",
  Ephesians: "Ephesians",
  Philippians: "Philippians",
  Colossians: "Colossians",
  "1 Thessalonians": "1 Thessalonians",
  "2 Thessalonians": "2 Thessalonians",
  "1 Timothy": "1 Timothy",
  "2 Timothy": "2 Timothy",
  Philemon: "Philemon",
  Hebrews: "Hebrews",
  James: "James",
  "1 Peter": "1 Peter",
  "2 Peter": "2 Peter",
  Revelation: "Revelation",
};

const ABBREV_KEYS = Object.keys(ABBREV).sort((a, b) => b.length - a.length);

function normalizeRef(ref) {
  return String(ref).replace(/[–—−]/g, "-").trim();
}

function stripAB(token) {
  return token.replace(/[abAB](?=-|$)/g, "").replace(/[abAB]$/, "");
}

function chapterCount(bible, book, chapter) {
  return Object.keys(bible[book][String(chapter)]).length;
}

function verseText(bible, book, chapter, verse) {
  const text = bible[book]?.[String(chapter)]?.[String(verse)];
  if (!text) throw new Error(`Missing ${book} ${chapter}:${verse}`);
  return text;
}

function expandSpan(bible, book, startCh, startVs, endCh, endVs) {
  const verses = [];
  for (let ch = startCh; ch <= endCh; ch += 1) {
    const first = ch === startCh && startVs ? startVs : 1;
    const last = ch === endCh && endVs ? endVs : chapterCount(bible, book, ch);
    for (let vs = first; vs <= last; vs += 1) {
      verses.push({
        book,
        chapter: ch,
        verse: vs,
        text: verseText(bible, book, ch, vs),
      });
    }
  }
  return verses;
}

function splitBook(ref) {
  const raw = normalizeRef(ref);
  for (const key of ABBREV_KEYS) {
    if (raw === key || raw.startsWith(`${key} `)) {
      return [ABBREV[key], raw.slice(key.length).trim()];
    }
  }
  throw new Error(`Unknown book in reference: ${ref}`);
}

function parseNumericParts(bible, book, rest) {
  const parts = rest.split(",").map((p) => p.trim()).filter(Boolean);
  const verses = [];
  let lastChapter = null;
  for (const rawPart of parts) {
    const part = stripAB(rawPart.replace(/\s+/g, ""));
    let m;
    if ((m = part.match(/^(\d+):(\d+)-(\d+):(\d+)$/))) {
      verses.push(...expandSpan(bible, book, +m[1], +m[2], +m[3], +m[4]));
      lastChapter = +m[3];
    } else if ((m = part.match(/^(\d+)-(\d+):(\d+)-(\d+)$/))) {
      verses.push(...expandSpan(bible, book, +m[1], null, +m[2], +m[4]));
      lastChapter = +m[2];
    } else if ((m = part.match(/^(\d+)-(\d+):(\d+)$/))) {
      verses.push(...expandSpan(bible, book, +m[1], null, +m[2], +m[3]));
      lastChapter = +m[2];
    } else if ((m = part.match(/^(\d+):(\d+)-(\d+)$/))) {
      verses.push(...expandSpan(bible, book, +m[1], +m[2], +m[1], +m[3]));
      lastChapter = +m[1];
    } else if ((m = part.match(/^(\d+):(\d+)$/))) {
      verses.push(...expandSpan(bible, book, +m[1], +m[2], +m[1], +m[2]));
      lastChapter = +m[1];
    } else if ((m = part.match(/^(\d+)-(\d+)$/))) {
      if (
        lastChapter != null &&
        +m[1] <= chapterCount(bible, book, lastChapter) &&
        +m[2] <= chapterCount(bible, book, lastChapter)
      ) {
        verses.push(...expandSpan(bible, book, lastChapter, +m[1], lastChapter, +m[2]));
      } else {
        verses.push(...expandSpan(bible, book, +m[1], null, +m[2], null));
        lastChapter = +m[2];
      }
    } else if ((m = part.match(/^(\d+)$/))) {
      if (lastChapter != null && +m[1] <= chapterCount(bible, book, lastChapter)) {
        verses.push(...expandSpan(bible, book, lastChapter, +m[1], lastChapter, +m[1]));
      } else {
        verses.push(...expandSpan(bible, book, +m[1], null, +m[1], null));
        lastChapter = +m[1];
      }
    } else {
      throw new Error(`Cannot parse ${rawPart} in ${book} ${rest}`);
    }
  }
  return verses;
}

function resolveReference(bible, ref, psalms = false) {
  const raw = normalizeRef(ref);
  if (psalms || /^[0-9,\-\s]+$/.test(raw)) {
    return { reference: ref, book: "Psalm", verses: parseNumericParts(bible, "Psalm", raw) };
  }
  const [book, rest] = splitBook(raw);
  return { reference: ref, book, verses: parseNumericParts(bible, book, rest) };
}
