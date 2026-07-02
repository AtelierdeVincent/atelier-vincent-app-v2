"""
🎯 L'ATELIER DE VINCENT - Application de Gestion CA
Application web créée avec Streamlit pour remplacer votre Excel

© 2024-2025 Vincent - L'Atelier de Vincent
Tous droits réservés.

Cette application est la propriété de Vincent.
Toute reproduction, distribution ou utilisation non autorisée est interdite.

Auteur : Vincent
Date : Décembre 2024
Version : 2.0
"""

# ==================== IMPORTS ====================

import streamlit as st
import pandas as pd
import plotly.express as px
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
import gspread
from google.oauth2.service_account import Credentials

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
            # Si aucun locale français n'est disponible, on continue sans
            # Les noms de jours/mois sont déjà en français dans le code
            pass

# ==================== CONFIGURATION ====================

st.set_page_config(
    page_title="L'Atelier de Vincent",
    page_icon="assets/logo.png",  # Utilise votre logo comme favicon
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration PWA pour utiliser votre logo sur mobile
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

    with st.form("login_form"):
        password = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="Entrez le mot de passe"
        )
        submitted = st.form_submit_button("Se connecter", use_container_width=True)

    if submitted:
        if password == "3108":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Mot de passe incorrect. Réessayez.")

    return False
# ==================== FONCTIONS UTILES ====================

# ==================== CONFIGURATION GOOGLE SHEETS ====================

SPREADSHEET_ID = "15muR5Bg2cdGfav5RxwKK7kVuC0iPaUoCz9awiKVCa6o"
SHEET_NAME = "Données"

@st.cache_resource
def get_gsheet_client():
    """Crée la connexion à Google Sheets"""
    try:
        # Charger les credentials depuis Streamlit secrets
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"❌ Erreur de connexion à Google Sheets : {e}")
        return None

# ==================== FONCTIONS UTILES ====================

@st.cache_data(ttl=10)
def charger_donnees():
    """Charge les données depuis Google Sheets"""
    try:
        client = get_gsheet_client()
        if not client:
            return None
        
        # Ouvrir le spreadsheet
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        
        # Récupérer toutes les données (ligne par ligne)
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 2:
            st.warning("⚠️ Aucune donnée trouvée dans Google Sheets")
            return None
        
        # La première ligne contient les en-têtes, les autres sont les données
        headers = all_values[0]
        data_rows = all_values[1:]
        
        # Créer le DataFrame manuellement
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Compter les lignes initiales
        nb_lignes_initiales = len(df)
        
        # Identifier les colonnes (même avec doublons, on prend les indices)
        # Colonnes attendues : A=Clé, B=Année, C=Date, D=Jour, E=Mois, F=Valeur, G=Nb_Collaborateurs
        
        # Traiter les colonnes par index pour éviter les problèmes de noms
        if len(df.columns) >= 7:
            df['date'] = pd.to_datetime(df.iloc[:, 2], errors='coerce', dayfirst=True)  # Colonne C (index 2)
            
            # Nettoyage robuste des montants (colonne F = index 5)
            def nettoyer_montant(valeur):
                if pd.isna(valeur) or valeur == '' or valeur == '0':
                    return 0
                
                if isinstance(valeur, (int, float)):
                    return float(valeur)
                
                if isinstance(valeur, str):
                    import re
                    valeur_nettoyee = re.sub(r'[^\d,.-]', '', valeur)
                    valeur_nettoyee = valeur_nettoyee.replace(',', '.')
                    try:
                        return float(valeur_nettoyee)
                    except:
                        return 0
                
                return 0
            
            df['montant'] = df.iloc[:, 5].apply(nettoyer_montant)  # Colonne F (index 5)
            df['nb_collaborateurs'] = pd.to_numeric(df.iloc[:, 6], errors='coerce').fillna(0).astype(int)  # Colonne G (index 6)
        else:
            st.error(f"❌ Structure du sheet incorrecte. Colonnes trouvées : {len(df.columns)}")
            return None
        
        # Compter combien de lignes sont perdues
        nb_dates_invalides = df['date'].isna().sum()
        nb_montants_nuls = (df['montant'] == 0).sum()
        
        # Filtrer uniquement les lignes où date ET montant sont valides
        df = df.dropna(subset=['date'])
        df = df[df['montant'] > 0]  # On garde seulement les montants > 0
        nb_lignes_finales = len(df)
        
        # Sélectionner seulement les colonnes nécessaires
        df = df[['date', 'montant', 'nb_collaborateurs']].copy()
        
        # Détection et correction automatique si nécessaire
        if len(df) > 0:
            montants_non_nuls = df['montant']
            if len(montants_non_nuls) > 0:
                moyenne = montants_non_nuls.mean()
                
                # Si la moyenne est > 1000€, diviser par 100
                if moyenne > 1000:
                    df['montant'] = df['montant'] / 100
                    st.info("✅ Correction automatique appliquée aux montants")
        
        df = df.dropna(subset=['date', 'montant'])
        df = df[['date', 'montant', 'nb_collaborateurs']].copy()
        
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement : {e}")
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

def obtenir_citation_du_jour():
    """Retourne une citation motivante qui change chaque jour"""
    citations = [
        "💪 Chaque jour est une nouvelle opportunité de briller !",
        "✨ Le succès, c'est la somme de petits efforts répétés jour après jour.",
        "🎯 La seule façon de faire du bon travail, c'est d'aimer ce que vous faites.",
        "🌟 Votre attitude détermine votre altitude.",
        "💼 Le succès n'est pas la clé du bonheur. Le bonheur est la clé du succès.",
        "🚀 Croyez en vous et tout devient possible.",
        "⭐ La passion est l'énergie qui maintient tout en marche.",
        "🎨 Votre travail est une œuvre d'art qui se construit chaque jour.",
        "💎 L'excellence n'est pas une destination, c'est un voyage continu.",
        "🏆 Le succès commence par la volonté de l'atteindre.",
        "🌈 Aujourd'hui est rempli de possibilités infinies.",
        "💫 Chaque client est une opportunité de créer quelque chose de magnifique.",
        "🎯 La régularité bat le talent quand le talent ne travaille pas.",
        "🌟 Votre énergie positive attire le succès.",
        "💪 La persévérance transforme l'impossible en possible.",
        "✂️ Chaque coupe est une signature, chaque client une histoire.",
        "🎨 L'art de la coiffure, c'est l'art de sublimer les personnes.",
        "💼 Un professionnel n'attend pas l'inspiration, il crée les conditions du succès.",
        "🚀 Petit à petit, l'oiseau fait son nid - et vous bâtissez votre empire.",
        "⭐ Votre savoir-faire mérite le succès que vous construisez chaque jour.",
        "🌟 L'investissement en soi-même rapporte toujours les meilleurs intérêts.",
        "💎 La qualité n'est jamais un accident ; c'est toujours le résultat d'un effort intelligent.",
        "🏆 Ce que vous faites aujourd'hui peut améliorer tous vos lendemains.",
        "🌈 Le meilleur moment pour planter un arbre était il y a 20 ans. Le deuxième meilleur moment, c'est maintenant.",
        "💫 Votre travail est le reflet de qui vous êtes. Rendez-le remarquable !",
        "🎯 Le secret du succès : commencer avant d'être prêt.",
        "✨ Vos clients ne paient pas pour une coupe, ils paient pour votre expertise.",
        "💪 La discipline est le pont entre les objectifs et les accomplissements.",
        "🚀 Ne comptez pas les jours, faites que les jours comptent.",
        "⭐ Votre attitude d'aujourd'hui façonne votre réussite de demain."
    ]
    
    # Utilise la date du jour pour sélectionner une citation (change chaque jour)
    from datetime import datetime
    jour_annee = datetime.now().timetuple().tm_yday
    index = jour_annee % len(citations)
    return citations[index]

def obtenir_badge_reussite(ca_actuel, objectif, pourcentage):
    """Retourne un badge de réussite selon la performance"""
    if ca_actuel >= objectif:
        return {
            'emoji': '🏆',
            'titre': 'OBJECTIF ATTEINT !',
            'message': f'Félicitations ! Vous avez dépassé votre objectif de {pourcentage:.1f}% !',
            'couleur': '#2ECC71'  # Vert
        }
    elif pourcentage >= 95:
        return {
            'emoji': '🎯',
            'titre': 'PRESQUE !',
            'message': f'Plus que {objectif - ca_actuel:,.0f}€ pour atteindre votre objectif !',
            'couleur': '#F39C12'  # Orange
        }
    elif pourcentage >= 80:
        return {
            'emoji': '💪',
            'titre': 'BON RYTHME !',
            'message': f'Vous êtes à {pourcentage:.1f}% de votre objectif. Continuez !',
            'couleur': '#3498DB'  # Bleu
        }
    else:
        return {
            'emoji': '🚀',
            'titre': 'EN ROUTE !',
            'message': f'Vous avez réalisé {pourcentage:.1f}% de votre objectif.',
            'couleur': '#95A5A6'  # Gris
        }

def afficher_watermark():
    """Affiche un watermark discret en bas de page"""
    st.markdown("""
    <div style="text-align: center; padding: 20px 0; color: #bdc3c7; font-size: 11px; margin-top: 50px;">
        <p style="margin: 0;">✂️ Fait avec ❤️ par Vincent | © 2024-2025 L'Atelier de Vincent | Tous droits réservés</p>
    </div>
    """, unsafe_allow_html=True)

