import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import pdfplumber
import re
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")
st.title("⛪ Gestão de Turnos de Missas - 2026 (Online)")

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_dati = conn.read(worksheet="Foglio1", ttl=0)
    df_dati = df_dati.astype(str)
except Exception as e:
    st.error(f"Errore di connessione. Verifica i Secrets. Errore: {e}")
    st.stop()

# --- DATI STATICI ---
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

nomi_mesi = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

# --- FUNZIONE MAGICA: ESTRAZIONE LITURGIA ---
@st.cache_data # Memorizza il risultato per non rileggere il PDF ogni volta che clicchi
def carica_liturgia_da_pdf():
    liturgia_dict = {}
    nome_file = "calendario_2026.pdf" # Il file che hai caricato su GitHub
    
    if not os.path.exists(nome_file):
        return {} # Se non trova il file, restituisce vuoto senza rompersi

    try:
        with pdfplumber.open(nome_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Pulizia base del testo
            lines = full_text.split('\n')
            
            # Logica di estrazione: Cerchiamo le date (es: "11 JANEIRO")
            current_date = None
            buffer_text = []
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Regex per trovare date tipo "01 JANEIRO" o "1 JANEIRO"
                match = re.match(r"^(\d{1,2})\s+(JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)", line.upper())
                
                if match:
                    # Se avevamo già una data aperta, salviamo il testo accumulato
                    if current_date and buffer_text:
                        # Uniamo il testo e puliamo
                        descrizione = " ".join(buffer_text)
                        # Prendiamo solo la parte essenziale (titolo + letture)
                        # Spesso nel calendario c'è scritto "DOMINGO..."
                        liturgia_dict[current_date] = descrizione
                    
                    # Nuova data trovata
                    giorno, mese_nome = match.groups()
                    # Convertiamo mese nome in numero
                    mese_num = [k for k, v in nomi_mesi.items() if v == mese_nome][0]
                    
                    try:
                        current_date = datetime.date(2026, mese_num, int(giorno))
                        buffer_text = [line] # Iniziamo a salvare da questa riga (che contiene il titolo)
                    except:
                        current_date = None
                
                elif current_date:
                    # Se siamo dentro una data, continuiamo ad accumulare testo
                    # Fermiamoci se troviamo linee che sembrano numeri di pagina o spazzatura
                    if len(buffer_text) < 4: # Prendiamo max 3-4 righe di descrizione per non intasare
                        buffer_text.append(line)
            
            # Salva l'ultimo blocco
            if current_date and buffer_text:
                liturgia_dict[current_date] = " ".join(buffer_text)
                
    except Exception as e:
        st.warning(f"Non riesco a leggere il calendario liturgico: {e}")
        return {}

    return liturgia_dict

# Carichiamo la liturgia all'avvio
mappa_liturgica = carica_liturgia_da_pdf()

# --- CALCOLO DOMENICHE ---
domeniche_2026 = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    domeniche_2026.append(d)
    d += datetime.timedelta(days=7)

def safe_encode(text):
    if text == "nan" or text == "None": return ""
    # Rimuoviamo caratteri strani che rompono il PDF
    text = text.replace('–', '-').replace('“', '"').replace('”', '"')
    return text.encode('latin-1', 'replace').decode('latin-1')

def get_data_from_df(key):
    row = df_dati[df_dati['key_id'] == key]
    if not row.empty:
        c = row.iloc[0]['celebrante']
        n = row.iloc[0]['note']
        return (c if c != "nan" else "Selecionar..."), (n if n != "nan" else "")
    return "Selecionar...", ""

def update_google_sheet(key, celebrante, note):
    try:
        df_current = conn.read(worksheet="Foglio1", ttl=0)
        df_current = df_current.astype(str)
        if 'key_id' not in df_current.columns:
            df_current['key_id'] = ""; df_current['celebrante'] = ""; df_current['note'] = ""
        
        if key in df_current['key_id'].values:
            df_current.loc[df_current['key_id'] == key, 'celebrante'] = celebrante
            df_current.loc[df_current['key_id'] == key, 'note'] = note
        else:
            new_row = pd.DataFrame([{'key_id': key, 'celebrante': celebrante, 'note': note}]).astype(str)
            df_current = pd.concat([df_current, new_row], ignore_index=True)
            
        conn.update(worksheet="Foglio1", data=df_current)
        st.toast("Salvo! ✅")
    except:
        st.error("Errore salvataggio")

# --- PDF GENERATOR ---
def crea_pdf_mensile(mese_numero, nome_mese):
    df_print = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_encode(f"Escala de Missas - {nome_mese} 2026"), ln=True, align="C")
    pdf.ln(2)
    
    doms = [x for x in domeniche_2026 if x.month == mese_numero]
    
    def get_print(k):
        r = df_print[df_print['key_id'] == k]
        if not r.empty:
            c = r.iloc[0]['celebrante']; n = r.iloc[0]['note']
            return (c if c!="nan" else "Selecionar..."), (n if n!="nan" else "")
        return "Selecionar...", ""

    w_com = 45; w_ora = 15; w_cel = 55; w_not = 75

    for i, domenica in enumerate(doms):
        if i > 0 and i % 2 == 0:
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, safe_encode(f"Escala de Missas - {nome_mese} 2026"), ln=True, align="C")
            pdf.ln(5)
        elif i > 0:
            pdf.ln(8)

        # --- RECUPERO LITURGIA DAL DIZIONARIO ---
        # Cerchiamo se c'è testo per questa data
        testo_liturgia = mappa_liturgica.get(domenica, "")
        if testo_liturgia:
            # Puliamo un po' la stringa (togliamo la data iniziale che abbiamo già)
            # Esempio: "11 JANEIRO BATISMO..." -> "BATISMO..."
            pattern_data = f"{domenica.day} {nomi_mesi[domenica.month]}"
            testo_liturgia = testo_liturgia.replace(pattern_data, "").strip()
            # Tronchiamo se è troppo lungo per il titolo
            if len(testo_liturgia) > 130: testo_liturgia = testo_liturgia[:130] + "..."
            
            header_text = f"Dom, {domenica.day}/{domenica.month} - {testo_liturgia}"
        else:
            header_text = f"Domingo, {domenica.day} {nomi_mesi[domenica.month]}"

        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        # Multicell per gestire testi lunghi su più righe se la liturgia è lunga
        pdf.multi_cell(190, 6, safe_encode(header_text), 1, 'L', 1)
        
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(w_com, 6, "Comunidade", 1, 0, 'C', 1)
        pdf.cell(w_ora, 6, "Hora", 1, 0, 'C', 1)
        pdf.cell(w_cel, 6, "Celebrante", 1, 0, 'C', 1)
        pdf.cell(w_not, 6, "Notas", 1, 1, 'C', 1)
        
        pdf.set_font("Arial", size=9)
        
        for nome_comunita, orari in comunita_orari.items():
            if len(orari) == 2:
                x = pdf.get_x(); y = pdf.get_y(); h = 6
                pdf.cell(w_com, h*2, safe_encode(nome_comunita), 1, 0, 'L')
                x_split = pdf.get_x()
                
                k1 = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[0]}"
                c1, n1 = get_print(k1)
                if c1 == "Selecionar...": c1 = "---"
                pdf.cell(w_ora, h, orari[0], 1, 0, 'C')
                pdf.cell(w_cel, h, safe_encode(c1), 1, 0, 'L')
                pdf.cell(w_not, h, safe_encode(n1), 1, 1, 'L')
                
                pdf.set_xy(x_split, y + h)
                k2 = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[1]}"
                c2, n2 = get_print(k2)
                if c2 == "Selecionar...": c2 = "---"
                pdf.cell(w_ora, h, orari[1], 1, 0, 'C')
                pdf.cell(w_cel, h, safe_encode(c2), 1, 0, 'L')
                pdf.cell(w_not, h, safe_encode(n2), 1, 1, 'L')
            else:
                h = 6
                k = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[0]}"
                c, n = get_print(k)
                if c == "Selecionar...": c = "---"
                pdf.cell(w_com, h, safe_encode(nome_comunita), 1, 0, 'L')
                pdf.cell(w_ora, h, orari[0], 1, 0, 'C')
                pdf.cell(w_cel, h, safe_encode(c), 1, 0, 'L')
                pdf.cell(w_not, h, safe_encode(n), 1, 1, 'L')

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFACCIA ---
tabs = st.tabs(list(nomi_mesi.values()))

