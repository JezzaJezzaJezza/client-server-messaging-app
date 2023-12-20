import socket
import sys
import re
import threading
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

currentMode = "bcast" #Presetting parameters
currentRecipient = None
duplicateUsername = False

def startClient():
    username, hostname, port   = str(sys.argv[1]), str(sys.argv[2]), int(sys.argv[3])

    if not os.path.exists(f"./downloads_{username}"): #Checks if a user download folder exists, and creates one if it doesn't
        os.makedirs(f"./downloads_{username}")
        print("Download folder created.")

    if re.search(r'/', username): #Most of my protocols rely on "/", so having a "/" in the username would confuse a lot of the functions
        print("Username cannot contain '/'")
        exit()
    
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((hostname, port))
    clientSocket.send(username.encode())
    print("You can access the help menu by typing 'cmd.help'")

    rewriter = PromptSession()
    
    threading.Thread(target=recvMsg, args=(clientSocket,), daemon=True).start()
    try: #Allows for console to keep the Input: prompt always at the bottom, to give a "scrolling chat" effect
        with patch_stdout():
            while True:
                if duplicateUsername:
                    raise Exception("Username is already taken. Please choose another... Exiting")
                msg = rewriter.prompt("Input: ")
                if not sendMsg(clientSocket, msg):
                    break

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Closing connection.")
        msg = "//cmd.exit" #Keyboard interupt should not be an "unexpected connection"
        clientSocket.send(msg.encode())
    finally:
        msg = "//cmd.exit"
        clientSocket.send(msg.encode())
        clientSocket.close()
        exit()

def recvMsg(clientSocket):
    global duplicateUsername

    while True:
        try:
            header = clientSocket.recv(1024).decode()
            if not header:
                break
            

            if header.startswith("file/"): #header tells client what they should be expecting to receive. If no formatted header is supplies, then the header is the msg
                recvFile = header.split("/")[1]
                print(f"Downloading {recvFile}...")
                fileReceived(clientSocket, recvFile)
            elif header.startswith("duplicate/"):
                print("Username already exists. Choose another.")
                duplicateUsername = True
                break
            else:
                print(header)
        except Exception:
            break

def fileReceived(clientSocket, recvFile):
    try:
        with open(f"./downloads_Jezza/{recvFile}", "wb") as file: #creates the file, wait for all the data to arrive, and the write it to the file
            while True:
                data = clientSocket.recv(1024)
                if data == b"EOF":
                    break
                file.write(data)
        print("File has been received")
    except Exception as e:
        print(e)

def sendMsg(clientSocket, msg):
    global currentMode, currentRecipient

    #Check for commands
    if msg == "cmd.exit": #Exit command
        msg = "/"+ "/" + msg
        clientSocket.send(msg.encode())
        return False
    elif msg == "cmd.bcast": #Command to swap to broadcasting mode
        currentMode = "bcast"
        print("You are now broadcasting")
        return True
    elif msg == "cmd.ucast": #Command to swap to unicasting mode
        currentMode = "ucast"
        currentRecipient = None
        print("You are now unicasting (direct messaging) - in your next message, use the command msg/ followed directly by the username you would like to send the message to and then one more /. After typing the command, simply type your message. You only need to do this once, for your first message, the rest will default to the same user. To change user, retype the cmd.ucast command.")
        return True
    elif msg == "cmd.help": #Command will display all possible other commands, and how to use them
        print("HELP MENU:\ncmd.exit --> Exit the application\ncmd.bcast --> Toggle broadcast mode (will transmit your message to everyone)\ncmd.ucast --> Toggle unicast mode (will transmit to a specified person). At the start of your message, you can specify who to send it to by typing msg/desired_username/. After that you do not need to retype it for each message. Messages will default to your desired user, until you retype msg/different_user/ or toggle out of unicast mode.()\ncmd.download --> Will show you a numbered list of possible files to download. Select one by writing the number next to the download and hitting enter\n")
    elif msg == "cmd.download": #Command will display all downloadable files. It also sets the currentMode to download, meaning the messages sent, will be in reference to specific files.
        currentMode = "download"
        print("Please choose a file to download by typing its number.")
        lsRequest = "d/list/files"
        clientSocket.send(lsRequest.encode())
        return True

    #Currently if the user wants to change who the recipient is in unicast mode, they have to recall the unicast command and retype it
    #Sounds inherently bad, but if I did it so that it just checked if the message contained "/", then it might accidently give an error if the user actually
    #meant to use the "/" character while sending it to their recipient.

    #Dealing with messages from each case of mode
    if currentMode == "bcast": #Check for current mode and packages the messages accordingly
        msg = "b/" + "all/" + msg
    elif currentMode == "ucast":
        if currentRecipient == None and msg.count("/") == 0: #Check if the user has made a mistake and hasnt defined the recipient username
            print("Username not defined. Please format the message properly.")
            return True
        elif currentRecipient == None: #Check if the user still needs to input a recipient username, or if it can default to previous one
            currentRecipient, msg = msg.split("/", 2) #extracts the recipient name from the message
        msg = "u/" + currentRecipient + "/" + msg #formats the message
    elif currentMode == "download":
        print(msg)
        msg = "d/server/" + msg

    clientSocket.send(msg.encode()) #sends
    return True

if __name__ == "__main__":
    startClient()
