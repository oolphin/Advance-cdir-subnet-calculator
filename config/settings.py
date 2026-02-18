# config/settings.py
"""
Configuration centralisée de l'application
"""
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SSL_DIR = BASE_DIR / "ssl"

# Créer les répertoires si nécessaire
for directory in [DATA_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Configuration de l'application
APP_CONFIG = {
    "title": "Découpage CIDR Avancé - VLAN/VXLAN",
    "version": "3.1",
    "author": "Guy SOW",
    "icon": "🌐",
    "layout": "wide"
}

# Limites de sécurité
SECURITY_LIMITS = {
    "max_vlan_id": 4094,
    "min_vlan_id": 1,
    "max_vni": 16777215,
    "min_vni": 1,
    "max_name_length": 50,
    "max_description_length": 200,
    "max_csv_size": 5 * 1024 * 1024,  # 5 MB
    "max_subnets": 1000,
    "reserved_vlans": [1, 1002, 1003, 1004, 1005]
}

# Configuration de session
SESSION_CONFIG = {
    "max_history": 20,
    "cache_ttl": 3600,  # 1 heure
    "session_timeout": 86400  # 24 heures
}

# Configuration HTTPS
HTTPS_CONFIG = {
    "cert_paths": [
        (SSL_DIR / "cert.pem", SSL_DIR / "key.pem"),
        ("/etc/ssl/certs/streamlit.crt", "/etc/ssl/private/streamlit.key"),
        ("/etc/letsencrypt/live/domain/fullchain.pem", "/etc/letsencrypt/live/domain/privkey.pem")
    ]
}

# Configuration base de données (SQLite par défaut)
DATABASE_CONFIG = {
    "type": os.getenv("DB_TYPE", "sqlite"),
    "sqlite_path": DATA_DIR / "cidr_app.db",
    "postgres": {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "cidr_app"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "")
    }
}

# Configuration d'authentification
AUTH_CONFIG = {
    "enabled": os.getenv("AUTH_ENABLED", "false").lower() == "true",
    "cookie_name": "cidr_app_auth",
    "cookie_key": os.getenv("AUTH_COOKIE_KEY", "cidr_app_secret_key_change_in_production"),
    "cookie_expiry_days": 30,
    "default_users": {
        "admin": {
            "name": "Administrator",
            "password": "admin123",  # À changer en production
            "role": "admin"
        }
    }
}

# Configuration logging
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOGS_DIR / "app.log",
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5
}

# Configuration export
EXPORT_CONFIG = {
    "excel_max_rows": 100000,
    "enable_encryption": True,
    "compression": True
}

