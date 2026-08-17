const ORDINALS = [
  "", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
  "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth",
  "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth",
  "Nineteenth", "Twentieth", "Twenty-first", "Twenty-second",
  "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
  "Twenty-seventh",
];

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const RED_LETTER = {
  "1-1": "the Circumcision of Christ",
  "1-6": "the Epiphany of our Lord",
  "1-25": "the Conversion of Saint Paul",
  "2-2": "the Presentation of Christ in the Temple",
  "2-24": "Saint Matthias the Apostle",
  "3-25": "the Annunciation of the Blessed Virgin Mary",
  "4-25": "Saint Mark the Evangelist",
  "6-11": "Saint Barnabas the Apostle",
  "6-24": "the Nativity of Saint John the Baptist",
  "6-29": "Saint Peter the Apostle",
  "7-25": "Saint James the Apostle",
  "8-6": "the Transfiguration of our Lord",
  "8-15": "the feast of Saint Mary the Virgin",
  "8-24": "Saint Bartholomew the Apostle",
  "9-21": "Saint Matthew the Apostle",
  "9-29": "Saint Michael and All Angels",
  "10-18": "Saint Luke the Evangelist",
  "10-28": "Saint Simon and Saint Jude, Apostles",
  "11-1": "All Saints",
  "11-30": "Saint Andrew the Apostle",
  "12-21": "Saint Thomas the Apostle",
  "12-25": "the Nativity of our Lord",
  "12-26": "Saint Stephen, Deacon and Martyr",
  "12-27": "Saint John the Apostle and Evangelist",
  "12-28": "the Holy Innocents",
};

const YEAR_NOTES = {
  2026: {
    easter: "2026-04-05",
    ash: "2026-02-18",
    palm: "2026-03-29",
    ascension: "2026-05-14",
    pentecost: "2026-05-24",
    trinity: "2026-05-31",
    advent: "2026-11-29",
  },
};

function parseISODate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function iso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(d, n) {
  const next = new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  return next;
}

function sundayOnOrBefore(d) {
  const dow = d.getDay(); // 0 Sun
  return addDays(d, -dow);
}

function nthSundayAfter(anchor, d) {
  const sunday = sundayOnOrBefore(d);
  return Math.floor((sunday - anchor) / 86400000 / 7);
}

function yearAnchors(year) {
  const notes = YEAR_NOTES[year];
  if (notes) {
    return {
      easter: parseISODate(notes.easter),
      ash: parseISODate(notes.ash),
      palm: parseISODate(notes.palm),
      ascension: parseISODate(notes.ascension),
      pentecost: parseISODate(notes.pentecost),
      trinity: parseISODate(notes.trinity),
      advent: parseISODate(notes.advent),
    };
  }
  throw new Error(`No liturgical anchors for ${year}`);
}

