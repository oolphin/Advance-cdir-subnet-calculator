# 🌐 Application de Découpage CIDR Avancé - VLAN/VXLAN v3.1

Application web professionnelle pour la planification et le découpage de réseaux IP avec support VLAN et VXLAN.

## ✨ Nouveautés v3.1

### 🔄 Convertisseur de Masques CIDR
Nouvel onglet dédié à la conversion de masques et au calcul d'informations réseau :
- **Conversion manuelle** : Masque ↔ CIDR avec détails complets
- **Traitement en lot** : Import/export de données tabulaires
- **Support Excel** : Enrichissement de fichiers .xlsx

Voir [VERSION_31_NOTES.md](VERSION_31_NOTES.md) pour les détails complets.

## 🎯 Fonctionnalités principales

### 📌 Gestion VLAN/VXLAN
- Création et gestion de VLANs (1-4094)
- Support VXLAN avec VNI (1-16777215)
- Import/export CSV
- Validation automatique

### 🔧 Découpage réseau intelligent
- Calcul automatique de sous-réseaux
- Support masques /8 à /30
- Détection de conflits
- Optimisation de l'espace d'adressage

### 🔄 Convertisseur CIDR (Nouveau !)
- Conversion Masque ↔ CIDR
- Calcul d'informations réseau complètes
- Traitement en lot (CSV, Excel)
- Export des résultats

### 📋 Templates prédéfinis
- 🏢 Datacenter 3-Tier
- 🏫 Réseau Campus
- 🏠 Petite Entreprise
- ☁️ Multi-tenant VXLAN

### 📊 Exports multiples
- Excel (.xlsx) formaté
- CSV (avec séparateur configurable)
- JSON (pour automatisation)

## 🚀 Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run main.py
```

## 📖 Utilisation rapide

### Convertisseur de masques (Nouveau !)
1. **Sidebar** → **🔄 Convertisseur**
2. Entrer IP et masque ou utiliser le slider CIDR
3. Obtenir toutes les informations réseau

### Découpage réseau
1. **Sidebar** → **📌 VLANs** → Importer CSV ou ajouter manuellement
2. **🔧 Découpage** → Configurer réseau de base
3. **🚀 Calculer le découpage**

## 🏗️ Architecture

```
cidr_app_v18_with_converter/
├── main.py                      # Application principale
├── config/settings.py           # Configuration
├── core/
│   ├── network_calculator.py   # Calculs réseau
│   └── vlan_manager.py         # Gestion VLAN/VXLAN
├── services/
│   ├── export_service.py       # Exports
│   └── mask_converter.py       # Conversions CIDR (Nouveau !)
└── utils/
    ├── validators.py           # Validations
    └── logger.py               # Logging
```

## 👤 Auteur

**Guy SOW** - Network & Security Engineer

## 📄 Version

**v3.1** - Février 2026
