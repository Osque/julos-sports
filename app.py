import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from docx import Document
from io import BytesIO
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Extracteur Rugby", layout="wide")

# --- MOTEUR D'EXTRACTION OPTIMISÉ POUR RUGBYAMATEUR ---
def extraire_donnees(url, sport, nom_equipe):
    matchs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Sur RugbyAmateur.fr, les matchs sont souvent dans des éléments de classe 'match' ou des lignes de tableau
        # On récupère tous les blocs qui contiennent des dates et des noms d'équipes
        blocs = soup.find_all(['div', 'tr'])
        
        for bloc in blocs:
            text = bloc.get_text(separator=' ', strip=True)
            # Filtre : On cherche des lignes qui ressemblent à des matchs (présence de ' - ' ou ' vs ')
            if (' - ' in text or ' vs ' in text.lower()) and any(c.isdigit() for c in text):
                # On s'assure que la ligne n'est pas trop courte (menu) ou trop longue (texte générique)
                if 20 < len(text) < 160:
                    # Nettoyage des espaces multiples
                    clean_text = " ".join(text.split())
                    matchs.append({
                        "Équipe": nom_equipe,
                        "Match": clean_text,
                        "Source": url
                    })
    except Exception as e:
        return [{"Équipe": nom_equipe, "Match": f"Erreur : {e}", "Source": url}]
        
    # Retourne les 10 premiers matchs uniques
    return [dict(t) for t in {tuple(d.items()) for d in matchs}]

# --- INTERFACE ---
st.title("🏉 Extracteur Calendrier Rugby")

if 'clubs' not in st.session_state:
    st.session_state['clubs'] = [
        {"Nom": "Stade Langonnais (Nat 2)", "URL": "https://rugbyamateur.fr/club/stade-langonnais/calendrier/"},
        {"Nom": "Salles (Nat 2)", "URL": "https://app.scorenco.com/teams/49065"},
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

# Sélection
selection = []
for club in st.session_state['clubs']:
    if st.checkbox(club['Nom']):
        selection.append(club)

if st.button("Extraire le calendrier Rugby"):
    if not selection:
        st.warning("Sélectionnez au moins une équipe.")
    else:
        resultats = []
        for s in selection:
            resultats.extend(extraire_donnees(s['URL'], "Rugby", s['Nom']))
        
        if resultats:
            df = pd.DataFrame(resultats)
            st.table(df)
            
            # Export Word
            doc = Document()
            doc.add_heading('Calendrier Rugby', 0)
            for r in resultats:
                doc.add_paragraph(f"{r['Équipe']} : {r['Match']}")
            
            bio = BytesIO()
            doc.save(bio)
            st.download_button("Télécharger le fichier Word", bio.getvalue(), "calendrier_rugby.docx")
        else:
            st.error("Rien trouvé. Si le problème persiste, vérifiez l'URL dans l'onglet Gestion.")

st.sidebar.subheader("Gestion des clubs")
if st.sidebar.button("Réinitialiser liste"):
    del st.session_state['clubs']
    st.rerun()