function liturgicalDay(d) {
  const notes = yearAnchors(d.getFullYear());
  const { easter, ash, palm, ascension, pentecost, trinity, advent } = notes;
  const feast = RED_LETTER[`${d.getMonth() + 1}-${d.getDate()}`] || null;
  const weekday = WEEKDAYS[(d.getDay() + 6) % 7];
  const christmas = new Date(d.getFullYear(), 11, 25);
  const epiphany = new Date(d.getFullYear(), 0, 6);
  let season;

  const cmp = (a, b) => a - b;

  if (cmp(d, christmas) === 0) season = "Christmas Day";
  else if (iso(d) === `${d.getFullYear()}-12-24`) season = "Christmas Eve";
  else if (d >= new Date(d.getFullYear(), 11, 26) || d <= new Date(d.getFullYear(), 0, 5)) {
    season = "Christmastide";
  } else if (cmp(d, epiphany) === 0) season = "the Epiphany of our Lord";
  else if (d > epiphany && d < ash) {
    const n = nthSundayAfter(epiphany, d);
    season = d.getDay() === 0
      ? `the ${ORDINALS[Math.max(n, 1)]} Sunday after Epiphany`
      : `the week following the ${ORDINALS[Math.max(n, 1)]} Sunday after Epiphany`;
  } else if (cmp(d, ash) === 0) season = "Ash Wednesday";
  else if (d > ash && d < palm) {
    const n = nthSundayAfter(ash, d);
    season = d.getDay() === 0
      ? `the ${ORDINALS[Math.max(n, 1)]} Sunday in Lent`
      : `the week following the ${ORDINALS[Math.max(n, 1)]} Sunday in Lent`;
  } else if (cmp(d, palm) === 0) season = "Palm Sunday";
  else if (d > palm && d < easter) season = "Holy Week";
  else if (cmp(d, easter) === 0) season = "Easter Day";
  else if (d > easter && d < ascension) {
    const n = nthSundayAfter(easter, d);
    season = d.getDay() === 0
      ? `the ${ORDINALS[n]} Sunday after Easter`
      : n
        ? `the week following the ${ORDINALS[n]} Sunday after Easter`
        : "Easter Week";
  } else if (cmp(d, ascension) === 0) season = "Ascension Day";
  else if (d > ascension && d < pentecost) season = "the week following Ascension Day";
  else if (cmp(d, pentecost) === 0) season = "Whitsunday, the Feast of Pentecost";
  else if (d > pentecost && d < trinity) season = "the week following Whitsunday";
  else if (cmp(d, trinity) === 0) season = "Trinity Sunday";
  else if (d > trinity && d < advent) {
    const n = nthSundayAfter(trinity, d);
    season = d.getDay() === 0
      ? `the ${ORDINALS[n]} Sunday after Trinity`
      : `the week following the ${ORDINALS[n]} Sunday after Trinity`;
  } else if (d >= advent && d < christmas) {
    const n = Math.floor((d - advent) / 86400000 / 7) + 1;
    season = d.getDay() === 0
      ? `the ${ORDINALS[n]} Sunday in Advent`
      : `the week following the ${ORDINALS[n]} Sunday in Advent`;
  } else {
    season = "the Christian year";
  }

  let spoken;
  if (["Holy Week", "Easter Week", "Christmastide"].includes(season) || season.startsWith("the week")) {
    spoken = `${weekday} in ${season}`;
  } else if (d.getDay() === 0) {
    spoken = season;
  } else {
    spoken = `${weekday} in ${season}`;
  }

  return {
    date: iso(d),
    weekday,
    season,
    feast,
    color: liturgicalColor(d, season, feast),
    spoken,
    civil: d.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    }),
  };
}

const WHITE_FEASTS = new Set([
  "1-1", "1-6", "2-2", "3-25", "8-6", "8-15", "11-1", "12-25", "12-27",
]);
const RED_FEASTS = new Set([
  "1-25", "2-24", "4-25", "6-11", "6-24", "6-29", "7-25", "8-24",
  "9-21", "9-29", "10-18", "10-28", "11-30", "12-21", "12-26", "12-28",
]);

function liturgicalColor(d, season, feast) {
  const key = `${d.getMonth() + 1}-${d.getDate()}`;
  if (feast && WHITE_FEASTS.has(key)) return "white";
  if (feast && RED_FEASTS.has(key)) return "red";
  if (season === "Christmas Day" || season === "Christmas Eve" || season === "Christmastide") return "white";
  if (season === "the Epiphany of our Lord") return "white";
  if (season.includes("after Epiphany")) return "green";
  if (season === "Ash Wednesday" || season.includes("Lent") || season.includes("Ash Wednesday")) return "purple";
  if (season === "Palm Sunday" || season === "Holy Week") return "red";
  if (season === "Easter Day" || season.includes("after Easter") || season === "Easter Week") return "white";
  if (season === "Ascension Day" || season.includes("Ascension")) return "white";
  if (season.includes("Pentecost") || season.includes("Whitsunday")) return "red";
  if (season === "Trinity Sunday") return "white";
  if (season.includes("after Trinity")) return "green";
  if (season.includes("Advent")) return "purple";
  return "green";
}

function todayInChicago() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const get = (type) => parts.find((p) => p.type === type).value;
  return parseISODate(`${get("year")}-${get("month")}-${get("day")}`);
}

function currentHourInChicago() {
  return Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Chicago",
      hour: "numeric",
      hourCycle: "h23",
    }).format(new Date())
  );
}
