"""JSON Label Printer — stlite edition.

Runs entirely in the browser (via Marco's streamlit2stlite -> stlite/Pyodide).
Additional sibling of the Chemical and Text Label Printers: same print box,
same WebUSB Dymo pipeline, same 1000x350 label canvas and the same
calibrated chemical-label geometry — only the form changes. Here the user
pastes a JSON string describing ONE OR MORE labels, and the app renders
and prints each of them.

The page documents its own JSON schema in the instruction box at the
bottom, in plain words an AI agent can follow: point a preferred agent
(for example Microsoft 365 Copilot) at this page and ask it to provide
the JSON label strings. No separate Copilot skill — the page itself is
the instruction.

Nothing private is baked into this file. Owner/telephone default to the
same fake demo values as the chemical label app.
"""
import base64
import io
import json
import math
import re
from datetime import date

from PIL import Image, ImageDraw, ImageFont
import qrcode

# --- pure-tests:begin ---
# Everything between the pure-tests markers must not import streamlit,
# so tests can import it standalone.

# ---------------------------------------------------------------- assets ---
# (base64 blobs injected by build_json.py)
_FONT_BOLD_B64 = "__FONT_BOLD_B64__"
_FONT_REG_B64 = "__FONT_REG_B64__"
_SYMBOL_PNG_B64 = __SYMBOLS_JSON__

# ------------------------------------------------------------------ data ---
DEFAULT_OWNER = "Marco C."
DEFAULT_TEL = "555-0100"

MAX_LABELS = 20
MAX_COPIES = 20

# The nine GHS pictogram keys, in the standard GHS order.
GHS_KEYS = [
    "explos", "flamme", "rondflam", "bottle", "acid",
    "skull", "exclam", "silhouette", "pollu",
]

GHS_NAMES = {
    "explos": "Exploding bomb (GHS01)",
    "flamme": "Flame (GHS02)",
    "rondflam": "Flame over circle, oxidizer (GHS03)",
    "bottle": "Gas cylinder (GHS04)",
    "acid": "Corrosion (GHS05)",
    "skull": "Skull and crossbones (GHS06)",
    "exclam": "Exclamation mark (GHS07)",
    "silhouette": "Health hazard (GHS08)",
    "pollu": "Environment (GHS09)",
}

# Standard GHS diamond positions on the label stock (see
# docs/chemical-labels.md): (row, pos) in the 1-2-3-2-1 diamond grid.
# Top: acid. Row 1: silhouette (left), bottle (right). Row 2: pollu
# (left), explos (centre), skull (right). Row 3: flamme (left), exclam
# (right). Bottom: rondflam. Each pictogram has exactly one position;
# the app places it there. Unused diamonds are blacked out.
PICTOGRAM_POSITIONS = {
    "acid": (0, 0),
    "silhouette": (1, 0),
    "bottle": (1, 1),
    "pollu": (2, 0),
    "explos": (2, 1),
    "skull": (2, 2),
    "flamme": (3, 0),
    "exclam": (3, 1),
    "rondflam": (4, 0),
}

SIGNAL_WORDS = ("DANGER", "WARNING")

# --------------------------------------------------------------- geometry ---
# Identical to chem-server/chem_label.py (calibrated 2026-10-18).
CX = 805
ROW_Y = [48, 100, 152, 204, 256]
ROW_X = [
    [CX],
    [CX - 48, CX + 48],
    [CX - 96, CX, CX + 96],
    [CX - 48, CX + 48],
    [CX],
]
SYMBOL_SIZE = 85
BLACKOUT_SIZE = 65
QR_BOX = 3  # 150% bigger QR
NAME_MAX_WIDTH = 640  # px: wider names may run into the diamond grid


def _fonts():
    bold32 = ImageFont.truetype(io.BytesIO(base64.b64decode(_FONT_BOLD_B64)), 32)
    bold30 = ImageFont.truetype(io.BytesIO(base64.b64decode(_FONT_BOLD_B64)), 30)
    reg26 = ImageFont.truetype(io.BytesIO(base64.b64decode(_FONT_REG_B64)), 26)
    return bold32, bold30, reg26


def _symbol(key):
    raw = base64.b64decode(_SYMBOL_PNG_B64[key])
    return Image.open(io.BytesIO(raw))  # mode "1", 85x85, 1 = burned


