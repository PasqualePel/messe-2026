import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")

# --- 1. CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_dati = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    for col in ['key_id', 'celebrante', 'note', 'liturgia_custom']:
        if col not in df_dati.columns:
            df_dati[col] = ""
except:
    st.error("Errore connessione Google Sheets. Verifica i Secrets.")
    st.stop()

# --- 2. DATI E STRUTTURE ---
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

# Nomi dei mesi in Portoghese (Mozambico)
nomi_mesi = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# --- 3. MENU A SINISTRA (SIDEBAR) ---
with st.sidebar:
    st.image("https://www.vaticannews.va/content/dam/vaticannews/images/chiesa/vaticano/2018/06/05/1528189815591.jpg/_jcr_content/renditions/cq5dam.web.1280.1280.jpeg", width=100)
    st.title("Menu Principal")
    # Selezione del mese: questo valore non cambia finché l'utente non lo tocca
    mese_selezionato_nome = st.selectbox("Selecione o Mês para trabalhar:", list(nomi_mesi.values()))
    mese_num = [k for k, v in nomi_mesi.items() if v == mese_selezionato_nome][0]
    
    st.divider()
    st.info("Os dados são salvos automaticamente ao alterar qualquer campo.")

# --- 4. FUNZIONI CORE ---
def get_data_full(key):
    r = df_dati[df_dati['key_id'] == key]
    if not r.empty: 
        return (r.iloc[0]['celebrante'] if r.iloc[0]['celebrante']!="nan" else "Selecionar..."), \
               (r.iloc[0]['note'] if r.iloc[0]['note']!="nan" else ""), \
               (r.iloc[0]['liturgia_custom'] if 'liturgia_custom' in df_dati.columns and r.iloc[0]['liturgia_custom']!="nan" else "")
    return "Selecionar...", "", ""

def update_db(key, cel, note, lit_custom=None):
    try:
        df = conn.read(worksheet="Foglio1", ttl=0).astype(str)
        if key in df['key_id'].values:
            df.loc[df['key_id']==key, 'celebrante'] = cel
            df.loc[df['key_id']==key, 'note'] = note
            if lit_custom is not None: df.loc[df['key_id']==key, 'liturgia_custom'] = lit_custom
        else:
            nr = pd.DataFrame([{'key_id':key,'celebrante':cel,'note':note,'liturgia_custom':lit_custom if lit_custom else ""}]).astype(str)
            df = pd.concat([df, nr], ignore_index=True)
        conn.update(worksheet="Foglio1", data=df)
        st.toast("✅ Salvo com sucesso!")
    except: st.error("Erro de salvamento")

