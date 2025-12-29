"""
🎯 L'ATELIER DE VINCENT - Application de Gestion CA
Application web créée avec Streamlit pour remplacer votre Excel

Auteur : Vincent
Date : Décembre 2024
"""

# ==================== IMPORTS ====================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import calendar
import locale
import time
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from io import BytesIO

# Configuration du locale français (avec gestion d'erreur pour Streamlit Cloud)
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "French_France.1252")
        except locale.Error:
            pass

# ==================== CONFIGURATION ====================

st.set_page_config(
    page_title="L'Atelier de Vincent",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration PWA
st.markdown("""
    <head>
        <meta name="application-name" content="L'Atelier de Vincent">
        <meta name="apple-mobile-web-app-title" content="Atelier Vincent">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="theme-color" content="#A89332">
        <link rel="apple-touch-icon" href="assets/logo.png">
        <link rel="icon" type="image/png" sizes="192x192" href="assets/logo.png">
        <link rel="manifest" href="data:application/json;base64,ewogICJuYW1lIjogIkwnQXRlbGllciBkZSBWaW5jZW50IiwKICAic2hvcnRfbmFtZSI6ICJBdGVsaWVyIFZpbmNlbnQiLAogICJkZXNjcmlwdGlvbiI6ICJHZXN0aW9uIENBIHBvdXIgTCdBdGVsaWVyIGRlIFZpbmNlbnQiLAogICJzdGFydF91cmwiOiAiLyIsCiAgImRpc3BsYXkiOiAic3RhbmRhbG9uZSIsCiAgImJhY2tncm91bmRfY29sb3IiOiAiI0Y1RjVGMCIsCiAgInRoZW1lX2NvbG9yIjogIiNBODkzMzIiLAogICJpY29ucyI6IFsKICAgIHsKICAgICAgInNyYyI6ICJhc3NldHMvbG9nby5wbmciLAogICAgICAic2l6ZXMiOiAiNTEyeDUxMiIsCiAgICAgICJ0eXBlIjogImltYWdlL3BuZyIKICAgIH0KICBdCn0=">
    </head>
""", unsafe_allow_html=True)

# ==================== PROTECTION PAR MOT DE PASSE ====================

def verifier_mot_de_passe():
    """Retourne True si le mot de passe est correct."""
    
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 L'Atelier de Vincent")
    st.markdown("### Veuillez vous connecter pour accéder à l'application")
    
    password = st.text_input(
        "Mot de passe", 
        type="password",
        placeholder="Entrez le mot de passe"
    )
    
    if st.button("Se connecter", use_container_width=True):
        if password == "3108":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Mot de passe incorrect. Réessayez.")
    
    return False

# ==================== FONCTIONS UTILES ====================

@st.cache_data
def charger_donnees(fichier_excel):
    """Charge les données depuis votre fichier Excel"""
    try:
        df = pd.read_excel(fichier_excel, sheet_name="Données")
        
        df['date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['montant'] = pd.to_numeric(df['Valeur'], errors='coerce')
        df['nb_collaborateurs'] = pd.to_numeric(df['Nb_Collaborateurs'], errors='coerce').fillna(0).astype(int)
        
        df = df.dropna(subset=['date', 'montant'])
        df = df[['date', 'montant', 'nb_collaborateurs']].copy()
        
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        return None

def calculer_exercice(date):
    """Calcule l'exercice fiscal (juillet à juin)"""
    if date.month >= 7:
        return f"{date.year}/{date.year + 1}"
    else:
        return f"{date.year - 1}/{date.year}"

def formater_euro(montant):
    """Formate un nombre en euros français"""
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")

def generer_pdf_suivi(donnees_tableau, mois_selectionne, annee_mois_n, annee_mois_n_moins_1, total_n, total_n_moins_1, evolution_euro, evolution_pct):
    """Génère un PDF du tableau de suivi mensuel optimisé pour tenir sur une page A4 portrait"""
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.8*cm,
        leftMargin=0.8*cm,
        topMargin=1.5*cm,
        bottomMargin=0.8*cm
    )
    
    elements = []
    
    try:
        logo_path = "assets/logo_noir.png"
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.2*cm))
    except:
        pass
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    title_text = f"Suivi Mensuel - {mois_selectionne} {annee_mois_n} vs {mois_selectionne} {annee_mois_n_moins_1}"
    title = Paragraph(title_text, title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*cm))
    
    table_data = [['Jour', 'Date N-1', 'Date N', 'Montant N-1', 'Nb C. N-1', 'Montant N', 'Nb C. N']]
    
    for row in donnees_tableau:
        table_data.append([
            row['Jour'][:3],
            row['Date N-1'],
            row['Date N'],
            row['Montant N-1'],
            row['Nb Collab N-1'],
            row['Montant N'],
            row['Nb Collab N']
        ])
    
    col_widths = [1.5*cm, 2.2*cm, 2.2*cm, 2.8*cm, 1.4*cm, 2.8*cm, 1.4*cm]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*cm))
    
    totaux_data = [
        ['', f'{mois_selectionne} {annee_mois_n_moins_1}', f'{mois_selectionne} {annee_mois_n}', 'Évolution €', 'Évolution %'],
        ['Total', formater_euro(total_n_moins_1), formater_euro(total_n), formater_euro(evolution_euro), f"{evolution_pct:+.1f}%"]
    ]
    
    totaux_table = Table(totaux_data, colWidths=[3*cm, 3.5*cm, 3.5*cm, 3*cm, 2.5*cm])
    totaux_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
    ]))
    
    elements.append(totaux_table)
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer

