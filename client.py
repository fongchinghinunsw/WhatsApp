# Python 3.7
# Usage: python3 client.py server_IP server_port
# coding: utf-8

import sys
from socket import *
from threading import Thread
from helper import retrieve_components, decorate_chat_msg, username2password

server_IP = sys.argv[1]
server_port = int(sys.argv[2])


def notify_terminate_connection(connections):
  """ notify all current private chatting clients to close their sockets
      correspond to this user
  """
  message = "WhatsApp terminate connection"
  message = message.encode()

  for activeuser in connections:
    connections[activeuser].send(message)


def close_sockets(connections):
  """ close all unused sockets """
  for activeuser in connections:
    connections[activeuser].close()
  

def login_process():
  """ sends/receives authentication-related input/out to/from the server
  """
  global username

  LOGIN = True

  while LOGIN:
    prompt = client_socket.recv(2048)
    prompt = prompt.decode()
    print(prompt, end="")

    # we use endswith because the message may get packed with another
    # message at the front
    if prompt.endswith("Username: "):
      username = input()
      client_socket.send(username.encode())

    elif prompt.endswith("Password: "):
      password = input()
      client_socket.send(password.encode())

    elif prompt.endswith("Welcome back !\n"):

      message = str(privateAcceptSocket.getsockname()[0]) + " " + str(privateAcceptSocket.getsockname()[1])
      client_socket.send(message.encode())

      LOGIN = False


def command_process():
  """ sends input to the server """
  global CONNECTED

  while CONNECTED:
    command = input()

    if command.startswith("private "):
      user, message = retrieve_components(command)

      if user not in username2password:
        print("User doesn't exist")

      elif user == username:
        print("Can't send private message to yourself")

      elif user in private_connections and user in noLongerOnline:
        print("Can't send to this client as he/she has logged out")

      elif user in private_connections:
        message = "(private)" + decorate_chat_msg(username, message)
        private_connections[user].send(message.encode())

      else:
        print("You haven't executed <startprivate " + user + ">")

      # notify the server the client entered a command, avoid getting
      # automatically logged off.
      client_socket.send("WhatsApp sent private command".encode())

      continue

    client_socket.send(command.encode())

    if command == "logout":
      # closes all private sockets
      notify_terminate_connection(private_connections)
      close_sockets(private_connections)
      CONNECTED = False


def recv_handler():
  """ receives messages coming from the server """
  global client_socket
  global CONNECTED
  global privateConnectSocket
  while (1):
    prompt = client_socket.recv(2048)
    prompt = prompt.decode()

    if prompt == "WhatsApp " + username + " logout":
      print("You have been automatically logged out")
      notify_terminate_connection(private_connections)
      close_sockets(private_connections)
      CONNECTED = False
      break

    elif prompt.startswith("WhatsApp " + username + " startprivate"):
      # received by the private initializer

      prompt = prompt.split(' ')
      
      ip = prompt[-3]
      port = int(prompt[-2])
      target = prompt[-1]

      if target in noLongerOnline:
        noLongerOnline.remove(target)

      privateConnectSocket = socket(AF_INET, SOCK_STREAM)
      # connect to the private acceptor's private socket.
      privateConnectSocket.connect((ip, port))

      # send to privateConnectSocket = send to the private acceptor
      private_connections[target] = privateConnectSocket

      privateInitializerThread = Thread(name="privateInitializerHandler", target=private_initializer_handler, args=[target])
      privateInitializerThread.daemon = True
      privateInitializerThread.start()

      print("You have established a private messaging session with " + target)

      continue

    elif prompt.startswith("WhatsApp " + username + " allowprivate"):
      # received by the private acceptor

      prompt = prompt.split(' ')

      target = prompt[-1]

      if target in noLongerOnline:
        noLongerOnline.remove(target)

      privateAcceptorThread = Thread(name="privateAcceptorHandler", target=private_acceptor_handler, args=[target])
      privateAcceptorThread.daemon = True
      privateAcceptorThread.start()

      continue

    elif prompt.startswith("WhatsApp stopprivate"):
      prompt = prompt.split(' ')

      if prompt[2] == "(2)":
        print("The private connection with " + prompt[-1] + " has discontinued")

      # close the socket
      private_connections[prompt[-1]].close()
      del private_connections[prompt[-1]]
      continue

    print(prompt, flush=True)

def private_acceptor_handler(name):
  """ accept a connection from another client and receives private message from it
      , this function is called by the acceptor of the session
  """
  connectionSocket, connectionAddr = privateAcceptSocket.accept()
  # acceptor can use this socket to send to the initializer of this
  # private messaging session.
  private_connections[name] = connectionSocket
  
  while (1):

    msg = connectionSocket.recv(2048)
    msg = msg.decode()

    if msg == "WhatsApp terminate connection":
      noLongerOnline.add(name)
      connectionSocket.close()
      break

    elif len(msg) == 0:
      break

    print(msg)


def private_initializer_handler(name):
  """ receive message from a particular user in private messaging session,
      this function is called by the initializer of the session.
  """
  private_acceptor_socket = private_connections[name]
  while (1):
    msg = private_acceptor_socket.recv(2048)
    msg = msg.decode()
    if msg == "WhatsApp terminate connection":
      noLongerOnline.add(name)
      private_acceptor_socket.close()
      break

    elif len(msg) == 0:
      break

    print(msg)


# creates the client's socket
# perform the three-way handshake and TCP connection is established
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect((server_IP, server_port))

# stores all current private chat sockets with other users in the
# format {user1: socket1, user2: socket2, ...}
private_connections = {}

# stores a set of private chat clients that're not online anymore
noLongerOnline = set()

# initialize the username of this client as a global variable
username = ""
CONNECTED = True

# private server socket, used to accept connection from other clients
privateAcceptSocket = socket(AF_INET, SOCK_STREAM)
privateAcceptSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
privateAcceptSocket.bind(('localhost', 0))
privateAcceptSocket.listen(1)

login_process()

recvThread = Thread(name="recvHandler", target=recv_handler)
recvThread.daemon = True
recvThread.start()

command_process()

# closes remaining sockets
client_socket.close()
privateAcceptSocket.close()
