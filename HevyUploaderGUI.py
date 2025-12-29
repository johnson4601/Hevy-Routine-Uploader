import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import requests
import json
import os
import sys
import threading
import csv
from pathlib import Path

# --- Configuration for Saving API Key ---
CONFIG_FILE = Path.home() / ".hevy_uploader_config.json"
BASE_URL = "https://api.hevyapp.com/v1"

# --- DEFAULT INSTRUCTIONS (Backup if README.md is missing) ---
DEFAULT_README = """
Welcome to the Hevy Routine Manager!

STEP 1: GET YOUR API KEY
1. Open the Hevy App on your phone.
2. Go to Settings -> API.
3. Generate a new key and copy it.
4. Paste it into this app when asked.

STEP 2: UPLOAD WORKOUTS
1. Ask Gemini to generate a workout routine in JSON format.
2. Copy the code block provided by Gemini.
3. Paste it into the big text box here.
4. Enter a Folder Name (e.g., "Summer Shred").
5. Click "UPLOAD ROUTINES".

STEP 3: DOWNLOAD EXERCISE LIST
1. Click "DOWNLOAD EXERCISE LIST".
2. Choose where to save the .csv file.
3. Use this file to see which exercises are available for Gemini to use.

TROUBLESHOOTING
- If the app crashes, check your internet connection.
- If the API Key is wrong, click "Reset / Clear Saved Key" at the bottom.
"""

class HevyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hevy Routine Manager")
        self.root.geometry("600x700") # Made taller for the new button
        
        self.saved_data = self.load_config()

        # --- UI Elements ---
        
        # 1. API Key Input
        tk.Label(root, text="Hevy API Key:", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.entry_api = tk.Entry(root, width=60, show="*") 
        self.entry_api.pack(pady=5)
        if "api_key" in self.saved_data:
            self.entry_api.insert(0, self.saved_data["api_key"])

        # 2. Folder Name Input
        tk.Label(root, text="Training Block Name (Folder):", font=("Arial", 10)).pack(pady=(10, 5))
        self.entry_folder = tk.Entry(root, width=60)
        self.entry_folder.insert(0, self.saved_data.get("folder_name", "Gemini Workouts"))
        self.entry_folder.pack(pady=5)

        # 3. JSON Paste Area
        tk.Label(root, text="Paste JSON from Gemini below:", font=("Arial", 10)).pack(pady=(15, 5))
        self.text_area = scrolledtext.ScrolledText(root, width=70, height=12)
        self.text_area.pack(pady=5)

        # --- BUTTONS FRAME ---
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)

        # 4. Upload Button
        self.btn_upload = tk.Button(btn_frame, text="UPLOAD ROUTINES", bg="#2196F3", fg="white", 
                                    font=("Arial", 11, "bold"), width=20, command=self.start_upload_thread)
        self.btn_upload.grid(row=0, column=0, padx=5)

        # 5. Download Button
        self.btn_download = tk.Button(btn_frame, text="DOWNLOAD EXERCISE LIST", bg="#4CAF50", fg="white", 
                                    font=("Arial", 11, "bold"), width=25, command=self.start_download_thread)
        self.btn_download.grid(row=0, column=1, padx=5)

        # 6. Help / Readme Button (NEW)
        self.btn_help = tk.Button(root, text="❓ Instructions / Read Me", font=("Arial", 9, "bold"), 
                                  bg="#FFC107", fg="black", command=self.show_readme)
        self.btn_help.pack(pady=5)

        # 7. Reset Button
        self.btn_reset = tk.Button(root, text="Reset / Clear Saved Key", font=("Arial", 8), 
                                   fg="red", command=self.clear_config)
        self.btn_reset.pack(pady=5)

        # 8. Status Label
        self.status_label = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # --- NEW: README DISPLAY LOGIC ---
    def show_readme(self):
        """Displays README.md content or internal default text in a popup"""
        readme_content = DEFAULT_README
        
        # Try to find a real README.md file next to the executable/script
        if getattr(sys, 'frozen', False):
            # If running as compiled exe
            app_path = Path(sys.executable).parent
        else:
            # If running as python script
            app_path = Path(__file__).parent
            
        readme_path = app_path / "README.md"

        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read()
            except Exception as e:
                readme_content += f"\n\n(Error reading external README file: {e})"

        # Create Popup Window
        help_window = tk.Toplevel(self.root)
        help_window.title("Instructions")
        help_window.geometry("500x500")

        # Text Widget for Readme
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("Consolas", 10))
        text_widget.pack(expand=True, fill='both', padx=10, pady=10)
        
        text_widget.insert("1.0", readme_content)
        text_widget.config(state=tk.DISABLED) # Make it read-only
        
        # Close Button
        tk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=5)

    # --- Config Methods ---
    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self, api_key, folder_name):
        data = {"api_key": api_key, "folder_name": folder_name}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def clear_config(self):
        check1 = messagebox.askyesno("Hold Up!", "Are you sure you want to delete your saved API Key?")
        if not check1: return
        check2 = messagebox.askyesno("Wait...", "You know that key is super long, right?\n\nDo you really want to have to find it and copy-paste it again?")
        if not check2: return
        check3 = messagebox.askyesno("Last Chance", "Okay, brave soul. This is it.\n\nNuke the credentials?")
        if not check3: return

        if CONFIG_FILE.exists():
            os.remove(CONFIG_FILE)
        
        self.entry_api.delete(0, tk.END)
        self.entry_folder.delete(0, tk.END)
        self.entry_folder.insert(0, "Gemini Workouts")
        messagebox.showinfo("Reset Complete", "It's gone. I hope you have the new one handy!")
        self.log("Configuration cleared.")

    def log(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

    # --- UPLOAD Logic ---
    def start_upload_thread(self):
        self.btn_upload.config(state=tk.DISABLED, text="Uploading...")
        thread = threading.Thread(target=self.run_upload_process)
        thread.start()

    def run_upload_process(self):
        api_key = self.entry_api.get().strip()
        folder_name = self.entry_folder.get().strip()
        json_input = self.text_area.get("1.0", tk.END).strip()

        if not api_key:
            messagebox.showerror("Error", "Please enter your API Key.")
            self.reset_buttons()
            return
        if not json_input:
            messagebox.showerror("Error", "Please paste the JSON code.")
            self.reset_buttons()
            return

        self.save_config(api_key, folder_name)
        headers = {"api-key": api_key, "Content-Type": "application/json"}

        try:
            try:
                routines = json.loads(json_input)
                if not isinstance(routines, list):
                    routines = [routines]
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON. Copy exactly from Gemini.")
                self.reset_buttons()
                return

            self.log(f"Checking for folder: {folder_name}...")
            folder_id = self.get_or_create_folder(headers, folder_name)

            total = len(routines)
            for i, routine in enumerate(routines):
                self.log(f"Uploading {i+1}/{total}: {routine['routine']['title']}...")
                self.create_routine(headers, routine, folder_id)
            
            self.log("Done!")
            self.text_area.delete("1.0", tk.END) 
            messagebox.showinfo("Success", f"Uploaded {total} routines!")

        except Exception as e:
            self.log("Error occurred.")
            messagebox.showerror("Error", str(e))
        
        self.reset_buttons()

    def get_or_create_folder(self, headers, folder_name):
        res = requests.get(f"{BASE_URL}/routine_folders", headers=headers)
        if res.status_code == 401:
            raise Exception("Invalid API Key.")
        res.raise_for_status()
        folders = res.json().get("routine_folders", [])
        for f in folders:
            if f["title"] == folder_name:
                return f["id"]
        payload = {"routine_folder": {"title": folder_name}}
        res = requests.post(f"{BASE_URL}/routine_folders", headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["routine_folder"]["id"]

    def create_routine(self, headers, payload, folder_id):
        payload["routine"]["folder_id"] = folder_id
        res = requests.post(f"{BASE_URL}/routines", headers=headers, json=payload)
        res.raise_for_status()

    # --- DOWNLOAD Logic ---
    def start_download_thread(self):
        api_key = self.entry_api.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your API Key first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Exercise List As"
        )
        if not file_path: return 

        self.btn_download.config(state=tk.DISABLED, text="Downloading...")
        thread = threading.Thread(target=self.run_download_process, args=(api_key, file_path))
        thread.start()

    def run_download_process(self, api_key, file_path):
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        page = 1
        page_count = 1
        all_exercises = []

        try:
            self.log("Connecting to Hevy API...")
            while page <= page_count:
                self.log(f"Fetching page {page}...")
                response = requests.get(f"{BASE_URL}/exercise_templates", headers=headers, params={"page": page, "pageSize": 50})
                if response.status_code == 401: raise Exception("Invalid API Key.")
                response.raise_for_status()
                data = response.json()
                page_count = data.get("page_count", 1)
                all_exercises.extend(data.get("exercise_templates", []))
                page += 1

            self.log(f"Saving {len(all_exercises)} exercises to CSV...")
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["title", "primary_muscle_group", "equipment", "secondary_muscle_groups", "id", "type"])
                for ex in all_exercises:
                    writer.writerow([
                        ex.get("title", "Unknown"),
                        ex.get("primary_muscle_group", ""),
                        ex.get("equipment", ""),
                        ", ".join(ex.get("secondary_muscle_groups", [])),
                        ex.get("id", ""),
                        ex.get("type", "")
                    ])
            self.log("Download Complete!")
            messagebox.showinfo("Success", f"Saved {len(all_exercises)} exercises!")

        except Exception as e:
            self.log("Download Error.")
            messagebox.showerror("Error", str(e))
        self.reset_buttons()

    def reset_buttons(self):
        self.btn_upload.config(state=tk.NORMAL, text="UPLOAD ROUTINES")
        self.btn_download.config(state=tk.NORMAL, text="DOWNLOAD EXERCISE LIST")

if __name__ == "__main__":
    root = tk.Tk()
    app = HevyApp(root)
    root.mainloop()