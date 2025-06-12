
# ✨ Outfit Maker App: Your Personal Style Companion! ✨
Tired of staring at your closet, wondering what to wear? The Outfit Maker App is your personal stylist, helping you organize your wardrobe and discover fresh, stylish combinations from the clothes you already own. Say goodbye to fashion dilemmas and hello to effortless style!

# 🚀 Key Features
Complete Wardrobe Management: Easily add and manage all your clothing items, including:

Tops

Bottoms (pants, skirts, shorts)

Dresses

Outerwear (jackets, coats)

Shoes (NEW!)

Accessories

Local Photo & Data Storage: All your uploaded photos are neatly organized and saved directly on your computer in a wardrobe_photos/ directory, categorized by item type (e.g., wardrobe_photos/tops/, wardrobe_photos/shoes/). Your clothing metadata is stored in a secure local SQLite database (wardrobe.db).

Intelligent Outfit Generation: Our smart, rule-based "AI" engine generates complete, stylish outfits tailored to your existing wardrobe.

Smart Style Rules: The "AI" considers crucial factors like color harmony, formality matching, and pattern mixing to suggest aesthetically pleasing combinations.

Individual Item Swapping: Not quite right? No problem! After an outfit is generated, you can now individually change any piece (top, bottom, dress, outerwear, shoes, accessories). The app intelligently filters your wardrobe, showing only items that remain compatible with the rest of your chosen outfit.

Event-Based Styling (NEW!): Planning for a specific occasion? Select an event type (e.g., "Work/Office", "Party", "Casual Day Out") and the app's "AI" will suggest outfits whose formality aligns with your chosen event.

Outfit Saving & Loading (NEW!): Found an outfit you love? Save it with a custom name to your local database! You can easily load your favorite saved outfits back into the display anytime.

Intuitive Desktop Interface: A clean, user-friendly graphical interface built with Python's Tkinter, designed for a smooth experience on your PC.

# 🧠 How the "AI" Works (Your Built-in Stylist!)
While it's not a deep-learning AI that "sees" your clothes, our app uses a clever rule-based system that acts like a seasoned stylist. Here's the magic:

Metadata is Key: When you add an item, you provide essential tags like its main color, pattern (e.g., "solid", "striped", "floral"), and formality (e.g., "casual", "formal"). This information is the "AI's" secret sauce!

Core Outfit Structure: Every outfit always includes a top + bottom OR a dress. On top of that, it can optionally add an outerwear piece, shoes, and multiple accessories.

Styling Principles:

Formality Alignment: The "AI" ensures all items in an outfit share a similar formality level – no formal gowns with flip-flops! It also uses your selected occasion to guide formality.

Color Harmony: It's programmed to avoid jarring color clashes, favoring complementary or neutral pairings.

Pattern Balance: To keep your look cohesive, it tries to limit the number of busy patterns in a single outfit, often preferring one patterned item paired with solids.

Smart Selection: It randomly picks items from your wardrobe, but only those that strictly adhere to these styling rules and the chosen occasion. If it can't find a perfect match after several tries, it'll let you know!

# 🛠️ Technologies Under the Hood
Programming Language: Python

User Interface (GUI): Tkinter (Python's standard GUI library)

Image Processing: Pillow (PIL) for loading, resizing, and displaying your clothing photos.

Local Database: SQLite (Python's built-in sqlite3 module) for robust and persistent storage of your wardrobe data and saved outfits.

# ▶️ Getting Started (It's Easy!)
Ready to revolutionize your wardrobe? Follow these simple steps:

Save the Code: Save the provided Python code into a file named outfit_maker_app.py on your computer.

Install Pillow: If you don't have it already, open your terminal or command prompt and install the Pillow library:

pip install Pillow

Run the App: Navigate to the directory where you saved outfit_maker_app.py in your terminal or command prompt, and run:

python outfit_maker_app.py

That's it! The application will launch. It will automatically create a wardrobe.db file (for your clothing data and saved outfits) and a wardrobe_photos/ directory (for your images, organized by category) in the same location as your script.
