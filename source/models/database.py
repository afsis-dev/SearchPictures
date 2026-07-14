import oracledb


class Database:
    """Conexão Oracle criada sob demanda com os parâmetros informados pelo usuário.
    Erros de conexão e de consulta propagam para o chamador tratar.
    """

    def __init__(self, host, port, service, user, password):
        dsn = oracledb.makedsn(host=host, port=int(port), service_name=service)
        self.connection = oracledb.connect(user=user, password=password, dsn=dsn)

    def query(self, sql):
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
