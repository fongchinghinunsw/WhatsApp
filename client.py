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

# {user: serverSocket}
privateSocket = {}

p2pList = {}

username = ""
CONNECTED = True

def retrieve_components(command):
  """ split the command and return a list of arguments """
  command = command.strip(' ')
  command = command.split(' ')
  first_component = command.pop(0)

  if first_component == "message":
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
      LOGIN = False

  print("Logged in")

def command_process():
  global CONNECTED
  global privateConnectSocket

  while CONNECTED:
    command = input()

    if command.startswith("private"):
      user, message = retrieve_components(command)


      if user in p2pList:
        print("ready to send a private msg")
        p2pList[user].send(message.encode())
        print("Sent a private message")
      else:
        print("You haven't executed startprivate <" + user + ">", flush=True)

      continue
      

    clientSocket.send(command.encode())

    if command == "logout":
      CONNECTED = False



def main_handler():

  login_process()

  recvThread = Thread(name="recvHandler", target=recv_handler)
  recvThread.daemon = True
  recvThread.start()


  command_process()


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
      prompt = prompt.split(' ')
      
      ip = prompt[-3].strip(",'(")
      port = int(prompt[-2].rstrip(')'))
      target = prompt[-1]

      time.sleep(0.5)
      privateConnectSocket = socket(AF_INET, SOCK_STREAM)
      privateConnectSocket.connect((ip, 4689))

      p2pList[target] = privateConnectSocket


      continue

    elif prompt.startswith("WhatsApp " + username + " allowprivate"):
      print("Allowing private")
      prompt = prompt.split(' ')

      ip = prompt[-3].strip(",'(")
      port = int(prompt[-2].rstrip(')'))
      target = prompt[-1]

      
      privateThread = Thread(name="privateHandler", target=private_handler, args=[target])
      privateThread.daemon = True
      privateThread.start()


      print("Accepted connection")
      continue
      

    print(prompt, flush=True, end="")

def private_handler(target):
  privateAcceptSocket = socket(AF_INET, SOCK_STREAM)
  privateAcceptSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
  # binds the port number to the server's socket, the IP address of the server is localhost
  privateAcceptSocket.bind(('localhost', 4689))
  privateAcceptSocket.listen(1)

  connectionSocket, connectionAddr = privateAcceptSocket.accept()
  p2pList[target] = connectionSocket
  
  print("Hi")

  while (1):
    msg = connectionSocket.recv(2048)

    print(msg.decode())

  

mainThread = Thread(name="mainHandler", target=main_handler)
mainThread.daemon = True
mainThread.start()
# won't close until a daemon thread has completed its work


# clientSocket.close()
# Close the socket

# main thread
while CONNECTED:
  time.sleep(0.1)
