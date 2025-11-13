#!/usr/bin/env python3
"""
Skripta za automatsko kreiranje novih mikroservisa
Korišćenje: python scripts/create_service.py --name user-service --port 8001 --database user_db
"""

import argparse
import os
import shutil
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded configuration from {env_path}")
    else:
        print(f"ℹ️  No .env file found at {env_path}, using defaults")
except ImportError:
    print("ℹ️  python-dotenv not installed, using environment variables only")

# PostgreSQL konfiguracija iz .env fajla ili environment varijabli
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "host.docker.internal")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_PREFIX = os.getenv("DB_PREFIX", "basify")


class ServiceGenerator:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.templates_dir = self.project_root / "templates"
        self.services_dir = self.project_root / "services"
        self.docker_compose_file = self.project_root / "docker-compose.yml"

        # Ensure directories exist
        self.services_dir.mkdir(exist_ok=True)

    def validate_service_name(self, name: str) -> bool:
        """Validira ime servisa"""
        pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'
        return bool(re.match(pattern, name)) and len(name) >= 3

    def get_next_available_port(self, start_port: int = 8001) -> int:
        """Pronalazi sledeći dostupan port"""
        used_ports = set()

        # Čitaj postojeće portove iz docker-compose.yml
        if self.docker_compose_file.exists():
            try:
                with open(self.docker_compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f) or {}

                services = compose_data.get('services', {})
                for service_name, service_config in services.items():
                    ports = service_config.get('ports', [])
                    for port_mapping in ports:
                        if isinstance(port_mapping, str) and ':' in port_mapping:
                            host_port = port_mapping.split(':')[0]
                            try:
                                used_ports.add(int(host_port))
                            except ValueError:
                                continue
            except Exception as e:
                print(f"Warning: Could not read existing ports: {e}")

        # Pronađi sledeći dostupan port
        port = start_port
        while port in used_ports:
            port += 1

        return port

    def service_exists(self, name: str) -> bool:
        """Proverava da li servis već postoji"""
        service_path = self.services_dir / name
        return service_path.exists()

    def generate_replacements(self, name: str, port: int, database: str, **kwargs) -> Dict[str, str]:
        """Generiše mape za zamenu u template-ima"""
        # Kreiraj varijante imena
        service_name_clean = name.replace('-', '_')
        
        # Bolje model naming: user-service -> User (ne UserService)
        # Ukloni '-service' suffix ako postoji, pa capitalize
        entity_name = name.replace('-service', '').replace('-', '_')
        model_name = ''.join(word.capitalize() for word in entity_name.split('_'))
        
        # Ako je model_name još uvek generično, koristi prvi deo
        if model_name.lower() in ['service', 'api', 'app']:
            model_name = name.split('-')[0].capitalize()
            
        route_name = service_name_clean
        table_name = f"{entity_name.lower()}s"
        route_prefix = name.replace('-', '_')
        
        # Smart API endpoint generation
        api_prefix = self._generate_api_prefix(entity_name)
        api_resource = self._generate_api_resource_name(entity_name)

        replacements = {
            '{{SERVICE_NAME}}': name,
            '{{SERVICE_DESCRIPTION}}': f"{name.replace('-', ' ').title()}",
            '{{PORT}}': str(port),
            '{{DATABASE_NAME}}': database,
            '{{DATABASE_URL}}': f"postgres://postgres:password@postgres:5432/{database}",
            '{{MODEL_NAME}}': model_name,
            '{{TABLE_NAME}}': table_name,
            '{{ROUTE_NAME}}': route_name,
            '{{ROUTE_PREFIX}}': route_prefix,
            '{{API_PREFIX}}': api_prefix,
            '{{API_RESOURCE}}': api_resource,
            '{{API_RESOURCE_LOWER}}': api_resource.lower(),
            '{{TIMESTAMP}}': "2024-01-01T00:00:00Z",  # Template timestamp
        }

        # Dodaj dodatne parametre
        replacements.update(kwargs)

        return replacements

    def _generate_api_prefix(self, entity_name: str) -> str:
        """Generiše smart API prefix na osnovu entity imena"""
        # Poznati entity tipovi i njihovi API prefiksi
        api_mappings = {
            'user': '/users',
            'order': '/orders', 
            'product': '/products',
            'customer': '/customers',
            'invoice': '/invoices',
            'payment': '/payments',
            'category': '/categories',
            'tag': '/tags',
            'post': '/posts',
            'comment': '/comments',
            'file': '/files',
            'upload': '/uploads',
            'report': '/reports',
            'log': '/logs',
            'event': '/events',
            'notification': '/notifications',
            'message': '/messages',
            'task': '/tasks',
            'job': '/jobs',
            'inventory': '/inventory',
            'warehouse': '/warehouses'
        }
        
        entity_lower = entity_name.lower()
        
        # Proveři direktno mapiranje
        if entity_lower in api_mappings:
            return api_mappings[entity_lower]
        
        # Fallback: plural form
        if entity_lower.endswith('y'):
            return f"/{entity_lower[:-1]}ies"
        elif entity_lower.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return f"/{entity_lower}es"
        else:
            return f"/{entity_lower}s"

    def _generate_api_resource_name(self, entity_name: str) -> str:
        """Generiše resource name za API dokumentaciju"""
        return entity_name.lower()

    def process_template_file(self, template_path: Path, target_path: Path, replacements: Dict[str, str]):
        """Obrađuje template fajl i kreira novi sa zamenama"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Primeni zamene
            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)

            # Kreiraj direktorij ako ne postoji
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Created: {target_path.relative_to(self.project_root)}")

        except Exception as e:
            print(f"✗ Error creating {target_path}: {e}")
            raise

    def create_service_structure(self, name: str, replacements: Dict[str, str]):
        """Kreira strukturu servisa na osnovu template-a"""
        service_dir = self.services_dir / name
        service_template_dir = self.templates_dir / "service_template"

        # Kreiraj osnovne fajlove
        template_files = [
            ("main.py", "main.py"),
            ("models.py", "models.py"),
            ("requirements.txt", "requirements.txt"),
            ("routes/__init__.py", "routes/__init__.py"),
        ]

        for template_file, target_file in template_files:
            template_path = service_template_dir / template_file
            target_path = service_dir / target_file

            if template_path.exists():
                self.process_template_file(template_path, target_path, replacements)

        # Kreiraj route fajl sa dinamičkim imenom
        route_template = service_template_dir / "routes" / "{{ROUTE_NAME}}.py"
        route_target = service_dir / "routes" / f"{replacements['{{ROUTE_NAME}}']}.py"

        if route_template.exists():
            self.process_template_file(route_template, route_target, replacements)

        # Kreiraj Dockerfile
        dockerfile_template = self.templates_dir / "Dockerfile.template"
        dockerfile_target = service_dir / "Dockerfile"

        if dockerfile_template.exists():
            self.process_template_file(dockerfile_template, dockerfile_target, replacements)

    def clean_docker_compose(self):
        """Uklanja servise iz docker-compose.yml koji ne postoje u services/ folderu"""
        if not self.docker_compose_file.exists():
            return

        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}

            services = compose_data.get('services', {})
            services_to_remove = []

            for service_name in services.keys():

                service_path = self.services_dir / service_name
                if not service_path.exists():
                    services_to_remove.append(service_name)

            if services_to_remove:
                for service_name in services_to_remove:
                    del services[service_name]
                    print(f"✓ Removed {service_name} from docker-compose.yml")

                # Sačuvaj ažurirani docker-compose.yml
                with open(self.docker_compose_file, 'w') as f:
                    yaml.dump(compose_data, f, default_flow_style=False, indent=2)

        except Exception as e:
            print(f"Warning: Could not clean docker-compose.yml: {e}")

    def update_docker_compose(self, name: str, port: int, database: str):
        """Ažurira docker-compose.yml sa novim servisom"""
        compose_data = {}

        # Učitaj postojeći docker-compose.yml
        if self.docker_compose_file.exists():
            try:
                with open(self.docker_compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not read docker-compose.yml: {e}")

        # Kreiraj osnovnu strukturu ako ne postoji

        if 'services' not in compose_data:
            compose_data['services'] = {}

        # Dodaj novi servis
        service_env = {
            'DATABASE_URL': f'postgres://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@${{POSTGRES_HOST}}:${{POSTGRES_PORT}}/${{DB_PREFIX}}_{database}',
            'SERVICE_NAME': name,
            'PORT': str(port)
        }
        
        # Dodaj AUTH_SERVICE_URL za sve servise osim auth-service
        if name != 'auth-service':
            service_env['AUTH_SERVICE_URL'] = 'http://auth-service:8000'
        
        compose_data['services'][name] = {
            'build': {
                'context': '.',
                'dockerfile': f'./services/{name}/Dockerfile'
            },
            'ports': [f'{port}:{port}'],
            'environment': service_env,
            'restart': 'unless-stopped',
            'extra_hosts': ['${POSTGRES_HOST}:host-gateway']
        }

        # Sačuvaj ažurirani docker-compose.yml
        try:
            with open(self.docker_compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)

            print(f"✓ Updated: {self.docker_compose_file.relative_to(self.project_root)}")

        except Exception as e:
            print(f"✗ Error updating docker-compose.yml: {e}")
            raise

    def create_service(self, name: str, port: Optional[int] = None, database: Optional[str] = None, **kwargs) -> bool:
        """Glavna metoda za kreiranje servisa"""

        # Validacija
        if not self.validate_service_name(name):
            print(f"✗ Invalid service name: {name}")
            print("Service name must be lowercase, start with letter, contain only letters/numbers/hyphens")
            return False

        if self.service_exists(name):
            print(f"✗ Service {name} already exists")
            return False

        # Postavi default vrednosti
        if port is None:
            port = self.get_next_available_port()

        if database is None:
            # Generisi database name bez prefiksa (prefix će se dodati iz ${DB_PREFIX} varijable)
            service_clean = name.replace('-service', '').replace('-', '_')
            database = f'{service_clean}_db'

        print(f"Creating service: {name}")
        print(f"Port: {port}")
        print(f"Database: {database}")
        print("-" * 50)

        try:
            # Očisti docker-compose od nepostojećih servisa
            self.clean_docker_compose()

            # Generiši zamene
            replacements = self.generate_replacements(name, port, database, **kwargs)

            # Kreiraj strukturu servisa
            self.create_service_structure(name, replacements)

            # Ažuriraj docker-compose
            self.update_docker_compose(name, port, database)

            print("-" * 50)
            print(f"✓ Service {name} created successfully!")
            print(f"  Directory: services/{name}")
            print(f"  Port: {port}")
            print(f"  Database: {database}")
            print("")
            print("Next steps:")
            print(f"1. cd services/{name}")
            print("2. docker-compose build")
            print("3. docker-compose up")

            return True

        except Exception as e:
            print(f"✗ Failed to create service: {e}")

            # Pokušaj rollback
            service_path = self.services_dir / name
            if service_path.exists():
                try:
                    shutil.rmtree(service_path)
                    print(f"✓ Cleaned up partial service directory")
                except Exception as cleanup_error:
                    print(f"✗ Could not clean up {service_path}: {cleanup_error}")

            return False


def main():
    parser = argparse.ArgumentParser(description='Create a new microservice')
    parser.add_argument('--name', '-n', help='Service name (e.g., user-service)')
    parser.add_argument('--port', '-p', type=int, help='Service port (auto-detected if not provided)')
    parser.add_argument('--database', '-d', help='Database name (auto-generated if not provided)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--clean', '-c', action='store_true',
                        help='Clean docker-compose.yml from non-existing services')

    args = parser.parse_args()

    generator = ServiceGenerator()

    # Clean mode
    if args.clean:
        print("🧹 Cleaning docker-compose.yml...")
        generator.clean_docker_compose()
        print("✓ Done!")
        exit(0)

    if args.interactive:
        print("=== Basify Service Generator ===")
        name = input("Service name: ").strip()

        port_input = input(f"Port (default: auto-detect): ").strip()
        port = int(port_input) if port_input else None

        database_input = input(f"Database name (default: auto-generate): ").strip()
        database = database_input if database_input else None

    else:
        name = args.name
        port = args.port
        database = args.database

    # Validation
    if not name:
        print("✗ Service name is required")
        parser.print_help()
        exit(1)

    if generator.create_service(name, port, database):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
