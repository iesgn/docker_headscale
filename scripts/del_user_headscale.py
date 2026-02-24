import os
import requests
import sys
from libldap import LibLDAP 

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

def eliminar_en_headscale(uid):
    """Llama a la API para eliminar un usuario por su nombre (ID)."""
    # En la API de Headscale, el borrado suele ser DELETE /api/v1/user/{name}
    url = f"{HEADSCALE_URL}/api/v1/user/{uid}"

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