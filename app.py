import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")
st.title("⛪ Gestão de Turnos de Missas - 2026 (Online)")

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Leggiamo i dati esistenti
try:
    # ttl=0 assicura che leggiamo sempre i dati freschi
    df_dati = conn.read(worksheet="Foglio1", ttl=0)
    df_dati = df_dati.astype(str) # Convertiamo tutto in testo per sicurezza
except Exception as e:
    st.error(f"Errore di connessione. Verifica di aver condiviso il foglio con l'email del robot e di aver messo il link nei Secrets. Errore: {e}")
    st.stop()

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

domeniche_2026 = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    domeniche_2026.append(d)
    d += datetime.timedelta(days=7)

def safe_encode(text):
    if text == "nan" or text == "None": return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

# Funzione per ottenere dati dal DataFrame scaricato
def get_data_from_df(key):
    # Cerca la riga con questa key_id
    row = df_dati[df_dati['key_id'] == key]
    if not row.empty:
        c = row.iloc[0]['celebrante']
        n = row.iloc[0]['note']
        return (c if c != "nan" else "Selecionar..."), (n if n != "nan" else "")
    return "Selecionar...", ""

# Funzione per aggiornare Google Sheets
def update_google_sheet(key, celebrante, note):
    try:
        # Rileggiamo i dati attuali
        df_current = conn.read(worksheet="Foglio1", ttl=0)
        df_current = df_current.astype(str)
        
        # Se la colonna key_id non esiste, la creiamo (sicurezza)
        if 'key_id' not in df_current.columns:
            df_current['key_id'] = ""
            df_current['celebrante'] = ""
            df_current['note'] = ""

        # Aggiorniamo o aggiungiamo
        if key in df_current['key_id'].values:
            df_current.loc[df_current['key_id'] == key, 'celebrante'] = celebrante
            df_current.loc[df_current['key_id'] == key, 'note'] = note
        else:
            new_row = pd.DataFrame([{'key_id': key, 'celebrante': celebrante, 'note': note}])
            new_row = new_row.astype(str)
            df_current = pd.concat([df_current, new_row], ignore_index=True)
            
        conn.update(worksheet="Foglio1", data=df_current)
        st.toast("Salvo! ✅") # Conferma visiva
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")

# --- PDF ---
def crea_pdf_mensile(mese_numero, nome_mese):
    # Rileggiamo il DB per la stampa
    df_print = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_encode(f"Escala de Missas - {nome_mese} 2026"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(25, 7, "Data", 1, 0, 'C', 1)
    pdf.cell(45, 7, "Comunidade", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Hora", 1, 0, 'C', 1)
    pdf.cell(50, 7, "Celebrante", 1, 0, 'C', 1)
    pdf.cell(55, 7, "Notas", 1, 1, 'C', 1)
    
    domeniche_del_mese = [x for x in domeniche_2026 if x.month == mese_numero]
    
    # Funzione interna per cercare nel df_print
    def get_print(k):
        r = df_print[df_print['key_id'] == k]
        if not r.empty:
            c = r.iloc[0]['celebrante']
            n = r.iloc[0]['note']
            return (c if c!="nan" else "Selecionar..."), (n if n!="nan" else "")
        return "Selecionar...", ""

    for domenica in domeniche_del_mese:
        data_str = domenica.strftime("%d/%m/%Y")
        for nome_comunita, orari in comunita_orari.items():
            
            if len(orari) == 2: # Celle unite
                x = pdf.get_x()
                y = pdf.get_y()
                h = 7
                pdf.cell(25, h*2, data_str, 1, 0, 'C')
                pdf.cell(45, h*2, safe_encode(nome_comunita), 1, 0, 'L')
                x_split = pdf.get_x()
                
                # Riga 1
                k1 = f"{data_str}_{nome_comunita}_{orari[0]}"
                c1, n1 = get_print(k1)
                if c1 == "Selecionar...": c1 = "---"
                pdf.cell(15, h, orari[0], 1, 0, 'C')
                pdf.cell(50, h, safe_encode(c1), 1, 0, 'L')
                pdf.cell(55, h, safe_encode(n1), 1, 1, 'L')
                
                # Riga 2
                pdf.set_xy(x_split, y + h)
                k2 = f"{data_str}_{nome_comunita}_{orari[1]}"
                c2, n2 = get_print(k2)
                if c2 == "Selecionar...": c2 = "---"
                pdf.cell(15, h, orari[1], 1, 0, 'C')
                pdf.cell(50, h, safe_encode(c2), 1, 0, 'L')
                pdf.cell(55, h, safe_encode(n2), 1, 1, 'L')
            else:
                k = f"{data_str}_{nome_comunita}_{orari[0]}"
                c, n = get_print(k)
                if c == "Selecionar...": c = "---"
                pdf.cell(25, 7, data_str, 1, 0, 'C')
                pdf.cell(45, 7, safe_encode(nome_comunita), 1, 0, 'L')
                pdf.cell(15, 7, orari[0], 1, 0, 'C')
                pdf.cell(50, 7, safe_encode(c), 1, 0, 'L')
                pdf.cell(55, 7, safe_encode(n), 1, 1, 'L')

        pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 2, "", 1, 1, 'C', 1)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFACCIA ---
mesi = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

tabs = st.tabs(list(mesi.values()))

for i, mese_num in enumerate(mesi):
    with tabs[i]:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button(f"📥 Baixar PDF {mesi[mese_num]}", key=f"p_{mese_num}"):
                d_pdf = crea_pdf_mensile(mese_num, mesi[mese_num])
                st.download_button("Salvar Arquivo", d_pdf, f"Messe_{mesi[mese_num]}.pdf", "application/pdf")
        st.write("---")
        
        doms = [x for x in domeniche_2026 if x.month == mese_num]
        for d in doms:
            d_str = d.strftime("%d/%m/%Y")
            with st.expander(f"Domingo {d_str}", expanded=True):
                cols = st.columns([2, 1, 2, 2])
                cols[0].markdown("**Comunidade**")
                cols[1].markdown("**Hora**")
                cols[2].markdown("**Celebrante**")
                cols[3].markdown("**Notas**")
                
                for com, orari in comunita_orari.items():
                    with st.container():
                        for idx, orario in enumerate(orari):
                            r = st.columns([2, 1, 2, 2])
                            if idx == 0: r[0].markdown(f"**{com}**")
                            else: r[0].markdown("↳")
                            r[1].write(orario)
                            
                            # Logica DB
                            kid = f"{d_str}_{com}_{orario}"
                            # Leggiamo dal DF scaricato all'inizio
                            cel_db, note_db = get_data_from_df(kid)
                            
                            idx_cel = celebranti.index(cel_db) if cel_db in celebranti else 0
                            
                            def on_change_callback(k=kid):
                                # Quando l'utente cambia, salviamo subito su Google
                                nc = st.session_state[f"s_{k}"]
                                nn = st.session_state[f"n_{k}"]
                                update_google_sheet(k, nc, nn)
                            
                            r[2].selectbox("C", celebranti, key=f"s_{kid}", index=idx_cel, label_visibility="collapsed", on_change=on_change_callback)
                            r[3].text_input("N", key=f"n_{kid}", value=note_db, label_visibility="collapsed", on_change=on_change_callback)
                        st.write("")
