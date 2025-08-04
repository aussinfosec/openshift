import subprocess
import json
import sys  # For flush and stderr
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    Returns a tuple of (namespace, list of route details).
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
        return namespace, routes
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving routes for namespace '{namespace}': {e}", file=sys.stderr)
        return namespace, []
    except json.JSONDecodeError:
        print(f"Error parsing JSON for namespace '{namespace}'.", file=sys.stderr)
        return namespace, []

def main():
    namespaces = get_openshift_namespaces()
    if not namespaces:
        print("No namespaces found or error occurred.", file=sys.stderr)
        return

    all_routes = {}
    max_workers = 10  # Adjust based on your system's capabilities; e.g., 10-20 for 50 namespaces

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ns = {executor.submit(get_routes_for_namespace, ns): ns for ns in namespaces}
        for future in as_completed(future_to_ns):
            ns = future_to_ns[future]
            try:
                _, routes = future.result()
                print(f"Finished processing namespace: {ns}", flush=True)
                if routes:
                    all_routes[ns] = routes
            except Exception as exc:
                print(f"Namespace {ns} generated an exception: {exc}", file=sys.stderr)

    # Ensure all namespaces are included, even if no routes
    for ns in namespaces:
        if ns not in all_routes:
            all_routes[ns] = []

    # Sort namespaces for consistent output (optional)
    sorted_namespaces = sorted(all_routes.keys())

    # Print the results
    for ns in sorted_namespaces:
        routes = all_routes[ns]
        print(f"\nNamespace: {ns}")
        if routes:
            for route in routes:
                print(f"  Route: {route['name']}")
                print(f"    Host: {route['host']}")
                print(f"    Path: {route['path']}")
                print(f"    To Service: {route['to_service']}")
                print(f"    TLS Enabled: {route['tls_enabled']}")
                print(f"    Ingress Hosts: {', '.join(route['ingress_status'])}")
                print("---")
        else:
            print("  No routes found.")

if __name__ == "__main__":
    main()