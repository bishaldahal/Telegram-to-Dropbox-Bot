#!/bin/bash

# Define the path to the dummy directory
DUMMY_DIR="$(pwd)/dummy_dir"

# Start a background Python HTTP server that serves the dummy directory and always returns HTTP 200 OK
cd "$DUMMY_DIR"
python3 -m http.server 8000 --bind 0.0.0.0 &
HTTP_SERVER_PID=$!
cd -  # Return to the original directory

# Function to stop the HTTP server when the script exits
function cleanup {
    echo "Stopping HTTP server..."
    kill $HTTP_SERVER_PID
}

# Register the cleanup function to be called on the EXIT signal
trap cleanup EXIT

# Run the bot in a loop
until python3 -m bot; do
    echo "Bot crashed with exit code $?. Respawning.." >&2
    sleep 1
done