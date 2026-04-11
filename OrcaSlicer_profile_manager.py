import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

class OrcaProfileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("OrcaSlicer Profile Manager")
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
        
        # --- Configure the Bold Tag for Machine Names ---
        self.tree.tag_configure("machine_bold", font=("Arial", 10, "bold"))
        
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

     # --- UPDATED: Smarter Matchmaker applied to BOTH filaments and processes ---
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
            
            # Fallback for machines
            current = profile_name
            while current:
                parent = self.profile_db[category].get(current, {}).get('inherits')
                if not parent or parent not in self.profile_db[category]:
                    return [current]
                current = parent
            return [profile_name]

        # THE FIX: Apply the exact same compatible_printers check to processes!
        elif category in ['filament', 'process']:
            current = profile_name
            printers = []
            
            #
            
            # 1. Trace up inheritance to find the compatible_printers array
            while current:
                if current in self.profile_db[category]:
                    printers = self.profile_db[category][current].get('compatible_printers', [])
                    if printers:
                        break
                    current = self.profile_db[category][current]['inherits']
                else:
                    break
                    
            # 2. If we found compatible printers, cross-reference them with the machine DB
            if printers:
                for p in printers:
                    # If the listed printer is an exact machine profile, grab its master 'printer_model'
                    if p in self.profile_db['machine']:
                        model = self.profile_db['machine'][p].get('printer_model')
                        families.add(model if model else p)
                    else:
                        families.add(p)
                return list(families)

        # Fallback for Process profiles or Filaments with empty compatible_printers arrays
        current = profile_name
        while current:
            if '@' in current:
                return [current.split('@')[-1].strip()]
            if current in self.profile_db[category]:
                current = self.profile_db[category][current]['inherits']
            else:
                break
        return ["Global / Unassigned"]
    # -----------------------------------------------------------------------------

    def render_inheritance_tree(self):
        user_main_node = self.tree.insert("", "end", text="User Profiles", open=True)
        system_main_node = self.tree.insert("", "end", text="System Profiles", open=False)

        def get_roots(is_user):
            roots = {cat: [] for cat in self.categories}
            for cat in self.categories:
                for name, data in self.profile_db[cat].items():
                    if data['is_user'] == is_user:
                        parent = data['inherits']
                        if not parent or parent not in self.profile_db[cat] or self.profile_db[cat][parent]['is_user'] != is_user:
                            roots[cat].append(name)
            return roots

        def group_by_family(roots_dict):
            family_map = {}
            for cat in self.categories:
                for name in roots_dict[cat]:
                    families = self.get_machine_families(cat, name)
                    for family in families:
                        if family not in family_map:
                            family_map[family] = {'machine': [], 'filament': [], 'process': []}
                        if name not in family_map[family][cat]:
                            family_map[family][cat].append(name)
            return family_map

        user_family_map = group_by_family(get_roots(is_user=True))
        system_family_map = group_by_family(get_roots(is_user=False))

        def draw_tree(main_node, family_map, is_user):
            for family in sorted(family_map.keys()):
                machines = family_map[family]['machine']
                filaments = family_map[family]['filament']
                processes = family_map[family]['process']

                if machines:
                    for machine_name in sorted(machines):
                        # --- ADDED: tags=("machine_bold",) ---
                        machine_node = self._draw_node(main_node, machine_name, 'machine', is_user, prefix="🖨️ ", tags=("machine_bold",))
                        
                        if filaments:
                            fil_group = self.tree.insert(machine_node, "end", text="🧶 Filaments", open=is_user)
                            for fil_name in sorted(filaments):
                                self._draw_node(fil_group, fil_name, 'filament', is_user, prefix="")
                        if processes:
                            proc_group = self.tree.insert(machine_node, "end", text="⚙️ Processes", open=is_user)
                            for proc_name in sorted(processes):
                                self._draw_node(proc_group, proc_name, 'process', is_user, prefix="")
                else:
                    # --- ADDED: tags=("machine_bold",) ---
                    family_node = self.tree.insert(main_node, "end", text=f"🤖 [System Base: {family}]", open=is_user, tags=("machine_bold",))
                    if filaments:
                        fil_group = self.tree.insert(family_node, "end", text="🧶 Filaments", open=is_user)
                        for fil_name in sorted(filaments):
                            self._draw_node(fil_group, fil_name, 'filament', is_user, prefix="")
                    if processes:
                        proc_group = self.tree.insert(family_node, "end", text="⚙️ Processes", open=is_user)
                        for proc_name in sorted(processes):
                            self._draw_node(proc_group, proc_name, 'process', is_user, prefix="")

        draw_tree(user_main_node, user_family_map, is_user=True)
        draw_tree(system_main_node, system_family_map, is_user=False)

    # --- ADDED: tags=() parameter ---
    def _draw_node(self, parent_node, profile_name, category, is_user, prefix="", tags=()):
        data = self.profile_db[category][profile_name]
        children = [c for c in data['children'] if self.profile_db[category][c]['is_user'] == is_user]
        
        display_text = f"{prefix}{data['display_name']}"
        # Apply the tag to the node
        node_id = self.tree.insert(parent_node, "end", text=display_text, values=[data['path']], open=is_user, tags=tags)
        
        for child_name in sorted(children):
            # Pass empty tags to children so they stay normal weight
            self._draw_node(node_id, child_name, category, is_user, prefix="", tags=())
            
        return node_id

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