import streamlit as st
import datetime
from fpdf import FPDF
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import io
import xlsxwriter

# --- CONFIGURAZIONE ---
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
celebranti_standard = [
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
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# --- 3. FUNZIONI DATABASE ---
def get_data_full(key):
    r = df_dati[df_dati['key_id'] == key]
    if not r.empty: 
        c = r.iloc[0]['celebrante']
        if c == "nan" or c == "": c = "Selecionar..."
        return c, \
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
        st.toast("✅ Salvo!")
    except: st.error("Errore salvataggio")

def safe_encode(text):
    if text == "nan" or text is None: return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- 4. GENERATORE EXCEL (MODIFICATO PER SCRITTURA LIBERA) ---
def genera_excel_annuale():
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws_data = workbook.add_worksheet("Dati_Ref")
    ws_data.hide()
    ws_data.write_column('A1', celebranti_standard)

    fmt_title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
    fmt_liturgia = workbook.add_format({'bold': True, 'bg_color': '#FFF2CC', 'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_color': '#9C5700'})
    fmt_date_merged = workbook.add_format({'bold': True, 'bg_color': '#E2EFDA', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
    fmt_com_merged = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
    fmt_normal = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
    fmt_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})

    for m_num in range(1, 13):
        m_nome = nomi_mesi[m_num]
        ws = workbook.add_worksheet(m_nome)
        ws.set_column('A:A', 18); ws.set_column('B:B', 30); ws.set_column('C:C', 10); ws.set_column('D:D', 30); ws.set_column('E:E', 40)
        ws.merge_range('A1:E1', f"ESCALA - {m_nome.upper()} 2026", fmt_title)
        headers = ["Data", "Comunidade", "Hora", "Celebrante", "Notas"]
        ws.write_row('A2', headers, fmt_header)
        
        row = 2
        d = datetime.date(2026, 1, 1)
        d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7)) 
        
        while d.year == 2026:
            if d.month == m_num:
                d_str = d.strftime("%d/%m/%Y")
                lit_key = f"LIT_{d_str}"
                r_lit = df_dati[df_dati['key_id'] == lit_key]
                lit_db = r_lit.iloc[0]['liturgia_custom'] if not r_lit.empty and r_lit.iloc[0]['liturgia_custom'] != "nan" else ""
                
                if lit_db:
                    ws.merge_range(row, 0, row, 4, f"LITURGIA: {lit_db}", fmt_liturgia)
                    row += 1
                
                tot_righe = sum(len(x) for x in comunita_orari.values())
                start_row = row
                nome_mese_bello = nomi_mesi[m_num]
                txt_data = f"Domingo\n{d.day} de {nome_mese_bello}"
                ws.merge_range(start_row, 0, start_row + tot_righe - 1, 0, txt_data, fmt_date_merged)
                
                current_r = start_row
                for com, orari in comunita_orari.items():
                    n_orari = len(orari)
                    if n_orari > 1:
                        ws.merge_range(current_r, 1, current_r + n_orari - 1, 1, com, fmt_com_merged)
                    else:
                        ws.write(current_r, 1, com, fmt_normal)
                    
                    for ora in orari:
                        kid = f"{d_str}_{com}_{ora}"
                        r_cel = df_dati[df_dati['key_id'] == kid]
                        cel_val = r_cel.iloc[0]['celebrante'] if not r_cel.empty and r_cel.iloc[0]['celebrante'] not in ["nan", "Selecionar..."] else ""
                        note_val = r_cel.iloc[0]['note'] if not r_cel.empty and r_cel.iloc[0]['note'] != "nan" else ""

                        ws.write(current_r, 2, ora, fmt_center)
                        
                        # --- CELEBRANTE ---
                        ws.write(current_r, 3, cel_val, fmt_normal)
                        
                        # QUESTA È LA MODIFICA MAGICA PER EXCEL:
                        # 'show_error': False -> Permette di scrivere qualsiasi cosa senza errore
                        ws.data_validation(current_r, 3, current_r, 3, {
                            'validate': 'list',
                            'source': f'=Dati_Ref!$A$1:$A${len(celebranti_standard)}',
                            'show_error': False 
                        })
                        
                        ws.write(current_r, 4, note_val, fmt_normal)
                        current_r += 1
                row = current_r + 1 
            d += datetime.timedelta(days=7)
    workbook.close()
    return output.getvalue()