# Objectifs mensuels personnalisés pour l'exercice 2025/2026
OBJECTIFS_MENSUELS = {
    'Juillet': 11479.52,
    'Août': 13224.12,
    'Septembre': 11459.34,
    'Octobre': 11871.08,
    'Novembre': 12159.20,
    'Décembre': 15883.30,
    'Janvier': 13214.55,
    'Février': 13937.66,
    'Mars': 10975.85,
    'Avril': 14429.69,
    'Mai': 13870.38,
    'Juin': 14791.09
}


def generer_pdf_suivi(donnees_tableau, mois_selectionne, annee_mois_n, annee_mois_n_moins_1, total_n, total_n_moins_1, evolution_euro, evolution_pct):
    """Génère un PDF du tableau de suivi mensuel optimisé pour tenir sur une page A4 paysage"""
    buffer = BytesIO()
    
    # Créer le document en mode paysage
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1*cm
    )
    
    elements = []
    
    # Ajouter le logo en haut
    try:
        logo_path = "assets/logo_noir.png"
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=3*cm, height=3*cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.3*cm))
    except:
        pass
    
    # Titre
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    title_text = f"Suivi Mensuel - {mois_selectionne} {annee_mois_n} vs {mois_selectionne} {annee_mois_n_moins_1}"
    title = Paragraph(title_text, title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))
    
    # Préparer les données du tableau
    table_data = [['Jour', 'Date N-1', 'Date N', 'Montant N-1', 'Nb C. N-1', 'Montant N', 'Nb C. N']]
    
    for row in donnees_tableau:
        table_data.append([
            row['Jour'][:3],  # Abréger les jours (Lun, Mar, etc.)
            row['Date N-1'],
            row['Date N'],
            row['Montant N-1'],
            row['Nb Collab N-1'],
            row['Montant N'],
            row['Nb Collab N']
        ])
    
    # Créer le tableau avec des largeurs optimisées
    col_widths = [2*cm, 2.5*cm, 2.5*cm, 3*cm, 1.8*cm, 3*cm, 1.8*cm]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style du tableau
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Corps du tableau
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Totaux
    totaux_style = ParagraphStyle(
        'Totaux',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    totaux_text = f"""
    <b>Total {mois_selectionne} {annee_mois_n_moins_1}:</b> {formater_euro(total_n_moins_1)} | 
    <b>Total {mois_selectionne} {annee_mois_n}:</b> {formater_euro(total_n)} | 
    <b>Évolution:</b> {formater_euro(evolution_euro)} ({evolution_pct:+.1f}%)
    """
    
    totaux = Paragraph(totaux_text, totaux_style)
    elements.append(totaux)
    
    # Pied de page
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    date_generation = datetime.now().strftime("%d/%m/%Y à %H:%M")
    footer = Paragraph(f"<i>Document généré le {date_generation} - L'Atelier de Vincent</i>", footer_style)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(footer)
    
    # Construire le PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generer_pdf_historique(df, exercices):
    """Génère un PDF complet de la page Historique avec chaque tableau sur une page séparée"""
    buffer = BytesIO()
    
    # Créer le document en mode portrait par défaut
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Style des titres
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.black,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    # ========== PAGE 1 : STATISTIQUES PAR EXERCICE ==========
    # Logo
    try:
        logo_path = "assets/logo_noir.png"
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=3*cm, height=3*cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.3*cm))
    except:
        pass
    
    elements.append(Paragraph("Historique par Exercice", title_style))
    elements.append(Paragraph("L'Atelier de Vincent", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    
    elements.append(Paragraph("📊 Statistiques par Exercice", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Préparer les données
    stats_data = [['Exercice', 'CA Total', 'Jours\nTravaillés', 'Moy.\nCollab.', 'CA Moyen\nMensuel', 'CA Moyen\nJournalier']]
    
    for exercice in exercices:
        df_exercice = df[df['exercice'] == exercice]
        ca_total = df_exercice['montant'].sum()
        
        df_avec_ca = df_exercice[df_exercice['montant'] > 0]
        nb_jours_travailles = len(df_avec_ca)
        moyenne_collab = df_avec_ca['nb_collaborateurs'].mean() if len(df_avec_ca) > 0 else 0
        
        ca_moyen_jour = ca_total / nb_jours_travailles if nb_jours_travailles > 0 else 0
        ca_moyen_mois = ca_total / 12
        
        stats_data.append([
            exercice,
            formater_euro(ca_total),
            str(nb_jours_travailles),
            f"{moyenne_collab:.1f}",
            formater_euro(ca_moyen_mois),
            formater_euro(ca_moyen_jour)
        ])
    
    # Créer le tableau
    stats_table = Table(stats_data, colWidths=[2.5*cm, 3.5*cm, 2*cm, 1.8*cm, 3.5*cm, 3.5*cm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A89332')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(stats_table)
    
    # Pied de page
    date_generation = datetime.now().strftime("%d/%m/%Y à %H:%M")
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<i>Page 1/3 - Généré le {date_generation}</i>", footer_style))
    
    # Saut de page
    from reportlab.platypus import PageBreak
    elements.append(PageBreak())
    
    # ========== PAGE 2 : MONTANTS MENSUELS (PORTRAIT - MOIS EN LIGNES) ==========
    # Logo
    try:
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.2*cm))
    except:
        pass
    
    elements.append(Paragraph("📊 Montants Mensuels par Exercice", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Préparer les données avec MOIS EN LIGNES et EXERCICES EN COLONNES
    mois_ordre = ['Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
                  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin']
    mois_mapping = {
        'Juillet': 7, 'Août': 8, 'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
        'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 'Mai': 5, 'Juin': 6
    }
    
    # Filtrer les exercices >= 2019/2020
    exercices_filtre = [ex for ex in exercices if ex >= '2019/2020']
    
    # En-tête : Mois + Exercices
    monthly_data = [['Mois'] + exercices_filtre]
    
    # Chaque ligne = un mois
    for mois_nom in mois_ordre:
        row = [mois_nom]
        mois_num = mois_mapping[mois_nom]
        
        for exercice in exercices_filtre:
            df_ex = df[df['exercice'] == exercice]
            montant = df_ex[df_ex['mois'] == mois_num]['montant'].sum()
            row.append(formater_euro(montant))
        
        monthly_data.append(row)
    
    # Ligne Total
    row_total = ['TOTAL']
    for exercice in exercices_filtre:
        df_ex = df[df['exercice'] == exercice]
        total = df_ex['montant'].sum()
        row_total.append(formater_euro(total))
    monthly_data.append(row_total)
    
    # Calculer les largeurs de colonnes dynamiquement
    nb_exercices = len(exercices_filtre)
    largeur_mois = 2.5*cm
    largeur_exercice = (19*cm - largeur_mois) / nb_exercices  # 19cm = largeur utilisable
    col_widths = [largeur_mois] + [largeur_exercice] * nb_exercices
    
    # Créer le tableau
    monthly_table = Table(monthly_data, colWidths=col_widths)
    monthly_table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A89332')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        
        # Colonne Mois
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (0, -2), 8),
        
        # Données montants
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (1, 1), (-1, -2), 7),
        
        # Ligne Total
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#A89332')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 8),
        
        # Général
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(monthly_table)
    
    # Pied de page
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<i>Page 2/3 - Généré le {date_generation}</i>", footer_style))
    
    # Saut de page
    elements.append(PageBreak())
    
    # ========== PAGE 3 : COMPARATIF PAR JOUR DE LA SEMAINE (PAYSAGE) ==========
    # Cette page sera en paysage pour plus d'espace
    from reportlab.platypus import NextPageTemplate, PageTemplate, Frame
    
    # Ajouter un template paysage
    landscape_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id='landscape_frame'
    )
    landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape(A4))
    
    # Note: Pour simplifier, on garde en portrait mais avec une taille de police réduite
    
    # Logo
    try:
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
            elements.append(logo)
            elements.append(Spacer(1, 0.2*cm))
    except:
        pass
    
    elements.append(Paragraph("📅 Comparatif par Jour de la Semaine", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Mapping des jours
    jours_en_fr = {
        'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
    }
    df['jour_semaine_fr'] = df['jour_semaine'].map(jours_en_fr)
    jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # Préparer les données
    comparatif_data = [['Jour'] + list(exercices)]
    
    for jour in jours_ordre:
        row = [jour]
        for exercice in exercices:
            df_exercice = df[df['exercice'] == exercice]
            df_jour = df_exercice[df_exercice['jour_semaine_fr'] == jour]
            ca_jour = df_jour['montant'].sum()
            row.append(formater_euro(ca_jour))
        comparatif_data.append(row)
    
    # Créer le tableau comparatif
    nb_exercices_total = len(exercices)
    largeur_jour = 2*cm
    largeur_ex = (19*cm - largeur_jour) / nb_exercices_total
    col_widths_comp = [largeur_jour] + [largeur_ex] * nb_exercices_total
    
    comparatif_table = Table(comparatif_data, colWidths=col_widths_comp)
    comparatif_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A89332')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(comparatif_table)
    
    # Pied de page
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"<i>Page 3/3 - Généré le {date_generation}</i>", footer_style))
    
    # Construire le PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def enregistrer_transaction(date_saisie, montant, nb_collaborateurs):
    """Enregistre une nouvelle transaction dans Google Sheets"""
    try:
        client = get_gsheet_client()
        if not client:
            return False, "❌ Impossible de se connecter à Google Sheets"
        
        # Ouvrir le spreadsheet
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        
        # Préparer les données
        annee = date_saisie.year
        # Format pour Google Sheets : d/m/yyyy (sans zéros de tête)
        date_str_sheets = f"{date_saisie.day}/{date_saisie.month}/{date_saisie.year}"
        cle = f"{annee}|{date_saisie.strftime('%Y-%m-%d')}"
        
        # Noms des jours et mois en français
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        mois_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 
                   'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        
        jour_semaine = jours_fr[date_saisie.weekday()]
        mois_nom = mois_fr[date_saisie.month - 1]
        
        # Récupérer toutes les données pour trouver si la date existe
        all_data = worksheet.get_all_values()
        
        # Trouver la ligne correspondante (chercher dans la colonne Date - colonne C = index 2)
        ligne_existante = None
        for idx, row in enumerate(all_data[1:], start=2):  # Commencer à la ligne 2 (après l'en-tête)
            if len(row) > 2:
                # Comparer les dates en les parsant (pour gérer tous les formats)
                date_row = row[2]
                try:
                    # Parser la date du sheet
                    date_parsed = pd.to_datetime(date_row, dayfirst=True).date()
                    if date_parsed == date_saisie.date():
                        ligne_existante = idx
                        break
                except:
                    continue
        
        if ligne_existante:
            if montant == 0:
                # SUPPRESSION : Montant = 0
                worksheet.delete_rows(ligne_existante)
                message = f"🗑️ Transaction SUPPRIMÉE pour le {date_saisie.strftime('%d/%m/%Y')}"
            else:
                # MISE À JOUR : La date existe déjà
                worksheet.update_cell(ligne_existante, 6, montant)  # Colonne F = Valeur
                worksheet.update_cell(ligne_existante, 7, nb_collaborateurs)  # Colonne G = Nb_Collaborateurs
                message = f"✅ Transaction MISE À JOUR : {formater_euro(montant)} le {date_saisie.strftime('%d/%m/%Y')} ({nb_collaborateurs} collaborateur{'s' if nb_collaborateurs > 1 else ''})"
        else:
            if montant == 0:
                # Pas de création si montant = 0 et date inexistante
                message = f"ℹ️ Aucune donnée à supprimer pour le {date_saisie.strftime('%d/%m/%Y')}"
            else:
                # AJOUT : Nouvelle date
                nouvelle_ligne = [
                    cle,                  # Clé (A)
                    annee,                # Année (B)
                    date_str_sheets,      # Date au format Google Sheets : d/m/yyyy (C)
                    jour_semaine,         # Jour (D)
                    mois_nom,             # Mois (E)
                    montant,              # Valeur (F)
                    nb_collaborateurs     # Nb_Collaborateurs (G)
                ]
                
                worksheet.append_row(nouvelle_ligne)
                message = f"✅ Transaction AJOUTÉE : {formater_euro(montant)} le {date_saisie.strftime('%d/%m/%Y')} ({nb_collaborateurs} collaborateur{'s' if nb_collaborateurs > 1 else ''})"
        
        return True, message
        
    except Exception as e:
        return False, f"❌ Erreur lors de l'enregistrement : {str(e)}"

# ==================== SIDEBAR ====================

st.sidebar.title("📊 L'Atelier de Vincent")
st.sidebar.markdown("---")

st.sidebar.info("💡 **Données stockées dans Google Sheets**")
st.sidebar.markdown(f"📋 Sheet ID : `{SPREADSHEET_ID[:10]}...`")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "📊 Suivi", "📈 Historique", "🔮 Prévisions", "💰 Calculateur Financier", "⚙️ Données brutes"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Application créée pour gérer votre chiffre d'affaires")

# ========== FOOTER COPYRIGHT ==========
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; padding: 10px; color: #7f8c8d; font-size: 12px;">
    <p style="margin: 5px 0;">✂️ Fait avec ❤️ par <b>Vincent</b></p>
    <p style="margin: 5px 0;">© 2024-2025 L'Atelier de Vincent</p>
    <p style="margin: 5px 0; font-size: 10px;">Tous droits réservés</p>
    <p style="margin: 5px 0; font-size: 10px;">Version 2.0</p>
</div>
""", unsafe_allow_html=True)

# ==================== VÉRIFICATION MOT DE PASSE ====================

if not verifier_mot_de_passe():
    st.stop()

# ==================== CHARGEMENT DES DONNÉES ====================

df = charger_donnees()

if df is not None and not df.empty:
    # Trouver la dernière date avec une valeur > 0
    df_avec_valeur = df[df['montant'] > 0]
    if not df_avec_valeur.empty:
        derniere_date = df_avec_valeur['date'].max()
    else:
        derniere_date = df['date'].max()
    
    # Ajouter colonnes calculées
    df['exercice'] = df['date'].apply(calculer_exercice)
    df['annee'] = df['date'].dt.year
    df['mois'] = df['date'].dt.month
    df['jour_semaine'] = df['date'].dt.day_name()
    
    # ==================== PAGE ACCUEIL ====================

    if page == "🏠 Accueil":
        # En-tête centré
        st.markdown("""
        <h1 style='text-align: center;'>Tableau de Bord<br>L'Atelier de Vincent</h1>
        """, unsafe_allow_html=True)
        
        st.markdown("### 👋 Bonjour Vincent !")
        
        # ========== CITATION MOTIVANTE DU JOUR ==========
        citation = obtenir_citation_du_jour()
        st.info(citation)
        
        derniere_date_str = derniere_date.strftime("%d/%m/%Y")
        st.markdown(f"### Voici où nous en sommes à la date du : **{derniere_date_str}**")
        
        # ========== GRAPHIQUE DE PROGRESSION EXERCICE EN COURS ==========
        
        # Calculer dynamiquement l'exercice en cours (juillet-juin)
        _auj = datetime.now()
        if _auj.month >= 7:
            exercice_actuel = f"{_auj.year}/{_auj.year + 1}"
        else:
            exercice_actuel = f"{_auj.year - 1}/{_auj.year}"
        objectif_ca = 157000  # Objectif annuel en euros
        
        # Filtrer les données de l'exercice en cours uniquement (borné par les dates de l'exercice)
        _annee_ex = int(exercice_actuel.split('/')[0])
        _debut_ex = datetime(_annee_ex, 7, 1)
        _fin_ex = datetime(_annee_ex + 1, 6, 30)
        df_exercice_actuel = df[(df['date'] >= _debut_ex) & (df['date'] <= _fin_ex)]
        ca_actuel = df_exercice_actuel['montant'].sum()
        
        # Pourcentage de progression
        pourcentage_progression = (ca_actuel / objectif_ca * 100) if objectif_ca > 0 else 0
        
        # ========== BADGE DE RÉUSSITE ==========
        badge = obtenir_badge_reussite(ca_actuel, objectif_ca, pourcentage_progression)
        
        st.markdown(f"""
        <div style="background-color: {badge['couleur']}; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
            <h1 style="color: white; margin: 0;">{badge['emoji']} {badge['titre']}</h1>
            <p style="color: white; font-size: 18px; margin: 10px 0 0 0;">{badge['message']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Créer le graphique gauge (jauge)
        fig_gauge = px.pie(
            values=[ca_actuel, max(0, objectif_ca - ca_actuel)],
            names=['Réalisé', 'Restant'],
            hole=0.7,
            color_discrete_sequence=['#A89332', '#E5E5E5']
        )
        
        # Mise en forme pour ressembler à une jauge en demi-cercle
        fig_gauge.update_traces(
            textposition='none',
            hovertemplate='%{label}: %{value:,.0f} €<extra></extra>'
        )
        
        fig_gauge.update_layout(
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0),
            height=250,
            annotations=[
                dict(
                    text=f'<b>{formater_euro(ca_actuel)}</b><br><span style="font-size:14px">{pourcentage_progression:.1f}% de l\'objectif</span>',
                    x=0.5, y=0.5,
                    font_size=20,
                    showarrow=False,
                    font_color='#A89332'
                )
            ]
        )
        
        # Alternative : Utiliser un vrai gauge indicator
        fig_gauge_alt = {
            "data": [
                {
                    "type": "indicator",
                    "mode": "gauge+number+delta",
                    "value": ca_actuel,
                    "domain": {"x": [0, 1], "y": [0, 1]},
                    "title": {"text": f"<b>Objectif Exercice {exercice_actuel}</b><br><span style='font-size:0.8em'>Objectif : {formater_euro(objectif_ca)}</span>", "font": {"size": 16}},
                    "delta": {"reference": objectif_ca, "valueformat": ",.0f", "suffix": " €"},
                    "number": {"valueformat": ",.0f", "suffix": " €", "font": {"size": 28, "color": "#A89332"}},
                    "gauge": {
                        "axis": {
                            "range": [None, objectif_ca],
                            "tickwidth": 1,
                            "tickcolor": "gray",
                            "tickformat": ",.0f"
                        },
                        "bar": {"color": "#A89332", "thickness": 0.75},
                        "bgcolor": "white",
                        "borderwidth": 2,
                        "bordercolor": "gray",
                        "steps": [
                            {"range": [0, objectif_ca * 0.5], "color": "#FFE5E5"},
                            {"range": [objectif_ca * 0.5, objectif_ca * 0.8], "color": "#FFF5E5"},
                            {"range": [objectif_ca * 0.8, objectif_ca], "color": "#E5F5E5"}
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": objectif_ca
                        }
                    }
                }
            ],
            "layout": {
                "margin": {"t": 80, "b": 40, "l": 40, "r": 40},
                "height": 300,
                "font": {"family": "Arial, sans-serif"}
            }
        }
        
        # Afficher le graphique
        col_gauge1, col_gauge2, col_gauge3 = st.columns([1, 2, 1])
        
        with col_gauge2:
            st.plotly_chart(fig_gauge_alt, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("---")
        
        # ========== SECTION 1 : JOURNALIER ==========
        st.subheader("📅 Comparaison Journalière")
        
        date_n = derniere_date
        jour_semaine_n = date_n.strftime('%A')
        
        # Trouver le même jour de semaine l'année précédente (avec gestion 29 février)
        try:
            date_n_moins_1_approx = date_n.replace(year=date_n.year - 1)
        except ValueError:
            # Cas du 29 février en année non bissextile → utiliser 28 février
            date_n_moins_1_approx = datetime(date_n.year - 1, 2, 28)
        
        # Chercher le même jour de semaine dans une fenêtre de +/- 3 jours
        for delta in range(-3, 4):
            date_candidate = date_n_moins_1_approx + timedelta(days=delta)
            if date_candidate.strftime('%A') == jour_semaine_n:
                date_n_moins_1 = date_candidate
                break
        
        ca_jour_n = df[df['date'] == date_n]['montant'].sum()
        ca_jour_n_moins_1 = df[df['date'] == date_n_moins_1]['montant'].sum()
        
        evolution_jour_euro = ca_jour_n - ca_jour_n_moins_1
        evolution_jour_pct = (evolution_jour_euro / ca_jour_n_moins_1 * 100) if ca_jour_n_moins_1 != 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
               f"CA du {date_n_moins_1.strftime('%d/%m/%Y')}",
   		   formater_euro(ca_jour_n_moins_1),
               help=f"{jour_semaine_n} {date_n_moins_1.strftime('%d/%m/%Y')}"
           )


        with col2:
            st.metric(
                f"CA du **{derniere_date_str}**", 
                formater_euro(ca_jour_n),
                help=f"{jour_semaine_n} {date_n.strftime('%d/%m/%Y')}"
            )
        with col3:
            st.metric("Évolution €", formater_euro(evolution_jour_euro))
        with col4:
            st.metric("Évolution %", f"{evolution_jour_pct:+.1f}%")
        
        st.markdown("---")
        
        # ========== SECTION 2 : MENSUEL ==========
        
        mois_actuel = date_n.month
        annee_actuelle = date_n.year
        jour_actuel = date_n.day
        
        # Cumul mois N
        debut_mois_n = date_n.replace(day=1)
        df_mois_n = df[(df['date'] >= debut_mois_n) & (df['date'] <= date_n)]
        cumul_mois_n = df_mois_n['montant'].sum()
        
        nb_jours_ecoules = jour_actuel
        
        # Cumul mois N-1 : MÊME MOIS, année précédente, MÊME JOUR DE LA SEMAINE
        mois_n_moins_1 = mois_actuel
        annee_n_moins_1 = annee_actuelle - 1
        
        # Trouver le même jour de semaine l'année précédente (comme pour la comparaison journalière)
        jour_semaine_n = date_n.strftime('%A')
        
        try:
            date_fin_n_moins_1_approx = date_n.replace(year=annee_n_moins_1)
        except ValueError:
            # Cas du 29 février en année non bissextile → utiliser 28 février
            date_fin_n_moins_1_approx = datetime(annee_n_moins_1, 2, 28)
        
        # Chercher le même jour de semaine dans une fenêtre de +/- 3 jours
        date_fin_n_moins_1 = date_fin_n_moins_1_approx  # Valeur par défaut
        for delta in range(-3, 4):
            date_candidate = date_fin_n_moins_1_approx + timedelta(days=delta)
            if date_candidate.strftime('%A') == jour_semaine_n and date_candidate.month == mois_n_moins_1:
                date_fin_n_moins_1 = date_candidate
                break
        
        debut_mois_n_moins_1 = datetime(annee_n_moins_1, mois_n_moins_1, 1)
        
        df_mois_n_moins_1 = df[(df['date'] >= debut_mois_n_moins_1) & (df['date'] <= date_fin_n_moins_1)]
        cumul_mois_n_moins_1 = df_mois_n_moins_1['montant'].sum()
        
        jour_fin_n_moins_1 = date_fin_n_moins_1.day
        dernier_jour_mois_n_moins_1 = calendar.monthrange(annee_n_moins_1, mois_n_moins_1)[1]
        
        # Calculer l'objectif : CA mois N-1 complet + 4%
        # On prend le mois COMPLET de N-1 (pas juste les jours écoulés)
        debut_mois_complet_n_moins_1 = datetime(annee_n_moins_1, mois_n_moins_1, 1)
        fin_mois_complet_n_moins_1 = datetime(annee_n_moins_1, mois_n_moins_1, dernier_jour_mois_n_moins_1)
        df_mois_complet_n_moins_1 = df[(df['date'] >= debut_mois_complet_n_moins_1) & (df['date'] <= fin_mois_complet_n_moins_1)]
        ca_mois_complet_n_moins_1 = df_mois_complet_n_moins_1['montant'].sum()
        
        # Objectif = CA mois N-1 complet + 4%
        objectif_mois = ca_mois_complet_n_moins_1 * 1.04
        
        # Pourcentage de progression vers l'objectif (proratisé sur les jours écoulés)
        # Objectif proratisé = objectif_mois * (nb_jours_ecoules / nb_jours_du_mois)
        nb_jours_mois_n = calendar.monthrange(annee_actuelle, mois_actuel)[1]
        objectif_proratise = objectif_mois * (nb_jours_ecoules / nb_jours_mois_n)
        
        pourcentage_objectif = (cumul_mois_n / objectif_proratise * 100) if objectif_proratise > 0 else 0
        
        # Afficher le titre et la jauge côte à côte
        col_titre, col_jauge = st.columns([1, 2])
        
        with col_titre:
            st.subheader("📊 Comparaison Mensuelle")
        
        with col_jauge:
            # Affichage de l'objectif en haut
            st.markdown(f"**Objectif mois : {formater_euro(objectif_mois)}** (Mois 2024/2025 +4%)")
            
            # Calcul du reste à faire
            reste_a_faire_mois = max(0, objectif_mois - cumul_mois_n)
            
            # Créer un graphique en barres empilées
            import plotly.graph_objects as go
            
            fig_progress = go.Figure()
            
            # Barre bleue pour le réalisé
            fig_progress.add_trace(go.Bar(
                x=[cumul_mois_n],
                y=[''],
                orientation='h',
                name='Réalisé',
                marker=dict(color='#3498DB'),
                text=formater_euro(cumul_mois_n),
                textposition='inside',
                textfont=dict(color='white', size=14),
                hovertemplate='Réalisé: %{x:,.0f}€<extra></extra>'
            ))
            
            # Barre orange pour le reste
            if reste_a_faire_mois > 0:
                fig_progress.add_trace(go.Bar(
                    x=[reste_a_faire_mois],
                    y=[''],
                    orientation='h',
                    name='Reste',
                    marker=dict(color='#FF8C00'),
                    text=formater_euro(reste_a_faire_mois),
                    textposition='inside',
                    textfont=dict(color='white', size=14),
                    hovertemplate='Reste: %{x:,.0f}€<extra></extra>'
                ))
            
            fig_progress.update_layout(
                barmode='stack',
                showlegend=False,
                height=80,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                    range=[0, objectif_mois]
                ),
                yaxis=dict(
                    showticklabels=False,
                    showgrid=False
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_progress, use_container_width=True, config={'displayModeBar': False})
        
        evolution_mois_euro = cumul_mois_n - cumul_mois_n_moins_1
        evolution_mois_pct = (evolution_mois_euro / cumul_mois_n_moins_1 * 100) if cumul_mois_n_moins_1 != 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            jour_semaine_n_moins_1 = date_fin_n_moins_1.strftime('%A')
            st.metric(
                "Cumul Mois N-1", 
                formater_euro(cumul_mois_n_moins_1),
                help=f"{jour_semaine_n_moins_1} - Du 1er au {date_fin_n_moins_1.strftime('%d/%m/%Y')} ({jour_fin_n_moins_1} jours)"
            )
        with col2:
            st.metric(
                "Cumul Mois", 
                formater_euro(cumul_mois_n),
                help=f"Du 1er au {jour_actuel} {date_n.strftime('%B %Y')} ({nb_jours_ecoules} jours)"
            )
        with col3:
            st.metric("Évolution €", formater_euro(evolution_mois_euro))
        with col4:
            st.metric("Évolution %", f"{evolution_mois_pct:+.1f}%")
        
        # ========== MESSAGE MOTIVANT ==========
        st.markdown("")
        
        # CA TOTAL du mois de l'année dernière (mois complet)
        debut_mois_complet_n_moins_1 = datetime(annee_n_moins_1, mois_n_moins_1, 1)
        dernier_jour_complet = calendar.monthrange(annee_n_moins_1, mois_n_moins_1)[1]
        fin_mois_complet_n_moins_1 = datetime(annee_n_moins_1, mois_n_moins_1, dernier_jour_complet)
        
        df_mois_complet_n_moins_1 = df[(df['date'] >= debut_mois_complet_n_moins_1) & 
                                        (df['date'] <= fin_mois_complet_n_moins_1)]
        ca_total_mois_n_moins_1 = df_mois_complet_n_moins_1['montant'].sum()
        
        # Reste à faire
        reste_a_faire = ca_total_mois_n_moins_1 - cumul_mois_n
        
        # Nom du mois en français
        mois_fr_noms = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
        nom_mois_n_moins_1 = mois_fr_noms[mois_n_moins_1 - 1]
        
        if reste_a_faire > 0:
            st.info(
                f"🎯 **Objectif :** Pour atteindre le CA de **{nom_mois_n_moins_1} {annee_n_moins_1}** "
                f"({formater_euro(ca_total_mois_n_moins_1)}), il reste **{formater_euro(reste_a_faire)}** à faire."
            )
        else:
            depassement = abs(reste_a_faire)
            st.success(
                f"🎉 **Bravo !** Vous avez dépassé le CA de **{nom_mois_n_moins_1} {annee_n_moins_1}** "
                f"({formater_euro(ca_total_mois_n_moins_1)}) de **{formater_euro(depassement)}** !"
            )
        
        st.markdown("---")

        
        # ========== SECTION 3 : ANNUEL ==========
        st.subheader("📈 Comparaison Annuelle (Exercice)")
        
        exercice_actuel = calculer_exercice(date_n)
        annee_debut_exercice = int(exercice_actuel.split('/')[0])
        
        debut_exercice_n = datetime(annee_debut_exercice, 7, 1)
        df_exercice_n = df[(df['date'] >= debut_exercice_n) & (df['date'] <= date_n)]
        cumul_exercice_n = df_exercice_n['montant'].sum()
        
        # Même période exercice précédent (utilise date_n_moins_1 du calcul journalier)
        debut_exercice_n_moins_1 = datetime(annee_debut_exercice - 1, 7, 1)
        df_exercice_n_moins_1 = df[(df['date'] >= debut_exercice_n_moins_1) & (df['date'] <= date_n_moins_1)]
        cumul_exercice_n_moins_1 = df_exercice_n_moins_1['montant'].sum()
        
        nb_jours_exercice_n = (date_n - debut_exercice_n).days + 1
        nb_jours_exercice_n_moins_1 = (date_n_moins_1 - debut_exercice_n_moins_1).days + 1
        
        evolution_exercice_euro = cumul_exercice_n - cumul_exercice_n_moins_1
        evolution_exercice_pct = (evolution_exercice_euro / cumul_exercice_n_moins_1 * 100) if cumul_exercice_n_moins_1 != 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Cumul Année N-1", 
                formater_euro(cumul_exercice_n_moins_1),
                help=f"Du 1er juillet {annee_debut_exercice - 1} au {date_n_moins_1.strftime('%d/%m/%Y')} ({nb_jours_exercice_n_moins_1} jours)"
            )
        with col2:
            st.metric(
                "Cumul Année N", 
                formater_euro(cumul_exercice_n),
                help=f"Du 1er juillet {annee_debut_exercice} au {date_n.strftime('%d/%m/%Y')} ({nb_jours_exercice_n} jours)"
            )
        with col3:
            st.metric("Évolution €", formater_euro(evolution_exercice_euro))
        with col4:
            st.metric("Évolution %", f"{evolution_exercice_pct:+.1f}%")
        
        st.markdown("---")
        
        
       # ========== SECTION 4 : FORMULAIRE DE SAISIE ==========
        st.subheader("➕ Saisir une nouvelle entrée")
        
        with st.form("formulaire_saisie_accueil"):
            st.markdown("**📅 Date**")
            col_jour, col_mois, col_annee = st.columns(3)
            
            # Date du jour par défaut
            aujourd_hui = datetime.now()
            
            with col_jour:
                jour = st.selectbox(
                    "Jour",
                    options=list(range(1, 32)),
                    index=aujourd_hui.day - 1,
                    label_visibility="collapsed"
                )
            
            with col_mois:
                mois_fr = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                           'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
                mois = st.selectbox(
                    "Mois",
                    options=mois_fr,
                    index=aujourd_hui.month - 1,
                    label_visibility="collapsed"
                )
                mois_numero = mois_fr.index(mois) + 1
            
            with col_annee:
                annee = st.selectbox(
                    "Année",
                    options=list(range(2019, 2031)),
                    index=list(range(2019, 2031)).index(aujourd_hui.year),
                    label_visibility="collapsed"
                )
            
            # Construire la date
            try:
                date_saisie = datetime(annee, mois_numero, jour)
            except ValueError:
                # Si la date est invalide (ex: 31 février)
                st.error("⚠️ Date invalide")
                date_saisie = aujourd_hui
            
            st.markdown("**💰 Montant**")
            montant_saisie = st.number_input(
                "Montant (€)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                label_visibility="collapsed"
            )
            
            st.markdown("**👥 Nombre de collaborateurs**")
            nb_collaborateurs = st.selectbox(
                "Nombre de collaborateurs",
                options=[1, 2, 3, 4],
                index=1,  # Par défaut : 2 personnes (Patron + CDI)
                label_visibility="collapsed",
                help="1 = Patron seul | 2 = Patron + CDI | 3 = Patron + CDI + Stagiaire | 4 = Patron + CDI + 2 Stagiaires"
            )
            
            submit = st.form_submit_button("✅ Enregistrer", use_container_width=True)
            
            if submit:
                if montant_saisie >= 0:
                    succes, message = enregistrer_transaction(date_saisie, montant_saisie, nb_collaborateurs)
                    
                    if succes:
                        st.success(message)
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(message)
                        
        st.markdown("---")
        
        # Watermark
        afficher_watermark()



    # ==================== AUTRES PAGES ====================
    
    elif page == "📊 Suivi":
        st.title("📊 Suivi Mensuel par Exercice")
    
        # ========== SÉLECTION DE L'EXERCICE ==========
        exercices_disponibles = []
        annees = sorted(df['date'].dt.year.unique())
    
        for annee in annees:
            exercices_disponibles.append(f"{annee}/{annee + 1}")
    
        # Retirer les doublons et trier
        exercices_disponibles = sorted(list(set(exercices_disponibles)))
    
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
        
        # Mapper le nom du mois à son vrai numéro (1-12)
        mois_mapping = {
            'Juillet': 7, 'Août': 8, 'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
            'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 'Mai': 5, 'Juin': 6
        }
        mois_numero = mois_mapping[mois_selectionne]
    
        # Ajuster l'année du mois selon l'exercice
        if mois_numero >= 7:  # Juillet à Décembre
            annee_mois_n = annee_debut_exercice
        else:  # Janvier à Juin
            annee_mois_n = annee_debut_exercice + 1
    
        # Calculer l'année N-1
        annee_mois_n_moins_1 = annee_mois_n - 1
    
        # Nombre de jours dans le mois
        nb_jours_mois = calendar.monthrange(annee_mois_n, mois_numero)[1]
    
        # ========== CRÉATION DU TABLEAU ==========
        st.subheader(f"📋 {mois_selectionne} {annee_mois_n} vs {mois_selectionne} {annee_mois_n_moins_1}")
        
        # Bouton Export PDF (sera activé après calcul des données)
        placeholder_pdf_button = st.empty()
    
        # Créer les données du tableau
        donnees_tableau = []
    
        for jour in range(1, nb_jours_mois + 1):
            date_n = datetime(annee_mois_n, mois_numero, jour)
            jour_semaine = date_n.weekday()  # 0 = Lundi, 6 = Dimanche
        
            # Trouver la date N-1 correspondante (même jour de la semaine)
            # Chercher le même jour de la semaine dans l'année N-1
            date_reference_n_moins_1 = datetime(annee_mois_n_moins_1, mois_numero, jour)
            jours_diff = (jour_semaine - date_reference_n_moins_1.weekday()) % 7
        
            if jours_diff <= 3:
                date_n_moins_1 = date_reference_n_moins_1 + timedelta(days=jours_diff)
            else:
                date_n_moins_1 = date_reference_n_moins_1 - timedelta(days=7 - jours_diff)
        
            # Récupérer les montants et le nombre de collaborateurs
            data_n = df[df['date'] == date_n]
            montant_n = data_n['montant'].sum()
            nb_collab_n = data_n['nb_collaborateurs'].max() if not data_n.empty else 0
            
            data_n_moins_1 = df[df['date'] == date_n_moins_1]
            montant_n_moins_1 = data_n_moins_1['montant'].sum()
            nb_collab_n_moins_1 = data_n_moins_1['nb_collaborateurs'].max() if not data_n_moins_1.empty else 0
        
            # Noms des jours en français
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
    
        # Créer le DataFrame
        df_tableau = pd.DataFrame(donnees_tableau)
        
        # Calculer les totaux pour le PDF (avant l'affichage)
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
        
        # Bouton Export PDF avec le placeholder
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
        
        # Watermark
        afficher_watermark()
    
    elif page == "📈 Historique":
        # En-tête avec titre et bouton PDF
        col_titre, col_bouton = st.columns([3, 1])
        
        with col_titre:
            st.title("📈 Historique par Exercice")
        
        with col_bouton:
            # Bouton pour générer et télécharger le PDF
            if st.button("📄 Générer PDF", use_container_width=True, type="primary"):
                with st.spinner("Génération du PDF en cours..."):
                    # Générer le PDF
                    exercices_temp = sorted(df['exercice'].unique())
                    pdf_buffer = generer_pdf_historique(df, exercices_temp)
                    
                    # Téléchargement
                    st.download_button(
                        label="⬇️ Télécharger le PDF",
                        data=pdf_buffer,
                        file_name=f"historique_atelier_vincent_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF généré avec succès !")
        
        st.markdown("---")
        
        # ========== MAPPING DES JOURS EN FRANÇAIS ==========
        # La colonne jour_semaine existe déjà en anglais, on la mappe en français
        jours_en_fr = {
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
        }
        df['jour_semaine_fr'] = df['jour_semaine'].map(jours_en_fr)
        
        # Liste des exercices disponibles
        exercices = sorted(df['exercice'].unique())
        
        # ========== SECTION 1 : TABLEAU RÉCAPITULATIF PAR EXERCICE ==========
        st.subheader("📊 Statistiques par Exercice")
        
        stats_exercices = []
        
        for exercice in exercices:
            df_exercice = df[df['exercice'] == exercice]
            
            # CA Total
            ca_total = df_exercice['montant'].sum()
            
            # Moyenne de collaborateurs
            # On prend la moyenne des jours où il y a eu du CA
            df_avec_ca = df_exercice[df_exercice['montant'] > 0]
            if len(df_avec_ca) > 0:
                moyenne_collab = df_avec_ca['nb_collaborateurs'].mean()
            else:
                moyenne_collab = 0
            
            # Nombre de jours travaillés (jours avec CA > 0)
            nb_jours_travailles = len(df_avec_ca)
            
            # CA moyen journalier (sur jours travaillés uniquement)
            if nb_jours_travailles > 0:
                ca_moyen_jour = ca_total / nb_jours_travailles
            else:
                ca_moyen_jour = 0
            
            # CA moyen mensuel (CA total / 12 mois)
            ca_moyen_mois = ca_total / 12
            
            stats_exercices.append({
                'Exercice': exercice,
                'CA Total': formater_euro(ca_total),
                'Nb Jours Travaillés': nb_jours_travailles,
                'Moyenne Collaborateurs': f"{moyenne_collab:.1f}",
                'CA Moyen Mensuel': formater_euro(ca_moyen_mois),
                'CA Moyen Journalier': formater_euro(ca_moyen_jour)
            })
        
        # Afficher le tableau des stats
        df_stats = pd.DataFrame(stats_exercices)
        st.dataframe(df_stats, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # ========== SECTION 2 : TABLEAU DES MONTANTS MENSUELS PAR EXERCICE ==========
        st.subheader("📊 Montants Mensuels par Exercice")
        
        # Ordre des mois (juillet à juin pour correspondre à l'exercice fiscal)
        mois_ordre = ['Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
                      'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin']
        
        # Mapping nom du mois -> numéro du mois
        mois_mapping = {
            'Juillet': 7, 'Août': 8, 'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
            'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 'Mai': 5, 'Juin': 6
        }
        
        # Préparer les données
        monthly_data = []
        for exercice in exercices:
            if exercice >= '2019/2020':  # Filtrer à partir de 2019/2020
                row = {'Exercice': exercice}
                df_ex = df[df['exercice'] == exercice]
                
                for mois_nom in mois_ordre:
                    mois_num = mois_mapping[mois_nom]
                    montant = df_ex[df_ex['mois'] == mois_num]['montant'].sum()
                    row[mois_nom] = montant
                
                # Ajouter le total annuel
                row['Total'] = df_ex['montant'].sum()
                monthly_data.append(row)
        
        # Créer le DataFrame
        df_monthly = pd.DataFrame(monthly_data)
        
        # Ajouter une ligne "Moyenne" en bas
        moyenne_row = {'Exercice': 'Moyenne'}
        for mois in mois_ordre:
            moyenne_row[mois] = df_monthly[mois].mean()
        moyenne_row['Total'] = df_monthly['Total'].mean()
        df_monthly = pd.concat([df_monthly, pd.DataFrame([moyenne_row])], ignore_index=True)
        
        # Formater l'affichage
        def formater_montant(val):
            if isinstance(val, (int, float)):
                return f"{val:,.2f} €".replace(',', ' ')
            return val
        
        # Créer un dictionnaire de formatage pour toutes les colonnes sauf 'Exercice'
        format_dict = {col: formater_montant for col in df_monthly.columns if col != 'Exercice'}
        
        # Afficher le tableau avec formatage
        st.dataframe(
            df_monthly.style.format(format_dict).set_properties(**{
                'text-align': 'right'
            }, subset=[col for col in df_monthly.columns if col != 'Exercice']),
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        st.markdown("---")
        
        # ========== SECTION 3 : TABLEAU COMPARATIF PAR JOUR DE LA SEMAINE ==========
        st.subheader("📅 Tableau Comparatif par Jour de la Semaine")
        
        # Ordre des jours
        jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        # Créer un tableau avec tous les exercices côte à côte
        tableau_comparatif = {'Jour': jours_ordre}
        
        for exercice in exercices:
            df_exercice = df[df['exercice'] == exercice]
            
            ca_par_jour = []
            for jour in jours_ordre:
                df_jour = df_exercice[df_exercice['jour_semaine_fr'] == jour]
                ca_jour = df_jour['montant'].sum()
                ca_par_jour.append(formater_euro(ca_jour))
            
            tableau_comparatif[exercice] = ca_par_jour
        
        # Créer et afficher le DataFrame comparatif
        df_comparatif = pd.DataFrame(tableau_comparatif)
        st.dataframe(df_comparatif, hide_index=True, use_container_width=True, height=320)
        
        st.markdown("---")
        
        # ========== SECTION 4 : DÉTAILS PAR EXERCICE (OPTIONNEL) ==========
        with st.expander("📋 Voir les détails par exercice"):
            for exercice in exercices:
                st.markdown(f"#### Exercice {exercice}")
                
                df_exercice = df[df['exercice'] == exercice]
                
                # Calculer le CA cumulé par jour de la semaine
                ca_par_jour = []
                for jour in jours_ordre:
                    df_jour = df_exercice[df_exercice['jour_semaine_fr'] == jour]
                    ca_jour = df_jour['montant'].sum()
                    nb_occurrences = len(df_jour[df_jour['montant'] > 0])
                    
                    ca_par_jour.append({
                        'Jour': jour,
                        'CA Cumulé': formater_euro(ca_jour),
                        'Nb Jours': nb_occurrences
                    })
                
                # Afficher le tableau
                df_jours = pd.DataFrame(ca_par_jour)
                
                # Utiliser des colonnes pour un affichage plus compact
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.dataframe(
                        df_jours, 
                        hide_index=True, 
                        use_container_width=True,
                        height=280
                    )
                
                with col2:
                    # Afficher le total de l'exercice
                    total_exercice = df_exercice['montant'].sum()
                    st.metric("Total Exercice", formater_euro(total_exercice))
                    
                    # Meilleur jour
                    ca_valeurs = []
                    for row in ca_par_jour:
                        ca_str = row['CA Cumulé'].replace(' €', '').replace(',', '.').replace(' ', '')
                        ca_valeurs.append(float(ca_str))
                    
                    if ca_valeurs and max(ca_valeurs) > 0:
                        idx_max = ca_valeurs.index(max(ca_valeurs))
                        meilleur_jour = ca_par_jour[idx_max]['Jour']
                        meilleur_ca = ca_par_jour[idx_max]['CA Cumulé']
                        
                        st.info(f"🏆 Meilleur jour : **{meilleur_jour}**\n\n{meilleur_ca}")
                
                st.markdown("---")
        
        # Watermark
        afficher_watermark()
    
    elif page == "🔮 Prévisions":
        st.title("🔮 Prévisions et Objectifs")
        
        # ========== CONFIGURATION DE L'EXERCICE ==========
        # Détecter automatiquement les exercices disponibles dans les données
        exercices_disponibles = sorted(df['exercice'].unique().tolist(), reverse=True)
        
        # Ajouter l'exercice futur s'il n'est pas encore dans les données
        exercice_futur = f"{datetime.now().year}/{datetime.now().year + 1}" if datetime.now().month >= 7 else f"{datetime.now().year - 1}/{datetime.now().year}"
        if exercice_futur not in exercices_disponibles:
            exercices_disponibles.insert(0, exercice_futur)
        
        col_cfg1, col_cfg2 = st.columns([1, 2])
        
        with col_cfg1:
            exercice_actuel = st.selectbox(
                "📅 Exercice",
                options=exercices_disponibles,
                index=0,
                help="Sélectionnez l'exercice fiscal à analyser"
            )
        
        with col_cfg2:
            objectif_annuel = st.number_input(
                "🎯 Objectif annuel (€)",
                min_value=0,
                max_value=500000,
                value=157000,
                step=1000,
                help="Modifiez l'objectif de CA annuel pour cet exercice"
            )
        
        st.markdown("---")
        
        # Calculer les dates de début et fin de l'exercice
        annee_debut = int(exercice_actuel.split('/')[0])
        debut_exercice = datetime(annee_debut, 7, 1)
        fin_exercice = datetime(annee_debut + 1, 6, 30)
        
        # Date de référence :
        # - exercice passé (fin_exercice < aujourd'hui) -> 30 juin de cet exercice
        # - exercice en cours/futur -> aujourd'hui (sans brider par derniere_date)
        aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if aujourd_hui > fin_exercice:
            date_actuelle = fin_exercice
        else:
            date_actuelle = max(aujourd_hui, debut_exercice)
        
        # Filtrer les données de l'exercice sélectionné (borné par début ET fin d'exercice)
        df_exercice = df[(df['date'] >= debut_exercice) & (df['date'] <= min(date_actuelle, fin_exercice))]
        ca_actuel = df_exercice['montant'].sum()
        
        # Calculer les jours écoulés et restants
        jours_ecoules = (date_actuelle - debut_exercice).days + 1
        jours_totaux_exercice = (fin_exercice - debut_exercice).days + 1
        jours_restants = jours_totaux_exercice - jours_ecoules
        
        # Calculer les jours travaillés (jours avec CA > 0)
        jours_travailles = len(df_exercice[df_exercice['montant'] > 0])
        
        # ========== SECTION 1 : VUE D'ENSEMBLE ==========
        st.subheader(f"📊 Exercice {exercice_actuel} - Vue d'ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🎯 Objectif Annuel",
                formater_euro(objectif_annuel),
                help=f"Objectif annuel pour l'exercice {exercice_actuel}"
            )
        
        with col2:
            st.metric(
                "💰 CA Actuel",
                formater_euro(ca_actuel),
                f"{(ca_actuel / objectif_annuel * 100):.1f}% atteint"
            )
        
        with col3:
            st.metric(
                "📅 Jours Écoulés",
                f"{jours_ecoules} / {jours_totaux_exercice}",
                f"{(jours_ecoules / jours_totaux_exercice * 100):.1f}% de l'année"
            )
        
        with col4:
            reste_a_faire = objectif_annuel - ca_actuel
            st.metric(
                "🎯 Reste à Faire",
                formater_euro(reste_a_faire) if reste_a_faire > 0 else "Objectif atteint ! 🎉",
                f"{jours_restants} jours restants"
            )
        
        st.markdown("---")
        
        # ========== SECTION 2 : PROJECTION ==========
        st.subheader("📈 Projection de Fin d'Exercice")
        
        # Calculer le CA moyen journalier (sur jours travaillés)
        ca_moyen_jour = ca_actuel / jours_travailles if jours_travailles > 0 else 0
        
        # Estimer le nombre de jours travaillés restants (environ 80% des jours calendaires)
        jours_travailles_restants_estimes = int(jours_restants * (jours_travailles / jours_ecoules))
        
        # Projection basée sur la tendance actuelle
        projection_ca = ca_actuel + (ca_moyen_jour * jours_travailles_restants_estimes)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "📊 CA Moyen par Jour Travaillé",
                formater_euro(ca_moyen_jour),
                f"{jours_travailles} jours travaillés"
            )
            
            st.metric(
                "🔮 Projection Fin d'Exercice",
                formater_euro(projection_ca),
                f"{((projection_ca - objectif_annuel) / objectif_annuel * 100):+.1f}% vs objectif"
            )
        
        with col2:
            # Graphique de projection
            fig_projection = {
                "data": [
                    {
                        "type": "indicator",
                        "mode": "gauge+number+delta",
                        "value": projection_ca,
                        "domain": {"x": [0, 1], "y": [0, 1]},
                        "title": {"text": "<b>Projection vs Objectif</b>", "font": {"size": 14}},
                        "delta": {"reference": objectif_annuel, "valueformat": ",.0f", "suffix": " €"},
                        "number": {"valueformat": ",.0f", "suffix": " €", "font": {"size": 24}},
                        "gauge": {
                            "axis": {"range": [None, objectif_annuel * 1.1], "tickformat": ",.0f"},
                            "bar": {"color": "#3498DB"},
                            "steps": [
                                {"range": [0, objectif_annuel], "color": "#E5E5E5"}
                            ],
                            "threshold": {
                                "line": {"color": "#A89332", "width": 4},
                                "thickness": 0.75,
                                "value": objectif_annuel
                            }
                        }
                    }
                ],
                "layout": {
                    "margin": {"t": 50, "b": 20, "l": 20, "r": 20},
                    "height": 300
                }
            }
            
            st.plotly_chart(fig_projection, use_container_width=True, config={'displayModeBar': False})
        
        # Message selon projection
        if projection_ca >= objectif_annuel:
            ecart_projection = projection_ca - objectif_annuel
            st.success(f"🎉 **Excellente nouvelle !** Si vous maintenez ce rythme, vous dépasserez votre objectif de **{formater_euro(ecart_projection)}** !")
        else:
            manque_projection = objectif_annuel - projection_ca
            st.warning(f"⚠️ **Attention :** Au rythme actuel, vous seriez à **{formater_euro(manque_projection)}** de votre objectif. Il faudra accélérer !")
        
        st.markdown("---")
        
        # ========== SECTION 3 : SIMULATEUR ==========
        st.subheader("🎮 Simulateur d'Objectifs")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**💡 Si je fais X€ par jour de travail, quel sera mon CA annuel ?**")
            
            ca_simule_jour = st.number_input(
                "CA journalier simulé (€)",
                min_value=0.0,
                max_value=1000.0,
                value=ca_moyen_jour,
                step=10.0,
                help="Modifiez ce montant pour voir l'impact"
            )
            
            # Estimation du nombre de jours travaillés total pour l'exercice
            taux_jours_travailles = jours_travailles / jours_ecoules if jours_ecoules > 0 else 0.7
            jours_travailles_total_estimes = int(jours_totaux_exercice * taux_jours_travailles)
            
            ca_annuel_simule = ca_simule_jour * jours_travailles_total_estimes
            
            st.metric(
                "🎯 CA Annuel Projeté",
                formater_euro(ca_annuel_simule),
                f"{((ca_annuel_simule - objectif_annuel) / objectif_annuel * 100):+.1f}% vs objectif"
            )
            
            st.info(f"📅 Basé sur environ **{jours_travailles_total_estimes} jours travaillés** dans l'année")
        
        with col2:
            # Graphique comparatif
            scenarios = pd.DataFrame({
                'Scénario': ['Rythme actuel', 'Scénario simulé', 'Objectif'],
                'CA': [projection_ca, ca_annuel_simule, objectif_annuel],
                'Type': ['Projection', 'Simulation', 'Objectif']
            })
            
            fig_scenarios = px.bar(
                scenarios,
                x='Scénario',
                y='CA',
                color='Type',
                color_discrete_map={
                    'Projection': '#3498DB',
                    'Simulation': '#9B59B6',
                    'Objectif': '#A89332'
                },
                text='CA',
                title="Comparaison des Scénarios"
            )
            
            fig_scenarios.update_traces(
                texttemplate='%{text:,.0f}€',
                textposition='outside'
            )
            
            fig_scenarios.update_layout(
                showlegend=False,
                height=350,
                yaxis_title="CA Annuel (€)",
                yaxis_tickformat=",.0f",
                xaxis_title=""
            )
            
            st.plotly_chart(fig_scenarios, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("---")
        
        # ========== SECTION 4 : OBJECTIFS MENSUELS ==========
        st.subheader("📅 Objectifs Mensuels Personnalisés")
        
        # Calculer la somme des objectifs mensuels personnalisés
        total_objectifs_mensuels = sum(OBJECTIFS_MENSUELS.values())
        
        st.markdown(f"""
        Pour atteindre votre objectif de **{formater_euro(objectif_annuel)}** :
        - 🎯 Total des objectifs mensuels : **{formater_euro(total_objectifs_mensuels)}**
        - 📊 CA journalier nécessaire : **{formater_euro(objectif_annuel / jours_travailles_total_estimes)}** (sur {jours_travailles_total_estimes} jours travaillés estimés)
        """)
        
        # Tableau des objectifs mensuels
        mois_ordre = ['Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
                      'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin']
        
        mois_mapping = {
            'Juillet': 7, 'Août': 8, 'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
            'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 'Mai': 5, 'Juin': 6
        }
        
        objectifs_data = []
        for mois_nom in mois_ordre:
            mois_num = mois_mapping[mois_nom]
            
            # Récupérer l'objectif personnalisé pour ce mois
            objectif_mois_perso = OBJECTIFS_MENSUELS[mois_nom]
            
            # Ajuster l'année selon le mois
            if mois_num >= 7:
                annee_mois = annee_debut
            else:
                annee_mois = annee_debut + 1
            
            # CA réalisé pour ce mois
            debut_mois = datetime(annee_mois, mois_num, 1)
            dernier_jour_mois = calendar.monthrange(annee_mois, mois_num)[1]
            fin_mois = datetime(annee_mois, mois_num, dernier_jour_mois)
            
            df_mois = df[(df['date'] >= debut_mois) & (df['date'] <= fin_mois)]
            ca_mois = df_mois['montant'].sum()
            
            # Statut
            if fin_mois < date_actuelle:
                statut = "✅ Terminé"
                ecart = ca_mois - objectif_mois_perso
                ecart_str = f"{formater_euro(ecart)}" if ecart >= 0 else f"{formater_euro(ecart)}"
            elif debut_mois > date_actuelle:
                statut = "⏳ À venir"
                ecart_str = "-"
            else:
                statut = "🔄 En cours"
                ecart = ca_mois - objectif_mois_perso
                ecart_str = f"{formater_euro(ecart)}" if ecart >= 0 else f"{formater_euro(ecart)}"
            
            objectifs_data.append({
                'Mois': mois_nom,
                'Objectif': formater_euro(objectif_mois_perso),
                'Réalisé': formater_euro(ca_mois) if ca_mois > 0 else "-",
                'Écart': ecart_str,
                'Statut': statut
            })
        
        # Calculer les totaux UNIQUEMENT pour les mois écoulés ou en cours
        total_objectif_ecoule = 0
        total_realise_ecoule = 0
        
        for mois_nom in mois_ordre:
            mois_num = mois_mapping[mois_nom]
            if mois_num >= 7:
                annee_mois = annee_debut
            else:
                annee_mois = annee_debut + 1
            
            debut_mois = datetime(annee_mois, mois_num, 1)
            dernier_jour_mois = calendar.monthrange(annee_mois, mois_num)[1]
            fin_mois = datetime(annee_mois, mois_num, dernier_jour_mois)
            
            # Ne compter que les mois dont la fin est <= date actuelle
            if fin_mois <= date_actuelle:
                # Mois terminé
                total_objectif_ecoule += OBJECTIFS_MENSUELS[mois_nom]
                df_mois = df[(df['date'] >= debut_mois) & (df['date'] <= fin_mois)]
                total_realise_ecoule += df_mois['montant'].sum()
            elif debut_mois <= date_actuelle < fin_mois:
                # Mois en cours
                total_objectif_ecoule += OBJECTIFS_MENSUELS[mois_nom]
                df_mois = df[(df['date'] >= debut_mois) & (df['date'] <= date_actuelle)]
                total_realise_ecoule += df_mois['montant'].sum()
            # Sinon, mois futur : on ne compte pas
        
        total_ecart = total_realise_ecoule - total_objectif_ecoule
        
        # Ajouter la ligne de TOTAL (mois écoulés/en cours uniquement)
        objectifs_data.append({
            'Mois': '💰 TOTAL (en cours)',
            'Objectif': formater_euro(total_objectif_ecoule),
            'Réalisé': formater_euro(total_realise_ecoule),
            'Écart': formater_euro(total_ecart),
            'Statut': '✅' if total_ecart >= 0 else '⚠️'
        })
        
        df_objectifs = pd.DataFrame(objectifs_data)
        st.dataframe(df_objectifs, hide_index=True, use_container_width=True, height=550)
        
        # Note explicative
        st.info("""
        ℹ️ **Note :** Le total affiché ne prend en compte que les mois **écoulés et en cours**. 
        Les mois futurs ne sont pas inclus dans le calcul de l'écart.
        """)
        
        # ========== CALCUL DE PRIME ==========
        if total_ecart > 0:
            st.markdown("---")
            st.subheader("🎁 Calcul de Prime Salarié")
            
            st.success(f"""
            🎉 **Super performance !** 
            
            Sur les mois écoulés/en cours, vous avez un écart positif de **{formater_euro(total_ecart)}** par rapport aux objectifs.
            """)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("### 💡 Paramètres de Prime")
                
                # Pourcentage de l'écart à distribuer
                pourcentage_prime = st.slider(
                    "% de l'écart positif à distribuer en prime",
                    min_value=0,
                    max_value=100,
                    value=30,
                    step=5,
                    help="Quel pourcentage de l'écart souhaitez-vous redistribuer ?"
                )
                
                montant_distribuable = total_ecart * (pourcentage_prime / 100)
                
                st.metric(
                    "Montant distribuable",
                    formater_euro(montant_distribuable),
                    help="Montant disponible avant charges"
                )
            
            with col2:
                st.markdown("### 💰 Calcul de la Prime Brute")
                
                # En France : charges patronales ≈ 42% du salaire brut
                taux_charges_patronales = 0.42
                
                # Montant brut = Montant distribuable / (1 + charges patronales)
                prime_brute = montant_distribuable / (1 + taux_charges_patronales)
                
                # Coût total pour l'entreprise
                cout_total = prime_brute * (1 + taux_charges_patronales)
                
                # Prime nette approximative (charges salariales ≈ 22%)
                taux_charges_salariales = 0.22
                prime_nette_approx = prime_brute * (1 - taux_charges_salariales)
                
                st.metric(
                    "🎯 Prime Brute Salarié",
                    formater_euro(prime_brute),
                    help="Montant brut à verser au salarié"
                )
                
                st.metric(
                    "💵 Prime Nette (approx.)",
                    formater_euro(prime_nette_approx),
                    help="Montant net approximatif que recevra le salarié (après charges salariales ~22%)"
                )
                
                st.metric(
                    "💼 Coût Total Entreprise",
                    formater_euro(cout_total),
                    help="Coût total incluant charges patronales (~42%)"
                )
            
            # Tableau récapitulatif
            st.markdown("---")
            st.markdown("#### 📊 Récapitulatif")
            
            recap_data = {
                'Étape': [
                    '1️⃣ Écart positif total',
                    f'2️⃣ Part distribuée ({pourcentage_prime}%)',
                    '3️⃣ Prime brute salarié',
                    '4️⃣ Charges patronales (~42%)',
                    '5️⃣ Coût total entreprise',
                    '6️⃣ Prime nette salarié (~78%)'
                ],
                'Montant': [
                    formater_euro(total_ecart),
                    formater_euro(montant_distribuable),
                    formater_euro(prime_brute),
                    formater_euro(prime_brute * taux_charges_patronales),
                    formater_euro(cout_total),
                    formater_euro(prime_nette_approx)
                ]
            }
            
            df_recap = pd.DataFrame(recap_data)
            st.dataframe(df_recap, hide_index=True, use_container_width=True)
            
            st.info("""
            💡 **Notes importantes :**
            - Les taux de charges (42% patronales, 22% salariales) sont des estimations moyennes
            - Les charges réelles dépendent du statut, de la convention collective et du montant
            - Pour les montants exacts, consultez votre expert-comptable ou gestionnaire de paie
            - Cette prime peut être versée sous forme de prime exceptionnelle ou de prime sur objectifs
            """)
        else:
            st.markdown("---")
            st.info(f"""
            ℹ️ **Pas de prime disponible pour le moment**
            
            Sur les mois écoulés/en cours, l'écart par rapport aux objectifs est de **{formater_euro(total_ecart)}**. 
            Continuez vos efforts pour atteindre les objectifs et générer un écart positif !
            """)
        
        st.markdown("---")
        
        # ========== SECTION 5 : CONSEILS ==========
        st.subheader("💡 Conseils pour Atteindre l'Objectif")
        
        ca_necessaire_jour = (objectif_annuel - ca_actuel) / jours_travailles_restants_estimes if jours_travailles_restants_estimes > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"""
            **📊 Performance Actuelle**
            - CA/jour : {formater_euro(ca_moyen_jour)}
            - {jours_travailles} jours travaillés
            """)
        
        with col2:
            st.warning(f"""
            **🎯 Cible Nécessaire**
            - CA/jour : {formater_euro(ca_necessaire_jour)}
            - {jours_travailles_restants_estimes} jours restants estimés
            """)
        
        with col3:
            ecart_jour = ca_necessaire_jour - ca_moyen_jour
            if ecart_jour > 0:
                st.error(f"""
                **⚡ Effort Supplémentaire**
                - +{formater_euro(ecart_jour)}/jour
                - soit +{((ecart_jour / ca_moyen_jour * 100)):.1f}%
                """)
            else:
                st.success(f"""
                **🎉 Vous êtes au-dessus !**
                - Maintenir le rythme actuel
                - Objectif en vue !
                """)
        
        # Watermark
        afficher_watermark()
    
    elif page == "💰 Calculateur Financier":
        st.title("💰 Calculateur Financier")
        
        # Charger et afficher le calculateur HTML
        try:
            # Lire le fichier HTML
            with open('Calculateur_Salon.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Afficher le HTML dans un iframe
            import streamlit.components.v1 as components
            components.html(html_content, height=1200, scrolling=True)
            
        except FileNotFoundError:
            st.error("❌ Fichier Calculateur_Salon.html introuvable")
            st.info("💡 Assurez-vous que le fichier Calculateur_Salon.html est présent à la racine de votre application")
        
        # Watermark
        afficher_watermark()
    
    elif page == "⚙️ Données brutes":
        st.title("⚙️ Données brutes")
        st.dataframe(df, use_container_width=True)
        
        # Watermark
        afficher_watermark()

else:
    st.error("❌ Impossible de charger les données depuis Google Sheets")
    st.info("💡 Vérifiez que les secrets sont bien configurés dans Streamlit Cloud")

