"""Build the stlite single-file JSON label app.

Mirrors build_text.py (the text label app build) exactly:
1. Fills json_label_app_template.py with the embedded fonts and GHS symbols.
2. Inlines the same WebUSB driver into the same print-box HTML; the box's
   closing script tag travels as the inert token __PRINT_BOX_CLOSE__ and
   is restored at runtime (never a raw closer in the page source).
3. Runs Marco's streamlit2stlite converter -> json_label_app.html.

The print hook differs from the text app: it loops over RENDERED, the
list of (image, copies, name) built by the UI section, and emits one
print box per label.

Usage: python3 build_json.py
"""
import re
import sys

sys.path.insert(0, "/home/hatch/workspace/streamlit2stlite")
from streamlit2stlite.core import convert_streamlit_to_stlite

HERE = "/home/hatch/workspace/chem-server/stl-app"

PRINT_HOOK_TPL = '''
import streamlit.components.v1 as components

_PRINT_BOX = __PRINT_BOX_REPR__

if RENDERED:
    st.subheader("Print")
    for _idx, (_img, _copies, _name) in enumerate(RENDERED):
        _b64 = printer_matrix_b64(_img)
        _box = _PRINT_BOX.replace("__MATRIX_B64__", _b64)
        _box = _box.replace("__COPIES__", str(int(_copies)))
        _box = _box.replace("__COPIES_LABEL__",
                            f"{int(_copies)} label" + ("" if int(_copies) == 1 else "s"))
        # Restore the print box's real closing script tag. It travels through
        # the page as the inert token __PRINT_BOX_CLOSE__ (never a raw closer,
        # so the outer module script in json_label_app.html is never
        # terminated early) and is swapped for the real tag here at runtime,
        # built without a literal closer in the Python source for the same
        # reason.
        _box = _box.replace("__PRINT_BOX_CLOSE__", "</scr" + "ipt>")
        st.caption(f"Label {_idx + 1}: {_name} — {int(_copies)} "
                   + ("copy" if int(_copies) == 1 else "copies"))
        components.html(_box, height=132)
'''


def main():
    tpl = open(f"{HERE}/json_label_app_template.py").read()

    tpl = tpl.replace("__FONT_BOLD_B64__", open(f"{HERE}/font_bold.b64").read().strip())
    tpl = tpl.replace("__FONT_REG_B64__", open(f"{HERE}/font_regular.b64").read().strip())
    tpl = tpl.replace("__SYMBOLS_JSON__", open(f"{HERE}/symbols85.json").read().strip())
    assert "__FONT_BOLD_B64__" not in tpl
    assert "__FONT_REG_B64__" not in tpl
    assert "__SYMBOLS_JSON__" not in tpl

    # Print box: same box and same driver as the chemical/text apps. Inline
    # the driver JS, then swap its </script> closer for the inert token so
    # the outer module script in json_label_app.html is never terminated
    # early.
    box = open(f"{HERE}/print_box.html").read()
    box = box.replace("__DYMO_JS__", open(f"{HERE}/dymo_webusb.js").read())
    box = box.replace("</script>", "__PRINT_BOX_CLOSE__")
    assert "__DYMO_JS__" not in box
    assert "</script>" not in box
    hook = PRINT_HOOK_TPL.replace("__PRINT_BOX_REPR__", repr(box))
    tpl = tpl.replace("__PRINT_HOOK__", hook)

    open(f"{HERE}/json_label_app.py", "w").write(tpl)

    # Pure (streamlit-free) section for local tests.
    m = re.search(r"# --- pure-tests:begin ---\n(.*)\n# --- pure-tests:end ---",
                  tpl, re.S)
    pure = ("import base64\nimport io\nimport json\nimport math\nimport re\n"
            "from datetime import date\n"
            "from PIL import Image, ImageDraw, ImageFont\nimport qrcode\n" + m.group(1))
    open(f"{HERE}/json_label_pure.py", "w").write(pure)

    html = convert_streamlit_to_stlite(
        tpl, title="JSON Label Printer", requirements=["qrcode"])
    open(f"{HERE}/json_label_app.html", "w").write(html)
    print(f"json_label_app.html written ({len(html)} bytes)")
    # sanity: no raw </script> inside the embedded python other than the real closers
    n_close = html.count("</script>")
    print("literal </script> closers in final HTML:", n_close, "(expect 2: driver + module)")


if __name__ == "__main__":
    main()
