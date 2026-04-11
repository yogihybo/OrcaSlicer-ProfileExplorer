import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

class OrcaProfileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("OrcaSlicer Inheritance Tree Manager")
        self.root.geometry("1100x700")

        self.appdata = os.getenv('APPDATA')
        self.user_dir = os.path.join(self.appdata, "OrcaSlicer", "user", "default")
        self.system_dir = os.path.join(self.appdata, "OrcaSlicer", "system")
        
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
        
        self.delete_btn = tk.Button(footer_frame, text="🗑️ Delete Selected Profile", command=self.delete_profile, fg="red", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.delete_btn.pack(side=tk.RIGHT)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self.on_profile_select)

        # === Right Panel ===
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=3) 

        self.file_label = tk.Label(right_frame, text="Select a profile to edit", font=("Arial", 10, "italic"), fg="gray")
        self.file_label.pack(anchor="w")
        
        self.text_editor = tk.Text(right_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.text_editor.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.text_editor.bind("<Return>", self.auto_indent)
        self.text_editor.bind("<KeyRelease>", self.check_modifications)

        self.save_btn = tk.Button(right_frame, text="Save Changes to JSON", command=self.save_profile, bg="lightgray", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.save_btn.pack(pady=5)
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

    def reload_profiles(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.text_editor.delete(1.0, tk.END)
        self.file_label.config(text="Select a profile to edit", fg="gray")
        self.current_file_path = ""
        self.original_text = ""
        
        self.save_btn.config(state=tk.DISABLED, bg="lightgray", cursor="arrow")
        self.delete_btn.config(state=tk.DISABLED, cursor="arrow")
        
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
                        
                        # --- NEW: Extract Printer Model for Machine matching ---
                        printer_model = data.get('printer_model', None)
                        if isinstance(printer_model, list):
                            printer_model = printer_model[0] if printer_model else None
                        # -----------------------------------------------------

                        self.profile_db[category][profile_name] = {
                            'path': filepath,
                            'inherits': inherits,
                            'children': [],
                            'is_user': is_user,
                            'display_name': profile_name,
                            'printer_model': printer_model
                        }
                    except Exception:
                        pass 

    # --- NEW: The Matchmaker Helper Function ---
    def get_machine_family(self, category, profile_name):
        """Traces the inheritance chain to figure out which Printer Model a profile belongs to."""
        if category == 'machine':
            current = profile_name
            while current:
                if current in self.profile_db[category]:
                    model = self.profile_db[category][current].get('printer_model')
                    if model: return model
                    current = self.profile_db[category][current]['inherits']
                else:
                    break
            
            # Fallback: Absolute Root Machine Name
            current = profile_name
            while current:
                parent = self.profile_db[category].get(current, {}).get('inherits')
                if not parent or parent not in self.profile_db[category]:
                    return current
                current = parent
            return profile_name

        else: 
            # For filaments & processes, trace up to find the @ symbol from the system profile
            current = profile_name
            while current:
                if '@' in current:
                    return current.split('@')[-1].strip()
                if current in self.profile_db[category]:
                    current = self.profile_db[category][current]['inherits']
                else:
                    break
            return "Global / Unassigned"
    # -------------------------------------------

    def render_inheritance_tree(self):
        """Draws the Tree grouped purely by Machine Type."""
        user_main_node = self.tree.insert("", "end", text="User Profiles", open=True)
        system_main_node = self.tree.insert("", "end", text="System Profiles", open=False)

        # === 1. Gather & Group User Profiles ===
        user_roots = {cat: [] for cat in self.categories}
        for cat in self.categories:
            for name, data in self.profile_db[cat].items():
                if data['is_user']:
                    parent = data['inherits']
                    # It's a User Root if it has no parent, or its parent is a System profile
                    if not parent or parent not in self.profile_db[cat] or not self.profile_db[cat][parent]['is_user']:
                        user_roots[cat].append(name)

        user_tree_data = {}
        for cat in self.categories:
            for root_name in user_roots[cat]:
                family = self.get_machine_family(cat, root_name)
                if family not in user_tree_data:
                    user_tree_data[family] = {'machine': [], 'filament': [], 'process': []}
                user_tree_data[family][cat].append(root_name)

        # Draw User Profiles 
        for family in sorted(user_tree_data.keys()):
            family_node = self.tree.insert(user_main_node, "end", text=f"🤖 {family}", open=True)
            for cat in self.categories:
                if user_tree_data[family][cat]:
                    cat_node = self.tree.insert(family_node, "end", text=cat.capitalize(), open=True)
                    for root_name in sorted(user_tree_data[family][cat]):
                        self._draw_user_node(cat_node, root_name, cat)

        # === 2. Gather & Group System Profiles ===
        system_roots = {cat: [] for cat in self.categories}
        for cat in self.categories:
            for name, data in self.profile_db[cat].items():
                if not data['is_user']:
                    parent = data['inherits']
                    if not parent or parent not in self.profile_db[cat]:
                        system_roots[cat].append(name)

        system_tree_data = {}
        for cat in self.categories:
            for root_name in system_roots[cat]:
                family = self.get_machine_family(cat, root_name)
                if family not in system_tree_data:
                    system_tree_data[family] = {'machine': [], 'filament': [], 'process': []}
                system_tree_data[family][cat].append(root_name)

        # Draw System Profiles
        for family in sorted(system_tree_data.keys()):
            family_node = self.tree.insert(system_main_node, "end", text=f"🤖 {family}", open=False)
            for cat in self.categories:
                if system_tree_data[family][cat]:
                    cat_node = self.tree.insert(family_node, "end", text=cat.capitalize(), open=False)
                    for root_name in sorted(system_tree_data[family][cat]):
                        self._draw_system_node(cat_node, root_name, cat)

    def _draw_system_node(self, parent_node, profile_name, category):
        data = self.profile_db[category][profile_name]
        sys_children = [c for c in data['children'] if not self.profile_db[category][c]['is_user']]
        node_id = self.tree.insert(parent_node, "end", text=data['display_name'], values=[data['path']], open=False)
        for child_name in sorted(sys_children):
            self._draw_system_node(node_id, child_name, category)

    def _draw_user_node(self, parent_node, profile_name, category):
        data = self.profile_db[category][profile_name]
        user_children = [c for c in data['children'] if self.profile_db[category][c]['is_user']]
        node_id = self.tree.insert(parent_node, "end", text=data['display_name'], values=[data['path']], open=True)
        for child_name in sorted(user_children):
            self._draw_user_node(node_id, child_name, category)

    def on_profile_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item_data = self.tree.item(selection[0])
        
        if item_data['values']:
            self.current_file_path = item_data['values'][0]
            self.file_label.config(text=self.current_file_path, fg="black")
            
            if self.current_file_path.startswith(self.user_dir):
                self.delete_btn.config(state=tk.NORMAL, cursor="hand2")
            else:
                self.delete_btn.config(state=tk.DISABLED, cursor="arrow")
            
            with open(self.current_file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    formatted_json = json.dumps(data, indent=4)
                    
                    self.text_editor.delete(1.0, tk.END)
                    self.text_editor.insert(tk.END, formatted_json)
                    
                    self.original_text = formatted_json
                    self.check_modifications()
                    
                except json.JSONDecodeError:
                    messagebox.showerror("Error", f"Invalid JSON format in:\n{self.current_file_path}")
        else:
            self.delete_btn.config(state=tk.DISABLED, cursor="arrow")
            self.save_btn.config(state=tk.DISABLED, bg="lightgray", cursor="arrow")
            self.current_file_path = ""
            self.original_text = ""

    def save_profile(self):
        if not self.current_file_path or self.save_btn['state'] == tk.DISABLED:
            return
            
        try:
            current_text = self.text_editor.get("1.0", tk.END)
            new_data = json.loads(current_text)
            
            category = None
            for cat in self.categories:
                if f"\\{cat}\\" in self.current_file_path or f"/{cat}/" in self.current_file_path or self.current_file_path.endswith(f"{cat}"):
                    category = cat
                    break
                    
            if category and "inherits" in new_data:
                parent_name = new_data["inherits"]
                if parent_name and parent_name not in self.profile_db[category]:
                    messagebox.showerror("Validation Error", f"Save Blocked!\n\nThe parent profile '{parent_name}' does not exist in the System Base or User database.\n\nOrcaSlicer will crash or ignore this profile if the inheritance chain is broken. Please check your spelling.")
                    return
            
            with open(self.current_file_path, 'w', encoding='utf-8') as file:
                json.dump(new_data, file, indent=4)
            messagebox.showinfo("Success", "Profile successfully updated!")
            
            self.original_text = self.text_editor.get("1.0", "end-1c")
            self.check_modifications()
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON. Please fix formatting before saving.")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrcaProfileManager(root)
    root.mainloop()