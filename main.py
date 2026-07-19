import requests
import csv
import os
import glob
import time

examCodePos = 4
examIdPos = 5

# Complete authentication and device signatures from your fetch request
headers = {
    "accept": "*/*",
    "accept-language": "pt-PT,pt;q=0.9,pt-BR;q=0.8,en;q=0.7,en-US;q=0.6,en-GB;q=0.5",
    "authorization": "Bearer XXXXXX-XXXXXXXX",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "x-maintenance-bypass": "XXXXXXXX-XXXXXXXXX",
    "referer": "https://exames.eduqa.pt/"
}

csv_file_path = "ListagemTodosOsExames.csv"
base_dir = "Listagem de Itens de Prova"

if not os.path.exists(csv_file_path):
    print(f"Error: {csv_file_path} not found.")
    exit(1)

print(f"Reading {csv_file_path} and downloading PDFs...")

with open(csv_file_path, mode='r', encoding='utf-8', errors='replace') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=';')
    
    for row_idx, row in enumerate(csv_reader):
        # Ensure row has enough columns
        if len(row) <= max(examCodePos - 1, examIdPos - 1):
            continue
            
        examCode = row[examCodePos - 1].strip()
        examId = row[examIdPos - 1].strip()
        
        # Check if the examCode has a value
        if not examCode:
            continue
            
        if not examId:
            print(f"[Row {row_idx}] Skipping: examCode '{examCode}' is present but examId is missing.")
            continue

        print(f"[Row {row_idx}] Processing Exam Code: {examCode}, Exam ID: {examId}")
        
        # Extract student number to find the destination directory on disk
        student_num = ""
        if len(row) > 1 and " - " in row[1]:
            student_num = row[1].split(" - ")[-1].strip()
            
        # Find directory matching the pattern "* - {student_num}" to handle characters like "?" properly
        folder_path = None
        if student_num:
            pattern = os.path.join(base_dir, f"* - {student_num}")
            matches = glob.glob(pattern)
            if matches:
                folder_path = matches[0]
                
        # Fallback if no matching folder is found on disk
        if not folder_path:
            clean_folder_name = row[1].replace("?", "").strip() if len(row) > 1 else f"Student_{student_num}"
            folder_path = os.path.join(base_dir, clean_folder_name)
            
        # Extract filename from column 3 (index 2) or use default
        filename = f"{examId}.pdf"
        
        dest_path = os.path.join(folder_path, filename)
        
        # Avoid redundant downloads if file is already present
        if os.path.exists(dest_path):
            print(f"  -> File already exists: {dest_path} (Skipping)")
            continue
            
        # Create directories if they do not exist
        os.makedirs(folder_path, exist_ok=True)
        
        # Construct endpoint URL and request query parameters
        url = f"https://zsyz93b2si.execute-api.eu-west-1.amazonaws.com/prd/portal/conventionals/{examId}/pdf-url"
        params = {
            "examCode": examCode,
            "idMapeamento": "58",
            "year": "2026",
            "phase": "1fase",
            "schoolCode": "1114081"
        }
        
        try:
            # Making the GET request
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    pdf_url = data.get("url") or data.get("pdfUrl") or data.get("data", {}).get("url")
                    
                    if pdf_url:
                        pdf_response = requests.get(pdf_url, timeout=20)
                        if pdf_response.status_code == 200:
                            with open(dest_path, "wb") as f:
                                f.write(pdf_response.content)
                            print(f"  -> Success! File saved: {dest_path}")
                        else:
                            print(f"  -> Failed to download PDF stream. Status: {pdf_response.status_code}")
                    else:
                        print("  -> Could not parse S3 download URL from JSON response.")
                except ValueError:
                    # Stream raw binary content
                    with open(dest_path, "wb") as f:
                        f.write(response.content)
                    print(f"  -> Success! File saved: {dest_path}")
            else:
                print(f"  -> Request failed with status code: {response.status_code}")
                print(f"  -> Error details: {response.text}")
                
        except Exception as e:
            print(f"  -> Error occurred: {e}")
            
        # Add a polite delay of 5s to respect API rate limits
        time.sleep(1)
