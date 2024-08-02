# NeonAbyssDescriptor

## Description

Displays an overlay showing neon-abyss items descriptions.

## Usage

Run the build executable, or the main.py file via `python main.py`.
A small overlay should be displayed to the top left corner of the screen.

In game, when items are displayed, place the mouse to the top-left corner of the item, press the **Right CTRL** key while moving the mouse to the bottom-right corner of the item and release the **Right CTRL** key.
The rectangle drawn around the item **must include** the **whole object**.

You can leave a margin around the item if necessary.

You can draw a rectangle that includes many items. In that case, all the items description will appear in the overlay.

The time took by the overlay to find items is proportional to the rectangle area.

To clear the overlay, move your mouse over.

To exit the overlay, click on it !


## Configuration

The file `neondb\config.js` allows to configure the overlay.
The configuration options are :
- bgcolor : The background color of the overlay. Use one of https://www.plus2net.com/python/tkinter-colors.php
- fgcolor : The color of the overlay text. Use one of https://www.plus2net.com/python/tkinter-colors.php
- small_font : The font used for descriptions.
- large_font : The font used for titles.
- position : The position of the overlay on screen in +(top)+(left) format.
- decorated : Should the overlay window have title, close and minimize buttons ?
- quit : The event that closes the overlay. Use one of https://python-course.eu/tkinter/events-and-binds-in-tkinter.php
- clear : The event that clears the overlay. Use one of https://python-course.eu/tkinter/events-and-binds-in-tkinter.php
- column_size : The size of each description column, in pixels.
- topmost : Should the overlay be always displayed over all windows ?

- abyss_db : The path of the database extracted from abyssexplorer (this is a partial database that contains translations, but doesn't knows items comming from extensions),
- item_db : A list of databases extracted from the fandom wiki (only in english, but knows all extensions items)
 
 - threshold : A float value between 0 and 1 that tells how exactly the database image must match the item displayed. If the overlay shows wrong items, increase it. If the overlay doesn't find items, lower it.
 - trim_to_alpha : Reduce images in memory by trimming them.
 - size_ratio : Images from the wiki DB should be resized by this value to match images from the game.
 - small_size_ratio : Images from the wiki DB should be resized by this value to be displayed in the overlay.
 - use_colors : Use colors when searching images. If false, searching process should be greatly increase, but some incorrect items may be displayed.
 - language : The language displayed in the overlay, if there is no transcription available of an item, it will appear in english.

- translate : When no translation of an item is available, use an LLM model to generate a translation. Application loading will be slow with this option active.
- translator_model : The LLM model to use for automatic transcription.
- translator_lang : The transcription language value took by the LLM model.
- save_translated_path : Saves a translated version of the database when 'translate' is true. The, you will be able to turn of translation and use the translated model in 'item_db' to start the app quickly


## Build from source (windows)

To compile the project, install python3 (>= 3.10), and pip.
- https://www.python.org/downloads/windows/
- https://pip.pypa.io/en/stable/installation/

It is recommended to install and initialize a virtualenv via :
```commandline
python -m pip install --user virtualenv
python -m venv venv
venv\Scripts\activate.bat
```

Install project dependencies using :
```commandline
python -m pip install -r requirements.txt
```

Run the program via :
```commandline
python main.py
```

Build the executable via :
```commandline
pyinstall_neonabyss.cmd
```

The executable is generated in the `dist` folder, with all resources in `dist\neondb`.
