#!/usr/bin/env python3

import paramiko
import subprocess
import os
import logging
from datetime import datetime
import glob

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration SSH
ssh_config = {
    'hostname': '192.168.10.113',
    'username': 'monitor',
    'key_filename': '/home/domenico/.ssh/domid_rsa',
    'port': 22
}

# Configuration MySQL
db_config = {
    'host': '192.168.10.152',
    'user': 'dome',
    'password': 'votre_mot_de_passe_mysql',
    'database': 'plateflop'
}

# Configuration de la sauvegarde
backup_dir = '/home/domenico/pssm/backups'
backup_prefix = 'plateflop_backup_'
max_backups = 7

def ssh_execute_command(client, command, sudo=False):
    if sudo:
        command = f"sudo -S {command}"
    
    stdin, stdout, stderr = client.exec_command(command, get_pty=True)
    
    if sudo:
        stdin.write('votre_mot_de_passe_sudo\n')
        stdin.flush()
    
    return stdout.read().decode(), stderr.read().decode()

def create_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{backup_prefix}{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_file)

    # Création de la commande de sauvegarde
    backup_command = (
        f"mysqldump -h {db_config['host']} -u {db_config['user']} "
        f"-p{db_config['password']} {db_config['database']} > {backup_path}"
    )

    try:
        # Exécution de la commande de sauvegarde
        subprocess.run(backup_command, shell=True, check=True, stderr=subprocess.PIPE)
        logger.info(f"Sauvegarde créée : {backup_file}")

        # Suppression des anciennes sauvegardes si nécessaire
        cleanup_old_backups()
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la création de la sauvegarde : {e.stderr.decode()}")

def cleanup_old_backups():
    # Liste tous les fichiers de sauvegarde
    backups = glob.glob(os.path.join(backup_dir, f"{backup_prefix}*.sql"))
    
    # Trie les fichiers par date de modification (le plus récent en premier)
    backups.sort(key=os.path.getmtime, reverse=True)
    
    # Supprime les sauvegardes excédentaires
    for old_backup in backups[max_backups:]:
        os.remove(old_backup)
        logger.info(f"Ancienne sauvegarde supprimée : {os.path.basename(old_backup)}")

def main():
    try:
        # Création du répertoire de sauvegarde s'il n'existe pas
        os.makedirs(backup_dir, exist_ok=True)

        # Création de la sauvegarde
        create_backup()

    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite : {e}")

if __name__ == "__main__":
    main()