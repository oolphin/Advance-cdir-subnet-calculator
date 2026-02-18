# main.py
"""
Application principale - Découpage CIDR VLAN/VXLAN v3.0
Architecture modulaire et sécurisée
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# Imports des modules
from config.settings import APP_CONFIG, TEMPLATES, SESSION_CONFIG
from core.network_calculator import NetworkCalculator
from core.vlan_manager import VLANManager, VXLANManager
from services.export_service import ExportService
from services.mask_converter import MaskConverter
from utils.validators import SecurityValidator, ConflictDetector
from utils.logger import logger

# Configuration de la page
st.set_page_config(
    page_title=APP_CONFIG['title'],
    page_icon=APP_CONFIG['icon'],
    layout=APP_CONFIG['layout'],
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .stApp header button[kind="header"],
    button[data-testid="baseButton-header"],
    a[href*="share.streamlit.io"],
    div[data-testid="stDeployButton"],
    footer, .stToolbar {
        display: none !important;
        visibility: hidden !important;
    }
    .main .block-container {
        padding-top: 2rem !important;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

class SessionManager:
    """Gestionnaire de session amélioré"""
    
    @staticmethod
    def init():
        """Initialise la session utilisateur"""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.user_id = str(uuid.uuid4())[:8]
            st.session_state.vlan_manager = VLANManager()
            st.session_state.vxlan_manager = VXLANManager()
            st.session_state.network_type = 'VLAN'
            st.session_state.base_network = '10.0.0.0/21'
            st.session_state.results_df = None
            st.session_state.stats = {}
            st.session_state.history = []
            st.session_state.created_at = datetime.now()
            
            logger.info('session_initialized', user_id=st.session_state.user_id)
    
    @staticmethod
    def save_to_history(action: str, description: str):
        """Sauvegarde dans l'historique"""
        if len(st.session_state.history) >= SESSION_CONFIG['max_history']:
            st.session_state.history.pop(0)
        
        st.session_state.history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'description': description,
            'user_id': st.session_state.user_id
        })
        
        logger.info('history_saved', action=action, description=description)
    
    @staticmethod
    def clear():
        """Réinitialise complètement la session"""
        # Supprimer TOUTES les clés pour forcer une vraie réinitialisation
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Relancer l'initialisation
        SessionManager.init()
        logger.info('session_reset')

def render_sidebar():
    """Affiche le panneau latéral avec tabs"""
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        # Type de réseau
        network_type = st.radio(
            "Type de réseau",
            ["VLAN", "VXLAN"],
            index=0 if st.session_state.network_type == 'VLAN' else 1,
            horizontal=True
        )
        
        if network_type != st.session_state.network_type:
            st.session_state.network_type = network_type
            st.rerun()
        
        st.divider()
        
        # Tabs pour éviter la superposition
        tab1, tab2, tab3, tab4 = st.tabs(["📌 VLANs", "🔧 Découpage", "📋 Templates", "🔄 Convertisseur"])
        
        with tab1:
            if network_type == 'VLAN':
                render_vlan_management()
            else:
                render_vxlan_management()
        
        with tab2:
            render_network_config()
        
        with tab3:
            render_templates()
        
        with tab4:
            render_mask_converter()

