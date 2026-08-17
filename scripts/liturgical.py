#!/usr/bin/env python3
"""Traditional 1662/1928/REC liturgical day names."""

from __future__ import annotations

from datetime import date, timedelta

ORDINALS = [
    "", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
    "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth",
    "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth",
    "Nineteenth", "Twentieth", "Twenty-first", "Twenty-second",
    "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
    "Twenty-seventh",
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

RED_LETTER = {
    (1, 1): "the Circumcision of Christ",
    (1, 6): "the Epiphany of our Lord",
    (1, 25): "the Conversion of Saint Paul",
    (2, 2): "the Presentation of Christ in the Temple",
    (2, 24): "Saint Matthias the Apostle",
    (3, 25): "the Annunciation of the Blessed Virgin Mary",
    (4, 25): "Saint Mark the Evangelist",
    (6, 11): "Saint Barnabas the Apostle",
    (6, 24): "the Nativity of Saint John the Baptist",
    (6, 29): "Saint Peter the Apostle",
    (7, 25): "Saint James the Apostle",
    (8, 6): "the Transfiguration of our Lord",
    (8, 15): "the feast of Saint Mary the Virgin",
    (8, 24): "Saint Bartholomew the Apostle",
    (9, 21): "Saint Matthew the Apostle",
    (9, 29): "Saint Michael and All Angels",
    (10, 18): "Saint Luke the Evangelist",
    (10, 28): "Saint Simon and Saint Jude, Apostles",
    (11, 1): "All Saints",
    (11, 30): "Saint Andrew the Apostle",
    (12, 21): "Saint Thomas the Apostle",
    (12, 25): "the Nativity of our Lord",
    (12, 26): "Saint Stephen, Deacon and Martyr",
    (12, 27): "Saint John the Apostle and Evangelist",
    (12, 28): "the Holy Innocents",
}

DAY_WORDS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 21: "twenty-first",
    22: "twenty-second", 23: "twenty-third", 24: "twenty-fourth",
    25: "twenty-fifth", 26: "twenty-sixth", 27: "twenty-seventh",
    28: "twenty-eighth", 29: "twenty-ninth", 30: "thirtieth",
    31: "thirty-first",
}


def easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 16
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def advent_sunday(year: int) -> date:
    for delta in range(7):
        d = date(year, 11, 27) + timedelta(days=delta)
        if d.weekday() == 6:
            return d
    raise RuntimeError("advent sunday not found")


def _nth_sunday_after(anchor: date, d: date) -> int:
    """How many Sundays after `anchor` is the Sunday on or before `d`."""
    sunday = d - timedelta(days=(d.weekday() + 1) % 7)
    return (sunday - anchor).days // 7


# Project-established 2026 anchors (Trinity Mission tables + user calendar).
YEAR_NOTES = {
    2026: {
        "easter": date(2026, 4, 5),
        "ash": date(2026, 2, 18),
        "palm": date(2026, 3, 29),
        "ascension": date(2026, 5, 14),
        "pentecost": date(2026, 5, 24),
        "trinity": date(2026, 5, 31),
        "advent": date(2026, 11, 29),
    }
}


def year_anchors(year: int) -> dict:
    if year in YEAR_NOTES:
        return YEAR_NOTES[year]
    e = easter(year)
    return {
        "easter": e,
        "ash": e - timedelta(days=46),
        "palm": e - timedelta(days=7),
        "ascension": e + timedelta(days=39),
        "pentecost": e + timedelta(days=49),
        "trinity": e + timedelta(days=56),
        "advent": advent_sunday(year),
    }


