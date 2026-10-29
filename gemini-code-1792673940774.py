import io
import re
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

st.set_page_config(page_title="מערכת בדיקת מונים וברקודים", page_icon="📊", layout="wide")

st.title("📊 מערכת ניהול ובדיקת מונים וברקודים")
st.write("סריקת אקדח ברקוד בעגלה, טעינת קבצי XML לבדיקת דיוק, וטעינת קובץ אקסל פונקציונלי (השוואה לפי 6 ספרות אחרונות).")

# פונקציה לחילוץ מונים מקובץ XML לבדיקת דיוק
def extract_meters_from_xml(uploaded_file):
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        extracted = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                val = elem.text.strip()
                cleaned_val = re.sub(r'\D', '', val)
                if len(cleaned_val) == 12 and cleaned_val.startswith('050'):
                    extracted.append(cleaned_val)
        return extracted
    except Exception as e:
        st.error(f"שגיאה בקריאת הקובץ: {e}")
        return []

# פונקציה לחילוץ מונים מקובץ אקסל לבדיקה פונקציונלית (עמודה B)
def extract_meters_from_excel(uploaded_file):
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df_excel = pd.read_excel(xls, sheet_name=sheet_name)
        
        # לקיחת עמודה B (אינדקס 1)
        if df_excel.shape[1] > 1:
            col_b = df_excel.iloc[:, 1].astype(str).str.strip()
            extracted = []
            for val in col_b:
                cleaned_val = re.sub(r'\D', '', val)
                if len(cleaned_val) >= 6:
                    # לקיחת 6 הספרות האחרונות
                    extracted.append(cleaned_val[-6:])
            return list(set(extracted))
        else:
            st.error("קובץ האקסל חייב להכיל לפחות שתי עמודות (עמודה B).")
            return []
    except Exception as e:
        st.error(f"שגיאה בקריאת קובץ האקסל: {e}")
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
    uploaded_xmls = st.file_uploader(
        "טען קבצי XML לבדיקת דיוק (בחר את כולם יחד):", 
        type=["xml"], 
        accept_multiple_files=True
    )
    
    meter_to_files = {}
    all_extracted_meters = []

    if uploaded_xmls:
        for uploaded_file in uploaded_xmls:
            file_name = uploaded_file.name
            meters_from_file = extract_meters_from_xml(uploaded_file)
            for m in meters_from_file:
                all_extracted_meters.append(m)
                if m not in meter_to_files:
                    meter_to_files[m] = []
                if file_name not in meter_to_files[m]:
                    meter_to_files[m].append(file_name)
        
        if all_extracted_meters:
            st.success(f"נטענו בהצלחה {len(all_extracted_meters)} מופעים מתוך {len(uploaded_xmls)} קבצים!")
    
    xml_meters_unique = sorted(list(meter_to_files.keys()))
    accuracy_text_default = "\n".join(xml_meters_unique) if xml_meters_unique else ""
    
    accuracy_meters_text = st.text_area(
        "ברקודים מבדיקת הדיוק (או הדבק ידנית):", 
        value=accuracy_text_default,
        height=300, 
        placeholder="תוצאות בדיקת דיוק..."
    )

with col3:
    st.subheader("⚙️ בדיקה פונקציונלית")
    uploaded_excel = st.file_uploader("טען קובץ אקסל לבדיקה פונקציונלית:", type=["xlsx", "xls"])
    
    excel_meters = []
    if uploaded_excel is not None:
        excel_meters = extract_meters_from_excel(uploaded_excel)
        if excel_meters:
            st.success(f"נטענו בהצלחה {len(excel_meters)} מונים מקובץ האקסל!")
            
    functional_text_default = "\n".join(excel_meters) if excel_meters else ""
    
    functional_meters_text = st.text_area(
        "ברקודים מהבדיקה הפונקציונלית (או הדבק ידנית):", 
        value=functional_text_default,
        height=300, 
        placeholder="תוצאות בדיקה פונקציונלית..."
    )

st.divider()

# פונקציית נרמול אחידה: חילוץ 6 הספרות האחרונות מכל מספר לצורך השוואה מדויקת
def normalize_meter(val):
    cleaned = re.sub(r'\D', '', val)
    if not cleaned:
        return ''
    # לקיחת 6 הספרות האחרונות
    if len(cleaned) >= 6:
        return cleaned[-6:]
    return cleaned

def process_text_to_set(text_data):
    return {normalize_meter(line) for line in text_data.splitlines() if normalize_meter(line)}

set_cart = process_text_to_set(cart_meters_text)
set_accuracy = process_text_to_set(accuracy_meters_text)
set_functional = process_text_to_set(functional_meters_text)

# הצלבות
missing_in_accuracy = sorted(list(set_cart - set_accuracy))
missing_in_functional = sorted(list(set_cart - set_functional))

st.subheader("📋 סיכום ותוצאות הצלבה")

m1, m2, m3, m4 = st.columns(4)
m1.metric("סה״כ בעגלה", len(set_cart))
m2.metric("בבדיקת דיוק", len(set_accuracy))
m3.metric("חסרים בדיוק", len(missing_in_accuracy))
m4.metric("חסרים בפונקציונלית", len(missing_in_functional))

tab1, tab2, tab3 = st.tabs(["❌ מונים חסרים", "🔍 איתור כפילויות בין קבצים", "📊 דוח מלא להורדה"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"מונים בעגלה ש**לא נמצאו** בבדיקת דיוק ({len(missing_in_accuracy)}):")
        if missing_in_accuracy:
            df_acc = pd.DataFrame({"ברקוד חסר בדיוק": missing_in_accuracy})
            st.dataframe(df_acc, use_container_width=True)
        else:
            st.success("הכל קיים בבדיקת הדיוק!")

    with col_b:
        st.error(f"מונים בעגלה ש**לא נמצאו** בבדיקה פונקציונלית ({len(missing_in_functional)}):")
        if missing_in_functional:
            df_func = pd.DataFrame({"ברקוד חסר פונקציונלית": missing_in_functional})
            st.dataframe(df_func, use_container_width=True)
        else:
            st.success("הכל קיים בדיקה הפונקציונלית!")

with tab2:
    st.subheader("🔍 מונים שמופיעים ביותר מקובץ XML אחד (כפילויות)")
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
            st.warning(f"נמצאו {len(duplicates_data)} מונים המופיעים ביותר מקובץ אחד:")
            st.dataframe(df_dup, use_container_width=True)
        else:
            st.success("אין כפילויות! כל מונה מופיע בקובץ אחד בלבד.")
    else:
        st.info("טען קבצי XML כדי לראות ניתוח כפילויות.")

with tab3:
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
        with pd.ExcelWriter(buffer, engine='openpyxl') as
