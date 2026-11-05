import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


class Client:
    """Client réseau ; les callbacks ne doivent pas modifier les widgets Tkinter."""

    def __init__(self, username, server, port, on_message=None, on_disconnect=None):
        username = username.strip()
        if not username:
            raise ValueError("Le prénom ne peut pas être vide.")
        if not server.strip() or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("Adresse ou port invalide.")
        if "\n" in username or "\r" in username:
            raise ValueError("Le prénom doit tenir sur une ligne.")
        self.username = username
        self.on_message = on_message or print
        self.on_disconnect = on_disconnect or (lambda: None)
        self.listening = False
        self._close_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._closed = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.settimeout(10)
            self.socket.connect((server.strip(), port))
            self.socket.sendall(f"USERNAME {username}\n".encode("utf-8"))
            self.socket.settimeout(None)
        except OSError as error:
            self.socket.close()
            raise ConnectionError(
                f"Connexion impossible à {server}:{port}. Vérifiez le serveur, "
                "Tailscale, l'adresse IP et le port."
            ) from error
        self.listening = True

    def listener(self):
        pending = b""
        try:
            while self.listening:
                data = self.socket.recv(1024)
                if not data:
                    break
                pending += data
                while b"\n" in pending and self.listening:
                    line, pending = pending.split(b"\n", 1)
                    self.handle_msg(line.decode("utf-8", errors="replace").rstrip("\r"))
            if pending and self.listening:
                self.handle_msg(pending.decode("utf-8", errors="replace"))
        except OSError as error:
            if self.listening:
                self.on_message(f"Connexion interrompue : {error}")
        finally:
            self.tidy_up()
            self.on_disconnect()

    def listen(self):
        if hasattr(self, "listen_thread") or not self.listening:
            return
        self.listen_thread = threading.Thread(target=self.listener, daemon=True)
        self.listen_thread.start()

    def send(self, message):
        if not message.strip() or "\n" in message or "\r" in message:
            raise ValueError("Le message doit être non vide et tenir sur une ligne.")
        try:
            with self._send_lock:
                if not self.listening:
                    raise ConnectionError("Le client est déconnecté.")
                self.socket.sendall((message + "\n").encode("utf-8"))
        except OSError as error:
            self.tidy_up()
            raise ConnectionError("Le message n'a pas pu être envoyé.") from error

    def tidy_up(self):
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            self.listening = False
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()

    def handle_msg(self, data):
        if data in ("QUIT", ""):
            self.tidy_up()
        else:
            self.on_message(data)


