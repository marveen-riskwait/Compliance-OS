"""ISO 3166-1 alpha-2 country catalogue.

Why codes and not names: the risk engine, the transaction monitor and the
public data sources all compare countries. A free-text field ("Iran",
"Islamic Republic of Iran", "IR") silently fails those comparisons — a
customer typed as "Iran (Islamic Republic of)" never matched the FATF list.
Storing the two-letter code makes every join exact, and the UI shows the name.

`to_iso2()` is deliberately forgiving on input (code, English name, common
aliases, "US-CA"-style prefixes) and strict on output: a code or None.
"""
import re

# (code, English short name)
COUNTRIES = [
    ("AF", "Afghanistan"), ("AX", "Åland Islands"), ("AL", "Albania"), ("DZ", "Algeria"),
    ("AS", "American Samoa"), ("AD", "Andorra"), ("AO", "Angola"), ("AI", "Anguilla"),
    ("AQ", "Antarctica"), ("AG", "Antigua and Barbuda"), ("AR", "Argentina"), ("AM", "Armenia"),
    ("AW", "Aruba"), ("AU", "Australia"), ("AT", "Austria"), ("AZ", "Azerbaijan"),
    ("BS", "Bahamas"), ("BH", "Bahrain"), ("BD", "Bangladesh"), ("BB", "Barbados"),
    ("BY", "Belarus"), ("BE", "Belgium"), ("BZ", "Belize"), ("BJ", "Benin"),
    ("BM", "Bermuda"), ("BT", "Bhutan"), ("BO", "Bolivia"), ("BQ", "Bonaire, Sint Eustatius and Saba"),
    ("BA", "Bosnia and Herzegovina"), ("BW", "Botswana"), ("BV", "Bouvet Island"), ("BR", "Brazil"),
    ("IO", "British Indian Ocean Territory"), ("BN", "Brunei Darussalam"), ("BG", "Bulgaria"), ("BF", "Burkina Faso"),
    ("BI", "Burundi"), ("CV", "Cabo Verde"), ("KH", "Cambodia"), ("CM", "Cameroon"),
    ("CA", "Canada"), ("KY", "Cayman Islands"), ("CF", "Central African Republic"), ("TD", "Chad"),
    ("CL", "Chile"), ("CN", "China"), ("CX", "Christmas Island"), ("CC", "Cocos (Keeling) Islands"),
    ("CO", "Colombia"), ("KM", "Comoros"), ("CG", "Congo"), ("CD", "Congo, Democratic Republic of the"),
    ("CK", "Cook Islands"), ("CR", "Costa Rica"), ("CI", "Côte d'Ivoire"), ("HR", "Croatia"),
    ("CU", "Cuba"), ("CW", "Curaçao"), ("CY", "Cyprus"), ("CZ", "Czechia"),
    ("DK", "Denmark"), ("DJ", "Djibouti"), ("DM", "Dominica"), ("DO", "Dominican Republic"),
    ("EC", "Ecuador"), ("EG", "Egypt"), ("SV", "El Salvador"), ("GQ", "Equatorial Guinea"),
    ("ER", "Eritrea"), ("EE", "Estonia"), ("SZ", "Eswatini"), ("ET", "Ethiopia"),
    ("FK", "Falkland Islands"), ("FO", "Faroe Islands"), ("FJ", "Fiji"), ("FI", "Finland"),
    ("FR", "France"), ("GF", "French Guiana"), ("PF", "French Polynesia"), ("TF", "French Southern Territories"),
    ("GA", "Gabon"), ("GM", "Gambia"), ("GE", "Georgia"), ("DE", "Germany"),
    ("GH", "Ghana"), ("GI", "Gibraltar"), ("GR", "Greece"), ("GL", "Greenland"),
    ("GD", "Grenada"), ("GP", "Guadeloupe"), ("GU", "Guam"), ("GT", "Guatemala"),
    ("GG", "Guernsey"), ("GN", "Guinea"), ("GW", "Guinea-Bissau"), ("GY", "Guyana"),
    ("HT", "Haiti"), ("HM", "Heard Island and McDonald Islands"), ("VA", "Holy See"), ("HN", "Honduras"),
    ("HK", "Hong Kong"), ("HU", "Hungary"), ("IS", "Iceland"), ("IN", "India"),
    ("ID", "Indonesia"), ("IR", "Iran"), ("IQ", "Iraq"), ("IE", "Ireland"),
    ("IM", "Isle of Man"), ("IL", "Israel"), ("IT", "Italy"), ("JM", "Jamaica"),
    ("JP", "Japan"), ("JE", "Jersey"), ("JO", "Jordan"), ("KZ", "Kazakhstan"),
    ("KE", "Kenya"), ("KI", "Kiribati"), ("KP", "North Korea"), ("KR", "South Korea"),
    ("KW", "Kuwait"), ("KG", "Kyrgyzstan"), ("LA", "Laos"), ("LV", "Latvia"),
    ("LB", "Lebanon"), ("LS", "Lesotho"), ("LR", "Liberia"), ("LY", "Libya"),
    ("LI", "Liechtenstein"), ("LT", "Lithuania"), ("LU", "Luxembourg"), ("MO", "Macao"),
    ("MG", "Madagascar"), ("MW", "Malawi"), ("MY", "Malaysia"), ("MV", "Maldives"),
    ("ML", "Mali"), ("MT", "Malta"), ("MH", "Marshall Islands"), ("MQ", "Martinique"),
    ("MR", "Mauritania"), ("MU", "Mauritius"), ("YT", "Mayotte"), ("MX", "Mexico"),
    ("FM", "Micronesia"), ("MD", "Moldova"), ("MC", "Monaco"), ("MN", "Mongolia"),
    ("ME", "Montenegro"), ("MS", "Montserrat"), ("MA", "Morocco"), ("MZ", "Mozambique"),
    ("MM", "Myanmar"), ("NA", "Namibia"), ("NR", "Nauru"), ("NP", "Nepal"),
    ("NL", "Netherlands"), ("NC", "New Caledonia"), ("NZ", "New Zealand"), ("NI", "Nicaragua"),
    ("NE", "Niger"), ("NG", "Nigeria"), ("NU", "Niue"), ("NF", "Norfolk Island"),
    ("MK", "North Macedonia"), ("MP", "Northern Mariana Islands"), ("NO", "Norway"), ("OM", "Oman"),
    ("PK", "Pakistan"), ("PW", "Palau"), ("PS", "Palestine"), ("PA", "Panama"),
    ("PG", "Papua New Guinea"), ("PY", "Paraguay"), ("PE", "Peru"), ("PH", "Philippines"),
    ("PN", "Pitcairn"), ("PL", "Poland"), ("PT", "Portugal"), ("PR", "Puerto Rico"),
    ("QA", "Qatar"), ("RE", "Réunion"), ("RO", "Romania"), ("RU", "Russia"),
    ("RW", "Rwanda"), ("BL", "Saint Barthélemy"), ("SH", "Saint Helena"), ("KN", "Saint Kitts and Nevis"),
    ("LC", "Saint Lucia"), ("MF", "Saint Martin"), ("PM", "Saint Pierre and Miquelon"), ("VC", "Saint Vincent and the Grenadines"),
    ("WS", "Samoa"), ("SM", "San Marino"), ("ST", "Sao Tome and Principe"), ("SA", "Saudi Arabia"),
    ("SN", "Senegal"), ("RS", "Serbia"), ("SC", "Seychelles"), ("SL", "Sierra Leone"),
    ("SG", "Singapore"), ("SX", "Sint Maarten"), ("SK", "Slovakia"), ("SI", "Slovenia"),
    ("SB", "Solomon Islands"), ("SO", "Somalia"), ("ZA", "South Africa"), ("GS", "South Georgia and the South Sandwich Islands"),
    ("SS", "South Sudan"), ("ES", "Spain"), ("LK", "Sri Lanka"), ("SD", "Sudan"),
    ("SR", "Suriname"), ("SJ", "Svalbard and Jan Mayen"), ("SE", "Sweden"), ("CH", "Switzerland"),
    ("SY", "Syria"), ("TW", "Taiwan"), ("TJ", "Tajikistan"), ("TZ", "Tanzania"),
    ("TH", "Thailand"), ("TL", "Timor-Leste"), ("TG", "Togo"), ("TK", "Tokelau"),
    ("TO", "Tonga"), ("TT", "Trinidad and Tobago"), ("TN", "Tunisia"), ("TR", "Türkiye"),
    ("TM", "Turkmenistan"), ("TC", "Turks and Caicos Islands"), ("TV", "Tuvalu"), ("UG", "Uganda"),
    ("UA", "Ukraine"), ("AE", "United Arab Emirates"), ("GB", "United Kingdom"), ("US", "United States"),
    ("UM", "United States Minor Outlying Islands"), ("UY", "Uruguay"), ("UZ", "Uzbekistan"), ("VU", "Vanuatu"),
    ("VE", "Venezuela"), ("VN", "Vietnam"), ("VG", "Virgin Islands, British"), ("VI", "Virgin Islands, U.S."),
    ("WF", "Wallis and Futuna"), ("EH", "Western Sahara"), ("YE", "Yemen"), ("ZM", "Zambia"),
    ("ZW", "Zimbabwe"), ("XK", "Kosovo"),
]

