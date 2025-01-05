import requests
import json
import gspread
from google.oauth2.service_account import Credentials
import time
import hashlib
import hmac
import pandas as pd
import streamlit as st
from datetime import date


# Google Sheets setup
SHEET_NAME = "Sheet1"  # Name of the sheet
SRC_SHEET_ID = "1JGEHO-lPIM49hI3hlZ83b3fSHdZ1LAHCTpVqpiQSQNQ"


# Function to process JSON response
def process_response(response):
    result = response.get("result", [])
    data = []
    for device in result:
        row = {item["code"]: item["value"] for item in device["status"]}
        row["Device ID"] = device["id"]
        data.append(row)
        # Add a blank row to separate devices
        data.append({})
    return data

# Function to update the Google Sheet
def batch_update_sheet(client, data, start_row):
    worksheet = client.open_by_key(SRC_SHEET_ID).worksheet(SHEET_NAME)
    batch_data = []
    for row in data:
        batch_data.append([row.get(key, "") for key in row.keys()])

    # Determine the starting range for the batch update
    end_row = start_row + len(batch_data) - 1
    range_ = f"A{start_row}:Z{end_row}"
    worksheet.update(range_, batch_data)
    return end_row + 1  # Return the next starting row

def script():


  # Declare constants
    ClientID = "gskeq9yqu5xetvtrnyy4"
    ClientSecret = "d9fb042af13a4c57a2a72ef2aa369ff9"
    BaseUrl = "https://openapi.tuyaeu.com"
    EmptyBodyEncoded = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


  # Initialize variables
    collected_data = []
    last_row = 10  # Track the last row for Google Sheet
    start_time = time.time()


    # Set up the scope and credentials
    creds = Credentials.from_service_account_file('sheets-381015-aa5c72321656.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive'])
    
    # Authorize the client
    client = gspread.authorize(creds)

    while True:
        # Get the current timestamp in milliseconds
        tuyatime = str(int(time.time() * 1000))

        # Step 1: Get Access Token
        URL = "/v1.0/token?grant_type=1"
        StringToSign = f"{ClientID}{tuyatime}GET\n{EmptyBodyEncoded}\n\n{URL}"
        AccessTokenSign = hmac.new(
            ClientSecret.encode(), StringToSign.encode(), hashlib.sha256
        ).hexdigest().upper()

        headers = {
            "sign_method": "HMAC-SHA256",
            "client_id": ClientID,
            "t": tuyatime,
            "mode": "cors",
            "Content-Type": "application/json",
            "sign": AccessTokenSign,
        }

        response = requests.get(f"{BaseUrl}{URL}", headers=headers)
        AccessTokenResponse = response.json()
        AccessToken = AccessTokenResponse.get("result", {}).get("access_token")

        # Step 2: Send Device Status Request
        DeviceIDs = "bf4847303f353ca56ecq9u,bf61a2863242531e4958ka"
        URL = f"/v1.0/iot-03/devices/status?device_ids={DeviceIDs}"
        StringToSign = f"{ClientID}{AccessToken}{tuyatime}GET\n{EmptyBodyEncoded}\n\n{URL}"
        RequestSign = hmac.new(
            ClientSecret.encode(), StringToSign.encode(), hashlib.sha256
        ).hexdigest().upper()

        headers.update({"access_token": AccessToken, "sign": RequestSign})
        response = requests.get(f"{BaseUrl}{URL}", headers=headers)
        RequestResponse = response.json()

        # Process response and add to collected data
        processed_data = process_response(RequestResponse)
        collected_data.extend(processed_data)

        # Display the result in Streamlit
        st.write(pd.DataFrame(processed_data))

        # If 1 minute has passed, batch update the Google Sheet
        if time.time() - start_time >= 60:
            last_row = batch_update_sheet(client, collected_data, last_row)
            collected_data = []  # Reset collected data
            start_time = time.time()

        time.sleep(1)  # Wait for 1 second before the next request

# Streamlit UI
def main():
    st.title("Device Status Dashboard")

    # Button to start the monitoring process
    if st.button("Start Monitoring"):
        script()

      
if __name__ == "__main__":
    main()
