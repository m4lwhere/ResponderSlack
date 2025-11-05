#!/usr/bin/env python3
"""
Export Responder hashes to CSV or TXT format.

Usage:
    python3 exportHashes.py --csv          # Export to CSV format
    python3 exportHashes.py --txt          # Export to TXT format
    python3 exportHashes.py --both         # Export both formats
    python3 exportHashes.py                # Default: CSV format
"""

import sqlite3
import json
import csv
import argparse
import datetime
from responderSlack import DbConnect, executeQuery, getTimestamp, printWithTimestamp


def exportToCsv(cursor, filename='hashes.csv'):
    """
    Export all hashes to CSV format with full details.

    Args:
        cursor: Database connection object
        filename: Output filename for CSV (default: hashes.csv)

    Returns:
        int: Number of hashes exported, or -1 on failure
    """
    try:
        printWithTimestamp(f"Querying database for all hashes...")
        res = executeQuery(cursor, "SELECT user,type,client,fullhash,timestamp FROM Responder")

        if res is None:
            printWithTimestamp("ERROR: Failed to query hashes from database")
            return -1

        output = []
        header = ['user', 'type', 'client', 'fullhash', 'timestamp']

        for row in res.fetchall():
            output.append([row[0], row[1], row[2], row[3], row[4]])

        with open(filename, 'w', newline='') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(header)
            writer.writerows(output)

        printWithTimestamp(f"✓ Successfully exported {len(output)} hashes to {filename}")
        return len(output)

    except sqlite3.Error as e:
        printWithTimestamp(f"ERROR: Database error - {e}")
        return -1
    except IOError as e:
        printWithTimestamp(f"ERROR: File I/O error - {e}")
        return -1


def exportToTxt(cursor, filename='hashes.txt'):
    """
    Export all hashes to TXT format (hashes only, one per line).

    Args:
        cursor: Database connection object
        filename: Output filename for TXT (default: hashes.txt)

    Returns:
        int: Number of hashes exported, or -1 on failure
    """
    try:
        printWithTimestamp(f"Querying database for all hashes...")
        res = executeQuery(cursor, "SELECT fullhash FROM Responder")

        if res is None:
            printWithTimestamp("ERROR: Failed to query hashes from database")
            return -1

        hash_count = 0
        with open(filename, 'w') as hashFile:
            for row in res.fetchall():
                hashFile.write(f"{row[0]}\n")
                hash_count += 1

        printWithTimestamp(f"✓ Successfully exported {hash_count} hashes to {filename}")
        return hash_count

    except sqlite3.Error as e:
        printWithTimestamp(f"ERROR: Database error - {e}")
        return -1
    except IOError as e:
        printWithTimestamp(f"ERROR: File I/O error - {e}")
        return -1


def loadConfig():
    """
    Load configuration from config.json.

    Returns:
        str: Path to Responder database
    """
    try:
        with open("./config.json", "r") as configFile:
            config = json.loads(configFile.read())

        respDB = config["ResponderDB"]
        printWithTimestamp(f"Loaded config - Database: {respDB}")
        return respDB

    except FileNotFoundError:
        printWithTimestamp("ERROR: config.json not found")
        raise
    except json.JSONDecodeError as e:
        printWithTimestamp(f"ERROR: Invalid JSON in config.json - {e}")
        raise
    except KeyError:
        printWithTimestamp("ERROR: ResponderDB not found in config.json")
        raise


def main():
    """Main function to handle command-line arguments and export hashes."""
    parser = argparse.ArgumentParser(
        description='Export Responder hashes to CSV or TXT format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 exportHashes.py              # Export to CSV (default)
  python3 exportHashes.py --csv        # Export to CSV
  python3 exportHashes.py --txt        # Export to TXT
  python3 exportHashes.py --both       # Export both formats
  python3 exportHashes.py --csv -o my_hashes.csv  # Custom filename
        """
    )

    parser.add_argument('--csv', action='store_true',
                        help='Export to CSV format (default)')
    parser.add_argument('--txt', action='store_true',
                        help='Export to TXT format (hashes only)')
    parser.add_argument('--both', action='store_true',
                        help='Export both CSV and TXT formats')
    parser.add_argument('-o', '--output', type=str,
                        help='Output filename (default: hashes.csv or hashes.txt)')

    args = parser.parse_args()

    # Determine export format
    export_csv = args.csv or args.both or (not args.txt and not args.both)
    export_txt = args.txt or args.both

    cursor = None

    try:
        printWithTimestamp("=== Responder Hash Export Tool ===")

        # Load config and connect to database
        respDB = loadConfig()
        cursor = DbConnect(respDB)

        success = True

        # Export CSV
        if export_csv:
            csv_filename = args.output if args.output and not args.both else 'hashes.csv'
            result = exportToCsv(cursor, csv_filename)
            if result == -1:
                success = False

        # Export TXT
        if export_txt:
            txt_filename = args.output if args.output and not args.both else 'hashes.txt'
            result = exportToTxt(cursor, txt_filename)
            if result == -1:
                success = False

        if success:
            printWithTimestamp("=== Export Complete ===")
        else:
            printWithTimestamp("=== Export Failed ===")
            exit(1)

    except Exception as e:
        printWithTimestamp(f"ERROR: {e}")
        exit(1)

    finally:
        # Ensure database connection is properly closed
        if cursor:
            cursor.close()
            printWithTimestamp("Database connection closed")


if __name__ == "__main__":
    main()
