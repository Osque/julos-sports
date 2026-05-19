import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from docx import Document
from io import BytesIO
from datetime import datetime
import time

# Imports Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Générateur de Calendrier Sportif", layout="wide")

# --- DONNÉES PAR DÉFAUT (OFFICIELLES : FFR, FFF, FFHANDBALL) ---
DONNEES_INITIALES = {
    "Rugby": {
        "Stade Langonais (Nationale 2)": "https://monclubhouse.ffr.fr/clubs/stade-langonnais",
        "Salles (Nationale 2)": "https://monclubhouse.ffr.fr/clubs/us-salles",
        "Rugby Club Bassin D'Arcachon (Fédérale 1)": "https://monclubhouse.ffr.fr/clubs/rugby-club-bassin-d-arcachon",
        "Union Athletique Gujan Mestras (Fédérale 1)": "https://monclubhouse.ffr.fr/clubs/u-ath-gujan-mestras",
        "Floirac Rive Droite Rugby (Fédérale 1)": "https://monclubhouse.ffr.fr/clubs/club-municipal-de-floirac",
        "Saint Médard Rugby Club (Fédérale 1)": "https://monclubhouse.ffr.fr/clubs/st-medard-en-jalles-r-c",
        "US Bazas Rugby (Fédérale 2)": "https://monclubhouse.ffr.fr/clubs/us-bazadaise",
        "CA Lormont Rugby (Fédérale 2)": "https://monclubhouse.ffr.fr/clubs/c-a-lormont-hauts-de-garonne",
        "AS Mérignac Rugby (Fédérale 2)": "https://monclubhouse.ffr.fr/clubs/as-merignac-rugby",
        "US Castillonnaise (Fédérale 2)": "https://monclubhouse.ffr.fr/clubs/us-castillonnaise",
        "Stade Bordelais (Fédérale 2)": "https://monclubhouse.ffr.fr/clubs/stade-bordelais",
        "Les Lionnes Elite 1": "https://www.leslionnes-rugby.com/calendrier?team=elite"
    },
    "Football": {
        "FC BASSIN D'ARCACHON (N3)": "https://epreuves.fff.fr/competition/club/580598-f-c-bassin-d-arcachon",
        "US Lège Cap Ferret (N3)": "https://epreuves.fff.fr/competition/club/552060-lege-cap-ferret-us",
        "SA Gazinet Cestas (N3)": "https://www.fff.fr/competition/club/505963-s-a-gazinet-cestas/equipes.html",
        "Poule A (Régional 1)": "https://lfna.fff.fr/competitions" # Lien générique à remplacer par l'URL de la poule exacte FFF
    },
    "Handball": {
        "CA Béglais (D2 Féminine)": "https://www.ffhandball.fr/competitions/saison-2025-2026-21/national/d2-feminine-2025-26-28228/poule-187259/journee-3/",
        "Stade Pessacais UC (D2 Féminine)": "https://www.ffhandball.fr/competitions/saison-2025-2026-21/national/d2-feminine-2025-26-28228/poule-187259/journee-3/",
        "US Mios Biganos (N1 Féminine)": "https://www.ffhandball.fr/competitions/saison-2025-2026-21/national/nationale-1-feminine-2025-26-28626/poule-169734/journee-26/",
        "Mérignac Gironde HB (N1 Féminine)": "https://www.ffhandball.fr/competitions/saison-2025-2026-21/national/nationale-1-feminine-2025-26-28626/poule-169734/journee-26/"
    }
}

if 'base_clubs' not in st.session_state:
    st.session_state['base_clubs'] = DONNEES_INITIALES

