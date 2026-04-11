import os
import json
import tkinter as tk
from tkinter import ttk, messagebox

class OrcaProfileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("OrcaSlicer Inheritance Tree Manager")
        self.root.geometry("1100x700")

        # Define directory paths
        self.appdata = os.getenv('APPDATA')
        self.user_dir = os.path.join(self.appdata, "OrcaSlicer", "user", "default")
        self.system_dir = os.path.join(self.appdata, "OrcaSlicer", "system")
        
        self.categories = ["machine", "filament", "process"]
        
        # Initialize the databases and state tracking
        self.profile_db = {cat: {} for cat in self.categories}
        self.original_text = "" 
        
        self.setup_ui()
        self.build_database()
        self.render_inheritance_tree()

    def setup_ui(self):
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === Left Panel: Profile Trees ===
        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame, weight=1) 

        header_frame = tk.Frame(left_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(header_frame, text="Profile Explorer", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        reload_btn = tk.Button(header_frame, text="↻ Reload", command=self.reload_profiles, font=("Arial", 9), cursor="hand2")
        reload_btn.pack(side=tk.RIGHT)
        
        # Footer frame for the Delete Button
        footer_frame = tk.Frame(left_frame)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # NOTE: Delete button is now an instance variable and starts DISABLED
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

        # === Right Panel: Unified Editor ===
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=3) 

        self.file_label = tk.Label(right_frame, text="Select a profile to edit", font=("Arial", 10, "italic"), fg="gray")
        self.file_label.pack(anchor="w")
        
        self.text_editor = tk.Text(right_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.text_editor.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Bind keys for auto-indent and modification tracking
        self.text_editor.bind("<Return>", self.auto_indent)
        self.text_editor.bind("<KeyRelease>", self.check_modifications)

        # NOTE: Save button is now an instance variable and starts DISABLED
        self.save_btn = tk.Button(right_frame, text="Save Changes to JSON", command=self.save_profile, bg="lightgray", font=("Arial", 9, "bold"), state=tk.DISABLED)
        self.save_btn.pack(pady=5)
        
        self.current_file_path = ""

    # --- NEW: State Management Logic ---
    def check_modifications(self, event=None):
        """Checks if the text in the editor differs from the originally loaded file."""
        if not self.current_file_path:
            return
            
        # We use "end-1c" to ignore the automatic trailing newline tkinter adds
        current_text = self.text_editor.get("1.0", "end-1c")
        
        if current_text != self.original_text:
            self.save_btn.config(state=tk.NORMAL, bg="lightgreen", cursor="hand2")
        else:
            self.save_btn.config(state=tk.DISABLED, bg="lightgray", cursor="arrow")
    # -----------------------------------

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
        
        # Trigger modification check after auto-indent inserts new text
        self.check_modifications()
        return "break"

    def delete_profile(self):
        # Additional safety check just in case
        if not self.current_file_path or not self.current_file_path.startswith(self.user_dir):
            return
            
        profile_name = os.path.basename(self.current_file_path)
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete:\n\n{profile_name}\n\nThis action cannot be undone.",
            icon='warning'
        )
        
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
        
        # Reset buttons to disabled states
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
                        
                        self.profile_db[category][profile_name] = {
                            'path': filepath,
                            'inherits': inherits,
                            'children': [],
                            'is_user': is_user,
                            'display_name': profile_name
                        }
                    except Exception:
                        pass 

    def render_inheritance_tree(self):
        for category in self.categories:
            cat_node = self.tree.insert("", "end", text=category.capitalize(), open=True)
            
            user_root = self.tree.insert(cat_node, "end", text="User Profiles", open=True)
            system_root = self.tree.insert(cat_node, "end", text="System Profiles", open=False)

            sys_roots = []
            for name, data in self.profile_db[category].items():
                if not data['is_user']:
                    parent = data['inherits']
                    if not parent or parent not in self.profile_db[category]:
                        sys_roots.append(name)
                        
            for root_name in sorted(sys_roots):
                self._draw_system_node(system_root, root_name, category)

            user_roots = []
            for name, data in self.profile_db[category].items():
                if data['is_user']:
                    parent = data['inherits']
                    if not parent or parent not in self.profile_db[category] or not self.profile_db[category][parent]['is_user']:
                        user_roots.append(name)

            system_to_user_map = {}
            for u_root in user_roots:
                parent = self.profile_db[category][u_root]['inherits']
                parent_display = parent if parent else "No Parent (Orphaned)"
                
                if parent_display not in system_to_user_map:
                    system_to_user_map[parent_display] = []
                system_to_user_map[parent_display].append(u_root)

            for sys_parent in sorted(system_to_user_map.keys()):
                group_node = self.tree.insert(user_root, "end", text=f"[Parent: {sys_parent}]", open=True)
                for u_name in sorted(system_to_user_map[sys_parent]):
                    self._draw_user_node(group_node, u_name, category)

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
        
        # If they clicked an actual file, not a parent grouping folder
        if item_data['values']:
            self.current_file_path = item_data['values'][0]
            self.file_label.config(text=self.current_file_path, fg="black")
            
            # --- NEW: Delete Button Logic ---
            if self.current_file_path.startswith(self.user_dir):
                self.delete_btn.config(state=tk.NORMAL, cursor="hand2")
            else:
                self.delete_btn.config(state=tk.DISABLED, cursor="arrow")
            # --------------------------------
            
            with open(self.current_file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    formatted_json = json.dumps(data, indent=4)
                    
                    self.text_editor.delete(1.0, tk.END)
                    self.text_editor.insert(tk.END, formatted_json)
                    
                    # Store the baseline text and reset the save button
                    self.original_text = formatted_json
                    self.check_modifications()
                    
                except json.JSONDecodeError:
                    messagebox.showerror("Error", f"Invalid JSON format in:\n{self.current_file_path}")
        else:
            # They clicked a folder folder, disable both buttons to be safe
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
            
            with open(self.current_file_path, 'w', encoding='utf-8') as file:
                json.dump(new_data, file, indent=4)
            messagebox.showinfo("Success", "Profile successfully updated!")
            
            # Update the baseline to reflect the new saved state
            self.original_text = self.text_editor.get("1.0", "end-1c")
            self.check_modifications()
            
            # Note: We don't automatically reload the tree anymore so you don't lose your place!
            # You can manually hit the reload button if you changed the profile's 'name' or 'inherits'.
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON. Please fix formatting before saving.")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrcaProfileManager(root)
    root.mainloop()