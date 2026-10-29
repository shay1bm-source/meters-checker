import io
import re
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

# ניסיון ייבוא ספריית קריאת PDF אם קיימת בסביבה
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

st.set_page_config(page_title="מערכת בדיקת מונים וברקודים", page_icon="📊", layout="wide")

st.title("📊 מערכת ניהול ובדיקת מונים וברקודים")
st.write("ניהול עגלה, בדיקת דיוק (XML, PDF, ZIP או הדבקה), ובדיקה פונקציונלית (אקסל, ZIP או הדבקה לפי 6 ספרות אחרונות).")

# פונקציה לחילוץ מונים מקובץ XML
def extract_meters_from_xml_content(xml_content):
    try:
        root = ET.fromstring(xml_content)
        extracted = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                val = elem.text.strip()
                cleaned_val = re.sub(r'\D', '', val)
                if len(cleaned_val) == 12 and cleaned_val.startswith('050'):
                    extracted.append(cleaned_val)
        return extracted
    except Exception as e:
        return []

# פונקציה לחילוץ מונים מקובץ PDF (דוח בדיקה)
def extract_meters_from_pdf(uploaded_file):
    if not PDF_SUPPORT:
        return []
    try:
        reader = pypdf.PdfReader(uploaded_file)
        extracted = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                found = re.findall(r'\b050\d{9}\b', page_text)
                extracted.extend(found)
        return list(set(extracted))
    except Exception as e:
        return []

# פונקציה לחילוץ מונים מקובץ אקסל לבדיקה פונקציונלית (עמודה B)
def extract_meters_from_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df_excel = pd.read_excel(xls, sheet_name=sheet_name)
        
        if df_excel.shape[1] > 1:
            col_b = df_excel.iloc[:, 1].astype(str).str.strip()
            extracted = []
            for val in col_b:
                cleaned_val = re.sub(r'\D', '', val)
                if len(cleaned_val) >= 6:
                    extracted.append(cleaned_val[-6:])
            return list(set(extracted))
        else:
            return []
    except Exception as e:
        return []

# חלוקה ל-3 עמודות
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🛒 עגלה")
    cart_meters_text = st.text_area(
        "סרוק ברקודים בעגלה (אקדח ברקוד — אחד בכל שורה):", 
        height=380, 
        placeholder="סרוק לכאן עם אקדח הברקוד..."
    )

with col2:
    st.subheader("🔍 בדיקת דיוק")
    uploaded_accuracy = st.file_uploader(
        "טען קבצי XML, PDF, ZIP או טקסט:", 
        type=["xml", "pdf", "zip", "txt"], 
        accept_multiple_files=True
    )
    
    meter_to_files = {}
    all_extracted_meters = []

    if uploaded_accuracy:
        for uploaded_file in uploaded_accuracy:
            file_name = uploaded_file.name
            
            if file_name.endswith('.zip'):
                try:
                    with zipfile.ZipFile(uploaded_file, 'r') as z:
                        for zip_info in z.namelist():
                            if zip_info.endswith('.xml'):
                                with z.open(zip_info) as xml_file:
                                    meters_from_file = extract_meters_from_xml_content(xml_file.read())
                                    for m in meters_from_file:
                                        all_extracted_meters.append(m)
                                        if m not in meter_to_files:
                                            meter_to_files[m] = []
                                        if zip_info not in meter_to_files[m]:
                                            meter_to_files[m].append(zip_info)
                            elif zip_info.endswith('.pdf') and PDF_SUPPORT:
                                with z.open(zip_info) as pdf_file:
                                    meters_from_file = extract_meters_from_pdf(pdf_file)
                                    for m in meters_from_file:
                                        all_extracted_meters.append(m)
                                        if m not in meter_to_files:
                                            meter_to_files[m] = []
                                        if zip_info not in meter_to_files[m]:
                                            meter_to_files[m].append(zip_info)
                except Exception as e:
                    st.error(f"שגיאה בחילוץ קובץ ה-ZIP: {e}")
            
            elif file_name.endswith('.xml'):
                meters_from_file = extract_meters_from_xml_content(uploaded_file.read())
                for m in meters_from_file:
                    all_extracted_meters.append(m)
                    if m not in meter_to_files:
                        meter_to_files[m] = []
                    if file_name not in meter_to_files[m]:
                        meter_to_files[m].append(file_name)
            
            elif file_name.endswith('.pdf'):
                meters_from_file = extract_meters_from_pdf(uploaded_file)
                for m in meters_from_file:
                    all_extracted_meters.append(m)
                    if m not in meter_to_files:
                        meter_to_files[m] = []
                    if file_name not in meter_to_files[m]:
                        meter_to_files[m].append(file_name)

        if all_extracted_meters:
            st.success(f"נטענו בהצלחה {len(all_extracted_meters)} מופעים!")

    xml_meters_unique = sorted(list(meter_to_files.keys()))
    accuracy_text_default = "\n".join(xml_meters_unique) if xml_meters_unique else ""
    
    accuracy_meters_text = st.text_area(
        "תוצאות בדיקת דיוק (או הדבק ידנית):", 
        value=accuracy_text_default,
        height=260, 
        placeholder="מונים לבדיקת דיוק..."
    )

