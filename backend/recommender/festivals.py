"""Festivals and national days: how people usually dress for them, and when they fall.

Used in three places:
- the request parser: "Style me for Republic Day" / "ganesh chaturti" (typos are fine),
- the stylist: pieces in the festival's colours score higher, and each outfit says why,
- the Overview card: today's festival (with today's colour for Navratri) or the next one.

Colours are common customs, used as gentle preferences, never rules. Dates were checked against
several 2026-27 calendars in October 2026; lunar festivals can differ by a day between regions
(and Eid depends on the moon). Add next year's dates to DATES.
"""
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Festival:
    key: str
    name: str
    aliases: tuple[str, ...]         # ways people type it (lower case)
    colours: tuple[str, ...]         # colour words the colour parser understands
    occasion: str = "Festive"
    style: str | None = "Traditional"
    tip: str = ""

    @property
    def colour_text(self) -> str:
        names = list(self.colours)
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


_ALL = [
    Festival("republic_day", "Republic Day", ("republic day", "republicday", "26 january", "26th january", "26 jan", "26th jan", "gantantra diwas"),
             ("saffron", "white", "green"), "Festive", None, "Tiranga colours: saffron, white and green. Khadi and cotton look lovely."),
    Festival("independence_day", "Independence Day", ("independence day", "15 august", "15th august", "15 aug", "15th aug", "swatantrata diwas"),
             ("saffron", "white", "green"), "Festive", None, "Tiranga colours: saffron, white and green."),
    Festival("gandhi_jayanti", "Gandhi Jayanti", ("gandhi jayanti", "2 october", "2nd october", "2 oct", "2nd oct"),
             ("white", "cream", "beige"), "Festive", "Traditional", "Simple whites and khadi."),
    Festival("makar_sankranti", "Makar Sankranti", ("makar sankranti", "sankranti", "sankrant", "uttarayan",
                                                    "kite festival", "til gul", "khichdi"),
             ("black", "yellow", "green"), "Festive", "Traditional",
             "Black is traditional in Maharashtra (with halwa jewellery); yellow and green elsewhere."),
    Festival("pongal", "Pongal", ("pongal", "thai pongal"), ("yellow", "green", "white"), "Festive", "Traditional",
             "Silk or cotton in sunny yellow and fresh green."),
    Festival("lohri", "Lohri", ("lohri",), ("red", "yellow", "orange"), "Festive", "Traditional",
             "Phulkari brights, and a warm layer for the bonfire."),
    Festival("bihu", "Bihu", ("bihu", "rongali bihu"), ("cream", "red", "gold"), "Festive", "Traditional",
             "Mekhela chador style: cream with red or gold."),
    Festival("vasant_panchami", "Vasant Panchami", ("vasant panchami", "basant panchami", "saraswati puja"),
             ("yellow",), "Festive", "Traditional", "Yellow for spring and Saraswati."),
    Festival("maha_shivratri", "Maha Shivratri", ("maha shivratri", "mahashivratri", "shivratri"),
             ("white", "saffron", "green"), "Festive", "Traditional", "Simple whites, saffron or green."),
    Festival("holi", "Holi", ("holi", "dhulandi", "rangpanchami", "rang panchami"), ("white",), "Casual", None,
             "Old whites you don't mind turning colourful."),
    Festival("gudi_padwa", "Gudi Padwa", ("gudi padwa", "padwa", "ugadi", "cheti chand"),
             ("yellow", "orange", "green", "pink"), "Festive", "Traditional", "Nauvari or bright silk sarees, nath and gajra."),
    Festival("baisakhi", "Baisakhi", ("baisakhi", "vaisakhi"), ("yellow", "orange", "green"), "Festive", "Traditional",
             "Harvest brights: yellow and orange."),
    Festival("ram_navami", "Ram Navami", ("ram navami", "ramnavami"), ("yellow", "orange", "red"), "Festive", "Traditional",
             "Yellow or saffron."),
    Festival("eid", "Eid", ("eid", "eid ul fitr", "eid al fitr", "ramzan eid", "ramadan eid", "bakri eid", "eid ul adha",
                            "eid al adha", "bakrid"),
             ("white", "green", "pastel"), "Festive", "Traditional", "Elegant whites, greens and pastels."),
    Festival("raksha_bandhan", "Raksha Bandhan", ("raksha bandhan", "rakshabandhan", "rakhi"),
             ("pink", "yellow", "orange", "red"), "Festive", "Traditional", "Bright, happy colours."),
    Festival("teej", "Teej", ("teej", "hariyali teej", "hartalika teej"), ("green",), "Festive", "Traditional",
             "Green, with bangles and mehendi."),
    Festival("janmashtami", "Janmashtami", ("janmashtami", "krishna janmashtami", "gokulashtami", "dahi handi"),
             ("yellow", "royal blue", "peacock green"), "Festive", "Traditional", "Krishna's yellow, blue and peacock colours."),
    Festival("onam", "Onam", ("onam", "thiruvonam"), ("cream", "white", "gold"), "Festive", "Traditional",
             "Kerala kasavu: cream or white with a gold border."),
    Festival("ganesh_chaturthi", "Ganesh Chaturthi", ("ganesh chaturthi", "ganesh chathurthi", "ganesh utsav", "ganeshotsav",
                                                      "ganpati", "ganapati", "vinayaka chaturthi", "vinayagar chathurthi"),
             ("yellow", "red", "orange", "green"), "Festive", "Traditional",
             "Bappa's favourites: yellow, red and orange; nauvari and Paithani look stunning."),
    Festival("navratri", "Navratri", ("navratri", "navaratri", "garba", "dandiya", "durga ashtami"),
             ("red", "yellow", "green", "orange", "royal blue", "pink"), "Festive", "Traditional",
             "Each day has its own colour. Garba nights: flared, twirl-friendly pieces."),
    Festival("durga_puja", "Durga Puja", ("durga puja", "pujo", "sindoor khela", "bijoya"),
             ("red", "white"), "Festive", "Traditional", "Lal paar sada: white with a red border."),
    Festival("dussehra", "Dussehra", ("dussehra", "dusshera", "dussera", "dasara", "vijayadashami", "vijaya dashami"),
             ("red", "orange", "yellow"), "Festive", "Traditional", "Bright traditional wear."),
    Festival("karva_chauth", "Karva Chauth", ("karva chauth", "karwa chauth", "karwachauth"),
             ("red", "maroon", "pink"), "Festive", "Traditional", "Bridal reds and maroons."),
    Festival("dhanteras", "Dhanteras", ("dhanteras",), ("gold", "yellow", "red"), "Festive", "Traditional",
             "Gold and yellow for prosperity."),
    Festival("diwali", "Diwali", ("diwali", "deepavali", "divali", "laxmi puja", "lakshmi puja", "choti diwali"),
             ("red", "gold", "maroon", "pink", "yellow"), "Festive", "Traditional",
             "Rich colours, your best jewellery, and keep flowy dupattas away from diyas."),
    Festival("bhai_dooj", "Bhai Dooj", ("bhai dooj", "bhaidooj", "bhau beej", "bhai phota"),
             ("pink", "yellow", "orange"), "Festive", "Traditional", "Bright, cheerful colours."),
    Festival("chhath", "Chhath Puja", ("chhath", "chhath puja", "chhath pooja"), ("yellow", "orange", "red"), "Festive",
             "Traditional", "Yellow and saffron, simple and graceful."),
    Festival("guru_nanak_jayanti", "Guru Nanak Jayanti", ("guru nanak jayanti", "gurpurab", "gurupurab"),
             ("white", "saffron", "cream"), "Festive", "Traditional", "Whites and saffron, with your head covered at the gurdwara."),
    Festival("christmas", "Christmas", ("christmas", "xmas", "x mas"), ("red", "green", "white"), "Party", None,
             "Red, green or a touch of sparkle."),
    Festival("new_year", "New Year's Eve", ("new year", "new years", "new year eve", "new years eve", "nye"),
             ("black", "gold", "silver"), "Party", None, "Black with a little sparkle."),
    Festival("valentines", "Valentine's Day", ("valentine", "valentines", "valentines day", "valentine day"),
             ("red", "pink"), "Date", None, "Reds and pinks."),
]
FESTIVALS = {f.key: f for f in _ALL}