def render_vlan_management():
    """Gestion des VLANs"""
    with st.expander("📌 Gestion des VLANs", expanded=False):
        manager = st.session_state.vlan_manager
        
        # Import CSV
        st.subheader("📥 Importer depuis CSV")
        
        st.markdown("""
        **Format CSV accepté :**
        ```
        vlan_id,cdir,nom,description,reserve
        1300,/24,VLAN_LAN,Users Wire,False
        1301,/24,VLAN_WIFI,Users WiFi,False
        1302,/24,VLAN_VoIP,Telephony,False
        1303,/26,VLAN_PRINTER,Printers,False
        ```
        """)
        
        uploaded_file = st.file_uploader(
            "Fichier CSV/TXT",
            type=['csv', 'txt'],
            key="vlan_csv_upload",
            help="Format: vlan_id,cdir,nom,description,reserve"
        )
        
        if uploaded_file:
            try:
                content = uploaded_file.getvalue().decode('utf-8')
                
                with st.spinner("🔄 Analyse du fichier..."):
                    result = manager.import_from_file_content(content)
                    
                    if 'error' in result:
                        st.error(f"❌ {result['error']}")
                    elif result.get('total_vlans', 0) > 0:
                        st.success(f"✅ {result['total_vlans']} VLANs trouvés dans le fichier")
                        
                        # Résumé par masque
                        st.markdown("**Résumé par masque :**")
                        for masque, count in sorted(result['decoupages_par_masque'].items()):
                            st.caption(f"• /{masque} : {count} VLAN(s)")
                        
                        # Aperçu
                        if result['vlans']:
                            st.markdown("**Aperçu (premiers VLANs) :**")
                            apercu = []
                            for v in result['vlans'][:5]:
                                apercu.append({
                                    'VLAN': v['vlan_id'],
                                    'Nom': v['nom_original'],
                                    'Masque': f"/{v['masque']}"
                                })
                            st.dataframe(apercu, hide_index=True, use_container_width=True)
                            
                            if len(result['vlans']) > 5:
                                st.caption(f"... et {len(result['vlans']) - 5} autres")
                        
                        st.divider()
                        
                        # Options d'import
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("1️⃣ Importer VLANs uniquement", use_container_width=True):
                                # Nettoyer et importer
                                manager.clear()
                                for v in result['vlans']:
                                    manager.add(
                                        v['vlan_id'],
                                        v['nom_original'],
                                        v['description'],
                                        v['reserve']
                                    )
                                st.success(f"✅ {len(result['vlans'])} VLANs importés!")
                                st.rerun()
                        
                        with col2:
                            if st.button("2️⃣ VLANs + Découpages (ordre fichier)", use_container_width=True, type="primary"):
                                # Importer VLANs
                                manager.clear()
                                for v in result['vlans']:
                                    manager.add(
                                        v['vlan_id'],
                                        v['nom_original'],
                                        v['description'],
                                        v['reserve']
                                    )
                                
                                # Importer découpages dans l'ordre
                                st.session_state.subnet_configs = result['decoupages_ordonnes']
                                st.session_state.import_mode = 'ordered'
                                st.session_state.vlan_mapping = {
                                    i: v['vlan_id'] 
                                    for i, v in enumerate(result['vlans'])
                                }
                                
                                st.success("✅ VLANs et découpages importés!")
                                st.info("👉 Cliquez sur 'Calculer le découpage' pour générer les sous-réseaux")
                                st.rerun()
                        
                        # Option groupée
                        if st.button("3️⃣ VLANs + Découpages groupés par masque", use_container_width=True):
                            manager.clear()
                            for v in result['vlans']:
                                manager.add(
                                    v['vlan_id'],
                                    v['nom_original'],
                                    v['description'],
                                    v['reserve']
                                )
                            
                            st.session_state.subnet_configs = result['decoupages_groupes']
                            st.session_state.import_mode = 'grouped'
                            
                            st.success("✅ VLANs et découpages groupés importés!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Aucun VLAN valide trouvé dans le fichier")
                        
            except Exception as e:
                st.error(f"❌ Erreur lors de l'import : {str(e)}")
        
        st.divider()
        
        # Ajout manuel
        st.subheader("➕ Ajouter un VLAN manuellement")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            vlan_id = st.number_input(
                "VLAN ID",
                min_value=1,
                max_value=4094,
                value=manager.suggest_next_id(),
                key="vlan_id_input"
            )
        with col2:
            if st.button("🔄", help="Suggérer un ID"):
                st.session_state.vlan_id_input = manager.suggest_next_id()
                st.rerun()
        
        name = st.text_input("Nom", max_chars=50, key="vlan_name_input")
        description = st.text_area("Description", max_chars=200, key="vlan_desc_input")
        reserved = st.checkbox("Marquer comme réservé", key="vlan_reserved")
        
        if st.button("➕ Ajouter VLAN", type="primary"):
            if name:
                success, message = manager.add(vlan_id, name, description, reserved)
                if success:
                    st.success(message)
                    SessionManager.save_to_history("vlan_added", f"VLAN {vlan_id} - {name}")
                    logger.info('vlan_added', vlan_id=vlan_id, name=name)
                else:
                    st.error(message)
            else:
                st.error("Le nom est requis")
        
        # Liste des VLANs
        if manager.count() > 0:
            st.divider()
            st.subheader(f"VLANs configurés ({manager.count()})")
            
            for vlan in manager.get_all():
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "📌" if vlan.get('reserved') else "🔵"
                    st.markdown(f"{icon} **VLAN {vlan['vlan_id']}** - {vlan['name']}")
                    if vlan.get('description'):
                        st.caption(vlan['description'])
                with col2:
                    if st.button("🗑️", key=f"del_vlan_{vlan['vlan_id']}"):
                        manager.remove(vlan['vlan_id'])
                        st.rerun()
            
            # Détection de conflits
            conflicts = manager.detect_conflicts()
            if conflicts:
                st.warning(f"⚠️ {len(conflicts)} conflit(s) détecté(s)")
                for conflict in conflicts:
                    st.caption(f"• {conflict['message']}")
        else:
            st.info("Aucun VLAN configuré")

