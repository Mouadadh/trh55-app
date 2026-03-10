import streamlit as st
import pandas as pd
import pickle
import os
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
import datetime
from PIL import Image as PILImage

# Configuration page
st.set_page_config(page_title="Documents - TRH 55", layout="wide")

# ✅ LOGO INTÉGRÉ DIRECTEMENT (fichier local logo.png)
LOGO_PATH = "logo.png"

# Vérifier que le fichier existe
if not os.path.exists(LOGO_PATH):
    st.error(f"❌ Fichier {LOGO_PATH} introuvable dans le dossier !")
    st.stop()

# Info entreprise
ENTREPRISE = "TRH 55"
ADRESSE_ENTREPRISE = "77 Rue Mohamed Smiha Eth 10 N°57\nCasablanca, Maroc"
TELEPHONE = "+212 661 04 90 34"
ICE = "003927010000072"
CLIENTS_FILE = "clients_trh55.pkl"
NUM_FILE_FACTURE = "numeros_facture.json"
NUM_FILE_LIVRAISON = "numeros_livraison.json"

def format_montant(montant):
    """Formate les montants avec espaces : 20 000,00 Dhs"""
    return f"{montant:,.2f}".replace(',', ' ').replace('.', ',') + " Dhs"

UNITES = ["unité", "forfait", "cm", "m", "m²", "pièce"]

def nombre_en_lettres(n):
    """Convertit un nombre en lettres (français marocain : dirhams + centimes)"""
    if n == 0:
        return "zéro dirhams"
    
    unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    dizaines = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
    
    def convert_centaines(num):
        if num == 0:
            return ""
        elif num < 10:
            return unites[num]
        elif num == 10:
            return "dix"
        elif num == 11:
            return "onze"
        elif num == 12:
            return "douze"
        elif num == 13:
            return "treize"
        elif num == 14:
            return "quatorze"
        elif num == 15:
            return "quinze"
        elif num == 16:
            return "seize"
        elif num < 20:
            return "dix-" + unites[num - 10]
        elif num == 71:
            return "soixante et onze"
        elif num < 80 and num > 70:
            return "soixante-" + unites[num - 70] if num != 71 else "soixante et onze"
        elif num == 80:
            return "quatre-vingts"
        elif num < 90 and num > 80:
            return "quatre-vingt-" + unites[num - 80]
        elif num < 100:
            d = num // 10
            u = num % 10
            if u == 1 and d != 8 and d != 9:
                return dizaines[d] + " et un"
            elif u == 0:
                result = dizaines[d]
                return result + "s" if d == 8 else result
            else:
                return dizaines[d] + "-" + unites[u]
        else:
            c = num // 100
            reste = num % 100
            centaine = "cent" if c == 1 else unites[c] + " cent"
            if reste == 0:
                return centaine + "s" if c > 1 else centaine
            return centaine + " " + convert_centaines(reste)
    
    entier = int(n)
    decimales = int(round((n - entier) * 100))
    
    if entier == 0:
        partie_entiere = "zéro"
    elif entier < 1000:
        partie_entiere = convert_centaines(entier)
    elif entier < 1000000:
        milliers = entier // 1000
        reste = entier % 1000
        if milliers == 1:
            result = "mille"
        else:
            result = convert_centaines(milliers) + " mille"
        if reste > 0:
            result += " " + convert_centaines(reste)
        partie_entiere = result
    else:
        partie_entiere = "montant trop élevé"
    
    result = partie_entiere + " dirhams"
    
    if decimales > 0:
        if decimales == 1:
            centimes_str = "un centime"
        else:
            centimes_str = convert_centaines(decimales) + " centimes"
        result += " et " + centimes_str
    
    return result.strip()

def load_clients():
    if os.path.exists(CLIENTS_FILE):
        try:
            with open(CLIENTS_FILE, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, list):
                    st.info("📱 Migration clients anciens → nouveaux format")
                    new_data = {client: "" for client in data}
                    save_clients(new_data)
                    return new_data
                return data
        except Exception as e:
            st.error(f"Erreur chargement: {e}")
            return {}
    return {}

