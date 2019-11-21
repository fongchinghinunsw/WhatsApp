# Python 3
# Usage: python3 server.py server_port block_duration timeout
# coding: utf-8

import sys
from socket import *
from datetime import datetime
from threading import Timer, Condition, Thread
from helper import retrieve_components, decorate_chat_msg, is_existing_user, username2password


server_port = int(sys.argv[1])
block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])


class User:
  """ contains all the information about the online user """
  def __init__(self, socket, address):
    self.username = None
    self.socket = socket
    self.address = address
    self.private_accepting_port = None

  def __repr__(self):
    return "User({}, {})".format(self.socket, self.address)

  def get_username(self):
    return self.username

  def get_socket(self):
    return self.socket

  def get_address(self):
    return self.address

  def get_private_accepting_port(self):
    return self.private_accepting_port

  def set_username(self, username):
    self.username = username

  def set_private_accepting_port(self, port):
    self.private_accepting_port = port

  def send_prompt(self, prompt):
    self.socket.send(prompt.encode())

  def get_input(self):
    message = self.socket.recv(2048)
    return message.decode()


def create_thread(user_object):
  """ create a separate thread for handling the interaction between the
      server and each client
  """
  thread = Thread(name="MainHandler", target=main_handler, args=[user_object])
  thread.daemon = True
  thread.start()



def is_online_user(username):
  """ return True if 'username' is online """
  return username in [user.get_username() for user in online_users]


def has_blocked(userA, userB):
  """ return True if userA has blocked userB """
  if userB in block_users:
    print(block_users)
    print(block_users[userB])
    if userA in block_users[userB]:
      return True
    else:
      return False
  else:
    return False


def has_existing_connection(userA, userB):
  """ return True if there's a private messaging session between userA and userB """
  if userA in activeP2PSessions:
    if userB in activeP2PSessions[userA]:
      return True

  if userB in activeP2PSessions:
    if userA in activeP2PSessions[userB]:
      return True

  return False
  

def login_unblock(username):
  """ unblock the user by removing the user from the blocked_list
      and remove its # of unsuccessful login attempts history
  """
  print("unblock")
  del unSuccessfulAttempt[username]
  del blocked_login[username]


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
    for online_user in online_users:
      # need to check if "online_user" has blocked "user"
      if has_blocked(online_user.get_username(), user.get_username()):
        get_blocked = True
        continue

      if user.get_username() == online_user.get_username():
        continue

      online_user.send_prompt(message)

    if get_blocked:
      user.send_prompt("Your message could not be delivered to some recipients")

  elif typeOfMsg == 1:
    # just send to all online users if it's a login/logout broadcast
    for online_user in online_users:
      # when A login/logout do not inform B if A blocked B and
      # do not inform A itself
      if has_blocked(user.get_username(), online_user.get_username())\
         or user.get_username() == online_user.get_username():
        continue

      online_user.send_prompt(message)


def logout(user):
  """ logout the user from the server, following operations are done
      (1) send broadcast to notify users that user has logged out
      (2) remove the user from the online users list
      (3) record the user's last online time
      (4) send message to the client application to confirm the log out
      (5) remove the user's record from all active P2P sessions
      (6) delete the user object
  """
  print("Executing logout")
  print(activeP2PSessions)
  send_broadcast(user, user.get_username() + " has logged out\n", 1)
  for online_user in online_users:
    if online_user.get_username() == user.get_username():
      online_users.remove(online_user)
      lastLoggedIn[online_user.get_username()] = datetime.now()

      user.send_prompt("WhatsApp " + user.get_username() + " logout")
      break

  if user.get_username() in activeP2PSessions:
    del activeP2PSessions[user.get_username()]
    for activeuser in activeP2PSessions:
      if user.get_username() in activeP2PSessions[activeuser]:
        activeP2PSessions[activeuser].remove(user.get_username())

  print(activeP2PSessions)
  del user


