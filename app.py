import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from docx import Document
from io import BytesIO
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Extracteur Calendrier Sportif", layout="wide")

# --- MOTEUR D'EXTRACTION (Hybride : RugbyAmateur + Scan Textuel) ---
def extraire_donnees(url, nom_equipe):
    matchs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extraction spécifique RugbyAmateur (ra-card)
        cards = soup.find_all('div', class_='ra-card')
        for card in cards:
            date = card.find('div', class_='ra-day')
            date_str = date.get_text(strip=True) if date else "Date non trouvée"
            match_links = card.find_all('a', class_='ra-match')
            for match in match_links:
                dom = match.find('span', class_='ra-name-right')
                ext = match.find('span', class_='ra-name-left')
                heure = match.find('div', class_='ra-score')
                matchs.append({
                    "Équipe Suivie": nom_equipe,
                    "Date": date_str,
                    "Heure": heure.get_text(strip=True) if heure else "??:??",
                    "Rencontre": f"{dom.get_text(strip=True) if dom else '...'} vs {ext.get_text(strip=True) if ext else '...'}",
                    "Source": url
                })

        # 2. Extraction générique (pour les pages comme Les Lionnes)
        if not matchs:
            # On cherche tous les blocs pouvant contenir des infos de matchs
            for tag in soup.find_all(['p', 'div', 'tr', 'li']):
                text = tag.get_text(strip=True)
                # Heuristique : ligne contenant "vs" ou "-" avec des chiffres (date/heure)
                if len(text) > 20 and len(text) < 150 and ("vs" in text.lower() or " - " in text) and any(c.isdigit() for c in text):
                    matchs.append({
                        "Équipe Suivie": nom_equipe,
                        "Date": "Consulter source",
                        "Heure": "-",
                        "Rencontre": text,
                        "Source": url
                    })

    except Exception as e:
        return [{"Équipe Suivie": nom_equipe, "Rencontre": f"Erreur : {e}", "Date": "-", "Heure": "-", "Source": url}]
        
    # Retourne les résultats uniques
    return [dict(t) for t in {tuple(d.items()) for d in matchs}]

# --- INITIALISATION BASE ---
if 'clubs' not in st.session_state:
    st.session_state['clubs'] = [
        {"Nom": "Stade Langonnais (Nat 2)", "URL": "https://rugbyamateur.fr/club/stade-langonnais/calendrier/"},
        {"Nom": "Salles (Nat 2)", "URL": "https://rugbyamateur.fr/club/u-s-salles/calendrier/"},
        {"Nom": "RC Bassin Arcachon (Féd 1)", "URL": "https://rugbyamateur.fr/club/rugby-club-bassin-d-arcachon/calendrier/"},
        {"Nom": "UA Gujan Mestras (Féd 1)", "URL": "https://rugbyamateur.fr/club/u-ath-gujan-mestras/calendrier/"},
        {"Nom": "Floirac Rive Droite (Féd 1)", "URL": "https://rugbyamateur.fr/club/club-municipal-de-floirac/resultats/"},
        {"Nom": "St Médard Rugby (Féd 1)", "URL": "https://rugbyamateur.fr/club/st-medard-en-jalles-r-c/calendrier/"},
        {"Nom": "US Bazas (Féd 2)", "URL": "https://rugbyamateur.fr/club/u-s-bazadaise/calendrier/"},
        {"Nom": "CA Lormont (Féd 2)", "URL": "https://rugbyamateur.fr/club/c-a-lormont-hauts-de-garonne/calendrier/"},
        {"Nom": "AS Mérignac (Féd 2)", "URL": "https://rugbyamateur.fr/club/a-s-merignac-rugby/calendrier/"},
        {"Nom": "US Castillonnaise (Féd 2)", "URL": "https://rugbyamateur.fr/club/u-s-castillonnaise/calendrier/"},
        {"Nom": "Stade Bordelais (Féd 2)", "URL": "https://rugbyamateur.fr/club/stade-bordelais/calendrier/"},
        {"Nom": "Les Lionnes Elite 1", "URL": "https://www.leslionnes-rugby.com/calendrier?team=elite"}
    ]

# --- INTERFACE ---
st.title("🏉 Extracteur Calendrier Rugby")

selection = []
col_sel, col_res = st.columns([1, 2])

with col_sel:
    st.subheader("Cochez les clubs")
    for i, club in enumerate(st.session_state['clubs']):
        if st.checkbox(club['Nom'], key=f"check_{i}"):
            selection.append(club)

with col_res:
    if st.button("Lancer l'extraction", type="primary"):
        if not selection:
            st.warning("Sélectionnez au moins une équipe.")
        else:
            resultats = []
            with st.spinner("Analyse en cours..."):
                for s in selection:
                    resultats.extend(extraire_donnees(s['URL'], s['Nom']))
            
            if resultats:
                df = pd.DataFrame(resultats)
                st.dataframe(df, use_container_width=True)
                
                # Export Word
                doc = Document()
                doc.add_heading('Planning des matchs', 0)
                for r in resultats:
                    doc.add_paragraph(f"{r['Date']} - {r['Heure']} | {r['Rencontre']} | {r['Équipe Suivie']}")
                
                bio = BytesIO()
                doc.save(bio)
                st.download_button("💾 Télécharger le fichier Word", bio.getvalue(), "matchs_rugby.docx")
            else:
                st.error("Aucun match trouvé.")

# --- SECTION GESTION ---
with st.expander("⚙️ Gérer les clubs"):
    n_nom = st.text_input("Nom du club")
    n_url = st.text_input("URL calendrier")
    if st.button("Ajouter à la liste"):
        st.session_state['clubs'].append({"Nom": n_nom, "URL": n_url})
        st.rerun()