def render_vxlan_management():
    """Gestion des VXLANs"""
    with st.expander("📌 Gestion des VXLANs", expanded=False):
        manager = st.session_state.vxlan_manager
        
        # Import CSV
        st.subheader("📥 Importer depuis CSV")
        
        st.markdown("""
        **Format CSV accepté :**
        ```
        vni,cdir,nom,description,mtu,reserve
        10000,/24,TENANT_A_WEB,Tenant A Web,1500,False
        10001,/24,TENANT_A_APP,Tenant A Application,1500,False
        10002,/25,TENANT_A_DB,Tenant A Database,1500,False
        11000,/24,TENANT_B_WEB,Tenant B Web,9000,False
        ```
        """)
        
        uploaded_file = st.file_uploader(
            "Fichier CSV/TXT",
            type=['csv', 'txt'],
            key="vxlan_csv_upload",
            help="Format: vni,cdir,nom,description,mtu,reserve"
        )
        
        if uploaded_file:
            try:
                content = uploaded_file.getvalue().decode('utf-8')
                
                with st.spinner("🔄 Analyse du fichier..."):
                    result = manager.import_from_file_content(content)
                    
                    if 'error' in result:
                        st.error(f"❌ {result['error']}")
                    elif result.get('total_vxlans', 0) > 0:
                        st.success(f"✅ {result['total_vxlans']} VXLANs trouvés dans le fichier")
                        
                        # Résumé par masque
                        st.markdown("**Résumé par masque :**")
                        for masque, count in sorted(result['decoupages_par_masque'].items()):
                            st.caption(f"• /{masque} : {count} VXLAN(s)")
                        
                        # Aperçu
                        if result['vxlans']:
                            st.markdown("**Aperçu (premiers VXLANs) :**")
                            apercu = []
                            for v in result['vxlans'][:5]:
                                apercu.append({
                                    'VNI': v['vni'],
                                    'Nom': v['nom_original'],
                                    'Masque': f"/{v['masque']}",
                                    'MTU': v.get('mtu', 1500)
                                })
                            st.dataframe(apercu, hide_index=True, use_container_width=True)
                            
                            if len(result['vxlans']) > 5:
                                st.caption(f"... et {len(result['vxlans']) - 5} autres")
                        
                        st.divider()
                        
                        # Options d'import
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("1️⃣ Importer VXLANs uniquement", use_container_width=True):
                                # Nettoyer et importer
                                manager.clear()
                                for v in result['vxlans']:
                                    manager.add(
                                        v['vni'],
                                        v['nom_original'],
                                        v['description'],
                                        v.get('mtu', 1500),
                                        v['reserve']
                                    )
                                st.success(f"✅ {len(result['vxlans'])} VXLANs importés!")
                                st.rerun()
                        
                        with col2:
                            if st.button("2️⃣ VXLANs + Découpages (ordre fichier)", use_container_width=True, type="primary"):
                                # Importer VXLANs
                                manager.clear()
                                for v in result['vxlans']:
                                    manager.add(
                                        v['vni'],
                                        v['nom_original'],
                                        v['description'],
                                        v.get('mtu', 1500),
                                        v['reserve']
                                    )
                                
                                # Importer découpages dans l'ordre
                                st.session_state.subnet_configs = result['decoupages_ordonnes']
                                st.session_state.import_mode = 'ordered'
                                st.session_state.vlan_mapping = {
                                    i: v['vni'] 
                                    for i, v in enumerate(result['vxlans'])
                                }
                                
                                st.success("✅ VXLANs et découpages importés!")
                                st.info("👉 Cliquez sur 'Calculer le découpage' pour générer les sous-réseaux")
                                st.rerun()
                        
                        # Option groupée
                        if st.button("3️⃣ VXLANs + Découpages groupés par masque", use_container_width=True):
                            manager.clear()
                            for v in result['vxlans']:
                                manager.add(
                                    v['vni'],
                                    v['nom_original'],
                                    v['description'],
                                    v.get('mtu', 1500),
                                    v['reserve']
                                )
                            
                            st.session_state.subnet_configs = result['decoupages_groupes']
                            st.session_state.import_mode = 'grouped'
                            
                            st.success("✅ VXLANs et découpages groupés importés!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Aucun VXLAN valide trouvé dans le fichier")
                        
            except Exception as e:
                st.error(f"❌ Erreur lors de l'import : {str(e)}")
        
        st.divider()
        
        # Ajout manuel
        st.subheader("➕ Ajouter un VXLAN manuellement")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            vni = st.number_input(
                "VNI",
                min_value=1,
                max_value=16777215,
                value=manager.suggest_next_vni(),
                key="vni_input"
            )
        with col2:
            if st.button("🔄", help="Suggérer un VNI"):
                st.session_state.vni_input = manager.suggest_next_vni()
                st.rerun()
        
        name = st.text_input("Nom", max_chars=50, key="vxlan_name_input")
        description = st.text_area("Description", max_chars=200, key="vxlan_desc_input")
        
        col1, col2 = st.columns(2)
        with col1:
            mtu = st.number_input("MTU", value=1500, min_value=1280, max_value=9000)
        with col2:
            reserved = st.checkbox("Réservé", key="vxlan_reserved")
        
        if st.button("➕ Ajouter VXLAN", type="primary"):
            if name:
                success, message = manager.add(vni, name, description, mtu, reserved)
                if success:
                    st.success(message)
                    SessionManager.save_to_history("vxlan_added", f"VXLAN {vni} - {name}")
                    logger.info('vxlan_added', vni=vni, name=name)
                else:
                    st.error(message)
            else:
                st.error("Le nom est requis")
        
        # Liste des VXLANs
        if manager.count() > 0:
            st.subheader(f"VXLANs configurés ({manager.count()})")
            
            for vxlan in manager.get_all():
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "📌" if vxlan.get('reserved') else "🔵"
                    st.markdown(f"{icon} **VXLAN {vxlan['vni']}** - {vxlan['name']}")
                    st.caption(f"Multicast: {vxlan['multicast_ip']} | MTU: {vxlan['mtu']}")
                with col2:
                    if st.button("🗑️", key=f"del_vxlan_{vxlan['vni']}"):
                        manager.remove(vxlan['vni'])
                        st.rerun()
        else:
            st.info("Aucun VXLAN configuré")

def render_network_config():
    """Configuration du découpage réseau"""
    with st.expander("🌐 Découpage de réseau", expanded=True):
        # Réseau de base
        base_network = st.text_input(
            "Réseau de base (CIDR)",
            value=st.session_state.base_network,
            help="Format: 10.0.0.0/21"
        )
        
        validator = SecurityValidator()
        is_valid, error_msg = validator.validate_network(base_network)
        
        if is_valid:
            st.success("✅ Réseau valide")
            st.session_state.base_network = base_network
        else:
            st.error(f"❌ {error_msg}")
            return
        
        st.divider()
        
        # Configuration des sous-réseaux
        st.subheader("Configuration des sous-réseaux")
        
        col1, col2 = st.columns(2)
        with col1:
            count = st.number_input("Nombre", min_value=1, max_value=100, value=4)
        with col2:
            size = st.selectbox(
                "Taille",
                options=[24, 25, 26, 27, 28, 29, 30],
                format_func=lambda x: f"/{x}"
            )
        
        if 'subnet_configs' not in st.session_state:
            st.session_state.subnet_configs = []
        
        if st.button("➕ Ajouter configuration"):
            st.session_state.subnet_configs.append({'nombre': count, 'taille': size})
            st.rerun()
        
        # Afficher les configurations
        if st.session_state.subnet_configs:
            st.subheader("Configurations ajoutées")
            for i, config in enumerate(st.session_state.subnet_configs):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"✅ {config['nombre']} sous-réseaux /{config['taille']}")
                with col2:
                    if st.button("🗑️", key=f"del_config_{i}"):
                        st.session_state.subnet_configs.pop(i)
                        st.rerun()
        
        st.divider()
        
        # Bouton de calcul
        if st.button("🚀 Calculer le découpage", type="primary", use_container_width=True):
            if not st.session_state.subnet_configs:
                st.error("Ajoutez au moins une configuration")
            else:
                calculate_subnets()