def _draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def build_label_image(name, signal, h_codes, pictograms, qr_url, owner, tel,
                      expiration_date=None):
    """Render one chemical/sample label. pictograms: list of GHS keys.

    Same layout as chem-server/chem_label.py, plus one extra line at the
    bottom of the left text column: "Exp: YYYY-MM-DD" when an expiration
    date is given. With no expiration date the image is pixel-identical
    to the chemical label app for the same inputs.
    Returns a 1-bit PIL image, 1000x350, 1 = burned.
    """
    _font_name, _font_sig, _font = _fonts()
    H, W = 350, 1000
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    y = 12
    d.text((20, y), name, font=_font_name, fill=1); y += 42
    if signal:
        d.text((20, y), signal, font=_font_sig, fill=1); y += 38
    d.text((20, y), f"Owner: {owner}", font=_font, fill=1); y += 32
    d.text((20, y), f"Tel: {tel}", font=_font, fill=1); y += 32
    if h_codes:
        d.text((20, y), h_codes, font=_font, fill=1); y += 32
    if expiration_date:
        d.text((20, y), f"Exp: {expiration_date}", font=_font, fill=1); y += 32
    if qr_url:
        qr = qrcode.QRCode(box_size=QR_BOX, border=1)
        qr.add_data(qr_url); qr.make(fit=True)
        qi = qr.make_image(fill_color="black", back_color="white").convert("1")
        qi = qi.point(lambda p: 1 if p == 0 else 0)
        qw, qh = qi.size
        img.paste(qi, (W // 2 - qw // 2, H - qh - 8))
    show = {PICTOGRAM_POSITIONS[k]: k for k in (pictograms or [])}
    for row_idx in range(5):
        for pos_idx, cx in enumerate(ROW_X[row_idx]):
            cy = ROW_Y[row_idx]
            if (row_idx, pos_idx) in show:
                sym = _symbol(show[(row_idx, pos_idx)])
                x0 = cx - SYMBOL_SIZE // 2
                y0 = cy - SYMBOL_SIZE // 2
                mask = sym.point(lambda p: 255 if p else 0)
                img.paste(1, (x0, y0), mask)
            else:
                _draw_diamond(d, cx, cy, BLACKOUT_SIZE, fill=1)
    return img


def printer_matrix_b64(img):
    """Mirror of chem_label.print_image's raster pipeline.

    ROTATE_270, pack 1-bit MSB-first, 44 bytes/row x 1000 rows -> base64.
    """
    lr = img.transpose(Image.ROTATE_270)
    ls = lr.tobytes()
    rl = int(math.ceil(img.height / 8))
    rows = [ls[i:i + rl] for i in range(0, len(ls), rl)]
    assert len(rows) == 1000 and all(len(r) == rl for r in rows), \
        f"unexpected matrix {(len(rows), len(rows[0]))}"
    return base64.b64encode(b"".join(rows)).decode()


# ------------------------------------------------------------- validation ---
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LABEL_FIELDS = {
    "name", "signal", "h_codes", "ghs_pictograms", "qr_url",
    "expiration_date", "owner", "tel", "copies",
}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def parse_labels_json(text):
    """Parse the pasted JSON string into a list of label dicts.

    Returns (labels, errors, warnings). labels is a list of normalized
    dicts (empty when errors is non-empty). Every error names the
    offending field, e.g. labels[1].signal. Warnings never block printing.
    """
    errors, warnings = [], []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [f"Invalid JSON: {exc}"], []
    if isinstance(data, list):
        data = {"labels": data}
    elif isinstance(data, dict) and "labels" not in data and "name" in data:
        data = {"labels": [data]}
    if not isinstance(data, dict):
        return [], ["Top level must be a JSON object (or an array of labels)."], []
    if "labels" not in data:
        return [], ["Top level must contain a 'labels' array (or be a single "
                    "label object with a 'name')."], []
    owner_default = data.get("owner", DEFAULT_OWNER)
    tel_default = data.get("tel", DEFAULT_TEL)
    if not isinstance(owner_default, str):
        errors.append("owner: must be a string.")
    if not isinstance(tel_default, str):
        errors.append("tel: must be a string.")
    raw_labels = data["labels"]
    if not isinstance(raw_labels, list) or not raw_labels:
        errors.append("labels: must be a non-empty array of label objects.")
        return [], errors, warnings
    if len(raw_labels) > MAX_LABELS:
        errors.append(f"labels: at most {MAX_LABELS} labels per JSON string "
                      f"(got {len(raw_labels)}).")
        return [], errors, warnings
    labels = []
    for i, raw in enumerate(raw_labels):
        where = f"labels[{i}]"
        if not isinstance(raw, dict):
            errors.append(f"{where}: must be an object.")
            continue
        for key in sorted(raw):
            if key not in _LABEL_FIELDS:
                warnings.append(f"{where}.{key}: unknown field — ignored.")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{where}.name: required, must be a non-empty string.")
            continue
        signal = raw.get("signal")
        if signal is not None:
            if not isinstance(signal, str) or signal.upper() not in SIGNAL_WORDS:
                errors.append(f"{where}.signal: must be 'DANGER', 'WARNING' "
                              "or null.")
                continue
            signal = signal.upper()
        h_codes = raw.get("h_codes")
        if h_codes is not None and not isinstance(h_codes, str):
            errors.append(f"{where}.h_codes: must be a string or null.")
            continue
        pictograms = raw.get("ghs_pictograms") or []
        if not isinstance(pictograms, list):
            errors.append(f"{where}.ghs_pictograms: must be an array of "
                          "pictogram names or an empty array.")
            continue
        bad = [p for p in pictograms
               if not isinstance(p, str) or p not in GHS_KEYS]
        if bad:
            errors.append(f"{where}.ghs_pictograms: unknown pictogram(s) "
                          f"{bad} — use only: {', '.join(GHS_KEYS)}.")
            continue
        if len(set(pictograms)) != len(pictograms):
            errors.append(f"{where}.ghs_pictograms: list each pictogram at "
                          "most once.")
            continue
        qr_url = raw.get("qr_url")
        if qr_url is not None and (not isinstance(qr_url, str) or not qr_url):
            errors.append(f"{where}.qr_url: must be a web address string "
                          "or null.")
            continue
        expiration_date = raw.get("expiration_date")
        if expiration_date is not None:
            if (not isinstance(expiration_date, str)
                    or not _DATE_RE.match(expiration_date)):
                errors.append(f"{where}.expiration_date: must be a date in "
                              "YYYY-MM-DD format, e.g. '2027-03-15'.")
                continue
            try:
                date.fromisoformat(expiration_date)
            except ValueError:
                errors.append(f"{where}.expiration_date: "
                              f"'{expiration_date}' is not a real calendar date.")
                continue
        copies = raw.get("copies", 1)
        if not _is_int(copies) or not 1 <= copies <= MAX_COPIES:
            errors.append(f"{where}.copies: must be a whole number from 1 "
                          f"to {MAX_COPIES}.")
            continue
        owner = raw.get("owner", owner_default)
        tel = raw.get("tel", tel_default)
        if not isinstance(owner, str) or not isinstance(tel, str):
            errors.append(f"{where}.owner / {where}.tel: must be strings.")
            continue
        labels.append({
            "name": name.strip(),
            "signal": signal,
            "h_codes": (h_codes.strip() if isinstance(h_codes, str) else None),
            "pictograms": list(pictograms),
            "qr_url": qr_url,
            "expiration_date": expiration_date,
            "owner": owner,
            "tel": tel,
            "copies": copies,
        })
        try:
            _font_name, _, _ = _fonts()
            probe = ImageDraw.Draw(Image.new("1", (10, 10), 0))
            bbox = probe.textbbox((0, 0), name.strip(), font=_font_name)
            if bbox[2] - bbox[0] > NAME_MAX_WIDTH:
                warnings.append(f"{where}.name: very long — it may run into "
                                "the diamond grid; shorten the name.")
        except Exception:
            pass
        if isinstance(qr_url, str) and len(qr_url) > 120:
            warnings.append(f"{where}.qr_url: very long — the QR code will "
                            "be large and may crowd the text; prefer a short "
                            "SDS link.")
    if errors:
        return [], errors, warnings
    return labels, [], warnings


# -------------------------------------------------------------- sample data ---
SAMPLE_JSON = """{
  "owner": "Marco C.",
  "tel": "555-0100",
  "labels": [
    {
      "name": "Sodium Lauryl Sulfate",
      "signal": "DANGER",
      "h_codes": "H228 H302+H332 H315 H318 H335 H412",
      "ghs_pictograms": ["acid", "flamme", "exclam"],
      "qr_url": "https://old.scharlab.com/docs/msds/descargarpdf.php?path=SO0499_EN.pdf&idid=EN",
      "expiration_date": "2027-03-15",
      "copies": 2
    },
    {
      "name": "Water",
      "signal": null,
      "h_codes": null,
      "ghs_pictograms": [],
      "qr_url": "https://pubchem.ncbi.nlm.nih.gov/compound/962",
      "expiration_date": "2028-01-01",
      "copies": 1
    }
  ]
}"""

TOP_TEXT = """Paste a JSON string below to print one or more chemical/sample
labels on the Dymo LabelWriter 450 Turbo plugged into this computer. This
is the JSON edition of the muse-print label apps: the same label as the
chemical label app, driven by JSON instead of a form.

Point your preferred AI agent — for example Microsoft 365 Copilot — at this
page and ask it to provide the JSON label strings for a set of ingredients,
or for a single ingredient. The full JSON schema is documented in the
instruction box at the bottom of this page. The agent may ask you for
missing information, or look it up online, for example from the ingredient's
safety data sheet (SDS). Then paste the JSON below, check the previews, and
print each label with its yellow Print button. Nothing is uploaded: the JSON
never leaves this page."""

SCHEMA_DOC = """This page prints chemical/sample labels from a JSON string.
It is written so an AI agent can read it and generate the JSON. If you are
an agent: read this whole box, then produce the JSON described below.

WHAT THE APP DOES

The user pastes one JSON string into the text box at the top of this page.
The JSON describes one or more labels. The app renders each label on the
same 1000 by 350 canvas as the muse-print chemical label app — chemical
name, GHS signal word, owner, telephone, hazard codes, GHS pictograms in
the diamond grid, a QR code, and an expiration date — and prints each label
on the Dymo LabelWriter 450 Turbo plugged into this computer, over WebUSB.
The user checks the preview of every label before printing.

THE JSON SHAPE

The top level is one JSON object with two optional defaults and one
required array:

    {
      "owner": "Marco C.",
      "tel": "555-0100",
      "labels": [ ... one object per label, in print order ... ]
    }

Shortcuts the app also accepts: a bare array of label objects is treated
as the labels array, and a bare single label object (with a name and no
labels key) is treated as one label.

FIELD BY FIELD — each label object

- name (required, text): the chemical or sample name. Printed at the top
  of the label in bold. Example: Sodium Lauryl Sulfate.
- signal (optional, text or null): the GHS signal word — exactly DANGER,
  exactly WARNING, or null when the substance has no signal word. Printed
  under the name. Water has null.
- h_codes (optional, text or null): the hazard statements, as one
  space-separated string, for example H315 H319. Printed under the
  telephone line. Null when there are none.
- ghs_pictograms (optional, array of text, may be empty): the GHS
  pictograms to show in the diamond grid on the right of the label. Use
  ONLY these nine exact words, each at most once: explos, flamme,
  rondflam, bottle, acid, skull, exclam, silhouette, pollu. The app
  places each pictogram in its standard diamond position (see below); the
  agent only lists which ones apply and never gives positions. Diamonds
  with no pictogram are printed blacked out.
- qr_url (optional, text or null): the web address encoded in the QR code
  at the bottom of the label — usually the safety data sheet (SDS) or the
  PubChem page for the chemical. Null means no QR code. Prefer short
  links: a very long address makes a large QR code.
- expiration_date (optional, text or null): the expiry date of the sample
  on this label, ALWAYS in YYYY-MM-DD format, for example 2027-03-15.
  Printed as Exp: 2027-03-15. Null or omitted means no expiry line.
  Never write it as March 15, 2027 or 15/03/2027.
- owner (optional, text): the name printed as Owner: ... If omitted on a
  label, the top-level owner is used; if that is missing too, the app
  uses its demo default.
- tel (optional, text): the telephone printed as Tel: ... Same fallback
  as owner.
- copies (optional, whole number from 1 to 20, default 1): how many
  copies of THIS label to print.

Top-level owner and tel (optional, text): defaults applied to every label
that does not set its own.

WHERE EACH PICTOGRAM GOES — the app places them, the agent only names them

- Top diamond: acid (corrosion, GHS05)
- Row 1, left: silhouette (health hazard, GHS08); right: bottle (gas
  cylinder, GHS04)
- Row 2, left: pollu (environment, GHS09); centre: explos (exploding
  bomb, GHS01); right: skull (skull and crossbones, GHS06)
- Row 3, left: flamme (flame, GHS02); right: exclam (exclamation mark,
  GHS07)
- Bottom diamond: rondflam (flame over circle, oxidizer, GHS03)

RULES FOR GENERATING THE JSON

Output ONLY the JSON object, no explanatory text around it. Use exactly
the field names above. Use null (not an empty string) for a missing
signal, h_codes, qr_url, or expiration_date. Keep ghs_pictograms to the
nine words listed. Keep dates in YYYY-MM-DD. At most 20 labels per JSON
string. If the user does not give an expiration date, leave the field
out or set it to null — never guess a date.

WHERE TO LOOK UP THE FACTS (SDS SOURCES)

For a typical consumer-product ingredient (shampoo, skin cream, and so
on), look up the GHS signal word, H-codes, pictograms, and SDS link in
one of these reputable sources, in this order:

- PubChem — https://pubchem.ncbi.nlm.nih.gov/ — search the ingredient
  by name or CAS number; the GHS Classification section lists the signal
  word, hazard statements, and pictograms.
- ECHA (European Chemicals Agency) — https://echa.europa.eu/ — search
  the substance; the Classification and Labelling data gives the
  harmonised classification.
- Sigma-Aldrich SDS search — https://www.sigmaaldrich.com/US/en/search/sds
  — search by CAS number or product name for the supplier safety data
  sheet.
- The chemical supplier's own SDS page (for example Scharlab, Fisher
  Scientific, or the manufacturer of the ingredient).

If sources disagree, prefer the supplier SDS for the exact product the
user has. If a fact cannot be found, ask the user instead of guessing.

EXAMPLE — ask the agent like this

Open this page and read the label schema in the instruction box at the
bottom. Then make me the JSON for these samples: (list them). For each
one, look up the GHS signal word, H-codes, pictograms, and SDS link,
and use the expiration date I give you. Output only the JSON, so I can
paste it into the app and print.

EXAMPLE JSON — two labels

    {
      "owner": "Marco C.",
      "tel": "555-0100",
      "labels": [
        {
          "name": "Sodium Lauryl Sulfate",
          "signal": "DANGER",
          "h_codes": "H228 H302+H332 H315 H318 H335 H412",
          "ghs_pictograms": ["acid", "flamme", "exclam"],
          "qr_url": "https://old.scharlab.com/docs/msds/descargarpdf.php?path=SO0499_EN.pdf&idid=EN",
          "expiration_date": "2027-03-15",
          "copies": 2
        },
        {
          "name": "Water",
          "signal": null,
          "h_codes": null,
          "ghs_pictograms": [],
          "qr_url": "https://pubchem.ncbi.nlm.nih.gov/compound/962",
          "expiration_date": "2028-01-01",
          "copies": 1
        }
      ]
    }

HOW ERRORS WORK

If the JSON is invalid, the app lists every problem and names the field,
for example labels[1].signal. Fix the named fields and paste again.
Unknown fields are ignored with a warning and never block printing."""

# --- pure-tests:end ---

# -------------------------------------------------------------------- UI ---
import streamlit as st  # noqa: E402  (kept out of the pure section for tests)

st.set_page_config(page_title="JSON Label Printer", page_icon="🏷️")
st.title("🏷️ JSON Label Printer")
st.caption("Browser edition — prints via WebUSB to the Dymo plugged into this computer.")
st.markdown(TOP_TEXT)

json_text = st.text_area("JSON label string", value=SAMPLE_JSON, height=300)
RENDERED = []
labels, errors, warnings = parse_labels_json(json_text)
for err in errors:
    st.error(err)
for warn in warnings:
    st.warning(warn)
if not errors and labels:
    for idx, lab in enumerate(labels):
        img = build_label_image(
            lab["name"], lab["signal"], lab["h_codes"], lab["pictograms"],
            lab["qr_url"], lab["owner"], lab["tel"], lab["expiration_date"],
        )
        RENDERED.append((img, lab["copies"], lab["name"]))
        st.subheader(f"Label {idx + 1} of {len(labels)}: {lab['name']}")
        st.image(img, use_container_width=True)

__PRINT_HOOK__

with st.expander("How this app works — schema and instructions for AI agents",
                 expanded=True):
    st.markdown(SCHEMA_DOC)
