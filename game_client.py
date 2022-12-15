#---------------------------------------
# Name: game_client.py
# Date: 2022-12-14 
# Author: Josh Wolowich, 7889737
#---------------------------------------

import os
from time import sleep
import sys
import random 
from random import randint
import threading
import socket
import json
import time

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 8601               # Arbitrary non-privileged port

TITLE_SCREEN = '''
   STAR DUEL
-Client Version-
'''

OPTIONS1 = '''
Please Enter Choice Number
1. Join Game
2. Host Game
'''

OPTIONS2 = '''
Please Enter Choice Number
Use Rollback?
1. Yes
2. No
'''

PLAYER_MESSAGE_FORMAT = '${{"Location":"{}", "Shoot":"{}"}}$' #message sent by player client

HOST_MESSAGE_FORMAT = '${{"GameOver":"{}", "OpponentLocation":"{}", "OpponentShoot":"{}", "Rollback":"{}", "PlayerLocation":"{}", "PlayerShoot":"{}", "Winner":"{}"}}$' #message sent by host client


MAP_SIZE = 12 #size of game map

DROP_CHANCE = 0.01 #chance of sleeping instead of sending message to server

p1Location = int(MAP_SIZE/2) #location of player 1
p2Location = int(MAP_SIZE/2) #location of player 2
p1Shoot = 0 #true if player 1 is shooting
p2Shoot = 0 #true if player 2 is shooting
gameOver = 1 #true if game is over
won = 0 #true if player has won
rollback = 0 #true if rollback needs to be done
rollbackActive = 0 #true when packets are droped and rollback is about to occur 
useRollback = 0 #true when rollback is chosen
rollbackLocations = [int(MAP_SIZE/2)] * 2 #player locations to rollback to
rollbackShots = [0] * 2 #player shooting flags to rollback to

#class handles displaying the game map
class GameMap:
    
    def displayMap(self):
        global gameOver

        while gameOver < 1:
            os.system('clear')
            self.printMap()
            sleep(0.1)

    def printMap(self):
        map = "+"
        for c in range(MAP_SIZE*2):
            map = map + "-"
        map = map + "+"

        for r in range(MAP_SIZE):
            map = map + "\n|"
            if(r == p1Location):
                map = map + ">"
            else:
                map = map + " "
            if(r == p1Location and r == p2Location and p1Shoot and p2Shoot):
                for c in range(int((MAP_SIZE*2-2)/2) - 1):
                    map = map + "="
                map = map + "><"
                for c in range(int((MAP_SIZE*2-2)/2) - 1):
                    map = map + "="
            elif(r == p1Location and p1Shoot):
                for c in range(MAP_SIZE*2-3):
                    map = map + "="
                map = map + ">"
            elif(r == p2Location and p2Shoot):
                map = map + "<"
                for c in range(MAP_SIZE*2-3):
                    map = map + "="
            else:  
                for c in range(MAP_SIZE*2-2):
                    map = map + " "
            if(r == p2Location):
                map = map + "<"
            else:
                map = map + " "

            map = map + "|"
        map = map + "\n+"
        
        for c in range(MAP_SIZE*2):
            map = map + "-"
        map = map + "+"

        print(map)

#class handles making decisions for a computer controlled player
class ComPlayer:

    def play(self):
        global gameOver

        while gameOver < 1:
            self.action()
            sleep(0.1)

    
    def action(self):
        global p1Location
        global p1Shoot

        p1Shoot = 0
        choice = randint(0,10)
        #randomly choose an action for the player
        if(choice == 0):
            p1Shoot = 1
        elif(choice == 1):
            p1Location = max(p1Location-1,0)
        elif(choice == 2):
            p1Location = min(p1Location+1,MAP_SIZE-1)

#class handles hosting responsibilites
class Host:

    #recieve and send messages to player
    def handlePlayer(self,conn):
        global gameOver
        global p2Location
        global p2Shoot
        global p1Location
        global p1Shoot
        global rollbackActive
        global rollbackLocations
        global rollbackShots
        global rollback

        gameOver = 0
        lastMessageTime = 0 #time since last received message
        conn.setblocking(0)

        while gameOver < 1:

            message = ""
            #if rollback must occur
            if not rollbackActive and rollback and useRollback:
                message = HOST_MESSAGE_FORMAT.format(gameOver, rollbackLocations[0], rollbackShots[0], 1, rollbackLocations[1], rollbackShots[1], 0)
                rollback = 0
                p2Location = rollbackLocations[1]
                p2Shoot = rollbackShots[1]
                p1Location = rollbackLocations[0]
                p1Shoot = rollbackShots[0]
            
            #send message
            message = HOST_MESSAGE_FORMAT.format(gameOver, p1Location, p1Shoot, 0, p2Location, p2Shoot, 0)
            msgBytes = message.encode()
            conn.sendall(msgBytes)

            try:
                #receive message
                data = conn.recv(1024)
                if data:
                    #if recieved message after rollback was actived, signal to rollback
                    if rollbackActive:
                        rollbackActive = 0
                        rollback = 1

                    #convert to json
                    dataStr = data.decode('UTF-8')
                    start = dataStr.find('$')+1
                    end = dataStr.find('$',start)
                    splitDataStr = dataStr[start : end]
                    dataJson = json.loads(splitDataStr)
                    
                    #update info
                    if "Location" in dataJson and "Shoot" in dataJson:
                        p2Location = int(dataJson["Location"])
                        p2Shoot = int(dataJson["Shoot"])
                        lastMessageTime = time.time()

            except BlockingIOError:
                #if not received in time, activate rollabck
                if lastMessageTime < time.time() + 0.3:
                    if useRollback and not rollbackActive and not rollback:
                        rollbackActive = 1
                        rollbackLocations[0] = p1Location
                        rollbackLocations[1] = p2Location
                        rollbackShots[0] = p1Shoot
                        rollbackShots[1] = p2Shoot
            
            sleep(0.1)

        #update who won
        playerWon = 1
        if won:
            playerWon = 0
        
        #send final message
        message = HOST_MESSAGE_FORMAT.format(gameOver, p1Location, p1Shoot, 0, p2Location, p2Shoot, playerWon)
        msgBytes = message.encode()
        conn.sendall(msgBytes)

    #check if a player has won
    def checkWin(self):
        global gameOver
        global won

        while gameOver < 1:
            #cannot win durring a rolback
            if(p1Location == p2Location and not rollbackActive):
                if(p1Shoot and not p2Shoot):
                    gameOver = 1
                    won = 1
                elif(p2Shoot and not p1Shoot):
                    gameOver = 1
                    won = 0

