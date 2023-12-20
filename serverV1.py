import socket
import sys
import threading
import os
import json
import time
import logging

clients = {}

def clientHandle(connectionSocket):

    try:

        username = connectionSocket.recv(1024).decode() #receive username

        if username in clients:
            rejectionMsg = "duplicate/Username already exists. Choose a different username."
            #print(f"Connection rejected - Duplicate username: {username}")
            logging.warning(f"Duplicate username detected: {username}")
            connectionSocket.send(rejectionMsg.encode())
            connectionSocket.close()
            return

        clients[username] = connectionSocket #store username in clients list
        bcast(f"{username} has connected", username) #Inform that a user of "username" has joined
        logging.info(f"Connection authenticated with {username}")
        confirmationMsg = "Connection established."
        connectionSocket.send(confirmationMsg.encode()) #Send confirmation msg

        while True:

                msg = connectionSocket.recv(1024).decode()
                

                if '/' in msg:
                    mode, recipient, msg = msg.split("/", 2)
                    if msg == "cmd.exit": #Disconnects the user, if the command is received
                        #print(f"{username} has disconnected")
                        logging.info(f"{username} disconnected")
                        bcast(f"{username} has disconnected", username)
                        connectionSocket.close()
                        clients.pop(username, None)
                        break


                    #print(f"Recieved: {username} said {msg} in mode {mode} to {recipient}")
                    logging.info(f"Recieved: {username} said {msg} in mode {mode} to {recipient}")
                    response = "Message recieved" #Confirmation msg for client
                    connectionSocket.send(response.encode())
                    
                    if mode == "b": #Mode defines what the user wants the message to be for. The mode can be "b" for broadcast, "u" for unicast and "d" for download
                        msg = username + ": " + msg #Here the msg is rewritten, so that the other clients can see which user said what
                        bcast(msg, username)
                        logging.info(f"Broadcasted: {msg}")
                    elif mode == "u":
                        msg = username + ": " + msg
                        if recipient not in clients: #Does a quick check to see if the recepient of the the msg actually exists before sending
                            logging.error(f"Unicast - No recipient found.")
                            exceptionResponse = "error/Username not found"
                            connectionSocket.send(exceptionResponse.encode())
                        else:
                            ucast(msg, recipient)
                            logging.info(f"Unicasted: {msg} to {recipient}")
                    elif mode == "d":
                        if recipient == "list": #Checks if the message was to actually download the files or to have them listed
                            #print(f"Sending file list to {username}")
                            logging.info(f"Sending file list to {username}")
                            lsFiles = listFiles() #The listFiles function returns a list of all downloadable files from the downloads folder. It also enumerates each filename, so that the user can easily request a specific file by just typing the corresponding number
                            lsFiles = json.dumps(lsFiles) #Serialises the list so that it can be sent
                            sendData = lsFiles
                            connectionSocket.send(sendData.encode())
                        elif recipient == "server": #Indicates that the client in fact requested for a file to be downloaded from the server
                            try:
                                #print(f"Fetching file {msg} for {username}")
                                logging.info(f"Fetching file {msg} for {username}")
                                allFiles = os.listdir("./downloads") #Returns a normal list of the contents of the folder "downloads"
                                sendFile = allFiles[int(msg)-1] #Msg is expected to be some integer, which corresponds to the list of files sent earlier. From that, the file that the user wants can be worked out by -1, which will give us the index of the file

                                header = f"file/{sendFile}" #Send a header to let the client know that they are about to receive a file
                                connectionSocket.send(header.encode())

                                time.sleep(0.2) #Delay is added just to make sure that it doesnt start sending while the client hasn't switched over to "receive file" mode

                                with open(f"./downloads/{sendFile}", "rb") as file: #sends the file in chunks of 1024 bytes
                                    content = file.read(1024)
                                    while content:
                                        connectionSocket.send(content)
                                        content = file.read(1024)

                                time.sleep(0.2)
                                connectionSocket.send(b"EOF") #Send EOF
                                #print("File was sent successfully")
                                logging.info("File was sent successfully")

                            except:
                                #print(f"File could not be found for {username}") 
                                logging.error(f"File could not be found for {username}") #The user had a missinput
                                downloadError = "File input not recognised."
                                connectionSocket.send(downloadError.encode())
                    
                else: #Incase the user disconnects suddenly, server will let others know that the user did not disconnect on purpose
                    connectionSocket.close()
                    #print(f"{username} has disconnect unexpectedly") 
                    logging.warning(f"{username} has disconnect unexpectedly")#This is displayed if the user didn't disconnect using the cmd.exit command or ctrl + C
                    bcast(f"{username} has disconnected unexpectedly", username)
                    clients.pop(username, None) 
                    break
    except ConnectionResetError:
        #print(f"{username} has disconnected")
        logging.info(f"{username} has disconnected")
        bcast(f"{username} has disconnected", username)
        connectionSocket.close()
        clients.pop(username, None)
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Error: {e} - generated by {username}")
        connectionSocket.close()
        if username in clients:
            clients.pop(username, None)

def listFiles():
    fileList = []
    tmpAllFiles = os.listdir("./downloads")
    for i, file in enumerate(tmpAllFiles, start=1): #enumerates the file list
        fileList.append(f"{i}.{file}")
    return fileList

def bcast(msg, sUsername):
    for username, client in clients.items(): #Sends a msg to everyone apart from the user who sent the msg in the first place (sUsername)
        if username != sUsername:
            client.send(msg.encode())

def ucast(msg, rUsername):
    recipientSocket = clients.get(rUsername) #Send msg to specified recipient (rUsername)
    if recipientSocket:
        recipientSocket.send(msg.encode())
    else:
        print(f"User {rUsername} not found.")

def startServer():
    logging.basicConfig(level=logging.INFO,
                        filename='server.log',
                        filemode='a',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    if not os.path.exists(f"./downloads"): #Checks if a user download folder exists, and creates one if it doesn't
        os.makedirs(f"./downloads")
        logging.info("Download folder created.")
    port = int(sys.argv[1])
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    serverSocket.bind(("", port))
    #print("The server is ready to receive")
    logging.info("Server has started")
    serverSocket.listen(64)

    while True: 
        connectionSocket, addr = serverSocket.accept()
        #print(f"Connection established: {addr}")
        logging.info(f"Connection established with {addr}")
        threading.Thread(target=clientHandle, args=(connectionSocket,)).start()

if __name__=="__main__":
    startServer()

