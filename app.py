import streamlit as st
import datetime
from fpdf import FPDF

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestão de Missas", layout="wide")

st.title("⛪ Gestão de Turnos de Missas - Paróquia")

# --- 1. DATI ---
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

# --- 2. FUNZIONI ---
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

def crea_pdf_mensile(mese_numero, nome_mese):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Escala de Missas - {nome_mese} 2026", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    
    # Intestazioni
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 7, "Data", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Comunidade", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Hora", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Celebrante", 1, 0, 'C', 1)
    pdf.cell(55, 7, "Notas", 1, 1, 'C', 1)
    
    # Dati del mese
    domeniche_del_mese = [d for d in domeniche_2026 if d.month == mese_numero]
    
    for domenica in domeniche_del_mese:
        data_str = domenica.strftime("%d/%m/%Y")
        for nome_comunita, orari in comunita_orari.items():
            for orario in orari:
                key_id = f"{data_str}_{nome_comunita}_{orario}"
                dati_salvati = st.session_state['dati_messe'].get(key_id, {})
                
                cel = dati_salvati.get('celebrante', "Selecionar...")
                nota = dati_salvati.get('note', "")
                if cel == "Selecionar...": cel = "---"
                
                # Encoding
                com_txt = nome_comunita.encode('latin-1', 'replace').decode('latin-1')
                cel_txt = cel.encode('latin-1', 'replace').decode('latin-1')
                nota_txt = nota.encode('latin-1', 'replace').decode('latin-1')
                
                pdf.cell(25, 7, data_str, 1)
                pdf.cell(45, 7, com_txt, 1)
                pdf.cell(15, 7, orario, 1, 0, 'C')
                pdf.cell(50, 7, cel_txt, 1)
                pdf.cell(55, 7, nota_txt, 1, 1)
        
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 2, "", 1, 1, 'C', 1)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. INTERFACCIA ---
mesi = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

tabs = st.tabs(list(mesi.values()))

for i, mese_num in enumerate(mesi):
    nome_mese = mesi[mese_num]
    with tabs[i]:
        # --- ZONA ALTA: PDF ---
        c_sx, c_dx = st.columns([3, 1])
        with c_dx:
            if st.button(f"📥 Baixar PDF {nome_mese}", key=f"btn_{mese_num}"):
                pdf_data = crea_pdf_mensile(mese_num, nome_mese)
                st.download_button("Clique para Salvar", pdf_data, f"Missas_{nome_mese}.pdf", "application/pdf")
        
        st.markdown("---")
        st.markdown(f"### 👇 INSERISCI QUI I TURNI DI: {nome_mese.upper()}")
        
        # --- ZONA BASSA: INPUT ---
        domeniche_mese = [d for d in domeniche_2026 if d.month == mese_num]
        
        for domenica in domeniche_mese:
            data_str = domenica.strftime("%d/%m/%Y")
            
            with st.expander(f"Domingo {data_str}", expanded=True):
                # Intestazione Colonne
                k1, k2, k3, k4 = st.columns([2, 1, 2, 2])
                k1.caption("Comunidade")
                k2.caption("Hora")
                k3.caption("Celebrante")