#recieve and send messages to server
def handleServer():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        global gameOver
        global p1Location
        global p2Location
        global p1Shoot
        global p2Shoot
        global won

        s.connect((HOST, PORT))
        data = s.recv(1024)
        if data:
            #convert to json
            dataStr = data.decode('UTF-8')
            start = dataStr.find('$')+1
            end = dataStr.find('$',start)
            splitDataStr = dataStr[start : end]
            dataJson = json.loads(splitDataStr)
            gameOver = int(dataJson["GameOver"])

        while gameOver < 1:

            #chance to drop connection for 2 seconds
            if random.random() < DROP_CHANCE:
                sleep(2)
            message = PLAYER_MESSAGE_FORMAT.format(p1Location, p1Shoot)

            msgBytes = message.encode()
            s.sendall(msgBytes)

            data = s.recv(1024)
            if data:
                #convert to json
                dataStr = data.decode('UTF-8')
                start = dataStr.find('$')+1
                end = dataStr.find('$',start)
                splitDataStr = dataStr[start : end]

                try:
                    dataJson = json.loads(splitDataStr)
                    if "OpponentLocation" in dataJson and "OpponentShoot" in dataJson and "GameOver" in dataJson and "Winner" in dataJson and "Rollback" in dataJson and "PlayerLocation" in dataJson and "PlayerShoot" in dataJson:
                        #update info
                        p2Location = int(dataJson["OpponentLocation"])
                        p2Shoot = int(dataJson["OpponentShoot"])
                        gameOver = int(dataJson["GameOver"])
                        won = int(dataJson["Winner"])
                        if int(dataJson["Rollback"]) == 1:
                            p1Location = int(dataJson["PlayerLocation"])
                            p1Shoot = int(dataJson["PlayerShoot"])
                except json.decoder.JSONDecodeError:
                    #sleep if bad message
                    sleep(0.01)
            
            sleep(0.1)

#start the client
def startUp():
    global gameOver
    global useRollback
    gameOver = 1

    map = GameMap()
    com = ComPlayer()

    #get host/join choice
    print(TITLE_SCREEN)
    choice = input(OPTIONS1)
    if int(choice) == 1:
        #create threads 
        mapThread = threading.Thread(target=GameMap.displayMap, args=(map,))
        comThread = threading.Thread(target=ComPlayer.play, args=(com,))
        serverThread = threading.Thread(target=handleServer, args=())
        serverThread.start()

        #wait until host starts game
        while gameOver == 1:
            sleep(0.1)
        mapThread.start()
        comThread.start()
        
        try:
            mapThread.join()
            comThread.join()

            serverThread.join()

            #end game
            os.system('clear')
            print(TITLE_SCREEN)
            if won:
                print("Congratulations You Are Victorious!")
            else:
                print("You Have Been Defeated!")
            

        except KeyboardInterrupt:
            gameOver = 1
            mapThread.join()
            comThread.join()
            serverThread.join()
            print("Exiting")
            sys.exit(0)

    elif int(choice) == 2:

        os.system('clear')
        print(TITLE_SCREEN)
        #get rollback choice
        choice = input(OPTIONS2)
        if int(choice) == 1:
            useRollback = 1
        try:
            map = GameMap()
            com = ComPlayer()
            gameHost = Host()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                print("Game is being hosted at: ",socket.gethostname(),":",PORT)
                s.listen()

                #accept player
                p2Conn, p2Addr = s.accept()
                print("Player 2 Joined From: ",p2Addr)
                print("Starting Game...")
                
                #create threads
                p2Thread = threading.Thread(target=Host.handlePlayer, args=(gameHost,p2Conn))
                checkWinThread = threading.Thread(target=Host.checkWin, args=(gameHost,))
                mapThread = threading.Thread(target=GameMap.displayMap, args=(map,))
                comThread = threading.Thread(target=ComPlayer.play, args=(com,))
                p2Thread.start()

                #wait until game starts 
                while gameOver == 1:
                    sleep(0.1)
                checkWinThread.start()
                mapThread.start()
                comThread.start()
                p2Thread.join()
                checkWinThread.join()
                mapThread.join()
                comThread.join()
                p2Conn.close() 
                s.close()
            
            #end game
            os.system('clear')
            print(TITLE_SCREEN)
            if won:
                print("Congratulations You Are Victorious!")
            else:
                print("You Have Been Defeated!")
                       
        except KeyboardInterrupt:

            gameOver = 1
            p2Thread.join()
            checkWinThread.join() 
            mapThread.join()
            comThread.join()
            p2Conn.close() 
            s.close()
            print("Exiting")
            sys.exit(0)

startUp()
print("Exiting")