for i, mese_num in enumerate(nomi_mesi):
    with tabs[i]:
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button(f"📥 Baixar PDF {nomi_mesi[mese_num]}", key=f"p_{mese_num}"):
                d_pdf = crea_pdf_mensile(mese_num, nomi_mesi[mese_num])
                st.download_button("Salvar Arquivo", d_pdf, f"Messe_{nomi_mesi[mese_num]}.pdf", "application/pdf")
        st.write("---")
        
        doms = [x for x in domeniche_2026 if x.month == mese_num]
        for d in doms:
            # Recupero testo liturgia per l'interfaccia
            lit_text = mappa_liturgica.get(d, "")
            # Pulizia per visualizzazione web
            pattern_data = f"{d.day} {nomi_mesi[d.month]}"
            if lit_text:
                lit_text = lit_text.replace(pattern_data, "").strip()
                # Prendiamo solo la prima riga (il titolo) per l'interfaccia, per non ingombrare
                titolo_breve = lit_text.split('\n')[0]
                # Se c'è un trattino all'inizio, togliamolo
                if titolo_breve.startswith("-") or titolo_breve.startswith("–"): titolo_breve = titolo_breve[1:].strip()
                header_vis = f"Domingo, {d.day} {nomi_mesi[d.month]} | {titolo_breve}"
            else:
                header_vis = f"Domingo, {d.day} {nomi_mesi[d.month]}"

            with st.expander(f"📅 {header_vis}", expanded=True):
                # Se ci sono dati liturgici completi (letture), mostriamoli dentro l'expander come info
                if lit_text:
                    st.caption(f"📖 {lit_text}")

                cols = st.columns([2, 1, 2, 3])
                cols[0].markdown("**Comunidade**")
                cols[1].markdown("**Hora**")
                cols[2].markdown("**Celebrante**")
                cols[3].markdown("**Notas**")
                
                d_str = d.strftime("%d/%m/%Y")
                for com, orari in comunita_orari.items():
                    with st.container():
                        for idx, orario in enumerate(orari):
                            r = st.columns([2, 1, 2, 3])
                            if idx == 0: r[0].markdown(f"**{com}**")
                            else: r[0].markdown("↳")
                            r[1].write(orario)
                            
                            kid = f"{d_str}_{com}_{orario}"
                            cel_db, note_db = get_data_from_df(kid)
                            idx_cel = celebranti.index(cel_db) if cel_db in celebranti else 0
                            
                            def on_change_callback(k=kid):
                                nc = st.session_state[f"s_{k}"]; nn = st.session_state[f"n_{k}"]
                                update_google_sheet(k, nc, nn)
                            
                            r[2].selectbox("C", celebranti, key=f"s_{kid}", index=idx_cel, label_visibility="collapsed", on_change=on_change_callback)
                            r[3].text_input("N", key=f"n_{kid}", value=note_db, label_visibility="collapsed", on_change=on_change_callback)
                        st.write("")