def save_clients(clients):
    with open(CLIENTS_FILE, 'wb') as f:
        pickle.dump(clients, f)

def get_next_number(date_doc, num_file):
    prefix = date_doc.strftime("%Y%m%d")
    
    if os.path.exists(num_file):
        try:
            with open(num_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}
    
    last_num = int(data.get(prefix, 0))
    new_num = last_num + 1
    data[prefix] = new_num
    
    with open(num_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    return f"{prefix}{new_num:03d}"

# CLASSE BACKGROUND (modifiée pour enlever le soulignement et monter le texte)
class CanvaBackground:
    def __init__(self, logo_path):
        self.logo_path = logo_path
    
    def draw_page(self, canvas_obj, doc):
        canvas_obj.saveState()
        
        # BANDEAU HORIZONTAL GRIS FONCÉ en haut (même couleur que tableau)
        canvas_obj.setFillColor(colors.HexColor('#F0F4F8'))
        canvas_obj.rect(0, A4[1] - 3*cm, A4[0], 3*cm, fill=1, stroke=0)
        
        # TEXTE "TRH 55" couleur cohérente avec en-têtes (MONTÉ PLUS HAUT)
        canvas_obj.setFillColor(colors.HexColor('#2C2C2C'))
        canvas_obj.setFont("Helvetica-Bold", 24)
        canvas_obj.drawString(2*cm, A4[1] - 1.9*cm, "TRH 55")  # 🔥 Changé de 2.3cm à 1.9cm
        
        # 🔥 LIGNE SUPPRIMÉE (soulignement enlevé)
        # canvas_obj.setStrokeColor(colors.HexColor('#2C2C2C'))
        # canvas_obj.setLineWidth(1)
        # canvas_obj.line(2*cm, A4[1] - 2.6*cm, 5*cm, A4[1] - 2.6*cm)
        
        # FOOTER (même couleur que lignes de tableau)
        canvas_obj.setFillColor(colors.HexColor('#F8F8F8'))
        canvas_obj.rect(0, 0, A4[0], 1.8*cm, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.HexColor('#3D3D3D'))
        
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawCentredString(A4[0]/2, 1.3*cm, "TRH 55")
        
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawCentredString(A4[0]/2, 0.85*cm, f"ICE : {ICE} | ADRESSE : 77 Rue Mohamed Smiha Eth 10 N°57 Casablanca, Maroc | TÉL : +212 661 04 90 34")
        
        canvas_obj.setFont("Helvetica-BoldOblique", 8)
        canvas_obj.drawCentredString(A4[0]/2, 0.25*cm, "Merci de votre confiance")
        
        canvas_obj.restoreState()

# Initialisation session state
if 'document_type' not in st.session_state:
    st.session_state.document_type = None
if 'clients' not in st.session_state:
    st.session_state.clients = load_clients()

# Page d'accueil
if st.session_state.document_type is None:
    st.markdown("""
    <style>
    .main-header {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 3rem !important;
        color: #1f77b4;
    }
    .metric-container {
        padding: 2rem !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px !important;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        transition: transform 0.3s ease;
        height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-container:hover {
        transform: translateY(-10px);
    }
    .stMetric > label {
        color: white !important;
        font-size: 1.8rem !important;
        margin-bottom: 1rem !important;
    }
    .stMetric > div > div {
        color: white !important;
        font-size: 2.5rem !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">📄 DOCUMENTS TRH 55</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        if st.button("🧾 **FACTURE**\n*Générer une facture professionnelle*", 
                    type="primary", use_container_width=True, help="Cliquez pour créer une facture"):
            st.session_state.document_type = "facture"
            st.rerun()
    
    with col2:
        if st.button("📦 **BON DE LIVRAISON**\n*Livraison de marchandises*", 
                    type="primary", use_container_width=True, help="Cliquez pour créer un bon de livraison"):
            st.session_state.document_type = "livraison"
            st.rerun()
    
    st.markdown("---")
    st.info("👆 **Choisissez un document pour commencer**")

else:
    # Page commune FACTURE / BON DE LIVRAISON
    document_config = {
        "facture": {
            "title": "🧾 Factures - TRH 55",
            "num_file": NUM_FILE_FACTURE,
            "doc_type": "FACTURE",
            "sidebar_title": "📊 Factures aujourd'hui",
            "show_prices": True
        },
        "livraison": {
            "title": "📦 Bons de Livraison - TRH 55", 
            "num_file": NUM_FILE_LIVRAISON,
            "doc_type": "BON DE LIVRAISON",
            "sidebar_title": "📦 Bons aujourd'hui",
            "show_prices": False
        }
    }
    
    config = document_config[st.session_state.document_type]
    
    if 'client_selected' not in st.session_state:
        st.session_state.client_selected = ""
    if 'date_doc_key' not in st.session_state:
        st.session_state.date_doc_key = None
    if 'num_document' not in st.session_state:
        st.session_state.num_document = ""
    
    st.title(config["title"])
    
    # Sidebar (déplacée ICI après le titre)
    with st.sidebar:
        st.header("👥 Gestion Clients")
        
        client_names = list(st.session_state.clients.keys())
        client_selected = st.selectbox(
            "Sélectionner client:",
            options=["-- Nouveau --"] + client_names,
            index=0
        )
        
        if client_selected != "-- Nouveau --":
            st.session_state.client_selected = client_selected
            st.text_area("Adresse", st.session_state.clients[client_selected], height=60, key="addr_display", disabled=True)
        else:
            st.session_state.client_selected = ""
        
        st.divider()
        
        st.subheader("➕ Nouveau Client")
        new_client = st.text_input("Nom *")
        new_adresse = st.text_area("Adresse", height=80)
        
        if st.button("💾 Ajouter Client"):
            if new_client and new_client not in st.session_state.clients:
                st.session_state.clients[new_client] = new_adresse
                save_clients(st.session_state.clients)
                st.session_state.client_selected = new_client
                st.success(f"✅ {new_client} ajouté!")
                st.rerun()
            else:
                st.error("❌ Nom existant ou vide")
        
        st.divider()
        
        # Compteur spécifique au type de document
        if os.path.exists(config["num_file"]):
            try:
                with open(config["num_file"], "r") as f:
                    nums = json.load(f)
                today_prefix = datetime.date.today().strftime("%Y%m%d")
                today_count = nums.get(today_prefix, 0)
                st.metric(config["sidebar_title"], f"{today_count}")
            except:
                pass
        
        # Bouton retour à l'accueil
        if st.button("🏠 Accueil"):
            st.session_state.document_type = None
            st.rerun()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📄 Informations Document")
        date_doc = st.date_input("Date", datetime.date.today())
        
        if "num_document_key" not in st.session_state or st.session_state.date_doc_key != date_doc:
            st.session_state.date_doc_key = date_doc
            st.session_state.num_document = get_next_number(date_doc, config["num_file"])
        
        num_document_display = st.text_input(f"N° {config['doc_type']} AUTO", st.session_state.num_document, disabled=True)
    
    st.header("📦 Lignes de Document")
    num_rows = st.number_input("Nombre de lignes", 1, 15, 3)
    
    produits = []
    for i in range(num_rows):
        with st.expander(f"Ligne {i+1}", expanded=(i < 2)):
            if config["show_prices"]:
                # FACTURE : avec prix
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1.2])
                with col1:
                    prod = st.text_input("Description", key=f"prod_{i}", placeholder="Ex: Produit")
                with col2:
                    qte = st.number_input("Qté", min_value=0.0, value=1.0, step=1.0, key=f"qte_{i}")
                with col3:
                    unite = st.selectbox("Unité", UNITES, index=0, key=f"unite_{i}")
                with col4:
                    prix = st.number_input("Prix Unitaire (Dhs)", min_value=0.0, value=0.0, step=10.0, key=f"prix_{i}")
                
                if prod.strip() and qte > 0 and prix > 0:
                    total_ligne = qte * prix
                    produits.append({
                        "Description": prod.strip(),
                        "Prix Unitaire": format_montant(prix),
                        "Quantité": int(qte) if qte == int(qte) else qte,
                        "Unité": unite,
                        "Total": format_montant(total_ligne)
                    })
            else:
                # BON DE LIVRAISON : sans prix
                col1, col2, col3 = st.columns([3, 1.2, 1.2])
                with col1:
                    prod = st.text_input("Description", key=f"prod_{i}", placeholder="Ex: Produit")
                with col2:
                    qte = st.number_input("Qté", min_value=0.0, value=1.0, step=1.0, key=f"qte_{i}")
                with col3:
                    unite = st.selectbox("Unité", UNITES, index=0, key=f"unite_{i}")
                
                if prod.strip() and qte > 0:
                    produits.append({
                        "Description": prod.strip(),
                        "Quantité": int(qte) if qte == int(qte) else qte,
                        "Unité": unite
                    })
    
    if produits:
        st.subheader("👀 Aperçu Document")
        df = pd.DataFrame(produits)
        st.dataframe(df, use_container_width=True)
        
        if config["show_prices"]:
            total_ht = round(sum(float(p["Total"].replace(" Dhs", "").replace(' ', '').replace(',', '.')) for p in produits), 2)
            st.metric("**TOTAL**", f"**{format_montant(total_ht)}**")
            
            montant_lettres = nombre_en_lettres(total_ht)
            st.info(f"💬 **Arrêté à :** {montant_lettres.capitalize()}")
    
    # Génération PDF
    if st.button(f"🖨️ GÉNÉRER {config['doc_type']} PDF", type="primary", use_container_width=True):
        if not produits:
            st.error("❌ Ajoutez au moins un produit")
        elif not st.session_state.client_selected:
            st.error("❌ Sélectionnez un client")
        elif not st.session_state.clients.get(st.session_state.client_selected):
            st.error("❌ Adresse du client manquante")
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=3.5*cm,
                bottomMargin=2.8*cm
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=36,
                textColor=colors.HexColor('#2C2C2C'),  # Couleur cohérente
                spaceAfter=5,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT
            )
            
            header_style = ParagraphStyle(
                'Header',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#3D3D3D'),  # Couleur cohérente
                alignment=TA_RIGHT,
                spaceAfter=3
            )
            
            story.append(Spacer(1, 1*cm))
            story.append(Paragraph(f"<b>{config['doc_type']}</b>", title_style))
            story.append(Spacer(1, 0.3*cm))
            
            date_sans_espace = date_doc.strftime('%d/%m/%Y')
            info_data = [
                [Paragraph(f"<b>DATE : </b>{date_sans_espace}", header_style)],
                [Paragraph(f"<b>{config['doc_type']} N°: </b>{st.session_state.num_document}", header_style)]
            ]
            info_table = Table(info_data, colWidths=[16.5*cm])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 1*cm))
            
            emetteur_text = (
                f"<b>TRH 55</b><br/>"
                f"77 Rue Mohamed Smiha Eth 10 N°57<br/>"
                f"Casablanca<br/>"
                f"Maroc<br/>"
                f"<b>TEL:</b> {TELEPHONE}<br/>"
                f"<b>ICE:</b> {ICE}"
            )
            
            emetteur_dest_data = [
                [
                    Paragraph("<b>ÉMETTEUR :</b>", styles['Heading3']),
                    Paragraph("<b>DESTINATAIRE :</b>", styles['Heading3'])
                ],
                [
                    Paragraph(emetteur_text, styles['Normal']),
                    Paragraph(
                        f"<b>{st.session_state.client_selected}</b><br/>"
                        f"{st.session_state.clients[st.session_state.client_selected].replace(chr(10), '<br/>')}",
                        styles['Normal']
                    )
                ]
            ]
            
            emetteur_table = Table(emetteur_dest_data, colWidths=[8*cm, 8*cm])
            emetteur_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ]))
            story.append(emetteur_table)
            story.append(Spacer(1, 1.5*cm))
            
            if config["show_prices"]:
                # FACTURE : avec prix et total
                table_data = [["DÉSIGNATION", "P.U.", "QTE", "UNITÉ", "TOTAL"]]
                
                for p in produits:
                    table_data.append([
                        p["Description"],
                        p["Prix Unitaire"],
                        str(p["Quantité"]),
                        p["Unité"],
                        p["Total"]
                    ])
                
                total_ht = round(sum(float(p["Total"].replace(" Dhs", "").replace(' ', '').replace(',', '.')) for p in produits), 2)
                table_data.append(["", "", "", "TOTAL :", format_montant(total_ht)])
                
                for i in range(1, len(table_data)-1):
                    table_data[i][0] = Paragraph(table_data[i][0], styles['Normal'])
                
                invoice_table = Table(table_data, colWidths=[8.2*cm, 2.8*cm, 1.6*cm, 2.1*cm, 3.0*cm])
                invoice_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F4F8')),  # Même que header
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2C2C2C')),   # Même texte
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2C2C2C')),  # Pas de soulignement
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
                    ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (4, -1), (4, -1), 12),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8F8F8')]),  # Même que footer
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E0E0E0')),
                ]))
            else:
                # BON DE LIVRAISON : sans prix ni total
                table_data = [["DÉSIGNATION", "QUANTITÉ", "UNITÉ"]]
                
                for p in produits:
                    table_data.append([
                        p["Description"],
                        str(p["Quantité"]),
                        p["Unité"]
                    ])
                
                for i in range(1, len(table_data)):
                    table_data[i][0] = Paragraph(table_data[i][0], styles['Normal'])
                
                invoice_table = Table(table_data, colWidths=[12*cm, 2.5*cm, 3*cm])
                invoice_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F4F8')),  # Même que header
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2C2C2C')),   # Même texte
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2C2C2C')),  # Pas de soulignement
                    ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (2, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),  # Même que footer
                ]))
            
            story.append(invoice_table)
            
            if config["show_prices"]:
                story.append(Spacer(1, 0.8*cm))
                total_ht = round(sum(float(p["Total"].replace(" Dhs", "").replace(' ', '').replace(',', '.')) for p in produits), 2)
                montant_lettres = nombre_en_lettres(total_ht)
                arrete_style = ParagraphStyle(
                    'Arrete',
                    parent=styles['Normal'],
                    fontSize=10,
                    fontName='Helvetica-BoldOblique',
                    textColor=colors.HexColor('#3D3D3D')  # Couleur cohérente
                )
                story.append(Paragraph(f"<b>Arrêté la présente facture à la somme de :</b> {montant_lettres.capitalize()}", arrete_style))
            
            doc.build(story, onFirstPage=CanvaBackground(LOGO_PATH).draw_page, onLaterPages=CanvaBackground(LOGO_PATH).draw_page)
            
            buffer.seek(0)
            
            st.success(f"✅ {config['doc_type']} {st.session_state.num_document} générée !")
            st.download_button(
                label="📥 TÉLÉCHARGER PDF",
                data=buffer.getvalue(),
                file_name=f"{config['doc_type'].replace(' ', '_')}_{st.session_state.num_document}.pdf",
                mime="application/pdf"
            )
    
    if not produits:
        st.info("➕ Ajoutez des produits pour générer le document")
    elif not st.session_state.client_selected:
        st.warning("👤 Sélectionnez un client")
