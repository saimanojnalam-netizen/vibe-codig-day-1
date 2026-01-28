"""
Shortee Notes App - Complete Standalone Version
All-in-one solution with Email and WhatsApp sharing
Professional architecture with robust error handling
"""

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import os
import logging
import smtplib
import threading
import webbrowser
import urllib.parse
import math
import random
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    'app_title': '🚀 NoteBridge ✨',
    'version': '2.0.0',
    'data_file': 'notes.txt',
    'window_width': 900,
    'window_height': 700,
    'min_width': 700,
    'min_height': 500,
}

THEME = {
    'primary': "#2563eb",
    'primary_hover': "#1d4ed8",
    'text_primary': "#0f172a",
    'background': "#0b1220",
    'surface': "#0f172a",
    'surface_alt': "#111827",
    'muted': "#94a3b8",
    'success': "#22c55e",
    'error': '#ef4444',
}

SMTP_CONFIG = {
    'gmail_smtp': 'smtp.gmail.com',
    'smtp_port': 587,
}

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging for the application"""
    logger = logging.getLogger('ShorteeApp')
    logger.setLevel(logging.INFO)
    
    # File handler
    try:
        fh = logging.FileHandler('app.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

logger = setup_logging()

# ============================================================================
# DATA MODELS
# ============================================================================

class Note:
    """Represents a single note"""
    def __init__(self, title, content, note_id=None, created_at=None):
        self.id = note_id or datetime.now().isoformat()
        self.title = title
        self.content = content
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            title=data['title'],
            content=data['content'],
            note_id=data['id'],
            created_at=data['created_at']
        )


# ============================================================================
# SERVICES
# ============================================================================

class NotesService:
    """Handles note operations and persistence"""
    
    def __init__(self, filename='notes.json'):
        self.filename = filename
        self.notes = self._load_notes()
    
    def _load_notes(self):
        """Load notes from JSON file"""
        try:
            if not os.path.exists(self.filename):
                logger.info(f"Notes file not found, starting fresh")
                return []
            
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            notes = [Note.from_dict(item) for item in data]
            logger.info(f"Loaded {len(notes)} notes")
            return notes
        except Exception as e:
            logger.error(f"Error loading notes: {e}")
            return []
    
    def _save_notes(self):
        """Save notes to JSON file"""
        try:
            data = [note.to_dict() for note in self.notes]
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.notes)} notes")
            return True
        except Exception as e:
            logger.error(f"Error saving notes: {e}")
            return False
    
    def add_note(self, title, content):
        """Create new note"""
        note = Note(title=title, content=content)
        self.notes.append(note)
        self._save_notes()
        logger.info(f"Added note: {note.id}")
        return note
    
    def update_note(self, note_id, title, content):
        """Update existing note"""
        for note in self.notes:
            if note.id == note_id:
                note.title = title
                note.content = content
                note.updated_at = datetime.now().isoformat()
                self._save_notes()
                logger.info(f"Updated note: {note_id}")
                return True
        return False
    
    def delete_note(self, note_id):
        """Delete note"""
        for i, note in enumerate(self.notes):
            if note.id == note_id:
                self.notes.pop(i)
                self._save_notes()
                logger.info(f"Deleted note: {note_id}")
                return True
        return False
    
    def get_note(self, note_id):
        """Get note by ID"""
        for note in self.notes:
            if note.id == note_id:
                return note
        return None
    
    def search_notes(self, query):
        """Search notes"""
        query = query.lower()
        return [n for n in self.notes if query in n.title.lower() or query in n.content.lower()]
    
    def get_all_notes(self):
        """Get all notes"""
        return self.notes
    
    def sort_notes(self, sort_by='date_desc'):
        """Sort notes"""
        if sort_by == 'date_desc':
            return sorted(self.notes, key=lambda x: x.created_at, reverse=True)
        elif sort_by == 'date_asc':
            return sorted(self.notes, key=lambda x: x.created_at)
        elif sort_by == 'title':
            return sorted(self.notes, key=lambda x: x.title)
        return self.notes


class EmailService:
    """Handles email sending via Gmail SMTP"""
    
    @staticmethod
    def is_valid_email(email):
        """Validate email format"""
        return '@' in email and '.' in email.split('@')[1]
    
    @staticmethod
    def send_email(recipient, sender, password, subject, body, on_success=None, on_error=None):
        """Send email via Gmail SMTP"""
        def _send():
            try:
                logger.info("=" * 60)
                logger.info("Starting email send process")
                logger.info("=" * 60)
                
                # Validate
                if not all([recipient, sender, password, subject, body]):
                    raise ValueError("Missing email parameters")
                
                if not EmailService.is_valid_email(recipient):
                    raise ValueError(f"Invalid recipient: {recipient}")
                if not EmailService.is_valid_email(sender):
                    raise ValueError(f"Invalid sender: {sender}")
                
                logger.info(f"✓ Recipient: {recipient}")
                logger.info(f"✓ Sender: {sender}")
                logger.info("Creating MIME message...")
                
                # Create message
                message = MIMEMultipart()
                message["From"] = sender
                message["To"] = recipient
                message["Subject"] = subject
                message.attach(MIMEText(body, "plain", "utf-8"))
                logger.info("✓ Message created")
                
                # Connect
                logger.info(f"Connecting to {SMTP_CONFIG['gmail_smtp']}...")
                server = smtplib.SMTP(SMTP_CONFIG['gmail_smtp'], SMTP_CONFIG['smtp_port'], timeout=15)
                logger.info("✓ Connected")
                
                try:
                    logger.info("Starting TLS...")
                    server.starttls()
                    logger.info("✓ TLS started")
                    
                    logger.info(f"Authenticating as {sender}...")
                    server.login(sender, password)
                    logger.info("✓ Authenticated")
                    
                    logger.info("Sending message...")
                    server.send_message(message)
                    logger.info("✓ Message sent")
                    
                finally:
                    server.quit()
                
                logger.info("=" * 60)
                logger.info(f"✅ EMAIL SENT SUCCESSFULLY to {recipient}")
                logger.info("=" * 60)
                
                if on_success:
                    on_success(recipient)
            
            except smtplib.SMTPAuthenticationError:
                error = (
                    "❌ AUTHENTICATION ERROR\n\n"
                    "Solutions:\n"
                    "1. Enable 2-Step Verification in your Google Account\n"
                    "2. Generate an App Password at:\n"
                    "   https://myaccount.google.com/apppasswords\n"
                    "3. Use the 16-character app password (not your regular password)\n"
                    "4. Make sure your email address is correct"
                )
                logger.error("Authentication failed")
                if on_error:
                    on_error(error)
            
            except Exception as e:
                error = (
                    f"❌ ERROR: {type(e).__name__}\n\n"
                    f"{str(e)}\n\n"
                    "Troubleshooting:\n"
                    "• Check your internet connection\n"
                    "• Verify both email addresses are correct\n"
                    "• Ensure you're using an App Password (16 chars)\n"
                    "• Check app.log for detailed information"
                )
                logger.error(f"{type(e).__name__}: {e}", exc_info=True)
                if on_error:
                    on_error(error)
        
        # Send in background
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()


class Summarizer:
    """Lightweight extractive summarizer (no external APIs)"""

    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "if", "while", "with", "at", "by", "for",
        "from", "into", "on", "onto", "of", "to", "in", "out", "over", "then", "so", "as",
        "is", "are", "was", "were", "be", "been", "being", "this", "that", "it", "its",
        "their", "they", "them", "you", "your", "i", "we", "our", "us", "he", "she", "his",
        "hers", "do", "does", "did", "can", "could", "should", "would", "will", "just", "about",
        "not", "no", "yes", "very"
    }

    @staticmethod
    def _sentences(text):
        # Split on sentence boundaries; fallback to line breaks
        parts = re.split(r"(?<=[.!?])\s+|\n", text.strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _word_freq(text):
        words = re.findall(r"[a-zA-Z']+", text.lower())
        freq = {}
        for w in words:
            if w in Summarizer.STOPWORDS or len(w) <= 2:
                continue
            freq[w] = freq.get(w, 0) + 1
        return freq

    @staticmethod
    def summarize(text, max_sentences=3):
        if not text or not text.strip():
            return ""
        sentences = Summarizer._sentences(text)
        if len(sentences) <= max_sentences:
            return " \n".join(sentences)
        freq = Summarizer._word_freq(text)
        scored = []
        for idx, sent in enumerate(sentences):
            words = re.findall(r"[a-zA-Z']+", sent.lower())
            score = sum(freq.get(w, 0) for w in words)
            # slight boost for earlier sentences to keep context
            score += max(0, (len(sentences) - idx)) * 0.02
            scored.append((score, idx, sent))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top = sorted(scored[:max_sentences], key=lambda x: x[1])
        summary = " \n".join([t[2] for t in top])
        return summary


class ShareService:
    """Handles sharing via multiple platforms"""
    
    @staticmethod
    def share_whatsapp(content):
        """Open WhatsApp Web with message"""
        try:
            encoded = urllib.parse.quote(content)
            webbrowser.open(f"https://web.whatsapp.com/send?text={encoded}")
            logger.info("WhatsApp Web opened")
            return True
        except Exception as e:
            logger.error(f"Error opening WhatsApp: {e}")
            return False
    

    
    @staticmethod
    def copy_clipboard(content, root):
        """Copy to clipboard"""
        try:
            root.clipboard_clear()
            root.clipboard_append(content)
            root.update()
            logger.info("Copied to clipboard")
            return True
        except Exception as e:
            logger.error(f"Error copying: {e}")
            return False
    
    @staticmethod
    def export_file(content, filepath):
        """Export to text file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting: {e}")
            return False


