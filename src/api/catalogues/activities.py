"""Closed business-activity catalogue, linked to risk.

The manager's point: "Business activity has to be a closed catalogue so a risk
can be attached to it — Crypto = automatic high risk." A free-text field cannot
carry a weight; a code can. Each category maps to NACE Rev. 2 divisions (so a
NACE code auto-selects the category) and to a default risk impact that seeds
the standard methodology's ACTIVITY_IN factor. Free text typed before this
catalogue existed is recoded by keyword (`to_activity_code`), and what could
not be recoded is kept verbatim so nothing a human wrote is lost.
"""
import re

# code, label, NACE division/group prefixes, default impact, high_risk
ACTIVITIES = [
    ("VASP_CRYPTO", "Virtual assets / crypto (VASP)", ["66.19", "64.99", "63.11"], 25, True),
    ("GAMBLING", "Gambling, betting & casinos", ["92"], 25, True),
    ("MSB_PAYMENTS", "Money services, remittance & payments (MSB / PSP / e-money)", [], 25, True),
    ("ARMS_DEFENCE", "Arms, defence & dual-use goods", ["25.40", "30.40"], 25, True),
    ("CORRESPONDENT_BANKING", "Correspondent banking", [], 25, True),
    ("PRECIOUS_METALS", "Precious metals, stones & jewellery", ["24.41", "32.12", "46.72", "47.77"], 20, True),
    ("HOLDING_SHELL", "Holding / SPV / shell company", ["64.20", "70.10"], 20, True),
    ("REAL_ESTATE", "Real estate & property development", ["68", "41.10"], 15, False),
    ("NPO_CHARITY", "Non-profit, charity & religious organisation", ["94"], 15, False),
    ("ART_ANTIQUES", "Art, antiques & auction houses", ["47.78", "47.79", "90.03", "91"], 15, False),
    ("OTHER_FINANCIAL", "Other financial services (non-bank)", ["64.9", "66.1", "66.2", "66.3"], 15, False),
    ("TCSP", "Trust & company service providers", [], 15, False),
    ("CASH_INTENSIVE", "Cash-intensive business (bars, car washes, vending…)", [], 15, False),
    ("PUBLIC_SECTOR", "Public administration & state-owned entities", ["84"], 10, False),
    ("OIL_GAS_MINING", "Oil, gas & mining", ["05", "06", "07", "08", "09", "19"], 10, False),
    ("WHOLESALE_TRADE", "Wholesale & import / export", ["46"], 10, False),
    ("FUNDS_ASSET_MGMT", "Investment funds & asset management", ["64.30", "66.30"], 10, False),
    ("BANKING_REGULATED", "Bank / credit institution (regulated)", ["64.11", "64.19"], 5, False),
    ("INSURANCE", "Insurance & reinsurance", ["65"], 5, False),
    ("PROFESSIONAL_SERVICES", "Legal, accounting & consulting", ["69", "70.2", "71", "73", "74"], 5, False),
    ("CONSTRUCTION", "Construction", ["41", "42", "43"], 5, False),
    ("RETAIL_TRADE", "Retail trade", ["47"], 5, False),
    ("TRANSPORT_LOGISTICS", "Transport, logistics & shipping", ["49", "50", "51", "52", "53"], 5, False),
    ("HOSPITALITY_TRAVEL", "Hospitality, travel & tourism", ["55", "56", "79"], 5, False),
    ("TECHNOLOGY", "Technology, software & data", ["58.2", "62", "63"], 0, False),
    ("TELECOM_MEDIA", "Telecom, media & publishing", ["58", "59", "60", "61"], 0, False),
    ("MANUFACTURING", "Manufacturing (general)", ["1", "2", "3"], 0, False),
    ("HEALTHCARE_PHARMA", "Healthcare & pharma", ["21", "86", "87", "88"], 0, False),
    ("EDUCATION", "Education", ["85"], 0, False),
    ("AGRICULTURE", "Agriculture, forestry & fishing", ["01", "02", "03"], 0, False),
    ("ENERGY_UTILITIES", "Energy & utilities", ["35", "36", "37", "38", "39"], 0, False),
    ("OTHER", "Other (describe)", [], 0, False),
]

CODES = [a[0] for a in ACTIVITIES]
LABELS = {a[0]: a[1] for a in ACTIVITIES}
IMPACTS = {a[0]: a[3] for a in ACTIVITIES}
HIGH_RISK_CODES = {a[0] for a in ACTIVITIES if a[4]}

