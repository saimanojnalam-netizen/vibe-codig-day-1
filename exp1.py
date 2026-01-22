import tkinter as tk
from tkinter import messagebox, ttk, filedialog, font
import json
import os
from datetime import datetime
from PIL import Image, ImageTk  # pip install pillow
import threading


class NotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Shortee Notes App ✨")
        self.root.geometry("800x700")
        self.root.configure(bg="#f8fafc")
        self.root.minsize(600, 500)

        self.notes = []
        self.filtered_notes = []
        self.sort_by = "date_desc"
        self.current_search = ""
        self.load_notes()

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.create_menu()
        self.create_widgets()
        self.update_listbox()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 File", menu=file_menu)
        file_menu.add_command(label="💾 Save All", command=self.save_notes)
        file_menu.add_command(label="📤 Export JSON", command=self.export_json)
        file_menu.add_command(label="📥 Import JSON", command=self.import_json)
        file_menu.add_separator()
        file_menu.add_command(label="❌ Exit", command=self.root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ View", menu=view_menu)
        view_menu.add_command(label="🔍 Search Notes", command=self.focus_search)
        view_menu.add_command(label="📊 Stats", command=self.show_stats)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔧 Tools", menu=tools_menu)
        tools_menu.add_command(label="✨ Theme Dark", command=lambda: self.set_theme("dark"))
        tools_menu.add_command(label="☀️ Theme Light", command=lambda: self.set_theme("light"))

    def create_widgets(self):
        # Header with stats
        header_frame = tk.Frame(self.root, bg="#1a202c", height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        self.title_label = tk.Label(header_frame, text="🚀 Shortee Notes APP",
                                    font=("Segoe UI", 22, "bold"), fg="#63b3ed", bg="#1a202c")
        self.title_label.pack(side=tk.LEFT, padx=20, pady=15)

        self.stats_label = tk.Label(header_frame, text="📊 0 notes",
                                    font=("Segoe UI", 12), fg="#e2e8f0", bg="#1a202c")
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Toolbar
        toolbar = tk.Frame(self.root, bg="#edf2f7", height=50)
        toolbar.pack(fill=tk.X, pady=(10, 0))
        toolbar.pack_propagate(False)

        ttk.Button(toolbar, text="➕ New Note", command=self.add_note).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(toolbar, text="💾 Save", command=self.save_current).pack(side=tk.LEFT, padx=5, pady=10)
        ttk.Button(toolbar, text="✏️ Edit", command=self.edit_note).pack(side=tk.LEFT, padx=5, pady=10)
        ttk.Button(toolbar, text="🗑️ Delete", command=self.delete_note).pack(side=tk.LEFT, padx=5, pady=10)
        ttk.Button(toolbar, text="📤 Export", command=self.export_json).pack(side=tk.LEFT, padx=5, pady=10)

        self.sort_var = tk.StringVar(value="date_desc")
        ttk.Combobox(toolbar, textvariable=self.sort_var, values=["date_desc", "date_asc", "title_az", "title_za"],
                     state="readonly", width=12).pack(side=tk.LEFT, padx=10)
        self.sort_var.trace("w", self.on_sort_change)

        # Search
        search_frame = tk.Frame(toolbar, bg="#edf2f7")
        search_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 14), bg="#edf2f7").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=25, font=("Segoe UI", 11), relief="flat", bg="white")
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # Main content frame
        content_frame = tk.Frame(self.root, bg="#f8fafc")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        # Note editor (left panel)
        editor_frame = tk.LabelFrame(content_frame, text="📝 Editor", font=("Segoe UI", 13, "bold"),
                                     bg="#f8fafc", fg="#2d3748", padx=15, pady=15)
        editor_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        tk.Label(editor_frame, text="Title:", font=("Segoe UI", 11, "bold"), bg="#f8fafc").grid(row=0, column=0,
                                                                                                sticky="w")
        self.title_entry = tk.Entry(editor_frame, width=50, font=("Segoe UI", 12, "bold"), relief="flat",
                                    bd=3, bg="#ffffff", fg="#2d3748")
        self.title_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(editor_frame, text="Content:", font=("Segoe UI", 11, "bold"), bg="#f8fafc").grid(row=1, column=0,
                                                                                                  sticky="nw",
                                                                                                  pady=(15, 0))
        text_frame = tk.Frame(editor_frame, bg="#f8fafc")
        text_frame.grid(row=1, column=1, sticky="nsew", pady=(15, 0))
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.content_text = tk.Text(text_frame, height=10, wrap=tk.WORD, font=("Segoe UI", 11),
                                    relief="flat", bd=3, bg="#fefefe", fg="#2d3748",
                                    insertbackground="#4299e1", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=scrollbar.set)
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags dropdown
        tk.Label(editor_frame, text="Tags:", font=("Segoe UI", 11, "bold"), bg="#f8fafc").grid(row=2, column=0,
                                                                                               sticky="w", pady=(15, 0))
        self.tags_var = tk.StringVar()
        tags_combo = ttk.Combobox(editor_frame, textvariable=self.tags_var,
                                  values=["work", "personal", "ideas", "gate", "study"],
                                  width=20, state="readonly")
        tags_combo.grid(row=2, column=1, sticky="w", pady=(15, 0))

        editor_frame.grid_columnconfigure(1, weight=1)

        # Notes list (right panel)
        list_frame = tk.LabelFrame(content_frame, text="📋 Notes List", font=("Segoe UI", 13, "bold"),
                                   bg="#f8fafc", fg="#2d3748", padx=15, pady=15)
        list_frame.grid(row=1, column=0, sticky="nsew")

        self.notes_listbox = tk.Listbox(list_frame, height=20, font=("Consolas", 11),
                                        bg="#ffffff", fg="#2d3748", selectbackground="#4299e1",
                                        relief="flat", bd=3, highlightthickness=0,
                                        activestyle="dotbox")
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.notes_listbox.yview)
        self.notes_listbox.configure(yscrollcommand=list_scroll.set)
        self.notes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_listbox.bind('<<ListboxSelect>>', self.on_select)
        self.notes_listbox.bind('<Double-1>', self.on_double_click)

    def set_theme(self, theme):
        if theme == "dark":
            self.root.configure(bg="#1a202c")
            # Add dark mode colors...
        else:
            self.root.configure(bg="#f8fafc")

    def show_stats(self):
        total = len(self.notes)
        if total > 0:
            dates = [note.get("date", "") for note in self.notes]
            recent = sum(1 for d in dates if "2026" in d) if dates else 0
            messagebox.showinfo("📊 Stats",
                                f"Total Notes: {total}\nRecent (2026): {recent}\nAvg length: {sum(len(n.get('content', '')) for n in self.notes) // total if total else 0} chars")

    def export_json(self):
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if file:
            with open(file, 'w') as f:
                json.dump(self.notes, f, indent=4)
            messagebox.showinfo("📤 Exported", f"Saved to {file}")

    def import_json(self):
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if file:
            try:
                with open(file, 'r') as f:
                    imported = json.load(f)
                    self.notes.extend(imported)
                    self.update_listbox()
                    self.save_notes()
                messagebox.showinfo("📥 Imported", f"Added {len(imported)} notes")
            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {e}")

    def focus_search(self):
        self.search_entry.focus()

    def on_sort_change(self, *args):
        self.update_listbox()

    def load_notes(self):
        if os.path.exists('notes.json'):
            try:
                with open('notes.json', 'r') as f:
                    self.notes = json.load(f)
                # Add timestamps if missing
                for note in self.notes:
                    if "date" not in note:
                        note["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            except:
                self.notes = []

    def save_notes(self):
        # Add current timestamp and tags
        selection = self.notes_listbox.curselection()
        if selection:
            idx = selection[0]
            self.notes[idx]["tags"] = self.tags_var.get()
            self.notes[idx]["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open('notes.json', 'w') as f:
            json.dump(self.notes, f, indent=4)

    def save_current(self):
        """Save the currently edited note: update if one is selected, otherwise add a new note."""
        selection = self.notes_listbox.curselection()
        title = self.title_entry.get().strip()
        content = self.content_text.get(1.0, tk.END).strip()
        tags = self.tags_var.get()

        if selection:
            idx = selection[0]
            if title and content:
                self.notes[idx] = {
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                self.update_listbox()
                self.save_notes()
                messagebox.showinfo("💾 Saved", "Note updated and saved.")
            else:
                messagebox.showwarning("⚠️ Error", "Title and content required!")
        else:
            # No selection — create a new note
            self.add_note()

    def add_note(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get(1.0, tk.END).strip()
        tags = self.tags_var.get()
        if title and content:
            self.notes.append({
                "title": title,
                "content": content,
                "tags": tags,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            self.clear_entries()
            self.update_listbox()
            self.save_notes()
        else:
            messagebox.showwarning("⚠️ Error", "Title and content required!")

    def edit_note(self):
        selection = self.notes_listbox.curselection()
        if selection:
            idx = selection[0]
            title = self.title_entry.get().strip()
            content = self.content_text.get(1.0, tk.END).strip()
            tags = self.tags_var.get()
            if title and content:
                self.notes[idx] = {
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                self.update_listbox()
                self.save_notes()
            else:
                messagebox.showwarning("⚠️ Error", "Title and content required!")
        else:
            messagebox.showwarning("⚠️ No Selection", "Select a note to edit")

    def delete_note(self):
        selection = self.notes_listbox.curselection()
        if selection:
            if messagebox.askyesno("🗑️ Confirm Delete", "Delete this note?"):
                idx = selection[0]
                del self.notes[idx]
                self.clear_entries()
                self.update_listbox()
                self.save_notes()
        else:
            messagebox.showwarning("⚠️ No Selection", "Select a note to delete")

    def on_select(self, event):
        selection = self.notes_listbox.curselection()
        if selection:
            idx = selection[0]
            note = self.notes[idx]
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, note.get("title", ""))
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(1.0, note.get("content", ""))
            self.tags_var.set(note.get("tags", ""))

    def on_double_click(self, event):
        self.edit_note()

    def on_search(self, event=None):
        self.current_search = self.search_entry.get().lower()
        self.update_listbox()

    def update_listbox(self):
        self.filtered_notes = self.notes.copy()

        # Search filter
        if self.current_search:
            self.filtered_notes = [n for n in self.filtered_notes
                                   if self.current_search in n.get("title", "").lower() or
                                   self.current_search in n.get("content", "").lower()]

        # Sort
        if self.sort_by == "date_desc":
            self.filtered_notes.sort(key=lambda x: x.get("date", ""), reverse=True)
        elif self.sort_by == "date_asc":
            self.filtered_notes.sort(key=lambda x: x.get("date", ""))
        elif self.sort_by == "title_az":
            self.filtered_notes.sort(key=lambda x: x.get("title", "").lower())
        elif self.sort_by == "title_za":
            self.filtered_notes.sort(key=lambda x: x.get("title", "").lower(), reverse=True)

        self.notes_listbox.delete(0, tk.END)
        for note in self.filtered_notes:
            display = f"📄 {note.get('title', '')}"
            if note.get('tags'):
                display += f"  🏷️ {note['tags']}"
            display += f"  ({note.get('date', '')[:10]})"
            self.notes_listbox.insert(tk.END, display)

        self.stats_label.config(text=f"📊 {len(self.filtered_notes)}/{len(self.notes)} notes")

    def clear_entries(self):
        self.title_entry.delete(0, tk.END)
        self.content_text.delete(1.0, tk.END)
        self.tags_var.set("")


if __name__ == "__main__":
    root = tk.Tk()
    app = NotesApp(root)
    root.mainloop()