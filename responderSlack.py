from time import sleep
import requests, sqlite3, json, datetime, logging

# Configure logging for database operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def getTimestamp():
    """Get formatted timestamp for console output."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def printWithTimestamp(message):
    """Print message to console with timestamp."""
    print(f"[{getTimestamp()}] {message}")

def sendWebhook(hookPayload):
    r = requests.post(url=webhook, headers={'Content-Type': 'application/json'}, data=json.dumps(hookPayload))

def DbConnect(dbFile):
    """
    Connect to SQLite database with concurrency-safe settings.

    Enables WAL mode for concurrent read/write access and sets timeouts
    to prevent indefinite blocking on database locks.
    """
    try:
        # Connect with 30-second timeout to prevent infinite waits
        conn = sqlite3.connect(dbFile, timeout=30.0)

        # Enable WAL (Write-Ahead Logging) mode for concurrent access
        # This allows readers and writers to operate without blocking each other
        conn.execute("PRAGMA journal_mode=WAL;")

        # Set busy timeout to 30 seconds (30000 ms)
        # SQLite will automatically retry for up to 30 seconds if database is locked
        conn.execute("PRAGMA busy_timeout=30000;")

        logger.info(f"Database connection established to {dbFile} with WAL mode enabled")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database {dbFile}: {e}")
        raise

def executeQuery(cursor, query, retries=3, delay=2):
    """
    Execute a database query with retry logic for handling locks.

    Args:
        cursor: Database cursor/connection object
        query: SQL query string to execute
        retries: Number of retry attempts on lock errors (default: 3)
        delay: Delay in seconds between retries (default: 2)

    Returns:
        Query result object or None on failure

    Raises:
        sqlite3.Error: If query fails after all retries
    """
    for attempt in range(retries):
        try:
            result = cursor.execute(query)
            return result
        except sqlite3.OperationalError as e:
            # Check if it's a database lock error
            if "locked" in str(e).lower() and attempt < retries - 1:
                logger.warning(f"Database locked, retry {attempt + 1}/{retries} in {delay}s: {e}")
                sleep(delay)
            else:
                logger.error(f"Database operational error after {attempt + 1} attempts: {e}")
                raise
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error executing query: {e}")
            raise
    return None

def checkNewHash(cursor, lastTime):
    """
    Check for new hashes in the database since lastTime.

    Args:
        cursor: Database connection object
        lastTime: Timestamp to check for new entries after

    Returns:
        List of new hash entries or empty list if none found
    """
    try:
        # Search for any hash in the db newer than the lastTime
        res = executeQuery(cursor, f"SELECT user,type,client,fullhash FROM Responder WHERE timestamp > '{lastTime}'")
        if res is None:
            logger.error("Failed to query new hashes from database")
            return []

        Output = []
        # Store the results in a list of lists to reference later
        for row in res.fetchall():
            # Check if we're discarding duplicates
            if discardDupes:
                userNew = row[0]
                checkPrevHash = executeQuery(cursor, f"SELECT user,client FROM Responder WHERE timestamp < '{lastTime}'")
                if checkPrevHash is None:
                    logger.warning("Failed to check for duplicate hashes, skipping duplicate check")
                else:
                    for prevRow in checkPrevHash:
                        if prevRow[0] == userNew:
                            printWithTimestamp(f"Duplicate found: {userNew} - skipping")
                            return False
            Output.append([row[0], row[1], row[2], row[3]])
        return Output
    except sqlite3.Error as e:
        logger.error(f"Database error in checkNewHash: {e}")
        return []

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

            # Print to console and send webhook
            printWithTimestamp(f"New hash captured - User: {i[0]}, Type: {i[1]}, IP: {i[2]}")
            sendWebhook(hookPayload)
        return True
    else:
        return False

def sendStartupNotification():
    """Send a webhook notification that ResponderSlack is starting."""
    startupPayload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🟢 ResponderSlack Started"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"ResponderSlack is now listening for new hashes.\n*Started at:* {getTimestamp()}"
                }
            }
        ]
    }
    sendWebhook(startupPayload)
    printWithTimestamp("ResponderSlack started - Listening for new hashes...")

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

    # Send startup notification
    sendStartupNotification()

    while True:
        checkHash = sendHash()
        if checkHash:
            lastTime = datetime.datetime.utcnow()
        sleep(sleepTime)

if __name__ == "__main__":
    main()