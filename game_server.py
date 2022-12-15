#---------------------------------------
# Name: game_server.py
# Date: 2022-12-14 
# Author: Josh Wolowich, 7889737
#---------------------------------------

import time
from time import sleep
import sys
from random import randint
import threading
import socket
import json

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 8601               # Arbitrary non-privileged port

TITLE_SCREEN = '''
   STAR DUEL
-Server Version-
'''

OPTIONS = '''
Please Type Choice Number
Use Rollback?
1. Yes
2. No
'''

MESSAGE_FORMAT = '${{"GameOver":"{}", "OpponentLocation":"{}", "OpponentShoot":"{}", "Rollback":"{}", "PlayerLocation":"{}", "PlayerShoot":"{}", "Winner":"{}"}}$' #message to send to players

MAP_SIZE = 12 #size of game map

locations = [int(MAP_SIZE/2)] * 2 #player locations 
shots = [0] * 2 #player shooting flags 
gameOver = 0 #true when game ends 
rollback = [0] * 2 #true when player must rollback
winner = -1 #winner player number
rollbackActive = 0 #true when packets are droped and rollback is about to occur 
useRollback = 0 #true when rollback is chosen
rollbackLocations = [int(MAP_SIZE/2)] * 2 #player locations to rollback to
rollbackShots = [0] * 2 #player shooting flags to rollback to 

#handles sending and receiving messages from players
def handlePlayer(conn, playerNum, OpponentNum):
    global gameOver
    global locations
    global shots
    global rollbackActive
    global rollbackLocations
    global rollbackShots
    global rollback

    lastMessageTime = 0 #time of last received message
    conn.setblocking(0)
    while gameOver < 1:
        message = ""
        
        #if rollback must occur
        if not rollbackActive and rollback[playerNum] and useRollback:
            message = MESSAGE_FORMAT.format(gameOver, rollbackLocations[OpponentNum], rollbackShots[OpponentNum], 1, rollbackLocations[playerNum], rollbackShots[playerNum], 0)
            rollback[playerNum] = 0
            locations[playerNum] = rollbackLocations[playerNum]
            shots[playerNum] = rollbackShots[playerNum]
            print("Rolled Back Player:", playerNum + 1)

        #send message
        message = MESSAGE_FORMAT.format(gameOver, locations[OpponentNum], shots[OpponentNum], 0, locations[playerNum], shots[playerNum], 0)
        msgBytes = message.encode()
        conn.sendall(msgBytes)
        try:
            #receive message
            data = conn.recv(1024)
            if data:
                #if recieved message after rollback was actived, signal to rollback
                if rollbackActive:
                    rollbackActive = 0
                    rollback[1] = 1
                    rollback[0] = 1

                #convert to json
                dataStr = data.decode('UTF-8')
                start = dataStr.find('$')+1
                end = dataStr.find('$',start)
                splitDataStr = dataStr[start : end]
                dataJson = json.loads(splitDataStr)

                #update info
                if "Location" in dataJson and "Shoot" in dataJson:
                    locations[playerNum] = int(dataJson["Location"])
                    shots[playerNum] = int(dataJson["Shoot"])
                    lastMessageTime = time.time()

        except BlockingIOError:
            #if not received in time, activate rollabck
            if lastMessageTime < time.time() + 0.3:
                if useRollback and not rollbackActive and not rollback[0] and not rollback[1]:
                    rollbackActive = 1
                    rollbackLocations[0] = locations[0]
                    rollbackLocations[1] = locations[1]
                    rollbackShots[0] = shots[0]
                    rollbackShots[1] = shots[1]
    
        sleep(0.1)

    #update who won
    playerWon = 0
    if playerNum == winner:
        playerWon = 1

    #send final message
    message = MESSAGE_FORMAT.format(gameOver, locations[OpponentNum], shots[OpponentNum], 0, locations[playerNum], shots[playerNum], playerWon)
    msgBytes = message.encode()
    conn.sendall(msgBytes)

#check if a player has won
def checkWin():
    global gameOver
    global winner

    while gameOver < 1:
        #cannot win durring a rolback
        if(locations[0] == locations[1] and not rollbackActive):
            if(shots[0] and not shots[1]):
                gameOver = 1
                winner = 0
            elif(shots[1] and not shots[0]):
                gameOver = 1
                winner = 1


#start the server
def startUp():
    global useRollback

    try:
        print(TITLE_SCREEN)
        #get rollback choice
        choice = input(OPTIONS)
        if int(choice) == 1:
            useRollback = 1

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            print("Game is being hosted at: ",socket.gethostname(),":",PORT)
            s.listen()

            #accept players
            p1Conn, p1Addr = s.accept()
            print("Player 1 Joined From: ",p1Addr)
            p2Conn, p2Addr = s.accept()
            print("Player 2 Joined From: ",p2Addr)
            print("Starting Game...")
            p1Thread = threading.Thread(target=handlePlayer, args=(p1Conn, 0, 1))
            p2Thread = threading.Thread(target=handlePlayer, args=(p2Conn, 1, 0))
            checkWinThread = threading.Thread(target=checkWin, args=())
            p1Thread.start()
            p2Thread.start()
            checkWinThread.start()
            p1Thread.join()
            p2Thread.join()
            checkWinThread.join()
            p1Conn.close()
            p2Conn.close() 
            s.close()

            #end game
            print("The Game Has Concluded.")
                    
    except KeyboardInterrupt:
        global gameOver
        gameOver = 1
        p1Thread.join()
        p2Thread.join()
        checkWinThread.join() 
        p1Conn.close()
        p2Conn.close() 
        s.close()
        print("Exiting")
        sys.exit(0)

startUp()
print("Exiting")