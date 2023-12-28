import os
import subprocess
import json
import sys
import csv

# User-editable section
parent_folder_id = 'ca6cc8b9-f663-4422-a204-c2a63daed34c'
wallet_file = '/Volumes/Untitled/Spawn/ardrive-wallet.json'

def get_existing_folder_id(folder_name, parent_folder_id):
    command = ['ardrive', 'list-folder', '-F', parent_folder_id]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error listing folders: {result.stderr}")
        sys.exit(1)

    folders = json.loads(result.stdout)
    for folder in folders:
        if folder.get("name") == folder_name:
            return folder.get("entityId")
    return None

def create_ardrive_folder(folder_name, parent_folder_id):
    existing_folder_id = get_existing_folder_id(folder_name, parent_folder_id)
    if existing_folder_id:
        return existing_folder_id

    command = [
        'ardrive', 'create-folder', '-F', parent_folder_id, '-n', folder_name, '-w', wallet_file, '--turbo'
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error creating folder: {result.stderr}")
        sys.exit(1)
    try:
        folder_data = json.loads(result.stdout)
        if 'created' in folder_data and len(folder_data['created']) > 0:
            return folder_data['created'][0]['entityId']
        else:
            print("Unexpected output format: 'entityId' not found in 'created' list.")
            print(f"Output: {result.stdout}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        print(f"Output: {result.stdout}")
        sys.exit(1)

def upload_file_to_ardrive(local_path, parent_folder_id, dest_file_name, log_writer):
    command = [
        'ardrive', 'upload-file', '--local-path', local_path, '-F', parent_folder_id, '-d', dest_file_name, '-w', wallet_file, '--upsert', '--turbo'
    ]
    for attempt in range(5):
        print(f"Executing command: {' '.join(command)}")  # Print the command
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            file_data = json.loads(result.stdout)
            file_id = file_data['created'][0]['entityId']
            log_writer.writerow([file_id, dest_file_name, parent_folder_id])
            return
        else:
            print(f"Attempt {attempt+1} failed: {result.stderr}")
    log_writer.writerow(['Failed', dest_file_name, parent_folder_id])
    sys.exit(f"Failed to upload {dest_file_name} after 5 attempts.")

def process_folder(folder_path, parent_folder_id, log_writer):
    folder_name = os.path.basename(folder_path)
    ardrive_folder_id = create_ardrive_folder(folder_name, parent_folder_id)

    for file_name in sorted(os.listdir(folder_path)):
        if file_name.startswith('.'):
            continue
        local_file_path = os.path.join(folder_path, file_name)
        upload_file_to_ardrive(local_file_path, ardrive_folder_id, file_name, log_writer)

def main(to_upload_path, uploaded_path, log_file_path):
    # Check if the log file already exists to decide whether to write headers
    log_file_exists = os.path.isfile(log_file_path)

    with open(log_file_path, 'a', newline='') as log_file:  # Changed 'w' to 'a' for append mode
        log_writer = csv.writer(log_file)

        # Write headers only if the file didn't exist before
        if not log_file_exists:
            log_writer.writerow(['File ID', 'File Name', 'Folder ID'])

        for folder_name in sorted(os.listdir(to_upload_path)):
            if folder_name.startswith('.'):
                continue
            folder_path = os.path.join(to_upload_path, folder_name)
            if os.path.isdir(folder_path):
                process_folder(folder_path, parent_folder_id, log_writer)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 uploader.py /path/to/to_upload /path/to/uploaded /path/to/uploader_log.csv")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
