# Sample code for Multi-Threaded Server
# Python 3
# Usage: python3 UDPserver3.py
# coding: utf-8
from socket import *
from threading import Timer, Condition, Thread
import time
import sys
from datetime import datetime

#Server will run on this port
serverPort = int(sys.argv[1])
block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])

# This is a lock, allows one or more threads to wait until they are notified by another thread.
t_lock = Condition()
# will store clients info in this list
clients = []

# the number of unsuccessful attempts for each user
unSuccessfulAttempt = {}

# users that are blocked for a period
blockedList = {}

# user to user blocking
# here user1 is blocked by user2, user3, ...
# {user1: {user2, user3, ...}}
blockUsers = {}

onlineUsers = []

# stores message in the format {user1:[msg1, msg2, ...], user2: [msg1, msg2, ...]}
offlineMessageBox = {}

# saves the last online time for all users.
lastLoggedIn = {}

class User:
  def __init__(self, socket, address):
    self.username = None
    self.socket = socket
    self.address = address
    self.thread = None
    self.loginTime = None

  def __repr__(self):
    return self.username

  def send_prompt(self, prompt):
    self.socket.send(prompt.encode())

  def get_input(self):
    message = self.socket.recv(2048)
    return message.decode()

  def get_username(self):
    return self.username

  def get_socket(self):
    return self.socket

  def get_address(self):
    return self.address

  def get_thread(self):
    return self.thread

  def get_loginTime(self):
    return self.loginTime

  def set_username(self, username):
    self.username = username

  def set_thread(self, thread):
    self.thread = thread




def create_username_password_mapping():
  username2password = {}
  with open('credentials.txt', 'r') as credentials:
    for line in credentials:
      name, pwd = line.rstrip('\n').split(' ')
      username2password[name] = pwd
  return username2password

def create_thread(user):
  thread = Thread(name="WelcomingHandler", target=welcoming_handler, args=[user])
  thread.daemon = True
  thread.start()
  return thread

def decorate_message(username, message):
  return username + ": " + message + "\n"


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

def is_existing_user(username, mapping):
  return username in mapping


def is_online_user(username):
  return username in [user.get_username() for user in onlineUsers]

def has_blocked(userA, userB):
  if userB in blockUsers:
    if userA in blockUsers[userB]:
      return True
    else:
      return False
  else:
    return False

def send_broadcast(user, message, typeOfMsg):
  """send broadcast to all online users that didn't block the sender

  Parameters:
  user (User): the user object
  message (String): the message
  typeOfMsg (int): 0 impiles the message is a normal broadcast,
  1 impiles the message is a login/logout broadcast

  """
  if typeOfMsg == 0:
    get_blocked = False
    for onlineUser in onlineUsers:
      # if "onlineUser" has blocked "user"
      if has_blocked(onlineUser.get_username(), user.get_username()):
        get_blocked = True

      if user.get_username() == onlineUser.get_username():
        continue

      onlineUser.send_prompt(message)

    if get_blocked:
      user.send_prompt("Your message could not be delivered to some recipients\n")

  elif typeOfMsg == 1:
    for onlineUser in onlineUsers:
      if has_blocked(user.get_username(), onlineUser.get_username()):
        continue

      onlineUser.send_prompt(message)



def logout(user):
  print("Executing logout")
  for onlineUser in onlineUsers:
    if onlineUser.get_username() == user.get_username():
      onlineUsers.remove(onlineUser)
      lastLoggedIn[onlineUser.get_username()] = datetime.now()

      user.send_prompt("WhatsApp: you have been logged out\n")
    else:
      onlineUser.send_prompt(user.get_username() + " has logged out\n")

  

username2password = create_username_password_mapping()

def login_process(user):

  print("WhatsApp version 3.2.4")

  while (1):

    user.send_prompt("Username: ")
    username = user.get_input()
    print("username is", username)

    if is_existing_user(username, username2password):
      for _ in range(3):

        user.send_prompt("Password: ")
        print("Prompted for password")
        password = user.get_input()
        print("password is", password)

        if is_online_user(username):
          user.send_prompt("This account has logged in on another device.\n")
          password = ""
          break
        elif username2password[username] == password:
          # delete user's unsuccessful login record
          if username in unSuccessfulAttempt:
            del unSuccessfulAttempt[username]

          user.set_username(username)
          onlineUsers.append(user) 

          send_broadcast(user, user.get_username() + " has logged in\n", 1)
          break

        else:
          # user inputs wrong password
          if username in unSuccessfulAttempt:
            unSuccessfulAttempt[username] += 1
            if unSuccessfulAttempt[username] >= 3:


              if username not in blockedList:
                blockedList[username] = Timer(block_duration, unblock, [username])
                blockedList[username].start()
            
              user.send_prompt("Your account has been blocked. Please try again later.\n")
              print("sending blocked prompt")
              break
          else:
            unSuccessfulAttempt[username] = 1

          user.send_prompt("Invalid Password. Please try again.\n")
          print("sending retry prompt")
        

    else:
      user.send_prompt("User doesn't exist\n")
      print("sending no user prompt")
      continue

    if password == username2password[username]:
      user.send_prompt("Welcome back !\n")
      print("sending welcoming prompt")

      if user.get_username() in offlineMessageBox:
        print(offlineMessageBox[user.get_username()])
        if user.get_username() in offlineMessageBox:
          for msg in offlineMessageBox[user.get_username()]:
            user.send_prompt(msg)
      break


