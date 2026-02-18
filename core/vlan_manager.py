# core/vlan_manager.py
"""
Gestionnaire de VLANs avec validation et détection de conflits
"""
from typing import List, Dict, Optional, Tuple
from utils.validators import SecurityValidator, ConflictDetector

class VLANManager:
    """Gestionnaire de VLANs avec sécurité renforcée"""
    
    def __init__(self):
        self.vlans: List[Dict] = []
        self.validator = SecurityValidator()
        self.conflict_detector = ConflictDetector()
    
    def add(self, vlan_id: int, name: str, description: str = "", 
            reserved: bool = False) -> Tuple[bool, str]:
        """
        Ajoute un VLAN avec validation
        
        Args:
            vlan_id: ID du VLAN (1-4094)
            name: Nom du VLAN
            description: Description optionnelle
            reserved: Si True, exclu de l'attribution automatique
            
        Returns:
            (succès, message)
        """
        try:
            # Validations
            self.validator.validate_vlan_id(vlan_id)
            clean_name = self.validator.sanitize_name(name)
            clean_desc = self.validator.sanitize_description(description)
            
            # Vérifier l'unicité
            if self.exists(vlan_id):
                return False, f"❌ VLAN {vlan_id} existe déjà"
            
            # Ajouter
            self.vlans.append({
                'vlan_id': vlan_id,
                'name': clean_name.upper(),
                'description': clean_desc,
                'reserved': reserved,
                'type': 'VLAN'
            })
            
            return True, f"✅ VLAN {vlan_id} - {clean_name} ajouté"
            
        except Exception as e:
            return False, f"❌ Erreur: {str(e)}"
    
    def remove(self, vlan_id: int) -> Tuple[bool, str]:
        """Supprime un VLAN"""
        if not self.exists(vlan_id):
            return False, f"❌ VLAN {vlan_id} n'existe pas"
        
        self.vlans = [v for v in self.vlans if v['vlan_id'] != vlan_id]
        return True, f"✅ VLAN {vlan_id} supprimé"
    
    def exists(self, vlan_id: int) -> bool:
        """Vérifie si un VLAN existe"""
        return any(v['vlan_id'] == vlan_id for v in self.vlans)
    
    def get(self, vlan_id: int) -> Optional[Dict]:
        """Récupère un VLAN par son ID"""
        for vlan in self.vlans:
            if vlan['vlan_id'] == vlan_id:
                return vlan
        return None
    
    def get_all(self) -> List[Dict]:
        """Retourne tous les VLANs"""
        return self.vlans.copy()
    
    def get_available(self) -> List[Dict]:
        """Retourne les VLANs non réservés"""
        return [v for v in self.vlans if not v.get('reserved', False)]
    
    def suggest_next_id(self) -> int:
        """Suggère le prochain ID VLAN disponible"""
        if not self.vlans:
            return 10
        
        used_ids = [v['vlan_id'] for v in self.vlans]
        max_id = max(used_ids)
        
        # Trouver le prochain multiple de 10
        next_id = max_id + 10
        next_id = ((next_id + 9) // 10) * 10
        
        # S'assurer qu'il est dans la plage valide
        if next_id > 4094:
            # Chercher un trou dans la séquence
            for candidate in range(10, 4095, 10):
                if candidate not in used_ids:
                    return candidate
            return 10  # Fallback
        
        return next_id
    
    def detect_conflicts(self) -> List[Dict]:
        """Détecte les conflits dans la configuration"""
        return self.conflict_detector.detect_vlan_conflicts(self.vlans)
    
    def import_from_csv(self, csv_data: List[Dict]) -> Tuple[int, List[str]]:
        """
        Importe des VLANs depuis des données CSV
        
        Args:
            csv_data: Liste de dictionnaires avec clés: vlan_id, name, description, reserved
            
        Returns:
            (nombre_importés, liste_erreurs)
        """
        imported = 0
        errors = []
        
        for i, row in enumerate(csv_data, 1):
            try:
                vlan_id = int(row.get('vlan_id', 0))
                name = str(row.get('name', f'VLAN_{vlan_id}'))
                description = str(row.get('description', ''))
                reserved = str(row.get('reserved', 'false')).lower() == 'true'
                
                success, msg = self.add(vlan_id, name, description, reserved)
                
                if success:
                    imported += 1
                else:
                    errors.append(f"Ligne {i}: {msg}")
                    
            except Exception as e:
                errors.append(f"Ligne {i}: Erreur - {str(e)}")
        
        return imported, errors
    
    def import_from_file_content(self, content: str) -> Dict:
        """
        Importe un fichier CSV avec format spécifique incluant les CIDR
        Format: vlan_id,cdir,nom,description,Sous-reseau,gateway,hosts,reserve
        
        Args:
            content: Contenu du fichier CSV
            
        Returns:
            Dictionnaire avec vlans, decoupages_ordonnes, etc.
        """
        import pandas as pd
        from io import StringIO
        
        try:
            df = pd.read_csv(StringIO(content))
            df.columns = df.columns.str.strip()
            
            # Vérifier colonnes requises
            required = ['vlan_id', 'cdir', 'nom']
            for col in required:
                if col not in df.columns:
                    return {'error': f"Colonne '{col}' manquante"}
            
            vlans_importes = []
            decoupages_par_masque = {}
            
            # Compter par masque
            for _, row in df.iterrows():
                cdir = str(row.get('cdir', '')).strip()
                if cdir and cdir.startswith('/'):
                    masque = int(cdir[1:])
                    decoupages_par_masque[masque] = decoupages_par_masque.get(masque, 0) + 1
            
            # Créer les VLANs dans l'ordre
            for idx, row in df.iterrows():
                try:
                    vlan_id = int(row['vlan_id'])
                    cdir = str(row['cdir']).strip()
                    nom = str(row['nom']).strip()
                    description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
                    reserve = str(row.get('reserve', 'False')).strip().lower() == 'true'
                    
                    masque = None
                    if cdir and cdir.startswith('/'):
                        masque = int(cdir[1:])
                    
                    if masque:
                        vlans_importes.append({
                            'vlan_id': vlan_id,
                            'nom': nom.upper(),
                            'nom_original': nom,
                            'description': description,
                            'reserve': reserve,
                            'type': 'VLAN',
                            'masque': masque,
                            'ordre': idx
                        })
                        
                except Exception as e:
                    continue
            
            # Trier par ordre
            vlans_importes.sort(key=lambda x: x['ordre'])
            
            # Créer découpages ordonnés (1 par VLAN)
            decoupages_ordonnes = []
            for vlan in vlans_importes:
                decoupages_ordonnes.append({
                    'nombre': 1,
                    'taille': vlan['masque'],
                    'vlan_associe': vlan['vlan_id'],
                    'nom_vlan': vlan['nom_original']
                })
            
            # Créer découpages groupés par masque
            decoupages_groupes = []
            for masque, count in sorted(decoupages_par_masque.items()):
                decoupages_groupes.append({
                    'nombre': count,
                    'taille': masque
                })
            
            return {
                'vlans': vlans_importes,
                'decoupages_par_masque': decoupages_par_masque,
                'decoupages_ordonnes': decoupages_ordonnes,
                'decoupages_groupes': decoupages_groupes,
                'total_vlans': len(vlans_importes)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def export_to_dict(self) -> List[Dict]:
        """Exporte la configuration en dictionnaire"""
        return [
            {
                'vlan_id': v['vlan_id'],
                'name': v['name'],
                'description': v.get('description', ''),
                'reserved': v.get('reserved', False)
            }
            for v in self.vlans
        ]
    
    def clear(self):
        """Efface tous les VLANs"""
        self.vlans = []
    
    def count(self) -> int:
        """Retourne le nombre de VLANs"""
        return len(self.vlans)
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur les VLANs"""
        total = len(self.vlans)
        reserved = sum(1 for v in self.vlans if v.get('reserved', False))
        available = total - reserved
        
        used_ids = [v['vlan_id'] for v in self.vlans]
        min_id = min(used_ids) if used_ids else 0
        max_id = max(used_ids) if used_ids else 0
        
        return {
            'total': total,
            'reserved': reserved,
            'available': available,
            'min_id': min_id,
            'max_id': max_id,
            'conflicts': len(self.detect_conflicts())
        }


class VXLANManager:
    """Gestionnaire de VXLANs"""
    
    def __init__(self):
        self.vxlans: List[Dict] = []
        self.validator = SecurityValidator()
    
    def add(self, vni: int, name: str, description: str = "",
            mtu: int = 1500, reserved: bool = False) -> Tuple[bool, str]:
        """
        Ajoute un VXLAN
        
        Args:
            vni: VNI (1-16777215)
            name: Nom du VXLAN
            description: Description optionnelle
            mtu: MTU (défaut 1500)
            reserved: Si réservé
            
        Returns:
            (succès, message)
        """
        try:
            # Validations
            self.validator.validate_vni(vni)
            clean_name = self.validator.sanitize_name(name)
            clean_desc = self.validator.sanitize_description(description)
            
            # Vérifier l'unicité
            if self.exists(vni):
                return False, f"❌ VXLAN {vni} existe déjà"
            
            # Générer l'IP multicast
            multicast_ip = self._generate_multicast_ip(vni)
            
            # Ajouter
            self.vxlans.append({
                'vni': vni,
                'name': clean_name.upper(),
                'description': clean_desc,
                'multicast_ip': multicast_ip,
                'mtu': mtu,
                'reserved': reserved,
                'type': 'VXLAN'
            })
            
            return True, f"✅ VXLAN {vni} - {clean_name} ajouté (Multicast: {multicast_ip})"
            
        except Exception as e:
            return False, f"❌ Erreur: {str(e)}"
    
    def remove(self, vni: int) -> Tuple[bool, str]:
        """Supprime un VXLAN"""
        if not self.exists(vni):
            return False, f"❌ VXLAN {vni} n'existe pas"
        
        self.vxlans = [v for v in self.vxlans if v['vni'] != vni]
        return True, f"✅ VXLAN {vni} supprimé"
    
    def exists(self, vni: int) -> bool:
        """Vérifie si un VXLAN existe"""
        return any(v['vni'] == vni for v in self.vxlans)
    
    def get(self, vni: int) -> Optional[Dict]:
        """Récupère un VXLAN par son VNI"""
        for vxlan in self.vxlans:
            if vxlan['vni'] == vni:
                return vxlan
        return None
    
    def get_all(self) -> List[Dict]:
        """Retourne tous les VXLANs"""
        return self.vxlans.copy()
    
    def get_available(self) -> List[Dict]:
        """Retourne les VXLANs non réservés"""
        return [v for v in self.vxlans if not v.get('reserved', False)]
    
    def suggest_next_vni(self) -> int:
        """Suggère le prochain VNI disponible"""
        if not self.vxlans:
            return 10000
        
        used_vnis = [v['vni'] for v in self.vxlans]
        max_vni = max(used_vnis)
        
        # Prochain multiple de 1000
        next_vni = max_vni + 1000
        next_vni = ((next_vni + 999) // 1000) * 1000
        
        if next_vni > 16777215:
            # Chercher un trou
            for candidate in range(10000, 16777216, 1000):
                if candidate not in used_vnis:
                    return candidate
            return 10000
        
        return next_vni
    
    def import_from_file_content(self, content: str) -> Dict:
        """
        Importe un fichier CSV avec format spécifique incluant les CIDR
        Format: vni,cdir,nom,description,mtu,reserve
        
        Args:
            content: Contenu du fichier CSV
            
        Returns:
            Dictionnaire avec vxlans, decoupages_ordonnes, etc.
        """
        import pandas as pd
        from io import StringIO
        
        try:
            df = pd.read_csv(StringIO(content))
            df.columns = df.columns.str.strip()
            
            # Vérifier colonnes requises
            required = ['vni', 'cdir', 'nom']
            for col in required:
                if col not in df.columns:
                    return {'error': f"Colonne '{col}' manquante"}
            
            vxlans_importes = []
            decoupages_par_masque = {}
            
            # Compter par masque
            for _, row in df.iterrows():
                cdir = str(row.get('cdir', '')).strip()
                if cdir and cdir.startswith('/'):
                    masque = int(cdir[1:])
                    decoupages_par_masque[masque] = decoupages_par_masque.get(masque, 0) + 1
            
            # Créer les VXLANs dans l'ordre
            for idx, row in df.iterrows():
                try:
                    vni = int(row['vni'])
                    cdir = str(row['cdir']).strip()
                    nom = str(row['nom']).strip()
                    description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
                    mtu = int(row.get('mtu', 1500)) if pd.notna(row.get('mtu')) else 1500
                    reserve = str(row.get('reserve', 'False')).strip().lower() == 'true'
                    
                    masque = None
                    if cdir and cdir.startswith('/'):
                        masque = int(cdir[1:])
                    
                    if masque:
                        # Générer l'IP multicast
                        multicast_ip = self._generate_multicast_ip(vni)
                        
                        vxlans_importes.append({
                            'vni': vni,
                            'nom': nom.upper(),
                            'nom_original': nom,
                            'description': description,
                            'mtu': mtu,
                            'multicast_ip': multicast_ip,
                            'reserve': reserve,
                            'type': 'VXLAN',
                            'masque': masque,
                            'ordre': idx
                        })
                        
                except Exception as e:
                    continue
            
            # Trier par ordre
            vxlans_importes.sort(key=lambda x: x['ordre'])
            
            # Créer découpages ordonnés (1 par VXLAN)
            decoupages_ordonnes = []
            for vxlan in vxlans_importes:
                decoupages_ordonnes.append({
                    'nombre': 1,
                    'taille': vxlan['masque'],
                    'vxlan_associe': vxlan['vni'],
                    'nom_vxlan': vxlan['nom_original']
                })
            
            # Créer découpages groupés par masque
            decoupages_groupes = []
            for masque, count in sorted(decoupages_par_masque.items()):
                decoupages_groupes.append({
                    'nombre': count,
                    'taille': masque
                })
            
            return {
                'vxlans': vxlans_importes,
                'decoupages_par_masque': decoupages_par_masque,
                'decoupages_ordonnes': decoupages_ordonnes,
                'decoupages_groupes': decoupages_groupes,
                'total_vxlans': len(vxlans_importes)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_multicast_ip(self, vni: int) -> str:
        """Génère l'adresse IP multicast pour un VNI"""
        octet3 = (vni >> 8) & 0xFF
        octet4 = vni & 0xFF
        return f"239.0.{octet3}.{octet4}"
    
    def import_from_csv(self, csv_data: List[Dict]) -> Tuple[int, List[str]]:
        """Importe des VXLANs depuis CSV"""
        imported = 0
        errors = []
        
        for i, row in enumerate(csv_data, 1):
            try:
                vni = int(row.get('vni', 0))
                name = str(row.get('name', f'VXLAN_{vni}'))
                description = str(row.get('description', ''))
                mtu = int(row.get('mtu', 1500))
                reserved = str(row.get('reserved', 'false')).lower() == 'true'
                
                success, msg = self.add(vni, name, description, mtu, reserved)
                
                if success:
                    imported += 1
                else:
                    errors.append(f"Ligne {i}: {msg}")
                    
            except Exception as e:
                errors.append(f"Ligne {i}: Erreur - {str(e)}")
        
        return imported, errors
    
    def export_to_dict(self) -> List[Dict]:
        """Exporte la configuration"""
        return [
            {
                'vni': v['vni'],
                'name': v['name'],
                'description': v.get('description', ''),
                'multicast_ip': v['multicast_ip'],
                'mtu': v.get('mtu', 1500),
                'reserved': v.get('reserved', False)
            }
            for v in self.vxlans
        ]
    
    def clear(self):
        """Efface tous les VXLANs"""
        self.vxlans = []
    
    def count(self) -> int:
        """Retourne le nombre de VXLANs"""
        return len(self.vxlans)
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques"""
        total = len(self.vxlans)
        reserved = sum(1 for v in self.vxlans if v.get('reserved', False))
        available = total - reserved
        
        used_vnis = [v['vni'] for v in self.vxlans]
        min_vni = min(used_vnis) if used_vnis else 0
        max_vni = max(used_vnis) if used_vnis else 0
        
        return {
            'total': total,
            'reserved': reserved,
            'available': available,
            'min_vni': min_vni,
            'max_vni': max_vni
        }
