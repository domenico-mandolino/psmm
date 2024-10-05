#!/usr/bin/env python3

import paramiko 

import requests 

import logging 

from getpass import getpass 

from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 
logger = logging.getLogger(__name__)

# Configuration des serveurs
servers = [ {"name": "Serveur FTP", "hostname": "192.168.10.185", "username": "monitor"}, 
            {"name": "Serveur Web", "hostname": "192.168.10.113", "username": "monitor"}, 
            {"name": "Serveur MariaDB", "hostname": "192.168.10.152", "username": "monitor"}
]

# Configuration SSH
ssh_key_path = '/home/domenico/.ssh/domid_rsa' 
ssh_password = " " # Mot de passe SSH et sudo

# URL du webhook Google Chat
WEBHOOK_URL = "" 

def ssh_connect(hostname, username, ssh_key, passphrase):
    client = paramiko.SSHClient() 
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
    try: 
        private_key = paramiko.RSAKey.from_private_key_file(ssh_key, password=passphrase) 
        client.connect(hostname, username=username, pkey=private_key, timeout=10) 
        return client

    except Exception as e: 
        logger.error(f"Erreur de connexion à {hostname}: {e}") 
        return None 

def run_command(ssh_client, command, sudo=False): 
    if sudo:
        command = f"echo {ssh_password} | sudo -S {command}" 
    stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True) 
    return stdout.read().decode('utf-8').strip()

def check_updates(ssh_client): 
    logger.info("Vérification des mises à jour disponibles...") 
    run_command(ssh_client, "sudo apt update", sudo=True) 
    upgradable = run_command(ssh_client, "apt list --upgradable | grep -v Listing", sudo=True) 
    return upgradable.strip().split("\n") if upgradable.strip() else []

def get_system_status(ssh_client): 
    cpu_usage = run_command(ssh_client, "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'") 
    mem_usage = run_command(ssh_client, "free | grep Mem | awk '{print $3/$2 * 100.0}'") 
    disk_usage = run_command(ssh_client, "df -h / | awk 'NR==2 {print $5}'") 
    try:
        cpu_usage = round(float(cpu_usage.replace(',', '.')), 1) 
        mem_usage = round(float(mem_usage.replace(',', '.')), 1)
        disk_usage = round(float(disk_usage.rstrip('%').replace(',', '.')), 1)
        return f"CPU: {cpu_usage}%, RAM: {mem_usage:.1f}%, Disque: {disk_usage}%" 
    
    except ValueError as e: 
        logger.error(f"Erreur lors de la conversion des valeurs : {e}")
        return f"CPU: {cpu_usage:.1f}%, RAM: {mem_usage:.1f}%, Disque: {disk_usage:.1f}%" 
def send_chat_message(message): 
    payload = {"text": message} 
    try:    
        response = requests.post(WEBHOOK_URL, json=payload) 
        response.raise_for_status() # Lève une exception pour les codes d'état HTTP d'erreur
        logger.info(f"Message envoyé avec succès. Statut: {response.status_code}") 
    except requests.exceptions.RequestException as e:
        logger.error(f"Échec de l'envoi du message. Erreur: {e}")

def main(): 
    ssh_passphrase = getpass("Entrez la phrase de passe pour votre clé SSH : ") 
    status_message = f"État des serveurs au {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n\n" 
    
    for server in servers:
        logger.info(f"Vérification du serveur {server['name']}...") 
        try:
            ssh_client = ssh_connect(server['hostname'], server['username'], ssh_key_path, ssh_passphrase) 
            if ssh_client: 
                status = get_system_status(ssh_client) 
                updates = check_updates(ssh_client) 
                status_message += f"{server['name']}:\n" 
                status_message += f" État: {status}\n" 
                if updates:
                     status_message += f" Mises à jour disponibles: {len(updates)}\n" 
                else: 
                    status_message += " Aucune mise à jour disponible\n" 
                ssh_client.close()
            else:
                status_message += f"**{server['name']}**: Impossible de se connecter\n" 
        except Exception as e: 
            status_message += f"**{server['name']}**: Erreur - {str(e)}\n"
        status_message += "\n" 

    logger.info("Envoi du rapport au chat Google...")    
    logger.info(f"Message envoyé : {status_message}")
    send_chat_message(status_message) 
    logger.info("Rapport envoyé avec succès.")

if __name__ == "__main__":
    main()
