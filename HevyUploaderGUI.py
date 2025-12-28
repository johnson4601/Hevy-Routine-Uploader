import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import requests
import json
import os
import threading
import csv
from pathlib import Path

# --- Configuration for Saving API Key ---
CONFIG_FILE = Path.home() / ".hevy_uploader_config.json"
BASE_URL = "https://api.hevyapp.com/v1"

class HevyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hevy Routine Manager")
        self.root.geometry("600x650") 
        
        # Load saved config if it exists
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
        self.btn_upload.grid(row=0, column=0, padx=10)

        # 5. Download Button
        self.btn_download = tk.Button(btn_frame, text="DOWNLOAD EXERCISE LIST", bg="#4CAF50", fg="white", 
                                    font=("Arial", 11, "bold"), width=25, command=self.start_download_thread)
        self.btn_download.grid(row=0, column=1, padx=10)

        # 6. Reset Button
        self.btn_reset = tk.Button(root, text="Reset / Clear Saved Key", font=("Arial", 8), 
                                   fg="red", command=self.clear_config)
        self.btn_reset.pack(pady=5)

        # 7. Status Label
        self.status_label = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

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
        # Check 1: The Standard Warning
        check1 = messagebox.askyesno("Hold Up!", "Are you sure you want to delete your saved API Key?")
        if not check1:
            return

        # Check 2: The Practicality Check
        check2 = messagebox.askyesno("Wait...", "You know that key is super long, right?\n\nDo you really want to have to find it and copy-paste it again?")
        if not check2:
            return

        # Check 3: The Final Warning
        check3 = messagebox.askyesno("Last Chance", "Okay, brave soul. This is it.\n\nNuke the credentials?")
        if not check3:
            return

        # If they survived the gauntlet, delete the file
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
            
            # --- SUCCESS! ---
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
        
        if not file_path:
            return 

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
                
                if response.status_code == 401:
                    raise Exception("Invalid API Key.")
                response.raise_for_status()
                
                data = response.json()
                page_count = data.get("page_count", 1)
                exercises = data.get("exercise_templates", [])
                all_exercises.extend(exercises)
                
                page += 1

            self.log(f"Saving {len(all_exercises)} exercises to CSV...")
            
            with open(file_path, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["title", "primary_muscle_group", "equipment", "secondary_muscle_groups", "id", "type"])
                
                for ex in all_exercises:
                    title = ex.get("title", "Unknown")
                    p_muscle = ex.get("primary_muscle_group", "")
                    equip = ex.get("equipment", "")
                    s_muscles = ", ".join(ex.get("secondary_muscle_groups", []))
                    ex_id = ex.get("id", "")
                    ex_type = ex.get("type", "")
                    
                    writer.writerow([title, p_muscle, equip, s_muscles, ex_id, ex_type])

            self.log("Download Complete!")
            messagebox.showinfo("Success", f"Successfully saved {len(all_exercises)} exercises to:\n{file_path}")

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