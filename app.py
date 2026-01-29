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

try:
    df_dati = conn.read(worksheet="Foglio1", ttl=0)
    df_dati = df_dati.astype(str)
except Exception as e:
    st.error(f"Errore di connessione. Verifica i Secrets. Errore: {e}")
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

# Nomi mesi per la visualizzazione
nomi_mesi = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
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
            df_current['key_id'] = ""
            df_current['celebrante'] = ""
            df_current['note'] = ""

        if key in df_current['key_id'].values:
            df_current.loc[df_current['key_id'] == key, 'celebrante'] = celebrante
            df_current.loc[df_current['key_id'] == key, 'note'] = note
        else:
            new_row = pd.DataFrame([{'key_id': key, 'celebrante': celebrante, 'note': note}])
            new_row = new_row.astype(str)
            df_current = pd.concat([df_current, new_row], ignore_index=True)
            
        conn.update(worksheet="Foglio1", data=df_current)
        st.toast("Salvo! ✅")
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")

# --- PDF MODIFICATO (Data Intestazione) ---
def crea_pdf_mensile(mese_numero, nome_mese):
    df_print = conn.read(worksheet="Foglio1", ttl=0).astype(str)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Titolo PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_encode(f"Escala de Missas - {nome_mese} 2026"), ln=True, align="C")
    pdf.ln(5)
    
    domeniche_del_mese = [x for x in domeniche_2026 if x.month == mese_numero]
    
    def get_print(k):
        r = df_print[df_print['key_id'] == k]
        if not r.empty:
            c = r.iloc[0]['celebrante']
            n = r.iloc[0]['note']
            return (c if c!="nan" else "Selecionar..."), (n if n!="nan" else "")
        return "Selecionar...", ""

    for domenica in domeniche_del_mese:
        # --- INTESTAZIONE DATA (Barra Grigia) ---
        # Formato: "Domingo, 1 Fevereiro"
        data_header = f"Domingo, {domenica.day} {nomi_mesi[domenica.month]}"
        
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(200, 200, 200) # Grigio scuro per la data
        # Larghezza totale pagina ~190. Scriviamo la data come un titolo di sezione
        pdf.cell(190, 8, safe_encode(data_header), 1, 1, 'L', 1)
        
        # --- INTESTAZIONE COLONNE (Sotto la data) ---
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(240, 240, 240) # Grigio chiaro per le colonne
        # NOTA: Abbiamo tolto la colonna DATA. Allarghiamo le altre.
        # Larghezze nuove: Comunità(60), Ora(20), Celebrante(60), Note(50) = 190 Totale
        pdf.cell(60, 6, "Comunidade", 1, 0, 'C', 1)
        pdf.cell(20, 6, "Hora", 1, 0, 'C', 1)
        pdf.cell(60, 6, "Celebrante", 1, 0, 'C', 1)
        pdf.cell(50, 6, "Notas", 1, 1, 'C', 1)
        
        pdf.set_font("Arial", size=10)
        
        # --- RIGHE DELLA TABELLA ---
        for nome_comunita, orari in comunita_orari.items():
            
            # CASO A: Celle Unite (Santa Monica / Sao Miguel)
            if len(orari) == 2:
                # Coordinate iniziali
                x = pdf.get_x()
                y = pdf.get_y()
                h = 7 # Altezza riga
                
                # 1. Disegna Comunità (Alta doppio: h*2)
                pdf.cell(60, h*2, safe_encode(nome_comunita), 1, 0, 'L')
                
                # Salviamo dove inizia la colonna orari
                x_split = pdf.get_x()
                
                # Riga 1 (Primo orario)
                k1 = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[0]}"
                c1, n1 = get_print(k1)
                if c1 == "Selecionar...": c1 = "---"
                
                pdf.cell(20, h, orari[0], 1, 0, 'C')
                pdf.cell(60, h, safe_encode(c1), 1, 0, 'L')
                pdf.cell(50, h, safe_encode(n1), 1, 1, 'L')
                
                # Riga 2 (Secondo orario)
                # Spostiamo il cursore sotto la riga 1, ma a destra della comunità
                pdf.set_xy(x_split, y + h)
                
                k2 = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[1]}"
                c2, n2 = get_print(k2)
                if c2 == "Selecionar...": c2 = "---"
                
                pdf.cell(20, h, orari[1], 1, 0, 'C')
                pdf.cell(60, h, safe_encode(c2), 1, 0, 'L')
                pdf.cell(50, h, safe_encode(n2), 1, 1, 'L') # Va a capo
                
            # CASO B: Riga Normale
            else:
                k = f"{domenica.strftime('%d/%m/%Y')}_{nome_comunita}_{orari[0]}"
                c, n = get_print(k)
                if c == "Selecionar...": c = "---"
                
                pdf.cell(60, 7, safe_encode(nome_comunita), 1, 0, 'L')
                pdf.cell(20, 7, orari[0], 1, 0, 'C')
                pdf.cell(60, 7, safe_encode(c), 1, 0, 'L')
                pdf.cell(50, 7, safe_encode(n), 1, 1, 'L')

        # Spazio vuoto tra le domeniche
        pdf.ln(5)

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
            d_str = d.strftime("%d/%m/%Y")
            
            # Intestazione Data in stile portoghese anche nell'interfaccia
            data_header_visual = f"{d.day} {nomi_mesi[d.month]}"
            
            with st.expander(f"📅 Domingo, {data_header_visual}", expanded=True):
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
                            
                            kid = f"{d_str}_{com}_{orario}"
                            cel_db, note_db = get_data_from_df(kid)
                            
                            idx_cel = celebranti.index(cel_db) if cel_db in celebranti else 0
                            
                            def on_change_callback(k=kid):
                                nc = st.session_state[f"s_{k}"]
                                nn = st.session_state[f"n_{k}"]
                                update_google_sheet(k, nc, nn)
                            
                            r[2].selectbox("C", celebranti, key=f"s_{kid}", index=idx_cel, label_visibility="collapsed", on_change=on_change_callback)
                            r[3].text_input("N", key=f"n_{kid}", value=note_db, label_visibility="collapsed", on_change=on_change_callback)
                        st.write("")
