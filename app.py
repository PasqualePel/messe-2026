import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestão de Missas 2026", layout="wide")
st.title("⛪ Gestão de Turnos de Missas - 2026")

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
nomi_mesi = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

# --- MEMORIA DEL MESE ATTIVO ---
# Se non esiste ancora, impostiamo Gennaio come default
if 'mese_attivo_index' not in st.session_state:
    st.session_state['mese_attivo_index'] = 0

domeniche_2026 = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    domeniche_2026.append(d)
    d += datetime.timedelta(days=7)

def safe_encode(text):
    if text == "nan" or text == "None" or text is None: return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 3. FUNZIONI DATABASE ---
def get_data_full(key):
    r = df_dati[df_dati['key_id'] == key]
    if not r.empty: 
        c = r.iloc[0]['celebrante']
        n = r.iloc[0]['note']
        l = r.iloc[0]['liturgia_custom'] if 'liturgia_custom' in df_dati.columns else ""
        return (c if c!="nan" else "Selecionar..."), (n if n!="nan" else ""), (l if l!="nan" else "")
    return "Selecionar...", "", ""

def update_db(key, cel, note, lit_custom=None):
    try:
        df = conn.read(worksheet="Foglio1", ttl=0).astype(str)
        for col in ['key_id','celebrante','note','liturgia_custom']:
            if col not in df.columns: df[col] = ""
            
        if key in df['key_id'].values:
            df.loc[df['key_id']==key, 'celebrante'] = cel
            df.loc[df['key_id']==key, 'note'] = note
            if lit_custom is not None:
                df.loc[df['key_id']==key, 'liturgia_custom'] = lit_custom
        else:
            lit_val = lit_custom if lit_custom else ""
            nr = pd.DataFrame([{'key_id':key,'celebrante':cel,'note':note,'liturgia_custom':lit_val}]).astype(str)
            df = pd.concat([df, nr], ignore_index=True)
            
        conn.update(worksheet="Foglio1", data=df)
        st.toast("✅ Dados Salvos!")
    except: st.error("Errore salvataggio")

# --- 4. GENERATORE PDF ---
def crea_pdf_mensile(mese, nome_mese):
    df_print = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page()
    pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(2)
    doms = [x for x in domeniche_2026 if x.month == mese]
    w_com=45; w_ora=15; w_cel=55; w_not=75
    for i, dom in enumerate(doms):
        if i>0 and i%2==0: pdf.add_page(); pdf.set_font("Arial","B",16); pdf.cell(0,10,safe_encode(f"Escala - {nome_mese} 2026"),ln=True,align="C"); pdf.ln(5)
        elif i>0: pdf.ln(8)
        key_lit = f"LIT_{dom.strftime('%d/%m/%Y')}"
        row_lit = df_print[df_print['key_id'] == key_lit]
        lit_manuale = row_lit.iloc[0]['liturgia_custom'] if not row_lit.empty and row_lit.iloc[0]['liturgia_custom'] != "nan" else ""
        nome_mese_bello = nomi_mesi[dom.month].capitalize()
        data_estesa = f"Domingo, {dom.day} de {nome_mese_bello}"
        if lit_manuale:
            txt_header = f"{data_estesa} - {lit_manuale.replace(chr(10), ' ')}"
        else:
            txt_header = data_estesa
        pdf.set_font("Arial","B",10); pdf.set_fill_color(220,220,220)
        pdf.multi_cell(190, 6, safe_encode(txt_header), 1, 'L', 1)
        pdf.set_font("Arial","B",8); pdf.set_fill_color(240,240,240)
        pdf.cell(w_com,6,"Comunidade",1,0,'C',1); pdf.cell(w_ora,6,"Hora",1,0,'C',1); pdf.cell(w_cel,6,"Celebrante",1,0,'C',1); pdf.cell(w_not,6,"Notas",1,1,'C',1)
        pdf.set_font("Arial",size=9)
        def gp(k):
            r = df_print[df_print['key_id']==k]
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

# --- 5. INTERFACCIA WEB CON MEMORIA SCHEDA ---

# Funzione per cambiare il mese attivo
def set_active_tab():
    # Cerchiamo di capire quale tab è stata cliccata tramite i tasti o l'indice
    pass

# Mostriamo le schede dei mesi
nomi_lista = list(nomi_mesi.values())
tab_selezionata = st.tabs(nomi_lista)

for i, mese_num in enumerate(nomi_mesi):
    with tab_selezionata[i]:
        # Se entriamo in questa tab, aggiorniamo la memoria del mese attivo
        st.session_state['mese_attivo_index'] = i
        
        c1, c2 = st.columns([3, 1])
        with c2:
            if st.button(f"📥 Baixar PDF {nomi_mesi[mese_num]}", key=f"btn_{mese_num}"):
                d_pdf = crea_pdf_mensile(mese_num, nomi_mesi[mese_num])
                st.download_button("Salvar PDF", d_pdf, f"Messe_{nomi_mesi[mese_num]}.pdf", "application/pdf")
        st.write("---")
        
        doms = [x for x in domeniche_2026 if x.month == mese_num]
        for d in doms:
            key_lit = f"LIT_{d.strftime('%d/%m/%Y')}"
            _, _, lit_saved = get_data_full(key_lit)
            valore_editor = lit_saved if lit_saved else ""
            nome_mese_bello = nomi_mesi[mese_num].capitalize()
            data_portoghese = f"{d.day} de {nome_mese_bello}"
            titolo_visual = valore_editor[:60] + "..." if len(valore_editor)>60 else valore_editor
            if not titolo_visual: titolo_visual = "(Inserir Liturgia)"
            
            with st.expander(f"📅 {data_portoghese} | {titolo_visual}", expanded=True):
                # Callback speciale per la liturgia
                def cb_lit(k=key_lit):
                    update_db(k, "", "", st.session_state[f"txt_{k}"])

                st.text_input(f"📖 Liturgia para {data_portoghese}", 
                              value=valore_editor, 
                              key=f"txt_{key_lit}", 
                              on_change=cb_lit,
                              placeholder="Es: V Domingo do Tempo Comum...")

                cols = st.columns([2,1,2,3])
                cols[0].markdown("**Comunidade**"); cols[1].markdown("**Hora**"); cols[2].markdown("**Cel**"); cols[3].markdown("**Notas**")
                d_str = d.strftime("%d/%m/%Y")
                for com, orari in comunita_orari.items():
                    with st.container():
                        for idx, ora in enumerate(orari):
                            r = st.columns([2,1,2,3])
                            if idx == 0: r[0].markdown(f"**{com}**")
                            else: r[0].markdown("↳")
                            r[1].write(ora)
                            kid = f"{d_str}_{com}_{ora}"
                            cel, note, _ = get_data_full(kid)
                            
                            # Callback speciale per i celebranti
                            def cb(k=kid):
                                update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None)

                            ic = celebranti.index(cel) if cel in celebranti else 0
                            r[2].selectbox("C", celebranti, index=ic, key=f"s_{kid}", label_visibility="collapsed", on_change=cb)
                            r[3].text_input("N", value=note, key=f"n_{kid}", label_visibility="collapsed", on_change=cb)
                        st.write("")
