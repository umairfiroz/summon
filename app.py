"""Split & Spell - receipt scanning fused with a shared bill-splitting calculator.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from split_and_spell import gemma, sample, split, theme, ui

APP_DIR = Path(__file__).parent
SAMPLE_IMAGE = APP_DIR / "assets" / "sample_receipt.png"
METHODS = ["Equal split", "Custom amounts", "By item"]
STEP_INDEX = {"upload": 0, "review": 1, "split": 2, "result": 3}
FAIL_TEXT = "We couldn't read this receipt. Try a clearer image or enter the items manually."

st.set_page_config(page_title="Split & Spell", page_icon=":material/receipt_long:", layout="wide")
ss = st.session_state


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #

def init_state() -> None:
    defaults = {
        "step": "upload",
        "source": None,            # "sample" | "gemma" | "manual"
        "merchant": None,
        "symbol": "£",
        "detected_total": None,    # pence, from the receipt
        "image": None,             # bytes of the receipt image, shown unmodified
        "raw": None,               # Gemma's raw JSON
        "receipt_notes": [],
        "lines": [],               # {"id", "name", "price"} price in pence or None
        "charges": {"service": 0, "tip": 0, "tax": 0, "discount": 0},
        "people": [],              # {"id", "name"}
        "method": "Equal split",
        "assign": {},              # item id -> [person ids]
        "custom": {},              # person id -> pence or None
        "mismatch_ok": False,
        "next_id": 1,
        "upload_error": None,
        "person_error": None,
        "flash": None,
        "result": None,
    }
    for key, value in defaults.items():
        if key not in ss:
            ss[key] = value


def new_id() -> int:
    ss.next_id += 1
    return ss.next_id


def reset_bill(keep_people: bool = True) -> None:
    for key in ("source", "merchant", "detected_total", "image", "raw", "upload_error", "flash", "result"):
        ss[key] = None
    ss.symbol = "£"
    ss.receipt_notes = []
    ss.lines = []
    ss.charges = {"service": 0, "tip": 0, "tax": 0, "discount": 0}
    ss.assign = {}
    ss.mismatch_ok = False
    if not keep_people:
        ss.people = []
        ss.custom = {}
        ss.method = "Equal split"


def pence_to_float(value: int | None) -> float | None:
    return None if value is None else value / 100


def money(pence: int) -> str:
    return split.format_money(pence, ss.symbol)


def item_by_id(iid: int) -> dict:
    return next(i for i in ss.lines if i["id"] == iid)


def person_name(pid: int) -> str:
    return next((p["name"] for p in ss.people if p["id"] == pid), "Removed person")


def api_key() -> str | None:
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # no secrets file locally
        key = None
    return key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ss.get("user_api_key") or None


# --------------------------------------------------------------------------- #
# Loading a receipt
# --------------------------------------------------------------------------- #

def load_receipt(receipt: gemma.Receipt, source: str, image: bytes | None) -> None:
    reset_bill(keep_people=True)
    ss.source = source
    ss.merchant = receipt.merchant
    ss.symbol = receipt.symbol
    ss.image = image
    ss.raw = receipt.raw
    ss.detected_total = split.to_pence(receipt.total) if receipt.total is not None else None
    discount = split.to_pence(receipt.discount) if receipt.discount else 0
    for item in receipt.items:
        price = split.to_pence(item.line_total)
        if price < 0:
            # Negative lines are discounts: show them explicitly as a discount.
            discount += -price
            ss.receipt_notes.append(f"“{item.name}” ({money(price)}) was added to Discounts.")
            continue
        iid = new_id()
        ss.lines.append({"id": iid, "name": item.name, "price": price})
        ss.assign[iid] = []
    ss.charges = {
        "service": split.to_pence(receipt.service_charge) if receipt.service_charge else 0,
        "tip": split.to_pence(receipt.tip) if receipt.tip else 0,
        "tax": split.to_pence(receipt.tax_added) if receipt.tax_added else 0,
        "discount": discount,
    }
    ss.step = "review"


def load_sample() -> None:
    reset_bill(keep_people=False)
    ss.source = "sample"
    ss.merchant = sample.MERCHANT
    ss.image = SAMPLE_IMAGE.read_bytes() if SAMPLE_IMAGE.exists() else None
    ss.detected_total = split.to_pence(sample.TOTAL)
    ids_by_name = {}
    for name, price in sample.ITEMS:
        iid = new_id()
        ids_by_name[name] = iid
        ss.lines.append({"id": iid, "name": name, "price": split.to_pence(price)})
    ss.people = []
    pid_by_name = {}
    for name in sample.PEOPLE:
        pid = new_id()
        pid_by_name[name] = pid
        ss.people.append({"id": pid, "name": name})
    ss.assign = {ids_by_name[item]: [pid_by_name[n] for n in names] for item, names in sample.BY_ITEM.items()}
    ss.custom = {pid_by_name[n]: split.to_pence(v) for n, v in sample.CUSTOM.items()}
    ss.method = "Equal split"
    ss.step = "review"


def start_manual() -> None:
    reset_bill(keep_people=True)
    ss.source = "manual"
    iid = new_id()
    ss.lines = [{"id": iid, "name": "", "price": None}]
    ss.assign = {iid: []}
    ss.step = "review"


def read_with_gemma(image: bytes) -> None:
    ss.upload_error = None
    try:
        with st.spinner("Reading your receipt…"):
            receipt = gemma.read_receipt(gemma.make_client(api_key()), image)
    except gemma.GemmaError as exc:
        ss.upload_error = str(exc)
        return
    load_receipt(receipt, "gemma", image)
    st.rerun()


# --------------------------------------------------------------------------- #
# Widget callbacks (keep the canonical state in sync with the widgets)
# --------------------------------------------------------------------------- #

def cb_item_name(iid: int) -> None:
    item_by_id(iid)["name"] = ss[f"item_name_{iid}"]


def cb_item_price(iid: int) -> None:
    value = ss[f"item_price_{iid}"]
    item_by_id(iid)["price"] = None if value is None else split.to_pence(round(value, 2))
    ss.mismatch_ok = False


def cb_remove_item(iid: int) -> None:
    ss.lines = [i for i in ss.lines if i["id"] != iid]
    ss.assign.pop(iid, None)
    ss.mismatch_ok = False


def cb_add_item() -> None:
    iid = new_id()
    ss.lines.append({"id": iid, "name": "", "price": None})
    ss.assign[iid] = []


def cb_charge(name: str) -> None:
    value = ss[f"charge_{name}"]
    ss.charges[name] = split.to_pence(round(value or 0, 2))
    ss.mismatch_ok = False


def validate_name(name: str, exclude_pid: int | None = None) -> str | None:
    clean = name.strip()
    if not clean:
        return "Enter a name."
    if any(p["name"].lower() == clean.lower() and p["id"] != exclude_pid for p in ss.people):
        return f"{clean} is already in the list. Use a different name, such as {clean} B."
    return None


def cb_add_person() -> None:
    name = ss.get("new_person", "")
    error = validate_name(name)
    if error:
        ss.person_error = error
        return
    ss.person_error = None
    ss.people.append({"id": new_id(), "name": name.strip()})
    ss.new_person = ""


def cb_rename(pid: int) -> None:
    value = ss[f"person_name_{pid}"]
    error = validate_name(value, exclude_pid=pid)
    if error:
        ss.person_error = error
        return  # keep the old name; the field is reset from state on the next run
    ss.person_error = None
    next(p for p in ss.people if p["id"] == pid)["name"] = value.strip()


def cb_remove_person(pid: int) -> None:
    name = person_name(pid)
    ss.people = [p for p in ss.people if p["id"] != pid]
    ss.custom.pop(pid, None)
    orphaned = []
    for iid, pids in ss.assign.items():
        if pid in pids:
            pids.remove(pid)
            if not pids:
                orphaned.append(item_by_id(iid)["name"] or "an unnamed item")
    if orphaned:
        ss.flash = ("warning", f"{name} was removed. Reassign {', '.join(orphaned)} before confirming.")
    else:
        ss.flash = ("info", f"{name} was removed.")


def cb_assign(iid: int) -> None:
    ss.assign[iid] = list(ss[f"assign_{iid}"] or [])


def cb_custom(pid: int) -> None:
    value = ss[f"custom_{pid}"]
    ss.custom[pid] = None if value is None else split.to_pence(round(value, 2))


def cb_method() -> None:
    ss.method = ss.method_widget or ss.method


def go(step: str) -> None:
    ss.step = step


# --------------------------------------------------------------------------- #
# Calculations (pure functions in split.py do the money maths)
# --------------------------------------------------------------------------- #

def items_total() -> int:
    return sum(i["price"] or 0 for i in ss.lines)


def charges_net() -> int:
    c = ss.charges
    return c["service"] + c["tip"] + c["tax"] - c["discount"]


def bill_total() -> int:
    return items_total() + charges_net()


def review_problems() -> list[str]:
    problems = []
    if not ss.lines:
        problems.append("Add at least one item.")
    if any(not i["name"].strip() for i in ss.lines):
        problems.append("Give every item a name.")
    if any(i["price"] is None for i in ss.lines):
        problems.append("Enter a line total for every item.")
    if bill_total() < 0:
        problems.append("The discount is larger than the bill.")
    mismatch = ss.detected_total is not None and bill_total() != ss.detected_total
    if mismatch and not ss.mismatch_ok:
        problems.append("Confirm the bill total below, or correct the items.")
    return problems


def compute_split() -> tuple[dict[int, int] | None, list[str], dict[int, str]]:
    """Return (amount per person id or None if blocked, blocking messages, detail per person id)."""
    names = {p["id"]: p["name"] for p in ss.people}
    total = bill_total()
    if not ss.people:
        return None, ["Add at least one person."], {}

    if ss.method == "Equal split":
        by_name = split.equal_split(total, list(names.values()))
        return {pid: by_name[n] for pid, n in names.items()}, [], {}

    if ss.method == "Custom amounts":
        amounts = {pid: ss.custom.get(pid) for pid in names}
        missing = [names[pid] for pid, v in amounts.items() if v is None]
        check = split.check_custom(total, {pid: v or 0 for pid, v in amounts.items()})
        blockers = []
        if missing:
            blockers.append(f"Enter an amount for {', '.join(missing)}.")
        if check.remaining > 0:
            blockers.append(f"Assign the remaining {money(check.remaining)} to continue.")
        elif check.remaining < 0:
            blockers.append(f"Reduce the amounts by {money(-check.remaining)} to continue.")
        return ({pid: v or 0 for pid, v in amounts.items()} if not blockers else None), blockers, {}

    # By item
    unassigned = [i["name"] or "Unnamed item" for i in ss.lines if not ss.assign.get(i["id"])]
    items = [
        split.Item(name=i["name"], price=i["price"] or 0, shared_by=[names[p] for p in ss.assign.get(i["id"], []) if p in names])
        for i in ss.lines
    ]
    result = split.split_bill(items, list(names.values()), list(names.values())[0], extras=charges_net())
    details = {}
    for pid in names:
        parts = []
        for i in ss.lines:
            sharers = [p for p in ss.assign.get(i["id"], []) if p in names]
            if pid in sharers:
                k = len(sharers)
                prefix = "" if k == 1 else ("½ " if k == 2 else f"1/{k} ")
                parts.append(prefix + (i["name"] or "Unnamed item"))
        details[pid] = ", ".join(parts) if parts else "No items"
    if unassigned:
        return None, [f"Assign {', '.join(unassigned)} to at least one person."], details
    return {pid: result.people[n].total for pid, n in names.items()}, [], details


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

init_state()

# Header: brand on the left, theme control on the right.
with st.container(key="header"):
    left, right = st.columns([3, 1], vertical_alignment="center")
    left.html(ui.brand())
    with right:
        mode = st.segmented_control(
            "Theme",
            theme.MODES,
            format_func=lambda m: theme.MODE_LABELS[m],
            default="system",
            required=True,
            key="theme",
            bind="query-params",
            help="System follows your device setting.",
        ) or "system"

st.html(theme.css(mode))
st.html(theme.persistence_script(mode), unsafe_allow_javascript=True)

st.html(ui.page_title())
st.html(ui.steps(STEP_INDEX[ss.step]))

if ss.flash:
    kind, text = ss.flash
    st.html(ui.notice(text, kind))
    ss.flash = None


def receipt_panel() -> None:
    """Left column: the original receipt, unmodified."""
    with st.container(key="panel_receipt"):
        source_label = {"sample": "Sample receipt", "gemma": "Read by Gemma 4", "manual": "Entered manually"}[ss.source]
        st.html(ui.badge(source_label, neutral=ss.source != "gemma") + ui.merchant(ss.merchant if ss.source != "manual" else "Manual entry"))
        if ss.image:
            with st.expander("Receipt preview", expanded=True):
                with st.container(key="preview_area"):
                    st.image(ss.image, width="stretch")
        else:
            st.caption("No receipt image. Items were entered by hand.")
        if ss.source == "sample":
            st.caption("Sample data for the demo. These items were preloaded, not read by AI.")
            if api_key() and ss.image:
                if st.button("Read this sample with Gemma 4", key="read_sample_live", width="stretch"):
                    read_with_gemma(ss.image)
                if ss.upload_error:
                    st.html(ui.notice(f"{FAIL_TEXT} ({ss.upload_error})", "error"))
        if ss.source == "gemma" and ss.raw is not None:
            with st.expander("What Gemma 4 extracted"):
                st.code(json.dumps(ss.raw, indent=2, ensure_ascii=False), language="json")
        st.button("Replace receipt", key="replace", width="stretch", on_click=go, args=("upload",))


# ---------- Upload ---------------------------------------------------------- #
if ss.step == "upload":
    with st.container(key="panel_upload"):
        st.html(ui.heading("Start with your receipt", "Upload a clear photo or scanned receipt."))
        uploaded = st.file_uploader("Choose receipt", type=["jpg", "jpeg", "png", "webp"], key="uploader")
        st.caption(
            "Your image is sent to Google's Gemini API, where the open-weight Gemma 4 model reads the items. "
            "Split & Spell doesn't save receipts; they're cleared when you close the page."
        )
        key_missing = not api_key()
        if key_missing:
            st.html(ui.notice("Add a Gemini API key to read receipts. The sample receipt and manual entry work without one.", "info"))
            st.text_input("Gemini API key", type="password", key="user_api_key",
                          help="Free from aistudio.google.com. Kept only for this browser session.")
        if st.button("Read receipt", type="primary", disabled=uploaded is None or not api_key(), width="stretch"):
            read_with_gemma(uploaded.getvalue())
        if ss.upload_error:
            st.html(ui.notice(f"{FAIL_TEXT} Details: {ss.upload_error}", "error"))
        if uploaded is None:
            st.caption("Choose a receipt to continue.")

        st.html(ui.subheading("Other ways to start"))
        c1, c2 = st.columns(2)
        c1.button("Use sample receipt", on_click=load_sample, width="stretch", help="The Lantern Kitchen, £56.00, with four people.")
        c2.button("Enter items manually", on_click=start_manual, width="stretch")

# ---------- Review ---------------------------------------------------------- #
elif ss.step == "review":
    col_left, col_right = st.columns([38, 62], gap="medium")
    with col_left:
        receipt_panel()
    with col_right:
        with st.container(key="panel_review"):
            st.html(ui.heading("Review receipt", "Check the items and prices before splitting."))
            st.html(ui.notice("Check the total before continuing.", "info"))
            for note in ss.receipt_notes:
                st.html(ui.notice(note, "info"))

            for index, item in enumerate(ss.lines):
                iid = item["id"]
                ss[f"item_name_{iid}"] = item["name"]
                ss[f"item_price_{iid}"] = pence_to_float(item["price"])
                c_name, c_price, c_remove = st.columns([6, 3, 2], vertical_alignment="bottom")
                vis = "visible" if index == 0 else "collapsed"
                c_name.text_input("Item", key=f"item_name_{iid}", on_change=cb_item_name, args=(iid,),
                                  label_visibility=vis, placeholder="Item name", max_chars=80)
                c_price.number_input(f"Line total ({ss.symbol.strip()})", key=f"item_price_{iid}", on_change=cb_item_price,
                                     args=(iid,), min_value=0.0, step=0.01, format="%.2f", label_visibility=vis,
                                     placeholder="0.00", help="The price printed for the whole line, after quantity." if index == 0 else None)
                c_remove.button("Remove", key=f"remove_item_{iid}", on_click=cb_remove_item, args=(iid,),
                                width="stretch", help=f"Remove {item['name'] or 'this item'}")
            st.button("Add item", icon=":material/add:", type="tertiary", on_click=cb_add_item)

            has_charges = any(ss.charges.values())
            with st.expander("Charges and discounts", expanded=has_charges):
                st.caption("Only add charges printed on the receipt. UK VAT is usually already included in prices.")
                cc = st.columns(4)
                for col, (name, label) in zip(cc, [("service", "Service charge"), ("tip", "Tip"), ("tax", "Tax added"), ("discount", "Discount")]):
                    ss[f"charge_{name}"] = pence_to_float(ss.charges[name])
                    col.number_input(f"{label} ({ss.symbol.strip()})", key=f"charge_{name}", on_change=cb_charge, args=(name,),
                                     min_value=0.0, step=0.01, format="%.2f")

            rows = [("Items total", money(items_total()))]
            for name, label in [("service", "Service charge"), ("tip", "Tip"), ("tax", "Tax added")]:
                if ss.charges[name]:
                    rows.append((label, money(ss.charges[name])))
            if ss.charges["discount"]:
                rows.append(("Discount", money(-ss.charges["discount"])))
            detected = [("Receipt total (detected)", money(ss.detected_total) if ss.detected_total is not None else "Not detected")]
            st.html(ui.reconciliation(rows, "Bill total", money(bill_total()), after=detected))

            if ss.detected_total is not None:
                if bill_total() == ss.detected_total:
                    st.html(ui.notice(f"The items add up to the receipt total of {money(ss.detected_total)}.", "success", "Matches"))
                else:
                    st.html(ui.notice(
                        f"The items add up to {money(bill_total())}, but the receipt total is {money(ss.detected_total)}. "
                        "Correct a missing item, charge or discount, or confirm the bill total.", "warning"))
                    ss.mismatch_ok = st.checkbox(f"Use {money(bill_total())} as the bill total", value=ss.mismatch_ok, key=f"mismatch_{bill_total()}")
            else:
                st.caption("No total was detected on the receipt, so check the bill total against the paper copy.")

            problems = review_problems()
            if problems:
                st.html(ui.notice(" ".join(problems), "warning", "Before you continue"))
            st.button("Continue to split", type="primary", disabled=bool(problems), on_click=go, args=("split",), width="stretch")

# ---------- Split ----------------------------------------------------------- #
elif ss.step == "split":
    col_left, col_right = st.columns([38, 62], gap="medium")
    with col_left:
        receipt_panel()
    with col_right:
        with st.container(key="panel_people"):
            st.html(ui.heading("Participants", "Add everyone sharing the bill."))
            if not ss.people:
                st.html(ui.empty_people())
            for person in ss.people:
                pid = person["id"]
                ss[f"person_name_{pid}"] = person["name"]
                c_name, c_remove = st.columns([8, 2], vertical_alignment="bottom")
                c_name.text_input("Name", key=f"person_name_{pid}", on_change=cb_rename, args=(pid,),
                                  label_visibility="collapsed", max_chars=40)
                c_remove.button("Remove", key=f"remove_person_{pid}", on_click=cb_remove_person, args=(pid,),
                                width="stretch", help=f"Remove {person['name']}")
            with st.form("add_person", clear_on_submit=False, border=False):
                c_new, c_add = st.columns([8, 2], vertical_alignment="bottom")
                c_new.text_input("Add a person", key="new_person", placeholder="Name", max_chars=40)
                c_add.form_submit_button("Add", on_click=cb_add_person, width="stretch")
            if ss.person_error:
                st.html(ui.notice(ss.person_error, "error"))
                ss.person_error = None

        with st.container(key="panel_split"):
            st.html(ui.heading("Choose a split", f"Bill total {money(bill_total())}."))
            ss.method_widget = ss.method
            st.segmented_control("Split method", METHODS, key="method_widget", on_change=cb_method, required=True)

            amounts, blockers, details = compute_split()
            names = {p["id"]: p["name"] for p in ss.people}

            if ss.method == "Equal split" and ss.people:
                values = set(amounts.values())
                headline = f"{money(next(iter(values)))} each" if len(values) == 1 else "Equal shares, to the penny"
                st.html(ui.main_amount(f"{money(bill_total())} split between {len(ss.people)} "
                                       f"{'person' if len(ss.people) == 1 else 'people'}", headline))
                if len(values) > 1:
                    st.caption("The total doesn't divide exactly, so the first people listed pay 1p more. Everyone's amount is shown below.")

            elif ss.method == "Custom amounts" and ss.people:
                st.caption("Enter what each person owes.")
                for person in ss.people:
                    pid = person["id"]
                    ss[f"custom_{pid}"] = pence_to_float(ss.custom.get(pid))
                    st.number_input(f"{person['name']} ({ss.symbol.strip()})", key=f"custom_{pid}", on_change=cb_custom,
                                    args=(pid,), min_value=0.0, step=0.01, format="%.2f", placeholder="0.00")
                assigned = sum(v or 0 for pid, v in ss.custom.items() if pid in names)
                remaining = bill_total() - assigned
                if remaining > 0:
                    st.html(ui.notice(f"{money(remaining)} left to assign.", "warning", "Remaining"))
                elif remaining < 0:
                    st.html(ui.notice(f"{money(-remaining)} over the bill total.", "error", "Over"))
                else:
                    st.html(ui.notice(f"All {money(bill_total())} assigned.", "success", "Balanced"))

            elif ss.method == "By item" and ss.people:
                st.caption("Choose who had each item. Shared items are divided equally between the people selected."
                           + (" Charges and discounts are shared in proportion to each person's items." if charges_net() else ""))
                for item in ss.lines:
                    iid = item["id"]
                    ss[f"assign_{iid}"] = [p for p in ss.assign.get(iid, []) if p in names]
                    label = f"{item['name']} · {money(item['price'] or 0)}"
                    if not ss.assign.get(iid):
                        label += " · not assigned"
                    st.pills(label, list(names), selection_mode="multi", format_func=lambda p: names[p],
                             key=f"assign_{iid}", on_change=cb_assign, args=(iid,))

            if amounts is not None:
                rows = [(names[pid], money(a), details.get(pid)) for pid, a in amounts.items()]
                st.html(ui.subheading("Summary"))
                st.html(ui.people_table(rows, "Amount owed by each person"))
                st.html(ui.reconciliation([], "Total assigned", money(sum(amounts.values()))))
            if blockers:
                st.html(ui.notice(" ".join(blockers), "warning", "To confirm"))

            c_back, c_confirm = st.columns([1, 2])
            c_back.button("Back to review", on_click=go, args=("review",), width="stretch")
            if c_confirm.button("Confirm split", type="primary", disabled=amounts is None, width="stretch"):
                ss.result = {"amounts": {names[pid]: a for pid, a in amounts.items()}, "details": {names[pid]: details.get(pid) for pid in amounts},
                             "method": ss.method, "total": bill_total()}
                go("result")
                st.rerun()

# ---------- Result ---------------------------------------------------------- #
elif ss.step == "result":
    res = ss.result
    col_left, col_right = st.columns([38, 62], gap="medium")
    with col_left:
        receipt_panel()
    with col_right:
        with st.container(key="panel_result"):
            st.html(ui.heading("Your split is ready", f"{ss.merchant or 'Manual entry'} · {res['method']} · "
                                                      f"{len(res['amounts'])} {'person' if len(res['amounts']) == 1 else 'people'}"))
            st.html(ui.main_amount("Total", money(res["total"])))
            rows = [(n, money(a), res["details"].get(n)) for n, a in res["amounts"].items()]
            st.html(ui.people_table(rows, "Amount owed by each person"))
            st.html(ui.reconciliation([], "Total assigned", money(sum(res["amounts"].values()))))

            lines = [f"{ss.merchant or 'Bill'}: {money(res['total'])} ({res['method'].lower()})"]
            lines += [f"{n}: {money(a)}" for n, a in res["amounts"].items()]
            lines.append(f"Total assigned: {money(sum(res['amounts'].values()))}")
            summary = "\n".join(lines)
            st.html(ui.copy_button(summary), unsafe_allow_javascript=True)
            with st.expander("Summary text"):
                st.code(summary, language=None, wrap_lines=True)

            c1, c2 = st.columns(2)
            c1.button("Edit split", on_click=go, args=("split",), width="stretch")
            if c2.button("Start a new receipt", width="stretch"):
                reset_bill(keep_people=False)
                ss.step = "upload"
                st.rerun()
