import docker
from config import config

client = docker.from_env()

def is_port_free(port):
    for container in client.containers.list():
        container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        for port_binding in container_ports.get(f"{config.PORT_IN_CONTAINER}/tcp", []):
            if port_binding['HostPort'] == str(port):
                return False
    return True

def get_free_port(used_ports):
    available_ports = list(set(config.PORT_RANGE) - used_ports)
    for port in available_ports:
        if is_port_free(port):
            used_ports.add(port)
            return port
    return None

def run_container(image_name, port):
    return client.containers.run(image_name, detach=True, ports={f"{config.PORT_IN_CONTAINER}/tcp": port})
