"""
Ce module gère la réception et l'analyse des messages envoyés par un client.
"""
from socket import socket
import threading 
#Il fournit la classe Thread dont hérite ClientListener pour s'exécuter en tâche de fond en parallèle du serveur.
import re 
import time

#Thread, chaque instance devient un thread à part entière, dont le code s'exécutera lors de l'appel à .start().
#server : L'objet Server parent (pour pouvoir appeler ses méthodes echo et remove_socket).
#socket : Le socket TCP dédié à ce client.
#address : Le tuple (IP, Port) du client.
class ClientListener(threading.Thread):

    def __init__(self, server, socket, address):
        super(ClientListener, self).__init__(daemon=True)
        self.server= server
        self.socket= socket
        self.address= address
        self.listening= True
        self.username= "No username"

#Boucle d'Écoute du Thread
    def run(self):
        pending = b""
        while self.listening:
            data= ""
            try:
                data = self.socket.recv(1024)
            except socket.error as error:
                print(f"Réception impossible pour {self.address} : {error}")
                break
            if not data:
                break
            pending += data
            while b"\n" in pending and self.listening:
                line, pending = pending.split(b"\n", 1)
                self.handle_msg(line.decode('UTF-8', errors='replace').strip())
        if self.listening:
            self.quit()
        print("Ending client thread for", self.address)
 
 #Procédure de Déconnexion Propre : quit()
    def quit(self):
        self.listening = False
        self.server.remove_socket(self.socket)
        try:
            self.socket.close()
        except OSError:
            pass
        self.server.echo("{0} has quit\n".format(self.username))

#Analyse et Routage du Message :
#Diffuse à tout le chat l'annonce d'arrivée
    def handle_msg(self, data):
        print(self.address, "sent :", data)
        username_result = re.fullmatch(r'USERNAME\s+(.+)', data)
        if username_result:
            self.username = username_result.group(1)
            self.server.echo("{0} has joined.\n".format(self.username))
        elif data == "QUIT":
            self.quit()
        elif data == "":
            self.quit()
        elif data:
            self.server.echo("{0}: {1}\n".format(self.username, data))
