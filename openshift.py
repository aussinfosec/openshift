import subprocess
import json
import sys  # For flush

def get_openshift_namespaces():
    """
    Retrieve the list of OpenShift namespaces (projects) using 'oc projects -q'.
    """
    try:
        output = subprocess.check_output(['oc', 'projects', '-q']).decode('utf-8').strip()
        namespaces = output.splitlines()
        return namespaces
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving namespaces: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Error: 'oc' command not found. Ensure OpenShift CLI is installed and in PATH.", file=sys.stderr)
        return []

def get_routes_for_namespace(namespace):
    """
    Retrieve route information for a given namespace using 'oc get routes -o json'.
    Returns a list of route details.
    """
    try:
        output = subprocess.check_output(['oc', 'get', 'routes', '-n', namespace, '-o', 'json']).decode('utf-8')
        routes_data = json.loads(output)
        routes = []
        for item in routes_data.get('items', []):
            spec = item.get('spec', {})
            status = item.get('status', {})
            route_info = {
                'name': item['metadata']['name'],
                'host': spec.get('host', 'N/A'),
                'path': spec.get('path', 'N/A'),
                'to_service': spec.get('to', {}).get('name', 'N/A'),
                'tls_enabled': bool(spec.get('tls')),
                'ingress_status': [ing.get('host', 'N/A') for ing in status.get('ingress', [])]
            }
            routes.append(route_info)
        return routes
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving routes for namespace '{namespace}': {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"Error parsing JSON for namespace '{namespace}'.", file=sys.stderr)
        return []

def main():
    namespaces = get_openshift_namespaces()
    if not namespaces:
        print("No namespaces found or error occurred.", file=sys.stderr)
        return

    for ns in namespaces:
        print(f"Processing namespace: {ns}...", flush=True)
        routes = get_routes_for_namespace(ns)
        print(f"Finished processing namespace: {ns}", flush=True)
        
        # Print results immediately for this namespace
        if routes:
            print(f"\nNamespace: {ns}")
            for route in routes:
                print(f"  Route: {route['name']}")
                print(f"    Host: {route['host']}")
                print(f"    Path: {route['path']}")
                print(f"    To Service: {route['to_service']}")
                print(f"    TLS Enabled: {route['tls_enabled']}")
                print(f"    Ingress Hosts: {', '.join(route['ingress_status'])}")
                print("---")
        else:
            print(f"No routes found in namespace: {ns}")

if __name__ == "__main__":
    main()