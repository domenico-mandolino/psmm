#!/usr/bin/env python3

import paramiko
import mysql.connector
import logging
from getpass import getpass
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration SSH (réutilisez la même que dans votre script précédent)
ssh_config = {
    'hostname': '192.168.10.113',
    'username': 'monitor',
    'key_filename': '/home/domenico/.ssh/domid_rsa',
    'port': 22
}

# Configuration MySQL (réutilisez la même que dans votre script précédent)
db_config = {
    'host': '192.168.10.152',
    'user': 'dome',
    'password': getpass("Entrez le mot de passe MySQL pour dome :"),
    'database': 'plateflop'
}

# Configuration du serveur SMTP (pour Gmail)
smtp_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_username': 'domenico.mandolino@laplateforme.io',  
    'smtp_password': 'mot de passe appliaction',
    'from_email': 'domenico.mandolino@laplateforme.io',  # Même que smtp_username
    'to_email': 'plateflop_admin@example.com'  # L'e-mail de l'administrateur
}

# Fonction pour récupérer les logs de la veille depuis la base de données
def get_yesterday_logs(cursor):
    yesterday = datetime.now() - timedelta(days=1)
    query = """
    SELECT error_type, error_message, timestamp 
    FROM error_log 
    WHERE DATE(timestamp) = DATE(%s)
    ORDER BY timestamp
    """
    cursor.execute(query, (yesterday,))
    return cursor.fetchall()
# Function pour formater les logs en un message e-mail
def format_email_message(logs):
    if not logs:
        return "Aucune tentative de connexion n'a été enregistrée hier."

    message = "Historique des tentatives de connexion d'hier :\n\n"
    for log in logs:
        error_type, error_message, timestamp = log
        message += f"Date/Heure: {timestamp}\n"
        message += f"Type d'erreur: {error_type}\n"
        message += f"Message: {error_message}\n"
        message += "-" * 50 + "\n"

    return message

#Fonction pour envoyer l'e-mail 
def send_email(subject, body):
    message = MIMEMultipart()
    message["From"] = smtp_config['from_email']
    message["To"] = smtp_config['to_email']
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
            server.starttls()
            server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
            server.send_message(message)
        logger.info("E-mail envoyé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'e-mail : {e}")

# Maintenant, assemblons tout dans la fonction principale
def main():
    try:
        # Connexion à la base de données
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        logger.info("Connexion à MySQL établie avec succès.")

        # Récupération des logs d'hier
        logs = get_yesterday_logs(cursor)
        
        # Formatage du message
        email_body = format_email_message(logs)
        
        # Envoi de l'e-mail
        subject = "Rapport quotidien des tentatives de connexion"
        send_email(subject, email_body)

    except mysql.connector.Error as db_err:
        logger.error(f"Erreur de base de données : {db_err}")
    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite : {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
        logger.info("Connexion à la base de données fermée.")

if __name__ == "__main__":
    main()