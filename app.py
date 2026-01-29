import streamlit as st
import pdfplumber
import os

st.title("🕵️‍♂️ Ispettore PDF Liturgico")

# Nomi possibili del file
files = ["calendario-liturgico-2026-definitivo.pdf", "calendario_2026.pdf"]
path = next((f for f in files if os.path.exists(f)), None)

if not path:
    st.error("❌ File non trovato su GitHub!")
else:
    st.success(f"✅ File trovato: {path}")
    st.write("Ecco le prime 2 pagine come le vede il computer. Copia questo testo e mandalo al tecnico:")
    
    try:
        with pdfplumber.open(path) as pdf:
            # Leggiamo le prime 2 pagine
            testo_grezzo = ""
            for i in range(min(2, len(pdf.pages))):
                testo_grezzo += f"--- PAGINA {i+1} ---\n"
                testo_grezzo += pdf.pages[i].extract_text() + "\n\n"
            
            # Mostriamo il testo in un box codice
            st.code(testo_grezzo)
    except Exception as e:
        st.error(f"Errore lettura: {e}")
