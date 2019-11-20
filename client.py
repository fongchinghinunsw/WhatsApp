# Python 3
# Usage: python3 UDPClient3.py localhost 12000
# coding: utf-8
from socket import *
import sys
from threading import Thread
import time

# Server would be running on the same host as Client
serverName = sys.argv[1]
serverPort = int(sys.argv[2])

# creates the client's socket
# perform the three-way handshake and TCP connection is established
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

currentPrivateConnection = {}

username = ""
CONNECTED = True

privateAcceptSocket = socket(AF_INET, SOCK_STREAM)
privateAcceptSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
# binds the port number to the server's socket, the IP address of the server is localhost
privateAcceptSocket.bind(('localhost', 0))
privateAcceptSocket.listen(1)

def retrieve_components(command):
  """ split the command and return a list of arguments """
  command = command.strip(' ')
  command = command.split(' ')
  first_component = command.pop(0)

  if first_component == "message" or first_component == "private":
    return [command[0], ' '.join(command[1:])]
  elif first_component == "broadcast":
    return ' '.join(command)
  elif len(command) != 1:
    return command
  else:
    return command[0]

def login_process():
  global username

  LOGIN = True

  while LOGIN:
    prompt = clientSocket.recv(2048)
    prompt = prompt.decode()
    print(prompt, flush=True, end="")


    if prompt == "Username: ":
      username = input()
      clientSocket.send(username.encode())

    elif prompt == "Password: ":
      password = input()
      clientSocket.send(password.encode())

    elif prompt == "Welcome back !\n":

      print("private acceptor's server ip =", str(privateAcceptSocket.getsockname()[0]), "port =", str(privateAcceptSocket.getsockname()[1]))
      message = str(privateAcceptSocket.getsockname()[0]) + " " + str(privateAcceptSocket.getsockname()[1])
      clientSocket.send(message.encode())

      LOGIN = False

  print("Logged in")

def command_process():
  global CONNECTED
  global privateConnectSocket

  while CONNECTED:
    command = input()

    if command.startswith("private"):
      user, message = retrieve_components(command)


      if user in currentPrivateConnection:
        print("ready to send a private msg")
        currentPrivateConnection[user].send(message.encode())
        print("Sent a private message")
      else:
        print("You haven't executed startprivate <" + user + ">", flush=True)

      continue
      

    clientSocket.send(command.encode())

    if command == "logout":
      for session in currentPrivateSessions:
        currentPrivateSessions[session].close()
      privateAcceptSocket.close()
      CONNECTED = False



def recv_handler():
  global clientSocket
  global CONNECTED
  global privateConnectSocket
  while (1):
    prompt = clientSocket.recv(2048)
    prompt = prompt.decode()

    print("Received a msg")

    if prompt == "WhatsApp " + username + " logout":
      print("You have been automatically logged out", flush=True)
      CONNECTED = False
      break

    elif prompt.startswith("WhatsApp " + username + " startprivate"):
      # you are the private initializer
      print(prompt)
      prompt = prompt.split(' ')
      
      ip = prompt[-3]
      port = int(prompt[-2])
      target = prompt[-1]

      privateConnectSocket = socket(AF_INET, SOCK_STREAM)
      # connect to the private acceptor's private socket.
      print("private initializer is trying to connect to ip =", str(ip), "port =", str(port))
      privateConnectSocket.connect((ip, port))

      # send to privateConnectSocket = send to the private acceptor
      currentPrivateConnection[target] = privateConnectSocket

      privateInitializerThread = Thread(name="privateInitializerHandler", target=private_initializer_handler, args=[target])
      privateInitializerThread.daemon = True
      privateInitializerThread.start()

      continue

    elif prompt.startswith("WhatsApp " + username + " allowprivate"):
      # you are the private acceptor
      print("Allowing private")
      prompt = prompt.split(' ')

      ip = prompt[-3]
      port = int(prompt[-2])
      target = prompt[-1]
      
      privateAcceptorThread = Thread(name="privateAcceptorHandler", target=private_acceptor_handler, args=[target])
      privateAcceptorThread.daemon = True
      privateAcceptorThread.start()


      print("Accepted connection")
      continue

    elif prompt.startswith("WhatsApp stopprivate with"):
      print("Stopping private")
      prompt = prompt.split(' ')
      currentPrivateConnection[prompt[-1]].close()
      del currentPrivateConnection[prompt[-1]]
      continue

    print(prompt, flush=True, end="")

def private_acceptor_handler(target):

  connectionSocket, connectionAddr = privateAcceptSocket.accept()
  print("private acceptor receive connection from " + str(connectionAddr))
  # acceptor can use this socket to send to the private initializer.
  currentPrivateConnection[target] = connectionSocket
  
  print("started private_handler")

  while (1):
    msg = connectionSocket.recv(2048)
    print("Received a msg")

    print(msg.decode())

def private_initializer_handler(name):
  print(currentPrivateConnection)
  privateAcceptorSocket = currentPrivateConnection[name]
  while (1):
    msg = privateAcceptorSocket.recv(2048)

    print(msg.decode())
  

login_process()

recvThread = Thread(name="recvHandler", target=recv_handler)
recvThread.daemon = True
recvThread.start()

command_process()

# clientSocket.close()
# Close the socket
