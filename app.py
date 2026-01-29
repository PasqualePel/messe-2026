import streamlit as st
import datetime
from fpdf import FPDF

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")

st.title("⛪ Gestão de Turnos de Missas - 2026")

# --- 1. DATI (Le liste) ---
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
    
    # Intestazioni PDF
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 7, "Data", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Comunidade", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Hora", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Celebrante", 1, 0, 'C', 1)
    pdf.cell(55, 7, "Notas", 1, 1, 'C', 1)
    
    domeniche_del_mese = [d for d in domeniche_2026 if d.month == mese_numero]
    
    for domenica in domeniche_del_mese:
        data_str = domenica.strftime("%d/%m/%Y")
        
        # Variabile per non ripetere la data troppe volte (opzionale, ma sta meglio)
        prima_riga_domenica = True 
        
        for nome_comunita, orari in comunita_orari.items():
            for idx, orario in enumerate(orari):
                key_id = f"{data_str}_{nome_comunita}_{orario}"
                dati_salvati = st.session_state['dati_messe'].get(key_id, {})
                
                cel = dati_salvati.get('celebrante', "Selecionar...")
                if cel == "Selecionar...": cel = "---"
                nota = dati_salvati.get('note', "")
                
                # --- LOGICA VISIVA ---
                # 1. Gestione Data: La scriviamo solo alla prima riga della domenica? 
                # Se vuoi la data su tutte le righe, lascia così. Se la vuoi una volta sola, dimmelo.
                data_visualizzata = data_str 
                
                # 2. Gestione Comunità: Scriviamo il nome solo se è il primo orario (idx == 0)
                if idx == 0:
                    comunita_visualizzata = nome_comunita
                else:
                    comunita_visualizzata = "" # Lasciamo vuoto per il secondo orario
                
                # Encoding caratteri
                com_enc = comunita_visualizzata.encode('latin-1', 'replace').decode('latin-1')
                cel_enc = cel.encode('latin-1', 'replace').decode('latin-1')
                nota_enc = nota.encode('latin-1', 'replace').decode('latin-1')

                pdf.cell(25, 7, data_visualizzata, 1)
                pdf.cell(45, 7, com_enc, 1)
                pdf.cell(15, 7, orario, 1, 0, 'C')
                pdf.cell(50, 7, cel_enc, 1)
                pdf.cell(55, 7, nota_enc, 1, 1)
                
                prima_riga_domenica = False
        
        # Riga separatrice grigia tra una domenica e l'altra
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
        # --- Sezione PDF ---
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button(f"📥 Baixar PDF {mesi[mese_num]}", key=f"pdf_{mese_num}"):
                data_pdf = crea_pdf_mensile(mese_num, mesi[mese_num])
                st.download_button("Salvar Arquivo", data_pdf, f"Messe_{mesi[mese_num]}.pdf", "application/pdf")
        
        st.write("---")
        
        # --- Sezione Calendario ---
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
                    for idx, orario in enumerate(orari):
                        
                        riga = st.columns([2, 1, 2, 2])
                        
                        # Nome Comunità (grassetto solo al primo orario)
                        if idx == 0:
                            riga[0].markdown(f"**{nome_comunita}**")
                        else:
                            riga[0].markdown(f"↳") # Piccola freccia per indicare "idem"
                            
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
                    st.write("")