def liturgical_day(d: date) -> dict:
    notes = year_anchors(d.year)
    e = notes["easter"]
    ash = notes["ash"]
    palm = notes["palm"]
    ascension = notes["ascension"]
    pentecost = notes["pentecost"]
    trinity = notes["trinity"]
    advent = notes["advent"]
    christmas = date(d.year, 12, 25)
    epiphany = date(d.year, 1, 6)

    feast = RED_LETTER.get((d.month, d.day))
    weekday = "Sunday" if d.weekday() == 6 else WEEKDAYS[d.weekday()]

    if d == christmas:
        season = "Christmas Day"
    elif d == date(d.year, 12, 24):
        season = "Christmas Eve"
    elif date(d.year, 12, 26) <= d <= date(d.year, 12, 31) or d <= date(d.year, 1, 5):
        season = "Christmastide"
    elif d == epiphany:
        season = "the Epiphany of our Lord"
    elif epiphany < d < ash:
        first = epiphany + timedelta(days=(6 - epiphany.weekday()) % 7)
        if first <= epiphany:
            first += timedelta(days=7)
        n = _nth_sunday_after(first - timedelta(days=7), d)
        if d.weekday() == 6:
            season = f"the {ORDINALS[n]} Sunday after Epiphany"
        else:
            season = f"the week following the {ORDINALS[max(n, 1)]} Sunday after Epiphany"
    elif d == ash:
        season = "Ash Wednesday"
    elif ash < d < palm:
        first_lent = ash + timedelta(days=(6 - ash.weekday()) % 7)
        if first_lent == ash:
            first_lent += timedelta(days=7)
        if d < first_lent:
            season = "the week of Ash Wednesday"
        elif d.weekday() == 6:
            n = ((d - first_lent).days // 7) + 1
            season = f"the {ORDINALS[n]} Sunday in Lent"
        else:
            n = _nth_sunday_after(first_lent, d)
            season = f"the week following the {ORDINALS[max(n, 1)]} Sunday in Lent"
    elif d == palm:
        season = "Palm Sunday"
    elif palm < d < e:
        season = "Holy Week"
    elif d == e:
        season = "Easter Day"
    elif e < d < ascension:
        n = _nth_sunday_after(e, d)
        if d.weekday() == 6:
            season = f"the {ORDINALS[n]} Sunday after Easter"
        else:
            season = f"the week following the {ORDINALS[max(n, 1)]} Sunday after Easter" if n else "Easter Week"
    elif d == ascension:
        season = "Ascension Day"
    elif ascension < d < pentecost:
        season = "the week following Ascension Day"
    elif d == pentecost:
        season = "Whitsunday, the Feast of Pentecost"
    elif pentecost < d < trinity:
        season = "the week following Whitsunday"
    elif d == trinity:
        season = "Trinity Sunday"
    elif trinity < d < advent:
        n = _nth_sunday_after(trinity, d)
        if d.weekday() == 6:
            season = f"the {ORDINALS[n]} Sunday after Trinity"
        else:
            season = f"the week following the {ORDINALS[max(n, 1)]} Sunday after Trinity"
    elif advent <= d < christmas:
        n = ((d - advent).days // 7) + 1
        if d.weekday() == 6:
            season = f"the {ORDINALS[n]} Sunday in Advent"
        else:
            season = f"the week following the {ORDINALS[n]} Sunday in Advent"
    else:
        season = "the Christian year"

    if season in {"Holy Week", "Easter Week", "Christmastide"}:
        spoken = f"{weekday} in {season}"
    elif season.startswith("the week"):
        spoken = f"{weekday} in {season}"
    elif "Day" in season or season.startswith("Ash") or season.startswith("Whitsunday") or "Eve" in season:
        spoken = season if d.weekday() == 6 or "Day" in season else f"{weekday}, {season}"
    elif d.weekday() == 6:
        spoken = season
    else:
        spoken = f"{weekday} in {season}"

    return {
        "date": d.isoformat(),
        "weekday": weekday,
        "season": season,
        "feast": feast,
        "spoken": spoken,
        "civil": f"{weekday}, {d.strftime('%B')} {d.day}, {d.year}",
    }


def number_year(year: int) -> str:
    if year == 2026:
        return "two thousand twenty-six"
    thousands, rest = divmod(year, 1000)
    if thousands == 2 and rest < 100:
        return f"two thousand {_small(rest)}" if rest else "two thousand"
    return str(year)


def _small(n: int) -> str:
    ones = [
        "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if n < 20:
        return ones[n]
    t, o = divmod(n, 10)
    return tens[t] if o == 0 else f"{tens[t]}-{ones[o]}"


def orientation_sentence(d: date) -> str:
    info = liturgical_day(d)
    spoken_day = f"the {DAY_WORDS[d.day]} of {d.strftime('%B')}"
    year = f"the year of our Lord {number_year(d.year)}"
    when = info["season"]
    feast = f", {info['feast']}" if info["feast"] else ""
    return (
        f"This is {info['weekday']}, {spoken_day}, in {year}, "
        f"{when}{feast}."
    )
