import streamlit as st
import datetime
from fpdf import FPDF

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")
st.title("⛪ Gestão de Turnos de Missas - 2026")

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

def safe_encode(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def crea_pdf_mensile(mese_numero, nome_mese):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_encode(f"Escala de Missas - {nome_mese} 2026"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    
    # Intestazioni
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 7, "Data", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Comunidade", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Hora", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Celebrante", 1, 0, 'C', 1)
    pdf.cell(55, 7, "Notas", 1, 1, 'C', 1)
    
    domeniche_del_mese = [d for d in domeniche_2026 if d.month == mese_numero]
    
    for domenica in domeniche_del_mese:
        data_str = domenica.strftime("%d/%m/%Y")
        
        for nome_comunita, orari in comunita_orari.items():
            
            # --- CASO A: Comunità con 2 Orari (Celle Unite) ---
            if len(orari) == 2:
                # Salviamo la posizione iniziale (X, Y)
                x_start = pdf.get_x()
                y_start = pdf.get_y()
                row_height = 7
                
                # 1. Disegna la colonna DATA (alta 14)
                pdf.cell(25, row_height * 2, data_str, 1, 0, 'C')
                
                # 2. Disegna la colonna COMUNITA (alta 14) - Questo unisce le righe
                pdf.cell(45, row_height * 2, safe_encode(nome_comunita), 1, 0, 'L')
                
                # Salviamo la X dove iniziano le colonne degli orari
                x_split = pdf.get_x()
                
                # --- PRIMA RIGA (Primo orario) ---
                orario_1 = orari[0]
                key_1 = f"{data_str}_{nome_comunita}_{orario_1}"
                dati_1 = st.session_state['dati_messe'].get(key_1, {})
                cel_1 = dati_1.get('celebrante', "Selecionar...")
                if cel_1 == "Selecionar...": cel_1 = "---"
                nota_1 = dati_1.get('note', "")

                pdf.cell(15, row_height, orario_1, 1, 0, 'C')
                pdf.cell(50, row_height, safe_encode(cel_1), 1, 0, 'L')
                pdf.cell(55, row_height, safe_encode(nota_1), 1, 1, 'L') # ln=1 va a capo
                
                # --- SECONDA RIGA (Secondo orario) ---
                # Spostiamo il cursore manualmente sotto la prima riga, ma allineato a destra del nome
                pdf.set_xy(x_split, y_start + row_height)
                
                orario_2 = orari[1]
                key_2 = f"{data_str}_{nome_comunita}_{orario_2}"
                dati_2 = st.session_state['dati_messe'].get(key_2, {})
                cel_2 = dati_2.get('celebrante', "Selecionar...")
                if cel_2 == "Selecionar...": cel_2 = "---"
                nota_2 = dati_2.get('note', "")

                pdf.cell(15, row_height, orario_2, 1, 0, 'C')
                pdf.cell(50, row_height, safe_encode(cel_2), 1, 0, 'L')
                pdf.cell(55, row_height, safe_encode(nota_2), 1, 1, 'L') # ln=1 va a capo, pronto per prossima comunità
            
            # --- CASO B: Comunità con 1 Orario (Standard) ---
            else:
                orario = orari[0]
                key_id = f"{data_str}_{nome_comunita}_{orario}"
                dati = st.session_state['dati_messe'].get(key_id, {})
                cel = dati.get('celebrante', "Selecionar...")
                if cel == "Selecionar...": cel = "---"
                nota = dati.get('note', "")
                
                pdf.cell(25, 7, data_str, 1, 0, 'C')
                pdf.cell(45, 7, safe_encode(nome_comunita), 1, 0, 'L')
                pdf.cell(15, 7, orario, 1, 0, 'C')
                pdf.cell(50, 7, safe_encode(cel), 1, 0, 'L')
                pdf.cell(55, 7, safe_encode(nota), 1, 1, 'L')

        # Separatore tra le domeniche
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
    with tabs[i]:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button(f"📥 Baixar PDF {mesi[mese_num]}", key=f"pdf_{mese_num}"):
                data_pdf = crea_pdf_mensile(mese_num, mesi[mese_num])
                st.download_button("Salvar Arquivo", data_pdf, f"Messe_{mesi[mese_num]}.pdf", "application/pdf")
        
        st.write("---")
        
        domeniche_mese = [d for d in domeniche_2026 if d.month == mese_num]
        
        for domenica in domeniche_mese:
            data_str = domenica.strftime("%d/%m/%Y")
            
            with st.expander(f"Domingo {data_str}", expanded=True):
                cols = st.columns([2, 1, 2, 2])
                cols[0].markdown("**Comunidade**")
                cols[1].markdown("**Hora**")
                cols[2].markdown("**Celebrante**")
                cols[3].markdown("**Notas**")
                
                for nome_comunita, orari in comunita_orari.items():
                    # Usiamo il container per tenere visivamente uniti gli orari
                    with st.container():
                        for idx, orario in enumerate(orari):
                            riga = st.columns([2, 1, 2, 2])
                            
                            # INTERFACCIA WEB: Mostriamo la freccetta per chiarezza durante la compilazione
                            if idx == 0:
                                riga[0].markdown(f"**{nome_comunita}**")
                            else:
                                riga[0].markdown(f"↳") 
                                
                            riga[1].write(orario)
                            
                            key_id = f"{data_str}_{nome_comunita}_{orario}"
                            saved = st.session_state['dati_messe'].get(key_id, {})
                            
                            val_cel = saved.get('celebrante', "Selecionar...")
                            idx_cel = celebranti.index(val_cel) if val_cel in celebranti else 0
                            cel_scelto = riga[2].selectbox("Cel", celebranti, key=f"s_{key_id}", index=idx_cel, label_visibility="collapsed")
                            
                            val_nota = saved.get('note', "")
                            nota_scritta = riga[3].text_input("N", key=f"n_{key_id}", value=val_nota, label_visibility="collapsed")
                            
                            st.session_state['dati_messe'][key_id] = {
                                "celebrante": cel_scelto,
                                "note": nota_scritta
                            }
                        # Separatore sottile
                        st.write("")