# Navratri day colours (with the goddess of the day).
_NAVRATRI_2026 = [("orange", "Maa Shailaputri"), ("white", "Maa Brahmacharini"), ("red", "Maa Chandraghanta"),
                  ("royal blue", "Maa Kushmanda"), ("yellow", "Maa Skandamata"), ("green", "Maa Katyayani"),
                  ("grey", "Maa Kalaratri"), ("purple", "Maa Mahagauri"), ("peacock green", "Maa Siddhidatri")]
# 2027 starts on a Thursday; colours follow the usual weekday rule (check your local list).
_NAVRATRI_2027 = [("yellow", "Maa Shailaputri"), ("green", "Maa Brahmacharini"), ("grey", "Maa Chandraghanta"),
                  ("orange", "Maa Kushmanda"), ("white", "Maa Skandamata"), ("red", "Maa Katyayani"),
                  ("royal blue", "Maa Kalaratri"), ("pink", "Maa Mahagauri"), ("purple", "Maa Siddhidatri")]

# (festival key, first day, last day, day colours or None)
DATES = [
    ("navratri", date(2026, 10, 11), date(2026, 10, 19), _NAVRATRI_2026),
    ("dussehra", date(2026, 10, 20), date(2026, 10, 20), None),
    ("dhanteras", date(2026, 11, 6), date(2026, 11, 6), None),
    ("diwali", date(2026, 11, 7), date(2026, 11, 9), None),
    ("bhai_dooj", date(2026, 11, 10), date(2026, 11, 10), None),
    ("christmas", date(2026, 12, 25), date(2026, 12, 25), None),
    ("new_year", date(2026, 12, 31), date(2026, 12, 31), None),
    ("lohri", date(2027, 1, 13), date(2027, 1, 13), None),
    ("makar_sankranti", date(2027, 1, 14), date(2027, 1, 15), None),
    ("republic_day", date(2027, 1, 26), date(2027, 1, 26), None),
    ("valentines", date(2027, 2, 14), date(2027, 2, 14), None),
    ("eid", date(2027, 3, 10), date(2027, 3, 10), None),
    ("holi", date(2027, 3, 22), date(2027, 3, 22), None),
    ("independence_day", date(2027, 8, 15), date(2027, 8, 15), None),
    ("janmashtami", date(2027, 8, 25), date(2027, 8, 25), None),
    ("navratri", date(2027, 9, 30), date(2027, 10, 8), _NAVRATRI_2027),
    ("gandhi_jayanti", date(2027, 10, 2), date(2027, 10, 2), None),
    ("diwali", date(2027, 10, 29), date(2027, 10, 29), None),
    ("christmas", date(2027, 12, 25), date(2027, 12, 25), None),
]


