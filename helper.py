def get_username_to_password_mapping():
  """ read lines from 'credentials.txt' to form a dictionary
      with username to password mapping
  """
  username2password = {}
  with open('credentials.txt', 'r') as credentials:
    for line in credentials:
      name, pwd = line.rstrip('\n').split(' ')
      username2password[name] = pwd

  return username2password


def retrieve_components(command):
  """ split the command and return its arguments """
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


def decorate_chat_msg(username, message):
  """ Decorate the message sent by a user by adding the sender's name
      and a colon at the front
  """
  return username + ": " + message


def is_existing_user(username, user_dict):
  """ check if the user exists in the dictionary """
  return username in user_dict


# a dictionary stores username:password key-value pairs.
username2password = get_username_to_password_mapping()
