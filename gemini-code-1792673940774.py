import io
import re
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

st.set_page_config(
    page_title="מערכת בדיקת מונים וברקודים",
    page_icon="📊",
    layout="wide",
)

st.title("📊 מערכת ניהול ובדיקת מונים וברקודים")
st.write(
    "ניהול עגלה, בדיקת דיוק (XML, PDF, ZIP או טקסט), ובדיקה פונקציונלית"
    " (אקסל, ZIP או הדבקה לפי 6 ספרות אחרונות)."
)


def normalize_meter(val):
    """מנרמל מספר מונה ל-6 ספרות אחרונות לאחר הסרת תווים שאינם ספרות."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    cleaned = re.sub(r"\D", "", s)
    if not cleaned:
        return ""
    if len(cleaned) >= 6:
        return cleaned[-6:]
    return cleaned


def extract_meters_from_xml_content(xml_content):
    try:
        root = ET.fromstring(xml_content)
        extracted = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                val = elem.text.strip()
                cleaned_val = re.sub(r"\D", "", val)
                if "050" in cleaned_val and len(cleaned_val) >= 10:
                    match = re.search(r"(050\d{9})", cleaned_val)
                    if match:
                        extracted.append(match.group(1))
                    else:
                        extracted.append(cleaned_val.lstrip("0"))
        return list(set(extracted))
    except Exception:
        return []


def extract_meters_from_pdf(uploaded_file):
    if not PDF_SUPPORT:
        return []
    try:
        reader = pypdf.PdfReader(uploaded_file)
        extracted = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted.extend(re.findall(r"\b050\d{9}\b", page_text))
        return list(set(extracted))
    except Exception:
        return []


def extract_functional_from_excel(uploaded_file, require_checkmeter=True):
    """
    מחזיר:
    - valid_meters: מונים עם CheckMeter או Set Meter Time ו-RFlag תקין
    - all_meters: כל המונים שמופיעים בקובץ
    - open_res_only_meters: מונים שמופיעים רק תחת Open Resolution ללא CheckMeter/Set Meter Time
    """
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = "Data" if "Data" in xls.sheet_names else xls.sheet_names[0]
        df_excel = pd.read_excel(xls, sheet_name=sheet_name)

        meter_col_name = None
        for col in df_excel.columns:
            col_str = str(col).lower()
            if any(k in col_str for k in ["metternum", "meter", "kodmone", "מונה", "ברקוד"]):
                meter_col_name = col
                break

        notes_col_name = None
        for col in df_excel.columns:
            col_str = str(col).lower()
            if any(k in col_str for k in ["notes", "הערות", "סטטוס"]):
                notes_col_name = col
                break

        rflag_col_name = None
        for col in df_excel.columns:
            col_str = str(col).lower()
            if "rflag" in col_str or "flag" in col_str:
                rflag_col_name = col
                break

        if meter_col_name is None:
            df_all = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            all_set = set()
            for col_idx in range(df_all.shape[1]):
                for val in df_all.iloc[:, col_idx].dropna():
                    norm = normalize_meter(val)
                    if norm:
                        all_set.add(norm)
            return {
                "valid_meters": sorted(list(all_set)),
                "all_meters": sorted(list(all_set)),
                "open_res_only_meters": [],
            }

        all_set = set()
        valid_set = set()
        notes_by_meter = {}

        for _, row in df_excel.iterrows():
            norm = normalize_meter(row[meter_col_name])
            if not norm:
                continue
            all_set.add(norm)

            note_val = (
                str(row[notes_col_name]).strip()
                if (notes_col_name and pd.notna(row[notes_col_name]))
                else ""
            )
            rflag_val = (
                row[rflag_col_name]
                if (rflag_col_name and pd.notna(row[rflag_col_name]))
                else True
            )
            rflag_ok = str(rflag_val).strip().lower() in ["true", "1", "yes"]

            notes_by_meter.setdefault(norm, []).append((note_val, rflag_ok))

            if not require_checkmeter:
                valid_set.add(norm)
            else:
                if any(k in note_val.lower() for k in ["checkmeter", "set meter time"]) and rflag_ok:
                    valid_set.add(norm)

        open_res_only = sorted([
            m
            for m, items in notes_by_meter.items()
            if m not in valid_set and any("open resolution" in n.lower() for n, _ in items)
        ])

        return {
            "valid_meters": sorted(list(valid_set)),
            "all_meters": sorted(list(all_set)),
            "open_res_only_meters": open_res_only,
        }
    except Exception:
        return {"valid_meters": [], "all_meters": [], "open_res_only_meters": []}


col1, col2 = st.columns(2)

with col1:
    st.subheader("🛒 עגלה ובדיקת דיוק")
    cart_meters_text = st.text_area(
        "סרוק ברקודים בעגלה (אקדח ברקוד — אחד בכל שורה):",
        height=200,
        placeholder="סרוק לכאן עם אקדח הברקוד...",
    )

    uploaded_accuracy = st.file_uploader(
        "🔍 טען קבצי בדיקת דיוק (XML, PDF, ZIP או טקסט):",
        type=["xml", "pdf", "zip", "txt"],
        accept_multiple_files=True,
    )

    meter_to_files = {}
    all_extracted_meters = []

    if uploaded_accuracy:
        for uploaded_file in uploaded_accuracy:
            file_name = uploaded_file.name
            file_name_lower = file_name.lower()

            if file_name_lower.endswith(".zip"):
                try:
                    with zipfile.ZipFile(uploaded_file, "r") as z:
                        for zip_info in z.namelist():
                            zip_lower = zip_info.lower()
                            if zip_lower.endswith(".xml"):
                                with z.open(zip_info) as xml_file:
                                    meters_from_file = extract_meters_from_xml_content(xml_file.read())
                                    for m in meters_from_file:
                                        all_extracted_meters.append(m)
                                        meter_to_files.setdefault(m, [])
                                        if zip_info not in meter_to_files[m]:
                                            meter_to_files[m].append(zip_info)
                            elif zip_lower.endswith(".pdf") and PDF_SUPPORT:
                                with z.open(zip_info) as pdf_file:
                                    meters_from_file = extract_meters_from_pdf(pdf_file)
                                    for m in meters_from_file:
                                        all_extracted_meters.append(m)
                                        meter_to_files.setdefault(m, [])
                                        if zip_info not in meter_to_files[m]:
                                            meter_to_files[m].append(zip_info)
                            elif zip_lower.endswith(".txt"):
                                with z.open(zip_info) as txt_file:
                                    txt_content = txt_file.read().decode("utf-8", errors="ignore")
                                    for line in txt_content.splitlines():
                                        n = normalize_meter(line)
                                        if n:
                                            all_extracted_meters.append(n)
                                            meter_to_files.setdefault(n, [])
                                            if zip_info not in meter_to_files[n]:
                                                meter_to_files[n].append(zip_info)
                except Exception as e:
                    st.error(f"שגיאה בחילוץ קובץ ה-ZIP: {e}")

            elif file_name_lower.endswith(".xml"):
                meters_from_file = extract_meters_from_xml_content(uploaded_file.read())
                for m in meters_from_file:
                    all_extracted_meters.append(m)
                    meter_to_files.setdefault(m, [])
                    if file_name not in meter_to_files[m]:
                        meter_to_files[m].append(file_name)

            elif file_name_lower.endswith(".pdf"):
                meters_from_file = extract_meters_from_pdf(uploaded_file)
                for m in meters_from_file:
                    all_extracted_meters.append(m)
                    meter_to_files.setdefault(m, [])
                    if file_name not in meter_to_files[m]:
                        meter_to_files[m].append(file_name)

            elif file_name_lower.endswith(".txt"):
                txt_content = uploaded_file.read().decode("utf-8", errors="ignore")
                for line in txt_content.splitlines():
                    n = normalize_meter(line)
                    if n:
                        all_extracted_meters.append(n)
                        meter_to_files.setdefault(n, [])
                        if file_name not in meter_to_files[n]:
                            meter_to_files[n].append(file_name)

        if all_extracted_meters:
            st.success(f"נטענו בהצלחה {len(all_extracted_meters)} מופעים לדיוק!")

    xml_meters_unique = sorted({normalize_meter(m) for m in meter_to_files.keys() if normalize_meter(m)})
    accuracy_text_default = "\n".join(xml_meters_unique) if xml_meters_unique else ""

    accuracy_meters_text = st.text_area(
        "תוצאות בדיקת דיוק (או הדבק ידנית):",
        value=accuracy_text_default,
        height=150,
        placeholder="מונים לבדיקת דיוק...",
    )

with col2:
    st.subheader("⚙️ בדיקה פונקציונלית")
    strict_checkmeter = st.checkbox(
        "ספור כ'נבדק פונקציונלית' רק מונים עם CheckMeter / Set Meter Time תקין (ולא רק Open Resolution)",
        value=True,
    )
    uploaded_excel = st.file_uploader(
        "טען קובץ אקסל או ZIP פונקציונלי:",
        type=["xlsx", "xls", "zip", "txt"],
    )

    excel_meters = []
    open_res_only_from_file = []

    if uploaded_excel is not None:
        file_name_lower = uploaded_excel.name.lower()
        if file_name_lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(uploaded_excel, "r") as z:
                    valid_acc = set()
                    open_acc = set()
                    for zip_info in z.namelist():
                        zip_lower = zip_info.lower()
                        if zip_lower.endswith((".xlsx", ".xls")):
                            with z.open(zip_info) as excel_file:
                                res = extract_functional_from_excel(
                                    excel_file, require_checkmeter=strict_checkmeter
                                )
                                valid_acc.update(res["valid_meters"])
                                open_acc.update(res["open_res_only_meters"])
                        elif zip_lower.endswith(".txt"):
                            with z.open(zip_info) as txt_file:
                                txt_content = txt_file.read().decode("utf-8", errors="ignore")
                                for line in txt_content.splitlines():
                                    n = normalize_meter(line)
                                    if n:
                                        valid_acc.add(n)
                    excel_meters = sorted(list(valid_acc))
                    open_res_only_from_file = sorted(list(open_acc - valid_acc))
            except Exception as e:
                st.error(f"שגיאה בחילוץ קובץ ה-ZIP הפונקציונלי: {e}")
        elif file_name_lower.endswith((".xlsx", ".xls")):
            res = extract_functional_from_excel(uploaded_excel, require_checkmeter=strict_checkmeter)
            excel_meters = res["valid_meters"]
            open_res_only_from_file = res["open_res_only_meters"]
        elif file_name_lower.endswith(".txt"):
            txt_content = uploaded_excel.read().decode("utf-8", errors="ignore")
            excel_meters = sorted(
                list({normalize_meter(line) for line in txt_content.splitlines() if normalize_meter(line)})
            )

        if excel_meters:
            st.success(f"נטענו בהצלחה {len(excel_meters)} מונים פונקציונליים תקינים!")
        if open_res_only_from_file:
            open_str = ", ".join(open_res_only_from_file)
            st.info(
                f"נמצאו {len(open_res_only_from_file)} מונים שמופיעים בקובץ רק תחת Open Resolution: {open_str}"
            )

    functional_text_default = "\n".join(excel_meters) if excel_meters else ""

    functional_meters_text = st.text_area(
        "תוצאות בדיקה פונקציונלית (או הדבק ידנית):",
        value=functional_text_default,
        height=290,
        placeholder="מונים לבדיקה פונקציונלית...",
    )

st.divider()

run_check = st.button("🔍 הפעל בדיקה והצלבה", type="primary", use_container_width=True)

if run_check:
    st.session_state["checked"] = True

if st.session_state.get("checked", False):
    cart_lines = [line.strip() for line in cart_meters_text.splitlines() if line.strip()]
    cart_normalized_list = [normalize_meter(line) for line in cart_lines if normalize_meter(line)]

    set_cart = set(cart_normalized_list)
    set_accuracy = {normalize_meter(line) for line in accuracy_meters_text.splitlines() if normalize_meter(line)}
    set_functional = {normalize_meter(line) for line in functional_meters_text.splitlines() if normalize_meter(line)}

    missing_in_accuracy = sorted(list(set_cart - set_accuracy))
    missing_in_functional = sorted(list(set_cart - set_functional))
    checked_in_functional = sorted(list(set_cart & set_functional))

    cart_prefixes = {m[:2] for m in set_cart if len(m) >= 2}
    func_same_series = {m for m in set_functional if len(m) >= 2 and m[:2] in cart_prefixes}
    missing_from_cart_in_series = sorted(list(func_same_series - set_cart))
    other_series_in_func = sorted(list(set_functional - set_cart - set(missing_from_cart_in_series)))

    cart_counts = {m: cart_normalized_list.count(m) for m in set_cart}
    cart_duplicates = {m: count for m, count in cart_counts.items() if count > 1}

    st.subheader("📋 סיכום ותוצאות הצלבה")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("סה״כ בעגלה (ייחודי)", len(set_cart))
    m2.metric("נבדקו פונקציונלית", len(checked_in_functional))
    m3.metric("חסרים בדיוק", len(missing_in_accuracy))
    m4.metric("חסרים / לא עברו בפונקציונלית", len(missing_in_functional))

    tab1, tab2, tab3, tab4 = st.tabs([
        "❌ מונים חסרים",
        "⚙️ נבדקו פונקציונלית",
        "🔍 איתור כפילויות וסדרות נוספות",
        "📊 דוח מלא להורדה",
    ])

    with tab1:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.error(f"בעגלה אבל **לא בדיוק** ({len(missing_in_accuracy)}):")
            if missing_in_accuracy:
                st.dataframe(pd.DataFrame({"6 ספרות אחרונות": missing_in_accuracy}), use_container_width=True)
            else:
                st.success("הכל קיים בבדיקת הדיוק!")

        with col_b:
            st.error(f"בעגלה אבל **לא נבדקו פונקציונלית** ({len(missing_in_functional)}):")
            if missing_in_functional:
                st.dataframe(pd.DataFrame({"6 ספרות אחרונות": missing_in_functional}), use_container_width=True)
            else:
                st.success("כל מוני העגלה נבדקו פונקציונלית!")

        with col_c:
            st.warning(f"בפונקציונלי (אותה סדרה) אבל **חסרים בעגלה** ({len(missing_from_cart_in_series)}):")
            if missing_from_cart_in_series:
                st.dataframe(pd.DataFrame({"6 ספרות אחרונות": missing_from_cart_in_series}),