# ============================================================================
# UI APPLICATION
# ============================================================================

class ShorteeApp:
    """Main application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(CONFIG['app_title'])
        self.root.geometry(f"{CONFIG['window_width']}x{CONFIG['window_height']}")
        self.root.minsize(CONFIG['min_width'], CONFIG['min_height'])
        self.root.configure(bg=THEME['background'])
        
        # Background art state and canvas
        self.bg_art_enabled = True
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0)
        # Place the canvas behind all widgets (fills entire window)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_canvas.lower('all')
        # Redraw background on resize
        self.root.bind("<Configure>", self._on_resize)
        
        # Services
        self.notes_service = NotesService(CONFIG['data_file'])
        self.share_service = ShareService
        
        # State
        self.selected_note_id = None
        self.sort_by = "date_desc"
        
        # UI Setup
        self._setup_styles()
        self._create_ui()
        self._load_notes()
        # Initial background draw
        self._redraw_background()
    
    def _setup_styles(self):
        """Configure styles"""
        style = ttk.Style()
        style.theme_use("clam")

        default_font = ("Segoe UI", 10)
        heading_font = ("Segoe UI", 12, "bold")
        style.configure("TLabel", background=THEME['surface'], foreground="#e2e8f0", font=default_font)
        style.configure("Heading.TLabel", background=THEME['surface'], foreground="#e2e8f0", font=heading_font)
        style.configure("TFrame", background=THEME['surface'])
        style.configure("Card.TFrame", background=THEME['surface_alt'], borderwidth=1, relief="flat")
        style.configure("TButton", font=default_font, padding=(10, 6))
        style.configure(
            "Accent.TButton",
            background=THEME['primary'],
            foreground="#ffffff",
            bordercolor=THEME['primary'],
            focusthickness=3,
            focuscolor=THEME['primary_hover'],
            padding=(12, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", THEME['primary_hover'])],
            relief=[("pressed", "sunken"), ("!pressed", "raised")]
        )
        style.configure(
            "Treeview",
            background=THEME['surface_alt'],
            foreground="#e2e8f0",
            fieldbackground=THEME['surface_alt'],
            rowheight=26,
            bordercolor=THEME['surface'],
        )
        style.configure(
            "Treeview.Heading",
            background=THEME['primary'],
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", THEME['primary_hover'])])
        
        # Add border styles for card frames
        style.configure("Border.Card.TFrame", background=THEME['surface_alt'], borderwidth=2, relief="flat", padding=1)
        style.configure(
            "Border.TFrame",
            background=THEME['surface'],
            borderwidth=2,
            relief="solid"
        )
    
    def _create_ui(self):
        """Create user interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📄 File", menu=file_menu)
        file_menu.add_command(label="➕ New Note", command=self._new_note)
        file_menu.add_command(label="💾 Save", command=self._save_note)
        file_menu.add_command(label="🗑️ Delete", command=self._delete_note)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Share menu
        share_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📣 Share", menu=share_menu)
        share_menu.add_command(label="✉️ Email", command=self._share_email)
        share_menu.add_command(label="💬 WhatsApp", command=self._share_whatsapp)
        share_menu.add_separator()
        share_menu.add_command(label="📋 Clipboard", command=self._copy_clipboard)
        share_menu.add_command(label="📄 Export TXT", command=self._export_txt)
        share_menu.add_separator()
        share_menu.add_command(label="🧠 Summarize Note", command=self._summarize_note)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ View", menu=view_menu)
        view_menu.add_command(label="Toggle Background Art", command=self._toggle_background_art)
        
        # Toolbar
        toolbar = ttk.Frame(self.root, style="Card.TFrame")
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(toolbar, text="➕ New", style="Accent.TButton", command=self._new_note).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(toolbar, text="💾 Save", style="Accent.TButton", command=self._save_note).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(toolbar, text="🗑️ Delete", style="Accent.TButton", command=self._delete_note).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(toolbar, text="📣 Share", style="Accent.TButton", command=self._show_share_menu).pack(side=tk.LEFT, padx=4, pady=6)
        ttk.Button(toolbar, text="🧠 Summarize", style="Accent.TButton", command=self._summarize_note).pack(side=tk.LEFT, padx=4, pady=6)
        
        # Main content
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - with border design
        left_border = tk.Frame(main_frame, bg=THEME['primary'], highlightthickness=0)
        left_border.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=2)
        
        left = ttk.Frame(left_border, style="Card.TFrame")
        left.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        ttk.Label(left, text="📌 Notes", style="Heading.TLabel").pack(pady=6, padx=6)
        
        # Search
        search_frame = ttk.Frame(left)
        search_frame.pack(fill=tk.X, pady=5, padx=6)
        ttk.Label(search_frame, text="🔍 Search:", foreground="#cbd5e1", background=THEME['surface_alt']).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Notes tree with styled frame
        tree_frame = tk.Frame(left, bg=THEME['primary'], highlightthickness=0)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=6)
        
        tree_inner = tk.Frame(tree_frame, bg=THEME['surface_alt'])
        tree_inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        scrollbar = ttk.Scrollbar(tree_inner)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.notes_tree = ttk.Treeview(tree_inner, columns=('title', 'date'), show='tree headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.notes_tree.yview)
        
        self.notes_tree.column('#0', width=0, stretch=tk.NO)
        self.notes_tree.column('title', anchor=tk.W, width=150)
        self.notes_tree.column('date', anchor=tk.W, width=80)
        self.notes_tree.heading('title', text='Title')
        self.notes_tree.heading('date', text='Date')
        
        self.notes_tree.pack(fill=tk.BOTH, expand=True)
        self.notes_tree.bind('<<TreeviewSelect>>', self._on_select)
        
        # Right panel - with border design
        right_border = tk.Frame(main_frame, bg=THEME['primary'], highlightthickness=0)
        right_border.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=2)
        
        right = ttk.Frame(right_border, style="Card.TFrame")
        right.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        ttk.Label(right, text="📄 Content", style="Heading.TLabel").pack(pady=6, padx=6)
        
        self.content_text = tk.Text(
            right,
            font=('Segoe UI', 11),
            wrap=tk.WORD,
            bg=THEME['surface'],
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            bd=1,
            highlightthickness=2,
            highlightcolor=THEME['primary'],
            highlightbackground=THEME['muted'],
        )
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=8, padx=8)

    # -----------------------------
    # Background art helpers
    # -----------------------------
    def _on_resize(self, event=None):
        # Redraw background when window resizes
        self._redraw_background()

    def _toggle_background_art(self):
        self.bg_art_enabled = not self.bg_art_enabled
        self._redraw_background()

    def _redraw_background(self):
        # Clear previous drawing
        self.bg_canvas.delete('all')
        if not self.bg_art_enabled:
            return
        w = max(self.root.winfo_width(), 1)
        h = max(self.root.winfo_height(), 1)
        
        # Gradient background
        self._draw_vertical_gradient(0, 0, w, h, start_color="#0ea5e9", end_color="#0f172a")
        
        # Decorative machine gears
        self._draw_gear(w*0.15, h*0.20, 40, teeth=12, fill="#60a5fa", outline="#1e3a8a")
        self._draw_gear(w*0.25, h*0.32, 28, teeth=10, fill="#93c5fd", outline="#1e40af")
        self._draw_gear(w*0.12, h*0.40, 34, teeth=11, fill="#38bdf8", outline="#0ea5e9")
        
        # Cartoon robot
        self._draw_robot(w*0.82, h*0.75, scale=1.0)
        
        # Light circuit lines
        self._draw_circuits(w, h)

    def _draw_vertical_gradient(self, x, y, w, h, start_color="#000000", end_color="#FFFFFF", steps=64):
        sr, sg, sb = self._hex_to_rgb(start_color)
        er, eg, eb = self._hex_to_rgb(end_color)
        for i in range(steps):
            t = i / max(steps-1, 1)
            r = int(sr + (er - sr) * t)
            g = int(sg + (eg - sg) * t)
            b = int(sb + (eb - sb) * t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            y0 = y + int(h * i / steps)
            y1 = y + int(h * (i+1) / steps)
            self.bg_canvas.create_rectangle(x, y0, x + w, y1, outline="", fill=color)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_gear(self, cx, cy, r, teeth=12, fill="#7dd3fc", outline="#0ea5e9"):
        # Draw gear body
        self.bg_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=2)
        inner_r = r * 0.45
        self.bg_canvas.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r, fill="#0f172a", outline="")
        
        # Teeth as small triangles around the circle
        for i in range(teeth):
            angle = 2 * math.pi * i / teeth
            a2 = angle + (2 * math.pi / teeth) * 0.5
            outer = r + 10
            p1 = (cx + r * math.cos(angle),  cy + r * math.sin(angle))
            p2 = (cx + outer * math.cos(angle + 0.15), cy + outer * math.sin(angle + 0.15))
            p3 = (cx + r * math.cos(a2),     cy + r * math.sin(a2))
            self.bg_canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], fill=fill, outline=outline)

    def _draw_robot(self, x, y, scale=1.0):
        # Simple friendly robot
        s = 50 * scale
        body_w, body_h = s*1.5, s*1.6
        head_w, head_h = s*1.2, s*0.9
        
        # Shadow
        self.bg_canvas.create_oval(x - body_w/2, y + body_h/2, x + body_w/2, y + body_h/2 + 10, fill="#0b1220", outline="")
        
        # Body
        self.bg_canvas.create_round_rect = getattr(self.bg_canvas, 'create_rectangle')  # fallback
        self.bg_canvas.create_rectangle(x - body_w/2, y - body_h/2, x + body_w/2, y + body_h/2, fill="#1f2937", outline="#93c5fd", width=2)
        
        # Head
        hx, hy = x, y - body_h/2 - head_h/2
        self.bg_canvas.create_rectangle(hx - head_w/2, hy - head_h/2, hx + head_w/2, hy + head_h/2, fill="#0ea5e9", outline="#93c5fd", width=2)
        
        # Eyes
        eye_r = s*0.12
        self.bg_canvas.create_oval(hx - head_w*0.25 - eye_r, hy - eye_r, hx - head_w*0.25 + eye_r, hy + eye_r, fill="#ffffff", outline="")
        self.bg_canvas.create_oval(hx + head_w*0.25 - eye_r, hy - eye_r, hx + head_w*0.25 + eye_r, hy + eye_r, fill="#ffffff", outline="")
        pupil_r = eye_r*0.5
        self.bg_canvas.create_oval(hx - head_w*0.25 - pupil_r, hy - pupil_r, hx - head_w*0.25 + pupil_r, hy + pupil_r, fill="#0b1220", outline="")
        self.bg_canvas.create_oval(hx + head_w*0.25 - pupil_r, hy - pupil_r, hx + head_w*0.25 + pupil_r, hy + pupil_r, fill="#0b1220", outline="")
        
        # Antenna
        self.bg_canvas.create_line(hx, hy - head_h/2, hx, hy - head_h/2 - s*0.4, fill="#93c5fd", width=3)
        self.bg_canvas.create_oval(hx - s*0.08, hy - head_h/2 - s*0.48, hx + s*0.08, hy - head_h/2 - s*0.32, fill="#38bdf8", outline="#93c5fd")
        
        # Arms
        self.bg_canvas.create_line(x - body_w/2, y - s*0.2, x - body_w/2 - s*0.6, y - s*0.3, fill="#93c5fd", width=3)
        self.bg_canvas.create_line(x + body_w/2, y - s*0.2, x + body_w/2 + s*0.6, y - s*0.3, fill="#93c5fd", width=3)

    def _draw_circuits(self, w, h):
        random.seed(42)
        for _ in range(12):
            x1 = random.randint(int(w*0.05), int(w*0.95))
            y1 = random.randint(int(h*0.10), int(h*0.90))
            x2 = x1 + random.randint(-80, 80)
            y2 = y1 + random.randint(-60, 60)
            self.bg_canvas.create_line(x1, y1, x2, y2, fill="#64748b", width=1)
            self.bg_canvas.create_oval(x1-3, y1-3, x1+3, y1+3, fill="#f8fafc", outline="#64748b")
            self.bg_canvas.create_oval(x2-3, y2-3, x2+3, y2+3, fill="#f8fafc", outline="#64748b")
    
    def _load_notes(self):
        """Load notes in treeview"""
        self.notes_tree.delete(*self.notes_tree.get_children())
        notes = self.notes_service.sort_notes(self.sort_by)
        for note in notes:
            date_str = note.created_at[:10]
            self.notes_tree.insert('', 'end', iid=note.id, values=(note.title, date_str))
    
    def _on_select(self, event):
        """Handle note selection"""
        sel = self.notes_tree.selection()
        if sel:
            self.selected_note_id = sel[0]
            note = self.notes_service.get_note(self.selected_note_id)
            if note:
                self.content_text.delete('1.0', tk.END)
                self.content_text.insert('1.0', note.content)
    
    def _on_search(self, *args):
        """Handle search"""
        query = self.search_var.get()
        self.notes_tree.delete(*self.notes_tree.get_children())
        
        results = self.notes_service.search_notes(query) if query else self.notes_service.get_all_notes()
        for note in sorted(results, key=lambda x: x.created_at, reverse=True):
            self.notes_tree.insert('', 'end', iid=note.id, values=(note.title, note.created_at[:10]))
    
    def _new_note(self):
        """Create new note"""
        dlg = tk.Toplevel(self.root)
        dlg.title("New Note")
        dlg.geometry("400x200")
        
        ttk.Label(dlg, text="Title:").pack(pady=5)
        title_entry = ttk.Entry(dlg, width=40)
        title_entry.pack(pady=5)
        
        ttk.Label(dlg, text="Content:").pack(pady=5)
        content_text = tk.Text(dlg, height=8, width=40)
        content_text.pack(pady=5, fill=tk.BOTH, expand=True)
        
        def save():
            title = title_entry.get().strip()
            content = content_text.get('1.0', tk.END).strip()
            if not title or not content:
                messagebox.showerror("Error", "Title and content required")
                return
            self.notes_service.add_note(title, content)
            dlg.destroy()
            self._load_notes()
            messagebox.showinfo("Success", "Note created")
        
        ttk.Button(dlg, text="Create", command=save).pack(pady=10)
    
    def _save_note(self):
        """Save current note"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        note = self.notes_service.get_note(self.selected_note_id)
        content = self.content_text.get('1.0', tk.END).strip()
        self.notes_service.update_note(self.selected_note_id, note.title, content)
        messagebox.showinfo("Success", "Note saved")
    
    def _delete_note(self):
        """Delete note"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        if messagebox.askyesno("Confirm", "Delete this note?"):
            self.notes_service.delete_note(self.selected_note_id)
            self.content_text.delete('1.0', tk.END)
            self._load_notes()
            messagebox.showinfo("Success", "Note deleted")
    
    def _share_email(self):
        """Share via email"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        dlg = tk.Toplevel(self.root)
        dlg.title("📧 Send Email")
        dlg.geometry("520x550")
        dlg.resizable(False, False)
        
        # Header
        header = ttk.Frame(dlg)
        header.pack(fill=tk.X, padx=20, pady=15)
        ttk.Label(header, text="✉️ Share Note via Gmail", font=('Segoe UI', 14, 'bold')).pack()
        
        # Quick Setup Instructions
        info_frame = tk.Frame(dlg, bg='#e0f2fe', relief=tk.RIDGE, bd=2)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text="📌 Quick Setup (One-time only):", 
                 font=('Segoe UI', 10, 'bold'), background='#e0f2fe').pack(pady=5, padx=10, anchor='w')
        
        instructions = tk.Text(info_frame, height=6, wrap=tk.WORD, bg='#e0f2fe', 
                              font=('Segoe UI', 9), relief=tk.FLAT, cursor='arrow')
        instructions.pack(padx=10, pady=5, fill=tk.X)
        instructions.insert('1.0', 
            "1. Go to: https://myaccount.google.com/security\n"
            "2. Enable '2-Step Verification' if not already enabled\n"
            "3. Go to: https://myaccount.google.com/apppasswords\n"
            "4. Select 'Mail' and your device, click 'Generate'\n"
            "5. Copy the 16-character password and paste below\n"
            "   (Note: Use App Password, NOT your regular Gmail password)"
        )
        instructions.config(state='disabled')
        
        # Form
        form = ttk.Frame(dlg)
        form.pack(padx=20, pady=10, fill=tk.X)
        
        ttk.Label(form, text="Recipient Email:", font=('Segoe UI', 10, 'bold')).pack(pady=(5,2), anchor='w')
        recipient = ttk.Entry(form, width=50, font=('Segoe UI', 10))
        recipient.pack(pady=(0,10), fill=tk.X)
        recipient.insert(0, "recipient@example.com")
        recipient.focus()
        recipient.select_range(0, tk.END)
        
        ttk.Label(form, text="Your Gmail Address:", font=('Segoe UI', 10, 'bold')).pack(pady=(5,2), anchor='w')
        sender = ttk.Entry(form, width=50, font=('Segoe UI', 10))
        sender.pack(pady=(0,10), fill=tk.X)
        sender.insert(0, "your.email@gmail.com")
        
        ttk.Label(form, text="Gmail App Password (16 characters):", font=('Segoe UI', 10, 'bold')).pack(pady=(5,2), anchor='w')
        password = ttk.Entry(form, width=50, show="●", font=('Segoe UI', 10))
        password.pack(pady=(0,5), fill=tk.X)
        
        # Show/Hide password
        show_pass_var = tk.BooleanVar()
        def toggle_password():
            password.config(show="" if show_pass_var.get() else "●")
        
        ttk.Checkbutton(form, text="Show password", variable=show_pass_var, 
                       command=toggle_password).pack(pady=5, anchor='w')
        
        def send():
            recip = recipient.get().strip()
            send_from = sender.get().strip()
            pwd = password.get().strip()
            
            # Validation
            if not recip:
                messagebox.showerror("Error", "Please enter recipient email address")
                recipient.focus()
                return
            
            if not EmailService.is_valid_email(recip):
                messagebox.showerror("Error", "Invalid recipient email format")
                recipient.focus()
                return
            
            if not send_from:
                messagebox.showerror("Error", "Please enter your Gmail address")
                sender.focus()
                return
                
            if not EmailService.is_valid_email(send_from):
                messagebox.showerror("Error", "Invalid sender email format")
                sender.focus()
                return
            
            if not pwd:
                messagebox.showerror("Error", "Please enter your Gmail App Password")
                password.focus()
                return
            
            if len(pwd) < 16:
                messagebox.showwarning("Warning", 
                    "App Password should be 16 characters.\n"
                    "Make sure you're using an App Password, not your regular Gmail password.")
            
            note = self.notes_service.get_note(self.selected_note_id)
            subject = f"📝 Shared Note: {note.title}"
            content = f"Title: {note.title}\n\n{note.content}\n\n---\nShared from Shortee Notes App"
            
            # Show sending dialog
            sending = tk.Toplevel(dlg)
            sending.title("Sending Email...")
            sending.geometry("350x120")
            sending.transient(dlg)
            sending.grab_set()
            
            ttk.Label(sending, text="📤 Sending your email...", 
                     font=('Segoe UI', 11, 'bold')).pack(pady=15)
            progress = ttk.Progressbar(sending, mode='indeterminate', length=300)
            progress.pack(pady=10, padx=20)
            progress.start(10)
            
            def on_success(email):
                try:
                    progress.stop()
                    sending.destroy()
                    messagebox.showinfo("✅ Email Sent Successfully!", 
                        f"Your note has been sent to:\n\n{email}\n\n"
                        "The recipient should receive it shortly.")
                    dlg.destroy()
                except:
                    pass
            
            def on_error(error):
                try:
                    progress.stop()
                    sending.destroy()
                    messagebox.showerror("❌ Failed to Send Email", error)
                except:
                    pass
            
            EmailService.send_email(recip, send_from, pwd, subject, content, on_success, on_error)
        
        # Buttons - Fixed at bottom
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(side=tk.BOTTOM, pady=15)
        
        send_btn = ttk.Button(btn_frame, text="📧 Send Email", command=send, style="Accent.TButton")
        send_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to send
        dlg.bind('<Return>', lambda e: send())
    
    def _share_whatsapp(self):
        """Share via WhatsApp"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        note = self.notes_service.get_note(self.selected_note_id)
        content = f"📝 *{note.title}*\n\n{note.content}"
        
        if ShareService.share_whatsapp(content):
            messagebox.showinfo("✅ WhatsApp", "WhatsApp Web opened.\nSelect contact and send.")
        else:
            messagebox.showerror("Error", "Could not open WhatsApp")
    

    
    def _copy_clipboard(self):
        """Copy to clipboard"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        content = self.content_text.get('1.0', tk.END).strip()
        if ShareService.copy_clipboard(content, self.root):
            messagebox.showinfo("✅ Success", "Copied to clipboard")
        else:
            messagebox.showerror("Error", "Failed to copy")
    
    def _export_txt(self):
        """Export to text file"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        note = self.notes_service.get_note(self.selected_note_id)
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")], initialfile=f"{note.title}.txt")
        
        if filepath:
            content = self.content_text.get('1.0', tk.END).strip()
            if ShareService.export_file(content, filepath):
                if messagebox.askyesno("Success", "File exported.\nOpen file?"):
                    os.startfile(filepath)
            else:
                messagebox.showerror("Error", "Failed to export")

    def _summarize_note(self):
        """Generate and display a brief summary for the selected note"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return

        note = self.notes_service.get_note(self.selected_note_id)
        content = self.content_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showinfo("Summary", "This note is empty.")
            return

        summary = Summarizer.summarize(content, max_sentences=3)
        if not summary:
            messagebox.showinfo("Summary", "Could not create a summary for this note.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("🧠 AI Summary")
        dlg.geometry("520x320")
        dlg.configure(bg=THEME['surface'])
        dlg.resizable(False, False)

        header = ttk.Frame(dlg)
        header.pack(fill=tk.X, padx=16, pady=12)
        ttk.Label(header, text=f"Summary: {note.title}", style="Heading.TLabel").pack(anchor='w')

        body = ttk.Frame(dlg)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        text = tk.Text(
            body,
            height=8,
            wrap=tk.WORD,
            bg=THEME['surface_alt'],
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief=tk.FLAT,
            font=('Segoe UI', 10)
        )
        text.pack(fill=tk.BOTH, expand=True)
        text.insert('1.0', summary)
        text.config(state='disabled')

        btns = ttk.Frame(dlg)
        btns.pack(pady=12)

        def copy_summary():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(summary)
                self.root.update()
                messagebox.showinfo("Copied", "Summary copied to clipboard")
            except Exception as e:
                logger.error(f"Error copying summary: {e}")
                messagebox.showerror("Error", "Could not copy summary")

        ttk.Button(btns, text="📋 Copy", style="Accent.TButton", command=copy_summary).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Close", command=dlg.destroy).pack(side=tk.LEFT, padx=6)
    
    def _show_share_menu(self):
        """Show share menu"""
        if not self.selected_note_id:
            messagebox.showwarning("Warning", "No note selected")
            return
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✉️ Email", command=self._share_email)
        menu.add_command(label="💬 WhatsApp", command=self._share_whatsapp)
        menu.add_separator()
        menu.add_command(label="📋 Clipboard", command=self._copy_clipboard)
        menu.add_command(label="📄 Export TXT", command=self._export_txt)
        menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the application"""
    root = tk.Tk()
    app = ShorteeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