class ChatApplication:
    def __init__(self, root):
        self.root = root
        self.client = None
        self.session = 0
        self.connecting = False
        self.events = queue.Queue()
        self.closed = threading.Event()
        self.root.title("Messagerie")
        self.root.geometry("760x520")
        self.root.minsize(620, 400)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        panel = ttk.Frame(root, padding=16)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        connection = ttk.LabelFrame(panel, text="Connexion", padding=10)
        connection.grid(row=0, column=0, sticky="ew")
        self.username = tk.StringVar(value="asmaa")
        self.server = tk.StringVar(value="100.80.2.24")
        self.port = tk.StringVar(value="59001")
        self.connection_fields = []
        for column, (label, variable) in enumerate((
            ("Prénom", self.username), ("Adresse du serveur", self.server),
            ("Port", self.port),
        )):
            connection.columnconfigure(column, weight=1)
            ttk.Label(connection, text=label).grid(row=0, column=column, sticky="w")
            field = ttk.Entry(connection, textvariable=variable, width=18)
            field.grid(row=1, column=column, sticky="ew", padx=(0, 10))
            self.connection_fields.append(field)
        self.connect_button = ttk.Button(connection, text="Se connecter", command=self.connect)
        self.connect_button.grid(row=1, column=3)
        self.disconnect_button = ttk.Button(connection, text="Se déconnecter", command=self.disconnect, state="disabled")
        self.disconnect_button.grid(row=2, column=3, pady=(8, 0))
        self.status = tk.StringVar(value="Déconnecté")
        ttk.Label(panel, textvariable=self.status).grid(row=1, column=0, sticky="w", pady=10)
        self.messages = scrolledtext.ScrolledText(panel, wrap="word", state="disabled")
        self.messages.grid(row=2, column=0, sticky="nsew")
        compose = ttk.Frame(panel)
        compose.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        compose.columnconfigure(0, weight=1)
        self.message = tk.StringVar()
        self.message_field = ttk.Entry(compose, textvariable=self.message, state="disabled")
        self.message_field.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.message_field.bind("<Return>", self.send)
        self.send_button = ttk.Button(compose, text="Envoyer", command=self.send, state="disabled")
        self.send_button.grid(row=0, column=1)
        self.root.after(100, self.process_events)

    def append_message(self, message):
        self.messages.configure(state="normal")
        self.messages.insert("end", message if message.endswith("\n") else message + "\n")
        self.messages.see("end")
        self.messages.configure(state="disabled")

    def connect(self):
        if self.connecting or self.client is not None:
            return
        username, server = self.username.get().strip(), self.server.get().strip()
        try:
            port = int(self.port.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Connexion", "Le port doit être un nombre entre 1 et 65535.")
            return
        if not username or not server:
            messagebox.showerror("Connexion", "Renseignez le prénom et l'adresse du serveur.")
            return
        self.connect_button.configure(state="disabled")
        self.connecting = True
        self.session += 1
        for field in self.connection_fields:
            field.configure(state="disabled")
        self.status.set("Connexion en cours…")
        threading.Thread(target=self.open_connection, args=(username, server, port, self.session), daemon=True).start()

    def open_connection(self, username, server, port, session):
        try:
            client = Client(username, server, port,
                            lambda msg: self.events.put((session, "message", msg)),
                            lambda: self.events.put((session, "disconnected", None)))
            self.events.put((session, "connected", client))
            if self.closed.is_set():
                client.tidy_up()
        except (ValueError, ConnectionError) as error:
            self.events.put((session, "error", str(error)))

    def process_events(self):
        try:
            while True:
                session, kind, value = self.events.get_nowait()
                if session != self.session:
                    if kind == "connected":
                        value.tidy_up()
                    continue
                if kind == "connected":
                    self.connecting = False
                    self.client = value
                    self.disconnect_button.configure(state="normal")
                    self.status.set(f"Connecté : {value.username}")
                    self.message_field.configure(state="normal")
                    self.send_button.configure(state="normal")
                    self.message_field.focus_set()
                    value.listen()
                elif kind == "message":
                    self.append_message(value)
                elif kind in ("disconnected", "error"):
                    self.connecting = False
                    self.client = None
                    self.disconnect_button.configure(state="disabled")
                    self.status.set("Déconnecté")
                    self.connect_button.configure(state="normal")
                    for field in self.connection_fields:
                        field.configure(state="normal")
                    self.message_field.configure(state="disabled")
                    self.send_button.configure(state="disabled")
                    if kind == "error":
                        messagebox.showerror("Connexion", value)
                    else:
                        self.append_message("La connexion est fermée.")
                elif kind == "send_failed":
                    self.message.set(value)
                elif kind == "sent" and self.client is not None and self.client.listening:
                    self.message_field.configure(state="normal")
                    self.send_button.configure(state="normal")
                    self.message_field.focus_set()
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)

    def send(self, event=None):
        message = self.message.get().strip()
        if not message or self.client is None or str(self.send_button["state"]) == "disabled":
            return
        self.message.set("")
        self.message_field.configure(state="disabled")
        self.send_button.configure(state="disabled")
        threading.Thread(target=self.send_message, args=(self.client, message, self.session), daemon=True).start()

    def send_message(self, client, message, session):
        try:
            client.send(message)
            if message == "QUIT":
                client.tidy_up()
            else:
                self.events.put((session, "sent", None))
        except (ConnectionError, ValueError) as error:
            self.events.put((session, "send_failed", message))
            self.events.put((session, "message", str(error)))
            if client.listening:
                self.events.put((session, "sent", None))

    def disconnect(self):
        if self.client is None:
            return
        self.disconnect_button.configure(state="disabled")
        self.message_field.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.status.set("Déconnexion en cours…")
        threading.Thread(target=self.send_message, args=(self.client, "QUIT", self.session), daemon=True).start()

    def close(self):
        self.closed.set()
        if self.client is not None:
            self.client.tidy_up()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    ChatApplication(root)
    root.mainloop()
