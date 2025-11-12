import os
import yaml
import logging
from typing import Dict, Optional, List
from urllib.parse import urlparse
from pathlib import Path


class ServiceDiscovery:
    """
    Service Discovery sistem za lociranje mikroservisa
    Podržava i lokalno i Docker okruženje
    """
    
    def __init__(self, compose_file_path: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.environment = os.getenv("ENVIRONMENT", "docker").lower()
        
        # Path to docker-compose.yml file
        self.compose_file_path = compose_file_path or self._find_compose_file()
        
        # Cache za service URLs
        self._service_cache: Dict[str, str] = {}
        
        # Load services from docker-compose.yml
        self._available_services = self._load_services_from_compose()
        
        self.logger.info(f"ServiceDiscovery initialized in '{self.environment}' environment")
        self.logger.info(f"Loaded {len(self._available_services)} services from {self.compose_file_path}")
    
    def _find_compose_file(self) -> str:
        """Pronalazi docker-compose.yml file u project root-u"""
        # Za Docker container - koristi environment variable ili fallback
        compose_env = os.getenv("COMPOSE_FILE")
        if compose_env and os.path.exists(compose_env):
            return compose_env
        
        # Standardne lokacije
        possible_locations = [
            "docker-compose.yml",           # Trenutni direktorijum
            "../docker-compose.yml",       # Parent direktorijum
            "/app/../docker-compose.yml",   # Za Docker containers
            "/app/docker-compose.yml",     # Copy u container
        ]
        
        for location in possible_locations:
            if os.path.exists(location):
                return location
        
        # Pokušaj da nađeš u parent direktorijumima
        current_dir = Path.cwd()
        for path in [current_dir] + list(current_dir.parents):
            compose_file = path / "docker-compose.yml"
            if compose_file.exists():
                return str(compose_file)
        
        # Fallback - vrati putanju u trenutnom direktorijumu
        self.logger.warning("Could not find docker-compose.yml, using fallback")
        return "docker-compose.yml"
    
    def _load_services_from_compose(self) -> Dict[str, int]:
        """Učitava servise iz docker-compose.yml fajla"""
        services = {}
        
        try:
            if not os.path.exists(self.compose_file_path):
                self.logger.warning(f"Docker compose file not found: {self.compose_file_path}")
                return services
            
            with open(self.compose_file_path, 'r') as file:
                compose_data = yaml.safe_load(file)
            
            if not compose_data or 'services' not in compose_data:
                self.logger.warning("No services section found in docker-compose.yml")
                return services
            
            for service_name, service_config in compose_data['services'].items():
                # Izvuci port iz ports mapping-a
                port = self._extract_port_from_service(service_config)
                if port:
                    services[service_name] = port
                    self.logger.debug(f"Found service: {service_name}:{port}")
                else:
                    self.logger.warning(f"Could not determine port for service: {service_name}")
            
        except Exception as e:
            self.logger.error(f"Error loading services from compose file: {e}")
        
        return services
    
    def _extract_port_from_service(self, service_config: Dict) -> Optional[int]:
        """Izvlači port iz service konfiguracije"""
        if not isinstance(service_config, dict):
            return None
        
        # Pokušaj da izvučeš iz ports mapping-a
        ports = service_config.get('ports', [])
        if ports and isinstance(ports, list):
            # Uzmi prvi port mapping (format: "8001:8001" ili port: 8001)
            first_port = ports[0]
            if isinstance(first_port, str) and ':' in first_port:
                # Format "external:internal"
                external_port = first_port.split(':')[0]
                try:
                    return int(external_port)
                except ValueError:
                    pass
            elif isinstance(first_port, int):
                return first_port
        
        # Pokušaj da izvučeš iz environment varijabli
        environment = service_config.get('environment', {})
        if isinstance(environment, dict):
            port_value = environment.get('PORT')
            if port_value:
                try:
                    # Ukloni quotes ako postoje
                    return int(str(port_value).strip("'\""))
                except ValueError:
                    pass
        elif isinstance(environment, list):
            for env_var in environment:
                if isinstance(env_var, str) and env_var.startswith('PORT='):
                    try:
                        return int(env_var.split('=')[1].strip("'\""))
                    except ValueError:
                        pass
        
        return None

    def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Vraća punu URL adresu za dati servis
        
        Args:
            service_name: Naziv servisa (npr. 'user-service')
            
        Returns:
            Puna URL adresa servisa ili None ako servis nije pronađen
        """
        
        # Proveri cache først
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        # Dobij base URL na osnovu environment-a
        base_url = self._get_base_url(service_name)
        
        if base_url:
            self._service_cache[service_name] = base_url
            self.logger.debug(f"Resolved {service_name} -> {base_url}")
        else:
            self.logger.warning(f"Could not resolve service: {service_name}")
        
        return base_url
    
    def _get_base_url(self, service_name: str) -> Optional[str]:
        """Generiše base URL na osnovu environment-a"""
        
        # 1. Pokušaj explicit environment variable
        env_var = f"{service_name.upper().replace('-', '_')}_URL"
        explicit_url = os.getenv(env_var)
        if explicit_url:
            return explicit_url
        
        # 2. Dobij port za servis
        port = self._get_service_port(service_name)
        if not port:
            return None
        
        # 3. Generiši URL na osnovu environment-a
        if self.environment == "local":
            return f"http://localhost:{port}"
        else:
            # Docker environment - koristi service name kao hostname
            return f"http://{service_name}:{port}"
    
    def _get_service_port(self, service_name: str) -> Optional[int]:
        """Dobija port za dati servis"""
        
        # 1. Pokušaj explicit port environment variable
        port_var = f"{service_name.upper().replace('-', '_')}_PORT"
        explicit_port = os.getenv(port_var)
        if explicit_port:
            try:
                return int(explicit_port)
            except ValueError:
                self.logger.warning(f"Invalid port in {port_var}: {explicit_port}")
        
        # 2. Koristi port iz docker-compose.yml
        if service_name in self._available_services:
            return self._available_services[service_name]
        
        # 3. Pokušaj da parsuje iz SERVICE_NAME_URL ako postoji
        url_var = f"{service_name.upper().replace('-', '_')}_URL"
        service_url = os.getenv(url_var)
        if service_url:
            try:
                parsed = urlparse(service_url)
                return parsed.port
            except Exception:
                pass
        
        return None
    
    def register_service(self, service_name: str, url: str) -> None:
        """
        Registruje servis sa eksplicitnim URL-om
        
        Args:
            service_name: Naziv servisa
            url: Puna URL adresa servisa
        """
        self._service_cache[service_name] = url
        self.logger.info(f"Registered service: {service_name} -> {url}")
    
    def unregister_service(self, service_name: str) -> None:
        """
        Uklanja servis iz registry-ja
        
        Args:
            service_name: Naziv servisa za uklanjanje
        """
        if service_name in self._service_cache:
            del self._service_cache[service_name]
            self.logger.info(f"Unregistered service: {service_name}")
    
    def list_services(self) -> Dict[str, str]:
        """
        Vraća sve registrovane servise
        
        Returns:
            Dictionary sa service_name -> url mapiranjima
        """
        # Kombina cached servise sa onima iz docker-compose.yml
        all_services = {}
        
        # Dodaj cached servise
        all_services.update(self._service_cache)
        
        # Dodaj servise iz docker-compose.yml ako nisu već cached
        for service_name in self._available_services:
            if service_name not in all_services:
                url = self._get_base_url(service_name)
                if url:
                    all_services[service_name] = url
        
        return all_services
    
    def health_check_service(self, service_name: str) -> bool:
        """
        Jednostavna provera dostupnosti servisa
        
        Args:
            service_name: Naziv servisa za proveru
            
        Returns:
            True ako je servis dostupan, False inače
        """
        try:
            import socket
            from urllib.parse import urlparse
            
            url = self.get_service_url(service_name)
            if not url:
                return False
            
            parsed = urlparse(url)
            hostname = parsed.hostname or 'localhost'
            port = parsed.port or 80
            
            # Probaj da se konektuješ na host:port
            with socket.create_connection((hostname, port), timeout=2):
                return True
                
        except Exception as e:
            self.logger.debug(f"Health check failed for {service_name}: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Briše cached service URLs"""
        self._service_cache.clear()
        self.logger.info("Service cache cleared")