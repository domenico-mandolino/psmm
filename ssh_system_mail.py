#!/usr/bin/env python3
import mysql.connector
import paramiko
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from getpass import getpass

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration de la base de données (sans le mot de passe)
db_config = {
    'host': '192.168.10.152',
    'user': 'dome',
    'database': 'plateflop'
}

# Configuration SSH
ssh_config = {
    'hostname': '192.168.10.113',
    'username': 'monitor',
    'key_filename': '/home/domenico/.ssh/domid_rsa',
    'port': 22
}

# Configuration des seuils d'alerte
SEUILS = {
    'CPU': 70,
    'RAM': 80,
    'DISK': 90
}

# Configuration e-mail
email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'domenico.mandolino@laplateforme.io',
    'sender_password': 'votre_mot_de_passe_email',
    'recipient_email': 'domenico.mandolino@laplateforme.io'
}

def ensure_table_exists(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            cpu_usage FLOAT NOT NULL,
            ram_total INT NOT NULL,
            ram_used INT NOT NULL,
            disk_usage FLOAT NOT NULL
        )
    """)
    logger.info("La table system_status a été vérifiée/créée avec succès.")

def send_alert_email(cpu_usage, ram_usage, disk_usage):
    subject = "Alerte - Ressources système critiques"
    body = f"""
    Attention, les seuils critiques suivants ont été dépassés :
    
    CPU Usage: {cpu_usage:.2f}% (Seuil: {SEUILS['CPU']}%)
    RAM Usage: {ram_usage:.2f}% (Seuil: {SEUILS['RAM']}%)
    Disk Usage: {disk_usage:.2f}% (Seuil: {SEUILS['DISK']}%)
    
    Veuillez vérifier le système dès que possible.
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_config['sender_email']
    msg['To'] = email_config['recipient_email']
    
    try:
        logger.info(f"Tentative d'envoi d'e-mail à {email_config['recipient_email']}")
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['sender_email'], email_config['sender_password'])
            server.send_message(msg)
        logger.info("E-mail d'alerte envoyé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'e-mail : {e}")

def check_thresholds(cpu_usage, ram_usage, disk_usage):
    alerts = []
    if cpu_usage > SEUILS['CPU']:
        alerts.append(f"CPU Usage: {cpu_usage:.2f}% > {SEUILS['CPU']}%")
    if ram_usage > SEUILS['RAM']:
        alerts.append(f"RAM Usage: {ram_usage:.2f}% > {SEUILS['RAM']}%")
    if disk_usage > SEUILS['DISK']:
        alerts.append(f"Disk Usage: {disk_usage:.2f}% > {SEUILS['DISK']}%")
    return alerts

def main():
    try:
        # Demande du mot de passe de la base de données
        db_password = getpass("Entrez le mot de passe pour la base de données MySQL : ")
        db_config['password'] = db_password

        # Demande de la phrase de passe SSH
        ssh_passphrase = getpass("Entrez la phrase de passe pour votre clé SSH : ")

        # Connexion à la base de données
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        logger.info("Connexion MySQL établie avec succès.")

        # Vérification/création de la table
        ensure_table_exists(cursor)

        # Connexion SSH avec clé et phrase de passe
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_key = paramiko.RSAKey.from_private_key_file(ssh_config['key_filename'], password=ssh_passphrase)
        ssh.connect(hostname=ssh_config['hostname'], 
                    username=ssh_config['username'], 
                    pkey=ssh_key, 
                    port=ssh_config['port'])
        logger.info("Connexion SSH établie avec succès.")

        # Récupération des informations système
        cpu_command = "top -bn1 | grep 'Cpu(s)'"
        ram_command = "free -m"
        disk_command = "df -h /"

        stdin, stdout, stderr = ssh.exec_command(cpu_command)
        cpu_info = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command(ram_command)
        ram_info = stdout.read().decode().strip()
        stdin, stdout, stderr = ssh.exec_command(disk_command)
        disk_info = stdout.read().decode().strip()

        # Traitement des informations
        cpu_usage = float(cpu_info.split(",")[0].split()[1])  # Extrait le pourcentage CPU
        ram_total = int(ram_info.splitlines()[1].split()[1])  # Total RAM en Mo
        ram_used = int(ram_info.splitlines()[1].split()[2])  # RAM utilisée en Mo
        ram_usage = (ram_used / ram_total) * 100  # Pourcentage d'utilisation RAM
        disk_usage = float(disk_info.splitlines()[1].split()[4][:-1])  # Utilisation disque

        logger.info(f"Statistiques récupérées : CPU {cpu_usage}%, RAM {ram_usage:.2f}%, Disk {disk_usage}%")

        # Vérification des seuils et envoi d'e-mail si nécessaire
        alerts = check_thresholds(cpu_usage, ram_usage, disk_usage)
        if alerts:
            logger.warning("Seuils dépassés : " + ", ".join(alerts))
            send_alert_email(cpu_usage, ram_usage, disk_usage)
        else:
            logger.info("Tous les seuils sont respectés. Aucune alerte envoyée.")

        # Insertion des données dans la base de données
        timestamp = datetime.now()
        cursor.execute(
            "INSERT INTO system_status (timestamp, cpu_usage, ram_total, ram_used, disk_usage) VALUES (%s, %s, %s, %s, %s)",
            (timestamp, cpu_usage, ram_total, ram_used, disk_usage)
        )

        # Suppression des données plus anciennes que 72 heures
        delete_time = timestamp - timedelta(hours=72)
        cursor.execute("DELETE FROM system_status WHERE timestamp < %s", (delete_time,))
        
        conn.commit()
        logger.info("Statut système inséré avec succès dans la base de données.")

    except paramiko.SSHException as ssh_err:
        logger.error(f"Erreur de connexion SSH : {ssh_err}")
    except mysql.connector.Error as db_err:
        logger.error(f"Erreur de base de données : {db_err}")
    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite : {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
        if 'ssh' in locals():
            ssh.close()
        logger.info("Toutes les connexions ont été fermées.")

if __name__ == "__main__":
    main()