"""
🎯 L'ATELIER DE VINCENT - Application de Gestion CA
Application web créée avec Streamlit pour remplacer votre Excel

Auteur : Vincent
Date : Décembre 2024
"""

# ==================== IMPORTS ====================
# Ces lignes importent les bibliothèques nécessaires

import streamlit as st          # Pour créer l'interface web
import pandas as pd             # Pour manipuler les données (comme Excel)
import plotly.express as px     # Pour créer des graphiques interactifs
from datetime import datetime, timedelta
import os

# ==================== CONFIGURATION ====================
# Configuration de la page web

st.set_page_config(
    page_title="L'Atelier de Vincent",
    page_icon="📊",
    layout="wide",  # Utilise toute la largeur de l'écran
    initial_sidebar_state="expanded"
)

# ==================== FONCTIONS UTILES ====================

@st.cache_data  # Cette ligne met les données en cache pour aller plus vite
def charger_donnees(fichier_excel):
    """
    Charge les données depuis votre fichier Excel
    Équivalent à : ouvrir votre fichier Excel et lire la feuille "Données"
    """
    try:
        # Lire la feuille "Données"
        df = pd.read_excel(fichier_excel, sheet_name="Données")
        
        # Convertir la colonne C en date (si elle existe)
        if 'C' in df.columns:
            # Convertir en date avec gestion d'erreurs (ignore les dates invalides)
            df['date'] = pd.to_datetime(df['C'], errors='coerce')
            # Supprimer les lignes avec des dates invalides
            df = df.dropna(subset=['date'])
        
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        return None

def calculer_exercice(date):
    """
    Calcule l'exercice fiscal (juillet à juin)
    Exemple : 15/08/2024 → exercice 2024/2025
    """
    if date.month >= 7:  # Si on est après juillet
        return f"{date.year}/{date.year + 1}"
    else:
        return f"{date.year - 1}/{date.year}"

def formater_euro(montant):
    """
    Formate un nombre en euros français
    Exemple : 1500.5 → 1 500,50 €
    """
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")

# ==================== SIDEBAR (MENU LATÉRAL) ====================

st.sidebar.title("📊 L'Atelier de Vincent")
st.sidebar.markdown("---")

# Sélection du fichier Excel
fichier_excel = st.sidebar.text_input(
    "📁 Chemin du fichier Excel",
    value="CA_Atelier_Vincent_B2C2_vers_D4E4.xlsm",
    help="Entrez le chemin complet de votre fichier Excel"
)

# Menu de navigation
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "📊 Dashboard", "📈 Historique", "➕ Saisie", "⚙️ Données brutes"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Application créée pour gérer votre chiffre d'affaires")

# ==================== CHARGEMENT DES DONNÉES ====================

if os.path.exists(fichier_excel):
    df = charger_donnees(fichier_excel)
    
    if df is not None and not df.empty:
        # Préparer les données
        # Identifier les colonnes date et montant
        
        # Si les colonnes n'ont pas de noms clairs, on utilise les index
        if 'date' not in df.columns:
            # Trouver la colonne de dates (colonne C = index 2)
            if len(df.columns) > 2:
                df['date'] = pd.to_datetime(df.iloc[:, 2], errors='coerce')
        
        if 'montant' not in df.columns:
            # Trouver la colonne des montants (colonne F = index 5)
            if len(df.columns) > 5:
                df['montant'] = pd.to_numeric(df.iloc[:, 5], errors='coerce')
        
        # Supprimer les lignes sans date ou sans montant valide
        df = df.dropna(subset=['date', 'montant'])
        
        # Ne garder que les lignes avec montant > 0
        df = df[df['montant'] > 0]
        
        # Ajouter la colonne exercice
        df['exercice'] = df['date'].apply(calculer_exercice)
        df['annee'] = df['date'].dt.year
        df['mois'] = df['date'].dt.month
        df['jour_semaine'] = df['date'].dt.day_name()
        
else:
    st.error(f"❌ Fichier non trouvé : {fichier_excel}")
    st.stop()

# ==================== PAGE ACCUEIL ====================

