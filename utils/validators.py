# utils/validators.py
"""
Validation et sanitization sécurisées
"""
import re
import ipaddress
from html import escape
from typing import Tuple, Optional
from config.settings import SECURITY_LIMITS

class ValidationError(Exception):
    """Exception pour erreurs de validation"""
    pass

class SecurityValidator:
    """Validateur avec sécurité renforcée"""
    
    @staticmethod
    def validate_vlan_id(vlan_id: int) -> bool:
        """Valide un ID VLAN"""
        if not isinstance(vlan_id, int):
            raise ValidationError("VLAN ID doit être un entier")
        
        if not (SECURITY_LIMITS['min_vlan_id'] <= vlan_id <= SECURITY_LIMITS['max_vlan_id']):
            raise ValidationError(
                f"VLAN ID doit être entre {SECURITY_LIMITS['min_vlan_id']} "
                f"et {SECURITY_LIMITS['max_vlan_id']}"
            )
        
        if vlan_id in SECURITY_LIMITS['reserved_vlans']:
            raise ValidationError(
                f"VLAN {vlan_id} est réservé (standard 802.1Q)"
            )
        
        return True
    
    @staticmethod
    def validate_vni(vni: int) -> bool:
        """Valide un VNI VXLAN"""
        if not isinstance(vni, int):
            raise ValidationError("VNI doit être un entier")
        
        if not (SECURITY_LIMITS['min_vni'] <= vni <= SECURITY_LIMITS['max_vni']):
            raise ValidationError(
                f"VNI doit être entre {SECURITY_LIMITS['min_vni']} "
                f"et {SECURITY_LIMITS['max_vni']}"
            )
        
        return True
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Nettoie et valide un nom"""
        if not name:
            raise ValidationError("Le nom ne peut pas être vide")
        
        # Longueur maximale
        if len(name) > SECURITY_LIMITS['max_name_length']:
            raise ValidationError(
                f"Nom trop long (max {SECURITY_LIMITS['max_name_length']} caractères)"
            )
        
        # Caractères autorisés : alphanumériques, underscore, tiret, espace
        if not re.match(r'^[A-Za-z0-9_\- ]+$', name):
            raise ValidationError(
                "Caractères non autorisés. Utilisez uniquement lettres, chiffres, _, - et espaces"
            )
        
        # Mots réservés
        reserved_words = ['DROP', 'DELETE', 'INSERT', 'SCRIPT', 'EXEC', 'EVAL']
        if name.upper() in reserved_words:
            raise ValidationError(f"Nom réservé non autorisé: {name}")
        
        # Échappement HTML
        return escape(name.strip())
    
    @staticmethod
    def sanitize_description(description: str) -> str:
        """Nettoie et valide une description"""
        if len(description) > SECURITY_LIMITS['max_description_length']:
            raise ValidationError(
                f"Description trop longue (max {SECURITY_LIMITS['max_description_length']} caractères)"
            )
        
        return escape(description.strip())
    
    @staticmethod
    def validate_network(network: str) -> Tuple[bool, Optional[str]]:
        """Valide un réseau CIDR"""
        try:
            net = ipaddress.ip_network(network, strict=False)
            
            # Vérifier que c'est une plage raisonnable
            if net.prefixlen < 8:
                return False, "Masque trop petit (minimum /8)"
            
            if net.prefixlen > 32:
                return False, "Masque invalide (maximum /32)"
            
            return True, None
            
        except ValueError as e:
            return False, f"Format CIDR invalide: {str(e)}"
    
    @staticmethod
    def validate_csv_content(content: bytes) -> Tuple[bool, Optional[str]]:
        """Valide le contenu d'un fichier CSV"""
        # Taille maximale
        if len(content) > SECURITY_LIMITS['max_csv_size']:
            return False, f"Fichier trop volumineux (max {SECURITY_LIMITS['max_csv_size'] // (1024*1024)} MB)"
        
        # Convertir en string
        try:
            text = content.decode('utf-8')
        except:
            return False, "Encodage invalide (UTF-8 requis)"
        
        # Patterns dangereux
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',  # onclick, onload, etc.
            r'eval\(',
            r'exec\(',
            r'__import__',
            r'subprocess',
            r'os\.system'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "Contenu potentiellement dangereux détecté"
        
        return True, None
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Valide une adresse IP"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

class ConflictDetector:
    """Détecteur de conflits dans la configuration"""
    
    @staticmethod
    def detect_vlan_conflicts(vlans_config: list) -> list:
        """Détecte les conflits dans la configuration VLAN"""
        conflicts = []
        
        # IDs dupliqués
        vlan_ids = [v['vlan_id'] for v in vlans_config]
        duplicates = {id_: vlan_ids.count(id_) for id_ in set(vlan_ids) if vlan_ids.count(id_) > 1}
        
        for vlan_id, count in duplicates.items():
            conflicts.append({
                'type': 'ID_DUPLICATE',
                'severity': 'CRITICAL',
                'message': f"VLAN ID {vlan_id} utilisé {count} fois",
                'action': 'Supprimer les doublons'
            })
        
        # VLANs réservés
        for vlan in vlans_config:
            if vlan['vlan_id'] in SECURITY_LIMITS['reserved_vlans']:
                conflicts.append({
                    'type': 'VLAN_RESERVED',
                    'severity': 'WARNING',
                    'message': f"VLAN {vlan['vlan_id']} est réservé",
                    'action': 'Vérifier si intentionnel'
                })
        
        return conflicts
    
    @staticmethod
    def detect_subnet_overlaps(subnets: list) -> list:
        """Détecte les chevauchements de sous-réseaux"""
        conflicts = []
        networks = []
        
        for i, subnet_str in enumerate(subnets):
            try:
                net = ipaddress.ip_network(subnet_str)
                
                # Vérifier contre tous les autres
                for j, other_net in enumerate(networks):
                    if net.overlaps(other_net):
                        conflicts.append({
                            'type': 'SUBNET_OVERLAP',
                            'severity': 'CRITICAL',
                            'message': f"Chevauchement: {net} et {other_net}",
                            'indices': [i, j]
                        })
                
                networks.append(net)
            except:
                conflicts.append({
                    'type': 'INVALID_SUBNET',
                    'severity': 'CRITICAL',
                    'message': f"Sous-réseau invalide: {subnet_str}",
                    'index': i
                })
        
        return conflicts
    
    @staticmethod
    def validate_gateway_in_network(gateway: str, network: str) -> bool:
        """Valide que la gateway est dans le réseau"""
        try:
            gw = ipaddress.ip_address(gateway)
            net = ipaddress.ip_network(network)
            return gw in net
        except:
            return False