# Templates prédéfinis
TEMPLATES = {
    'datacenter_3tier': {
        'nom': '🏢 Datacenter 3-Tier',
        'description': 'Architecture datacenter classique (Web/App/DB)',
        'reseau_base': '10.0.0.0/22',
        'network_type': 'VLAN',
        'vlans': [
            {'vlan_id': 10, 'nom': 'WEB_DMZ', 'description': 'Web servers DMZ', 'cdir': '/25'},
            {'vlan_id': 11, 'nom': 'WEB_BACKEND', 'description': 'Web backend', 'cdir': '/25'},
            {'vlan_id': 20, 'nom': 'APP_TIER', 'description': 'Application tier', 'cdir': '/25'},
            {'vlan_id': 21, 'nom': 'APP_CACHE', 'description': 'Application cache', 'cdir': '/26'},
            {'vlan_id': 22, 'nom': 'APP_QUEUE', 'description': 'Message queue', 'cdir': '/26'},
            {'vlan_id': 30, 'nom': 'DB_PRIMARY', 'description': 'Database primary', 'cdir': '/26'},
            {'vlan_id': 31, 'nom': 'DB_REPLICA', 'description': 'Database replica', 'cdir': '/26'},
            {'vlan_id': 40, 'nom': 'MGMT', 'description': 'Management network', 'cdir': '/27'},
        ],
        'decoupages': [
            {'nombre': 1, 'taille': 25},  # WEB_DMZ
            {'nombre': 1, 'taille': 25},  # WEB_BACKEND
            {'nombre': 1, 'taille': 25},  # APP_TIER
            {'nombre': 1, 'taille': 26},  # APP_CACHE
            {'nombre': 1, 'taille': 26},  # APP_QUEUE
            {'nombre': 1, 'taille': 26},  # DB_PRIMARY
            {'nombre': 1, 'taille': 26},  # DB_REPLICA
            {'nombre': 1, 'taille': 27},  # MGMT
        ]
    },
    'campus_network': {
        'nom': '🏫 Réseau Campus',
        'description': 'Segmentation pour campus universitaire/entreprise',
        'reseau_base': '172.16.0.0/16',
        'network_type': 'VLAN',
        'vlans': [
            {'vlan_id': 10, 'nom': 'ADMIN', 'description': 'Administration', 'cdir': '/24'},
            {'vlan_id': 20, 'nom': 'STAFF', 'description': 'Personnel', 'cdir': '/23'},
            {'vlan_id': 30, 'nom': 'STUDENTS', 'description': 'Étudiants', 'cdir': '/22'},
            {'vlan_id': 40, 'nom': 'GUESTS', 'description': 'Invités WiFi', 'cdir': '/24'},
            {'vlan_id': 50, 'nom': 'IOT', 'description': 'Devices IoT', 'cdir': '/25'},
            {'vlan_id': 60, 'nom': 'SERVERS', 'description': 'Serveurs', 'cdir': '/25'},
        ],
        'decoupages': [
            {'nombre': 1, 'taille': 24},  # ADMIN
            {'nombre': 1, 'taille': 23},  # STAFF
            {'nombre': 1, 'taille': 22},  # STUDENTS
            {'nombre': 1, 'taille': 24},  # GUESTS
            {'nombre': 1, 'taille': 25},  # IOT
            {'nombre': 1, 'taille': 25},  # SERVERS
        ]
    },
    'small_office': {
        'nom': '🏠 Petite Entreprise',
        'description': 'Configuration simple pour PME',
        'reseau_base': '192.168.1.0/24',
        'network_type': 'VLAN',
        'vlans': [
            {'vlan_id': 10, 'nom': 'PROD', 'description': 'Production', 'cdir': '/26'},
            {'vlan_id': 20, 'nom': 'GUEST', 'description': 'WiFi invités', 'cdir': '/27'},
            {'vlan_id': 30, 'nom': 'SERVERS', 'description': 'Serveurs', 'cdir': '/28'},
            {'vlan_id': 40, 'nom': 'MGMT', 'description': 'Management', 'cdir': '/28'},
        ],
        'decoupages': [
            {'nombre': 1, 'taille': 26},  # PROD (62 hosts)
            {'nombre': 1, 'taille': 27},  # GUEST (30 hosts)
            {'nombre': 1, 'taille': 28},  # SERVERS (14 hosts)
            {'nombre': 1, 'taille': 28},  # MGMT (14 hosts)
        ]
    },
    'multi_tenant_vxlan': {
        'nom': '☁️ Multi-tenant VXLAN',
        'description': 'Infrastructure cloud multi-locataire',
        'reseau_base': '192.168.0.0/16',
        'network_type': 'VXLAN',
        'vxlans': [
            {'vni': 10000, 'nom': 'TENANT_A_WEB', 'description': 'Tenant A Web', 'mtu': 1500, 'cdir': '/24'},
            {'vni': 10001, 'nom': 'TENANT_A_APP', 'description': 'Tenant A App', 'mtu': 1500, 'cdir': '/24'},
            {'vni': 10002, 'nom': 'TENANT_A_DB', 'description': 'Tenant A DB', 'mtu': 1500, 'cdir': '/25'},
            {'vni': 11000, 'nom': 'TENANT_B_WEB', 'description': 'Tenant B Web', 'mtu': 1500, 'cdir': '/24'},
            {'vni': 11001, 'nom': 'TENANT_B_APP', 'description': 'Tenant B App', 'mtu': 1500, 'cdir': '/25'},
            {'vni': 12000, 'nom': 'TENANT_C_ALL', 'description': 'Tenant C All', 'mtu': 9000, 'cdir': '/24'},
        ],
        'decoupages': [
            {'nombre': 1, 'taille': 24},  # TENANT_A_WEB
            {'nombre': 1, 'taille': 24},  # TENANT_A_APP
            {'nombre': 1, 'taille': 25},  # TENANT_A_DB
            {'nombre': 1, 'taille': 24},  # TENANT_B_WEB
            {'nombre': 1, 'taille': 25},  # TENANT_B_APP
            {'nombre': 1, 'taille': 24},  # TENANT_C_ALL
        ]
    }
}
