import os
import requests
import sys
from libldap import LibLDAP, normalizar_uid

# --- Configuración ---
HEADSCALE_URL = os.getenv('HEADSCALE_URL')
API_KEY = os.getenv('HEADSCALE_API_KEY')

if not HEADSCALE_URL or not API_KEY:
    print("❌ Error: HEADSCALE_URL o HEADSCALE_API_KEY no configuradas.")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

def confirmar(mensaje):
    """Pregunta al usuario para confirmar la acción."""
    respuesta = input(f"{mensaje} (s/n): ").lower()
    return respuesta == 's'

def obtener_id_headscale(uid):
    """Resuelve el ID numérico de un usuario a partir de su nombre."""
    nombre_hs = normalizar_uid(uid)
    url = f"{HEADSCALE_URL}/api/v1/user"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            usuarios = response.json().get('users', [])
            for u in usuarios:
                if u['name'] == nombre_hs:
                    return u['id']
    except Exception as e:
        print(f"⚠️ Error obteniendo ID de {uid}: {e}")
    return None

def eliminar_nodos_de_usuario(user_id, uid):
    """Borra todos los nodos asociados a un usuario.

    Headscale no permite eliminar un usuario que aún tiene nodos
    ('user not empty: node(s) found'), así que hay que borrarlos antes.
    """
    url = f"{HEADSCALE_URL}/api/v1/node"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"⚠️  No se pudieron listar los nodos de {uid}: "
                  f"{response.status_code} - {response.text}")
            return

        nodos = response.json().get('nodes', [])
        # El nodo trae un objeto 'user' con su id; filtramos por ese id.
        propios = [n for n in nodos
                   if str(n.get('user', {}).get('id')) == str(user_id)]

        for nodo in propios:
            node_id = nodo['id']
            node_name = nodo.get('name', node_id)
            del_resp = requests.delete(f"{url}/{node_id}", headers=headers)
            if del_resp.status_code == 200:
                print(f"   🧹 [NODO] '{node_name}' (id {node_id}) eliminado.")
            else:
                print(f"   ❌ [NODO] No se pudo borrar '{node_name}': "
                      f"{del_resp.status_code} - {del_resp.text}")
    except Exception as e:
        print(f"⚠️ Error eliminando nodos de {uid}: {e}")

def eliminar_en_headscale(uid):
    """Llama a la API para eliminar un usuario por su ID numérico."""
    # La API de Headscale borra por ID numérico: DELETE /api/v1/user/{id}
    user_id = obtener_id_headscale(uid)
    if user_id is None:
        print(f"ℹ️  [NOT FOUND] El usuario '{uid}' no existe en Headscale.")
        return

    # Primero borramos sus nodos, si no Headscale rechaza el borrado.
    eliminar_nodos_de_usuario(user_id, uid)

    url = f"{HEADSCALE_URL}/api/v1/user/{user_id}"

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            print(f"🗑️  [BORRADO] Usuario '{uid}' eliminado con éxito.")
        elif response.status_code == 404:
            print(f"ℹ️  [NOT FOUND] El usuario '{uid}' no existe en Headscale.")
        else:
            print(f"❌ [ERROR] {uid}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🔥 Error de conexión al borrar {uid}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 delete_user_headscale.py <username_o_aula>")
        return

    objetivo = sys.argv[1]

    print("⚠️  AVISO: al borrar un usuario se eliminarán también TODOS sus "
          "nodos registrados en Headscale.")

    ldap = LibLDAP()

    # Caso 1: Es un Aula (Grupo)
    if objetivo in ldap.grupos:
        nombre_aula = ldap.grupos[objetivo]
        res = ldap.buscar(f"(cn={objetivo})", attr=['member'], base_dn=ldap.group_dn)
        
        if res and 'member' in res[0]:
            miembros = [m.split(',')[0].split('=')[1] for m in res[0]['member']]
            
            print(f"⚠️  Se van a eliminar {len(miembros)} usuarios del aula '{nombre_aula}'.")
            if confirmar(f"¿Estás SEGURO de que quieres borrar a TODO el aula {objetivo}?"):
                for m_uid in miembros:
                    eliminar_en_headscale(m_uid)
            else:
                print("Operación cancelada.")
        else:
            print(f"La clase {objetivo} no tiene miembros.")

    # Caso 2: Es un Usuario Individual
    else:
        # Verificamos primero si existe en LDAP para dar un feedback más claro
        u_info = ldap.buscar(f"(uid={objetivo})", attr=['cn'])
        nombre_display = u_info[0]['cn'][0] if u_info else objetivo
        
        if confirmar(f"¿Realmente quieres borrar al usuario '{nombre_display}' ({objetivo})?"):
            eliminar_en_headscale(objetivo)
        else:
            print("Operación cancelada.")

    ldap.logout()

if __name__ == "__main__":
    main()