# Keyword recoding of free text. Order matters: specific before generic.
_KEYWORDS = [
    ("VASP_CRYPTO", r"crypto|bitcoin|ethereum|virtual asset|vasp|digital asset|blockchain|token|defi|nft"),
    ("GAMBLING", r"casino|gambl|betting|bookmak|lottery|poker|igaming"),
    ("ARMS_DEFENCE", r"\barms\b|weapon|defen[cs]e|ammunition|military|dual[- ]use"),
    ("PRECIOUS_METALS", r"gold|silver|precious|jewel|diamond|gemstone|bullion"),
    ("CORRESPONDENT_BANKING", r"correspondent"),
    ("MSB_PAYMENTS", r"money service|money transfer|remittance|payment|psp\b|e-?money|electronic money|forex|bureau de change|currency exchange|fx broker|money exchange"),
    ("HOLDING_SHELL", r"holding|\bspv\b|special purpose|shell compan"),
    ("TCSP", r"trust (and|&) company|corporate service|fiduciar|trustee service|company formation|registered agent"),
    ("FUNDS_ASSET_MGMT", r"asset manag|fund manag|investment fund|hedge fund|private equity|\bfund\b|wealth manag|portfolio manag|aifm|ucits"),
    ("BANKING_REGULATED", r"\bbank\b|banking|credit institution|savings"),
    ("INSURANCE", r"insur|reinsur|assurance"),
    ("OTHER_FINANCIAL", r"financ|lending|leasing|factoring|broker|securities|fintech"),
    ("REAL_ESTATE", r"real estate|property|immobil|realty|estate agen"),
    ("NPO_CHARITY", r"charit|non[- ]?profit|ngo\b|foundation|church|religio|association"),
    ("ART_ANTIQUES", r"\bart\b|antique|auction|gallery|collectible"),
    ("CASH_INTENSIVE", r"cash[- ]intensive|car wash|vending|laundromat|nightclub|\bbar\b"),
    ("OIL_GAS_MINING", r"\boil\b|\bgas\b|petrol|mining|mineral|extraction"),
    ("PUBLIC_SECTOR", r"government|public admin|state[- ]owned|municipal|ministry|embassy"),
    ("CONSTRUCTION", r"construct|building|contractor|civil engineering"),
    ("WHOLESALE_TRADE", r"wholesale|import|export|trading|commodit|distribut"),
    ("RETAIL_TRADE", r"retail|shop|store|e-?commerce|supermarket|boutique"),
    ("TRANSPORT_LOGISTICS", r"transport|logistic|shipping|freight|maritime|airline|courier"),
    ("HOSPITALITY_TRAVEL", r"hotel|restaurant|travel|tourism|hospitality|caf[eé]|catering"),
    ("HEALTHCARE_PHARMA", r"health|pharma|medical|clinic|hospital|biotech"),
    ("EDUCATION", r"school|education|universit|training|academy"),
    ("AGRICULTURE", r"agri|farm|fishing|fisher|forest|livestock"),
    ("ENERGY_UTILITIES", r"energy|utilit|electric|solar|wind power|water supply|waste"),
    ("TECHNOLOGY", r"software|technolog|\bsaas\b|\bit\b|data|cloud|app development|digital"),
    ("TELECOM_MEDIA", r"telecom|media|publishing|broadcast|advertis|marketing"),
    ("MANUFACTURING", r"manufactur|factory|industrial|production"),
    ("PROFESSIONAL_SERVICES", r"law firm|legal|lawyer|accounting|audit|consult|advisory|notary"),
]
_COMPILED = [(code, re.compile(rx, re.I)) for code, rx in _KEYWORDS]


def to_activity_code(value):
    """Catalogue code for a code, a label or free text — None if nothing fits.
    Never raises."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    up = s.upper().replace(" ", "_").replace("-", "_")
    if up in LABELS:
        return up
    low = s.lower()
    for code, label in LABELS.items():
        if low == label.lower():
            return code
    for code, rx in _COMPILED:
        if rx.search(s):
            return code
    return None


def normalize_or_keep(value):
    if value is None:
        return None
    code = to_activity_code(value)
    if code:
        return code
    s = str(value).strip()
    return s or None


def activity_label(code):
    if not code:
        return None
    return LABELS.get(str(code).upper(), code)


def is_high_risk(value):
    return to_activity_code(value) in HIGH_RISK_CODES


def activity_from_nace(nace):
    """Best category for a NACE Rev. 2 code ('64.19', '6419', '64.1', '92')."""
    if not nace:
        return None
    digits = re.sub(r"[^0-9]", "", str(nace))
    if not digits:
        return None
    dotted = digits[:2] + ("." + digits[2:4] if len(digits) > 2 else "")
    best, best_len = None, 0
    for code, _label, prefixes, _i, _h in ACTIVITIES:
        for p in prefixes:
            pd = p.replace(".", "")
            if digits.startswith(pd) and len(pd) > best_len:
                best, best_len = code, len(pd)
    return best


def catalogue():
    return [{"code": c, "label": l, "nace": n, "default_impact": i, "high_risk": h}
            for c, l, n, i, h in ACTIVITIES]
