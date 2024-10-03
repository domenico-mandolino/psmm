#!/usr/bin/env python3

import paramiko
import smtplib
import mysql.connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from getpass import getpass

# Configuration SSH
ssh_config = {
    'hostname': '192.168.10.152',  # Adresse IP du serveur mail
    'username': 'dome',
    'key_filename': '/home/domenico/.ssh/domid_rsa',
    'port': 22
}

# Configuration MySQL
db_config = {
    'host': '192.168.10.152',
    'user': 'dome',
    'password': getpass("Entrez le mot de passe MySQL pour dome : "),
    'database': 'plateflop'
}

# Configuration e-mail
smtp_server = "192.168.10.152"
smtp_port = 25  # Port SMTP standard
sender_email = "dome@srv-mail.homelab.lan"
receiver_email = "admin@homelab.lan"

def get_yesterday_logs():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    query = f"""
    SELECT error_type, error_message, timestamp 
    FROM error_log 
    WHERE DATE(timestamp) = '{yesterday}'
    ORDER BY timestamp
    """
    
    cursor.execute(query)
    logs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return logs

def format_logs(logs):
    formatted_logs = ""
    for log in logs:
        formatted_logs += f"{log[2]} - {log[0]}: {log[1]}\n"
    return formatted_logs

def send_email(logs):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Rapport des tentatives de connexion du {(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}"

    body = f"Voici les tentatives de connexion enregistrées hier :\n\n{format_logs(logs)}"
    message.attach(MIMEText(body, "plain"))

    try:
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(**ssh_config)
            
            stdin, stdout, stderr = ssh.exec_command(f"echo '{message.as_string()}' | sendmail -t")
            
            if stderr.read():
                print(f"Erreur lors de l'envoi de l'e-mail : {stderr.read().decode()}")
            else:
                print("E-mail envoyé avec succès.")
    except Exception as e:
        print(f"Erreur lors de la connexion SSH ou de l'envoi de l'e-mail : {str(e)}")

if __name__ == "__main__":
    logs = get_yesterday_logs()
    if logs:
        send_email(logs)
    else:
        print("Aucune tentative de connexion enregistrée hier.")
