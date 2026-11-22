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
                val = elem.text.strip()
                cleaned_val = re.sub(r"\D", "", val)
                if "050" in cleaned_val and len(cleaned_val) >= 10:
                    match = re.search(r"(050\d{9})", cleaned_val)
                    if match:
                        extracted.append(match.group(1))
                    else:
                        stripped_val = cleaned_val.lstrip("0")
                        extracted.append(stripped_val)
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
                found = re.findall(r"\b050\d{9}\b", page_text)
                extracted.extend(found)
        return list(set(extracted))
    except Exception:
        return []


def extract_meters_from_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df_excel = pd.read_excel(xls, sheet_name=sheet_name)

        extracted = []
        meter_col_name = None
        for col in df_excel.columns:
            col_str = str(col).lower()
            if any(k in col_str for k in ["metternum", "meter", "kodmone", "מונה", "ברקוד"]):
                meter_col_name = col
                break

        if meter_col_name is not None:
            for val in df_excel[meter_col_name].dropna():
                norm = normalize_meter(val)
                if norm:
                    extracted.append(norm)
        else:
            df_all = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            for col_idx in range(df_all.shape[1]):
                for val in df_all.iloc[:, col_idx].dropna():
                    norm = normalize_meter(val)
                    if norm:
                        extracted.append(norm)

        return list(set(extracted))
    except Exception:
        return []


# חלוקה ל-2 עמודות
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
        placeholder="מונים לבדיקת דיוק..."
    )

with col2:
    st.subheader("⚙️ בדיקה פונקציונלית")
    uploaded_excel = st.file_uploader("טען קובץ אקסל או ZIP פונקציונלי:", type=["xlsx", "xls", "zip", "txt"])

    excel_meters = []
    if uploaded_excel is not None:
        file_name_lower = uploaded_excel.name.lower()
        if file_name_lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(uploaded_excel, "r") as z:
                    for zip_info in z.namelist():
                        zip_lower = zip_info.lower()
                        if zip_lower.endswith((".xlsx", ".xls")):
                            with z.open(zip_info) as excel_file:
                                meters_from_file = extract_meters_from_excel(excel_file)
                                excel_meters.extend(meters_from_file)
                        elif zip_lower.endswith(".txt"):
                            with z.open(zip_info) as txt_file:
                                txt_content = txt_file.read().decode("utf-8", errors="ignore")
                                for line in txt_content.splitlines():
                                    n = normalize_meter(line)
                                    if n:
                                        excel_meters.append(n)
                excel_meters = sorted(list(set(excel_meters)))
            except Exception as e:
                st.error(f"שגיאה בחילוץ קובץ ה-ZIP הפונקציונלי: {e}")
        elif file_name_lower.endswith((".xlsx", ".xls")):
            excel_meters = sorted(list(set(extract_meters_from_excel(uploaded_excel))))
        elif file_name_lower.endswith(".txt"):
            txt_content = uploaded_excel.read().decode("utf-8", errors="ignore")
            excel_meters = sorted(list({normalize_meter(line) for line in txt_content.splitlines() if normalize_meter(line)}))

        if excel_meters:
            st.success(f"נטענו בהצלחה {len(excel_meters)} מונים פונקציונליים ייחודיים!")

    functional_text_default = "\n".join(excel_meters) if excel_meters else ""

    functional_meters_text = st.text_area(
        "תוצאות בדיקה פונקציונלית (או הדבק ידנית):",
        value=functional_text_default,
        height=325,
        placeholder="מונים לבדיקה פונקציונלית..."
    )

st.divider()

run_check = st.button("🔍 הפעל בדיקה והצלבה", type="primary", use_container_width=True
