# services/mask_converter.py
"""
Service de conversion CIDR ↔ Masque
Fonctionnalités de calcul réseau et conversion
"""
import pandas as pd
import io
from typing import Optional, Dict, List


class MaskConverter:
    """Convertisseur de masques de sous-réseau"""
    
    @staticmethod
    def mask_to_cidr(mask: str) -> Optional[int]:
        """
        Convertit un masque en notation CIDR
        
        Args:
            mask: Masque au format xxx.xxx.xxx.xxx
            
        Returns:
            Préfixe CIDR ou None si invalide
        """
        try:
            return sum(bin(int(o))[2:].zfill(8).count('1') for o in mask.split('.'))
        except Exception:
            return None
    
    @staticmethod
    def cidr_to_mask(cidr: int) -> str:
        """
        Convertit un préfixe CIDR en masque
        
        Args:
            cidr: Préfixe CIDR (0-32)
            
        Returns:
            Masque au format xxx.xxx.xxx.xxx
        """
        if not 0 <= cidr <= 32:
            raise ValueError("CIDR doit être entre 0 et 32")
        
        bits = ('1' * cidr).ljust(32, '0')
        return '.'.join(str(int(bits[i:i+8], 2)) for i in range(0, 32, 8))
    
    @staticmethod
    def ip_to_cidr(ip: str, mask: str) -> Optional[str]:
        """
        Convertit IP + Masque en notation CIDR
        
        Args:
            ip: Adresse IP
            mask: Masque de sous-réseau
            
        Returns:
            Notation CIDR (ex: 192.168.1.0/24) ou None
        """
        cidr = MaskConverter.mask_to_cidr(mask)
        return f"{ip}/{cidr}" if cidr is not None else None
    
    @staticmethod
    def network_address(ip: str, mask: str) -> str:
        """
        Calcule l'adresse réseau
        
        Args:
            ip: Adresse IP
            mask: Masque de sous-réseau
            
        Returns:
            Adresse réseau
        """
        parts_ip = [int(x) for x in ip.split('.')]
        parts_mask = [int(x) for x in mask.split('.')]
        return '.'.join(str(a & b) for a, b in zip(parts_ip, parts_mask))
    
    @staticmethod
    def broadcast_address(ip: str, mask: str) -> str:
        """
        Calcule l'adresse de broadcast
        
        Args:
            ip: Adresse IP
            mask: Masque de sous-réseau
            
        Returns:
            Adresse de broadcast
        """
        parts_ip = [int(x) for x in ip.split('.')]
        parts_mask = [int(x) for x in mask.split('.')]
        return '.'.join(str((a & b) | (~b & 0xFF)) for a, b in zip(parts_ip, parts_mask))
    
    @staticmethod
    def host_count(cidr: int) -> int:
        """
        Calcule le nombre d'hôtes disponibles
        
        Args:
            cidr: Préfixe CIDR
            
        Returns:
            Nombre d'hôtes disponibles
        """
        if cidr >= 32:
            return 0
        hosts = 2 ** (32 - cidr) - 2
        return max(hosts, 0)
    
    @staticmethod
    def get_network_info(ip: str, mask: str) -> Dict:
        """
        Retourne toutes les informations réseau
        
        Args:
            ip: Adresse IP
            mask: Masque de sous-réseau
            
        Returns:
            Dictionnaire avec toutes les infos
        """
        cidr = MaskConverter.mask_to_cidr(mask)
        if cidr is None:
            return {'error': 'Masque invalide'}
        
        network = MaskConverter.network_address(ip, mask)
        broadcast = MaskConverter.broadcast_address(ip, mask)
        hosts = MaskConverter.host_count(cidr)
        
        return {
            'ip': ip,
            'mask': mask,
            'cidr': cidr,
            'notation_cidr': f"{network}/{cidr}",
            'network': network,
            'broadcast': broadcast,
            'hosts': hosts,
            'first_host': MaskConverter._increment_ip(network),
            'last_host': MaskConverter._decrement_ip(broadcast)
        }
    
    @staticmethod
    def _increment_ip(ip: str) -> str:
        """Incrémente une IP de 1"""
        parts = [int(x) for x in ip.split('.')]
        parts[3] += 1
        for i in range(3, 0, -1):
            if parts[i] > 255:
                parts[i] = 0
                parts[i-1] += 1
        return '.'.join(str(p) for p in parts)
    
    @staticmethod
    def _decrement_ip(ip: str) -> str:
        """Décrémente une IP de 1"""
        parts = [int(x) for x in ip.split('.')]
        parts[3] -= 1
        for i in range(3, 0, -1):
            if parts[i] < 0:
                parts[i] = 255
                parts[i-1] -= 1
        return '.'.join(str(p) for p in parts)
    
    @staticmethod
    def process_batch(data: str, separator: str = '\t') -> pd.DataFrame:
        """
        Traite des données en lot
        
        Args:
            data: Données brutes (IP\tMasque)
            separator: Séparateur de colonnes
            
        Returns:
            DataFrame avec les résultats
        """
        df = pd.read_csv(io.StringIO(data), sep=separator)
        df.columns = ['IP', 'Masque'] + list(df.columns[2:])
        
        # Calculs
        df['CIDR'] = df.apply(
            lambda r: MaskConverter.ip_to_cidr(str(r['IP']), str(r['Masque'])), 
            axis=1
        )
        df['Réseau'] = df.apply(
            lambda r: MaskConverter.network_address(str(r['IP']), str(r['Masque'])), 
            axis=1
        )
        df['Broadcast'] = df.apply(
            lambda r: MaskConverter.broadcast_address(str(r['IP']), str(r['Masque'])), 
            axis=1
        )
        df['Hosts'] = df.apply(
            lambda r: MaskConverter.host_count(MaskConverter.mask_to_cidr(str(r['Masque']))), 
            axis=1
        )
        
        return df
    
    @staticmethod
    def process_excel(df: pd.DataFrame, col_ip: str, col_mask: str) -> pd.DataFrame:
        """
        Traite un fichier Excel
        
        Args:
            df: DataFrame d'entrée
            col_ip: Nom de la colonne IP
            col_mask: Nom de la colonne Masque
            
        Returns:
            DataFrame enrichi
        """
        df['CIDR'] = df.apply(
            lambda r: MaskConverter.ip_to_cidr(str(r[col_ip]), str(r[col_mask])), 
            axis=1
        )
        df['Réseau'] = df.apply(
            lambda r: MaskConverter.network_address(str(r[col_ip]), str(r[col_mask])), 
            axis=1
        )
        df['Broadcast'] = df.apply(
            lambda r: MaskConverter.broadcast_address(str(r[col_ip]), str(r[col_mask])), 
            axis=1
        )
        df['Hosts'] = df.apply(
            lambda r: MaskConverter.host_count(MaskConverter.mask_to_cidr(str(r[col_mask]))), 
            axis=1
        )
        
        return df
