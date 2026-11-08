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
st.write("ניהול עגלה, בדיקת דיוק (XML, PDF, ZIP או הדבקה), ובדיקה פונקציונלית (אקסל, ZIP או הדבקה לפי 6 ספרות אחרונות).")

# פונקציה משופרת לחילוץ מונים מקובץ XML (מתמודדת עם אפסים מובילים ומאתרת 050)
def extract_meters_from_xml_content(xml_content):
    try:
        root = ET.fromstring(xml_content)
        extracted = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                val = elem.text.strip()
                cleaned_val = re.sub(r'\D', '', val)
                if '050' in cleaned_val and len(cleaned_val) >= 10:
                    match = re.search(r'(050\d{9})', cleaned_val)
                    if match:
                        extracted.append(match.group(1))
                    else:
                        extracted.append(cleaned_val.
