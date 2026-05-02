import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

DATA_FILE = os.path.join(os.path.expanduser("~"), ".book_tracker_books.json")

class Book:
    def __init__(self, title, author, genre, pages):
        self.title = title
        self.author = author
        self.genre = genre
        self.pages = pages

    def to_dict(self):
        return {"title": self.title, "author": self.author, "genre": self.genre, "pages": self.pages}

    @staticmethod
    def from_dict(d):
        return Book(d["title"], d["author"], d["genre"], d["pages"])

class EditDialog(simpledialog.Dialog):
    def __init__(self, parent, book: Book):
        self.book = book
        super().__init__(parent, title="Edit Book")

    def body(self, master):
        ttk.Label(master, text="Title:").grid(row=0, column=0, sticky="w")
        self.title_var = tk.StringVar(value=self.book.title)
        ttk.Entry(master, textvariable=self.title_var, width=40).grid(row=0, column=1, sticky="w")

        ttk.Label(master, text="Author:").grid(row=1, column=0, sticky="w")
        self.author_var = tk.StringVar(value=self.book.author)
        ttk.Entry(master, textvariable=self.author_var, width=40).grid(row=1, column=1, sticky="w")

        ttk.Label(master, text="Genre:").grid(row=2, column=0, sticky="w")
        self.genre_var = tk.StringVar(value=self.book.genre)
        ttk.Entry(master, textvariable=self.genre_var, width=40).grid(row=2, column=1, sticky="w")

        ttk.Label(master, text="Pages:").grid(row=3, column=0, sticky="w")
        self.pages_var = tk.StringVar(value=str(self.book.pages))
        ttk.Entry(master, textvariable=self.pages_var, width=10).grid(row=3, column=1, sticky="w")

        return master

    def validate(self):
        if not self.title_var.get().strip() or not self.author_var.get().strip() or not self.genre_var.get().strip():
            messagebox.showwarning("Validation", "Title, Author and Genre cannot be empty.")
            return False
        try:
            pages = int(self.pages_var.get())
            if pages <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Pages must be a positive integer.")
            return False
        return True

    def apply(self):
        self.book.title = self.title_var.get().strip()
        self.book.author = self.author_var.get().strip()
        self.book.genre = self.genre_var.get().strip()
        self.book.pages = int(self.pages_var.get())

