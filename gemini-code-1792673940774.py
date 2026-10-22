import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="מערכת בדיקת מונים בעגלה", page_icon="🛒", layout="wide")

st.title("🛒 מערכת בדיקת מונים בעגלה")
st.write("הכנס את רשימות המונים כדי לזהות באופן מיידי איזה מונים שנמצאים בעגלה לא עברו בדיקה.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. קלט מונים")
    cart_meters_text = st.text_area(
        "מונים בעגלה (אחד בכל שורה):", 
        height=220, 
        placeholder="הדבק כאן את מספרי המונים שבעגלה..."
    )
    checked_meters_text = st.text_area(
        "מונים אחרי בדיקה (אחד בכל שורה):", 
        height=220, 
        placeholder="הדבק כאן את מספרי המונים שנבדקו..."
    )

with col2:
    st.subheader("2. תוצאות הצלבה")
    
    # פונקציית ניקוי: הסרת רווחים והסרת אפסים מובילים
    def clean_meter(val):
        cleaned = val.strip()
        return cleaned.lstrip('0') if cleaned else ''

    # עיבוד וניקוי הרשימות
    cart_list = [clean_meter(line) for line in cart_meters_text.splitlines() if clean_meter(line)]
    checked_list = [clean_meter(line) for line in checked_meters_text.splitlines() if clean_meter(line)]
    
    set_cart = set(cart_list)
    set_checked = set(checked_list)
    
    # מונים בעגלה שלא עברו בדיקה
    failed_meters = sorted(list(set_cart - set_checked))
    
    # מדדים חזותיים
    m1, m2, m3 = st.columns(3)
    m1.metric("מונים בעגלה", len(set_cart))
    m2.metric("מונים שעברו בדיקה", len(set_checked))
    m3.metric("בעגלה ולא עברו בדיקה", len(failed_meters))
    
    st.divider()
    
    if failed_meters:
        st.error(f"⚠️ נמצאו {len(failed_meters)} מונים בעגלה שלא עברו בדיקה:")
        df_failed = pd.DataFrame({"מספר מונה בעגלה": failed_meters})
        st.dataframe(df_failed, use_container_width=True)
        
        # יצירת קובץ אקסל להורדה
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_failed.to_excel(writer, index=False, sheet_name='לא עברו בדיקה')
        
        st.download_button(
            label="📥 הורד דוח מונים שלא עברו בדיקה (Excel)",
            data=buffer.getvalue(),
            file_name="מונים_בעגלה_שלא_עברו_בדיקה.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif set_cart and set_checked:
        st.success("🎉 כל המונים שבעגלה עברו בדיקה בהצלחה!")
    else:
        st.info("הכנס נתונים בשני השדות מימין כדי לראות את תוצאות ההצלבה.")