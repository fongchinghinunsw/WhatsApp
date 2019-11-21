# Python 3
# Usage: python3 client.py <server_IP> <server_port>
# coding: utf-8

import sys
from socket import *
from threading import Thread
from helper import retrieve_components, decorate_chat_msg, username2password

server_IP = sys.argv[1]
server_port = int(sys.argv[2])


def login_process():
  global username

  LOGIN = True

  while LOGIN:
    prompt = client_socket.recv(2048)
    prompt = prompt.decode()
    print(prompt, flush=True, end="")
    #print(repr(prompt))

    if prompt == "Username: ":
      username = input()
      client_socket.send(username.encode())

    elif prompt == "Password: ":
      password = input()
      client_socket.send(password.encode())

    elif prompt == "Welcome back !\n":

      #print("private acceptor's server ip =", str(privateAcceptSocket.getsockname()[0]), "port =", str(privateAcceptSocket.getsockname()[1]))
      message = str(privateAcceptSocket.getsockname()[0]) + " " + str(privateAcceptSocket.getsockname()[1])
      client_socket.send(message.encode())

      LOGIN = False

  #print("Logged in")

def command_process():
  global CONNECTED
  global privateConnectSocket

  while CONNECTED:
    command = input()
    print("inputted a command")

    if command.startswith("private "):
      user, message = retrieve_components(command)

      if user not in username2password:
        print("User doesn't exist")

      if user == username:
        print("Can't send private message to yourself")

      if user in private_connections:
        #print("ready to send a private msg")
        message = "(private)" + decorate_chat_msg(username, message)
        private_connections[user].send(message.encode())
        #print("Sent a private message")
      else:
        print("You haven't executed <startprivate " + user + ">", flush=True)

      # notify the server the client entered a command, avoid getting
      # automatically logged off.
      client_socket.send("WhatsApp sent private command".encode())

      continue

    client_socket.send(command.encode())

    if command == "logout":
      for session in private_connections:
        private_connections[session].close()
      privateAcceptSocket.close()
      CONNECTED = False

  print("///")



def recv_handler():
  global client_socket
  global CONNECTED
  global privateConnectSocket
  while (1):
    prompt = client_socket.recv(2048)
    prompt = prompt.decode()

    print("Received a msg")

    if prompt == "WhatsApp " + username + " logout":
      print("You have been automatically logged out", flush=True)
      CONNECTED = False
      break

    elif prompt.startswith("WhatsApp " + username + " startprivate"):
      # you are the private initializer
      #print(prompt)
      prompt = prompt.split(' ')
      
      ip = prompt[-3]
      port = int(prompt[-2])
      target = prompt[-1]


      privateConnectSocket = socket(AF_INET, SOCK_STREAM)
      # connect to the private acceptor's private socket.
      #print("private initializer is trying to connect to ip =", str(ip), "port =", str(port))
      privateConnectSocket.connect((ip, port))

      # send to privateConnectSocket = send to the private acceptor
      private_connections[target] = privateConnectSocket

      privateInitializerThread = Thread(name="privateInitializerHandler", target=private_initializer_handler, args=[target])
      privateInitializerThread.daemon = True
      privateInitializerThread.start()

      print("You have established a private messaging session with " + target)

      continue

    elif prompt.startswith("WhatsApp " + username + " allowprivate"):
      # you are the private acceptor
      #print("Allowing private")
      prompt = prompt.split(' ')

      ip = prompt[-3]
      port = int(prompt[-2])
      target = prompt[-1]

      print("You have established a private messaging session with " + target)
      
      privateAcceptorThread = Thread(name="privateAcceptorHandler", target=private_acceptor_handler, args=[target])
      privateAcceptorThread.daemon = True
      privateAcceptorThread.start()


      print("Accepted connection")
      continue

    elif prompt.startswith("WhatsApp stopprivate with"):
      #print("Stopping private")
      prompt = prompt.split(' ')
      # close the socket
      private_connections[prompt[-1]].close()
      del private_connections[prompt[-1]]
      continue

    print(prompt, flush=True)

def private_acceptor_handler(target):
  """"""
  connectionSocket, connectionAddr = privateAcceptSocket.accept()
  #print("private acceptor receive connection from " + str(connectionAddr))
  # acceptor can use this socket to send to the initializer of this
  # private messaging session.
  private_connections[target] = connectionSocket
  
  while (1):

    msg = connectionSocket.recv(2048)
    if len(msg) == 0:
      break
    #print("Received a msg")

    print(msg.decode())


def private_initializer_handler(name):
  """ receive message from a particular user in private messaging
      session
  """
  #print(private_connections)
  private_acceptor_socket = private_connections[name]

  while (1):
    msg = private_acceptor_socket.recv(2048)
    if len(msg) == 0:
      break

    print(msg.decode())


# creates the client's socket
# perform the three-way handshake and TCP connection is established
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect((server_IP, server_port))

# stores all current private chat sockets with other users in the
# format {user1: socket1, user2: socket2, ...}
private_connections = {}

# initialize the username of this client as a global variable
username = ""
CONNECTED = True

privateAcceptSocket = socket(AF_INET, SOCK_STREAM)
privateAcceptSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
privateAcceptSocket.bind(('localhost', 0))
privateAcceptSocket.listen(1)

login_process()

recvThread = Thread(name="recvHandler", target=recv_handler)
recvThread.daemon = True
recvThread.start()

command_process()