class BookTrackerApp:
    def __init__(self, root):
        self.root = root
        root.title("Book Tracker")
        root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.books = []
        self.sort_column = None
        self.sort_reverse = False

        self.create_menu()
        self.create_toolbar()
        self.create_main()
        self.create_statusbar()
        self.bind_shortcuts()

        self.load_on_startup()
        self.update_status("Ready")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        # File
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="Load\tCtrl+L", command=self.load_from_file)
        filem.add_command(label="Save\tCtrl+S", command=self.save_to_file)
        filem.add_command(label="Export JSON As...", command=self.export_as)
        filem.add_separator()
        filem.add_command(label="Exit\tCtrl+Q", command=self.on_exit)
        menubar.add_cascade(label="File", menu=filem)
        # Edit
        editm = tk.Menu(menubar, tearoff=0)
        editm.add_command(label="Add Book\tCtrl+N", command=self.open_add_window)
        editm.add_command(label="Edit Selected\tEnter", command=self.edit_selected)
        editm.add_command(label="Delete Selected\tDel", command=self.delete_selected)
        menubar.add_cascade(label="Edit", menu=editm)
        # Help
        helpm = tk.Menu(menubar, tearoff=0)
        helpm.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpm)
        self.root.config(menu=menubar)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="Add", command=self.open_add_window).pack(side="left")
        ttk.Button(toolbar, text="Load", command=self.load_from_file).pack(side="left", padx=(6,0))
        ttk.Button(toolbar, text="Save", command=self.save_to_file).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Export", command=self.export_as).pack(side="left", padx=6)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Label(toolbar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_ent = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_ent.pack(side="left", padx=(4,6))
        search_ent.bind("<KeyRelease>", lambda e: self.apply_filters())

        ttk.Label(toolbar, text="Genre:").pack(side="left")
        self.filter_genre_var = tk.StringVar()
        self.filter_genre = ttk.Combobox(toolbar, textvariable=self.filter_genre_var, state="readonly", width=15)
        self.filter_genre.pack(side="left", padx=4)
        self.filter_genre['values'] = ["(All)"]
        self.filter_genre.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(toolbar, text="Min Pages:").pack(side="left", padx=(10,0))
        self.filter_pages_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.filter_pages_var, width=8).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Apply", command=self.apply_filters).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Clear", command=self.clear_filters).pack(side="left")

    def create_main(self):
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill="both", expand=True)

        cols = ("Title", "Author", "Genre", "Pages")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c, command=lambda _c=c: self.sort_by(_c))
            self.tree.column(c, anchor="w", width=150 if c!="Pages" else 80)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="left", fill="y")

        # Add-entry panel (on right)
        side = ttk.Frame(frame, padding=(10,0,0,0))
        side.pack(side="right", fill="y")

        ttk.Label(side, text="Title:").pack(anchor="w")
        self.title_var = tk.StringVar()
        ttk.Entry(side, textvariable=self.title_var, width=30).pack(anchor="w")

        ttk.Label(side, text="Author:").pack(anchor="w", pady=(6,0))
        self.author_var = tk.StringVar()
        ttk.Entry(side, textvariable=self.author_var, width=30).pack(anchor="w")

        ttk.Label(side, text="Genre:").pack(anchor="w", pady=(6,0))
        self.genre_var = tk.StringVar()
        ttk.Entry(side, textvariable=self.genre_var, width=30).pack(anchor="w")

        ttk.Label(side, text="Pages:").pack(anchor="w", pady=(6,0))
        self.pages_var = tk.StringVar()
        ttk.Entry(side, textvariable=self.pages_var, width=10).pack(anchor="w")

        ttk.Button(side, text="Add Book", command=self.add_book).pack(anchor="w", pady=(10,0))
        ttk.Button(side, text="Delete Selected", command=self.delete_selected).pack(anchor="w", pady=(6,0))
        ttk.Button(side, text="Edit Selected", command=self.edit_selected).pack(anchor="w", pady=(6,0))

    def create_statusbar(self):
        self.status_var = tk.StringVar()
        status = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=4)
        status.pack(side="bottom", fill="x")

    def bind_shortcuts(self):
        self.root.bind_all("<Control-n>", lambda e: self.open_add_window())
        self.root.bind_all("<Control-s>", lambda e: self.save_to_file())
        self.root.bind_all("<Control-l>", lambda e: self.load_from_file())
        self.root.bind_all("<Control-q>", lambda e: self.on_exit())
        self.root.bind_all("<Return>", lambda e: self.edit_selected())

    def update_status(self, text):
        self.status_var.set(text)

    def open_add_window(self):
        # focus side inputs
        self.title_var.set("")
        self.author_var.set("")
        self.genre_var.set("")
        self.pages_var.set("")
        self.root.after(50, lambda: self.root.focus_force())

    def add_book(self):
        title = self.title_var.get().strip()
        author = self.author_var.get().strip()
        genre = self.genre_var.get().strip()
        pages_s = self.pages_var.get().strip()

        if not title or not author or not genre or not pages_s:
            messagebox.showwarning("Validation", "All fields must be filled.")
            return
        try:
            pages = int(pages_s)
            if pages <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Pages must be a positive integer.")
            return

        b = Book(title, author, genre, pages)
        self.books.append(b)
        self.refresh_genre_list()
        self.apply_filters()  # keeps current filters/search
        self.update_status(f"Added: {title}")
        self.clear_side_inputs()

    def clear_side_inputs(self):
        self.title_var.set("")
        self.author_var.set("")
        self.genre_var.set("")
        self.pages_var.set("")

    def refresh_table(self, filtered=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        source = filtered if filtered is not None else self.books
        for b in source:
            self.tree.insert("", "end", values=(b.title, b.author, b.genre, b.pages))
        self.update_status(f"Showing {len(source)} book(s)")

    def refresh_genre_list(self):
        genres = sorted({b.genre for b in self.books})
        values = ["(All)"] + genres
        self.filter_genre['values'] = values
        cur = self.filter_genre_var.get()
        if cur not in values:
            self.filter_genre_var.set("(All)")

    def apply_filters(self):
        q = self.search_var.get().strip().lower()
        genre = self.filter_genre_var.get()
        min_pages_s = self.filter_pages_var.get().strip()
        min_pages = None
        if min_pages_s:
            try:
                min_pages = int(min_pages_s)
            except ValueError:
                messagebox.showwarning("Validation", "Min pages must be an integer.")
                return
        filtered = []
        for b in self.books:
            if genre and genre != "(All)" and b.genre != genre:
                continue
            if min_pages is not None and not (b.pages > min_pages):
                continue
            if q:
                if q not in b.title.lower() and q not in b.author.lower() and q not in b.genre.lower():
                    continue
            filtered.append(b)
        # apply current sort
        if self.sort_column:
            key = lambda x: getattr(x, self.sort_column.lower()) if self.sort_column!="Pages" else x.pages
            filtered.sort(key=key, reverse=self.sort_reverse)
        self.refresh_table(filtered)

    def clear_filters(self):
        self.search_var.set("")
        self.filter_genre_var.set("(All)")
        self.filter_pages_var.set("")
        self.refresh_table()

    def save_to_file(self):
        try:
            data = [b.to_dict() for b in self.books]
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.update_status(f"Saved {len(self.books)} book(s) to {DATA_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def load_from_file(self):
        if not os.path.exists(DATA_FILE):
            messagebox.showinfo("Info", "No saved data found.")
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.books = [Book.from_dict(d) for d in data]
            self.refresh_genre_list()
            self.apply_filters()
            self.update_status(f"Loaded {len(self.books)} book(s).")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def load_on_startup(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.books = [Book.from_dict(d) for d in data]
            except Exception:
                self.books = []
        self.refresh_genre_list()
        self.refresh_table()

    def export_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
        if not path:
            return
        try:
            data = [b.to_dict() for b in self.books]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.update_status(f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "No selection.")
            return
        confirmed = messagebox.askyesno("Delete", "Delete selected book(s)?")
        if not confirmed:
            return
        vals = [self.tree.item(s)["values"] for s in sel]
        for v in vals:
            title, author, genre, pages = v
            for b in list(self.books):
                if b.title == title and b.author == author and b.genre == genre and str(b.pages) == str(pages):
                    self.books.remove(b)
                    break
        self.refresh_genre_list()
        self.apply_filters()
        self.update_status("Deleted selected")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "No selection.")
            return
        item = sel[0]
        vals = self.tree.item(item)["values"]
        title, author, genre, pages = vals
        target = None
        for b in self.books:
            if b.title == title and b.author == author and b.genre == genre and str(b.pages) == str(pages):
                target = b
                break
        if not target:
            messagebox.showerror("Error", "Selected book not found.")
            return
        dlg = EditDialog(self.root, target)
        if dlg.result is not None:
            self.refresh_genre_list()
            self.apply_filters()
            self.update_status(f"Edited: {target.title}")

    def sort_by(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.apply_filters()

    def show_about(self):
        messagebox.showinfo("About", "Book Tracker\nGUI on Tkinter\nEnhanced UI")

    def on_exit(self):
        if messagebox.askyesno("Exit", "Save changes before exit?"):
            self.save_to_file()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = BookTrackerApp(root)
    root.geometry("1000x600")
    root.mainloop()
