import requests
import csv

# --- CONFIGURATION ---
API_KEY = "24532c89-c38b-4171-b0a7-e812b13f8905"
URL = "https://api.hevyapp.com/v1/exercise_templates"
HEADERS = {"api-key": API_KEY}
FILENAME = "hevy_exercises.csv"

def fetch_and_save_exercises():
    exercises = []
    page = 1
    page_size = 100 

    print(f"Connecting to Hevy API...")

    while True:
        try:
            response = requests.get(URL, headers=HEADERS, params={"page": page, "page_size": page_size})
            
            # Check for 404 specifically (End of List)
            if response.status_code == 404:
                print("  - Reached end of library.")
                break
                
            response.raise_for_status()
            
            data = response.json()
            page_data = data.get('exercise_templates', [])

            if not page_data:
                break 
            
            exercises.extend(page_data)
            print(f"  - Page {page}: Found {len(page_data)} exercises")
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"\nStopped due to unexpected error: {e}")
            break # Break so we still save what we found!

    # Write to CSV
    if exercises:
        fieldnames = ['title', 'primary_muscle_group', 'equipment', 'secondary_muscle_groups', 'id', 'type']

        with open(FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for ex in exercises:
                if 'secondary_muscle_groups' in ex and ex['secondary_muscle_groups']:
                    ex['secondary_muscle_groups'] = ", ".join(ex['secondary_muscle_groups'])
                writer.writerow(ex)

        print(f"\nSuccess! Saved {len(exercises)} exercises to '{FILENAME}'.")

if __name__ == "__main__":
    fetch_and_save_exercises()