def main_process(user):
  while (1):
    t = Timer(timeout, logout, [user])
    t.start()
    user.send_prompt("> ")
    command = user.get_input()
    print("command =", command)
    if command == "logout":

      logout(user)
      t.cancel()

      break


    elif command.startswith("message"):
      userComponent, message = retrieve_components(command)
      message = decorate_message(user.get_username(), message)

      if is_existing_user(userComponent, username2password):
        for onlineUser in onlineUsers:
          if onlineUser.get_username() == userComponent:
            if user.get_username() in blockUsers and onlineUser.get_username() in blockUsers[user.get_username()]:
              user.send_prompt("Your message could not be delivered as the recipient has blocked you\n")
            else:
              onlineUser.send_prompt(message)
            break
        # if no break
        else:
          if userComponent in offlineMessageBox:
            offlineMessageBox[userComponent].append(message)
          else:
            offlineMessageBox[userComponent] = [message]

        
      else:
        user.send_prompt("Invalid user")
      
    elif command.startswith("broadcast"):
      message = retrieve_components(command)
      message = decorate_message(user.get_username(), message)

      send_broadcast(user, message, 0)

    elif command == "whoelse":
      prompt = "Online Users: "
      for onlineUser in onlineUsers:
        if (onlineUser.get_username() != user.get_username()):
          prompt = prompt + onlineUser.get_username() + ", "

      prompt = prompt.rstrip(", ") 
      prompt += '\n'
      user.send_prompt(prompt)
       
    elif command.startswith("whoelsesince"):
      time = int(retrieve_components(command))


      result = {onlineUser.get_username() for onlineUser in onlineUsers}

      for i in lastLoggedIn:
        lastTime = lastLoggedIn[i]
        now = datetime.now()
        timeDelta = now - lastTime

        if timeDelta.seconds < time:
          result.add(i)

      prompt = "Users: "
      for i in result:
        prompt = prompt + i + ", "

      prompt = prompt.rstrip(", ") 
      prompt += '\n'
      user.send_prompt(prompt)
       
      

    elif command.startswith("block"):
      userComponent = retrieve_components(command)

      if userComponent not in username2password:
        print("User is invalid")
        user.send_prompt("User is invalid\n")
        continue
      elif userComponent == user.get_username():
        print("User is itself")
        user.send_prompt("Can't block yourself")
        continue

      if userComponent in blockUsers:
        blockUsers[userComponent] = blockUsers[user.get_username()].add(user.get_username())

      else:
        blockUsers[userComponent] = {user.get_username()}


    elif command.startswith("unblock"):
      userComponent = retrieve_components(command)

      if userComponent not in username2password:
        user.send_prompt("Username is invalid\n")

      elif userComponent in blockUsers and user.get_username() in blockUsers[userComponent]:
        blockUsers[userComponent].remove(user.get_username())

      else:
        user.send_prompt("User " + userComponent + " is not in your block list\n")

    elif command.startswith("startprivate"):
      userComponent = retrieve_components(command)

      if not is_existing_user(userComponent):
        user.send_prompt("User doesn't exist\n")

      for onlineUser in onlineUsers:
        if onlineUser.get_username() == userComponent:
          if has_blocked(userComponent, user.get_username()):
            user.send_prompt("Private message can't be established as you have been blocked\n")
            break
          else:
            pass
      else:
        user.send_prompt(userComponent + " is offline\n")

    else:
      if user in onlineUsers:
        user.send_prompt("Invalid command\n")
      else:
        # user has been logged out by the server automatically after timeout
        break
    t.cancel()

  


def welcoming_handler(user):
  global t_lock
  global welcomingSocket

  login_process(user)
  
  lastLoggedIn[user.get_username()] = datetime.now()

  main_process(user)

def unblock(*args):
  print("unblock")
  del unSuccessfulAttempt[args[0]]
  del blockedList[args[0]]

# we will use two sockets, one for sending and one for receiving
# socket.socket creates a new socket using the given address family, socket type
welcomingSocket = socket(AF_INET, SOCK_STREAM)
welcomingSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
# binds the port number to the server's socket, the IP address of the server is localhost
welcomingSocket.bind(('localhost', serverPort))

welcomingSocket.listen(1);





# threading.Thread's name is the thread name, target is a callable object which can be called by run()
#recv_thread = threading.Thread(name="RecvHandler", target=recv_handler)
# Daemon threads will be killed once the main program exits
#recv_thread.daemon = True
# starts the thread's activity, arrange a separate thread to call the run() method
#recv_thread.start()

#send_thread=threading.Thread(name="SendHandler",target=send_handler)
#send_thread.daemon = True
#send_thread.start()

while 1:
  # creates a connection socket dedicated to this particular client
  connectionSocket, clientAddress = welcomingSocket.accept()
  user = User(connectionSocket, clientAddress)
  user.thread = create_thread(user)
  