def calculer_resume_mensuel(df):
    """Calcule le résumé mensuel pour tous les exercices disponibles"""
    
    # Ajouter une colonne exercice et mois
    df['exercice'] = df['date'].apply(calculer_exercice)
    df['mois_num'] = df['date'].dt.month
    df['annee'] = df['date'].dt.year
    
    # Mapper les numéros de mois aux noms
    mois_noms = {
        7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 
        11: 'Novembre', 12: 'Décembre', 1: 'Janvier', 2: 'Février', 
        3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin'
    }
    
    # Grouper par exercice et mois
    resume = df.groupby(['exercice', 'mois_num']).agg({
        'montant': 'sum'
    }).reset_index()
    
    resume['mois'] = resume['mois_num'].map(mois_noms)
    
    # Pivot pour avoir les exercices en colonnes
    pivot = resume.pivot(index='mois_num', columns='exercice', values='montant').fillna(0)
    
    # Réordonner les mois (juillet à juin)
    ordre_mois = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
    pivot = pivot.reindex(ordre_mois)
    
    # Ajouter la colonne mois
    pivot.insert(0, 'Mois', [mois_noms[m] for m in ordre_mois])
    
    # Calculer les évolutions si on a au moins 2 exercices
    if len(pivot.columns) >= 3:  # Mois + au moins 2 exercices
        exercices = [col for col in pivot.columns if col != 'Mois']
        if len(exercices) >= 2:
            ex_actuel = exercices[-1]
            ex_precedent = exercices[-2]
            
            pivot['Évol €'] = pivot[ex_actuel] - pivot[ex_precedent]
            pivot['Évol %'] = ((pivot[ex_actuel] - pivot[ex_precedent]) / pivot[ex_precedent] * 100).round(1)
            pivot['Évol %'] = pivot['Évol %'].replace([float('inf'), -float('inf')], 0)
    
    return pivot

def calculer_ca_par_jour_semaine(df):
    """Calcule le CA par jour de la semaine pour chaque exercice"""
    
    # Ajouter les colonnes nécessaires
    df['exercice'] = df['date'].apply(calculer_exercice)
    df['jour_semaine'] = df['date'].dt.dayofweek  # 0 = Lundi, 6 = Dimanche
    
    # Noms des jours en français
    jours_fr = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 
                4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
    
    # Grouper par exercice et jour de la semaine
    ca_par_jour = df.groupby(['exercice', 'jour_semaine']).agg({
        'montant': 'sum',
        'date': 'count'  # Nombre de jours travaillés
    }).reset_index()
    
    ca_par_jour.columns = ['exercice', 'jour_semaine', 'ca_total', 'nb_jours']
    ca_par_jour['ca_moyen'] = ca_par_jour['ca_total'] / ca_par_jour['nb_jours']
    ca_par_jour['jour'] = ca_par_jour['jour_semaine'].map(jours_fr)
    
    # Pivot pour avoir les exercices en colonnes
    pivot_total = ca_par_jour.pivot(index='jour_semaine', columns='exercice', values='ca_total').fillna(0)
    pivot_nb = ca_par_jour.pivot(index='jour_semaine', columns='exercice', values='nb_jours').fillna(0)
    pivot_moyen = ca_par_jour.pivot(index='jour_semaine', columns='exercice', values='ca_moyen').fillna(0)
    
    # Réordonner les jours (lundi à dimanche)
    pivot_total = pivot_total.reindex([0, 1, 2, 3, 4, 5, 6])
    pivot_nb = pivot_nb.reindex([0, 1, 2, 3, 4, 5, 6])
    pivot_moyen = pivot_moyen.reindex([0, 1, 2, 3, 4, 5, 6])
    
    # Ajouter la colonne jour
    pivot_total.insert(0, 'Jour', [jours_fr[i] for i in range(7)])
    pivot_nb.insert(0, 'Jour', [jours_fr[i] for i in range(7)])
    pivot_moyen.insert(0, 'Jour', [jours_fr[i] for i in range(7)])
    
    return pivot_total, pivot_nb, pivot_moyen

