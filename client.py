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

CONNECTED = True

def login_process():
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

    elif prompt == "User doesn't exist\n":
      continue

    elif prompt == "Invalid Password. Please try again.\n":
      continue

    elif prompt == "Your account has been blocked. Please try again later.\n":
      continue

    elif prompt == "Welcome back !\n":
      LOGIN = False

  print("Logged in")

def command_process():
  global CONNECTED

  while CONNECTED:
    command = input()
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
  global CONNECTED
  while (1):
    prompt = clientSocket.recv(2048)
    prompt = prompt.decode()

    print(prompt, flush=True, end="")
    if prompt == "WhatsApp: you have been logged out\n":
      print("Break")
      CONNECTED = False
      break


mainThread = Thread(name="mainHandler", target=main_handler)
mainThread.daemon = True
mainThread.start()
# won't close until a daemon thread has completed its work


# clientSocket.close()
# Close the socket

# main thread
while CONNECTED:
  time.sleep(0.1)
