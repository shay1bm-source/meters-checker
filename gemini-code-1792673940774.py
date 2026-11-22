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

st.set_page_config(page_title="מערכת בדיקת מונים וברקודים", page_icon="📊", layout="wide")

st.title("📊 מערכת ניהול ובדיקת מונים וברקודים")
st.write("ניהול עגלה, בדיקת דיוק (XML, PDF, ZIP או טקסט), ובדיקה פונקציונלית (אקסל, ZIP או הדבקה).")


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
                cleaned_val = re.sub(r"\D", "", elem.text.strip())
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
    מחזיר מילון עם:
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
                "open_res_only_meters": []
            }

        all_set = set()
        valid_set = set()
        notes_by_meter = {}

        for _, row in df_excel.iterrows():
            norm = normalize_meter(row[meter_col_name])
            if not norm:
                continue
            all_set.add(norm)

            note_val = str(row[notes_col_name]).strip() if (notes_col_name and pd.notna(row[notes_col_name])) else ""
            rflag_val = row[rflag_col_name] if (rflag_col_name and pd.notna(row[rflag_col_name])) else True
            rflag_ok = str(rflag_val).strip().lower() in ["true", "1", "yes"]

            notes_by_meter.setdefault(norm, []).append((note_val, rflag_ok))

            if not require_checkmeter:
                valid_set.add(norm)
            else:
                if any(k in note_val.lower() for k in ["checkmeter", "set meter time"]) and rflag_ok:
                    valid_set.add(norm)

        open_res_only = sorted([
            m for m, items in notes_by_meter.items()
            if m not in valid_set and any("open resolution" in n.lower() for n, _ in items)
        ])

        return {
            "valid_meters": sorted(list(valid_set)),
            "all_meters": sorted(list(all_set)),
            "open_res_only_meters": open_res_only
        }
    except Exception:
        return {"valid_meters": [], "all_meters": [], "open_res_only_meters": []}


col1, col2 = st.columns(2)

with col1:
    st.subheader("🛒 עגלה ובדיקת דיוק")
    cart_meters_text = st.text_area(
        "סרוק ברקודים בעגלה (אקדח ברקוד — אחד בכל שורה):",
        height=200,
        placeholder="סרוק לכאן עם אקדח הברקוד..."
    )

    uploaded_accuracy = st.file_uploader(
        "🔍 טען קבצי בדיקת דיוק (XML, PDF, ZIP או טקסט):",
        type=["xml", "pdf", "zip", "txt"],
        accept_multiple_files=True
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