def login_process(user):
  """ handles all interactions between the server and the client while
      the client is trying to login
  """

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
          # delete user's unsuccessful login record if the password is
          # correct
          if username in unSuccessfulAttempt:
            del unSuccessfulAttempt[username]

          # set the name of the user and add it to the online_users list
          user.set_username(username)
          online_users.append(user) 

          send_broadcast(user, user.get_username() + " has logged in", 1)
          break

        else:
          # user inputs wrong password
          if username in unSuccessfulAttempt:
            unSuccessfulAttempt[username] += 1

            if unSuccessfulAttempt[username] >= 3:

              if username not in blocked_login:
                blocked_login[username] = Timer(block_duration, login_unblock, [username])
                blocked_login[username].start()
            
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

    # user logs in successfully
    if password == username2password[username]:
      user.send_prompt("Welcome back !\n")

      # sends out all the cached offline messages to the client
      if user.get_username() in offline_msg_box:
        print(offline_msg_box[user.get_username()])
        for msg in offline_msg_box[user.get_username()]:
          user.send_prompt(msg)

        del offline_msg_box[user.get_username()]

      print("waiting for user's info to come back")
      # try to get back the port number used by the client for accepting
      # private connections
      private = user.get_input()
      private = private.split(' ')
      user.set_private_accepting_port(private[1])
      print(user.get_username() + " private acceptor socket is " + str(private[0]) + " " + str(private[1]))
      break


def main_process(user):

  while (1):
    t = Timer(timeout, logout, [user])
    t.start()

    command = user.get_input()
    print("command =", command)
    if command == "logout":

      logout(user)
      t.cancel()

      break

    elif command.startswith("message "):
      userComponent, message = retrieve_components(command)
      message = decorate_chat_msg(user.get_username(), message)

      if userComponent == user.get_username():
        user.send_prompt("Can't send message to yourself")
        t.cancel()
        continue

      if is_existing_user(userComponent, username2password):
        for online_user in online_users:
          if online_user.get_username() == userComponent:
            if user.get_username() in block_users and online_user.get_username() in block_users[user.get_username()]:
              user.send_prompt("Your message could not be delivered as the recipient has blocked you")
            else:
              online_user.send_prompt(message)
            break

        # if the user is offline, add the message to the offline mail box
        else:
          message = message + '\n'
          if userComponent in offline_msg_box:
            offline_msg_box[userComponent].append(message)
          else:
            offline_msg_box[userComponent] = [message]

      else:
        user.send_prompt("Invalid user")
      
    elif command.startswith("broadcast "):
      message = retrieve_components(command)
      message = decorate_chat_msg(user.get_username(), message)

      send_broadcast(user, message, 0)

    elif command == "whoelse":
      prompt = "Online Users: "
      for online_user in online_users:
        if (online_user.get_username() != user.get_username()):
          prompt = prompt + online_user.get_username() + ", "

      prompt = prompt.rstrip(", ") 
      prompt += '\n'
      user.send_prompt(prompt)
       
    elif command.startswith("whoelsesince "):

      time = int(retrieve_components(command))
      # stores online users' name into a set
      result = {online_user.get_username() for online_user in online_users}

      for i in lastLoggedIn:
        lastTime = lastLoggedIn[i]
        now = datetime.now()
        timeDelta = now - lastTime

        if timeDelta.seconds < time:
          result.add(i)

      if user.get_username() in result:
        result.remove(user.get_username())

      prompt = "Users: "
      for i in result:
        prompt = prompt + i + ", "

      prompt = prompt.rstrip(", ") 
      prompt += '\n'
      user.send_prompt(prompt)
       
    elif command.startswith("block "):
      print(block_users)
      userComponent = retrieve_components(command)

      if userComponent not in username2password:
        print("User is invalid")
        user.send_prompt("User is invalid")
        t.cancel()
        continue

      elif userComponent == user.get_username():
        print("User is itself")
        user.send_prompt("Can't block yourself")
        t.cancel()
        continue

      user.send_prompt("You have blocked " + userComponent)

      if userComponent in block_users:
        block_users[userComponent].add(user.get_username())

      else:
        block_users[userComponent] = {user.get_username()}


    elif command.startswith("unblock "):
      print(block_users)
      userComponent = retrieve_components(command)

      if userComponent not in username2password:
        user.send_prompt("Username is invalid")

      elif userComponent == user.get_username():
        user.send_prompt("Unblocking yourself is invalid")

      elif userComponent in block_users and user.get_username() in block_users[userComponent]:
        block_users[userComponent].remove(user.get_username())

      else:
        user.send_prompt("User " + userComponent + " is not in your block list")

    elif command.startswith("startprivate "):
      userComponent = retrieve_components(command)
      print(userComponent)

      if not is_existing_user(userComponent, username2password):
        user.send_prompt("User doesn't exist")
        t.cancel()
        continue

      elif has_existing_connection(user.get_username(), userComponent):
        user.send_prompt("Can't establish private connection as current private connection with this user exists")
        t.cancel()
        continue

      if userComponent != user.get_username():

        for online_user in online_users:
          if online_user.get_username() == userComponent:
            if has_blocked(userComponent, user.get_username()):
              user.send_prompt("Private message can't be established as you have been blocked")
            else:
              if user.get_username() not in activeP2PSessions:
                activeP2PSessions[user.get_username()] = [online_user.get_username()]
              else:
                activeP2PSessions[user.get_username()].append(online_user.get_username())

              online_user.send_prompt("WhatsApp " + online_user.get_username() + " allowprivate " + user.get_username())

              user.send_prompt("WhatsApp " + user.get_username() + " startprivate " + str(online_user.get_address()) + " " + str(online_user.get_private_accepting_port()) + " " + online_user.get_username())


              print("startprivate is valid, messages should be sent")
              
            break

        else:
          user.send_prompt(userComponent + " is offline")

      else:
        user.send_prompt("Can't start private message with yourself")

    elif command.startswith("stopprivate "):

      userComponent = retrieve_components(command)

      found = False

      # check if there exists a private session between two users
      if user.get_username() in activeP2PSessions:
        if userComponent in activeP2PSessions[user.get_username()]:
          activeP2PSessions[user.get_username()].remove(userComponent)
          found = True

      elif userComponent in activeP2PSessions:
        if user.get_username() in activeP2PSessions[userComponent]:
          activeP2PSessions[userComponent].remove(user.get_username())
          found = True

      # asks two users to discontinue their private connection if there's one between them
      if found:
        for online_user in online_users:
          if online_user.get_username() == user.get_username():
            online_user.send_prompt("WhatsApp stopprivate with " + userComponent)
          elif online_user.get_username() == userComponent:
            online_user.send_prompt("WhatsApp stopprivate with " + user.get_username())
      else:
        fail_message = "You don't have an active p2p session with " + userComponent
        user.send_prompt(fail_message.encode())

    elif command == "WhatsApp sent private command":
      t.cancel()
      continue

    else:
      if user in online_users:
        user.send_prompt("Invalid command")
      else:
        # user has been logged out by the server automatically after timeout
        t.cancel()
        break
    t.cancel()


