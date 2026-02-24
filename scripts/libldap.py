from ldap3 import Server, Connection, ALL,SUBTREE,  MODIFY_DELETE, MODIFY_ADD,MODIFY_REPLACE

class LibLDAP(object):
    base_dn="ou=People,dc=gonzalonazareno,dc=org"
    group_dn="ou=Group,dc=gonzalonazareno,dc=org"
    conn=""
    isbind=False

    grupos={'asir1':'1º ASIR',
        'asir2':'2º ASIR',
        'smr1':'1º SMR',
        'smr2':'2º SMR',
        'antiguosalumnos':'Otros',
        'profesores':'Profesor',
        'antiguosprofesores':'A.P.',
        'openstackusers':'OpenStack',
        'tituladosasir':'Titulados ASIR',
        'tituladossmr':'Titulados SMR',}
    
    def __init__(self,username="",password=""):
        try:
            server = Server('ldap.gonzalonazareno.org')
        except:
            print("Error al conectar al servidor")
        try:
            if username!="":
                username="uid=%s,ou=People,dc=gonzalonazareno,dc=org" % username
                self.conn = Connection(server, username, password, auto_bind=True)
            else:
                self.conn = Connection(server,auto_bind=True)
            self.isbind=True;
        except:
            print("Error al realizar la conexión")

    def buscar(self,filter,attr=[],base_dn=base_dn):
        self.conn.search(base_dn,filter, search_scope=SUBTREE,attributes=attr)
        return [e.entry_attributes_as_dict  for e in self.conn.entries]
    
    def memberOfGroup(self,uid,key=False):
        lista=[]
        usuario="uid=%s,%s" % (uid,self.base_dn)
        grupos=self.buscar("(cn=*)",['cn','member'],self.group_dn)
        for grupo in grupos:
           
            if usuario in grupo["member"]:
                if key:
                    lista.append(grupo["cn"][0])
                else:    
                    lista.append(self.grupos[grupo["cn"][0]])
        return lista

    def isMemberOfGroup(self,uid,grupo):
        return grupo in self.memberOfGroup(uid,key=True)
    def isMemberOfGroups(self,uid,grupos=[]):
        for grupo in grupos:
            if grupo in self.memberOfGroup(uid,key=True):
                return True
        return False
    def conv_filtro(self,filtro):
        cadena=""
        if len(filtro)>0:
            cadena="(&(objectClass=inetOrgPerson)"
            for campo,valor in filtro.items():
                if campo=="grupo" and valor=='all': 
                    cadena+="(uid=*)"
                elif campo=="grupo": 
                    grupos=[valor]
                    if valor=="alumnos":
                        grupos=["asir1","asir2","smr1","smr2","antiguosalumnos"]
                    elif valor=="soloalumnos":
                        grupos=["asir1","asir2","smr1","smr2"]
                    elif valor=="allprofesores":
                        grupos=["profesores","antiguosprofesores"]
                    elif valor=="alltitulados":
                        grupos=["tituladosasir","tituladossmr"]
                    cadena2="(|"
                    for grupos in grupos:
                        cadena2+="(memberOf=cn=%s,ou=Group,dc=gonzalonazareno,dc=org)" % grupos
                    cadena2+=")"
                    cadena+=cadena2
                else:
                    cadena+="(%s=%s*)" % (campo,valor)
            cadena+=")"
        return cadena

    def logout(self):
        self.conn.unbind()
        self.isbind=False

    def add(self,uid,datos):
        usuario="uid=%s,%s" % (uid,self.base_dn)
        self.conn.add(usuario, attributes=datos)
    
    def delete(self,uid):
        usuario="uid=%s,%s" % (uid,self.base_dn)
        self.conn.delete(usuario)
    
    def modify(self,uid,datos):
        usuario="uid=%s,%s" % (uid,self.base_dn)
        for c,v in datos.items():
            datos[c]=[(MODIFY_REPLACE,[v])]
        self.conn.modify(usuario,datos)
    

    def modUserGroup(self,uid,grupo,adddel):
        modlist = []
        usuario="uid=%s,%s" % (uid,self.base_dn)
        grupo="cn=%s,%s" % (grupo,self.group_dn)
        if adddel=="add":
            return self.conn.modify(grupo,{'member': [(MODIFY_ADD, [usuario])]})
        elif adddel=="del":
            return self.conn.modify(grupo,{'member': [(MODIFY_DELETE, [usuario])]})
       