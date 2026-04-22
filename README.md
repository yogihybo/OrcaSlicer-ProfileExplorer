# OrcaSlicer Profile Explorer
A standalone Python GUI tool for managing, editing, and flattening OrcaSlicer profiles. 

run using:

```
python OrcaSlicer_profile_manager.py
```

OrcaSlicer relies on a complex inheritance system where user profiles are linked to base system profiles. This tool provides a clear, visual hierarchy of your printers, filaments, and processes, allowing you to edit the raw JSON safely without breaking inheritance chains.

## Features
* **Smart Machine Grouping:** Intelligently reads `compatible_printers` arrays to group your custom filaments and processes under their respective machine profiles.
* **Profile Flattening:** Sever the inheritance link to base system files by baking all parent/grandparent settings directly into your custom profile. 
* **Safe Duplication:** Safely clone profiles while automatically updating internal `setting_id` tags and sanitizing filenames.
* **Built-in Editor:** Edit the raw JSON with smart auto-indentation and real-time validation to prevent breaking the slicer.

## Requirements
This script uses standard Python libraries and requires no external dependencies.
* Python 3.x
* `tkinter` (Usually bundled with Python)

## How to Run
1. Clone the repository or download `OrcaManager.py`.
2. Run the script:
   ```bash
   python OrcaManager.py
   
<img width="1100" height="727" alt="image" src="https://github.com/user-attachments/assets/e66a9039-1284-49b6-9fe1-02a3d9443a2a" />