def main_handler(user_object):
  """ all interactions between the server and the client, consists
      of login process and main process
      this function is called inside create_thread()
  """
  global t_lock

  login_process(user_object)
  
  lastLoggedIn[user_object.get_username()] = datetime.now()

  main_process(user_object)


t_lock = Condition()

# the number of unsuccessful attempts for each user
# stored in the format {user1: 3, user2: 2, ...}
unSuccessfulAttempt = {}

# users that are blocked for a period
blocked_login = {}

# user to user blocking
# here user1 is blocked by user2, user3, ...
# {user1: {user2, user3, ...}}
block_users = {}

# stores a list of online users.
online_users = []

# stores message in the format {user1:[msg1, msg2, ...], user2: [msg1, msg2, ...]}
offline_msg_box = {}

# saves the last online time for all users.
lastLoggedIn = {}

# saves active p2p messaging sessions user pairs
# if A initiates a p2p session with B, then {A: [B], ...}
activeP2PSessions = {}

# server's socket allowing clients to connect with
server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_socket.bind(('localhost', server_port))

server_socket.listen(1);

while 1:
  # creates a connection socket dedicated to this particular client
  connectionSocket, clientAddress = server_socket.accept()
  print("Server receive connection from", str(clientAddress))
  user = User(connectionSocket, clientAddress[0])
  # create a separate thread for the client
  create_thread(user)

server_socket.close()
  
