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
            
            # קובץ ZIP
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
            
            # קובץ XML בודד
            elif file_name.endswith('.xml'):
                meters_from_file = extract_meters_from_xml_content(uploaded_file.read())
                for m in meters_from_file:
                    all_extracted_meters.append(m)
                    if m not in meter_to_files:
                        meter_to_files[m] = []
                    if file_name not in meter_to_files[m]:
                        meter_to_files[m].append(file_name)
            
            # קובץ PDF בודד
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

#
