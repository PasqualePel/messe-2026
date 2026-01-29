import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import pdfplumber
import re
import os

st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")
st.title("⛪ Gestão de Turnos de Missas - 2026 (Online)")

# --- 1. ISPETTORE FILE (SHERLOCK HOLMES) ---
# Questo pezzo ti dice esattamente cosa c'è nella cartella
with st.sidebar:
    st.header("📂 Controllo File")
    files_trovati = os.listdir(".")
    st.write("File presenti nel server:")
    st.code(files_trovati)
    
    if "calendario.pdf" in files_trovati:
        st.success("✅ 'calendario.pdf' TROVATO!")
    else:
        st.error("❌ 'calendario.pdf' NON TROVATO.")
        st.info("Rinomina il file su GitHub in: calendario.pdf (tutto minuscolo)")

# --- 2. CONNESSIONE DATI ---
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_dati = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    for col in ['key_id', 'celebrante', 'note', 'liturgia_custom']:
        if col not in df_dati.columns: df_dati[col] = ""
except:
    st.error("Errore connessione Google Sheets. Verifica i Secrets.")
    st.stop()

# --- 3. LETTURA PDF ---
@st.cache_data
def carica_liturgia():
    # Ora cerca SOLO il nome semplice
    path = "calendario.pdf"
    liturgia = {}
    
    if not os.path.exists(path): return {}

    try:
        with pdfplumber.open(path) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t: full_text += t + "\n"
            
            # Logica di lettura flessibile
            regex = r"(\d{1,2})\s*(?:DE|-|\/)?\s*(JANEIRO|FEVEREIRO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)"
            nomi_mesi_pdf = {"JANEIRO":1, "FEVEREIRO":2, "MARÇO":3, "ABRIL":4, "MAIO":5, "JUNHO":6, "JULHO":7, "AGOSTO":8, "SETEMBRO":9, "OUTUBRO":10, "NOVEMBRO":11, "DEZEMBRO":12}
            
            lines = full_text.split('\n')
            curr = None; buff = []
            
            for line in lines:
                l = line.strip().upper()
                if not l: continue
                m = re.search(regex, l)
                if m:
                    if curr and buff: liturgia[curr] = " ".join(buff)
                    g, mes_txt = m.groups()
                    try:
                        curr = datetime.date(2026, nomi_mesi_pdf[mes_txt], int(g))
                        clean = re.sub(regex, "", l).strip()
                        clean = re.sub(r"^[^A-Z0-9]+", "", clean)
                        buff = [clean]
                    except: pass
                elif curr and len(buff) < 5:
                    buff.append(line.strip())
            if curr and buff: liturgia[curr] = " ".join(buff)
    except: pass
    return liturgia