# --- CONFIGURATION SELENIUM ANTI-CRASH ---
@st.cache_resource(show_spinner=False)
def initialiser_navigateur():
    """Configure Chromium pour éviter l'erreur 111 (Connection refused) sur les petits serveurs."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage') # Évite les crashs liés à la RAM partagée
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1280,720') # Plus petit = moins de RAM consommée
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        # Timeout très important pour ne pas bloquer le script indéfiniment
        driver.set_page_load_timeout(30)
        return driver
    except WebDriverException as e:
        st.error(f"Erreur technique du navigateur : {e}")
        return None

def obtenir_html_rendu(driver, url):
    try:
        driver.get(url)
        time.sleep(3) # Laisse le temps au site (FFF, FFR) de charger ses données
        return driver.page_source
    except Exception as e:
        return None

# --- MOTEUR D'EXTRACTION ---
def analyser_html(html, sport, nom_equipe, url):
    matchs_trouves = []
    if not html:
        return matchs_trouves
        
    soup = BeautifulSoup(html, 'html.parser')
    
    # Logique générique qui attrape les structures FFF, FFR et FFHandball
    # Souvent, les matchs sont listés dans des divs flex ou des tableaux
    
    lignes = soup.find_all(['tr', 'div', 'li'])
    
    for ligne in lignes:
        texte_complet = ligne.get_text(separator=' | ', strip=True)
        # On cherche des mots clés typiques d'un match (" - ", heures "15:00", ou dates)
        if " - " in texte_complet and (":" in texte_complet or "202" in texte_complet):
            # Filtre de longueur pour éviter de prendre tout le menu du site
            if 15 < len(texte_complet) < 200:
                matchs_trouves.append({
                    "Sport": sport,
                    "Équipe Suivie": nom_equipe,
                    "Date & Heure": "Donnée brute (Format fédération)",
                    "Rencontre": texte_complet,
                    "Source": url
                })

    if not matchs_trouves:
         matchs_trouves.append({
            "Sport": sport, "Équipe Suivie": nom_equipe,
            "Date & Heure": "-",
            "Rencontre": "Structure du calendrier vide ou en mise à jour", "Source": url
        })

    return matchs_trouves

# --- EXPORT WORD ---
def generer_document_word(donnees):
    doc = Document()
    doc.add_heading('Calendrier des Matchs', 0)
    
    if not donnees:
        doc.add_paragraph("Aucun match trouvé.")
    else:
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Sport / Équipe'
        hdr_cells[1].text = 'Période'
        hdr_cells[2].text = 'Détail de la rencontre (Équipes & Score)'
        hdr_cells[3].text = 'Lien source'
        
        for match in donnees:
            row_cells = table.add_row().cells
            row_cells[0].text = f"{match.get('Sport', '')} - {match.get('Équipe Suivie', '')}"
            row_cells[1].text = match.get('Date & Heure', '')
            row_cells[2].text = match.get('Rencontre', '')
            row_cells[3].text = match.get('Source', '')

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFACE UTILISATEUR ---
st.title("📅 Extracteur de Calendriers Officiels (FFF / FFR / FFHB)")

onglet_gen, onglet_gest = st.tabs(["📊 Extraction", "⚙️ Gestion des Équipes"])

with onglet_gen:
    st.markdown("Cochez les clubs que vous souhaitez analyser. Le robot naviguera sur les sites officiels.")
    
    equipes_selectionnees = []
    col_g, col_d = st.columns([1, 2])
    
    with col_g:
        for sport, equipes in st.session_state['base_clubs'].items():
            with st.expander(f"🏅 {sport}"):
                for nom_equipe, url in equipes.items():
                    if st.checkbox(nom_equipe, key=f"check_{sport}_{nom_equipe}"):
                        equipes_selectionnees.append({"Sport": sport, "Nom": nom_equipe, "URL": url})
        
        lancer = st.button("Lancer l'extraction", type="primary")

    with col_d:
        if lancer:
            if not equipes_selectionnees:
                st.warning("Veuillez cocher au moins une équipe.")
            else:
                with st.spinner("Lancement du navigateur sécurisé (peut prendre 1 minute)..."):
                    navigateur = initialiser_navigateur()
                    tous_les_matchs = []
                    
                    if navigateur:
                        barre = st.progress(0)
                        for i, eq in enumerate(equipes_selectionnees):
                            st.write(f"Récupération : {eq['Nom']}")
                            html_rendu = obtenir_html_rendu(navigateur, eq["URL"])
                            matchs_extraits = analyser_html(html_rendu, eq["Sport"], eq["Nom"], eq["URL"])
                            
                            # Nettoyage des doublons (fréquent sur les sites fédéraux)
                            matchs_uniques = [dict(t) for t in {tuple(d.items()) for d in matchs_extraits}]
                            tous_les_matchs.extend(matchs_uniques)
                            barre.progress((i + 1) / len(equipes_selectionnees))
                            
                        navigateur.quit()
                        
                        st.success("Terminé !")
                        df = pd.DataFrame(tous_les_matchs)
                        st.dataframe(df, use_container_width=True)
                        
                        fichier_word = generer_document_word(tous_les_matchs)
                        st.download_button("📄 Télécharger au format Word", data=fichier_word, file_name="calendrier.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    else:
                        st.error("Échec critique : Le serveur manque de ressources pour lancer Chrome. Essayez de redémarrer l'application sur Streamlit Cloud.")

with onglet_gest:
    col_ajout, col_visu = st.columns(2)
    with col_ajout:
        st.subheader("Ajouter un lien officiel")
        s = st.selectbox("Sport", ["Rugby", "Football", "Handball"])
        n = st.text_input("Nom du club")
        u = st.text_input("URL officielle (FFF, FFR...)")
        if st.button("Ajouter"):
            if n and u:
                st.session_state['base_clubs'][s][n] = u
                st.rerun()
                
    with col_visu:
        st.subheader("Base actuelle")
        for s, eq in st.session_state['base_clubs'].items():
            if eq:
                st.markdown(f"**{s}**")
                for n, u in list(eq.items()):
                    c1, c2 = st.columns([4, 1])
                    c1.write(n)
                    if c2.button("❌", key=f"del_{s}_{n}"):
                        del st.session_state['base_clubs'][s][n]
                        st.rerun()