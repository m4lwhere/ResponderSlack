import requests, sqlite3, json, slack_sdk, logging, os, csv
from responderSlack import DbConnect
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def loadConfig():
    global respDB, channelID, botToken
        
    with open("./config.json", "r") as configFile:
        config = json.loads(configFile.read())
    
    respDB = config["ResponderDB"]
    channelID = config["channelID"]
    botToken = config["botToken"]
    print(botToken)
    if channelID == "replaceMe" or botToken == "replaceMe":
        raise ValueError("Must add channelID and botToken in config.json!")

def sendFileWebhook(fileName):
    client = WebClient(token=botToken)
    logger = logging.getLogger(__name__)

    try:
        # Call the files.upload method using the WebClient
        # Uploading files requires the `files:write` scope
        result = client.files_upload(
            channels=channelID,
            initial_comment="Here's my file :smile:",
            file=fileName,
        )
        # Log the result
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error uploading file: {}".format(e))

def buildCsv():
    res = cursor.execute(f"SELECT user,type,client,fullhash FROM Responder")
    output = []
    header = ['user','type','client','fullhash']
    for row in res.fetchall():
        output.append([row[0],row[1],row[2],row[3]])
    print(output)
    with open('hashes.csv', 'w', newline='') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(header)
        writer.writerows(output)

def buildFile():
    res = cursor.execute(f"SELECT fullhash FROM Responder")
    with open('hashes.txt', 'w') as hashFile:
        for row in res.fetchall():
            hashFile.writelines(f"{row[0]}\n")


def main():
    global cursor

    loadConfig()
    cursor = DbConnect(respDB)
    # buildCsv()
    buildFile()
    sendFileWebhook("hashes.txt")



if __name__ == "__main__":
    main()