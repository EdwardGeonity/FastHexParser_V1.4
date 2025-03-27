# FastHexParser_V1.4 (Hex Viewer (Native Byte Selection))

![FastHexParser_V1 4](https://github.com/user-attachments/assets/eb3d7b97-8a8c-4e03-a581-4f86da1f429d)

Overview

This application is a hex viewer, not a full hex editor, that shows the contents of a binary file in three columns:

    Offset column (addresses in hexadecimal)

    Hex column (raw bytes shown in hex groups)

    ASCII column (ASCII representation of those same bytes)

Users can open a file, scroll through its contents, click/drag to select bytes in either the hex or ASCII region, and see interpretations (like decimal, signed 16-bit, float32, etc.) of the selected data. The program also supports a simple “parser” mechanism to highlight annotated offsets from a text file.
How to Use

    Open the Program
    Launch the Python script. A window titled “Hex Viewer Alpha – Native Byte Selection” will appear, sized approximately 1400×800.

    Top Controls

        Open File
        Click “Open File” to pick a binary file from your system. The viewer will load it and display its contents in the three columns.

        Open Parser
        Click “Open Parser” if you have a .txt file (with lines like |offset|data|type|interpretation|) you want to load for highlighting. By default, the program looks for a file named <yourfile> + .txt in the same folder.

        Byte Grouping
        Choose how many bytes should be grouped together in the Hex column (1, 2, or 4). Changing this automatically refreshes the displayed data.

        Font Size
        Select your preferred font size (12, 14, 16, etc.). The display is refreshed with the chosen size.

    Main Display

        Offset Column (left)
        Shows the starting offset (hexadecimal) for each row (32 bytes per row).

        Hex Column (middle)
        Shows the file’s bytes as hex values, grouped according to the chosen grouping size.

        ASCII Column (right)
        Shows ASCII text representation of the same bytes. Non-printable characters are displayed as “.” (dot).

    Selecting Bytes
    Unlike typical text-based highlighting, this program uses native byte selection:

        Click and hold the left mouse button in either the Hex or ASCII column.

        Drag your mouse to extend the selection of bytes.

        Release the mouse to finalize the selection.
        When you select bytes in one column, the other column is also highlighted for the same byte range.

    Interpretation (Bottom Panel)
    After you release the mouse button, the bottom panel automatically updates with interpretations of the selected bytes:

        Hex (BE) – The raw bytes in Big-Endian hex notation (prefixed “0x”).

        Hex (LE) – The same bytes reversed (i.e. little-endian format).

        SignedInt16 – If 2 or more bytes are selected, interprets the first 2 as a little-endian signed 16-bit integer.

        Float32 – If 4 or more bytes are selected, interprets the first 4 as a little-endian 32-bit float.

        Decimal – Shows the entire selection interpreted as an unsigned decimal (little-endian).

    Saving an Interpretation
    Next to each interpretation field is a Write button. Clicking it appends a line to a text file in the format:

    |<offset_in_hex>|<raw_hex_be>|<data_type>|<interpretation_value>|

    By default, it creates or appends to <original_filename>.txt. If no file is open, it will ask for a target file.

    Parser

        A parser file (.txt) can contain lines like
        |00000050|0x41424344|Float32|SomeValue|

        When you click Open Parser, the program reads these lines, tries to match the specified offsets and hex data with what’s in the loaded file, and highlights them in the Hex and ASCII columns (lightblue color).

        This can be used to annotate or highlight known structures within the binary.

    Scrolling

        Use the vertical scrollbar on the right to scroll up/down.

        Use the horizontal scrollbar at the bottom if the hex lines wrap off the side.

        The program captures mouse wheel events (or Button-4/5 on Linux) to scroll all three text fields (offset/hex/ASCII) in sync.

    Keyboard Hotkeys

        b – Save the “Hex (BE)” interpretation

        l – Save “Hex (LE)”

        s – Save “SignedInt16”

        f – Save “Float32”

        d – Save “Decimal”
        This also works with Control or Command + letter.

Principles of Operation

    Three Parallel Text Widgets

        The program uses three Text widgets placed side by side:

            offset_text (left),

            hex_text (center),

            ascii_text (right).
            They are synchronized so that scrolling vertically moves all columns together.

    Native Byte Selection

        The program does not rely on the built-in Tkinter text selection for the hex/ASCII columns. Instead, it listens to mouse click/drag events on each widget.

        When the user clicks at coordinates (x,y), it converts that to a “text index” (e.g., row.col in the Text widget). From that index, it looks up which byte offset in the file is under the cursor by consulting an internal list called group_info.

        As the user drags, the program updates an in-memory range (start_offset to end_offset) of selected bytes, and applies a highlight tag ("highlight") to any corresponding hex or ASCII groups within that offset range.

    Interpretation of Bytes

        Once a final range of bytes is determined (e.g., offsets [X..Y]), the program retrieves those bytes from memory, performs conversions (hex, decimal, float, etc.), and displays the results in Entry fields.

    Parser Mechanism

        If a parser .txt is opened, each line is read in the form |offset|data|data_type|...|. The code checks the file’s actual bytes at that offset. If they match the specified hex string, it highlights them in a special color ("parsed").

        This allows you to see which bytes correspond to structured data or known values.

    Writing Output

        Whenever the user clicks Write (or uses a hotkey) on a specific interpretation, the code appends a line to a .txt file in the local folder, capturing the currently selected offset, raw hex (Big-Endian), data type, and interpreted value.

Notes and Tips

    No editing: This is a viewer, not an editor. It cannot modify the loaded file in memory.

    File size: For moderate file sizes (a few megabytes), this works well. Extremely large files (hundreds of MB or more) can be slow to display because all data is loaded at once. A more advanced “lazy loading” or “paging” approach would be needed for huge files.

    Group Size: Changing from 1-, 2-, or 4-byte groups can be useful for analyzing 16-bit or 32-bit data structures.

    ASCII Tab: Non-printable characters show as “.” (dot). Only ASCII range 0x20–0x7E is displayed directly.