# --- 5. GENERATORE PDF ---
def crea_pdf_mensile(m_num, m_nome):
    df_p = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page()
    pdf.set_font("Arial","B",16); pdf.cell(0,10,f"Escala - {m_nome} 2026".encode('latin-1','replace').decode('latin-1'),ln=True,align="C"); pdf.ln(2)
    
    # Calcolo domeniche del mese
    doms = []
    d = datetime.date(2026, 1, 1)
    d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
    while d.year == 2026:
        if d.month == m_num: doms.append(d)
        d += datetime.timedelta(days=7)
    
    w_com=45; w_ora=15; w_cel=55; w_not=75
    for i, dom in enumerate(doms):
        if i>0 and i%2==0: pdf.add_page(); pdf.set_font("Arial","B",16); pdf.cell(0,10,f"Escala - {m_nome} 2026".encode('latin-1','replace').decode('latin-1'),ln=True,align="C"); pdf.ln(5)
        elif i>0: pdf.ln(8)
        
        # Titolo liturgico
        kl = f"LIT_{dom.strftime('%d/%m/%Y')}"; rl = df_p[df_p['key_id']==kl]
        tit = rl.iloc[0]['liturgia_custom'] if not rl.empty and rl.iloc[0]['liturgia_custom']!="nan" else ""
        head = f"Domingo, {dom.day} de {m_nome}" + (f" - {tit}" if tit else "")
        
        pdf.set_font("Arial","B",10); pdf.set_fill_color(220,220,220)
        pdf.multi_cell(190, 6, head.encode('latin-1','replace').decode('latin-1'), 1, 'L', 1)
        
        pdf.set_font("Arial","B",8); pdf.set_fill_color(240,240,240)
        pdf.cell(w_com,6,"Comunidade",1,0,'C',1); pdf.cell(w_ora,6,"Hora",1,0,'C',1); pdf.cell(w_cel,6,"Celebrante",1,0,'C',1); pdf.cell(w_not,6,"Notas",1,1,'C',1)
        
        pdf.set_font("Arial",size=9)
        def gp(k):
            r = df_p[df_p['key_id']==k]
            if not r.empty: return (r.iloc[0]['celebrante'] if r.iloc[0]['celebrante'] not in ["nan","Selecionar..."] else "---"), (r.iloc[0]['note'] if r.iloc[0]['note']!="nan" else "")
            return "---", ""
        
        for com, ors in comunita_orari.items():
            if len(ors)==2:
                y_i = pdf.get_y(); pdf.cell(w_com, 12, com.encode('latin-1','replace').decode('latin-1'), 1, 0, 'L')
                xs = pdf.get_x(); c1,n1 = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[0]}")
                pdf.cell(w_ora,6,ors[0],1,0,'C'); pdf.cell(w_cel,6,c1.encode('latin-1','replace').decode('latin-1'),1,0,'L'); pdf.cell(w_not,6,n1.encode('latin-1','replace').decode('latin-1'),1,1,'L')
                pdf.set_xy(xs, y_i+6); c2,n2 = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[1]}")
                pdf.cell(w_ora,6,ors[1],1,0,'C'); pdf.cell(w_cel,6,c2.encode('latin-1','replace').decode('latin-1'),1,0,'L'); pdf.cell(w_not,6,n2.encode('latin-1','replace').decode('latin-1'),1,1,'L')
            else:
                c,n = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[0]}")
                pdf.cell(w_com,6,com.encode('latin-1','replace').decode('latin-1'),1,0,'L'); pdf.cell(w_ora,6,ors[0],1,0,'C')
                pdf.cell(w_cel,6,c.encode('latin-1','replace').decode('latin-1'),1,0,'L'); pdf.cell(w_not,6,n.encode('latin-1','replace').decode('latin-1'),1,1,'L')
    return pdf.output(dest='S').encode('latin-1','replace')

# --- 6. INTERFACCIA PRINCIPALE ---
st.header(f"📅 Escala de {mese_selezionato_nome}")

if st.button(f"📥 Baixar PDF de {mese_selezionato_nome}"):
    pdf_bytes = crea_pdf_mensile(mese_num, mese_selezionato_nome)
    st.download_button("Clique para Salvar", pdf_bytes, f"Messe_{mese_selezionato_nome}.pdf", "application/pdf")

st.divider()

# Calcolo domeniche per il mese selezionato
doms_m = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    if d.month == mese_num: doms_m.append(d)
    d += datetime.timedelta(days=7)

for d in doms_m:
    d_fmt = d.strftime("%d/%m/%Y")
    kl = f"LIT_{d_fmt}"; _, _, lit_s = get_data_full(kl)
    
    with st.expander(f"✨ Domingo, {d.day} de {mese_selezionato_nome} | {lit_s[:50] if lit_s else '(Sem Liturgia)'}", expanded=True):
        # Campo Liturgia
        new_lit = st.text_input(f"📖 Liturgia para {d.day} de {mese_selezionato_nome}", value=lit_s, key=f"t_{kl}", 
                                on_change=lambda k=kl: update_db(k, "", "", st.session_state[f"t_{k}"]))
        
        # Tabella Messe
        cols = st.columns([2,1,2,3])
        cols[0].markdown("**Comunidade**"); cols[1].markdown("**Hora**"); cols[2].markdown("**Cel**"); cols[3].markdown("**Notas**")
        
        for com, ors in comunita_orari.items():
            for idx, ora in enumerate(ors):
                r = st.columns([2,1,2,3]); kid = f"{d_fmt}_{com}_{ora}"
                if idx==0: r[0].markdown(f"**{com}**")
                else: r[0].markdown("↳")
                r[1].write(ora)
                cel, note, _ = get_data_full(kid)
                ic = celebranti.index(cel) if cel in celebranti else 0
                
                # Salvataggio celebrante/note
                r[2].selectbox("C", celebranti, index=ic, key=f"s_{kid}", label_visibility="collapsed", 
                               on_change=lambda k=kid: update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None))
                r[3].text_input("N", value=note, key=f"n_{kid}", label_visibility="collapsed", 
                                on_change=lambda k=kid: update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None))
            st.write("")
