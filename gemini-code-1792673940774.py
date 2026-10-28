import io
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

st.set_page_config(page_title="מערכת בדיקת מונים וברקודים", page_icon="📊", layout="wide")

st.title("📊 מערכת ניהול ובדיקת מונים וברקודים")
st.write("ניהול עגלה (כולל טעינת קובץ XML), הצלבה מול בדיקת דיוק ובדיקה פונקציונלית.")

# פונקציה לחילוץ מונים מקובץ XML
def extract_meters_from_xml(uploaded_file):
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        # מחפש כל ערך טקסטריות או תגים נפוצים ב-XML שיכולים להכיל מונים/ברקודים
        extracted = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                val = elem.text.strip()
                # סינון בסיסי למספרים/ברקודים (למשל באורך הגיוני)
                if len(val) >= 5:
                    extracted.append(val)
        return list(set(extracted))
    except Exception as e:
        st.error(f"שגיאה בקריאת קובץ ה-XML: {e}")
        return []

# חלוקה ל-3 עמודות כמבוקש
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🛒 עגלה")
    uploaded_xml = st.file_uploader("טען קובץ XML לחילוץ ברקודים:", type=["xml"])
    
    xml_meters = []
    if uploaded_xml is not None:
        xml_meters = extract_meters_from_xml(uploaded_xml)
        if xml_meters:
            st.success(ف`נטענו {len(xml_meters)} מונים מקובץ ה-XML!`)
    
    cart_text_default = "\n".join(xml_meters) if xml_meters else ""
    
    cart_meters_text = st.text_area(
        "סרוק ברקודים כאן — ברקוד בכל שורה:", 
        value=cart_text_default,
        height=300, 
        placeholder="סרוק או הדבק ברקודים בעגלה..."
    )

with col2:
    st.subheader("🔍 בדיקת דיוק")
    accuracy_meters_text = st.text_area(
        "הדבק כאן ברקודים מבדיקת הדיוק:", 
        height=380, 
        placeholder="הדבק כאן תוצאות בדיקת דיוק..."
    )

with col3:
    st.subheader("⚙️ בדיקה פונקציונלית")
    functional_meters_text = st.text_area(
        "הדבק כאן ברקודים מהבדיקה הפונקציונלית:", 
        height=380, 
        placeholder="הדבק כאן תוצאות בדיקה פונקציונלית..."
    )

st.divider()

# עיבוד וניקוי נתונים
def clean_list(text_data):
    return {line.strip() for line in text_data.splitlines() if line.strip()}

set_cart = clean_list(cart_meters_text)
set_accuracy = clean_list(accuracy_meters_text)
set_functional = clean_list(functional_meters_text)

# הצלבות
missing_in_accuracy = sorted(list(set_cart - set_accuracy))
missing_in_functional = sorted(list(set_cart - set_functional))

st.subheader("📋 סיכום ותוצאות הצלבה")

m1, m2, m3, m4 = st.columns(4)
m1.metric("סה״כ בעגלה", len(set_cart))
m2.metric("בבדיקת דיוק", len(set_accuracy))
m3.metric("חסרים בדיוק", len(missing_in_accuracy))
m4.metric("חסרים בפונקציונלית", len(missing_in_functional))

tab1, tab2 = st.tabs(["❌ מונים חסרים", "📊 דוח מלא להורדה"])

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
    st.write("הפקת דוח ריכוז, חוסרים והשוואות לאקסל:")
    if set_cart:
        # יצירת טבלת השוואה מרוכזת
        all_unique = sorted(list(set_cart | set_accuracy | set_functional))
        report_data = []
        for m in all_unique:
            report_data.append({
                "ברקוד / מונה": m,
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
