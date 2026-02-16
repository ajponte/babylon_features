import os
import sys
import requests

# Configuration for testing a remote Chroma instance
# Assuming Chroma is running on localhost:8000 in a Docker container
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8003))

def check_chroma_connection():
    """
    Attempts to connect to a remote Chroma server via HTTP.
    Exits with code 0 on success, 1 on failure.
    """
    chroma_url = f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v2/heartbeat"
    print(f"Attempting to connect to Chroma at {chroma_url}")
    try:
        response = requests.get(chroma_url, timeout=5) # 5 second timeout
        if response.status_code == 200:
            print(f"Successfully connected to Chroma at {chroma_url}")
            sys.exit(0)
        else:
            print(f"Failed to connect to Chroma at {chroma_url}. Status code: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not establish connection to Chroma at {chroma_url}.")
        print(f"Please ensure a Chroma server is running and accessible at {CHROMA_HOST}:{CHROMA_PORT}.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"ERROR: Connection to Chroma at {chroma_url} timed out after 5 seconds.")
        sys.exit(1)
    except Exception as e:
        print(f"AN UNEXPECTED ERROR OCCURRED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_chroma_connection()