if page == "🏠 Accueil":
    st.title("🏠 Bienvenue dans L'Atelier de Vincent")
    
    st.markdown("""
    ### 👋 Bonjour Vincent !
    
    Cette application web remplace votre tableau Excel et vous offre :
    
    - 📊 **Dashboard** : Vue d'ensemble de votre activité
    - 📈 **Historique** : Évolution de votre CA sur plusieurs exercices
    - ➕ **Saisie** : Ajouter facilement de nouvelles données
    - ⚙️ **Données brutes** : Consulter et filtrer vos données
    
    ### 🎯 Statistiques rapides
    """)
    
    # KPIs rapides
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total transactions", len(df))
    
    with col2:
        ca_total = df['montant'].sum()
        st.metric("CA Total", formater_euro(ca_total))
    
    with col3:
        exercice_actuel = calculer_exercice(datetime.now())
        df_exercice = df[df['exercice'] == exercice_actuel]
        ca_exercice = df_exercice['montant'].sum()
        st.metric(f"CA {exercice_actuel}", formater_euro(ca_exercice))
    
    with col4:
        nb_jours = df['date'].nunique()
        moyenne_jour = ca_total / nb_jours if nb_jours > 0 else 0
        st.metric("Moyenne/jour", formater_euro(moyenne_jour))
    
    st.markdown("---")
    st.info("👈 Utilisez le menu à gauche pour naviguer")

# ==================== PAGE DASHBOARD ====================

