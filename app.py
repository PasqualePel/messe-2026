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
    df_dati = conn.read(worksheet="Foglio1", ttl=0).astype(str)
except:
    st.error("Errore connessione Google Sheets.")
    st.stop()

# --- DATI ---
celebranti = [
    "Selecionar...", "Pe. Pasquale", "Pe. Márcio", "Pe. Stefano", "Pe. Roberto",
    "Pe. Antonio", "Pe. Massimo", "Pe. Pinto", "Pe José Angel",
    "Celebração Ir. Felicia", "Celebração Ir. Marilda", "Celebração", "Ninguém"
]
comunita_orari = {
    "Santa Monica": ["07:00", "09:00"], "São Francisco": ["07:00"], "São Miguel": ["07:00", "08:45"],
    "Santa Teresa C.": ["07:30"], "Santa Isabel": ["07:00"], "São João Batista": ["07:30"],
    "São Teodósio": ["07:30"], "Maria Auxiliadora": ["07:30"], "N.S Fátima": ["08:00"], "N.S Lurdes": ["07:30"]
}
nomi_mesi = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

# --- FUNZIONE ESTRAZIONE PDF POTENZIATA ---
@st.cache_data
def carica_liturgia_da_pdf():
    liturgia_dict = {}
    debug_text = "" # Variabile per vedere cosa legge
    
    # Nomi file possibili
    files = ["calendario-liturgico-2026-definitivo.pdf", "calendario_2026.pdf"]
    path = next((f for f in files if os.path.exists(f)), None)
    
    if not path:
        return {}, "FILE NON TROVATO. Carica 'calendario-liturgico-2026-definitivo.pdf' su GitHub!"

    try:
        with pdfplumber.open(path) as pdf:
            full_text = ""
            for i, page in enumerate(pdf.pages):
                extracted = page.extract_text()
                if extracted:
                    full_text += extracted + "\n"
                    if i == 0: debug_text = extracted[:1000] # Prendiamo l'inizio per debug
            
            lines = full_text.split('\n')
            current_date = None
            buffer = []
            
            # NUOVA REGEX POTENTE:
            # 1. Cerca numeri (1 o 2 cifre)
            # 2. Ignora "DE" opzionale o simboli
            # 3. Cerca il mese
            regex = r"(\d{1,2})\s*(?:DE|-|\/)?\s*(JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)"
            
            for line in lines:
                line_clean = line.strip().upper()
                if not line_clean: continue
                
                match = re.search(regex, line_clean)
                
                if match:
                    # Salva precedente
                    if current_date and buffer:
                        liturgia_dict[current_date] = " ".join(buffer)
                    
                    # Nuova data
                    g, m = match.groups()
                    mese_num = [k for k, v in nomi_mesi.items() if v == m][0]
                    try:
                        current_date = datetime.date(2026, mese_num, int(g))
                        # Rimuoviamo la data dal testo per pulire il titolo
                        # Es: "11 JANEIRO BATTESIMO" -> "BATTESIMO"
                        clean_title = re.sub(regex, "", line_clean).strip()
                        # Rimuoviamo caratteri non alfabetici all'inizio (es "-")
                        clean_title = re.sub(r"^[^A-Z0-9]+", "", clean_title)
                        buffer = [clean_title]
                    except:
                        current_date = None
                elif current_date:
                    if len(buffer) < 6: # Prendiamo un po' più righe
                        buffer.append(line.strip())
            
            if current_date and buffer:
                liturgia_dict[current_date] = " ".join(buffer)
                
    except Exception as e:
        return {}, f"Errore lettura: {e}"

    return liturgia_dict, debug_text

mappa_liturgica, testo_di_prova = carica_liturgia_da_pdf()

# --- SIDEBAR DIAGNOSTICA ---
with st.sidebar:
    st.header("🔧 Diagnostica PDF")
    st.info(f"Date trovate: {len(mappa_liturgica)}")
    
    if st.checkbox("Mostra testo grezzo PDF"):
        st.text_area("Cosa vede il computer (Prime righe):", value=testo_di_prova, height=300)
        st.write("---")
        st.write("Esempio dati estratti:")
        st.write(list(mappa_liturgica.items())[:3])

# --- LOGICA CALENDARIO ---
domeniche_2026 = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    domeniche_2026.append(d)
    d += datetime.timedelta(days=7)

def safe_encode(text):
    if text == "nan" or text == "None": return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

def get_data_from_df(key):
    r = df_dati[df_dati['key_id'] == key]
    if not r.empty: return r.iloc[0]['celebrante'], r.iloc[0]['note']
    return "Selecionar...", ""

def update_google_sheet(key, c, n):
    try:
        df = conn.read(worksheet="Foglio1", ttl=0).astype(str)
        if 'key_id' not in df.columns: df['key_id']=""; df['celebrante']=""; df['note']=""
        
        if key in df['key_id'].values:
            df.loc[df['key_id']==key, 'celebrante'] = c
            df.loc[df['key_id']==key, 'note'] = n
        else:
            nr = pd.DataFrame([{'key_id':key,'celebrante':c,'note':n}]).astype(str)
            df = pd.concat([df, nr], ignore_index=True)
        conn.update(worksheet="Foglio1", data=df); st.toast("✅")
    except: st.error("Errore salvataggio")

