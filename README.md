## tp_python_clientserver_chat

Simple client serveur app

## Travail à faire :

- télécharger le projet
- lire le code et le commenter
- executer et tester
  `python server.py`
  `python client.py`
- proposer des améliorations du programme

## Lancer le serveur avec Tailscale

Sur le PC de la personne qui héberge le serveur, ouvrir PowerShell dans ce
dossier puis exécuter :

```text
python server.py
```

Le serveur écoute sur le port `59001`. Il doit rester ouvert pendant toute la
conversation. Pour arrêter le serveur, utiliser `Ctrl+C`.

## Lancer un client

La fenêtre propose la connexion, l'affichage des messages et l'envoi par
**Envoyer** ou **Entrée**. Le bouton **Se déconnecter** ferme la connexion sans
fermer la fenêtre ; **Se connecter** permet ensuite de rejoindre le serveur.
Un message dont l'envoi échoue est conservé dans le champ de saisie.

Le client et le serveur délimitent chaque commande et message par un saut de
ligne. Utiliser les versions mises à jour des deux programmes ensemble.
Les opérations réseau s'exécutent en arrière-plan pour garder la fenêtre réactive.

Tests locaux : `python -m unittest discover -s . -p test_client.py -v`.

Chaque participant doit avoir Tailscale installé et connecté au même réseau.
Dans un autre terminal, exécuter :

```text
python client.py
```

Remplir les champs de connexion puis cliquer sur **Se connecter** :

- **Prénom** : votre prénom ;
- **Adresse du serveur** : `100.80.2.24` ;
- **Port** : `59001`.

Pour tester sur le même ordinateur que le serveur, utiliser `127.0.0.1`.
La personne qui héberge le serveur doit aussi lancer `python client.py` dans
un autre terminal pour ouvrir sa propre fenêtre de conversation.

Si la connexion échoue, vérifier que le serveur est lancé, que Tailscale est
connecté sur les deux ordinateurs et que l'adresse IP est bien celle de la
machine qui héberge `server.py`. Écrire `QUIT` pour quitter le chat.