# --- 5. GENERATORE PDF ---
def crea_pdf_mensile(m_num, m_nome):
    df_p = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    pdf = FPDF(); pdf.set_auto_page_break(False); pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_encode(f"Escala - {m_nome} 2026"), ln=True, align="C"); pdf.ln(2)
    
    doms = []
    d = datetime.date(2026, 1, 1)
    d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
    while d.year == 2026:
        if d.month == m_num: doms.append(d)
        d += datetime.timedelta(days=7)
    
    w_com, w_ora, w_cel, w_not = 45, 15, 55, 75
    
    for i, dom in enumerate(doms):
        if i > 0 and i % 2 == 0:
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, safe_encode(f"Escala - {m_nome} 2026"), ln=True, align="C"); pdf.ln(5)
        elif i > 0:
            pdf.ln(8)
        
        kl = f"LIT_{dom.strftime('%d/%m/%Y')}"; rl = df_p[df_p['key_id']==kl]
        tit_liturgia = rl.iloc[0]['liturgia_custom'] if not rl.empty and rl.iloc[0]['liturgia_custom']!="nan" else ""
        
        txt_data = f"Domingo, {dom.day} de {m_nome}"
        pdf.set_font("Arial", "B", 10); pdf.set_fill_color(200, 200, 200)
        pdf.cell(190, 7, safe_encode(txt_data), 1, 1, 'L', 1)
        
        txt_lit = f"LITURGIA: {tit_liturgia}" if tit_liturgia else "LITURGIA:"
        pdf.set_font("Arial", "B", 9); pdf.set_fill_color(255, 242, 204)
        pdf.cell(190, 6, safe_encode(txt_lit), 1, 1, 'L', 1)
        
        pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
        pdf.cell(w_com, 6, "Comunidade", 1, 0, 'C', 1); pdf.cell(w_ora, 6, "Hora", 1, 0, 'C', 1)
        pdf.cell(w_cel, 6, "Celebrante", 1, 0, 'C', 1); pdf.cell(w_not, 6, "Notas", 1, 1, 'C', 1)
        
        pdf.set_font("Arial", size=8)
        
        def gp(k):
            r = df_p[df_p['key_id']==k]
            if not r.empty: 
                c = r.iloc[0]['celebrante'] if r.iloc[0]['celebrante'] not in ["nan","Selecionar..."] else "---"
                n = r.iloc[0]['note'] if r.iloc[0]['note']!="nan" else ""
                return c, n
            return "---", ""
        
        for com, ors in comunita_orari.items():
            h = 6
            if len(ors) == 2:
                x_start = pdf.get_x(); y_start = pdf.get_y()
                pdf.cell(w_com, h*2, safe_encode(com), 1, 0, 'L')
                x_mid = pdf.get_x()
                c1, n1 = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[0]}")
                pdf.cell(w_ora, h, ors[0], 1, 0, 'C'); pdf.cell(w_cel, h, safe_encode(c1), 1, 0, 'L'); pdf.cell(w_not, h, safe_encode(n1), 1, 1, 'L')
                pdf.set_xy(x_mid, y_start + h)
                c2, n2 = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[1]}")
                pdf.cell(w_ora, h, ors[1], 1, 0, 'C'); pdf.cell(w_cel, h, safe_encode(c2), 1, 0, 'L'); pdf.cell(w_not, h, safe_encode(n2), 1, 1, 'L')
            else:
                c, n = gp(f"{dom.strftime('%d/%m/%Y')}_{com}_{ors[0]}")
                pdf.cell(w_com, h, safe_encode(com), 1, 0, 'L'); pdf.cell(w_ora, h, ors[0], 1, 0, 'C')
                pdf.cell(w_cel, h, safe_encode(c), 1, 0, 'L'); pdf.cell(w_not, h, safe_encode(n), 1, 1, 'L')
    return pdf.output(dest='S').encode('latin-1','replace')

