#!/usr/bin/env python3

# Importation des modules nécessaires
import paramiko # Pour la connexion SSH 
import sys # Pour accéder aux arguments de la ligne de commande 
import os # Pour les opérations liées au système de fichiers 
import logging # Pour la journalisation 
import getpass # Pour demander des mots de passe de manière sécurisée

# Configuration du logging

log_file = os.path.expanduser("~/ssh_sudo_script.log") 

logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s') 

logger = logging.getLogger(__name__) 

def ssh_execute_sudo_command(hostname, username, key_file, command):

    # Création d'un client SSH
    client = paramiko.SSHClient()

    # Autorisation automatique des clés d'hôte inconnues
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
    try:

        # Expansion du chemin de la clé SSH (remplace ~ par le chemin complet)
        key_file = os.path.expanduser(key_file)
        
        # Vérification de l'existence du fichier de clé
        if not os.path.exists(key_file): 
            raise FileNotFoundError(f"Le fichier de clé {key_file} n'existe pas.")
        
        # Journalisation des informations de connexion
        logger.info(f"Tentative de connexion à {hostname} avec l'utilisateur {username}") 

        logger.info(f"Utilisation de la clé : {key_file}")
        
        # Demande de la phrase de passe pour la clé SSH
        key_password = getpass.getpass("Entrez la phrase de passe pour la clé SSH (laissez vide si pas de phrase de passe) : ")
        
        # Chargement de la clé SSH
        key = paramiko.RSAKey.from_private_key_file(key_file, password=key_password or None)
        
        # Connexion au serveur SSH
        client.connect(hostname, username=username, pkey=key) 

        logger.info("Connexion réussie. Préparation de la commande sudo...")
        
        # Demande du mot de passe sudo
        sudo_password = getpass.getpass("Entrez le mot de passe sudo : ")
        
        # Préparation de la commande sudo
        sudo_command = f"sudo -S {command}"
        
        # Ouverture d'un canal pour l'exécution interactive
        channel = client.get_transport().open_session() 
        channel.get_pty() # Demande d'un pseudo-terminal channel.exec_command(sudo_command)
        channel.exec_command(sudo_command)        
        # Envoi du mot de passe sudo
        channel.send(sudo_password + '\n')
        
        # Récupération de la sortie de la commande
        stdout_data = [] 
        stderr_data = [] 
        while True: 
            if channel.recv_ready(): 
                stdout_data.append(channel.recv(1024).decode('utf-8')) 
            if channel.recv_stderr_ready(): 
                stderr_data.append(channel.recv_stderr(1024).decode('utf-8'))
            if channel.exit_status_ready(): 
                break
        
        # Affichage de la sortie standard
        print("Sortie de la commande:") 

        print(''.join(stdout_data))
        
        # Affichage des erreurs, s'il y en a
        if stderr_data: 
            print("Erreurs:") 
            print(''.join(stderr_data)) 
    except Exception as e:
        # Gestion des erreurs
        logger.error(f"Une erreur s'est produite: {str(e)}")
        print(f"Une erreur s'est produite: {str(e)}") 
    finally:
        # Fermeture de la connexion SSH, qu'il y ait eu une erreur ou non
        client.close()

# Point d'entrée du script
if __name__ == "__main__":

    # Vérification du nombre correct d'arguments
    if len(sys.argv) != 2: 
       print("Usage: python3 ssh_login_sudo.py <command>") 
       sys.exit(1)

    # Configuration des paramètres de connexion
    hostname = "192.168.10.113" 
    username = "monitor" 
    key_file = "~/.ssh/domid_rsa" 
    command = sys.argv[1] # La commande à exécuter est passée en argument

    # Exécution de la fonction principale 
    ssh_execute_sudo_command(hostname, username, key_file, command)