import os
import json
import tkinter as tk
import platform
from tkinter import ttk, messagebox, simpledialog

class OrcaProfileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("OrcaSlicer Profile Manager")
        self.root.geometry("1100x700")

        # --- CROSS-PLATFORM PATH RESOLUTION ---
        sys_os = platform.system()
        if sys_os == "Windows":
            self.base_dir = os.path.join(os.getenv('APPDATA'), "OrcaSlicer")
        elif sys_os == "Darwin":  # macOS
            self.base_dir = os.path.expanduser("~/Library/Application Support/OrcaSlicer")
        else:  # Linux
            self.base_dir = os.path.expanduser("~/.config/OrcaSlicer")

        self.user_dir = os.path.join(self.base_dir, "user", "default")
        self.system_dir = os.path.join(self.base_dir, "system")
        # --------------------------------------
        
        self.categories = ["machine", "filament", "process"]
        self.profile_db = {cat: {} for cat in self.categories}
        self.original_text = "" 
        
        self.setup_ui()
        self.build_database()
        self.render_inheritance_tree()

    def setup_ui(self):
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === Left Panel ===
        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame, weight=1) 

        header_frame = tk.Frame(left_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(header_frame, text="Profile Explorer", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        reload_btn = tk.Button(header_frame, text="↻ Reload", command=self.reload_profiles, font=("Arial", 9), cursor="hand2")
        reload_btn.pack(side=tk.RIGHT)
        
        footer_frame = tk.Frame(left_frame)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.delete_btn = tk.Button(footer_frame, text="🗑️ Delete Selected", command=self.delete_profile, fg="red", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.delete_btn.pack(side=tk.RIGHT)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        self.tree.tag_configure("machine_bold", font=("Arial", 10, "bold"))
        self.tree.bind("<<TreeviewSelect>>", self.on_profile_select)

        # === Right Panel ===
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=3) 

        self.file_label = tk.Label(right_frame, text="Select a profile to edit", font=("Arial", 10, "italic"), fg="gray")
        self.file_label.pack(anchor="w")
        
        # --- ENABLE UNDO IN TEXT EDITOR ---
        self.text_editor = tk.Text(right_frame, wrap=tk.NONE, font=("Consolas", 10), undo=True)
        self.text_editor.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.text_editor.bind("<Return>", self.auto_indent)
        self.text_editor.bind("<KeyRelease>", self.check_modifications)

        # --- Button Frame ---
        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(pady=5)

        self.save_btn = tk.Button(btn_frame, text="Save Changes to JSON", command=self.save_profile, bg="lightgray", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.flatten_btn = tk.Button(btn_frame, text="⏬ Flatten", command=self.flatten_profile, fg="white", bg="orange", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.flatten_btn.pack(side=tk.LEFT, padx=5)

        self.duplicate_btn = tk.Button(btn_frame, text="📑 Duplicate", command=self.duplicate_profile, bg="lightblue", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.duplicate_btn.pack(side=tk.LEFT, padx=5)
        
        self.current_file_path = ""

    def check_modifications(self, event=None):
        if not self.current_file_path:
            return
        current_text = self.text_editor.get("1.0", "end-1c")
        if current_text != self.original_text:
            self.save_btn.config(state=tk.NORMAL, bg="lightgreen", cursor="hand2")
        else:
            self.save_btn.config(state=tk.DISABLED, bg="lightgray", cursor="arrow")

    def auto_indent(self, event):
        cursor_pos = self.text_editor.index(tk.INSERT)
        line_start = f"{cursor_pos.split('.')[0]}.0"
        current_line_text = self.text_editor.get(line_start, cursor_pos)
        
        indent_chars = ""
        for char in current_line_text:
            if char in (' ', '\t'):
                indent_chars += char
            else:
                break
                
        self.text_editor.insert(tk.INSERT, "\n" + indent_chars)
        self.check_modifications()
        return "break"

    def delete_profile(self):
        if not self.current_file_path or not self.current_file_path.startswith(self.user_dir):
            return
            
        profile_name = os.path.basename(self.current_file_path)
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete:\n\n{profile_name}\n\nThis action cannot be undone.", icon='warning')
        
        if confirm:
            try:
                os.remove(self.current_file_path)
                messagebox.showinfo("Success", f"'{profile_name}' has been deleted.")
                self.reload_profiles() 
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete the profile.\n\n{e}")

    def flatten_profile(self):
        if not self.current_file_path or self.flatten_btn['state'] == tk.DISABLED:
            return

        try:
            current_data = json.loads(self.text_editor.get("1.0", tk.END))

            if "inherits" not in current_data or not current_data["inherits"]:
                messagebox.showinfo("Info", "This profile does not inherit anything. It is already fully flattened!")
                return

            confirm = messagebox.askyesno(
                "Confirm Flatten",
                "Flattening will merge all parent settings into this file and permanently break the inheritance link.\n\nThis means if the base profile receives bug fixes in a future OrcaSlicer update, this profile will NOT receive them.\n\nDo you want to continue?",
                icon='warning'
            )
            
            if not confirm:
                return

            category = None
            for cat in self.categories:
                if f"\\{cat}\\" in self.current_file_path or f"/{cat}/" in self.current_file_path or self.current_file_path.endswith(f"{cat}"):
                    category = cat
                    break

            if not category:
                return

            chain = []
            current_inherits = current_data["inherits"]

            while current_inherits:
                if current_inherits in self.profile_db[category]:
                    parent_path = self.profile_db[category][current_inherits]['path']
                    try:
                        with open(parent_path, 'r', encoding='utf-8') as f:
                            parent_data = json.load(f)
                            chain.append(parent_data)
                            current_inherits = parent_data.get("inherits")
                    except Exception:
                        messagebox.showerror("Error", f"Failed to read parent profile:\n{current_inherits}")
                        return
                else:
                    messagebox.showwarning("Incomplete Chain", f"Could not find parent profile '{current_inherits}'. The flattened profile may be missing base settings.")
                    break

            flattened_data = {}
            for parent_data in reversed(chain):
                flattened_data.update(parent_data)

            flattened_data.update(current_data)

            if "inherits" in flattened_data:
                del flattened_data["inherits"]

            formatted_json = json.dumps(flattened_data, indent=4)
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(tk.END, formatted_json)

            self.check_modifications()
            messagebox.showinfo("Success", "Profile flattened in the editor!\n\nReview the settings, then click 'Save Changes to JSON' to finalize it.")

        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON formatting in the editor. Please fix any syntax errors before flattening.")

    def duplicate_profile(self):
        if not self.current_file_path or self.duplicate_btn['state'] == tk.DISABLED:
            return

        try:
            current_data = json.loads(self.text_editor.get("1.0", tk.END))
            
            category = None
            for cat in self.categories:
                if f"\\{cat}\\" in self.current_file_path or f"/{cat}/" in self.current_file_path or self.current_file_path.endswith(f"{cat}"):
                    category = cat
                    break

            if not category:
                messagebox.showerror("Error", "Could not determine the profile category.")
                return

            current_name = current_data.get('name', 'New_Profile')
            
            new_name = simpledialog.askstring(
                "Duplicate Profile", 
                "Enter a new name for this profile:", 
                initialvalue=f"{current_name} (Copy)"
            )
            
            if not new_name:
                return 

            safe_filename = "".join([c for c in new_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.', '@')]).rstrip()
            if not safe_filename:
                safe_filename = "Duplicated_Profile"

            new_filepath = os.path.join(self.user_dir, category, f"{safe_filename}.json")

            if os.path.exists(new_filepath):
                messagebox.showerror("Error", f"A profile named '{safe_filename}' already exists!")
                return

            current_data['name'] = new_name
            
            if 'setting_id' in current_data:
                current_data['setting_id'] = new_name
                
            if 'settings_id' in current_data:
                current_data['settings_id'] = new_name

            os.makedirs(os.path.dirname(new_filepath), exist_ok=True)

            with open(new_filepath, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=4)

            messagebox.showinfo("Success", f"Profile duplicated successfully as '{new_name}'!")
            self.reload_profiles()

        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON formatting in the editor. Please fix any syntax errors before duplicating.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to duplicate profile:\n{e}")

    def reload_profiles(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.text_editor.delete(1.0, tk.END)
        self.file_label.config(text="Select a profile to edit", fg="gray")
        self.current_file_path = ""
        self.original_text = ""
        
        self.save_btn.config(state=tk.DISABLED, bg="lightgray", cursor="arrow")
        self.delete_btn.config(state=tk.DISABLED, cursor="arrow")
        self.flatten_btn.config(state=tk.DISABLED, cursor="arrow")
        self.duplicate_btn.config(state=tk.DISABLED, cursor="arrow") 
        
        self.profile_db = {cat: {} for cat in self.categories}
        self.build_database()
        self.render_inheritance_tree()

    def build_database(self):
        if os.path.exists(self.system_dir):
            self._scan_directory(self.system_dir, is_user=False)
        if os.path.exists(self.user_dir):
            self._scan_directory(self.user_dir, is_user=True)
            
        for category in self.categories:
            for name, data in self.profile_db[category].items():
                parent_name = data['inherits']
                if parent_name and parent_name in self.profile_db[category]:
                    self.profile_db[category][parent_name]['children'].append(name)

    def _scan_directory(self, base_path, is_user):
        for root, dirs, files in os.walk(base_path):
            category = None
            for cat in self.categories:
                if f"\\{cat}" in root or f"/{cat}" in root:
                    category = cat
                    break
                    
            if not category:
                continue

            for file in files:
                if file.endswith(".json"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        profile_name = data.get('name', file.replace('.json', ''))
                        inherits = data.get('inherits', None)
                        
                        printer_model = data.get('printer_model', None)
                        if isinstance(printer_model, list):
                            printer_model = printer_model[0] if printer_model else None

                        compatible_printers = data.get('compatible_printers', [])
                        if not isinstance(compatible_printers, list):
                            compatible_printers = [compatible_printers]

                        self.profile_db[category][profile_name] = {
                            'path': filepath,
                            'inherits': inherits,
                            'children': [],
                            'is_user': is_user,
                            'display_name': profile_name,
                            'printer_model': printer_model,
                            'compatible_printers': compatible_printers
                        }
                    except Exception:
                        pass 

    def get_machine_families(self, category, profile_name):
        families = set()
        
        if category == 'machine':
            current = profile_name
            while current:
                if current in self.profile_db[category]:
                    model = self.profile_db[category][current].get('printer_model')
                    if model: return [model]
                    current = self.profile_db[category][current]['inherits']
                else:
                    break
            
            current
