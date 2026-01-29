import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")

st.title("⛪ Gestão de Turnos de Missas - Ano 2026")
st.markdown("Selecione os celebrantes para cada missa e descarregue o PDF final.")

# --- DATI ---
celebranti = [
    "Selecionar...", 
    "Pe. Pasquale", "Pe. Márcio", "Pe. Stefano", "Pe. Roberto",
    "Pe. Antonio", "Pe. Massimo", "Pe. Pinto", "Pe José Angel",
    "Celebração Ir. Felicia", "Celebração Ir. Marilda", "Celebração", "Ninguém"
]

comunita_orari = {
    "Santa Monica": ["07:00", "09:00"],
    "São Francisco": ["07:00"],
    "São Miguel": ["07:00", "08:45"],
    "Santa Teresa C.": ["07:30"],
    "Santa Isabel": ["07:00"],
    "São João Batista": ["07:30"],
    "São Teodósio": ["07:30"],
    "Maria Auxiliadora": ["07:30"],
    "N.S Fátima": ["08:00"],
    "N.S Lurdes": ["07:30"]
}

# --- FUNZIONI ---
def get_sundays(year):
    d = datetime.date(year, 1, 1)
    d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
    sundays = []
    while d.year == year:
        sundays.append(d)
        d += datetime.timedelta(days=7)
    return sundays

domeniche_2026 = get_sundays(2026)

if 'dati_messe' not in st.session_state:
    st.session_state['dati_messe'] = {}

# --- INTERFACCIA ---
mesi = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

tabs = st.tabs(list(mesi.values()))

for i, mese_num in enumerate(mesi):
    with tabs[i]:
        st.header(f"Missas de {mesi[mese_num]}")
        domeniche_mese = [d for d in domeniche_2026 if d.month == mese_num]
        
        for domenica in domeniche_mese:
            data_str = domenica.strftime("%d/%m/%Y")
            with st.expander(f"Domingo {data_str}", expanded=False):
                # Intestazioni
                c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
                c1.markdown("**Comunidade**")
                c2.markdown("**Hora**")
                c3.markdown("**Celebrante**")
                c4.markdown("**Notas**")
                
                for nome_comunita, orari in comunita_orari.items():
                    for orario in orari:
                        key_id = f"{data_str}_{nome_comunita}_{orario}"
                        
                        col_a, col_b, col_c, col_d = st.columns([2, 1, 2, 2])
                        col_a.write(nome_comunita)
                        col_b.write(orario)
                        
                        saved_cel = st.session_state['dati_messe'].get(key_id, {}).get('celebrante', "Selecionar...")
                        saved_note = st.session_state['dati_messe'].get(key_id, {}).get('note', "")
                        
                        idx = celebranti.index(saved_cel) if saved_cel in celebranti else 0
                        scelta = col_c.selectbox("Cel", celebranti, key=f"c_{key_id}", index=idx, label_visibility="collapsed")
                        nota = col_d.text_input("Nota", key=f"n_{key_id}", value=saved_note, label_visibility="collapsed")
                        
                        st.session_state['dati_messe'][key_id] = {
                            "data": data_str, "comunita": nome_comunita,
                            "orario": orario, "celebrante": scelta, "note": nota
                        }

# --- PDF ---
def crea_pdf(dati):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Calendário de Missas 2026", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    
    # Intestazioni tabella
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(30, 7, "Data", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Comunidade", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Hora", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Celebrante", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Notas", 1, 1, 'C', 1)
    
    # Ordina per data e poi per orario
    lista = sorted(dati.values(), key=lambda x: (datetime.datetime.strptime(x['data'], "%d/%m/%Y"), x['orario']))
    
    for row in lista:
        cel = row['celebrante'] if row['celebrante'] != "Selecionar..." else "---"
        nt = row['note']
        
        # Encoding per caratteri speciali
        pdf.cell(30, 7, row['data'], 1)
        pdf.cell(45, 7, row['comunita'].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(15, 7, row['orario'], 1, 0, 'C')
        pdf.cell(50, 7, cel.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(50, 7, nt.encode('latin-1', 'replace').decode('latin-1'), 1, 1)
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

st.markdown("---")
if st.button("Gerar PDF Calendário"):
    if st.session_state['dati_messe']:
        b = crea_pdf(st.session_state['dati_messe'])
        st.success("Pronto!")
        st.download_button("Descarregar PDF", b, "calendario_2026.pdf", "application/pdf")
    else:
        st.warning("Sem dados.")