# --- 6. INTERFACCIA UTENTE ---
with st.sidebar:
    st.image("https://www.vaticannews.va/content/dam/vaticannews/images/chiesa/vaticano/2018/06/05/1528189815591.jpg/_jcr_content/renditions/cq5dam.web.1280.1280.jpeg", width=100)
    st.title("Menu")
    m_sel = st.selectbox("Selecione o Mês:", list(nomi_mesi.values()))
    m_num = [k for k,v in nomi_mesi.items() if v==m_sel][0]
    
    st.divider()
    
    st.markdown("### 🛠️ Opções")
    modo_libero = st.checkbox("✍️ Ativar Escrita Livre", help="Marque para escrever nomes que não estão na lista")
    
    st.divider()
    if st.button("📥 Baixar Excel Completo 2026"):
        excel_data = genera_excel_annuale()
        st.download_button("Salvar no PC", excel_data, "Turni_Messe_2026_Completo.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.header(f"📅 Escala de {m_sel} 2026")
if st.button(f"📄 Baixar PDF de {m_sel}"):
    pdf_bytes = crea_pdf_mensile(m_num, m_sel)
    st.download_button("Salvar PDF", pdf_bytes, f"Messe_{m_sel}.pdf", "application/pdf")

st.divider()

doms_m = []
d = datetime.date(2026, 1, 1)
d += datetime.timedelta(days=(6 - d.weekday() if d.weekday() <= 6 else 7))
while d.year == 2026:
    if d.month == m_num: doms_m.append(d)
    d += datetime.timedelta(days=7)

for d in doms_m:
    d_fmt = d.strftime("%d/%m/%Y")
    kl = f"LIT_{d_fmt}"; _, _, lit_s = get_data_full(kl)
    tit = lit_s if lit_s else ""
    
    with st.expander(f"✨ Domingo, {d.day} de {m_sel} | {tit if tit else '(LITURGIA)'}", expanded=True):
        st.text_input(f"📖 Liturgia {d.day}/{m_sel}", value=tit, key=f"t_{kl}", on_change=lambda k=kl: update_db(k, "","",st.session_state[f"t_{k}"]))
        
        cols = st.columns([2,1,2,3]); cols[0].markdown("**Comunidade**"); cols[1].markdown("**Hora**"); cols[2].markdown("**Cel**"); cols[3].markdown("**Notas**")
        for com, ors in comunita_orari.items():
            for idx, ora in enumerate(ors):
                r = st.columns([2,1,2,3]); kid = f"{d_fmt}_{com}_{ora}"
                if idx==0: r[0].markdown(f"**{com}**")
                else: r[0].markdown("↳")
                r[1].write(ora)
                cel, note, _ = get_data_full(kid)
                
                if modo_libero:
                    r[2].text_input("C", value=cel, key=f"s_{kid}", label_visibility="collapsed", on_change=lambda k=kid: update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None))
                else:
                    opzioni_correnti = celebranti_standard.copy()
                    if cel not in opzioni_correnti: opzioni_correnti.append(cel)
                    idx_c = opzioni_correnti.index(cel)
                    r[2].selectbox("C", opzioni_correnti, index=idx_c, key=f"s_{kid}", label_visibility="collapsed", on_change=lambda k=kid: update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None))
                
                r[3].text_input("N", value=note, key=f"n_{kid}", label_visibility="collapsed", on_change=lambda k=kid: update_db(k, st.session_state[f"s_{k}"], st.session_state[f"n_{k}"], None))
            st.write("")
