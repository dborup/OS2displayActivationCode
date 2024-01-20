#!/usr/bin/env python3

# Capture activation codes from screenshot.
#
# Environment Setup:
# It sets the XAUTHORITY and DISPLAY environment variables, which are necessary for interacting
# with the X server for screen capture.
#
# Screenshot Capture:
# It uses Pillow's ImageGrab module to capture a screenshot of the current screen and saves it
# as "screenshot.png".
# Image Processing:
# The captured screenshot is loaded using OpenCV (cv2), and then it's converted to grayscale.
#
# OCR (Optical Character Recognition):
# It uses the Tesseract OCR library (pytesseract) to extract text from the grayscale image, 
# which is expected to contain an activation code.
#
# Regular Expression Pattern:
# A regular expression pattern (pattern) is defined to search for a specific string ("OSiispiay") 
# followed by 8 digits in the OCR result.
#
# Activation Code Search:
# The script searches for the defined pattern in the OCR result using the re.search method.
#
# Logging and Handling Activation Codes:
# It checks if the detected activation code has been previously logged by reading 
# from "/etc/os2borgerpc/security/logged_codes.txt".
# If the code is not found in the log, it logs the activation code to the syslog using the subprocess.run 
# command and updates the log file with the latest code.
# 
# Main Part:
# The script's main part performs the following steps:
# Reads the last security check timestamp from a file, or uses a default value of 24 hours ago if the file 
# is non-existing or empty.
# Calculates the time difference (delta_sec) between the current time and the last security check timestamp.
# Reads and filters log events from "/var/log/syslog" based on regex patterns and timestamps.
# Filters out security events older than 5 minutes using the filter_security_events function.
# If there are filtered log events, it writes them to the CSV file using the csv_writer function.

import sys
from datetime import datetime, timedelta
import re
import subprocess
from PIL import ImageGrab
import cv2
import pytesseract
import os

# Set the XAUTHORITY and DISPLAY environment variables
os.environ["XAUTHORITY"] = "/home/chrome/.Xauthority"
os.environ["DISPLAY"] = ":0"

# Capture a screenshot using Pillow's ImageGrab
screenshot = ImageGrab.grab()

# Save the screenshot as an image file (you can adjust the filename as needed)
screenshot.save("screenshot.png")

# Load the saved image using OpenCV
image = cv2.imread('screenshot.png')

# Convert the image to grayscale
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Use any necessary preprocessing techniques (e.g., thresholding, noise reduction)

# Perform OCR using Tesseract
activation_code = pytesseract.image_to_string(gray_image)

# Define a regular expression pattern to find "OSiispiay" followed by 8 digits
pattern = r"OSiispiay\s+(\d{8})"

# Search for the pattern in the OCR result
match = re.search(pattern, activation_code)

if match:
    detected_code = match.group(1)
    print("Detected Activation Code:", detected_code)

    # Check if the activation code has been previously logged
    logged_codes = set()
    try:
        with open("/etc/os2borgerpc/security/logged_codes.txt", "r") as code_file:
            logged_codes = set(code_file.read().splitlines())
    except FileNotFoundError:
        pass

    if detected_code not in logged_codes:
        # Log the activation code to syslog
        subprocess.run(["logger", "-p", "local0.info", "-t", "os2displayactivationcode", detected_code])

        # Update the logged codes file with the latest code
        with open("/etc/os2borgerpc/security/logged_codes.txt", "w") as code_file:
            code_file.write(detected_code)

else:
    print("Activation code not found in the OCR result.")

# read syslog and log activations code to Magenta securityevent.csv
# all credit to Magenta ApS
def log_read(sec, log_name):
    """Search a (system) log from within the last "sec" seconds to now."""
    log_event_tuples = []
    now = datetime.now()

    with open(log_name) as f:
        for line in f.readlines():
            line = str(line.replace("\0", ""))
            log_event_timestamp = line[:15]
            log_event = line.strip("\n")
            # convert from log event timestamp to security event log timestamp.
            log_event_datetime = datetime.strptime(
                str(now.year) + " " + log_event_timestamp, "%Y %b  %d %H:%M:%S"
            )
            security_event_log_timestamp = datetime.strftime(
                log_event_datetime, "%Y%m%d%H%M%S"
            )
            # Detect lines from within the last x seconds to now.
            if (datetime.now() - timedelta(seconds=sec)) <= log_event_datetime <= now:
                log_event_tuples.append((security_event_log_timestamp, log_event))

    return log_event_tuples


def csv_writer(security_events):
    """Write security events to security events file."""
    with open("/etc/os2borgerpc/security/securityevent.csv", "at") as csvfile:
        for timestamp, security_problem_uid, log_event, complete_log in security_events:
            event_line = log_event.replace("\n", " ").replace("\r", "").replace(",", "")
            csvfile.write(
                f"{timestamp},{security_problem_uid},{event_line},{complete_log}\n"
            )


def filter_security_events(security_events):
    """Filter security events older than 5 minutes."""
    now = datetime.now()
    filtered_events = [
        security_event
        for security_event in security_events
        if datetime.strptime(security_event[0], "%Y%m%d%H%M%S")
        > now - timedelta(minutes=5)
    ]
    return filtered_events

# The file to inspect for events
log_name = "/var/log/syslog"

now = datetime.now()
# The default value in case lastcheck.txt is nonexisting or empty:
last_security_check = now - timedelta(hours=24)
try:
    with open("/etc/os2borgerpc/security/lastcheck.txt", "r") as fp:
        timestamp = fp.read()
        if timestamp:
            last_security_check = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
except IOError:
    pass

delta_sec = (now - last_security_check).total_seconds()
log_event_tuples = log_read(delta_sec, log_name)

security_problem_uid_template_var = "%SECURITY_PROBLEM_UID%"

regexes = [
    r"os2displayactivationcode: (.*)"
]

# Filter log_event_tuples based on regex matches and put them
# on the form the admin site expects:
# (timestamp, security_problem_uid, summary, complete_log) (which we don't use.)
log_event_tuples = [
    (log_timestamp, security_problem_uid_template_var, log_event, " ")
    for (log_timestamp, log_event) in log_event_tuples
    if any([re.search(regex, log_event, flags=re.IGNORECASE) for regex in regexes])
]

log_event_tuples = filter_security_events(log_event_tuples)

if not log_event_tuples:
    sys.exit()

csv_writer(log_event_tuples)
