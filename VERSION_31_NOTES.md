# Version 3.1 - Notes de version

## 🆕 Nouveautés

### Onglet Convertisseur de Masques CIDR

Ajout d'un nouvel onglet **🔄 Convertisseur** dans la sidebar avec trois fonctionnalités principales :

#### 1. **Conversion Manuelle** (🔢)
- Conversion bidirectionnelle Masque ↔ CIDR
- Calcul détaillé des informations réseau :
  - Adresse réseau
  - Adresse de broadcast
  - Plage d'IPs hôtes utilisables
  - Nombre d'hôtes disponibles
  - Première et dernière IP hôte
- Interface intuitive avec deux colonnes :
  - Gauche : Masque → CIDR
  - Droite : CIDR → Masque (avec slider)

#### 2. **Traitement en Lot** (📋)
- Importation de données au format texte (copier-coller)
- Support de séparateurs multiples (tabulation, point-virgule)
- Traitement de plusieurs lignes IP/Masque simultanément
- Export CSV des résultats
- Affichage en tableau avec toutes les informations réseau

#### 3. **Import/Export Excel** (📁)
- Import de fichiers `.xlsx`
- Détection automatique des colonnes IP et Masque
- Enrichissement du fichier avec :
  - Notation CIDR
  - Adresse réseau
  - Adresse de broadcast
  - Nombre d'hôtes
- Export du fichier enrichi au format Excel

## 🔧 Améliorations techniques

### Nouveau module `services/mask_converter.py`
- **Classe MaskConverter** avec méthodes statiques :
  - `mask_to_cidr()` : Conversion masque → CIDR
  - `cidr_to_mask()` : Conversion CIDR → masque
  - `ip_to_cidr()` : Combinaison IP + masque → notation CIDR
  - `network_address()` : Calcul adresse réseau
  - `broadcast_address()` : Calcul adresse broadcast
  - `host_count()` : Calcul nombre d'hôtes disponibles
  - `get_network_info()` : Informations réseau complètes
  - `process_batch()` : Traitement en lot
  - `process_excel()` : Traitement fichiers Excel

### Architecture
- Intégration propre dans l'architecture modulaire existante
- Réutilisation des composants (export, validation)
- Pas de régression sur les fonctionnalités existantes

## 📊 Cas d'usage

### Administrateurs réseau
- Conversion rapide masque → CIDR pour documentation
- Vérification des calculs de sous-réseaux
- Planification d'adressage IP

### Auditeurs et analystes
- Traitement en masse de configurations réseau
- Import de fichiers d'inventaire réseau
- Export de rapports enrichis

### Migration et intégration
- Conversion de configurations anciennes
- Préparation de données pour import dans des outils tiers
- Validation de plans d'adressage

## 🎯 Utilisation

### Accès
1. Ouvrir l'application
2. Cliquer sur l'onglet **🔄 Convertisseur** dans la sidebar
3. Choisir le mode de conversion souhaité

### Exemple - Conversion manuelle
1. Entrer l'IP : `192.152.0.0`
2. Entrer le masque : `255.255.0.0`
3. Cliquer sur **🔄 Convertir**
4. Résultat : `192.152.0.0/16` avec détails complets

### Exemple - Traitement en lot
```
IP          Masque
12.0.0.0    255.255.255.0
192.168.1.0 255.255.255.128
112.16.0.0  255.255.0.0
```
→ Génère un tableau avec CIDR, réseau, broadcast, hosts pour chaque ligne

## ⚙️ Configuration requise

### Dépendances (déjà présentes)
- Python 3.8+
- streamlit
- pandas
- openpyxl (pour Excel)

### Fichiers modifiés
- `main.py` : Ajout onglet et fonction `render_mask_converter()`
- `config/settings.py` : Version 3.0 → 3.1
- Nouveau : `services/mask_converter.py`

## 🔄 Migration depuis v3.0

Aucune action requise. L'onglet Convertisseur s'ajoute automatiquement aux fonctionnalités existantes sans affecter :
- La gestion des VLANs/VXLANs
- Le découpage de réseaux
- Les templates
- Les exports

## 📝 Notes

- Le convertisseur fonctionne indépendamment du module de découpage CIDR principal
- Les résultats de conversion ne sont pas stockés dans l'historique de session
- Parfait pour des vérifications rapides sans modifier la configuration principale
- Compatible avec toutes les classes de réseaux (A, B, C)

## 🚀 Prochaines étapes suggérées

- [ ] Ajout de la validation des adresses IP privées/publiques
- [ ] Calcul de superréseaux (agrégation CIDR)
- [ ] Support de IPv6
- [ ] Sauvegarde des conversions dans l'historique
- [ ] Export direct vers fichier Cisco/Juniper format