with col3:
    st.subheader("⚙️ בדיקה פונקציונלית")
    uploaded_excel = st.file_uploader("טען קובץ אקסל או ZIP פונקציונלי:", type=["xlsx", "xls", "zip", "txt"])
    
    excel_meters = []
    if uploaded_excel is not None:
        if uploaded_excel.name.endswith('.zip'):
            try:
                with zipfile.ZipFile(uploaded_excel, 'r') as z:
                    for zip_info in z.namelist():
                        if zip_info.endswith(('.xlsx', '.xls')):
                            with z.open(zip_info) as excel_file:
                                meters_from_file = extract_meters_from_excel(excel_file)
                                excel_meters.extend(meters_from_file)
                excel_meters = list(set(excel_meters))
            except Exception as e:
                st.error(f"שגיאה בחילוץ קובץ ה-ZIP הפונקציונלי: {e}")
        elif uploaded_excel.name.endswith(('.xlsx', '.xls')):
            excel_meters = extract_meters_from_excel(uploaded_excel)
            
        if excel_meters:
            st.success(f"נטענו בהצלחה {len(excel_meters)} מונים!")
            
    functional_text_default = "\n".join(excel_meters) if excel_meters else ""
    
    functional_meters_text = st.text_area(
        "תוצאות בדיקה פונקציונלית (או הדבק ידנית):", 
        value=functional_text_default,
        height=260, 
        placeholder="מונים לבדיקה פונקציונלית..."
    )

st.divider()

# כפתור בדיקה ראשי
run_check = st.button("🔍 בדיקה", type="primary", use_container_width=True)

# פונקציית נרמול אחידה לפי 6 ספרות אחרונות
def normalize_meter(val):
    cleaned = re.sub(r'\D', '', val)
    if not cleaned:
        return ''
    if len(cleaned) >= 6:
        return cleaned[-6:]
    return cleaned

if run_check:
    st.session_state['checked'] = True