CODES = {c for c, _ in COUNTRIES}
NAMES = dict(COUNTRIES)

# Common spellings that are not the short name above. Lower-case keys.
ALIASES = {
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB", "england": "GB",
    "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "united kingdom of great britain and northern ireland": "GB",
    "usa": "US", "u.s.": "US", "u.s.a.": "US", "united states of america": "US", "america": "US",
    "russian federation": "RU", "russia federation": "RU",
    "islamic republic of iran": "IR", "iran, islamic republic of": "IR", "iran (islamic republic of)": "IR",
    "dprk": "KP", "korea, democratic people's republic of": "KP", "democratic people's republic of korea": "KP",
    "korea (democratic people's republic of)": "KP", "korea, north": "KP",
    "korea, republic of": "KR", "republic of korea": "KR", "korea (republic of)": "KR", "korea, south": "KR", "korea": "KR",
    "syrian arab republic": "SY", "syria arab republic": "SY",
    "burma": "MM", "myanmar (burma)": "MM",
    "viet nam": "VN", "lao people's democratic republic": "LA", "lao pdr": "LA",
    "czech republic": "CZ", "turkey": "TR", "turkiye": "TR",
    "uae": "AE", "emirates": "AE", "hong kong sar": "HK", "hong kong, china": "HK", "macau": "MO", "macao sar": "MO",
    "taiwan, province of china": "TW", "republic of china": "TW",
    "bolivia (plurinational state of)": "BO", "plurinational state of bolivia": "BO",
    "venezuela (bolivarian republic of)": "VE", "bolivarian republic of venezuela": "VE",
    "tanzania, united republic of": "TZ", "united republic of tanzania": "TZ",
    "moldova, republic of": "MD", "republic of moldova": "MD",
    "micronesia (federated states of)": "FM", "federated states of micronesia": "FM",
    "the netherlands": "NL", "holland": "NL", "the bahamas": "BS", "the gambia": "GM",
    "ivory coast": "CI", "cote d'ivoire": "CI", "cape verde": "CV", "swaziland": "SZ",
    "macedonia": "MK", "republic of north macedonia": "MK", "east timor": "TL",
    "vatican": "VA", "vatican city": "VA", "state of palestine": "PS", "palestinian territory": "PS",
    "congo, the democratic republic of the": "CD", "democratic republic of the congo": "CD", "dr congo": "CD", "drc": "CD",
    "republic of the congo": "CG", "congo-brazzaville": "CG", "congo-kinshasa": "CD",
    "brunei": "BN", "saint helena, ascension and tristan da cunha": "SH", "st. lucia": "LC", "st lucia": "LC",
    "st. kitts and nevis": "KN", "st kitts and nevis": "KN", "st. vincent and the grenadines": "VC",
    "falkland islands (malvinas)": "FK", "british virgin islands": "VG", "bvi": "VG", "us virgin islands": "VI",
    "sao tome & principe": "ST", "são tomé and príncipe": "ST", "trinidad & tobago": "TT", "antigua & barbuda": "AG",
    "bosnia": "BA", "kosovo": "XK", "réunion": "RE", "reunion": "RE", "curacao": "CW",
    "aland islands": "AX", "eu": None, "european union": None, "unknown": None, "n/a": None, "": None,
}