elif page == "📊 Dashboard":
    st.title("📊 Dashboard de l'activité")
    
    # Sélection de l'exercice
    exercices = sorted(df['exercice'].unique(), reverse=True)
    exercice_selectionne = st.selectbox("Sélectionnez un exercice", exercices)
    
    # Filtrer sur l'exercice sélectionné
    df_exercice = df[df['exercice'] == exercice_selectionne]
    
    # KPIs principaux
    st.subheader(f"📈 Exercice {exercice_selectionne}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ca_total = df_exercice['montant'].sum()
        st.metric("CA Total", formater_euro(ca_total))
    
    with col2:
        nb_jours = len(df_exercice)
        st.metric("Jours travaillés", nb_jours)
    
    with col3:
        moyenne_jour = ca_total / nb_jours if nb_jours > 0 else 0
        st.metric("Moyenne/jour", formater_euro(moyenne_jour))
    
    with col4:
        moyenne_mois = ca_total / 12
        st.metric("Moyenne mensuelle", formater_euro(moyenne_mois))
    
    st.markdown("---")
    
    # Graphiques
    col_gauche, col_droite = st.columns(2)
    
    with col_gauche:
        st.subheader("📊 CA par mois")
        # Grouper par mois
        df_mois = df_exercice.groupby(df_exercice['date'].dt.to_period('M'))['montant'].sum().reset_index()
        df_mois['date'] = df_mois['date'].astype(str)
        
        fig_mois = px.bar(df_mois, x='date', y='montant', 
                          title="Chiffre d'affaires mensuel",
                          labels={'montant': 'CA (€)', 'date': 'Mois'})
        st.plotly_chart(fig_mois, use_container_width=True)
    
    with col_droite:
        st.subheader("📈 Évolution du CA")
        # Cumul progressif
        df_cumul = df_exercice.sort_values('date').copy()
        df_cumul['ca_cumule'] = df_cumul['montant'].cumsum()
        
        fig_cumul = px.line(df_cumul, x='date', y='ca_cumule',
                           title="CA cumulé sur l'exercice",
                           labels={'ca_cumule': 'CA cumulé (€)', 'date': 'Date'})
        st.plotly_chart(fig_cumul, use_container_width=True)
    
    # Tableau des meilleures performances
    st.subheader("🏆 Top 10 des meilleures journées")
    top10 = df_exercice.nlargest(10, 'montant')[['date', 'montant']].copy()
    top10['montant'] = top10['montant'].apply(formater_euro)
    st.dataframe(top10, hide_index=True, use_container_width=True)

# ==================== PAGE HISTORIQUE ====================

elif page == "📈 Historique":
    st.title("📈 Évolution historique du CA")
    
    # Calculer le tableau historique (comme votre tableau Excel F33:J43)
    historique = df.groupby('exercice').agg({
        'montant': ['sum', 'count']
    }).reset_index()
    
    historique.columns = ['Exercice', 'CA Total', 'Nb jours']
    historique['Moy. Mens.'] = historique['CA Total'] / 12
    historique['Moy. Jour'] = historique['CA Total'] / historique['Nb jours']
    
    # Calculer les évolutions
    historique['Évolution €'] = historique['CA Total'].diff()
    historique['Évol. %'] = historique['CA Total'].pct_change() * 100
    
    # Afficher le tableau
    st.subheader("📊 Tableau récapitulatif")
    
    # Formater pour l'affichage
    historique_affichage = historique.copy()
    historique_affichage['CA Total'] = historique_affichage['CA Total'].apply(formater_euro)
    historique_affichage['Moy. Mens.'] = historique_affichage['Moy. Mens.'].apply(formater_euro)
    historique_affichage['Moy. Jour'] = historique_affichage['Moy. Jour'].apply(formater_euro)
    historique_affichage['Évolution €'] = historique_affichage['Évolution €'].apply(
        lambda x: formater_euro(x) if pd.notna(x) else "-"
    )
    historique_affichage['Évol. %'] = historique_affichage['Évol. %'].apply(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
    )
    
    st.dataframe(historique_affichage, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # Graphique d'évolution
    st.subheader("📈 Graphique d'évolution")
    
    fig_histo = px.bar(historique, x='Exercice', y='CA Total',
                       title="Évolution du CA par exercice",
                       text='CA Total')
    fig_histo.update_traces(texttemplate='%{text:,.0f} €', textposition='outside')
    st.plotly_chart(fig_histo, use_container_width=True)
    
    # Ajouter les annotations COVID si applicable
    exercices_covid = ['2019/2020', '2020/2021']
    if any(ex in historique['Exercice'].values for ex in exercices_covid):
        st.warning("⚠️ Il faut prendre en compte l'impact du confinement lié au Covid-19 pour les exercices 2019/2020 et 2020/2021.")

# ==================== PAGE SAISIE ====================

elif page == "➕ Saisie":
    st.title("➕ Saisir une nouvelle transaction")
    
    st.markdown("""
    Utilisez ce formulaire pour ajouter une nouvelle entrée de CA.
    Les données seront ajoutées à votre fichier Excel.
    """)
    
    with st.form("formulaire_saisie"):
        col1, col2 = st.columns(2)
        
        with col1:
            date_saisie = st.date_input(
                "📅 Date",
                value=datetime.now(),
                format="DD/MM/YYYY"
            )
        
        with col2:
            montant_saisie = st.number_input(
                "💰 Montant (€)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f"
            )
        
        notes = st.text_area("📝 Notes (optionnel)", placeholder="Détails de la transaction...")
        
        submit = st.form_submit_button("✅ Enregistrer", use_container_width=True)
        
        if submit:
            if montant_saisie > 0:
                st.success(f"✅ Transaction enregistrée : {formater_euro(montant_saisie)} le {date_saisie.strftime('%d/%m/%Y')}")
                st.info("💡 Note : Dans cette version de démonstration, les données ne sont pas encore sauvegardées dans Excel. Cette fonctionnalité sera ajoutée prochainement.")
            else:
                st.error("❌ Le montant doit être supérieur à 0 €")

# ==================== PAGE DONNÉES BRUTES ====================

elif page == "⚙️ Données brutes":
    st.title("⚙️ Données brutes")
    
    st.markdown("Consultez et filtrez toutes vos données ici.")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exercices_filtre = st.multiselect(
            "Exercice(s)",
            options=sorted(df['exercice'].unique()),
            default=[]
        )
    
    with col2:
        annees_filtre = st.multiselect(
            "Année(s)",
            options=sorted(df['annee'].unique()),
            default=[]
        )
    
    with col3:
        montant_min = st.number_input("Montant minimum", value=0.0)
    
    # Appliquer les filtres
    df_filtre = df.copy()
    
    if exercices_filtre:
        df_filtre = df_filtre[df_filtre['exercice'].isin(exercices_filtre)]
    
    if annees_filtre:
        df_filtre = df_filtre[df_filtre['annee'].isin(annees_filtre)]
    
    if montant_min > 0:
        df_filtre = df_filtre[df_filtre['montant'] >= montant_min]
    
    # Afficher les résultats
    st.subheader(f"📊 {len(df_filtre)} transactions trouvées")
    
    # Statistiques rapides
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", formater_euro(df_filtre['montant'].sum()))
    with col2:
        st.metric("Moyenne", formater_euro(df_filtre['montant'].mean()))
    with col3:
        st.metric("Maximum", formater_euro(df_filtre['montant'].max()))
    
    # Tableau
    st.dataframe(
        df_filtre[['date', 'exercice', 'montant']].sort_values('date', ascending=False),
        hide_index=True,
        use_container_width=True
    )
    
    # Bouton de téléchargement
    csv = df_filtre.to_csv(index=False)
    st.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name=f"export_ca_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ==================== FOOTER ====================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        L'Atelier de Vincent - Gestion CA © 2024 | 
        Créé avec ❤️ par Vincent
    </div>
    """,
    unsafe_allow_html=True
)
