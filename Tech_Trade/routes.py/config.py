import mysql.connector

class ConexaoBD:
    def __init__(self):
        self.con = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="",
            database="tech_trade_db"
        )
        self.cursor = self.con.cursor()

    def select(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def insert(self, query):
        self.cursor.execute(query)
        self.con.commit()
        return self.cursor.lastrowid

    def update(self, query):
        self.cursor.execute(query)
        self.con.commit()
        return True

    def delete(self, query):
        self.cursor.execute(query)
        self.con.commit()
        return True

    def close(self):
        self.cursor.close()
        self.con.close()