# Nationality is often typed as an adjective ("British", "French"). Lower-case.
DEMONYMS = {
    "british": "GB", "english": "GB", "scottish": "GB", "welsh": "GB", "american": "US",
    "french": "FR", "german": "DE", "luxembourgish": "LU", "luxembourger": "LU", "belgian": "BE",
    "dutch": "NL", "swiss": "CH", "spanish": "ES", "italian": "IT", "portuguese": "PT", "irish": "IE",
    "austrian": "AT", "polish": "PL", "czech": "CZ", "slovak": "SK", "hungarian": "HU", "romanian": "RO",
    "bulgarian": "BG", "greek": "GR", "cypriot": "CY", "maltese": "MT", "danish": "DK", "swedish": "SE",
    "norwegian": "NO", "finnish": "FI", "icelandic": "IS", "estonian": "EE", "latvian": "LV",
    "lithuanian": "LT", "croatian": "HR", "slovenian": "SI", "serbian": "RS", "bosnian": "BA",
    "albanian": "AL", "ukrainian": "UA", "russian": "RU", "belarusian": "BY", "turkish": "TR",
    "israeli": "IL", "lebanese": "LB", "syrian": "SY", "iranian": "IR", "iraqi": "IQ", "saudi": "SA",
    "emirati": "AE", "qatari": "QA", "kuwaiti": "KW", "egyptian": "EG", "moroccan": "MA", "algerian": "DZ",
    "tunisian": "TN", "libyan": "LY", "nigerian": "NG", "ghanaian": "GH", "kenyan": "KE",
    "south african": "ZA", "ethiopian": "ET", "congolese": "CD", "senegalese": "SN", "ivorian": "CI",
    "indian": "IN", "pakistani": "PK", "bangladeshi": "BD", "sri lankan": "LK", "chinese": "CN",
    "hong konger": "HK", "taiwanese": "TW", "japanese": "JP", "korean": "KR", "south korean": "KR",
    "north korean": "KP", "vietnamese": "VN", "thai": "TH", "malaysian": "MY", "singaporean": "SG",
    "indonesian": "ID", "filipino": "PH", "australian": "AU", "new zealander": "NZ", "canadian": "CA",
    "mexican": "MX", "brazilian": "BR", "argentinian": "AR", "argentine": "AR", "chilean": "CL",
    "colombian": "CO", "peruvian": "PE", "venezuelan": "VE", "panamanian": "PA", "cuban": "CU",
    "jamaican": "JM", "monegasque": "MC", "liechtensteiner": "LI", "burmese": "MM", "kazakh": "KZ",
    "uzbek": "UZ", "georgian": "GE", "armenian": "AM", "azerbaijani": "AZ", "afghan": "AF", "yemeni": "YE",
}

