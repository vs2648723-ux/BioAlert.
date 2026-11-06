import mysql.connector
from config import DB

def conectar():
    return mysql.connector.connect(**DB, charset="utf8mb4")
