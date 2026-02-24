import os
import requests
import sys
from libldap import LibLDAP # Sustituye por el nombre de tu archivo .py

# --- Configuración desde el entorno ---
HEADSCALE_URL = os.getenv('HEADSCALE_URL')
API_KEY = os.getenv('HEADSCALE_API_KEY')

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

def usuario_existe(uid):
    """Verifica si el nombre de usuario (ID) ya existe."""
    url = f"{HEADSCALE_URL}/api/v1/user"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            usuarios = response.json().get('users', [])
            return any(u['name'] == uid for u in usuarios)
    except Exception as e:
        print(f"⚠️ Error verificando existencia: {e}")
    return False

def dar_alta_headscale(uid, nombre_completo, email, curso):
    """
    Crea el usuario con el esquema completo de la API.
    """
    if usuario_existe(uid):
        print(f"ℹ️ [OMITIDO] {uid} ya existe.")
        return

    url = f"{HEADSCALE_URL}/api/v1/user"
    
    # Formateamos el displayName según tu requisito
    display_name_formateado = f"{nombre_completo} ({curso})"
    
    # Payload con la estructura que me has pasado
    payload = {
        "name": uid,                      # El identificador (ej: josedom)
        "displayName": display_name_formateado, # Nombre Completo (Curso)
        "email": email,                   # Correo electrónico
        "pictureUrl": ""                  # Opcional, lo dejamos vacío
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"✅ [ALTA] {uid} registrado como: {display_name_formateado}")
        else:
            print(f"❌ [ERROR] {uid}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🔥 Error de conexión: {e}")

def procesar_usuario(ldap_obj, uid):
    """Obtiene los datos de LDAP y lanza el alta."""
    datos = ldap_obj.buscar(f"(uid={uid})", attr=['cn', 'mail'])
    if datos:
        user = datos[0]
        # Extraemos valores de las listas que devuelve ldap3
        nombre = user['cn'][0] if 'cn' in user else uid
        correo = user['mail'][0] if 'mail' in user else f"{uid}@dominio.com"
        
        # Obtenemos el curso (primer grupo al que pertenece)
        cursos_usuario = ldap_obj.memberOfGroup(uid)
        curso = cursos_usuario[0] if cursos_usuario else "Sin Curso"
        
        dar_alta_headscale(uid, nombre, correo, curso)
    else:
        print(f"❓ Usuario {uid} no encontrado en LDAP.")

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 add_user_headscale.py <username_o_aula>")
        return

    objetivo = sys.argv[1]
    ldap = LibLDAP()
    
    # Lógica para Aula o Usuario
    if objetivo in ldap.grupos:
        print(f"📂 Procesando Aula: {ldap.grupos[objetivo]}...")
        res = ldap.buscar(f"(cn={objetivo})", attr=['member'], base_dn=ldap.group_dn)
        if res and 'member' in res[0]:
            miembros = [m.split(',')[0].split('=')[1] for m in res[0]['member']]
            for m_uid in miembros:
                procesar_usuario(ldap, m_uid)
    else:
        procesar_usuario(ldap, objetivo)

    ldap.logout()

if __name__ == "__main__":
    main()