mappa_liturgica = carica_liturgia()

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
nomi_mesi = {1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"}
domeniche_2026 = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    domeniche_2026.append(d); d += datetime.timedelta(days=7)

def safe_encode(text):
    if text == "nan" or text is None: return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

def get_data_full(key):
    r = df_dati[df_dati['key_id'] == key]
    if not r.empty: 
        return (r.iloc[0]['celebrante'] if r.iloc[0]['celebrante']!="nan" else "Selecionar..."), (r.iloc[0]['note'] if r.iloc[0]['note']!="nan" else ""), (r.iloc[0]['liturgia_custom'] if 'liturgia_custom' in df_dati.columns and r.iloc[0]['liturgia_custom']!="nan" else "")
    return "Selecionar...", "", ""

def update_db(key, c, n, l=None):
    try:
        df = conn.read(worksheet="Foglio1", ttl=0).astype(str)
        if 'key_id' not in df.columns: 
            for x in ['key_id','celebrante','note','liturgia_custom']: df[x]=""
        if key in df['key_id'].values:
            df.loc[df['key_id']==key, 'celebrante'] = c; df.loc[df['key_id']==key, 'note'] = n
            if l is not None: df.loc[df['key_id']==key, 'liturgia_custom'] = l
        else:
            lv = l if l else ""
            nr = pd.DataFrame([{'key_id':key,'celebrante':c,'note':n,'liturgia_custom':lv}]).astype(str)
            df = pd.concat([df, nr], ignore_index=True)
        conn.update(worksheet="Foglio1", data=df); st.toast("✅")
    except: st.error("Errore salvataggio")

def crea_pdf_mensile(mese, nome_mese):
    df_p = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page()
    pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(2)
    doms = [x for x in domeniche_2026 if x.month == mese]
    w_com=45; w_ora=15; w_cel=55; w_not=75
    
    for i, dom in enumerate(doms):
        if i>0 and i%2==0: pdf.add_page(); pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(5)
        elif i>0: pdf.ln(8)
        
        kl = f"LIT_{dom.strftime('%d/%m/%Y')}"
        rl = df_p[df_p['key_id'] == kl]
        lm = rl.iloc[0]['liturgia_custom'] if not rl.empty and rl.iloc[0]['liturgia_custom']!="nan" else ""
        tit = lm if lm else mappa_liturgica.get(dom, "")
        tit = tit.replace("\n", " ")
        head = f"Dom, {dom.day}/{dom.month} - {tit}" if tit else f"Domingo, {dom.day} {nomi_mesi[dom.month].title()}"
        
        pdf.set_font("Arial","B",10); pdf.set_fill_color(220,220,220); pdf.multi_cell(190, 6, safe_encode(head), 1, 'L', 1)
        pdf.set_font("Arial","B",8); pdf.set_fill_color(240,240,240)
        pdf.cell(w_com,6,"Comunidade",1,0,'C',1); pdf.cell(w_ora,6,"Hora",1,0,'C',1); pdf.cell(w_cel,6,"Celebrante",1,0,'C',1); pdf.cell(w_not,6,"Notas",1,1,'C',1)
        pdf.set_font("Arial",size=9)
        def gp(k):
            r = df_p[df_p['key_id']==k]
            if not r.empty: return (r.iloc[0]['celebrante'] if r.iloc[0]['celebrante'] not in ["nan","Selecionar..."] else "---"), (r.iloc[0]['note'] if r.iloc[0]['note']!="nan" else "")
            return "---", ""
        for com, orari in comunita_orari.items():
            if len(orari)==2:
                x=pdf.get_x(); y=pdf.get_y(); h=6
                pdf.cell(w_com, h*2, safe_encode(com), 1,0,'L'); xs=pdf.get_x()
                c1,n1=gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[0]}")
                pdf.cell(w_ora,h,orari[0],1,0,'C'); pdf.cell(w_cel,h,safe_encode(c1),1,0,'L'); pdf.cell(w_not,h,safe_encode(n1),1,1,'L')
                pdf.set_xy(xs,y+h)
                c2,n2=gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[1]}")
                pdf.cell(w_ora,h,orari[1],1,0,'C'); pdf.cell(w_cel,h,safe_encode(c2),1,0,'L'); pdf.cell(w_not,h,safe_encode(n2),1,1,'L')
            else:
                h=6; c,n=gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{orari[0]}")
                pdf.cell(w_com,h,safe_encode(com),1,0,'L'); pdf.cell(w_ora,h,orari[0],1,0,'C'); pdf.cell(w_cel,h,safe_encode(c),1,0,'L'); pdf.cell(w_not,h,safe_encode(n),1,1,'L')
    return pdf.output(dest='S').encode('latin-1','replace')

tabs = st.tabs(list(nomi_mesi.values()))
for i, m_num in enumerate(nomi_mesi):
    with tabs[i]:
        if st.button(f"📥 Baixar PDF {nomi_mesi[m_num]}", key=f"b_{m_num}"):
            st.download_button("Salva PDF", crea_pdf_mensile(m_num,nomi_mesi[m_num]), f"Messe_{m_num}.pdf", "application/pdf")
        st.write("---")
        for d in [x for x in domeniche_2026 if x.month == m_num]:
            kl = f"LIT_{d.strftime('%d/%m/%Y')}"
            _,_,ls = get_data_full(kl)
            lp = mappa_liturgica.get(d, "")
            val_ed = ls if ls else lp
            tit_vis = val_ed[:50]+"..." if len(val_ed)>50 else val_ed
            if not tit_vis: tit_vis = "Liturgia non definita"
            
            with st.expander(f"📅 {d.day} {nomi_mesi[m_num].title()} | {tit_vis}", expanded=True):
                st.text_input("📖 Liturgia (Modificabile)", value=val_ed, key=f"txt_{kl}", on_change=lambda k=kl: update_db(k, "","",st.session_state[f"txt_{k}"]))
                cols = st.columns([2,1,2,3]); cols[0].markdown("**Comunidade**"); cols[1].markdown("**Hora**"); cols[2].markdown("**Cel**"); cols[3].markdown("**Notas**")
                d_str = d.strftime("%d/%m/%Y")
                for com, orari in comunita_orari.items():
                    with st.container():
                        for idx, ora in enumerate(orari):
                            r = st.columns([2,1,2,3])
                            if idx==0: r[0].markdown(f"**{com}**")
                            else: r[0].markdown("↳")
                            r[1].write(ora)
                            kid = f"{d_str}_{com}_{ora}"
                            cel, note, _ = get_data_full(kid)
                            def cb(k=kid): update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None)
                            ic = celebranti.index(cel) if cel in celebranti else 0
                            r[2].selectbox("C", celebranti, index=ic, key=f"s_{kid}", label_visibility="collapsed", on_change=cb)
                            r[3].text_input("N", value=note, key=f"n_{kid}", label_visibility="collapsed", on_change=cb)
                        st.write("")
