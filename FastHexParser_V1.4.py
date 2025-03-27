import tkinter as tk
from tkinter import filedialog, messagebox
import struct
import os
import re

class HexViewerNativeSelection(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fast Hex Parser v1.4 (Viewer Only)")
        self.geometry("1400x800")

        self.file_data = b""
        self.file_path = None
        
        self.grouping_size = tk.IntVar(value=1)
        self.font_size = tk.IntVar(value=14)

        # Byte selection: store start and end offset in the file.
        self.select_start_offset = None
        self.select_end_offset   = None

        # For storing positions (start_hex_idx, end_hex_idx, start_ascii_idx, end_ascii_idx, offset_in_file, hex_str)
        self.group_info = []
        
        # For interpretation
        self.selected_hex_be = ""
        self.selected_hex_le = ""
        self.current_offset = 0  # First byte of the selected range

        self.create_top_controls()
        self.create_text_areas()
        self.create_bottom_interpretation()

        self.bind_hotkeys()

    def create_top_controls(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        open_btn = tk.Button(top_frame, text="Open File", command=self.open_file)
        open_btn.pack(side=tk.LEFT, padx=5, pady=5)

        parser_btn = tk.Button(top_frame, text="Open Parser", command=self.open_parser)
        parser_btn.pack(side=tk.LEFT, padx=5, pady=5)

        tk.Label(top_frame, text="Byte grouping:").pack(side=tk.LEFT, padx=5)
        for size in [1, 2, 4]:
            rb = tk.Radiobutton(top_frame, text=f"{size} byte(s)",
                                variable=self.grouping_size,
                                value=size,
                                command=self.refresh_hex_view)
            rb.pack(side=tk.LEFT)

        tk.Label(top_frame, text="Font Size:").pack(side=tk.LEFT, padx=5)
        for fsize in [12, 14, 16, 18, 20]:
            rb = tk.Radiobutton(top_frame, text=f"{fsize}",
                                variable=self.font_size,
                                value=fsize,
                                command=self.change_font_size)
            rb.pack(side=tk.LEFT)

    def create_text_areas(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        x_scroll = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        y_scroll = tk.Scrollbar(main_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # offset_text
        self.offset_text = tk.Text(main_frame, width=10, bg="darkgray", fg="white",
                                   font=("Courier", self.font_size.get()), wrap="none")
        self.offset_text.pack(side=tk.LEFT, fill=tk.BOTH)

        # hex_text (note state="disabled" to prevent standard selection)
        self.hex_text = tk.Text(main_frame, bg="black", fg="white",
                                font=("Courier", self.font_size.get()), wrap="none",
                                state="disabled")
        self.hex_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ascii_text
        self.ascii_text = tk.Text(main_frame, width=34, bg="darkgray", fg="white",
                                  font=("Courier", self.font_size.get()), wrap="none",
                                  state="disabled")
        self.ascii_text.pack(side=tk.LEFT, fill=tk.BOTH)

        # Link scrolling
        def y_scroll_command(*args):
            self.offset_text.yview(*args)
            self.hex_text.yview(*args)
            self.ascii_text.yview(*args)
        y_scroll.config(command=y_scroll_command)
        self.offset_text.config(yscrollcommand=lambda *a: y_scroll.set(*a))
        self.hex_text.config(yscrollcommand=lambda *a: y_scroll.set(*a))
        self.ascii_text.config(yscrollcommand=lambda *a: y_scroll.set(*a))

        def x_scroll_command(*args):
            self.hex_text.xview(*args)
            self.ascii_text.xview(*args)
        x_scroll.config(command=x_scroll_command)
        self.hex_text.config(xscrollcommand=lambda *a: x_scroll.set(*a))
        self.ascii_text.config(xscrollcommand=lambda *a: x_scroll.set(*a))

        # Custom mouse events for hex_text and ascii_text
        self.hex_text.bind("<Button-1>", self.on_mouse_down_hex)
        self.hex_text.bind("<B1-Motion>", self.on_mouse_drag_hex)
        self.hex_text.bind("<ButtonRelease-1>", self.on_mouse_up_hex)

        self.ascii_text.bind("<Button-1>", self.on_mouse_down_ascii)
        self.ascii_text.bind("<B1-Motion>", self.on_mouse_drag_ascii)
        self.ascii_text.bind("<ButtonRelease-1>", self.on_mouse_up_ascii)

        # For mouse wheel scrolling
        self.offset_text.bind("<MouseWheel>", self._on_mousewheel)
        self.hex_text.bind("<MouseWheel>", self._on_mousewheel)
        self.ascii_text.bind("<MouseWheel>", self._on_mousewheel)
        self.offset_text.bind("<Button-4>", self._on_mousewheel_linux)
        self.offset_text.bind("<Button-5>", self._on_mousewheel_linux)
        self.hex_text.bind("<Button-4>", self._on_mousewheel_linux)
        self.hex_text.bind("<Button-5>", self._on_mousewheel_linux)
        self.ascii_text.bind("<Button-4>", self._on_mousewheel_linux)
        self.ascii_text.bind("<Button-5>", self._on_mousewheel_linux)

    def create_bottom_interpretation(self):
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        self.interp_entries = {}
        self.interp_buttons = {}
        self.interp_types = ["Hex (BE)", "Hex (LE)", "SignedInt16", "Float32", "Decimal"]

        for i, interp in enumerate(self.interp_types):
            lbl = tk.Label(bottom_frame, text=interp, font=("Courier", self.font_size.get()))
            lbl.grid(row=i, column=0, padx=5, pady=2, sticky="w")

            entry = tk.Entry(bottom_frame, font=("Courier", self.font_size.get()), width=25)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.interp_entries[interp] = entry

            btn = tk.Button(bottom_frame, text="Write",
                            command=lambda it=interp: self.write_value(it))
            btn.grid(row=i, column=2, padx=5, pady=2)
            self.interp_buttons[interp] = btn

    # ===========================
    # Methods for "native" byte selection
    # ===========================
    def on_mouse_down_hex(self, event):
        """Mouse button pressed inside hex column. Determine byte offset and start selection."""
        self.select_start_offset = self._point_to_offset_hex(event)
        self.select_end_offset   = self.select_start_offset
        self._update_highlight()

    def on_mouse_drag_hex(self, event):
        """Mouse movement while button is pressed in hex column."""
        new_offset = self._point_to_offset_hex(event)
        if new_offset is not None:
            self.select_end_offset = new_offset
            self._update_highlight()

    def on_mouse_up_hex(self, event):
        """Button released - finalize selection and perform interpretation."""
        self._interpret_selection()

    def on_mouse_down_ascii(self, event):
        """Mouse button pressed inside ascii column. Similar to hex."""
        self.select_start_offset = self._point_to_offset_ascii(event)
        self.select_end_offset   = self.select_start_offset
        self._update_highlight()

    def on_mouse_drag_ascii(self, event):
        new_offset = self._point_to_offset_ascii(event)
        if new_offset is not None:
            self.select_end_offset = new_offset
            self._update_highlight()

    def on_mouse_up_ascii(self, event):
        self._interpret_selection()

    def _point_to_offset_hex(self, event):
        """
        Determine which byte in the file the user clicked on,
        based on coordinates (event.x, event.y) in hex_text.
        """
        # First convert (x,y) to (row, col) in text field
        try:
            index_str = self.hex_text.index(f"@{event.x},{event.y}")  # "row.col"
        except:
            return None
        
        if not index_str:
            return None
        line_str, col_str = index_str.split(".")
        row = int(line_str)  # 1-based
        col = int(col_str)   # 0-based

        # Each line corresponds to 32 bytes (or less if end of file)
        # So byte offset of line start = (row-1)*32
        # But need to account for group_size, spaces, etc.

        # For convenience, use the same structure as during rendering: group_info.
        # group_info contains tuples (start_hex_idx, end_hex_idx, start_ascii_idx, end_ascii_idx, offset_in_file, hex_str)
        # We can "walk through" (or binary search) to find which one includes index_str.
        # But in "native" editors, they usually calculate directly by col.
        # Here for simplicity we'll use group_info.

        # Convert index_str => "integer" for comparison
        numeric_idx = self._index_to_int(index_str)

        # Find the group where start_hex_idx <= numeric_idx < end_hex_idx
        # Since there can be many groups per line, we'll do linear search
        # (for large files, better to store grouping by lines)
        for gstart, gend, astart, aend, off, hstr in self.group_info:
            gi1 = self._index_to_int(gstart)
            gi2 = self._index_to_int(gend)
            if gi1 <= numeric_idx < gi2:
                # This is the group. offset_in_file = off
                # If group_size>1, maybe inside group?
                # For simplicity, click on any part of group => offset_in_file (group start).
                return off
        return None

    def _point_to_offset_ascii(self, event):
        """Similar method but for ascii_text."""
        try:
            index_str = self.ascii_text.index(f"@{event.x},{event.y}")
        except:
            return None
        if not index_str:
            return None
        numeric_idx = self._index_to_int(index_str)

        # Find in group_info where start_ascii_idx <= numeric_idx < end_ascii_idx
        for gstart, gend, astart, aend, off, hstr in self.group_info:
            ai1 = self._index_to_int(astart)
            ai2 = self._index_to_int(aend)
            if ai1 <= numeric_idx < ai2:
                return off
        return None

    def _update_highlight(self):
        """Highlight bytes in range [select_start_offset, select_end_offset]."""
        if self.select_start_offset is None or self.select_end_offset is None:
            return
        start_off = min(self.select_start_offset, self.select_end_offset)
        end_off   = max(self.select_start_offset, self.select_end_offset)

        # Remove old highlighting
        self.hex_text.config(state="normal")
        self.ascii_text.config(state="normal")
        self.hex_text.tag_remove("highlight", "1.0", tk.END)
        self.ascii_text.tag_remove("highlight", "1.0", tk.END)

        # Iterate through group_info, find groups within [start_off, end_off]
        for gstart_idx, gend_idx, astart_idx, aend_idx, offset_in_file, hex_str in self.group_info:
            if start_off <= offset_in_file < (end_off+1):
                self.hex_text.tag_add("highlight", gstart_idx, gend_idx)
                self.ascii_text.tag_add("highlight", astart_idx, aend_idx)

        self.hex_text.tag_config("highlight", background="lightgreen", foreground="black")
        self.ascii_text.tag_config("highlight", background="lightgreen", foreground="black")

        self.hex_text.config(state="disabled")
        self.ascii_text.config(state="disabled")

    def _interpret_selection(self):
        """When user releases mouse button - interpret the selected range."""
        if self.select_start_offset is None or self.select_end_offset is None:
            self.clear_interpretations()
            return
        start_off = min(self.select_start_offset, self.select_end_offset)
        end_off   = max(self.select_start_offset, self.select_end_offset)

        if start_off < 0 or start_off >= len(self.file_data):
            self.clear_interpretations()
            return
        if end_off < 0:
            self.clear_interpretations()
            return
        if end_off >= len(self.file_data):
            end_off = len(self.file_data)-1

        selected_bytes = self.file_data[start_off:end_off+1]
        self.current_offset = start_off
        self.update_interpretations(selected_bytes)

    # ===========================
    # Other methods (as usual)
    # ===========================

    def change_font_size(self):
        new_font = ("Courier", self.font_size.get())
        self.offset_text.config(font=new_font)
        self.hex_text.config(font=new_font)
        self.ascii_text.config(font=new_font)

        for widget in self.interp_entries.values():
            widget.config(font=new_font)
        for widget in self.interp_buttons.values():
            widget.config(font=new_font)

    def bind_hotkeys(self):
        mapping = {
            "b": "Hex (BE)",
            "l": "Hex (LE)",
            "s": "SignedInt16",
            "f": "Float32",
            "d": "Decimal"
        }
        for key, interp in mapping.items():
            self.bind_all(f"<KeyPress-{key}>", lambda e, it=interp: self.hotkey_save(it))
            self.bind_all(f"<Control-KeyPress-{key}>", lambda e, it=interp: self.hotkey_save(it))
            self.bind_all(f"<Command-KeyPress-{key}>", lambda e, it=interp: self.hotkey_save(it))

    def hotkey_save(self, interp_type):
        self.write_value(interp_type)

    def open_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        self.file_path = path
        try:
            with open(path, "rb") as f:
                self.file_data = f.read()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.refresh_hex_view()

    def refresh_hex_view(self):
        self.offset_text.config(state="normal")
        self.offset_text.delete("1.0", tk.END)

        self.hex_text.config(state="normal")
        self.hex_text.delete("1.0", tk.END)

        self.ascii_text.config(state="normal")
        self.ascii_text.delete("1.0", tk.END)

        self.group_info.clear()

        group_size = self.grouping_size.get()
        bytes_per_line = 32
        groups_per_line = bytes_per_line // group_size
        data_len = len(self.file_data)

        offset = 0
        while offset < data_len:
            line_offset = offset
            line_bytes = self.file_data[offset : offset + bytes_per_line]
            offset += bytes_per_line

            # offset column
            self.offset_text.insert(tk.END, f"{line_offset:08X}\n")

            line_hex_str = []
            ascii_str = []

            for i in range(0, len(line_bytes)):
                b = line_bytes[i]
                if 32 <= b < 127:
                    ascii_str.append(chr(b))
                else:
                    ascii_str.append(".")

            # Remember where this line starts in hex_text
            start_line_hex_idx = self.hex_text.index(tk.INSERT)
            for i2 in range(groups_per_line):
                group_off = line_offset + i2 * group_size
                if group_off >= data_len:
                    break
                group_data = self.file_data[group_off : group_off+group_size]
                hex_part = group_data.hex().upper()
                line_hex_str.append(hex_part.ljust(group_size*2, " ") + " ")

            # Insert one line into hex_text
            self.hex_text.insert(tk.END, "".join(line_hex_str) + "\n")
            end_line_hex_idx = self.hex_text.index(tk.INSERT)

            # Insert ASCII
            self.ascii_text.insert(tk.END, "".join(ascii_str) + "\n")

            # Now divide this line into groups and record indices
            base_hex_start = self._index_to_int(start_line_hex_idx)
            base_hex_start = self._index_to_int(start_line_hex_idx)

            # Instead of float(...) - do:
            line_str = start_line_hex_idx.split('.')[0]
            line_num = int(line_str)
            ascii_line_index_str = f"{line_num}.0"
            ascii_line_start = self.ascii_text.index(ascii_line_index_str)
            base_ascii_start = self._index_to_int(ascii_line_start)


            current_hex_pos = 0
            current_ascii_pos = 0

            for i2 in range(groups_per_line):
                group_off = line_offset + i2 * group_size
                if group_off >= data_len:
                    break
                group_data = self.file_data[group_off : group_off+group_size]
                hex_part = group_data.hex().upper()
                
                displayed_length = (group_size * 2) + 1  # +1 for space
                
                start_hex_idx = self._int_to_index(base_hex_start + current_hex_pos)
                end_hex_idx   = self._int_to_index(base_hex_start + current_hex_pos + displayed_length)

                ascii_start_idx = self._int_to_index(base_ascii_start + current_ascii_pos)
                ascii_end_idx   = self._int_to_index(base_ascii_start + current_ascii_pos + len(group_data))

                self.group_info.append((
                    start_hex_idx,
                    end_hex_idx,
                    ascii_start_idx,
                    ascii_end_idx,
                    group_off,
                    hex_part
                ))

                current_hex_pos += displayed_length
                current_ascii_pos += len(group_data)

        self.offset_text.config(state="disabled")
        self.hex_text.config(state="disabled")
        self.ascii_text.config(state="disabled")

    def _index_to_int(self, idx_str):
        line, col = idx_str.split(".")
        return int(line)*10000 + int(col)

    def _int_to_index(self, val):
        line = val // 10000
        col  = val % 10000
        return f"{line}.{col}"

    def update_interpretations(self, selected_bytes):
        if not selected_bytes:
            self.clear_interpretations()
            return

        hex_be = "0x" + selected_bytes.hex().upper()
        hex_le = "0x" + selected_bytes[::-1].hex().upper()
        self.selected_hex_be = hex_be
        self.selected_hex_le = hex_le

        if len(selected_bytes) >= 2:
            signed16 = str(int.from_bytes(selected_bytes[:2], byteorder="little", signed=True))
        else:
            signed16 = ""

        if len(selected_bytes) >= 4:
            try:
                float32 = str(struct.unpack("<f", selected_bytes[:4])[0])
            except Exception:
                float32 = ""
        else:
            float32 = ""

        decimal_val = str(int.from_bytes(selected_bytes, byteorder="little", signed=False))

        self.interp_entries["Hex (BE)"].delete(0, tk.END)
        self.interp_entries["Hex (BE)"].insert(0, hex_be)
        self.interp_entries["Hex (LE)"].delete(0, tk.END)
        self.interp_entries["Hex (LE)"].insert(0, hex_le)
        self.interp_entries["SignedInt16"].delete(0, tk.END)
        self.interp_entries["SignedInt16"].insert(0, signed16)
        self.interp_entries["Float32"].delete(0, tk.END)
        self.interp_entries["Float32"].insert(0, float32)
        self.interp_entries["Decimal"].delete(0, tk.END)
        self.interp_entries["Decimal"].insert(0, decimal_val)

    def clear_interpretations(self):
        for itype in self.interp_types:
            self.interp_entries[itype].delete(0, tk.END)

    def write_value(self, interp_type):
        raw_value = self.selected_hex_be
        interp_text = self.interp_entries[interp_type].get().strip()
        line = f"|{self.current_offset:08X}|{raw_value}|{interp_type}|{interp_text}|"
        
        if self.file_path:
            base = os.path.basename(self.file_path)
            out_path = os.path.join(os.path.dirname(self.file_path), base + ".txt")
        else:
            out_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not out_path:
            return
        try:
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            self.bell()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_parser(self):
        """Works similarly to v1.3, but remember we're manually highlighting."""
        if not self.file_path:
            return
        parser_path = os.path.join(os.path.dirname(self.file_path),
                                   os.path.basename(self.file_path) + ".txt")
        if not os.path.exists(parser_path):
            parser_path = filedialog.askopenfilename(title="Open Parser File", filetypes=[("Text Files", "*.txt")])
            if not parser_path:
                return
        print(f"Parsing {parser_path} ...")
        try:
            with open(parser_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.hex_text.config(state="normal")
        self.ascii_text.config(state="normal")

        self.hex_text.tag_remove("parsed", "1.0", tk.END)
        self.ascii_text.tag_remove("parsed", "1.0", tk.END)

        for line in lines:
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            # offset_str = parts[1], data_str = parts[2], data_type = parts[3]
            offset_str = parts[1].strip()
            data_str   = parts[2].strip()
            data_type  = parts[3].strip()

            try:
                offset_int = int(offset_str, 16)
            except:
                continue

            if data_type in ["SignedInt16"]:
                expected_bytes = 2
            elif data_type in ["Float32"]:
                expected_bytes = 4
            else:
                if data_str.lower().startswith("0x"):
                    hex_val = data_str[2:]
                else:
                    hex_val = data_str
                expected_bytes = len(hex_val)//2

            # Get bytes from file_data
            if offset_int >= len(self.file_data):
                continue
            end_off = offset_int + expected_bytes
            if end_off > len(self.file_data):
                end_off = len(self.file_data)
            actual_bytes = self.file_data[offset_int:end_off]

            if data_str.lower().startswith("0x"):
                expected_data = data_str[2:].upper()
            else:
                expected_data = data_str.upper()

            actual_hex = actual_bytes.hex().upper()

            if actual_hex != expected_data:
                continue
            
            # Highlight in hex_text / ascii_text
            # Find groups in self.group_info within [offset_int, offset_int+expected_bytes)
            start_off = offset_int
            end_off   = offset_int + expected_bytes - 1

            for gstart_idx, gend_idx, astart_idx, aend_idx, ofile, hstr in self.group_info:
                if start_off <= ofile <= end_off:
                    self.hex_text.tag_add("parsed", gstart_idx, gend_idx)
                    self.ascii_text.tag_add("parsed", astart_idx, aend_idx)

        self.hex_text.tag_config("parsed", foreground="lightblue")
        self.ascii_text.tag_config("parsed", foreground="lightblue")

        self.hex_text.config(state="disabled")
        self.ascii_text.config(state="disabled")

    # ===========================
    # Mouse wheel scrolling
    # ===========================
    def _on_mousewheel(self, event):
        if event.delta > 0:
            step = -1
        else:
            step = 1
        self.offset_text.yview_scroll(step, "units")
        self.hex_text.yview_scroll(step, "units")
        self.ascii_text.yview_scroll(step, "units")
        return "break"

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            step = -1
        else:
            step = 1
        self.offset_text.yview_scroll(step, "units")
        self.hex_text.yview_scroll(step, "units")
        self.ascii_text.yview_scroll(step, "units")
        return "break"

if __name__ == "__main__":
    app = HexViewerNativeSelection()
    app.mainloop()