_NAME_TO_CODE = {name.lower(): code for code, name in COUNTRIES}
_NAME_TO_CODE.update({k: v for k, v in ALIASES.items() if v})
_NAME_TO_CODE.update(DEMONYMS)
_NULL_WORDS = {k for k, v in ALIASES.items() if v is None}
_STRIP = re.compile(r"[‘’`´]")


def _clean(value):
    s = _STRIP.sub("'", str(value or "")).strip()
    return re.sub(r"\s+", " ", s)


def to_iso2(value):
    """Return the ISO 3166-1 alpha-2 code for a code, a name or an alias — or
    None when the value is empty / not recognised. Never raises."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
        if value is None:
            return None
    s = _clean(value)
    if not s:
        return None
    low = s.lower()
    if low in _NULL_WORDS:
        return None
    up = s.upper()
    if len(up) == 2 and up in CODES:
        return up
    # "US-CA" (SEC EDGAR state of incorporation), "GB-ENG", "FR - Paris"
    m = re.match(r"^([A-Za-z]{2})\s*[-/]", s)
    if m and m.group(1).upper() in CODES:
        return m.group(1).upper()
    if low in _NAME_TO_CODE:
        return _NAME_TO_CODE[low]
    # "Iran (Islamic Republic of)" -> try the head before a parenthesis / comma
    head = re.split(r"[(,]", low)[0].strip()
    if head and head in _NAME_TO_CODE:
        return _NAME_TO_CODE[head]
    # "The Netherlands" / "Republic of X"
    for prefix in ("the ", "republic of ", "kingdom of ", "state of ", "federal republic of "):
        if low.startswith(prefix) and low[len(prefix):] in _NAME_TO_CODE:
            return _NAME_TO_CODE[low[len(prefix):]]
    return None


def is_iso2(value):
    return isinstance(value, str) and len(value) == 2 and value.upper() in CODES


def country_name(code):
    """English name for a code; the value itself when it is not a code (so
    legacy free text still displays)."""
    if not code:
        return None
    return NAMES.get(str(code).upper(), code)


def normalize_or_keep(value):
    """Best effort for stored data: the code when recognised, else the
    trimmed original (never silently drop what a human typed)."""
    if value is None:
        return None
    code = to_iso2(value)
    if code:
        return code
    s = _clean(value)
    return s or None


def same_country(a, b):
    """Compare two country values regardless of format."""
    ca, cb = to_iso2(a), to_iso2(b)
    if ca and cb:
        return ca == cb
    return _clean(a).lower() == _clean(b).lower() and bool(_clean(a))


def catalogue():
    return [{"code": c, "name": n} for c, n in sorted(COUNTRIES, key=lambda x: x[1])]
