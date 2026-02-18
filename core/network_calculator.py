# core/network_calculator.py
"""
Calculateur réseau optimisé avec caching
"""
import ipaddress
from typing import List, Dict, Any, Optional
from functools import lru_cache
import hashlib
import json

class NetworkCalculator:
    """Calculateur de réseaux IP avec optimisations"""
    
    def __init__(self, base_network: str):
        """
        Initialise le calculateur avec un réseau de base
        
        Args:
            base_network: Réseau CIDR (ex: "10.0.0.0/21")
        """
        self.base_network = ipaddress.ip_network(base_network, strict=False)
        self._cache = {}
    
    @staticmethod
    @lru_cache(maxsize=128)
    def calculate_subnet_params(subnet_str: str) -> Dict[str, Any]:
        """
        Calcule tous les paramètres d'un sous-réseau (avec cache)
        
        Args:
            subnet_str: Sous-réseau au format CIDR
            
        Returns:
            Dictionnaire avec tous les paramètres
        """
        subnet = ipaddress.ip_network(subnet_str, strict=False)
        hosts = list(subnet.hosts())
        
        # Cas spéciaux
        if subnet.prefixlen == 31:  # RFC 3021 - point-to-point
            usable_hosts = 2
            first_host = str(subnet.network_address)
            last_host = str(subnet.broadcast_address)
            gateway = last_host  # Gateway = dernière IP
        elif subnet.prefixlen == 32:  # Host route
            usable_hosts = 1
            first_host = str(subnet.network_address)
            last_host = first_host
            gateway = first_host
        else:
            usable_hosts = len(hosts)
            first_host = str(hosts[0]) if hosts else "N/A"
            last_host = str(hosts[-1]) if hosts else "N/A"
            gateway = last_host  # IMPORTANT: Gateway = dernière IP utilisable
            # Plage IP exclut la gateway
            last_usable = str(hosts[-2]) if len(hosts) > 1 else first_host
        
        return {
            'network': str(subnet.network_address),
            'cidr': str(subnet),
            'netmask': str(subnet.netmask),
            'prefix_length': subnet.prefixlen,
            'broadcast': str(subnet.broadcast_address),
            'first_host': first_host,
            'last_host': last_host,
            'gateway': gateway,  # Toujours la dernière IP utilisable
            'total_hosts': subnet.num_addresses,
            'usable_hosts': usable_hosts,
            'ip_range': f"{first_host} → {last_usable}" if first_host != "N/A" else "N/A"  # EXCLUT gateway
        }
    
    def generate_subnets(self, prefix_length: int, count: int) -> List[ipaddress.IPv4Network]:
        """
        Génère une liste de sous-réseaux
        
        Args:
            prefix_length: Longueur du masque (ex: 24 pour /24)
            count: Nombre de sous-réseaux à générer
            
        Returns:
            Liste de sous-réseaux IPv4Network
        """
        if prefix_length <= self.base_network.prefixlen:
            raise ValueError(
                f"Le masque /{prefix_length} doit être plus grand que "
                f"/{self.base_network.prefixlen}"
            )
        
        all_subnets = list(self.base_network.subnets(new_prefix=prefix_length))
        
        if count > len(all_subnets):
            raise ValueError(
                f"Impossible de créer {count} sous-réseaux /{prefix_length} "
                f"(maximum: {len(all_subnets)})"
            )
        
        return all_subnets[:count]
    
    def calculate_subnet_by_hosts(self, required_hosts: int) -> int:
        """
        Calcule la taille de masque nécessaire pour un nombre d'hôtes
        
        Args:
            required_hosts: Nombre d'hôtes requis
            
        Returns:
            Longueur de masque appropriée
        """
        # Trouver le masque qui permet au moins required_hosts + 2 (network + broadcast)
        for prefix in range(32, self.base_network.prefixlen, -1):
            subnet_size = 2 ** (32 - prefix)
            usable = subnet_size - 2
            
            if usable >= required_hosts:
                return prefix
        
        raise ValueError(
            f"Impossible d'allouer {required_hosts} hôtes dans {self.base_network}"
        )
    
    def split_network(self, configurations: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        """
        Découpe le réseau selon plusieurs configurations
        AVEC alignement correct pour éviter les chevauchements
        
        Args:
            configurations: Liste de configs [{'nombre': 3, 'taille': 24}, ...]
            
        Returns:
            Liste de sous-réseaux avec leurs paramètres et l'index de configuration
        """
        results = []
        current_ip = self.base_network.network_address
        
        # NE PAS TRIER - Suivre l'ordre exact des configurations
        for config_idx, config in enumerate(configurations):
            count = config['nombre']
            prefix_length = config['taille']
            
            for i in range(count):
                # Créer le sous-réseau
                try:
                    # Aligner l'IP sur la taille du sous-réseau pour éviter les chevauchements
                    subnet_size = 2 ** (32 - prefix_length)
                    current_int = int(current_ip)
                    
                    # Si l'IP n'est pas alignée, passer à la prochaine adresse alignée
                    if current_int % subnet_size != 0:
                        current_int = ((current_int // subnet_size) + 1) * subnet_size
                        current_ip = ipaddress.ip_address(current_int)
                    
                    # Créer le sous-réseau avec strict=True (pas d'arrondi arrière)
                    subnet = ipaddress.ip_network(
                        f"{current_ip}/{prefix_length}",
                        strict=True
                    )
                    
                    # Vérifier qu'on ne dépasse pas
                    if subnet.broadcast_address > self.base_network.broadcast_address:
                        raise ValueError("Capacité du réseau de base dépassée")
                    
                    # Calculer les paramètres
                    params = self.calculate_subnet_params(str(subnet))
                    params['config_index'] = config_idx  # Index de la configuration
                    params['subnet_index_in_config'] = i  # Index au sein de cette config
                    params['global_index'] = len(results)  # Index global
                    params['prefix_length'] = prefix_length
                    
                    results.append(params)
                    
                    # IMPORTANT : Passer à l'adresse APRÈS le broadcast
                    current_ip = subnet.broadcast_address + 1
                    
                except Exception as e:
                    raise ValueError(f"Erreur lors de la création du sous-réseau {i+1}: {str(e)}")
        
        return results
        
        return results
    
    def get_available_space(self, used_subnets: List[str]) -> List[ipaddress.IPv4Network]:
        """
        Calcule l'espace disponible après allocation
        
        Args:
            used_subnets: Liste des sous-réseaux utilisés (format CIDR)
            
        Returns:
            Liste des espaces libres
        """
        used_networks = [ipaddress.ip_network(s) for s in used_subnets]
        used_networks.sort(key=lambda x: x.network_address)
        
        available = []
        current_ip = self.base_network.network_address
        
        for used_net in used_networks:
            if current_ip < used_net.network_address:
                # Il y a un espace libre
                available.append(ipaddress.ip_network(
                    f"{current_ip}/{self.base_network.prefixlen}",
                    strict=False
                ))
            
            current_ip = used_net.broadcast_address + 1
        
        # Vérifier l'espace après le dernier
        if current_ip <= self.base_network.broadcast_address:
            available.append(ipaddress.ip_network(
                f"{current_ip}/{self.base_network.prefixlen}",
                strict=False
            ))
        
        return available
    
    def calculate_statistics(self, subnets: List[str]) -> Dict[str, Any]:
        """
        Calcule les statistiques d'utilisation
        
        Args:
            subnets: Liste des sous-réseaux utilisés
            
        Returns:
            Dictionnaire de statistiques
        """
        total_ips = self.base_network.num_addresses
        used_ips = sum(
            ipaddress.ip_network(s).num_addresses 
            for s in subnets
        )
        
        return {
            'base_network': str(self.base_network),
            'total_ips': total_ips,
            'used_ips': used_ips,
            'free_ips': total_ips - used_ips,
            'utilization': (used_ips / total_ips) * 100 if total_ips > 0 else 0,
            'subnet_count': len(subnets),
            'efficiency': self._calculate_efficiency(subnets)
        }
    
    def _calculate_efficiency(self, subnets: List[str]) -> float:
        """Calcule l'efficacité de l'allocation (absence de fragmentation)"""
        if not subnets:
            return 100.0
        
        # Trier les sous-réseaux
        networks = sorted(
            [ipaddress.ip_network(s) for s in subnets],
            key=lambda x: x.network_address
        )
        
        # Calculer les gaps
        gaps = 0
        for i in range(len(networks) - 1):
            expected_next = networks[i].broadcast_address + 1
            actual_next = networks[i + 1].network_address
            
            if expected_next != actual_next:
                gaps += int(actual_next) - int(expected_next)
        
        # Efficacité = (total - gaps) / total * 100
        total = self.base_network.num_addresses
        efficiency = ((total - gaps) / total) * 100 if total > 0 else 0
        
        return round(efficiency, 2)
    
    @staticmethod
    def get_cache_key(base_network: str, configurations: List[Dict]) -> str:
        """Génère une clé de cache unique pour une configuration"""
        config_str = json.dumps({
            'base': base_network,
            'configs': sorted(configurations, key=lambda x: (x['taille'], x['nombre']))
        }, sort_keys=True)
        
        return hashlib.md5(config_str.encode()).hexdigest()
