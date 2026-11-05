"""
Ce module définit la classe Server qui gère les connexions entrantes et la diffusion
des messages.

La classe ClientListener (importée) gère chaque client individuellement.
"""
#Permet à deux programmes de se parler à travers un réseau comme internet et réseau local
import socket
#Sortie du programme en cas d'erreur fatale
import sys 
#Permet de mettre en pause le programme
import time
import threading
#Importation de la classe ClientListener
from clientthread import ClientListener

class Server():
# socket.AF_INET : Utilise la famille d'adresses IPv4.
# socket.SOCK_STREAM : Utilise le protocole de transport TCP (fiable, ordonné et connecté).
#self= id et port
    def __init__(self, port):
        self.clients_sockets= []
        self.clients_lock = threading.Lock()
        self.listener= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.listener.bind(('', port))
            self.listener.listen(5)
        except OSError as error:
            self.listener.close()
            raise RuntimeError(
                f"Impossible de démarrer le serveur sur le port {port}. "
                "Le port est peut-être déjà utilisé."
            ) from error
        print(f"Serveur démarré : écoute sur le port {port}")
#on sait sur quel port le serveur écoute.

#recevoir les connexions clientes en continu.
#met le programme en pause jusqu'à ce qu'un client tente de se connecter. Dès que la connexion est établie, il retourne :
#client_socket : un nouveau socket dédié exclusivement aux échanges avec ce client.
#client_adress : un tuple (ensemble de donnée qui ne peut etre modifié) contenant (adresse_IP_client, port_éphémère).
    def run(self):
        while True:
            try:
                (client_socket, client_adress) = self.listener.accept()
            except socket.error as error:
                print(f"Erreur pendant l'acceptation d'un client : {error}")
                continue
            with self.clients_lock:
                self.clients_sockets.append(client_socket)
#Ajoute le socket du nouveau client à la liste globale self.clients_sockets pour qu'il reçoive les futurs messages diffusés.
            print("Start the thread for client:", client_adress)
            client_thread= ClientListener(self, client_socket, client_adress)
            client_thread.start()
            time.sleep(0.1)

    # Déconnexion d'un Client : remove_socket()
    def remove_socket(self, socket):
        with self.clients_lock:
            if socket in self.clients_sockets:
                self.clients_sockets.remove(socket)
#Déclare la méthode remove_socket, appelée par ClientListener.quit() lorsqu'un client quitte le chat.
#Retire le socket du client déconnecté de la liste self.clients_sockets pour ne plus tenter de lui envoyer de messages.

    #Diffusion des Messages
    #Affiche le message diffusé dans la console du serveur pour tracer l'activité.
    def echo(self, data):
        print("echoing:", data)
        with self.clients_lock:
            clients = list(self.clients_sockets)
        disconnected = []
        for sock in clients:
            try:
                sock.sendall(data.encode("UTF-8"))
            except socket.error as error:
                print(f"Client déconnecté pendant l'envoi : {error}")
                disconnected.append(sock)
        for sock in disconnected:
            self.remove_socket(sock)
            try:
                sock.close()
            except OSError:
                pass

#Point d'Entrée du Script
if __name__ == "__main__":
    try:
        Server(59001).run()
    except RuntimeError as error:
        print(f"Erreur serveur : {error}", file=sys.stderr)
        sys.exit(1)