# ==================== AFFICHAGE ====================

if verifier_mot_de_passe():
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=150)
        
        st.title("📊 Menu")
        
        st.markdown("---")
        
        fichier_excel = st.text_input(
            "📁 Fichier Excel",
            value="data/CA_Atelier_Vincent.xlsm",
            help="Chemin vers votre fichier Excel"
        )
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["🏠 Accueil", "📊 Suivi mensuel", "📈 Historique", "➕ Saisie", "⚙️ Données brutes"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.button("🔄 Recharger les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        with st.expander("ℹ️ Informations"):
            st.markdown("""
            **L'Atelier de Vincent**
            
            Application de gestion du chiffre d'affaires
            
            © 2024 Vincent
            """)
    
    # ========== CHARGEMENT DES DONNÉES ==========
    if os.path.exists(fichier_excel):
        df = charger_donnees(fichier_excel)
        
        if df is not None:
            
            # ========== PAGE ACCUEIL ==========
            if page == "🏠 Accueil":
                st.title("🏠 L'Atelier de Vincent")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Bienvenue dans votre espace de gestion")
                    st.markdown("""
                    Cette application vous permet de :
                    - 📊 Suivre votre chiffre d'affaires mensuel
                    - 📈 Analyser l'évolution historique
                    - ➕ Saisir de nouvelles données
                    - 📄 Exporter vos rapports en PDF
                    """)
                
                with col2:
                    if os.path.exists("assets/logo.png"):
                        st.image("assets/logo.png", width=200)
                
                st.markdown("---")
                
                # ========== INDICATEURS CLÉS ==========
                st.subheader("📊 Indicateurs clés")
                
                # Calculer l'exercice actuel
                date_actuelle = datetime.now()
                exercice_actuel = calculer_exercice(date_actuelle)
                
                # Filtrer les données de l'exercice actuel
                df['exercice'] = df['date'].apply(calculer_exercice)
                df_exercice_actuel = df[df['exercice'] == exercice_actuel]
                
                # Calculer les indicateurs
                ca_total = df_exercice_actuel['montant'].sum()
                nb_jours_travailles = len(df_exercice_actuel)
                ca_moyen_jour = ca_total / nb_jours_travailles if nb_jours_travailles > 0 else 0
                
                # Trouver le meilleur mois
                df_exercice_actuel['mois'] = df_exercice_actuel['date'].dt.month
                ca_par_mois = df_exercice_actuel.groupby('mois')['montant'].sum()
                meilleur_mois_num = ca_par_mois.idxmax() if not ca_par_mois.empty else 0
                
                mois_noms = {
                    7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre',
                    11: 'Novembre', 12: 'Décembre', 1: 'Janvier', 2: 'Février',
                    3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin'
                }
                meilleur_mois = mois_noms.get(meilleur_mois_num, 'N/A')
                
                # Calculer la moyenne mensuelle (sur 12 mois)
                ca_moyen_mois = ca_total / 12
                
                # Afficher les indicateurs
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("CA Total", formater_euro(ca_total))
                
                with col2:
                    st.metric("Meilleur mois", meilleur_mois)
                
                with col3:
                    st.metric("Moyenne/mois", formater_euro(ca_moyen_mois))
                
                with col4:
                    st.metric("CA moyen/jour", formater_euro(ca_moyen_jour))
                
                st.markdown("---")
                
                # ========== FORMULAIRE DE SAISIE ==========
                st.subheader("➕ Saisie rapide")
                
                with st.form("saisie_rapide"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        date_saisie = st.date_input("Date", value=datetime.now())
                    
                    with col2:
                        montant_saisie = st.number_input("Montant (€)", min_value=0.0, step=0.01)
                    
                    with col3:
                        nb_collab_saisie = st.number_input("Nb collaborateurs", min_value=0, step=1, value=2)
                    
                    submitted = st.form_submit_button("💾 Enregistrer", use_container_width=True)
                    
                    if submitted:
                        st.success(f"✅ Données enregistrées : {formater_euro(montant_saisie)} le {date_saisie}")
                        st.info("💡 Note : Pour l'instant, cette fonctionnalité est en mode démo. Les données ne sont pas encore sauvegardées dans le fichier Excel.")
            
            # ========== PAGE SUIVI MENSUEL ==========
            elif page == "📊 Suivi mensuel":
                st.title("📊 Suivi mensuel")
                
                # Calculer les exercices disponibles
                df['exercice'] = df['date'].apply(calculer_exercice)
                exercices_disponibles = sorted(df['exercice'].unique())
                
                # Exercice actuel par défaut
                date_actuelle = datetime.now()
                exercice_actuel = calculer_exercice(date_actuelle)
                
                if exercice_actuel in exercices_disponibles:
                    index_defaut = exercices_disponibles.index(exercice_actuel)
                else:
                    index_defaut = len(exercices_disponibles) - 1
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    exercice_selectionne = st.selectbox(
                        "📅 Choisir l'exercice",
                        options=exercices_disponibles,
                        index=index_defaut
                    )
                
                with col2:
                    mois_liste = ['Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
                                  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin']
                    
                    # Mois actuel par défaut
                    mois_actuel_index = (date_actuelle.month - 7) % 12
                    
                    mois_selectionne = st.selectbox(
                        "📆 Choisir le mois",
                        options=mois_liste,
                        index=mois_actuel_index
                    )
                
                st.markdown("---")
                
                # ========== CALCUL DES DATES ==========
                annee_debut_exercice = int(exercice_selectionne.split('/')[0])
                
                mois_mapping = {
                    'Juillet': 7, 'Août': 8, 'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
                    'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 'Mai': 5, 'Juin': 6
                }
                mois_numero = mois_mapping[mois_selectionne]
                
                if mois_numero >= 7:
                    annee_mois_n = annee_debut_exercice
                else:
                    annee_mois_n = annee_debut_exercice + 1
                
                annee_mois_n_moins_1 = annee_mois_n - 1
                nb_jours_mois = calendar.monthrange(annee_mois_n, mois_numero)[1]
                
                # ========== CRÉATION DU TABLEAU ==========
                st.subheader(f"📋 {mois_selectionne} {annee_mois_n} vs {mois_selectionne} {annee_mois_n_moins_1}")
                
                placeholder_pdf_button = st.empty()
                
                donnees_tableau = []
                
                for jour in range(1, nb_jours_mois + 1):
                    date_n = datetime(annee_mois_n, mois_numero, jour)
                    jour_semaine = date_n.weekday()
                    
                    date_reference_n_moins_1 = datetime(annee_mois_n_moins_1, mois_numero, jour)
                    jours_diff = (jour_semaine - date_reference_n_moins_1.weekday()) % 7
                    
                    if jours_diff <= 3:
                        date_n_moins_1 = date_reference_n_moins_1 + timedelta(days=jours_diff)
                    else:
                        date_n_moins_1 = date_reference_n_moins_1 - timedelta(days=7 - jours_diff)
                    
                    data_n = df[df['date'] == date_n]
                    montant_n = data_n['montant'].sum()
                    nb_collab_n = data_n['nb_collaborateurs'].max() if not data_n.empty else 0
                    
                    data_n_moins_1 = df[df['date'] == date_n_moins_1]
                    montant_n_moins_1 = data_n_moins_1['montant'].sum()
                    nb_collab_n_moins_1 = data_n_moins_1['nb_collaborateurs'].max() if not data_n_moins_1.empty else 0
                    
                    jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                    nom_jour = jours_fr[jour_semaine]
                    
                    donnees_tableau.append({
                        'Jour': nom_jour,
                        'Date N-1': date_n_moins_1.strftime('%d/%m/%Y'),
                        'Date N': date_n.strftime('%d/%m/%Y'),
                        'Montant N-1': formater_euro(montant_n_moins_1) if montant_n_moins_1 > 0 else '-',
                        'Nb Collab N-1': str(nb_collab_n_moins_1) if montant_n_moins_1 > 0 else '-',
                        'Montant N': formater_euro(montant_n) if montant_n > 0 else '-',
                        'Nb Collab N': str(nb_collab_n) if montant_n > 0 else '-'
                    })
                
                df_tableau = pd.DataFrame(donnees_tableau)
                
                # Calculer les totaux
                debut_mois_n = datetime(annee_mois_n, mois_numero, 1)
                fin_mois_n = datetime(annee_mois_n, mois_numero, nb_jours_mois)
                df_mois_n = df[(df['date'] >= debut_mois_n) & (df['date'] <= fin_mois_n)]
                total_n = df_mois_n['montant'].sum()
                
                debut_mois_n_moins_1 = datetime(annee_mois_n_moins_1, mois_numero, 1)
                fin_mois_n_moins_1 = datetime(annee_mois_n_moins_1, mois_numero, nb_jours_mois)
                df_mois_n_moins_1 = df[(df['date'] >= debut_mois_n_moins_1) & (df['date'] <= fin_mois_n_moins_1)]
                total_n_moins_1 = df_mois_n_moins_1['montant'].sum()
                
                evolution_euro = total_n - total_n_moins_1
                evolution_pct = (evolution_euro / total_n_moins_1 * 100) if total_n_moins_1 != 0 else 0
                
                # Bouton Export PDF
                with placeholder_pdf_button:
                    pdf_buffer = generer_pdf_suivi(
                        donnees_tableau, 
                        mois_selectionne, 
                        annee_mois_n, 
                        annee_mois_n_moins_1,
                        total_n,
                        total_n_moins_1,
                        evolution_euro,
                        evolution_pct
                    )
                    
                    st.download_button(
                        label="📄 Exporter en PDF",
                        data=pdf_buffer,
                        file_name=f"Suivi_{mois_selectionne}_{annee_mois_n}.pdf",
                        mime="application/pdf",
                        use_container_width=False
                    )
                
                st.markdown("---")
                
                # Afficher le tableau
                st.dataframe(
                    df_tableau,
                    hide_index=True,
                    use_container_width=True,
                    height=600,
                    column_config={
                        "Jour": st.column_config.TextColumn("Jour", width="small"),
                        "Date N-1": st.column_config.TextColumn("Date N-1", width="medium"),
                        "Date N": st.column_config.TextColumn("Date N", width="medium"),
                        "Montant N-1": st.column_config.TextColumn("Montant N-1", width="medium"),
                        "Nb Collab N-1": st.column_config.TextColumn("Nb Collab N-1", width="small"),
                        "Montant N": st.column_config.TextColumn("Montant N", width="medium"),
                        "Nb Collab N": st.column_config.TextColumn("Nb Collab N", width="small")
                    }
                )
                
                # ========== TOTAUX ==========
                st.markdown("---")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        f"Total {mois_selectionne} {annee_mois_n_moins_1}",
                        formater_euro(total_n_moins_1)
                    )
                
                with col2:
                    st.metric(
                        f"Total {mois_selectionne} {annee_mois_n}",
                        formater_euro(total_n)
                    )
                
                with col3:
                    st.metric("Évolution €", formater_euro(evolution_euro))
                
                with col4:
                    st.metric("Évolution %", f"{evolution_pct:+.1f}%")
                
                # ========== RÉSUMÉ MENSUEL ==========
                st.markdown("---")
                st.subheader("📋 Résumé mensuel")
                
                resume_df = calculer_resume_mensuel(df)
                
                # Préparer les données pour le graphique
                # On prend les 2 derniers exercices s'ils existent
                exercices_cols = [col for col in resume_df.columns if col not in ['Mois', 'Évol €', 'Évol %']]
                
                if len(exercices_cols) >= 2:
                    ex_n_moins_1 = exercices_cols[-2]
                    ex_n = exercices_cols[-1]
                    
                    # Créer deux colonnes : tableau et graphique
                    col_tableau, col_graphique = st.columns([3, 2])
                    
                    with col_tableau:
                        # Formater le tableau pour l'affichage
                        resume_display = resume_df.copy()
                        
                        for col in resume_display.columns:
                            if col not in ['Mois', 'Évol %']:
                                resume_display[col] = resume_display[col].apply(lambda x: formater_euro(x) if isinstance(x, (int, float)) else x)
                            elif col == 'Évol %':
                                resume_display[col] = resume_display[col].apply(lambda x: f"{x:+.1f}%" if isinstance(x, (int, float)) else x)
                        
                        st.dataframe(
                            resume_display,
                            hide_index=True,
                            use_container_width=True,
                            height=500
                        )
                    
                    with col_graphique:
                        # Créer le graphique en barres verticales
                        fig = go.Figure()
                        
                        fig.add_trace(go.Bar(
                            name=ex_n_moins_1,
                            x=resume_df['Mois'],
                            y=resume_df[ex_n_moins_1],
                            marker_color='#6C757D'
                        ))
                        
                        fig.add_trace(go.Bar(
                            name=ex_n,
                            x=resume_df['Mois'],
                            y=resume_df[ex_n],
                            marker_color='#A89332'
                        ))
                        
                        fig.update_layout(
                            title=f"Comparaison {ex_n_minus_1} vs {ex_n}",
                            xaxis_title="Mois",
                            yaxis_title="Chiffre d'affaires (€)",
                            barmode='group',
                            height=500,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.dataframe(resume_df, hide_index=True, use_container_width=True)
            
            # ========== PAGE HISTORIQUE ==========
            elif page == "📈 Historique":
                st.title("📈 Historique")
                
                # ========== ÉVOLUTION HISTORIQUE DU CA ==========
                st.subheader("📊 Évolution historique du CA")
                
                # Calculer le CA par mois pour tous les exercices
                df['exercice'] = df['date'].apply(calculer_exercice)
                df['annee_mois'] = df['date'].dt.to_period('M')
                
                ca_mensuel = df.groupby('annee_mois')['montant'].sum().reset_index()
                ca_mensuel['annee_mois'] = ca_mensuel['annee_mois'].dt.to_timestamp()
                
                # Créer le graphique d'évolution
                fig_evolution = px.line(
                    ca_mensuel,
                    x='annee_mois',
                    y='montant',
                    title="Évolution du CA mensuel",
                    labels={'annee_mois': 'Mois', 'montant': 'CA (€)'},
                    markers=True
                )
                
                fig_evolution.update_traces(line_color='#A89332', marker=dict(size=8))
                fig_evolution.update_layout(
                    xaxis_title="Mois",
                    yaxis_title="Chiffre d'affaires (€)",
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig_evolution, use_container_width=True)
                
                # Tableau récapitulatif
                st.markdown("---")
                
                resume_mensuel = calculer_resume_mensuel(df)
                
                # Formater pour l'affichage
                resume_display = resume_mensuel.copy()
                for col in resume_display.columns:
                    if col not in ['Mois', 'Évol %']:
                        resume_display[col] = resume_display[col].apply(lambda x: formater_euro(x) if isinstance(x, (int, float)) else x)
                    elif col == 'Évol %':
                        resume_display[col] = resume_display[col].apply(lambda x: f"{x:+.1f}%" if isinstance(x, (int, float)) else x)
                
                st.dataframe(resume_display, hide_index=True, use_container_width=True, height=500)
                
                # ========== CA PAR JOUR DE LA SEMAINE ==========
                st.markdown("---")
                st.subheader("📅 CA par jour de la semaine")
                
                ca_total_jour, nb_jours_travailles, ca_moyen_jour = calculer_ca_par_jour_semaine(df)
                
                # Créer des onglets pour les différentes vues
                tab1, tab2, tab3 = st.tabs(["CA Total", "Nb jours travaillés", "CA Moyen/jour"])
                
                with tab1:
                    st.markdown("#### CA Total par jour de la semaine")
                    
                    # Formater pour l'affichage
                    ca_total_display = ca_total_jour.copy()
                    for col in ca_total_display.columns:
                        if col != 'Jour':
                            ca_total_display[col] = ca_total_display[col].apply(lambda x: formater_euro(x))
                    
                    st.dataframe(ca_total_display, hide_index=True, use_container_width=True)
                
                with tab2:
                    st.markdown("#### Nombre de jours travaillés")
                    st.dataframe(nb_jours_travailles, hide_index=True, use_container_width=True)
                
                with tab3:
                    st.markdown("#### CA Moyen par jour")
                    
                    # Formater pour l'affichage
                    ca_moyen_display = ca_moyen_jour.copy()
                    for col in ca_moyen_display.columns:
                        if col != 'Jour':
                            ca_moyen_display[col] = ca_moyen_display[col].apply(lambda x: formater_euro(x))
                    
                    st.dataframe(ca_moyen_display, hide_index=True, use_container_width=True)
            
            elif page == "➕ Saisie":
                st.title("➕ Saisie de données")
                st.info("Utilisez le formulaire sur la page d'accueil")
            
            elif page == "⚙️ Données brutes":
                st.title("⚙️ Données brutes")
                st.dataframe(df, use_container_width=True)
        
        else:
            st.error("❌ Impossible de charger les données du fichier Excel")
    else:
        st.error(f"❌ Le fichier '{fichier_excel}' n'existe pas. Vérifiez le chemin dans la sidebar.")
