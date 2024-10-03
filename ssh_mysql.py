mport mysql.connector 
from mysql.connector import Error 

def connect_to_database(): 
    try:
        # Paramètres de connexion
        connection = mysql.connector.connect( 
            host='192.168.10.152', # Adresse de votre serveur MariaDB 
            database='plateflop', # Nom de votre base de données 
            user='dome', # Nom d'utilisateur 
            password='x' # Remplacez par le mot de passe de l'utilisateur
        ) 
        if connection.is_connected(): 
            print("Connexion réussie à la base de données")
            
            # Vous pouvez effectuer vos opérations ici
            return connection 

    except Error as e: 
            print(f"Erreur lors de la connexion à la base de données : {e}") 
            return None 
def main(): 
    db_connection = connect_to_database() 
    if db_connection:
        # Fermez la connexion à la base de données après l'utilisation
        db_connection.close() 