if st.session_state.get('checked', False):
    # איסוף רשימות גולמיות לבדיקת כפילויות בעגלה
    cart_lines = [line.strip() for line in cart_meters_text.splitlines() if line.strip()]
    cart_normalized_list = [normalize_meter(line) for line in cart_lines if normalize_meter(line)]
    
    set_cart = set(cart_normalized_list)
    set_accuracy = {normalize_meter(line) for line in accuracy_meters_text.splitlines() if normalize_meter(line)}
    set_functional = {normalize_meter(line) for line in functional_meters_text.splitlines() if normalize_meter(line)}

    # הצלבות
    missing_in_accuracy = sorted(list(set_cart - set_accuracy))
    missing_in_functional = sorted(list(set_cart - set_functional))
    checked_in_functional = sorted(list(set_cart & set_functional))

    # איתור כפילויות בעגלה
    cart_counts = {m: cart_normalized_list.count(m) for m in set_cart}
    cart_duplicates = {m: count for m, count in cart_counts.items() if count > 1}

    st.subheader("📋 סיכום ותוצאות הצלבה")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("סה״כ בעגלה (יחודי)", len(set_cart))
    m2.metric("נבדקו פונקציונלית", len(checked_in_functional))
    m3.metric("חסרים בדיוק", len(missing_in_accuracy))
    m4.metric("חסרים בפונקציונלית", len(missing_in_functional))

    tab1, tab2, tab3, tab4 = st.tabs(["❌ מונים חסרים", "⚙️ נבדקו פונקציונלית", "🔍 איתור כפילויות (עגלה ו-XML)", "📊 דוח מלא להורדה"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.error(f"מונים בעגלה ש**לא נמצאו** בבדיקת דיוק ({len(missing_in_accuracy)}):")
            if missing_in_accuracy:
                df_acc = pd.DataFrame({"6 ספרות אחרונות חסרות בדיוק": missing_in_accuracy})
                st.dataframe(df_acc, use_container_width=True)
            else:
                st.success("הכל קיים בבדיקת הדיוק!")

        with col_b:
            st.error(f"מונים בעגלה ש**לא נמצאו** בבדיקה פונקציונלית ({len(missing_in_functional)}):")
            if missing_in_functional:
                df_func = pd.DataFrame({"6 ספרות אחרונות חסרות בפונקציונלית": missing_in_functional})
                st.dataframe(df_func, use_container_width=True)
            else:
                st.success("הכל קיים בבדיקה הפונקציונלית!")

    with tab2:
        st.subheader(f"✅ מונים בעגלה שעברו בדיקה פונקציונלית בהצלחה ({len(checked_in_functional)}):")
        if checked_in_functional:
            df_checked_func = pd.DataFrame({"6 ספרות אחרונות שנבדקו פונקציונלית": checked_in_functional})
            st.dataframe(df_checked_func, use_container_width=True)
        else:
            st.info("אין מונים בעגלה שעברו בדיקה פונקציונלית.")

    with tab3:
        st.subheader("🔍 כפילויות בעגלה")
        if cart_duplicates:
            dup_cart_data = [{"6 ספרות אחרונות": m, "כמות הופעות בעגלה": cnt} for m, cnt in cart_duplicates.items()]
            df_dup_cart = pd.DataFrame(dup_cart_data)
            st.warning(f"נמצאו {len(cart_duplicates)} מונים שמופיעים יותר מפעם אחת בעגלה:")
            st.dataframe(df_dup_cart, use_container_width=True)
        else:
            st.success("אין כפילויות בעגלה! כל מונה מופיע פעם אחת בלבד.")

        st.divider()

        st.subheader("🔍 מונים שמופיעים ביותר מקובץ XML אחד (כפילויות דיוק)")
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
                df_dup = pd.DataFrame(duplicates_data)
                st.warning(f"נמצאו {len(duplicates_data)} מונים המופיעים ביותר מקובץ XML אחד:")
                st.dataframe(df_dup, use_container_width=True)
            else:
                st.success("אין כפילויות בקבצי הדיוק!")
        else:
            st.info("טען קבצי דיוק כדי לראות ניתוח כפילויות.")

    with tab4:
        st.write("הפקת דוח ריכוז, חוסרים והשוואות לאקסל:")
        if set_cart:
            all_unique = sorted(list(set_cart | set_accuracy | set_functional))
            report_data = []
            for m in all_unique:
                report_data.append({
                    "6 ספרות אחרונות": m,
                    "נמצא בעגלה": "כן" if m in set_cart else "לא",
                    "עבר בדיקת דיוק": "כן" if m in set_accuracy else "לא",
                    "עבר בדיקה פונקציונלית": "כן" if m in set_functional else "לא"
                })
            df_report = pd.DataFrame(report_data)
            st.dataframe(df_report, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_report.to_excel(writer, index=False, sheet_name='דוח מרוכז')
            
            st.download_button(
                label="📥 הורד דוח מלא לאקסל (Excel)",
                data=buffer.getvalue(),
                file_name="דוח_בדיקת_מונים_מרוכז.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("הכנס נתונים בעגלה כדי להפיק דוח.")
else:
    st.info("לחץ על כפתור **'בדיקה'** האדום למעלה כדי להציג את תוצאות ההצלבה והדוחות.")
