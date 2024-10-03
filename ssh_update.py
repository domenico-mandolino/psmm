(myenv) domenico@cli-domenico:~/psmm$ cat ssh_update.py
#!/usr/bin/env python3

import paramiko 

import smtplib 

from email.mime.text import MIMEText 

import logging 

from getpass import getpass

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 
logger = logging.getLogger(__name__)

# Configuration des serveurs
servers = [ 
    {"name": "Serveur FTP", "hostname": "192.168.10.185", "username": "monitor"}, 
    {"name": "Serveur Web", "hostname": "192.168.10.113", "username": "monitor"}, 
    {"name": "Serveur MariaDB", "hostname": "192.168.10.152", "username": "monitor"}
]
# Configuration SSH
ssh_key_path = '/home/domenico/.ssh/domid_rsa'
ssh_password = "mot de passe sudo monitor" 

# Configuration e-mail
email_config = { 
    'smtp_server': 'smtp.gmail.com', 
    'smtp_port': 587, 'sender_email': 
    'domenico.mandolino@laplateforme.io', 
    'sender_password': 'mot de passe application', 
    'recipient_email': 'domenico.mandolino@laplateforme.io'
}
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
    output = stdout.read().decode('utf-8').strip() 
    error = stderr.read().decode('utf-8').strip() 
    if error and "sudo" not in error:
        logger.error(f"Erreur lors de l'exécution de la commande: {error}")
    return output

def check_updates(ssh_client): 
    logger.info("Vérification des mises à jour disponibles...") 
    update_output = run_command(ssh_client, "apt update" , sudo=True) 
    logger.info(f"Résultat de 'apt update':\n{update_output}") 
    upgradable = run_command(ssh_client, "apt list --upgradable", sudo=True) 
    logger.info(f"Paquets pouvant être mis à jour:\n{upgradable}") 
    return "All packages are up to date" not in update_output and upgradable.strip() != ""

def perform_updates(ssh_client): 
    logger.info("Exécution des mises à jour...") 
    result = run_command(ssh_client, "DEBIAN_FRONTEND=noninteractive apt-get upgrade -y", sudo=True) 
    logger.info(f"Résultat de la mise à jour:\n{result}")
    return result

def check_reboot_required(ssh_client): 
    result = run_command(ssh_client, "[ -f /var/run/reboot-required ] && echo 'Reboot required' || echo 'No reboot needed'") 
    logger.info(f"Statut de redémarrage: {result}")
    return result

def send_email(subject, body):
    msg = MIMEText(body) 
    msg['Subject'] = subject 
    msg['From'] = email_config['sender_email'] 
    msg['To'] = email_config['recipient_email']
    
    try: 
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server: 
            server.starttls() 
            server.login(email_config['sender_email'], email_config['sender_password']) 
            server.send_message(msg)
        logger.info("E-mail envoyé avec succès.") 
    except Exception as e: 
        logger.error(f"Erreur lors de l'envoi de l'e-mail : {e}") 

def main():
    ssh_passphrase = getpass("Entrez la phrase de passe pour votre clé SSH : ") 
    reboot_required_servers = [] 
    
    for server in servers:
        logger.info(f"Vérification des mises à jour pour {server['name']} ({server['hostname']})...") 
        try: 
            ssh_client = ssh_connect(server['hostname'], server['username'], ssh_key_path, ssh_passphrase)
            if ssh_client:
                if check_updates(ssh_client): 
                    logger.info(f"Mises à jour disponibles pour {server['name']}. Installation en cours...") 
                    update_result = perform_updates(ssh_client) 
                    logger.info(f"Résultat de la mise à jour pour {server['name']}:\n{update_result}")
                
                    reboot_status = check_reboot_required(ssh_client) 
                    if "Reboot required" in reboot_status: 
                        reboot_required_servers.append(server['name']) 
                        logger.warning(f"Redémarrage nécessaire pour {server['name']} après la mise à jour.")

                else: logger.info(f"Aucune mise à jour nécessaire pour {server['name']}.")
            
                ssh_client.close() 
            else:
                logger.error(f"Impossible de se connecter à {server['name']} ({server['hostname']})")        
        except Exception as e: 
            logger.error(f"Erreur lors de la mise à jour de {server['name']}: {e}") 

    if reboot_required_servers:
        subject = "Redémarrage nécessaire après mises à jour" 
        body = f"Les serveurs suivants nécessitent un redémarrage après les mises à jour :\n\n" 
        body += "\n".join(reboot_required_servers) 
        send_email(subject, body)

if __name__ == "__main__":
    main()
(myenv) domenico@cli-domenico:~/psmm$ 