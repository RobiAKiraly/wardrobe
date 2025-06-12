import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import sqlite3
import os
import random
import shutil
import json # For saving outfit components as JSON string in DB

# --- Configuration ---
WARDROBE_PHOTOS_DIR = "wardrobe_photos"
DATABASE_NAME = "wardrobe.db"

# Ensure the main photos directory exists
os.makedirs(WARDROBE_PHOTOS_DIR, exist_ok=True)

# --- Database Management Class ---
class WardrobeDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        """
        Initializes the database connection and creates the clothing_items table
        and saved_outfits table if they don't already exist.
        """
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """
        Creates the clothing_items and saved_outfits tables.
        """
        # Clothing Items Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clothing_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                color TEXT NOT NULL,
                pattern TEXT NOT NULL,
                formality TEXT NOT NULL,
                image_path TEXT NOT NULL UNIQUE
            )
        ''')
        # Saved Outfits Table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_outfits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                outfit_json TEXT NOT NULL, -- Stores a JSON string of outfit component IDs/info
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_item(self, category, color, pattern, formality, source_image_path):
        """
        Adds a new clothing item to the database and copies the image to local storage.
        Args:
            category (str): Type of clothing (e.g., Top, Bottom).
            color (str): Main color of the item.
            pattern (str): Pattern of the item (e.g., Solid, Striped).
            formality (str): Formality level (e.g., Casual, Formal).
            source_image_path (str): Original file path of the image to be copied.
        Returns:
            int: The ID of the newly added item, or None if an error occurred.
        """
        # Create category subdirectory if it doesn't exist
        category_dir = os.path.join(WARDROBE_PHOTOS_DIR, category.replace(" ", "_").lower())
        os.makedirs(category_dir, exist_ok=True)

        # Generate a unique filename for the copied image
        filename = os.path.basename(source_image_path)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{os.urandom(4).hex()}{ext}" # Add random hex to ensure uniqueness
        
        destination_path = os.path.join(category_dir, unique_filename)

        try:
            shutil.copy(source_image_path, destination_path)
            # Store the relative path in the database
            relative_image_path = os.path.relpath(destination_path, start=os.getcwd())
            
            self.cursor.execute('''
                INSERT INTO clothing_items (category, color, pattern, formality, image_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (category, color.lower(), pattern, formality.lower(), relative_image_path))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Error: Item with image path {source_image_path} already exists. Skipping.")
            return None
        except Exception as e:
            print(f"Error adding item or copying image: {e}")
            # Clean up copied file if database insertion fails
            if os.path.exists(destination_path):
                os.remove(destination_path)
            return None

    def get_all_items(self):
        """
        Retrieves all clothing items from the database.
        Returns:
            list: A list of dictionaries, where each dictionary represents an item.
        """
        self.cursor.execute('SELECT id, category, color, pattern, formality, image_path FROM clothing_items')
        rows = self.cursor.fetchall()
        items = []
        for row in rows:
            items.append({
                'id': row[0],
                'category': row[1],
                'color': row[2],
                'pattern': row[3],
                'formality': row[4],
                'image_path': row[5] # This is the relative path
            })
        return items

    def delete_item(self, item_id):
        """
        Deletes a clothing item from the database by its ID and also deletes the associated image file.
        Args:
            item_id (int): The ID of the item to delete.
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            # First, get the image path from the item to be deleted
            self.cursor.execute('SELECT image_path FROM clothing_items WHERE id = ?', (item_id,))
            image_path_to_delete = self.cursor.fetchone()

            if image_path_to_delete:
                image_path = image_path_to_delete[0]
                self.cursor.execute('DELETE FROM clothing_items WHERE id = ?', (item_id,))
                self.conn.commit()
                
                # Delete the physical image file
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Deleted image file: {image_path}")
                else:
                    print(f"Warning: Image file not found at {image_path} during deletion.")
                return True
            else:
                print(f"Item with ID {item_id} not found in database.")
                return False
        except sqlite3.Error as e:
            print(f"Database error during deletion: {e}")
            return False
        except Exception as e:
            print(f"Error deleting image file: {e}")
            return False

    def save_outfit(self, outfit_name, outfit_dict):
        """
        Saves a generated outfit to the saved_outfits table.
        outfit_dict should contain item IDs and categories/types as a simple structure.
        """
        # Convert outfit_dict to a JSON string
        outfit_json = json.dumps(outfit_dict)
        try:
            self.cursor.execute('''
                INSERT INTO saved_outfits (name, outfit_json)
                VALUES (?, ?)
            ''', (outfit_name, outfit_json))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Outfit name '{outfit_name}' already exists. Please choose a different name.")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save outfit: {e}")
            return False

    def get_saved_outfits(self):
        """Retrieves all saved outfits."""
        self.cursor.execute('SELECT id, name, outfit_json, timestamp FROM saved_outfits ORDER BY timestamp DESC')
        rows = self.cursor.fetchall()
        saved_outfits = []
        for row in rows:
            saved_outfits.append({
                'id': row[0],
                'name': row[1],
                'outfit_data': json.loads(row[2]), # Parse JSON back to dict
                'timestamp': row[3]
            })
        return saved_outfits

    def delete_saved_outfit(self, outfit_id):
        """Deletes a saved outfit by its ID."""
        try:
            self.cursor.execute('DELETE FROM saved_outfits WHERE id = ?', (outfit_id,))
            self.conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete saved outfit: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        self.conn.close()

# --- Outfit Generation Logic Class ---
class OutfitGenerator:
    def __init__(self, clothing_items):
        """
        Initializes the OutfitGenerator with the current wardrobe items.
        Args:
            clothing_items (list): A list of dictionaries, each representing a clothing item.
        """
        self.items = clothing_items
        self.categories = {
            'Top': [],
            'Bottom': [],
            'Dress': [],
            'Outerwear': [],
            'Accessory': [],
            'Shoes': [],
        }
        # Populate categories for faster access
        for item in self.items:
            if item['category'] in self.categories:
                self.categories[item['category']].append(item)

    # Define formality levels (can be expanded)
    formality_levels = {
        'casual': 1,
        'smart casual': 2,
        'semi-formal': 3,
        'formal': 4,
    }

    # Occasion to formality mapping
    occasion_formality_map = {
        'Any': 0, # Wildcard, no strict filtering
        'Casual Day Out': 1,
        'Work/Office': 2,
        'Date Night': 2,
        'Party': 3,
        'Formal Event': 4,
    }

    # Basic color harmony rules (can be expanded)
    clashing_colors = {
        'red': ['orange', 'pink', 'green'],
        'orange': ['red', 'purple', 'blue'],
        'yellow': ['purple', 'brown'],
        'green': ['red', 'purple', 'brown'],
        'blue': ['orange'],
        'purple': ['yellow', 'green', 'orange'],
        'pink': ['red', 'brown'],
        'brown': ['yellow', 'green', 'pink'],
        'black': [], 'white': [], 'grey': [], 'beige': [], 'navy': []
    }

    neutral_colors = ['black', 'white', 'grey', 'beige', 'navy']

    def _get_random_element(self, arr):
        """Helper to get a random element from a list, returns None if list is empty."""
        if not arr:
            return None
        return random.choice(arr)

    def _do_colors_clash(self, color1, color2):
        """
        Checks if two colors clash based on predefined rules.
        Args:
            color1 (str): First color.
            color2 (str): Second color.
        Returns:
            bool: True if colors clash, False otherwise.
        """
        if not color1 or not color2:
            return False
        color1 = color1.lower()
        color2 = color2.lower()

        if color1 in self.neutral_colors or color2 in self.neutral_colors:
            return False

        if color1 in self.clashing_colors and color2 in self.clashing_colors[color1]:
            return True
        if color2 in self.clashing_colors and color1 in self.clashing_colors[color2]:
            return True
        return False

    def _do_formalities_match(self, item1, item2, tolerance=1):
        """
        Checks if the formality levels of two items are compatible within a tolerance.
        Args:
            item1 (dict): First clothing item.
            item2 (dict): Second clothing item.
            tolerance (int): Max difference in formality level allowed.
        Returns:
            bool: True if formalities match, False otherwise.
        """
        if not item1 or not item2 or 'formality' not in item1 or 'formality' not in item2:
            return True
        formal1 = self.formality_levels.get(item1['formality'].lower(), 0)
        formal2 = self.formality_levels.get(item2['formality'].lower(), 0)
        return abs(formal1 - formal2) <= tolerance

    def _is_item_suitable_for_occasion(self, item, occasion_formality_level):
        """
        Checks if an item's formality is suitable for the given occasion formality level.
        """
        if occasion_formality_level == 0: # 'Any' occasion, no formality filtering
            return True
        
        item_formal = self.formality_levels.get(item['formality'].lower(), 0)
        
        # Allow items that are at or slightly above/below the occasion's formality
        # For simplicity, let's say +/- 1 formality level is acceptable.
        return abs(item_formal - occasion_formality_level) <= 1


    def _do_patterns_match(self, selected_items):
        """
        Checks pattern mixing rule: allows at most one non-solid patterned item.
        Args:
            selected_items (list): List of clothing items in the current outfit attempt.
        Returns:
            bool: True if pattern rules are met, False otherwise.
        """
        patterned_items_count = 0
        for item in selected_items:
            if item and 'pattern' in item and item['pattern'].lower() != 'solid':
                patterned_items_count += 1
        return patterned_items_count <= 1

    def generate_outfit(self, occasion_type='Any'):
        """
        Generates a stylish outfit based on wardrobe items and styling rules,
        considering the specified occasion.
        Args:
            occasion_type (str): The selected occasion (e.g., 'Casual Day Out', 'Formal Event').
        Returns:
            dict or None: A dictionary representing the generated outfit, or None if no outfit could be formed.
        """
        occasion_formal_level = self.occasion_formality_map.get(occasion_type, 0) # Default to 'Any' (0)

        attempts = 0
        max_attempts = 1000 # Increased attempts for better chance of finding a combo

        while attempts < max_attempts:
            attempts += 1
            outfit = {
                'top': None,
                'bottom': None,
                'dress': None,
                'outerwear': None,
                'accessories': [],
                'shoes': None,
            }
            selected_items_for_rules = []

            # Filter categories by occasion formality initially
            available_tops = [item for item in self.categories['Top'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]
            available_bottoms = [item for item in self.categories['Bottom'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]
            available_dresses = [item for item in self.categories['Dress'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]
            available_outerwear = [item for item in self.categories['Outerwear'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]
            available_shoes = [item for item in self.categories['Shoes'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]
            available_accessories = [item for item in self.categories['Accessory'] if self._is_item_suitable_for_occasion(item, occasion_formal_level)]


            # 1. Select a Top or a Dress (mutually exclusive)
            use_dress = False
            if available_dresses and (not available_tops or random.random() < 0.3):
                outfit['dress'] = self._get_random_element(available_dresses)
                if outfit['dress']:
                    selected_items_for_rules.append(outfit['dress'])
                    use_dress = True
            
            if not use_dress:
                outfit['top'] = self._get_random_element(available_tops)
                outfit['bottom'] = self._get_random_element(available_bottoms)

                if outfit['top'] and outfit['bottom']:
                    if not self._do_formalities_match(outfit['top'], outfit['bottom']) or \
                       self._do_colors_clash(outfit['top']['color'], outfit['bottom']['color']):
                        continue
                    selected_items_for_rules.extend([outfit['top'], outfit['bottom']])
                else:
                    if not outfit['dress']:
                        continue
            else:
                outfit['top'] = None
                outfit['bottom'] = None

            if not selected_items_for_rules:
                return None

            # 2. Select Optional Outerwear
            if available_outerwear:
                potential_outerwear = self._get_random_element(available_outerwear)
                base_item = outfit['dress'] if outfit['dress'] else outfit['top']
                if base_item and self._do_formalities_match(base_item, potential_outerwear) and \
                   not self._do_colors_clash(base_item['color'], potential_outerwear['color']):
                    outfit['outerwear'] = potential_outerwear
                    selected_items_for_rules.append(outfit['outerwear'])

            # 3. Select Optional Shoes
            if available_shoes:
                potential_shoes = self._get_random_element(available_shoes)
                base_item_for_shoes = outfit['dress'] if outfit['dress'] else (outfit['bottom'] or outfit['top'])
                
                if base_item_for_shoes and self._do_formalities_match(base_item_for_shoes, potential_shoes) and \
                   not self._do_colors_clash(base_item_for_shoes['color'], potential_shoes['color']):
                    outfit['shoes'] = potential_shoes
                    selected_items_for_rules.append(outfit['shoes'])


            # 4. Select Optional Accessories
            if available_accessories:
                num_accessories = random.randint(0, min(len(available_accessories), 3))
                selected_accessory_ids = set()
                for _ in range(num_accessories):
                    accessory = self._get_random_element(available_accessories)
                    if accessory and accessory['id'] not in selected_accessory_ids:
                        base_item_for_acc = outfit['dress'] if outfit['dress'] else outfit['top']
                        if base_item_for_acc and self._do_formalities_match(base_item_for_acc, accessory) and \
                           not self._do_colors_clash(base_item_for_acc['color'], accessory['color']):
                            outfit['accessories'].append(accessory)
                            selected_items_for_rules.append(accessory)
                            selected_accessory_ids.add(accessory['id'])

            # Final check for pattern mixing across all selected items
            if self._do_patterns_match(selected_items_for_rules):
                return outfit

        return None # No suitable outfit found after max attempts

# --- Tkinter Application ---
class OutfitMakerApp:
    def __init__(self, master):
        """
        Initializes the Tkinter application window and components.
        """
        self.master = master
        master.title("Outfit Maker PC App")
        master.geometry("1000x800") # Set initial window size
        master.resizable(True, True) # Allow window resizing
        master.configure(bg="#f0f2f5") # Light background

        self.db = WardrobeDatabase()
        self.clothing_items = []
        self.load_items()

        self.generated_outfit = None # Store the currently generated outfit

        # Set up styles for consistent look
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'
        self.style.configure('TFrame', background='#ffffff')
        self.style.configure('TLabel', background='#ffffff', font=('Inter', 10))
        self.style.configure('TButton', font=('Inter', 10, 'bold'), padding=8, relief="flat", background='#6a1b9a', foreground='white')
        self.style.map('TButton', background=[('active', '#8e24aa')])
        self.style.configure('TCombobox', font=('Inter', 10), fieldbackground='white', background='white', selectbackground='#ede7f6', selectforeground='black')


        # --- Main Layout (PanedWindow for resizable sections) ---
        self.main_pane = tk.PanedWindow(master, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#f0f2f5")
        self.main_pane.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)

        # --- Left Frame: Wardrobe Management ---
        self.wardrobe_frame = ttk.Frame(self.main_pane, padding="20 20 20 20", relief="solid", borderwidth=1, style='TFrame')
        self.main_pane.add(self.wardrobe_frame, minsize=400) # Give min size to left pane

        self.wardrobe_frame.grid_columnconfigure(0, weight=1)
        self.wardrobe_frame.grid_columnconfigure(1, weight=1) # Ensure both columns can expand

        tk.Label(self.wardrobe_frame, text="Manage Your Wardrobe", font=("Inter", 22, "bold"), fg="#6a1b9a", bg="#ffffff").grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

        # Item Photo Upload
        self.image_path_var = tk.StringVar() 
        tk.Label(self.wardrobe_frame, text="Item Photo:", style='TLabel').grid(row=1, column=0, sticky="w", pady=5)
        tk.Button(self.wardrobe_frame, text="Browse Image", command=self.browse_image, style='TButton').grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        self.image_preview_label = tk.Label(self.wardrobe_frame, bg="#f8f8f8", relief="solid", borderwidth=1, text="Image Preview", font=("Inter", 10), fg="#888888")
        self.image_preview_label.grid(row=2, column=0, columnspan=2, pady=10, sticky="nsew")
        self.wardrobe_frame.grid_rowconfigure(2, weight=1) # Allow image preview to expand

        # Item Details Entry
        self.category_var = tk.StringVar(value="Top")
        tk.Label(self.wardrobe_frame, text="Category:", style='TLabel').grid(row=3, column=0, sticky="w", pady=5)
        # Updated category list to include "Shoes"
        ttk.Combobox(self.wardrobe_frame, textvariable=self.category_var,
                     values=["Top", "Bottom", "Dress", "Outerwear", "Accessory", "Shoes"], state="readonly", style='TCombobox').grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        self.color_var = tk.StringVar()
        tk.Label(self.wardrobe_frame, text="Main Color:", style='TLabel').grid(row=4, column=0, sticky="w", pady=5)
        tk.Entry(self.wardrobe_frame, textvariable=self.color_var, width=30).grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        self.pattern_var = tk.StringVar(value="Solid")
        tk.Label(self.wardrobe_frame, text="Pattern:", style='TLabel').grid(row=5, column=0, sticky="w", pady=5)
        ttk.Combobox(self.wardrobe_frame, textvariable=self.pattern_var,
                     values=["Solid", "Striped", "Floral", "Plaid", "Polka Dot", "Geometric", "Other"], state="readonly", style='TCombobox').grid(row=5, column=1, sticky="ew", padx=5, pady=5)

        self.formality_var = tk.StringVar(value="Casual")
        tk.Label(self.wardrobe_frame, text="Formality:", style='TLabel').grid(row=6, column=0, sticky="w", pady=5)
        ttk.Combobox(self.wardrobe_frame, textvariable=self.formality_var,
                     values=["Casual", "Smart Casual", "Semi-Formal", "Formal"], state="readonly", style='TCombobox').grid(row=6, column=1, sticky="ew", padx=5, pady=5)

        tk.Button(self.wardrobe_frame, text="Add Item to Wardrobe", command=self.add_item, style='TButton').grid(row=7, column=0, columnspan=2, pady=10, sticky="ew")

        # Wardrobe List Display
        tk.Label(self.wardrobe_frame, text="Your Current Wardrobe", font=("Inter", 16, "bold"), fg="#6a1b9a", bg="#ffffff").grid(row=8, column=0, columnspan=2, pady=10, sticky="ew")

        # Treeview for displaying items
        self.wardrobe_tree = ttk.Treeview(self.wardrobe_frame, columns=("Category", "Color", "Formality"), show="headings", height=8)
        self.wardrobe_tree.heading("Category", text="Category")
        self.wardrobe_tree.heading("Color", text="Color")
        self.wardrobe_tree.heading("Formality", text="Formality")
        
        self.wardrobe_tree.column("Category", width=100, anchor="center")
        self.wardrobe_tree.column("Color", width=100, anchor="center")
        self.wardrobe_tree.column("Formality", width=100, anchor="center")
        
        self.wardrobe_tree.grid(row=9, column=0, columnspan=2, sticky="nsew")
        
        # Scrollbar for the Treeview
        tree_scrollbar_y = ttk.Scrollbar(self.wardrobe_frame, orient="vertical", command=self.wardrobe_tree.yview)
        tree_scrollbar_y.grid(row=9, column=2, sticky="ns")
        self.wardrobe_tree.configure(yscrollcommand=tree_scrollbar_y.set)

        self.wardrobe_frame.grid_rowconfigure(9, weight=2) # Allow wardrobe list to expand

        tk.Button(self.wardrobe_frame, text="Delete Selected Item", command=self.delete_selected_item, style='TButton', background='#e53935', foreground='white').grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")
        self.style.map('Delete.TButton', background=[('active', '#ef5350')], style='Delete.TButton') # Style for delete button

        self.populate_wardrobe_tree()

        # --- Right Frame: Outfit Generation ---
        self.outfit_frame = ttk.Frame(self.main_pane, padding="20 20 20 20", relief="solid", borderwidth=1, style='TFrame')
        self.main_pane.add(self.outfit_frame, minsize=400) # Give min size to right pane

        self.outfit_frame.grid_columnconfigure(0, weight=1)
        self.outfit_frame.grid_columnconfigure(1, weight=1) # For the new clear outfit button

        tk.Label(self.outfit_frame, text="Generate Outfit", font=("Inter", 22, "bold"), fg="#6a1b9a", bg="#ffffff").grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Occasion selection
        self.occasion_var = tk.StringVar(value="Any")
        tk.Label(self.outfit_frame, text="Occasion:", style='TLabel').grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Combobox(self.outfit_frame, textvariable=self.occasion_var,
                     values=list(OutfitGenerator.occasion_formality_map.keys()), state="readonly", style='TCombobox').grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Buttons for outfit generation and clearing
        tk.Button(self.outfit_frame, text="Suggest an Outfit!", command=self.generate_outfit, style='TButton', background='#43a047').grid(row=2, column=0, pady=10, sticky="ew")
        self.style.map('Generate.TButton', background=[('active', '#66bb6a')], style='Generate.TButton') 

        tk.Button(self.outfit_frame, text="Clear Outfit", command=self.clear_outfit_display, style='TButton', background='#ff9800').grid(row=2, column=1, pady=10, sticky="ew", padx=(5,0)) 
        self.style.map('ClearOutfit.TButton', background=[('active', '#fb8c00')], style='ClearOutfit.TButton') 

        # Button to save current outfit
        tk.Button(self.outfit_frame, text="Save Current Outfit", command=self.save_current_outfit, style='TButton', background='#2196f3').grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        self.style.map('SaveOutfit.TButton', background=[('active', '#1976D2')], style='SaveOutfit.TButton') 

        # Button to view saved outfits
        tk.Button(self.outfit_frame, text="View Saved Outfits", command=self.open_saved_outfits_dialog, style='TButton', background='#9C27B0').grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")
        self.style.map('ViewSavedOutfits.TButton', background=[('active', '#7B1FA2')], style='ViewSavedOutfits.TButton') 


        # Outfit Display Area
        self.outfit_display_frame = ttk.Frame(self.outfit_frame, padding="10", style='TFrame', relief="groove", borderwidth=1)
        self.outfit_display_frame.grid(row=5, column=0, columnspan=2, pady=20, sticky="nsew")
        self.outfit_display_frame.grid_columnconfigure(0, weight=1)
        self.outfit_display_frame.grid_columnconfigure(1, weight=1)
        self.outfit_frame.grid_rowconfigure(5, weight=1) # Allow outfit display to expand

        tk.Label(self.outfit_display_frame, text="Your Suggested Outfit:", font=("Inter", 16, "bold"), fg="#424242", bg="#ffffff").grid(row=0, column=0, columnspan=2, pady=10)

        # Image placeholders for outfit items
        self.outfit_photos = {} # Store PhotoImage references
        self.outfit_labels = {} # Store Tkinter Label widgets
        self.accessory_image_labels = [] # To store accessory image labels for clearing
        self.change_buttons = {} # Store change buttons

        # Define item display positions and labels for clarity
        outfit_positions = {
            'top': (1, 0, "Top"),
            'bottom': (1, 1, "Bottom"),
            'dress': (2, 0, "Dress", 2), # Row, Col, Label, Colspan for dress
            'outerwear': (3, 0, "Outerwear"),
            'shoes': (3, 1, "Shoes"),
            'accessories': (4, 0, "Accessories", 2)
        }

        # Create widgets for each outfit component
        for item_type, (row, col, label_text, *colspan_val) in outfit_positions.items():
            colspan = colspan_val[0] if colspan_val else 1
            
            container = ttk.Frame(self.outfit_display_frame, style='TFrame', relief="solid", borderwidth=1, padding=5)
            container.grid(row=row, column=col, columnspan=colspan, padx=5, pady=5, sticky="nsew")
            container.grid_columnconfigure(0, weight=1)
            container.grid_rowconfigure(2, weight=1)

            tk.Label(container, text=label_text, font=("Inter", 12, "bold"), bg="#ffffff").grid(row=0, column=0, pady=2, sticky="ew")
            
            self.outfit_labels[item_type + "_info"] = tk.Label(container, text="No item selected", bg="#ffffff", wraplength=150, font=("Inter", 9))
            self.outfit_labels[item_type + "_info"].grid(row=1, column=0, pady=2, sticky="ew")
            
            if item_type != 'accessories':
                self.outfit_labels[item_type] = tk.Label(container, bg="#f0f0f0", relief="groove")
                self.outfit_labels[item_type].grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
                change_btn = tk.Button(container, text="Change", command=lambda t=item_type: self.open_change_item_dialog(t),
                                       style='TButton', background='#42a5f5', foreground='white')
                change_btn.grid(row=3, column=0, pady=5, sticky="ew")
                self.style.map('ChangeItem.TButton', background=[('active', '#2196f3')])
                self.change_buttons[item_type] = change_btn
            else:
                self.accessory_image_frame = ttk.Frame(container, style='TFrame')
                self.accessory_image_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
                change_btn = tk.Button(container, text="Change Accessories", command=lambda t=item_type: self.open_change_item_dialog(t),
                                       style='TButton', background='#42a5f5', foreground='white')
                change_btn.grid(row=3, column=0, pady=5, sticky="ew")
                self.change_buttons[item_type] = change_btn

        self.initial_outfit_display_state()

    def _create_placeholder_photo(self, color, size, text=""):
        """
        Helper to create a solid colored placeholder image with optional text.
        """
        img = Image.new('RGB', size, color=color)
        if text:
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", size=size[0]//5) 
            except IOError:
                font = ImageFont.load_default()
            
            text_bbox = d.textbbox((0,0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (size[0] - text_width) / 2
            y = (size[1] - text_height) / 2
            d.text((x, y), text, fill=(0,0,0), font=font)
        return ImageTk.PhotoImage(img)

    def initial_outfit_display_state(self):
        """Sets initial placeholder images/text for the outfit display area."""
        item_types_display_sizes = {
            'top': (150, 150), 'bottom': (150, 150), 'dress': (200, 200),
            'outerwear': (150, 150), 'shoes': (150, 150), 'accessory': (70, 70)
        }

        self.placeholder_photos = {
            'top': self._create_placeholder_photo("#D1C4E9", item_types_display_sizes['top'], text="TOP"),
            'bottom': self._create_placeholder_photo("#E1BEE7", item_types_display_sizes['bottom'], text="BOTTOM"),
            'dress': self._create_placeholder_photo("#F8BBD0", item_types_display_sizes['dress'], text="DRESS"),
            'outerwear': self._create_placeholder_photo("#BBDEFB", item_types_display_sizes['outerwear'], text="OUTERWEAR"),
            'shoes': self._create_placeholder_photo("#C8E6C9", item_types_display_sizes['shoes'], text="SHOES"),
            'accessory': self._create_placeholder_photo("#FFF9C4", item_types_display_sizes['accessory'], text="ACC")
        }

        for item_type in ['top', 'bottom', 'outerwear', 'dress', 'shoes']:
            label_key = item_type
            info_label_key = item_type + "_info"
            
            self.outfit_labels[info_label_key].config(text=f"No {item_type} selected")
            self.outfit_labels[label_key].config(image=self.placeholder_photos[item_type])
            self.outfit_photos[label_key] = self.placeholder_photos[item_type] 

        self.outfit_labels['accessories_info'].config(text="No accessories")
        for widget in self.accessory_image_frame.winfo_children():
            widget.destroy()
        self.accessory_image_labels = []
        
        for btn in self.change_buttons.values():
            btn.grid_forget()
        
        self.generated_outfit = None

    def browse_image(self):
        """
        Opens a file dialog for the user to select an image file.
        Updates the image_path_var variable and displays a preview.
        """
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if file_path:
            self.image_path_var.set(file_path)
            try:
                img = Image.open(file_path)
                img.thumbnail((200, 200), Image.LANCZOS)
                self.current_preview_photo = ImageTk.PhotoImage(img)
                self.image_preview_label.config(image=self.current_preview_photo, text="")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load image: {e}")
                self.image_preview_label.config(image=None, text="Image Preview Error")

    def add_item(self):
        """
        Adds a new clothing item to the database and updates the wardrobe display.
        """
        category = self.category_var.get()
        color = self.color_var.get().strip()
        pattern = self.pattern_var.get()
        formality = self.formality_var.get()
        source_image_path = self.image_path_var.get()

        if not all([category, color, pattern, formality, source_image_path]):
            messagebox.showwarning("Missing Info", "Please fill in all fields and select an image.")
            return

        item_id = self.db.add_item(category, color, pattern, formality, source_image_path)
        if item_id is not None:
            messagebox.showinfo("Success", f"Item '{category}' added with ID: {item_id}")
            self.load_items()
            self.clear_add_item_form()
        else:
            messagebox.showerror("Error", "Failed to add item. It might already exist or there was a file error.")


    def clear_add_item_form(self):
        """Clears the add item form after submission."""
        self.category_var.set("Top")
        self.color_var.set("")
        self.pattern_var.set("Solid")
        self.formality_var.set("Casual")
        self.image_path_var.set("")
        self.image_preview_label.config(image=None, text="Image Preview")
        self.current_preview_photo = None

    def load_items(self):
        """Loads all clothing items from the database into memory."""
        self.clothing_items = self.db.get_all_items()
        self.populate_wardrobe_tree()

    def populate_wardrobe_tree(self):
        """Populates the Treeview widget with current wardrobe items."""
        for item in self.wardrobe_tree.get_children():
            self.wardrobe_tree.delete(item)

        if not self.clothing_items:
            self.wardrobe_tree.insert("", "end", values=("No items yet", "", ""))
            return

        for item in self.clothing_items:
            self.wardrobe_tree.insert("", "end", iid=item['id'],
                                       values=(item['category'], item['color'].title(), item['formality'].title()))

    def delete_selected_item(self):
        """Deletes the selected item from the database and updates the display."""
        selected_item_id = self.wardrobe_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select an item to delete.")
            return

        response = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this item?")
        if response:
            if self.db.delete_item(selected_item_id):
                messagebox.showinfo("Deleted", "Item deleted successfully.")
                self.load_items()
                self.clear_outfit_display()
            else:
                messagebox.showerror("Error", "Failed to delete item.")

    def generate_outfit(self):
        """
        Generates and displays an outfit based on the current wardrobe.
        """
        if not self.clothing_items:
            messagebox.showwarning("No Wardrobe", "Please add some clothing items first to generate an outfit!")
            self.clear_outfit_display()
            return

        selected_occasion = self.occasion_var.get()
        generator = OutfitGenerator(self.clothing_items)
        outfit = generator.generate_outfit(occasion_type=selected_occasion)

        if outfit:
            self.generated_outfit = outfit
            self.display_outfit(outfit)
            messagebox.showinfo("Outfit Generated", "Here's a stylish outfit for you!")
            for btn in self.change_buttons.values():
                btn.grid()
        else:
            messagebox.showwarning("No Outfit Found", "Could not generate a stylish outfit with your current wardrobe. Try adding more diverse items or change the occasion filter!")
            self.clear_outfit_display()

    def save_current_outfit(self):
        """Saves the currently displayed outfit to the database."""
        if not self.generated_outfit:
            messagebox.showwarning("No Outfit", "Please generate an outfit first before saving.")
            return

        outfit_name = simpledialog.askstring("Save Outfit", "Enter a name for this outfit:", parent=self.master)
        if outfit_name:
            # Prepare a simplified outfit dictionary for saving (only item IDs and category)
            # This allows retrieving details from clothing_items table later
            outfit_to_save = {}
            for k, v in self.generated_outfit.items():
                if isinstance(v, dict) and 'id' in v: # Main items
                    outfit_to_save[k] = {'id': v['id'], 'category': v['category']}
                elif isinstance(v, list): # Accessories
                    outfit_to_save[k] = [{'id': acc['id'], 'category': acc['category']} for acc in v if 'id' in acc]
            
            if self.db.save_outfit(outfit_name, outfit_to_save):
                messagebox.showinfo("Saved", f"Outfit '{outfit_name}' saved successfully!")
            else:
                pass # Error message already handled by db.save_outfit

    def open_saved_outfits_dialog(self):
        """Opens a dialog to view, load, and delete saved outfits."""
        dialog = tk.Toplevel(self.master)
        dialog.title("Saved Outfits")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.geometry("700x500")
        dialog.configure(bg="#f0f2f5")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        tk.Label(dialog, text="Your Saved Outfits:", font=("Inter", 16, "bold"), fg="#6a1b9a", bg="#f0f2f5").grid(row=0, column=0, columnspan=2, pady=10)

        saved_outfits_tree = ttk.Treeview(dialog, columns=("Name", "Date Saved"), show="headings", height=10)
        saved_outfits_tree.heading("Name", text="Outfit Name")
        saved_outfits_tree.heading("Date Saved", text="Date Saved")
        saved_outfits_tree.column("Name", width=250, anchor="w")
        saved_outfits_tree.column("Date Saved", width=200, anchor="center")
        saved_outfits_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        tree_scrollbar_y = ttk.Scrollbar(dialog, orient="vertical", command=saved_outfits_tree.yview)
        tree_scrollbar_y.grid(row=1, column=2, sticky="ns")
        saved_outfits_tree.configure(yscrollcommand=tree_scrollbar_y.set)

        def populate_saved_outfits_tree():
            for item in saved_outfits_tree.get_children():
                saved_outfits_tree.delete(item)
            saved_outfits = self.db.get_saved_outfits()
            if not saved_outfits:
                saved_outfits_tree.insert("", "end", values=("No saved outfits yet.", ""))
                return
            for outfit in saved_outfits:
                saved_outfits_tree.insert("", "end", iid=outfit['id'],
                                           values=(outfit['name'], outfit['timestamp']))
        
        populate_saved_outfits_tree()

        # Action buttons
        button_frame = ttk.Frame(dialog, style='TFrame')
        button_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)

        def load_selected_outfit():
            selected_id = saved_outfits_tree.focus()
            if not selected_id:
                messagebox.showwarning("No Selection", "Please select an outfit to load.")
                return
            
            saved_outfits = self.db.get_saved_outfits()
            selected_outfit_data = next((o['outfit_data'] for o in saved_outfits if str(o['id']) == selected_id), None)
            
            if selected_outfit_data:
                # Reconstruct the full outfit dict using clothing_items in memory
                loaded_outfit = {}
                all_items_by_id = {item['id']: item for item in self.clothing_items} # Map item IDs to full item data

                for k, v in selected_outfit_data.items():
                    if k == 'accessories':
                        loaded_outfit[k] = [all_items_by_id.get(acc_info['id']) for acc_info in v if all_items_by_id.get(acc_info['id'])]
                    elif isinstance(v, dict) and 'id' in v:
                        loaded_outfit[k] = all_items_by_id.get(v['id'])
                
                # Check if all items in the loaded outfit are still in the wardrobe
                is_valid = True
                for part in ['top', 'bottom', 'dress', 'outerwear', 'shoes']:
                    if loaded_outfit.get(part) is not None and loaded_outfit[part]['id'] not in all_items_by_id:
                        is_valid = False
                        break
                for acc in loaded_outfit.get('accessories', []):
                    if acc['id'] not in all_items_by_id:
                        is_valid = False
                        break

                if is_valid:
                    self.generated_outfit = loaded_outfit
                    self.display_outfit(self.generated_outfit)
                    messagebox.showinfo("Loaded", "Outfit loaded successfully into main display.")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "One or more items in this saved outfit are no longer in your wardrobe. Please ensure all original items exist.")
            else:
                messagebox.showerror("Error", "Failed to load outfit data.")

        def delete_selected_saved_outfit():
            selected_id = saved_outfits_tree.focus()
            if not selected_id:
                messagebox.showwarning("No Selection", "Please select an outfit to delete.")
                return
            
            response = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this saved outfit?")
            if response:
                if self.db.delete_saved_outfit(selected_id):
                    messagebox.showinfo("Deleted", "Saved outfit deleted successfully.")
                    populate_saved_outfits_tree() # Refresh list
                    self.clear_outfit_display() # Clear current display if it was the deleted one
                else:
                    messagebox.showerror("Error", "Failed to delete saved outfit.")

        tk.Button(button_frame, text="Load Outfit", command=load_selected_outfit, style='TButton', background='#4CAF50').grid(row=0, column=0, sticky="ew", padx=5)
        tk.Button(button_frame, text="Delete Outfit", command=delete_selected_saved_outfit, style='TButton', background='#E53935').grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(button_frame, text="Close", command=dialog.destroy, style='TButton', background='#757575').grid(row=0, column=2, sticky="ew", padx=5)

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.master.wait_window(dialog)

    def display_outfit(self, outfit):
        """
        Displays the generated outfit in the right panel.
        Args:
            outfit (dict): A dictionary containing the selected clothing items.
        """
        if self.generated_outfit is None:
            self.clear_outfit_display()
            return

        item_types_display_sizes = {
            'top': (150, 150), 'bottom': (150, 150), 'dress': (200, 200),
            'outerwear': (150, 150), 'shoes': (150, 150), 'accessory': (70, 70)
        }

        for item_type in ['top', 'bottom', 'dress', 'outerwear', 'shoes']:
            item = outfit.get(item_type)
            label_key = item_type
            info_label_key = item_type + "_info"
            
            if item:
                try:
                    img = Image.open(item['image_path'])
                    img.thumbnail(item_types_display_sizes[item_type], Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.outfit_labels[label_key].config(image=photo)
                    self.outfit_photos[label_key] = photo
                    self.outfit_labels[info_label_key].config(text=f"{item['color'].title()} {item['pattern']}\n({item['formality'].title()})")
                except FileNotFoundError:
                    photo = self._create_placeholder_photo('lightgray', item_types_display_sizes[item_type], text="Image Missing")
                    self.outfit_labels[label_key].config(image=photo)
                    self.outfit_photos[label_key] = photo
                    self.outfit_labels[info_label_key].config(text=f"Image Missing for {item_type.title()}")
                except Exception as e:
                    photo = self._create_placeholder_photo('pink', item_types_display_sizes[item_type], text=f"Error: {e}")
                    self.outfit_labels[label_key].config(image=photo)
                    self.outfit_photos[label_key] = photo
                    self.outfit_labels[info_label_key].config(text=f"Image Error for {item_type.title()}")
            else:
                self.outfit_labels[label_key].config(image=self.placeholder_photos[item_type])
                self.outfit_photos[label_key] = self.placeholder_photos[item_type]
                self.outfit_labels[info_label_key].config(text=f"No {item_type} selected")

        accessories_text = []
        for widget in self.accessory_image_frame.winfo_children():
            widget.destroy()
        self.accessory_image_labels = []

        for i, acc in enumerate(outfit['accessories']):
            try:
                img = Image.open(acc['image_path'])
                img.thumbnail(item_types_display_sizes['accessory'], Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.outfit_photos[f'accessory_{i}'] = photo

                acc_container = ttk.Frame(self.accessory_image_frame, style='TFrame', relief="solid", borderwidth=1, padding=2)
                acc_container.grid(row=0, column=i, padx=3, pady=3, sticky="nsew")
                acc_container.grid_rowconfigure(0, weight=1)
                acc_container.grid_rowconfigure(1, weight=0)
                acc_container.grid_columnconfigure(0, weight=1)

                acc_label = tk.Label(acc_container, image=photo, bg="#ffffff")
                acc_label.grid(row=0, column=0, sticky="nsew")
                
                acc_info_label = tk.Label(acc_container, text=f"{acc['color'].title()}\n({acc['formality'].title()})", bg="#ffffff", font=("Inter", 8), wraplength=70)
                acc_info_label.grid(row=1, column=0, sticky="ew")

                accessories_text.append(f"{acc['color'].title()} {acc['category']}")
                self.accessory_image_labels.append(acc_label)

            except FileNotFoundError:
                photo = self._create_placeholder_photo('lightgray', item_types_display_sizes['accessory'], text="Missing")
                self.outfit_photos[f'accessory_{i}'] = photo

                acc_container = ttk.Frame(self.accessory_image_frame, style='TFrame', relief="solid", borderwidth=1, padding=2)
                acc_container.grid(row=0, column=i, padx=3, pady=3, sticky="nsew")
                acc_container.grid_rowconfigure(0, weight=1)
                acc_container.grid_rowconfigure(1, weight=0)
                acc_container.grid_columnconfigure(0, weight=1)
                acc_label = tk.Label(acc_container, image=photo, bg="#ffffff")
                acc_label.grid(row=0, column=0, sticky="nsew")
                acc_info_label = tk.Label(acc_container, text="Image Missing", bg="#ffffff", font=("Inter", 8))
                acc_info_label.grid(row=1, column=0, sticky="ew")
                accessories_text.append(f"Missing image for {acc['category']}")
                self.accessory_image_labels.append(acc_label)

            except Exception as e:
                photo = self._create_placeholder_photo('pink', item_types_display_sizes['accessory'], text=f"Error: {e}")
                self.outfit_photos[f'accessory_{i}'] = photo

                acc_container = ttk.Frame(self.accessory_image_frame, style='TFrame', relief="solid", borderwidth=1, padding=2)
                acc_container.grid(row=0, column=i, padx=3, pady=3, sticky="nsew")
                acc_container.grid_rowconfigure(0, weight=1)
                acc_container.grid_rowconfigure(1, weight=0)
                acc_container.grid_columnconfigure(0, weight=1)
                acc_label = tk.Label(acc_container, image=photo, bg="#ffffff")
                acc_label.grid(row=0, column=0, sticky="nsew")
                acc_info_label = tk.Label(acc_container, text=f"Error: {e}", bg="#ffffff", font=("Inter", 8), wraplength=70)
                acc_info_label.grid(row=1, column=0, sticky="ew")
                accessories_text.append(f"Error for {acc['category']}")
                self.accessory_image_labels.append(acc_label)


        if accessories_text:
            self.outfit_labels['accessories_info'].config(text="Accessories: " + ", ".join(accessories_text))
        else:
            self.outfit_labels['accessories_info'].config(text="No accessories")
        
        for col_idx in range(self.accessory_image_frame.grid_size()[0]):
            self.accessory_image_frame.grid_columnconfigure(col_idx, weight=0)
        for col_idx in range(len(outfit['accessories'])):
            self.accessory_image_frame.grid_columnconfigure(col_idx, weight=1)

    def clear_outfit_display(self):
        """Clears the displayed outfit."""
        self.initial_outfit_display_state()
        for widget in self.accessory_image_frame.winfo_children():
            widget.destroy() 
        self.accessory_image_labels = []
        
        for btn in self.change_buttons.values():
            btn.grid_forget()

    def open_change_item_dialog(self, item_type_to_change):
        """
        Opens a new dialog window to allow the user to select a replacement item
        for a specific category in the current outfit.
        """
        if not self.generated_outfit:
            messagebox.showwarning("No Outfit", "Please generate an outfit first before trying to change an item.")
            return

        dialog = tk.Toplevel(self.master)
        dialog.title(f"Change {item_type_to_change.title()}")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.geometry("600x400")
        dialog.configure(bg="#f0f2f5")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        tk.Label(dialog, text=f"Select a new {item_type_to_change.title()}:",
                 font=("Inter", 14, "bold"), bg="#f0f2f5", fg="#6a1b9a").grid(row=0, column=0, pady=10)

        change_tree = ttk.Treeview(dialog, columns=("Color", "Pattern", "Formality"), show="headings", height=10)
        change_tree.heading("Color", text="Color")
        change_tree.heading("Pattern", text="Pattern")
        change_tree.heading("Formality", text="Formality")
        change_tree.column("Color", width=100, anchor="center")
        change_tree.column("Pattern", width=100, anchor="center")
        change_tree.column("Formality", width=100, anchor="center")
        change_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        tree_scrollbar_y = ttk.Scrollbar(dialog, orient="vertical", command=change_tree.yview)
        tree_scrollbar_y.grid(row=1, column=1, sticky="ns")
        change_tree.configure(yscrollcommand=tree_scrollbar_y.set)

        compatible_items = []
        outfit_generator_instance = OutfitGenerator(self.clothing_items)

        # Get the formality level of the current occasion selection
        current_occasion_formal_level = outfit_generator_instance.occasion_formality_map.get(self.occasion_var.get(), 0)

        for item in self.clothing_items:
            # Check if category matches the type to change
            if item['category'].lower() != item_type_to_change.lower():
                if item_type_to_change.lower() == 'accessories' and item['category'].lower() == 'accessory':
                    pass
                else:
                    continue

            # Also filter by occasion suitability
            if not outfit_generator_instance._is_item_suitable_for_occasion(item, current_occasion_formal_level):
                continue


            is_compatible = True
            current_outfit_copy = self.generated_outfit.copy()
            
            if item_type_to_change != 'accessories':
                current_outfit_copy[item_type_to_change] = item
            else:
                current_outfit_copy['accessories'] = [item]

            proposed_outfit_items = []
            if current_outfit_copy['top']: proposed_outfit_items.append(current_outfit_copy['top'])
            if current_outfit_copy['bottom']: proposed_outfit_items.append(current_outfit_copy['bottom'])
            if current_outfit_copy['dress']: proposed_outfit_items.append(current_outfit_copy['dress'])
            if current_outfit_copy['outerwear']: proposed_outfit_items.append(current_outfit_copy['outerwear'])
            if current_outfit_copy['shoes']: proposed_outfit_items.append(current_outfit_copy['shoes'])
            proposed_outfit_items.extend(current_outfit_copy['accessories'])

            for i in range(len(proposed_outfit_items)):
                for j in range(i + 1, len(proposed_outfit_items)):
                    item1 = proposed_outfit_items[i]
                    item2 = proposed_outfit_items[j]

                    if outfit_generator_instance._do_colors_clash(item1['color'], item2['color']):
                        is_compatible = False
                        break
                    if not outfit_generator_instance._do_formalities_match(item1, item2):
                        is_compatible = False
                        break
                if not is_compatible:
                    break

            if not is_compatible:
                continue

            if not outfit_generator_instance._do_patterns_match(proposed_outfit_items):
                is_compatible = False
            
            if is_compatible:
                compatible_items.append(item)
                change_tree.insert("", "end", iid=item['id'],
                                   values=(item['color'].title(), item['pattern'], item['formality'].title()))

        if not compatible_items:
            tk.Label(dialog, text="No compatible items found in your wardrobe for this category.",
                     bg="#f0f2f5", fg="red").grid(row=2, column=0, pady=10)

        def select_item():
            selected_id = change_tree.focus()
            if not selected_id:
                messagebox.showwarning("No Selection", "Please select an item.")
                return

            selected_item = next((item for item in compatible_items if str(item['id']) == selected_id), None)
            
            if selected_item:
                if item_type_to_change != 'accessories':
                    if item_type_to_change == 'dress':
                        self.generated_outfit['top'] = None
                        self.generated_outfit['bottom'] = None
                    elif self.generated_outfit['dress'] and (item_type_to_change == 'top' or item_type_to_change == 'bottom'):
                        self.generated_outfit['dress'] = None
                    
                    self.generated_outfit[item_type_to_change] = selected_item
                else:
                    self.generated_outfit['accessories'] = [selected_item] # For simplicity, replace all
                
                self.display_outfit(self.generated_outfit) 
                dialog.destroy()
            else:
                messagebox.showwarning("Error", "Could not find selected item details.")


        tk.Button(dialog, text="Select Item", command=select_item, style='TButton', background='#4CAF50', foreground='white').grid(row=3, column=0, pady=10, sticky="ew")
        self.style.map('SelectItem.TButton', background=[('active', '#81C784')])

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.master.wait_window(dialog)

    def on_closing(self):
        """Handles graceful closing of the application."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.db.close()
            self.master.destroy()

# --- Main execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = OutfitMakerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
