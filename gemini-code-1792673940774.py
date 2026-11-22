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
                                excel_meters.extend(extract_meters_from_excel(excel_file))
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
    m4.metric("חסרים בעגלה מהסדרה (פונקציונלי)", len(missing_from_cart_in_series))

    if missing_from_cart_in_series:
        missing_str = ", ".join(missing_from_cart_in_series)
        st.warning(
            f"⚠️ שים לב: בפונקציונלי קיימים {len(missing_from_cart_in_series)} מונים מהסדרות של העגלה שלא נסרקו בעגלה: {missing_str}"
        )

    tab1, tab2, tab3, tab4 = st.tabs([
        "❌ מונים חסרים",
        "⚙️ נבדקו פונקציונלית",
        "🔍 איתור כפילויות וסדרות נוספות",
        "📊 דוח מלא להורדה"
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
            st.error(f"בעגלה אבל **לא בפונקציונלי** ({len(missing_in_functional)}):")
            if missing_in_functional:
                st.dataframe(pd.DataFrame({"6 ספרות אחרונות": missing_in_functional}), use_container_width=True)
            else:
                st.success("כל מוני העגלה מופיעים בפונקציונלי!")

        with col_c:
            st.warning(f"בפונקציונלי (אותה סדרה) אבל **חסרים בעגלה** ({len(missing_from_cart_in_series)}):")
            if missing_from_cart_in_series:
                st.dataframe(pd.DataFrame({"6 ספרות אחרונות": missing_from_cart_in_series}), use_container_width=True)
            else:
                st.success("אין מונים חסרים מהסדרה של העגלה!")

    with tab2:
        st.subheader(f"✅ מונים בעגלה שעברו בדיקה פונקציונלית בהצלחה ({len(checked_in_functional)}):")
        if checked_in_functional:
            st.dataframe(pd.DataFrame({"6 ספרות אחרונות שנבדקו פונקציונלית": checked_in_functional}), use_container_width=True)
        else:
            st.info("אין מונים בעגלה שעברו בדיקה פונקציונלית.")

    with tab3:
        st.subheader("🔍 כפילויות בעגלה")
        if cart_duplicates:
            dup_cart_data = [{"6 ספרות אחרונות": m, "כמות הופעות בעגלה": cnt} for m, cnt in cart_duplicates.items()]
            st.warning(f"נמצאו {len(cart_duplicates)} מונים שמופיעים יותר מפעם אחת בעגלה:")
            st.dataframe(pd.DataFrame(dup_cart_data), use_container_width=True)
        else:
            st.success("אין כפילויות בעגלה! כל מונה מופיע פעם אחת בלבד.")

        st.divider()

        st.subheader("🔍 מונים שמופיעים ביותר מקובץ אקסל או XML אחד")
        if meter_to_files:
            duplicates_data = []
            for m, files in meter_to_files.items():
                if len(files) > 1 or all_extracted_meters.count(m) > 1:
                    duplicates_data.append({
                        "מספר מונה": m,
                        "כמות הופעות": all_extracted_meters.count(m),
                        "שמות הקבצים בהם מופיע": ", ".join(files)
                    })
            duplicates_data.sort(key=lambda x: x["מספר מונה"])
            if duplicates_data:
                st.warning(f"נמצאו {len(duplicates_data)} מונים המופיעים ביותר מקובץ אחד:")
                st.dataframe(pd.DataFrame(duplicates_data), use_container_width=True)
            else:
                st.success("אין כפילויות!")
        else:
            st.info("טען קבצים כדי לראות ניתוח כפילויות.")

        st.divider()

        st.subheader(f"📦 מונים נוספים בפונקציונלי מסדרות אחרות ({len(other_series_in_func)})")
        if other_series_in_func:
            st.dataframe(pd.DataFrame({"6 ספרות אחרונות (סדרות אחרות)": other_series_in_func}), use_container_width=True)
        else:
            st.info("אין מונים נוספים מסדרות אחרות.")

    with tab4:
        st.write("הפקת דוח ריכוז, חוסרים והשוואות לאקסל:")
        if set_cart or set_functional or set_accuracy:
            all_unique = sorted(list(set_cart | set_accuracy | set_functional))
            report_data = []
            for m in all_unique:
                report_data.append({
                    "6 ספרות אחרונות": m,
                    "נמצא בעגלה": "כן" if m in set_cart else "לא",
                    "עבר בדיקת דיוק": "כן" if m in set_accuracy else "לא",
                    "עבר בדיקה פונקציונלית": "כן" if m in set_functional else "לא",
                    "חסר בעגלה (מסדרת העגלה)": "כן" if m in missing_from_cart_in_series else "לא"
                })
            df_report = pd.DataFrame(report_data)
            st.dataframe(df_report, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_report.to_excel(writer, index=False, sheet_name="דוח מרוכז")

            st.download_button(
                label="📥 הורד דוח מלא לאקסל (Excel)",
                data=buffer.getvalue(),
                file_name="דוח_בדיקת_מונים_מרוכז.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("הכנס נתונים כדי להפיק דוח.")
else:
    st.info("לחץ על כפתור **'הפעל בדיקה והצלבה'** האדום למעלה כדי להציג את תוצאות ההצלבה והדוחות.")
