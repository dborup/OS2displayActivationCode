import requests
import re
import json
from datetime import datetime, timedelta

# Python for getting activation code event from Magenta API and sending Teams messages
# Change to the script's directory before running it
# */1 8-16 * * 1-5 cd /path/to/script && python3 geteventsteams.py >> /usr/local/bin/geteventsteams.log 2>&1

# Function to load the previous event state from a file
def load_previous_state():
    try:
        with open('previous_state.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Function to save the current event state to a file
def save_current_state(events):
    with open('/usr/local/bin/previous_state.json', 'w') as file:
        json.dump(events, file)

# Function to fetch computer location information
def fetch_computer_location(computer_name):
    # Your API endpoint URL and headers for computer information
    computer_url = 'https://os2borgerpc-admin.magenta.dk/api/system/computers'
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer Your_API_Here'  # Replace with your API token
    }

    response = requests.get(computer_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for computer_info in data:
            if computer_info['name'] == computer_name:
                return computer_info['location']
    return None

# Calculate the "from_date" 7 days back from today
today = datetime.now()
seven_days_ago = today - timedelta(days=7)
from_date = seven_days_ago.strftime('%Y-%m-%d')

# Calculate the "to_date" as the current day
to_date = today.strftime('%Y-%m-%d')

# Your API endpoint URL and headers for activation code events
activation_url = 'https://os2borgerpc-admin.magenta.dk/api/system/events'
activation_headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer Your_API_Here'  # Replace with your API token
}

# Teams webhook URL (Replace with your actual Teams webhook URL)
teams_webhook_url = 'Your_API_Here'

# Parameters for the GET request for activation code events
params = {
    'from_date': from_date,
    'to_date': to_date,
    'status': 'NEW',
    'limit': '100',
    'offset': '0'
}

# Send GET request to the API for activation code events
response = requests.get(activation_url, headers=activation_headers, params=params)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse the JSON response for activation code events
    data = response.json()
    # Initialize a list to store the extracted data
    activation_data_list = []

    # Extract the 8-digit code, pc_name, and occurred_time from the "summary" field using regex
    for item in data['items']:
        match = re.search(r'os2displayactivationcode: (\d{8})', item['summary'])
        if match:
            activation_code = match.group(1)
            pc_name = item['pc_name']
            occurred_time = item['occurred_time']
            activation_data_list.append({
                'PC Name': pc_name,
                'Activation Code': activation_code,
                'Occurred Time': occurred_time
            })

    # Load the previous event state
    previous_state = load_previous_state()

    # Check if there are any new events
    new_activation_data_list = []
    for activation_data in activation_data_list:
        if activation_data not in previous_state:
            new_activation_data_list.append(activation_data)
        elif activation_data['PC Name'] not in [data['PC Name'] for data in previous_state if data['Activation Code'] == activation_data['Activation Code']]:
            # Add the PC Name if it has the same Activation Code but is not in the previous state
            new_activation_data_list.append(activation_data)

    if new_activation_data_list:
        # There are new events, update and save the current state
        save_current_state(activation_data_list)

        # Prepare the message to send to Teams with a red theme color
        message = {
            '@context': 'https://schema.org/extensions',
            '@type': 'MessageCard',
            'themeColor': 'FF0000',  # Red color
            'title': 'TODO: Activation Code Events',
            'text': 'List of Activation Code Events:'
        }

        sections = []
        for activation_data in new_activation_data_list:
            pc_name = activation_data['PC Name']
            location = fetch_computer_location(pc_name)  # Fetch computer location
            activation_code = activation_data['Activation Code']
            occurred_time = activation_data['Occurred Time']

            section = {
                'facts': [
                    {
                        'name': 'Location',
                        'value': location  # Display computer location
                    },
                    {
                        'name': 'Activation Code',
                        'value': activation_code
                    },
                    {
                        'name': 'Occurred Time',
                        'value': occurred_time
                    }
                ]
            }

            if pc_name:
                section['text'] = f'**PC Name:** {pc_name}'

            sections.append(section)

        message['sections'] = sections

        # Send the message to Teams using the webhook
        response_teams = requests.post(teams_webhook_url, json=message)

        # Check if the message was sent successfully (status code 200)
        if response_teams.status_code == 200:
            print("Message sent to Teams successfully.")
        else:
            print(f"Error sending message to Teams: {response_teams.status_code}")
    else:
        print("No changes in events, no message sent to Teams.")
else:
    print(f"Error: {response.status_code}")