def render_templates():
    """Affiche les templates prédéfinis avec option de sauvegarde et import personnalisés"""
    
    # Tabs pour templates prédéfinis, import et sauvegarde
    tab1, tab2, tab3 = st.tabs(["📋 Templates prédéfinis", "📂 Importer template", "💾 Sauvegarder config"])
    
    with tab1:
        st.markdown("Démarrez rapidement avec une configuration pré-établie")
        
        template_keys = list(TEMPLATES.keys())
        template_names = {k: TEMPLATES[k]['nom'] for k in template_keys}
        
        selected = st.selectbox(
            "Choisir un template",
            options=template_keys,
            format_func=lambda x: template_names[x],
            key="template_selector"
        )
        
        if selected:
            template = TEMPLATES[selected]
            st.info(f"**{template['description']}**")
            st.caption(f"Réseau: {template['reseau_base']}")
            
            # Afficher les VLANs/VXLANs avec leurs CIDR
            if template['network_type'] == 'VLAN':
                st.markdown("**VLANs configurés :**")
                vlans_display = []
                for v in template['vlans']:
                    vlans_display.append({
                        'VLAN': v['vlan_id'],
                        'Nom': v['nom'],
                        'CIDR': v.get('cdir', 'N/A'),
                        'Description': v['description'][:30]
                    })
                st.dataframe(vlans_display, hide_index=True, use_container_width=True)
            else:
                st.markdown("**VXLANs configurés :**")
                vxlans_display = []
                for v in template.get('vxlans', []):
                    vxlans_display.append({
                        'VNI': v['vni'],
                        'Nom': v['nom'],
                        'CIDR': v.get('cdir', 'N/A'),
                        'MTU': v.get('mtu', 1500)
                    })
                st.dataframe(vxlans_display, hide_index=True, use_container_width=True)
            
            # Résumé
            col1, col2 = st.columns(2)
            with col1:
                count = len(template.get('vlans', [])) or len(template.get('vxlans', []))
                st.metric("VLANs/VXLANs", count)
            with col2:
                st.metric("Sous-réseaux", len(template['decoupages']))
            
            if st.button("✨ Appliquer ce template", use_container_width=True, type="primary", key="apply_predefined"):
                apply_template(template)
                st.success("✅ Template appliqué! Cliquez sur 'Calculer le découpage'")
                st.rerun()
    
    with tab2:
        st.markdown("📂 **Importer un template personnalisé**")
        st.caption("Importez un fichier JSON de template créé précédemment")
        
        uploaded_template = st.file_uploader(
            "Fichier template (JSON)",
            type=['json'],
            key="template_upload",
            help="Sélectionnez un fichier template JSON"
        )
        
        if uploaded_template:
            try:
                import json
                template_content = uploaded_template.getvalue().decode('utf-8')
                template = json.loads(template_content)
                
                # Valider le template
                required_fields = ['nom', 'reseau_base', 'network_type', 'decoupages']
                missing_fields = [f for f in required_fields if f not in template]
                
                if missing_fields:
                    st.error(f"❌ Champs manquants dans le template: {', '.join(missing_fields)}")
                else:
                    # Afficher le résumé du template
                    st.success(f"✅ Template chargé: **{template['nom']}**")
                    
                    if template.get('description'):
                        st.info(template['description'])
                    
                    st.caption(f"Réseau: {template['reseau_base']}")
                    
                    # Afficher les VLANs/VXLANs
                    if template['network_type'] == 'VLAN':
                        vlans = template.get('vlans', [])
                        st.markdown(f"**{len(vlans)} VLANs configurés**")
                        if vlans:
                            vlans_preview = [{'VLAN': v['vlan_id'], 'Nom': v['nom']} for v in vlans[:5]]
                            st.dataframe(vlans_preview, hide_index=True, use_container_width=True)
                            if len(vlans) > 5:
                                st.caption(f"... et {len(vlans) - 5} autres VLANs")
                    else:
                        vxlans = template.get('vxlans', [])
                        st.markdown(f"**{len(vxlans)} VXLANs configurés**")
                        if vxlans:
                            vxlans_preview = [{'VNI': v['vni'], 'Nom': v['nom']} for v in vxlans[:5]]
                            st.dataframe(vxlans_preview, hide_index=True, use_container_width=True)
                            if len(vxlans) > 5:
                                st.caption(f"... et {len(vxlans) - 5} autres VXLANs")
                    
                    # Découpages
                    nb_subnets = sum(d['nombre'] for d in template['decoupages'])
                    st.markdown(f"**{nb_subnets} sous-réseaux** définis")
                    
                    st.divider()
                    
                    # Bouton d'application
                    if st.button("✨ Appliquer ce template", use_container_width=True, type="primary", key="apply_custom"):
                        apply_template(template)
                        st.success("✅ Template personnalisé appliqué! Cliquez sur 'Calculer le découpage'")
                        st.rerun()
                        
            except json.JSONDecodeError as e:
                st.error(f"❌ Erreur de lecture du fichier JSON: {str(e)}")
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement du template: {str(e)}")
    
    with tab3:
        st.markdown("💾 **Sauvegarder la configuration actuelle comme template**")
        
        # Vérifier qu'il y a une configuration
        has_config = (
            st.session_state.base_network and 
            st.session_state.get('subnet_configs') and
            (st.session_state.vlan_manager.count() > 0 or st.session_state.vxlan_manager.count() > 0)
        )
        
        if not has_config:
            st.warning("⚠️ Configurez d'abord votre réseau, VLANs et découpage")
        else:
            template_name = st.text_input("Nom du template", placeholder="Mon template personnalisé")
            template_desc = st.text_area("Description", placeholder="Description du template...")
            
            if st.button("💾 Sauvegarder comme template", type="primary", use_container_width=True):
                if not template_name:
                    st.error("Le nom est requis")
                else:
                    # Créer le template
                    custom_template = {
                        'nom': template_name,
                        'description': template_desc or "Template personnalisé",
                        'reseau_base': st.session_state.base_network,
                        'network_type': st.session_state.network_type,
                        'decoupages': st.session_state.subnet_configs.copy()
                    }
                    
                    # Ajouter VLANs ou VXLANs
                    if st.session_state.network_type == 'VLAN':
                        custom_template['vlans'] = [
                            {
                                'vlan_id': v['vlan_id'],
                                'nom': v['name'],
                                'description': v.get('description', '')
                            }
                            for v in st.session_state.vlan_manager.get_all()
                        ]
                    else:
                        custom_template['vxlans'] = [
                            {
                                'vni': v['vni'],
                                'nom': v['name'],
                                'description': v.get('description', ''),
                                'mtu': v.get('mtu', 1500)
                            }
                            for v in st.session_state.vxlan_manager.get_all()
                        ]
                    
                    # Exporter en JSON
                    import json
                    template_json = json.dumps(custom_template, indent=2, ensure_ascii=False)
                    
                    st.success("✅ Template créé !")
                    st.download_button(
                        "📥 Télécharger le template (JSON)",
                        data=template_json,
                        file_name=f"template_{template_name.lower().replace(' ', '_')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    st.info("💡 **Astuce**: Vous pouvez modifier ce fichier JSON et le réutiliser plus tard")

def apply_template(template: dict):
    """Applique un template avec attribution ordonnée 1:1 (comme import CSV)"""
    
    # Réseau de base
    st.session_state.base_network = template['reseau_base']
    st.session_state.network_type = template.get('network_type', 'VLAN')
    
    # VLANs ou VXLANs
    if template['network_type'] == 'VLAN':
        manager = st.session_state.vlan_manager
        manager.clear()
        
        # Stocker les VLANs dans l'ordre pour le mapping
        vlans_ordonnes = []
        for vlan in template['vlans']:
            manager.add(
                vlan['vlan_id'],
                vlan['nom'],
                vlan['description']
            )
            vlans_ordonnes.append(vlan)
    else:
        manager = st.session_state.vxlan_manager
        manager.clear()
        
        # Stocker les VXLANs dans l'ordre pour le mapping
        vlans_ordonnes = []
        for vxlan in template.get('vxlans', []):
            manager.add(
                vxlan['vni'],
                vxlan['nom'],
                vxlan['description'],
                vxlan.get('mtu', 1500)
            )
            vlans_ordonnes.append(vxlan)
    
    # Découpages
    st.session_state.subnet_configs = template['decoupages']
    
    # ACTIVER le mode ordered avec mapping 1:1 (comme import CSV option 2)
    # Cela garantit que chaque sous-réseau reçoit le VLAN correspondant dans l'ordre
    st.session_state.import_mode = 'ordered'
    
    # Créer le mapping : index du sous-réseau -> VLAN ID/VNI
    if template['network_type'] == 'VLAN':
        st.session_state.vlan_mapping = {
            i: vlan['vlan_id'] 
            for i, vlan in enumerate(vlans_ordonnes)
        }
    else:
        st.session_state.vlan_mapping = {
            i: vxlan['vni'] 
            for i, vxlan in enumerate(vlans_ordonnes)
        }
    
    SessionManager.save_to_history(
        "template_applied",
        f"Template '{template['nom']}' appliqué avec attribution ordonnée"
    )
    
    logger.info('template_applied', template=template['nom'], mode='ordered')

def calculate_subnets():
    """Calcule le découpage des sous-réseaux avec attribution selon l'ordre ou cyclique"""
    try:
        # Créer le calculateur
        calc = NetworkCalculator(st.session_state.base_network)
        
        # Découper
        results = calc.split_network(st.session_state.subnet_configs)
        
        # Récupérer le manager selon le type
        if st.session_state.network_type == 'VLAN':
            manager = st.session_state.vlan_manager
            available = manager.get_all()  # Tous les VLANs (pas seulement disponibles)
            id_field = 'VLAN ID'
            name_field = 'Nom VLAN'
        else:
            manager = st.session_state.vxlan_manager
            available = manager.get_all()
            id_field = 'VNI'
            name_field = 'Nom VXLAN'
        
        if not available:
            st.warning("⚠️ Aucun VLAN/VXLAN disponible pour l'attribution")
        
        # Mode d'import : ordered (1 VLAN par sous-réseau) ou grouped/normal (cyclique)
        import_mode = st.session_state.get('import_mode', 'normal')
        vlan_mapping = st.session_state.get('vlan_mapping', {})
        
        if import_mode == 'ordered' and vlan_mapping:
            # Mode import avec mapping 1:1 (ordre du fichier ou template)
            for result in results:
                # Utiliser global_index pour le mapping (pas enumerate)
                global_idx = result['global_index']
                
                if global_idx in vlan_mapping:
                    # Trouver le VLAN correspondant
                    vlan_id_recherche = vlan_mapping[global_idx]
                    vlan_trouve = None
                    
                    for v in available:
                        if v.get('vlan_id') == vlan_id_recherche or v.get('vni') == vlan_id_recherche:
                            vlan_trouve = v
                            break
                    
                    if vlan_trouve:
                        result[id_field] = vlan_trouve.get('vlan_id') or vlan_trouve.get('vni')
                        result[name_field] = vlan_trouve['name']
                        
                        if st.session_state.network_type == 'VXLAN':
                            result['Multicast IP'] = vlan_trouve.get('multicast_ip', 'N/A')
                            result['MTU'] = vlan_trouve.get('mtu', 1500)
                    else:
                        result[id_field] = "Non attribué"
                        result[name_field] = "Non défini"
                else:
                    result[id_field] = "Non attribué"
                    result[name_field] = "Non défini"
        else:
            # Mode normal/groupé : attribution cyclique par configuration
            # Regrouper les résultats par config_index
            results_by_config = {}
            for result in results:
                config_idx = result['config_index']
                if config_idx not in results_by_config:
                    results_by_config[config_idx] = []
                results_by_config[config_idx].append(result)
            
            # Attribuer pour chaque groupe de configuration
            for config_idx, config_results in results_by_config.items():
                for i, result in enumerate(config_results):
                    if available:
                        # Attribution cyclique au sein de cette configuration
                        config = available[i % len(available)]
                        result[id_field] = config.get('vlan_id') or config.get('vni')
                        result[name_field] = config['name']
                        
                        if st.session_state.network_type == 'VXLAN':
                            result['Multicast IP'] = config.get('multicast_ip', 'N/A')
                            result['MTU'] = config.get('mtu', 1500)
                    else:
                        result[id_field] = "Non attribué"
                        result[name_field] = "Non défini"
        
        # Créer le DataFrame en conservant l'ordre global
        results_sorted = sorted(results, key=lambda x: x['global_index'])
        df = pd.DataFrame(results_sorted)
        
        # Renommer les colonnes
        column_mapping = {
            'cidr': 'Sous-réseau',
            'netmask': 'Masque',
            'broadcast': 'Broadcast',
            'first_host': 'Première IP',
            'last_host': 'Dernière IP',
            'gateway': 'Gateway',
            'usable_hosts': 'Hosts utilisables',
            'ip_range': 'Plage IP'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Ajouter nom de sous-réseau
        df.insert(0, 'Nom sous-réseau', [f"SR_{i+1:03d}" for i in range(len(df))])
        
        # Ajouter colonne Masque réseau (CIDR)
        if 'prefix_length' in df.columns:
            df.insert(df.columns.get_loc('Masque'), 'Masque réseau', 
                     df['prefix_length'].apply(lambda x: f"/{x}"))
        
        # Ajouter description complète
        if st.session_state.network_type == 'VLAN':
            df['Description complète'] = df.apply(
                lambda row: f"{row['Nom sous-réseau']} - VLAN {row[id_field]} - {row[name_field]} - {row['Sous-réseau']}",
                axis=1
            )
        else:
            df['Description complète'] = df.apply(
                lambda row: f"{row['Nom sous-réseau']} - VXLAN {row[id_field]} - {row[name_field]} - {row['Sous-réseau']}",
                axis=1
            )
        
        # Nettoyer les colonnes techniques
        cols_to_drop = ['config_index', 'subnet_index_in_config', 'global_index', 
                       'prefix_length', 'network']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
        
        # Sauvegarder
        st.session_state.results_df = df
        
        # Calculer les stats
        subnets = df['Sous-réseau'].tolist()
        st.session_state.stats = calc.calculate_statistics(subnets)
        
        SessionManager.save_to_history(
            "subnets_calculated",
            f"{len(results)} sous-réseaux générés"
        )
        
        logger.info('subnets_calculated', count=len(results), mode=import_mode)
        
        # Réinitialiser le mode d'import après calcul
        if 'import_mode' in st.session_state:
            del st.session_state['import_mode']
        if 'vlan_mapping' in st.session_state:
            del st.session_state['vlan_mapping']
        
        st.success(f"✅ {len(results)} sous-réseaux calculés avec succès!")
        
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")
        logger.error('calculation_failed', error=str(e))

def render_results():
    """Affiche les résultats avec statistiques détaillées"""
    if st.session_state.results_df is None:
        st.info("👈 Configurez votre découpage dans le panneau latéral")
        return
    
    df = st.session_state.results_df
    stats = st.session_state.stats
    
    # Statistiques globales
    st.subheader("📊 Statistiques globales")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sous-réseaux", len(df))
    with col2:
        st.metric("IPs totales", f"{stats.get('total_ips', 0):,}")
    with col3:
        st.metric("IPs utilisées", f"{stats.get('used_ips', 0):,}")
    with col4:
        st.metric("Utilisation", f"{stats.get('utilization', 0):.1f}%")
    
    # Statistiques par CIDR
    st.subheader("📈 Répartition par masque CIDR")
    
    # Compter les sous-réseaux par masque
    cidr_stats = {}
    for _, row in df.iterrows():
        mask = row['Masque réseau'].split('/')[-1] if '/' in str(row['Masque réseau']) else 'N/A'
        cidr_key = f"/{mask}"
        if cidr_key not in cidr_stats:
            cidr_stats[cidr_key] = {'count': 0, 'ips': 0}
        cidr_stats[cidr_key]['count'] += 1
        cidr_stats[cidr_key]['ips'] += row.get('total_hosts', 0)
    
    # Afficher sous forme de colonnes
    cidr_cols = st.columns(min(len(cidr_stats), 6))
    for idx, (cidr, data) in enumerate(sorted(cidr_stats.items())):
        with cidr_cols[idx % 6]:
            st.metric(
                cidr,
                f"{data['count']} SR",
                f"{data['ips']:,} IPs"
            )
    
    st.divider()
    
    # Tableau des résultats
    st.subheader("📋 Résultats du découpage")
    st.dataframe(df, use_container_width=True, height=400)
    
    # Export
    st.divider()
    st.subheader("📥 Export")
    
    col1, col2, col3, col4 = st.columns(4)
    
    export_service = ExportService()
    
    with col1:
        excel_data = export_service.to_excel(
            df, stats, st.session_state.network_type, st.session_state.user_id
        )
        st.download_button(
            "📊 Excel",
            data=excel_data.getvalue(),
            file_name=f"cidr_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        csv_data = export_service.to_csv(df)
        st.download_button(
            "📄 CSV",
            data=csv_data,
            file_name=f"cidr_{datetime.now():%Y%m%d_%H%M%S}.csv",
            mime="text/csv"
        )
    
    with col3:
        json_data = export_service.to_json(df)
        st.download_button(
            "🔧 JSON",
            data=json_data,
            file_name=f"cidr_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json"
        )
    
    with col4:
        if st.button("🔄 Nouveau calcul"):
            st.session_state.results_df = None
            st.session_state.stats = {}
            st.session_state.subnet_configs = []
            st.rerun()

def render_mask_converter():
    """Affiche l'outil de conversion de masques CIDR"""
    st.markdown("### 🔄 Convertisseur Masques ↔ CIDR")
    st.caption("Conversion de masques de sous-réseau en notation CIDR et calcul d'informations réseau")
    
    # Sous-onglets
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🔢 Conversion", "📋 Traitement en lot", "📁 Excel"])
    
    # ─── Tab 1 : Conversion manuelle ─────────────────────────────────────────────
    with sub_tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Masque → CIDR")
            ip_manual = st.text_input("Adresse IP", value="10.58.0.0", key="ip_manual_conv")
            mask_manual = st.text_input("Masque de sous-réseau", value="255.255.0.0", key="mask_manual_conv")
            
            if st.button("🔄 Convertir", key="btn_mask_conv", use_container_width=True):
                info = MaskConverter.get_network_info(ip_manual, mask_manual)
                
                if 'error' in info:
                    st.error(f"❌ {info['error']}")
                else:
                    st.success(f"**Notation CIDR :** `{info['notation_cidr']}`")
                    
                    # Affichage des informations détaillées
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Réseau", info['network'])
                        st.metric("Broadcast", info['broadcast'])
                        st.metric("Masque", info['mask'])
                    with col_b:
                        st.metric("Première IP hôte", info['first_host'])
                        st.metric("Dernière IP hôte", info['last_host'])
                        st.metric("Hosts disponibles", f"{info['hosts']:,}")
        
        with col2:
            st.markdown("#### CIDR → Masque")
            cidr_input = st.slider("Préfixe CIDR", min_value=0, max_value=32, value=24, key="cidr_slider_conv")
            
            try:
                mask_result = MaskConverter.cidr_to_mask(cidr_input)
                hosts = MaskConverter.host_count(cidr_input)
                
                st.metric("Masque correspondant", mask_result)
                st.metric("Hosts disponibles", f"{hosts:,}")
                
                # Informations supplémentaires
                st.info(f"""
                **Informations réseau /{cidr_input}:**
                - Nombre de sous-réseaux : {2**(cidr_input-16) if cidr_input >= 16 else 'N/A'}
                - Taille du bloc : {2**(32-cidr_input)} IPs
                - Classe : {'A' if cidr_input <= 8 else 'B' if cidr_input <= 16 else 'C' if cidr_input <= 24 else 'D/E'}
                """)
            except Exception as e:
                st.error(f"Erreur : {e}")
    
    # ─── Tab 2 : Traitement en lot ────────────────────────────────────────────────
    with sub_tab2:
        st.markdown("""
        **Format attendu :** Deux colonnes `IP` et `Masque` séparées par une tabulation ou un point-virgule.
        """)
        
        sample = "IP\tMasque\n10.0.0.0\t255.255.255.0\n192.168.1.0\t255.255.255.128\n172.16.0.0\t255.255.0.0"
        raw = st.text_area(
            "Données (IP \\t Masque)", 
            value=sample, 
            height=200,
            key="batch_data_conv"
        )
        
        if st.button("🚀 Calculer", key="btn_batch_conv", use_container_width=True):
            try:
                # Détecter le séparateur
                sep = '\t' if '\t' in raw else ';'
                df = MaskConverter.process_batch(raw, sep)
                
                # Affichage
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Export CSV
                csv = df.to_csv(index=False, sep=';').encode('utf-8')
                st.download_button(
                    "⬇️ Télécharger CSV",
                    csv,
                    f"conversion_cidr_{datetime.now():%Y%m%d_%H%M%S}.csv",
                    "text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ Erreur de traitement : {e}")
    
    # ─── Tab 3 : Fichier Excel ────────────────────────────────────────────────────
    with sub_tab3:
        st.markdown("""
        Importez un fichier `.xlsx` avec au minimum deux colonnes : **IP** et **Masque**.
        La colonne CIDR sera ajoutée automatiquement.
        """)
        
        uploaded = st.file_uploader(
            "📂 Choisir un fichier Excel",
            type=["xlsx"],
            key="excel_upload_conv"
        )
        
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                
                # Détection automatique des colonnes
                cols = list(df.columns)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    col_ip = st.selectbox("Colonne IP", cols, index=0, key="col_ip_conv")
                with col_b:
                    col_mask = st.selectbox("Colonne Masque", cols, index=min(1, len(cols)-1), key="col_mask_conv")
                
                if st.button("🔄 Traiter", key="btn_excel_conv", use_container_width=True):
                    # Traitement
                    df = MaskConverter.process_excel(df, col_ip, col_mask)
                    
                    # Affichage
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Export Excel
                    import io
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='CIDR')
                    
                    st.download_button(
                        "⬇️ Télécharger Excel enrichi",
                        out.getvalue(),
                        f"conversion_cidr_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"❌ Erreur lors du traitement du fichier : {e}")

def render_user_manual():
    """Affiche le manuel d'utilisation"""
    with st.expander("📖 Manuel d'utilisation - Cliquez pour ouvrir", expanded=False):
        st.markdown("""
        ## 🎯 Guide de démarrage rapide
        
        ### Méthode 1️⃣ : Import CSV (Recommandé)
        
        1. **Préparez votre fichier CSV** avec ce format :
        ```
        vlan_id,cdir,nom,description
        300,/24,VLAN_LAN,Users Wire
        301,/24,VLAN_WIFI,Users WiFi
        302,/26,VLAN_PRINTER,Printers
        ```
        
        2. **Sidebar** → Onglet **📌 VLANs** → **📥 Importer CSV**
        
        3. Choisissez l'option d'import :
           - **1️⃣ Import VLANs** : Importe uniquement les VLANs
           - **2️⃣ VLANs + Ordre** : Importe VLANs + génère les découpages (recommandé)
        
        4. **Sidebar** → Onglet **🔧 Découpage** → **🚀 Calculer**
        
        ---
        
        ### Méthode 2️⃣ : Configuration manuelle
        
        #### Étape 1 : Type de réseau
        - **Sidebar** → Sélectionnez **VLAN** ou **VXLAN**
        
        #### Étape 2 : Configurer les VLANs
        - **Sidebar** → Onglet **📌 VLANs** → **➕ Ajouter manuellement**
        - Entrez : VLAN ID, Nom, Description
        - Répétez pour chaque VLAN
        
        #### Étape 3 : Configurer le découpage
        - **Sidebar** → Onglet **🔧 Découpage**
        - **Réseau de base** : Ex. `10.82.88.0/21`
        - **Ajouter configurations** :
          - Nombre : combien de sous-réseaux de cette taille
          - Taille : masque CIDR (/24, /25, /26, etc.)
          - Cliquez **➕ Ajouter configuration**
        - Répétez pour chaque groupe de sous-réseaux
        
        #### Étape 4 : Calculer
        - Cliquez **🚀 Calculer le découpage**
        
        ---
        
        ### Méthode 3️⃣ : Utiliser un template
        
        1. **Sidebar** → Onglet **📋 Templates** → **📋 Templates prédéfinis**
        
        2. Choisissez un template :
           - 🏢 Datacenter 3-Tier
           - 🏫 Réseau Campus
           - 🏠 Petite Entreprise
        
        3. Cliquez **✨ Appliquer ce template**
        
        4. **Onglet 🔧 Découpage** → **🚀 Calculer**
        
        ---
        
        ## 📊 Comprendre les résultats
        
        ### Statistiques globales
        - **Sous-réseaux** : Nombre total de sous-réseaux créés
        - **IPs totales** : Capacité totale du réseau de base
        - **IPs utilisées** : Nombre d'IPs allouées
        - **Utilisation** : Pourcentage d'utilisation du réseau
        
        ### Répartition par masque CIDR
        Affiche combien de sous-réseaux de chaque taille ont été créés.
        
        ### Tableau des résultats
        Chaque ligne représente un sous-réseau avec :
        - **Nom du subnet** : SR_001, SR_002, etc.
        - **N°VLAN** : VLAN assigné
        - **NET_ID** : Adresse réseau
        - **Netmask** : Masque de sous-réseau
        - **Broadcast** : Adresse de diffusion
        - **Plage IP** : IPs utilisables (HORS gateway)
        - **Gateway** : Dernière IP utilisable (séparée)
        
        ---
        
        ## 💾 Sauvegarder votre configuration
        
        1. Configurez votre réseau comme souhaité
        2. **Sidebar** → **📋 Templates** → **💾 Sauvegarder config**
        3. Entrez un nom et une description
        4. Cliquez **💾 Sauvegarder comme template**
        5. Téléchargez le fichier JSON
        
        ➡️ Vous pourrez réutiliser ce template plus tard !
        
        ---
        
        ## 📥 Exporter les résultats
        
        Après calcul, plusieurs formats disponibles :
        - **📊 Excel** : Fichier .xlsx avec formatage
        - **📄 CSV** : Format texte, compatible import
        - **🔧 JSON** : Format structuré pour scripts
        
        ---
        
        ## 💡 Astuces
        
        ### Pour un réseau /21 complet
        Un réseau /21 (ex: `10.82.88.0/21`) contient 2048 IPs de `10.82.88.0` à `10.82.95.255`.
        
        Pour le remplir complètement, vos découpages doivent utiliser toutes les IPs.
        
        **Exemple** : 18 VLANs avec des masques variés pour utiliser `10.82.88.0` → `10.82.95.255`
        
        ### Plage IP vs Gateway
        - **Plage IP** : IPs utilisables HORS gateway (pour les hôtes)
        - **Gateway** : Dernière IP, réservée pour la passerelle
        
        **Exemple pour un /24** :
        - Plage IP : `10.0.0.1` → `10.0.0.253` (253 IPs pour les hôtes)
        - Gateway : `10.0.0.254` (réservée)
        
        ### Import CSV avec ordre
        L'option **"VLANs + Ordre"** crée automatiquement les découpages dans l'ordre du fichier CSV.
        C'est la méthode la plus rapide !
        
        ---
        
        ## 🆘 Besoin d'aide ?
        
        - Les **expanders** (▶) cachent des détails : cliquez pour déplier
        - Les **tabs** en haut du sidebar permettent de naviguer entre sections
        - Le bouton **🗑️ Réinitialiser session** efface tout et recommence
        """)

def main():
    """Point d'entrée principal"""
    # Initialiser la session
    SessionManager.init()
    
    # Titre
    st.title(f"{APP_CONFIG['icon']} {APP_CONFIG['title']}")
    st.caption(f"Version {APP_CONFIG['version']} par {APP_CONFIG['author']}")
    
    # Manuel d'utilisation sur la page d'accueil
    render_user_manual()
    
    st.divider()
    
    # Afficher le sidebar
    render_sidebar()
    
    # Afficher les résultats complets (plus de section "Configuration rapide")
    render_results()
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"Session: {st.session_state.user_id}")
    with col2:
        st.caption(f"Créée: {st.session_state.created_at.strftime('%Y-%m-%d %H:%M')}")
    with col3:
        if st.button("🗑️ Réinitialiser session"):
            SessionManager.clear()
            st.rerun()

if __name__ == "__main__":
    main()