# --- PDF ---
def crea_pdf_mensile(mese, nome_mese):
    df_print = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page()
    pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(2)
    
    doms = [x for x in domeniche_2026 if x.month == mese]
    w_com=45; w_ora=15; w_cel=55; w_not=75
    
    for i, dom in enumerate(doms):
        if i>0 and i%2==0: pdf.add_page(); pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(5)
        elif i>0: pdf.ln(8)
        
        # Intestazione Liturgica
        lit = mappa_liturgica.get(dom, "")
        if lit: 
            # Pulizia per il PDF: Taglia se troppo lungo
            lit_clean = lit.replace("\n", " ")
            txt = f"Dom, {dom.day}/{dom.month} - {lit_clean}"
        else: txt = f"Domingo, {dom.day} {nomi_mesi[dom.month]}"
        
        pdf.set_font("Arial","B",10); pdf.set_fill_color(220,220,220)
        pdf.multi_cell(190, 6, safe_encode(txt), 1, 'L', 1)
        
        # Intestazioni Tabella
        pdf.set_font("Arial","B",8); pdf.set_fill_color(240,240,240)
        pdf.cell(w_com,6,"Comunidade",1,0,'C',1); pdf.cell(w_ora,6,"Hora",1,0,'C',1)
        pdf.cell(w_cel,6,"Celebrante",1,0,'C',1); pdf.cell(w_not,6,"Notas",1,1,'C',1)
        
        pdf.set_font("Arial",size=9)
        for com, orari in comunita_orari.items():
            if len(orari)==2:
                x=pdf.get_x(); y=pdf.get_y(); h=6
                pdf.cell(w_com, h*2, safe_encode(com), 1,0,'L')
                xs=pdf.get_x()
                # Riga 1
                r = df_print[df_print['key_id']==f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[0]}"]
                c1 = r.iloc[0]['celebrante'] if not r.empty else "---"; c1 = "---" if c1=="Selecionar..." else c1
                n1 = r.iloc[0]['note'] if not r.empty else ""
                pdf.cell(w_ora,h,orari[0],1,0,'C'); pdf.cell(w_cel,h,safe_encode(c1),1,0,'L'); pdf.cell(w_not,h,safe_encode(n1),1,1,'L')
                # Riga 2
                pdf.set_xy(xs, y+h)
                r = df_print[df_print['key_id']==f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[1]}"]
                c2 = r.iloc[0]['celebrante'] if not r.empty else "---"; c2 = "---" if c2=="Selecionar..." else c2
                n2 = r.iloc[0]['note'] if not r.empty else ""
                pdf.cell(w_ora,h,orari[1],1,0,'C'); pdf.cell(w_cel,h,safe_encode(c2),1,0,'L'); pdf.cell(w_not,h,safe_encode(n2),1,1,'L')
            else:
                h=6
                r = df_print[df_print['key_id']==f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[0]}"]
                c = r.iloc[0]['celebrante'] if not r.empty else "---"; c = "---" if c=="Selecionar..." else c
                n = r.iloc[0]['note'] if not r.empty else ""
                pdf.cell(w_com,h,safe_encode(com),1,0,'L'); pdf.cell(w_ora,h,orari[0],1,0,'C')
                pdf.cell(w_cel,h,safe_encode(c),1,0,'L'); pdf.cell(w_not,h,safe_encode(n),1,1,'L')
    return pdf.output(dest='S').encode('latin-1','replace')

# --- INTERFACCIA ---
tabs = st.tabs(list(nomi_mesi.values()))
for i, m_num in enumerate(nomi_mesi):
    with tabs[i]:
        if st.button(f"📥 Baixar PDF {nomi_mesi[m_num]}", key=f"d_{m_num}"):
            st.download_button("Salva", crea_pdf_mensile(m_num,nomi_mesi[m_num]), f"Messe_{m_num}.pdf", "application/pdf")
        st.write("---")
        for d in [x for x in domeniche_2026 if x.month == m_num]:
            lit = mappa_liturgica.get(d, "")
            # Puliamo per l'intestazione web (solo prima riga)
            short_lit = lit.split('\n')[0][:80] + "..." if len(lit)>80 else lit.split('\n')[0]
            if not short_lit: short_lit = ""
            
            with st.expander(f"📅 {d.day}/{d.month} {short_lit}", expanded=True):
                if lit: st.info(lit)
                cols = st.columns([2,1,2,3])
                cols[0].markdown("**Comunidade**"); cols[1].markdown("**Hora**"); cols[2].markdown("**Cel**"); cols[3].markdown("**Notas**")
                
                d_str = d.strftime("%d/%m/%Y")
                for com, orari in comunita_orari.items():
                    with st.container():
                        for idx, ora in enumerate(orari):
                            r = st.columns([2,1,2,3])
                            if idx==0: r[0].markdown(f"**{com}**")
                            else: r[0].markdown("↳")
                            r[1].write(ora)
                            kid = f"{d_str}_{com}_{ora}"
                            cel, note = get_data_from_df(kid)
                            
                            def cb(k=kid): update_google_sheet(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"])
                            ic = celebranti.index(cel) if cel in celebranti else 0
                            r[2].selectbox("C", celebranti, index=ic, key=f"s_{kid}", label_visibility="collapsed", on_change=cb)
                            r[3].text_input("N", value=note, key=f"n_{kid}", label_visibility="collapsed", on_change=cb)
                        st.write("")
