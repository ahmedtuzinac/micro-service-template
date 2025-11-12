#!/usr/bin/env python3
"""
Skripta za enable/disable mikroservisa u docker-compose.yml
Korišćenje: 
  python scripts/manage_service.py --enable user-service
  python scripts/manage_service.py --disable user-service
  python scripts/manage_service.py --list
"""

import argparse
import yaml
from pathlib import Path
import subprocess
import sys

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class ServiceManager:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.services_dir = self.project_root / "services"
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.disabled_services_file = self.project_root / ".disabled_services.yml"
    
    def service_exists(self, name: str) -> bool:
        """Proverava da li servis postoji u fajl sistemu"""
        service_path = self.services_dir / name
        return service_path.exists()
    
    def is_service_enabled(self, name: str) -> bool:
        """Proverava da li je servis enabled u docker-compose.yml"""
        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
            
            services = compose_data.get('services', {})
            return name in services
        except:
            return False
    
    def get_disabled_services(self) -> dict:
        """Čita listu disabled servisa"""
        if not self.disabled_services_file.exists():
            return {}
        
        try:
            with open(self.disabled_services_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except:
            return {}
    
    def save_disabled_services(self, disabled_services: dict):
        """Čuva listu disabled servisa"""
        try:
            with open(self.disabled_services_file, 'w') as f:
                yaml.dump(disabled_services, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save disabled services: {e}")
    
    def run_docker_command(self, command: list, description: str) -> bool:
        """Izvršava Docker komandu"""
        try:
            print(f"🐳 {description}...")
            result = subprocess.run(
                command, 
                cwd=self.project_root,
                capture_output=True, 
                text=True, 
                check=True
            )
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Docker command failed: {e}")
            if e.stderr:
                print(f"   Error: {e.stderr.strip()}")
            return False
        except Exception as e:
            print(f"✗ Error running Docker command: {e}")
            return False
    
    def enable_service(self, name: str) -> bool:
        """Omogućava servis - dodaje ga u docker-compose.yml"""
        
        # Proveri da li servis postoji u fajl sistemu
        if not self.service_exists(name):
            print(f"✗ Service '{name}' does not exist in services/ directory")
            return False
        
        # Proveri da li je već enabled
        if self.is_service_enabled(name):
            print(f"ℹ️  Service '{name}' is already enabled")
            return True
        
        # Učitaj disabled servise
        disabled_services = self.get_disabled_services()
        
        if name not in disabled_services:
            print(f"✗ Service '{name}' configuration not found in disabled services")
            print("This service was probably never added to docker-compose.yml")
            print("Use create_service.py to add it first")
            return False
        
        # Učitaj docker-compose.yml
        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
        except:
            compose_data = {'services': {}}
        
        # Dodaj servis u docker-compose.yml
        compose_data.setdefault('services', {})[name] = disabled_services[name]
        
        # Sačuvaj docker-compose.yml
        try:
            with open(self.docker_compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)
            
            # Ukloni iz disabled servisa
            del disabled_services[name]
            self.save_disabled_services(disabled_services)
            
            print(f"✅ Service '{name}' enabled in docker-compose.yml")
            
            # Pokreni servis u Docker-u
            docker_success = self.run_docker_command(
                ["docker-compose", "up", "-d", name],
                f"Starting service '{name}'"
            )
            
            if docker_success:
                print(f"🔄 Service '{name}' is now running")
            else:
                print(f"⚠️  Service enabled in config but failed to start Docker container")
                
            return True
            
        except Exception as e:
            print(f"✗ Failed to enable service: {e}")
            return False
    
    def disable_service(self, name: str) -> bool:
        """Onemogućava servis - uklanja ga iz docker-compose.yml ali čuva konfiguraciju"""
        
        # Proveri da li je servis enabled
        if not self.is_service_enabled(name):
            print(f"ℹ️  Service '{name}' is already disabled")
            return True
        
        # Učitaj docker-compose.yml
        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
        except:
            print("✗ Could not read docker-compose.yml")
            return False
        
        services = compose_data.get('services', {})
        
        if name not in services:
            print(f"✗ Service '{name}' not found in docker-compose.yml")
            return False
        
        # Prvo zaustavi i ukloni Docker kontejner
        print(f"🔻 Disabling service '{name}'...")
        docker_success = self.run_docker_command(
            ["docker-compose", "stop", name],
            f"Stopping service '{name}'"
        )
        
        if docker_success:
            self.run_docker_command(
                ["docker-compose", "rm", "-f", name],
                f"Removing container for '{name}'"
            )
        
        # Sačuvaj konfiguraciju servisa
        disabled_services = self.get_disabled_services()
        disabled_services[name] = services[name]
        self.save_disabled_services(disabled_services)
        
        # Ukloni iz docker-compose.yml
        del services[name]
        
        # Sačuvaj ažurirani docker-compose.yml
        try:
            with open(self.docker_compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)
            
            print(f"✅ Service '{name}' disabled successfully")
            print(f"   • Docker container stopped and removed")
            print(f"   • Configuration saved, can be re-enabled with: make enable-service NAME={name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to disable service: {e}")
            return False
    
    def list_services(self):
        """Prikazuje status svih servisa"""
        print("📋 Service Status Overview")
        print("=" * 50)
        
        # Servisi u fajl sistemu
        all_services = set()
        if self.services_dir.exists():
            all_services.update(d.name for d in self.services_dir.iterdir() if d.is_dir())
        
        # Disabled servisi
        disabled_services = self.get_disabled_services()
        all_services.update(disabled_services.keys())
        
        # Enabled servisi iz docker-compose.yml
        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
            enabled_services = set(compose_data.get('services', {}).keys())
            all_services.update(enabled_services)
        except:
            enabled_services = set()
        
        if not all_services:
            print("📂 No services found")
            return
        
        print(f"🟢 Enabled Services:")
        enabled_count = 0
        for service in sorted(enabled_services):
            print(f"   ✓ {service}")
            enabled_count += 1
        
        if enabled_count == 0:
            print("   (none)")
        
        print()
        print(f"🔸 Disabled Services:")
        disabled_count = 0
        for service in sorted(disabled_services.keys()):
            print(f"   ⏸️  {service}")
            disabled_count += 1
            
        if disabled_count == 0:
            print("   (none)")
        
        print()
        print(f"📊 Total: {len(all_services)} services ({enabled_count} enabled, {disabled_count} disabled)")


def main():
    parser = argparse.ArgumentParser(description='Manage microservices (enable/disable)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--enable', '-e', metavar='SERVICE', help='Enable a service')
    group.add_argument('--disable', '-d', metavar='SERVICE', help='Disable a service')
    group.add_argument('--list', '-l', action='store_true', help='List all services and their status')
    
    args = parser.parse_args()
    
    manager = ServiceManager()
    
    if args.list:
        manager.list_services()
    elif args.enable:
        if manager.enable_service(args.enable):
            exit(0)
        else:
            exit(1)
    elif args.disable:
        if manager.disable_service(args.disable):
            exit(0)
        else:
            exit(1)


if __name__ == "__main__":
    main()