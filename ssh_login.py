#!/usr/bin/env python3

# Cette ligne indique au système d'utiliser l'interpréteur Python 3


# Importation des modules nécessaires

import paramiko  # Pour la connexion SSH

import sys       # Pour accéder aux arguments de la ligne de commande

import os        # Pour les opérations liées au système de fichiers

import logging   # Pour la journalisation

import getpass   # Pour demander la phrase de passe de manière sécurisée


# Configuration du logging (journalisation)

log_file = os.path.expanduser("~/ssh_script.log")  # Définit le chemin du fichier de log

logging.basicConfig(filename=log_file, level=logging.DEBUG,

                    format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)  # Crée un objet logger pour ce script


def ssh_execute_command(hostname, username, key_file, command):

    # Fonction principale pour exécuter une commande via SSH

    client = paramiko.SSHClient()  # Crée un nouveau client SSH

    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Accepte automatiquement les clés d'hôte inconnues


    try:

        key_file = os.path.expanduser(key_file)  # Développe le chemin du fichier de clé (ex: '~' devient '/home/user')

        

        if not os.path.exists(key_file):

            raise FileNotFoundError(f"Le fichier de clé {key_file} n'existe pas.")

        

        logger.info(f"Tentative de connexion à {hostname} avec l'utilisateur {username}")

        logger.info(f"Utilisation de la clé : {key_file}")

        

        # Demande la phrase de passe de manière sécurisée

        passphrase = getpass.getpass("Entrez la phrase de passe pour la clé (laissez vide si pas de phrase de passe) : ")

        

        # Charge la clé privée

        key = paramiko.RSAKey.from_private_key_file(key_file, password=passphrase or None)

        

        # Établit la connexion SSH

        client.connect(hostname, username=username, pkey=key)


        logger.info("Connexion réussie. Exécution de la commande...")

        # Exécute la commande sur le serveur distant

        stdin, stdout, stderr = client.exec_command(command)


        print("Sortie de la commande:")

        # Affiche la sortie de la commande

        for line in stdout:

            print(line.strip())


        # Vérifie s'il y a des erreurs

        error = stderr.read().decode()

        if error:

            print("Erreurs:", error)


    # Gestion des différentes exceptions possibles

    except FileNotFoundError as e:

        logger.error(str(e))

        print(str(e))

    except paramiko.ssh_exception.PasswordRequiredException:

        logger.error("La clé nécessite une phrase de passe, mais aucune n'a été fournie.")

        print("La clé nécessite une phrase de passe, mais aucune n'a été fournie.")

    except paramiko.AuthenticationException as e:

        logger.error(f"Erreur d'authentification: {str(e)}")

        print(f"Erreur d'authentification: {str(e)}")

    except paramiko.SSHException as e:

        logger.error(f"Erreur SSH: {str(e)}")

        print(f"Erreur SSH: {str(e)}")

    except Exception as e:

        logger.error(f"Une erreur inattendue s'est produite: {str(e)}")

        print(f"Une erreur inattendue s'est produite: {str(e)}")

    finally:

        # Ferme toujours la connexion, même en cas d'erreur

        client.close()


# Point d'entrée du script

if __name__ == "__main__":

    if len(sys.argv) != 5:

        print("Usage: python ssh_login.py <hostname> <username> <key_file> <command>")

        sys.exit(1)


    # Récupère les arguments de la ligne de commande

    hostname = sys.argv[1]

    username = sys.argv[2]

    key_file = sys.argv[3]

    command = sys.argv[4]


    # Appelle la fonction principale

    ssh_execute_command(hostname, username, key_file, command)