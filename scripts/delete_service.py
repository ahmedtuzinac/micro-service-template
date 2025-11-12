#!/usr/bin/env python3
"""
Skripta za brisanje mikroservisa
Korišćenje: python scripts/delete_service.py --name user-service
"""

import argparse
import os
import shutil
import yaml
import subprocess
import sys
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


class ServiceDeleter:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.services_dir = self.project_root / "services"
        self.docker_compose_file = self.project_root / "docker-compose.yml"
    
    def service_exists(self, name: str) -> bool:
        """Proverava da li servis postoji"""
        service_path = self.services_dir / name
        return service_path.exists()
    
    def stop_and_remove_container(self, name: str) -> bool:
        """Zaustavi i ukloni Docker kontejner ako postoji"""
        try:
            # Proveri da li kontejner postoji
            result = subprocess.run(
                ["docker-compose", "ps", "-q", name],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"🐳 Stopping and removing container for '{name}'...")
                
                # Zaustavi kontejner
                subprocess.run(
                    ["docker-compose", "stop", name],
                    cwd=self.project_root,
                    capture_output=True,
                    check=False
                )
                
                # Ukloni kontejner
                subprocess.run(
                    ["docker-compose", "rm", "-f", name],
                    cwd=self.project_root,
                    capture_output=True,
                    check=False
                )
                
                print(f"✓ Container for '{name}' stopped and removed")
                return True
            else:
                print(f"ℹ️  No running container found for '{name}'")
                return True
                
        except Exception as e:
            print(f"⚠️  Could not stop container for '{name}': {e}")
            return False
    
    def remove_from_docker_compose(self, name: str) -> bool:
        """Uklanja servis iz docker-compose.yml"""
        if not self.docker_compose_file.exists():
            return True
            
        try:
            with open(self.docker_compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
            
            services = compose_data.get('services', {})
            
            if name in services:
                del services[name]
                print(f"✓ Removed {name} from docker-compose.yml")
                
                # Sačuvaj ažurirani docker-compose.yml
                with open(self.docker_compose_file, 'w') as f:
                    yaml.dump(compose_data, f, default_flow_style=False, indent=2)
                    
                return True
            else:
                print(f"ℹ️  Service {name} not found in docker-compose.yml")
                return True
                
        except Exception as e:
            print(f"✗ Error updating docker-compose.yml: {e}")
            return False
    
    def remove_service_directory(self, name: str) -> bool:
        """Uklanja direktorij servisa"""
        service_path = self.services_dir / name
        
        if not service_path.exists():
            print(f"ℹ️  Service directory {service_path} does not exist")
            return True
            
        try:
            shutil.rmtree(service_path)
            print(f"✓ Removed service directory: {service_path.relative_to(self.project_root)}")
            return True
        except Exception as e:
            print(f"✗ Error removing service directory: {e}")
            return False
    
    def delete_service(self, name: str, confirm: bool = False) -> bool:
        """Glavna metoda za brisanje servisa"""
        
        # Validacija imena
        if not name or len(name) < 2:
            print("✗ Invalid service name")
            return False
        
        # Proveri da li servis postoji
        exists_in_fs = self.service_exists(name)
        
        if not exists_in_fs:
            # Proveri da li je samo u docker-compose.yml
            try:
                with open(self.docker_compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f) or {}
                exists_in_compose = name in compose_data.get('services', {})
            except:
                exists_in_compose = False
            
            if not exists_in_compose:
                print(f"✗ Service '{name}' does not exist")
                return False
        
        # Potvrda brisanja
        if not confirm:
            print(f"🗑️  About to delete service: {name}")
            if exists_in_fs:
                print(f"   - Service directory: services/{name}")
            print(f"   - Docker compose entry")
            print()
            
            response = input("Are you sure you want to delete this service? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ Deletion cancelled")
                return False
        
        print(f"Deleting service: {name}")
        print("-" * 40)
        
        success = True
        
        # Zaustavi i ukloni Docker kontejner ako postoji
        if not self.stop_and_remove_container(name):
            success = False
        
        # Ukloni iz docker-compose.yml
        if not self.remove_from_docker_compose(name):
            success = False
        
        # Ukloni direktorij
        if exists_in_fs:
            if not self.remove_service_directory(name):
                success = False
        
        if success:
            print("-" * 40)
            print(f"✅ Service '{name}' deleted successfully!")
            print()
            print("Remaining services:")
            remaining_services = [d.name for d in self.services_dir.iterdir() if d.is_dir()]
            if remaining_services:
                for service in remaining_services:
                    print(f"  - {service}")
            else:
                print("  (none)")
        else:
            print("❌ Failed to delete service completely")
            
        return success


def main():
    parser = argparse.ArgumentParser(description='Delete a microservice')
    parser.add_argument('--name', '-n', required=True, help='Service name to delete (e.g., user-service)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--list', '-l', action='store_true', help='List all existing services')
    
    args = parser.parse_args()
    
    deleter = ServiceDeleter()
    
    # List mode
    if args.list:
        services_dir = deleter.services_dir
        if not services_dir.exists():
            print("📂 No services directory found")
            return
            
        services = [d.name for d in services_dir.iterdir() if d.is_dir()]
        
        if services:
            print("📋 Existing services:")
            for service in sorted(services):
                print(f"  - {service}")
        else:
            print("📂 No services found")
        return
    
    # Delete service
    if deleter.delete_service(args.name, confirm=args.yes):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()