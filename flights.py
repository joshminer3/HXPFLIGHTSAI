import json
import requests
import pandas as pd
from pandas import json_normalize
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

# Your API setup
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMjg4ODcyY2QtZmQ4OS00YTIxLWJhZGItZWE2OTNmOTY2ZTRkIiwidHlwZSI6ImFwaV90b2tlbiJ9.uFLEIdOU19u8E81NamqGiMghYN64HOmvFN_KJAWGfI4"
}
url = "https://api.edenai.run/v2/ocr/identity_parser"

# Temporary storage for the generated Excel file name
output_file = "passports_file.xlsx"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():

    global output_file
    trip_name = request.form['trip_name']
    file_urls = [url.strip() for url in request.form['file_urls'].splitlines() if url.strip()]

    #file_urls = request.form.getlist('file_urls')  # Get the list of URLs from the form
    dataframes = []

    # Loop through each file URL and process it
    for file_url in file_urls:
        json_payload = {
            "providers": "microsoft",
            "file_url": file_url  # Use the current file URL
        }

        # Make the API request for the current file
        response = requests.post(url, json=json_payload, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()

            microsoft_data = result.get("microsoft", {}).get("extracted_data", [])

            if microsoft_data:
                # Normalize the nested JSON data
                df = json_normalize(microsoft_data)

                # Check if 'given_names' exists before processing it
                if 'given_names' in df.columns:
                    # Extract first and second given names
                    df['first_given_name'] = df['given_names'].apply(lambda x: x[0]['value'] if isinstance(x, list) and len(x) > 0 else None)
                    df['middle_name'] = df['given_names'].apply(lambda x: x[1]['value'] if isinstance(x, list) and len(x) > 1 else None)

                    # Now drop the original 'given_names' column
                    df.drop(columns=['given_names'], inplace=True)

                # Select only the desired columns, check if they exist before filtering
                desired_columns = [
                    'last_name.value',  # Last name
                    'first_given_name',  # First given name (added)
                    'middle_name',  # Middle name (added)
                    'gender.value',  # Gender
                    'birth_date.value',  # Birth date
                    'expire_date.value',  # Expiration date
                    'document_id.value',  # Document ID
                    'country.name'  # Country name
                ]

                # Ensure only existing columns are selected
                filtered_df = df[[col for col in desired_columns if col in df.columns]]

                # Add the processed DataFrame to the list
                dataframes.append(filtered_df)
            else:
                print(f"No data extracted for file {file_url}")
        else:
            print(f"Error: API request failed for file {file_url} with status code {response.status_code}")
            print(response.text)

    # Concatenate all the DataFrames into a single DataFrame
    if dataframes:
        final_df = pd.concat(dataframes, ignore_index=True)
        # Save the DataFrame to an Excel file
        output_file = f"{trip_name}_passport_data.xlsx"
        final_df.to_excel(output_file, index=False)
        # Render result.html with a link to download the file
        return render_template('result.html')

    else:
        print("No data to display.")

@app.route('/download')
def download_file():
    # Serve the file for download
    return send_file(output_file, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)