def get(key: str | None) -> Festival | None:
    return FESTIVALS.get(key) if key else None


def day_colour(key: str, today: date) -> tuple[str, str] | None:
    """(colour, goddess) for festivals with a colour per day (Navratri), if today is one of them."""
    for k, start, end, days in DATES:
        if k == key and days and start <= today <= end:
            return days[(today - start).days]
    return None


def now(today: date, within: int = 21) -> dict | None:
    """Today's festival (with today's colour), else the next one within `within` days, else None."""
    upcoming = None
    for key, start, end, days in DATES:
        f = FESTIVALS[key]
        if start <= today <= end:
            n = (today - start).days
            colour, devi = days[n] if days else (f.colours[0], "")
            return {
                "key": key, "name": f.name, "today": True, "in_days": 0, "date": today.isoformat(),
                "colour": colour, "colours": [colour] if days else list(f.colours),
                "day_label": f"Day {n + 1}{f' · {devi}' if devi else ''}" if days else "",
                "title": f"{f.name} Day {n + 1}: {colour.title()}" if days else f"{f.name} today",
                "tip": f.tip, "occasion": f.occasion, "style": f.style,
            }
        if start > today and (upcoming is None or start < upcoming[1]):
            upcoming = (key, start, days)
    if upcoming and (upcoming[1] - today) <= timedelta(days=within):
        key, start, days = upcoming
        f = FESTIVALS[key]
        n = (start - today).days
        colour = days[0][0] if days else f.colours[0]
        return {
            "key": key, "name": f.name, "today": False, "in_days": n, "date": start.isoformat(),
            "colour": colour, "colours": [colour] if days else list(f.colours), "day_label": "",
            "title": f"{f.name} in {n} day{'s' if n != 1 else ''} ({start.day} {start.strftime('%b')})",
            "tip": f.tip, "occasion": f.occasion, "style": f.style,
        }
    return None
