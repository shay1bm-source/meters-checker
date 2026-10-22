import re
import io
import pandas as pd
import streamlit as st
from PIL import Image
import pytesseract

# הגדרות עמוד
st.set_page_config(
    page_title="מערכת הצלבת מונים",
    page_icon="⚡",
    layout="wide"
)

# עיצוב מימין לשמאל (RTL)
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-baseweb="textarea"] { direction: ltr; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ מערכת הצלבת מונים וזיהוי OCR")
st.write("העלה תמונות מונים או הדבק רשימות כדי לזהות באופן מיידי את המונים שלא נקלטו במערכת.")

# חלוקה לעמודות
col_input, col_results = st.columns([1, 1])

with col_input:
    st.subheader("1. קלט נתונים")
    
    # העלאת תמונות ל-OCR
    uploaded_files = st.file_uploader(
        "העלה תמונות מונים לסריקה (אופציונלי)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    ocr_numbers = set()
    if uploaded_files:
        with st.spinner("מבצע OCR ותמונות..."):
            for file in uploaded_files:
                try:
                    img = Image.open(file)
                    text = pytesseract.image_to_string(img, config='--psm 6 digits')
                    found = re.findall(r'\b\d{5,15}\b', text)
                    ocr_numbers.update(found)
                except Exception as e:
                    st.error(f"שגיאה בפענוח הקובץ {file.name}: {e}")
            st.success(f"חולצו {len(ocr_numbers)} מספרים מהתמונות!")

    # תיבות טקסט לרשימות
    all_meters_default = "\n".join(sorted(list(ocr_numbers))) if ocr_numbers else ""
    
    all_meters_text = st.text_area(
        "רשימת המונים המלאה (אחד בכל שורה):", 
        value=all_meters_default, 
        height=200
    )
    
    processed_meters_text = st.text_area(
        "רשימת המונים שהוכנסו בהצלחה בדוח (אחד בכל שורה):", 
        height=200
    )

with col_results:
    st.subheader("2. תוצאות הצלבה")
    
    # עיבוד נתונים
    all_list = [line.strip() for line in all_meters_text.splitlines() if line.strip()]
    processed_list = [line.strip() for line in processed_meters_text.splitlines() if line.strip()]
    
    set_all = set(all_list)
    set_processed = set(processed_list)
    missing_meters = sorted(list(set_all - set_processed))
    
    # מדדים
    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ נבדקו", len(set_all))
    m2.metric("נקלטו בהצלחה", len(set_processed))
    m3.metric("לא נקלטו", len(missing_meters))
    
    st.divider()
    
    if missing_meters:
        st.error(f"נמצאו {len(missing_meters)} מונים שלא נקלטו:")
        df_missing = pd.DataFrame({"מספר מונה": missing_meters})
        st.dataframe(df_missing, use_container_width=True)
        
        # יצוא ל-Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_missing.to_excel(writer, index=False, sheet_name='מונים חסרים')
        
        st.download_button(
            label="📥 הורד דוח מונים חסרים (Excel)",
            data=buffer.getvalue(),
            file_name="מונים_שלא_נקלטו.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif set_all and set_processed:
        st.success("🎉 כל המונים נקלטו בהצלחה!")
    else:
        st.info("הכנס נתונים בתיבות הקלט כדי לראות את התוצאות.")