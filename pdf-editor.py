import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, ttk
from PIL import Image, ImageTk
import fitz
import os

class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive PDF Text Editor")

        self.window_width = 1400
        self.window_height = 1000
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(True, True)

        self.canvas_width = 1200
        self.canvas_height = 800

        self.filepath = None
        self.pdf_document = None
        self.current_page_index = 0
        self.selected_text = None
        self.font_size = 12
        self.font_color = (0, 0, 0)
        self.typing_content = False
        self.dragged_widget = None

        self.scale_factor = 1
        self.crop_x = 0
        self.crop_y = 0

        self.sentences = []
        self.form_fields = {}
        self.canvas = None

        self.drawing = False
        self.current_stroke = []
        self.drawings = []  # all strokes (including bounding boxes)
        self.undo_stack = []  # undo actions

        # Dragging state variables
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.content_start_x = 0
        self.content_start_y = 0
        self.moving_content = None

        self.setup_gui()

    def setup_gui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10)

        button_frame = tk.Frame(top_frame)
        button_frame.pack()

        self.upload_button = tk.Button(button_frame, text="Upload PDF", command=self.upload_pdf)
        self.upload_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(button_frame, text="Save PDF", command=self.save_pdf, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.add_content_button = tk.Button(button_frame, text="Add New Content", command=self.add_new_content, state=tk.DISABLED)
        self.add_content_button.pack(side=tk.LEFT, padx=5)

        self.toggle_button = tk.Button(button_frame, text="Enable Drawing", command=self.toggle_drawing)
        self.toggle_button.pack(side=tk.LEFT, padx=5)

        self.font_size_label = tk.Label(button_frame, text="Font Size:")
        self.font_size_label.pack(side=tk.LEFT, padx=5)

        self.font_size_dropdown = tk.Spinbox(button_frame, from_=6, to_=100, width=5, command=self.update_font_size)
        self.font_size_dropdown.delete(0, tk.END)
        self.font_size_dropdown.insert(0, self.font_size)
        self.font_size_dropdown.pack(side=tk.LEFT, padx=5)

        self.color_button = tk.Button(button_frame, text="Font Color", command=self.select_color)
        self.color_button.pack(side=tk.LEFT, padx=5)

        self.font_family_label = tk.Label(button_frame, text="Font Family:")
        self.font_family_label.pack(side=tk.LEFT, padx=5)

        self.font_families = ["Helvetica", "Times", "Courier", "Arial", "Symbol"]
        self.font_family_var = tk.StringVar(value=self.font_families[0])
        self.font_family_dropdown = ttk.Combobox(button_frame, textvariable=self.font_family_var, values=self.font_families, state="readonly", width=10)
        self.font_family_dropdown.pack(side=tk.LEFT, padx=5)

        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=5)

        nav_button_frame = tk.Frame(nav_frame)
        nav_button_frame.pack()

        self.prev_button = tk.Button(nav_button_frame, text="Previous Page", command=self.prev_page, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=10)

        self.page_label = tk.Label(nav_button_frame, text="Page: 0 / 0")
        self.page_label.pack(side=tk.LEFT, padx=10)

        self.next_button = tk.Button(nav_button_frame, text="Next Page", command=self.next_page, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=10)

        self.canvas_frame = tk.Frame(self.root, width=self.canvas_width, height=self.canvas_height)
        self.canvas_frame.pack()

        self.canvas = tk.Canvas(self.canvas_frame, width=self.canvas_width, height=self.canvas_height, bg="grey")
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Bind Ctrl+Z for undo
        self.root.bind("<Control-z>", self.undo)

        self.root.bind("<Delete>", self.delete_selected_text_event)
        self.root.bind("<Configure>", self.on_window_resize)

        self.text_entry = tk.Text(self.root, width=50, height=3)
        self.text_entry.bind("<Control-Return>", self.update_text_content)
        self.text_entry.bind("<Escape>", lambda e: self.text_entry.place_forget())
        self.text_entry.place_forget()

        self.entry_widget = tk.Entry(self.root, width=50)
        self.entry_widget.bind("<Return>", self.update_form_field)
        self.entry_widget.bind("<Escape>", lambda e: self.entry_widget.place_forget())
        self.entry_widget.place_forget()

    def toggle_drawing(self):
        self.drawing = not self.drawing
        if self.drawing:
            self.toggle_button.config(text="Disable Drawing")
            self.canvas.config(cursor="cross")
            self.selected_text = None
            self.moving_content = None
            # Rebind to ensure we can draw again
            # self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        else:
            self.toggle_button.config(text="Enable Drawing")
            self.canvas.config(cursor="")
            self.current_stroke = []
            # Restore default binding to ensure click works for selection too
            # self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
            self.canvas.bind("<B1-Motion>", self.do_drag)
            self.canvas.bind("<ButtonRelease-1>", self.end_drag)

    def on_button_press(self, event):
        if not self.drawing:
            self.on_canvas_click(event)
            return
        # Start pencil-like stroke
        self.current_stroke = [{"x": event.x, "y": event.y}]

    def on_mouse_drag(self, event):
        if not self.drawing or not self.current_stroke:
            return
        self.current_stroke.append({"x": event.x, "y": event.y})
        if len(self.current_stroke) > 1:
            x1, y1 = self.current_stroke[-2]["x"], self.current_stroke[-2]["y"]
            x2, y2 = self.current_stroke[-1]["x"], self.current_stroke[-1]["y"]
            self.canvas.create_line(x1, y1, x2, y2, fill=self.get_color_hex(), width=2, capstyle=tk.ROUND, smooth=True, splinesteps=36)

    def on_button_release(self, event):
        if not self.drawing or not self.current_stroke:
            return
        if len(self.current_stroke) > 1:
            stroke = {
                "type": "stroke",
                "points": self.current_stroke.copy(),
                "color": self.get_color_hex(),
                "width": 2
            }
            # Compute bounding box for the stroke
            xs = [p["x"] for p in stroke["points"]]
            ys = [p["y"] for p in stroke["points"]]
            stroke["bbox"] = (min(xs), min(ys), max(xs), max(ys))

            self.drawings.append(stroke)
            self.undo_stack.append(stroke)
        self.current_stroke = []

    def undo(self, event=None):
        if self.undo_stack:
            last_action = self.undo_stack.pop()
            if last_action["type"] == "stroke":
                if last_action in self.drawings:
                    self.drawings.remove(last_action)
                    self.render_page()
        else:
            print("Undo stack is empty.")

    def get_color_hex(self):
        return '#%02x%02x%02x' % self.font_color

    def on_window_resize(self, event):
        new_width = self.root.winfo_width() - 200
        new_height = self.root.winfo_height() - 200
        new_width = max(new_width, 800)
        new_height = max(new_height, 600)
        self.canvas.config(width=new_width, height=new_height)
        self.canvas_width = new_width
        self.canvas_height = new_height
        self.render_page()

    def upload_pdf(self):
        self.filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not self.filepath:
            return
        try:
            self.pdf_document = fitz.open(self.filepath)
            if not self.pdf_document.is_encrypted:
                self.current_page_index = 0
                self.drawings = []
                self.undo_stack = []
                self.render_page()
                self.save_button.config(state=tk.NORMAL)
                self.add_content_button.config(state=tk.NORMAL)
                self.update_navigation_buttons()
            else:
                messagebox.showerror("Error", "The PDF is encrypted or has editing restrictions.")
                self.pdf_document.close()
                self.pdf_document = None
        except Exception as e:
            self.pdf_document = None
            messagebox.showerror("Error", f"Failed to open PDF: {e}")

    def render_page(self):
        if not self.pdf_document:
            return
        try:
            page = self.pdf_document[self.current_page_index]
            pdf_width = page.mediabox.width
            pdf_height = page.mediabox.height

            ratio_width = self.canvas_width / pdf_width
            ratio_height = self.canvas_height / pdf_height

            self.scale_factor = min(ratio_width, ratio_height)
            mat = fitz.Matrix(self.scale_factor, self.scale_factor)
            try:
                pix = page.get_pixmap(matrix=mat, annot=True)
            except TypeError:
                pix = page.get_pixmap(matrix=mat)

            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if pix.width < self.canvas_width or pix.height < self.canvas_height:
                new_image = Image.new("RGB", (int(self.canvas_width), int(self.canvas_height)), "grey")
                paste_x = (int(self.canvas_width) - pix.width) // 2
                paste_y = (int(self.canvas_height) - pix.height) // 2
                new_image.paste(image, (paste_x, paste_y))
                self.crop_x = -paste_x / self.scale_factor
                self.crop_y = -paste_y / self.scale_factor
                image = new_image
            else:
                self.crop_x = 0
                self.crop_y = 0

            self.current_image = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
            self.canvas.image = self.current_image

            total_pages = len(self.pdf_document)
            self.page_label.config(text=f"Page: {self.current_page_index + 1} / {total_pages}")

            self.extract_sentences()
            self.extract_form_fields()
            self.render_form_fields()

            # Redraw drawings
            for drawing in self.drawings:
                if drawing["type"] == "stroke":
                    points = drawing["points"]
                    if len(points) > 1:
                        flat_points = []
                        for p in points:
                            flat_points.extend([p["x"], p["y"]])
                        self.canvas.create_line(
                            *flat_points,
                            fill=drawing["color"],
                            width=drawing["width"],
                            capstyle=tk.ROUND,
                            smooth=True,
                            splinesteps=36
                        )

            # Show dragging feedback if needed
            if self.dragging and self.moving_content and self.moving_content.get("type") != "stroke":
                # For text/form fields dragging feedback
                rect = self.moving_content["rect"]
                canvas_x0 = (rect.x0 - self.crop_x) * self.scale_factor
                canvas_y0 = (rect.y0 - self.crop_y) * self.scale_factor
                canvas_x1 = (rect.x1 - self.crop_x) * self.scale_factor
                canvas_y1 = (rect.y1 - self.crop_y) * self.scale_factor
                self.canvas.create_rectangle(
                    canvas_x0, canvas_y0, canvas_x1, canvas_y1,
                    outline="orange", width=2, dash=(2, 2), tag="dragging"
                )
            elif self.dragging and self.moving_content and self.moving_content.get("type") == "stroke":
                # For stroke dragging feedback
                stroke = self.moving_content["stroke_data"]
                x0, y0, x1, y1 = stroke["bbox"]
                self.canvas.create_rectangle(x0, y0, x1, y1, outline="orange", width=2, dash=(2, 2), tag="dragging")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to render page: {e}")

    def extract_sentences(self):
        if not self.pdf_document:
            self.sentences = []
            return
        try:
            page = self.pdf_document[self.current_page_index]
            words = page.get_text("words")
            words.sort(key=lambda w: (w[1], w[0]))

            sentences = []
            current_sentence = []
            current_sentence_words = []
            current_block_no = None
            current_line_no = None

            for word in words:
                x0, y0, x1, y1, text, block_no, line_no, word_no = word
                if current_sentence and (block_no != current_block_no or line_no != current_line_no):
                    if current_sentence:
                        sentence_text = ' '.join(current_sentence)
                        sentences.append({
                            "text": sentence_text,
                            "words": current_sentence_words.copy(),
                            "rect": self.calculate_sentence_rect(current_sentence_words)
                        })
                        current_sentence = []
                        current_sentence_words = []
                if not current_sentence:
                    current_sentence_words = []
                current_sentence.append(text)
                current_sentence_words.append(word)
                if text.endswith(('.', '!', '?')):
                    sentence_text = ' '.join(current_sentence)
                    sentences.append({
                        "text": sentence_text,
                        "words": current_sentence_words.copy(),
                        "rect": self.calculate_sentence_rect(current_sentence_words)
                    })
                    current_sentence = []
                    current_sentence_words = []
                current_block_no = block_no
                current_line_no = line_no

            if current_sentence:
                sentence_text = ' '.join(current_sentence)
                sentences.append({
                    "text": sentence_text,
                    "words": current_sentence_words.copy(),
                    "rect": self.calculate_sentence_rect(current_sentence_words)
                })

            self.sentences = sentences
        except Exception as e:
            self.sentences = []
            messagebox.showerror("Error", f"Failed to extract sentences: {e}")

    def calculate_sentence_rect(self, words):
        try:
            x0 = min(w[0] for w in words) - 2
            y0 = min(w[1] for w in words) - 2
            x1 = max(w[2] for w in words) + 2
            y1 = max(w[3] for w in words) + 2
            return fitz.Rect(x0, y0, x1, y1)
        except Exception:
            return fitz.Rect(0, 0, 0, 0)

    def extract_form_fields(self):
        if not self.pdf_document:
            self.form_fields[self.current_page_index] = []
            return
        try:
            page = self.pdf_document[self.current_page_index]
            widgets = page.widgets()
            form_fields = []
            if widgets:
                for widget in widgets:
                    field_type = widget.field_type
                    field_flag_checkbox = getattr(widget, 'field_flag_checkbox', False)
                    is_checkbox = (field_type == "Btn" and field_flag_checkbox)
                    form_fields.append({
                        "field_name": widget.field_name,
                        "field_type": "checkbox" if is_checkbox else field_type,
                        "rect": widget.rect,
                        "widget": widget
                    })
            self.form_fields[self.current_page_index] = form_fields
        except Exception:
            self.form_fields[self.current_page_index] = []

    def render_form_fields(self):
        form_fields = self.form_fields.get(self.current_page_index, [])
        for field in form_fields:
            rect = field["rect"]
            canvas_x0 = (rect.x0 - self.crop_x) * self.scale_factor
            canvas_y0 = (rect.y0 - self.crop_y) * self.scale_factor
            canvas_x1 = (rect.x1 - self.crop_x) * self.scale_factor
            canvas_y1 = (rect.y1 - self.crop_y) * self.scale_factor

            self.canvas.create_rectangle(
                canvas_x0, canvas_y0, canvas_x1, canvas_y1,
                outline="blue", width=2, dash=(4, 2), tag="form_field"
            )

            if field["field_type"] == "checkbox":
                export_value = field["widget"].export_value
                field_value = field["widget"].field_value
                is_checked = (export_value and field_value == export_value) or (not export_value and field_value in ["Yes", "On"])

                if is_checked:
                    padding = 4
                    self.canvas.create_line(
                        canvas_x0 + padding, canvas_y0 + padding,
                        canvas_x0 + (canvas_x1 - canvas_x0) / 2, canvas_y1 - padding,
                        fill="green", width=2, tag="form_field"
                    )
                    self.canvas.create_line(
                        canvas_x0 + (canvas_x1 - canvas_x0) / 2, canvas_y1 - padding,
                        canvas_x1 - padding, canvas_y0 + padding,
                        fill="green", width=2, tag="form_field"
                    )

    def highlight_selected_sentence(self, rect):
        canvas_x0 = (rect.x0 - self.crop_x) * self.scale_factor
        canvas_y0 = (rect.y0 - self.crop_y) * self.scale_factor
        canvas_x1 = (rect.x1 - self.crop_x) * self.scale_factor
        canvas_y1 = (rect.y1 - self.crop_y) * self.scale_factor
        self.canvas.delete("highlight")
        self.canvas.create_rectangle(canvas_x0, canvas_y0, canvas_x1, canvas_y1, outline="red", width=2, tag="highlight")

    def highlight_selected_field(self, rect):
        canvas_x0 = (rect.x0 - self.crop_x) * self.scale_factor
        canvas_y0 = (rect.y0 - self.crop_y) * self.scale_factor
        canvas_x1 = (rect.x1 - self.crop_x) * self.scale_factor
        canvas_y1 = (rect.y1 - self.crop_y) * self.scale_factor
        self.canvas.delete("highlight")
        self.canvas.create_rectangle(canvas_x0, canvas_y0, canvas_x1, canvas_y1, outline="green", width=2, tag="highlight")

    def highlight_selected_stroke(self, bbox):
        x0, y0, x1, y1 = bbox
        self.canvas.delete("highlight")
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="purple", width=2, tag="highlight")

    def add_new_content(self):
        self.typing_content = True
        self.canvas.bind("<Button-1>", self.place_new_text_entry)
        messagebox.showinfo("Info", "Click on the PDF to place the new text.")

    def place_new_text_entry(self, event):
        x_canvas = event.x
        y_canvas = event.y
        self.text_entry.config(font=(self.font_family_var.get(), self.font_size))
        self.text_entry.delete(1.0, tk.END)
        self.text_entry.insert(tk.END, "")

        self.text_entry.place(x=x_canvas, y=y_canvas)
        self.text_entry.focus_set()

        self.canvas.unbind("<Button-1>")
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        if self.typing_content:
            self.text_entry.unbind("<Control-Return>")
            self.text_entry.bind("<Control-Return>", self.insert_new_text)
            messagebox.showinfo("Info", "After entering text, press Control+Return to submit.")
        else:
            self.text_entry.bind("<Control-Return>", self.update_text_content)

    def erase_original_text(self, rect):
        try:
            self.selected_text["page"].add_redact_annot(rect, fill=(1, 1, 1))
            self.selected_text["page"].apply_redactions()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to erase original text: {e}")

    def insert_new_text(self, event=None):
        if not self.typing_content:
            self.update_text_content()
            return
        self.typing_content = False
        x_canvas = self.text_entry.winfo_x()
        y_canvas = self.text_entry.winfo_y()

        pdf_x = (x_canvas + self.crop_x) / self.scale_factor
        pdf_y = (y_canvas + self.crop_y) / self.scale_factor

        page = self.pdf_document[self.current_page_index]
        text = self.text_entry.get(1.0, tk.END).strip()

        if text:
            try:
                font_family = self.font_family_var.get()
                font_mapping = {
                    "helvetica": "helv",
                    "times": "times",
                    "courier": "courier",
                    "arial": "helv",
                    "symbol": "symbol",
                }
                fitz_font_name = font_mapping.get(font_family.lower(), "helv")
                insertion_point = (pdf_x + 20, pdf_y + self.font_size / 2)
                font_color_normalized = tuple(c / 255 for c in self.font_color)

                page.insert_text(
                    insertion_point,
                    text,
                    fontsize=self.font_size,
                    fontname=fitz_font_name,
                    color=font_color_normalized,
                )

                self.render_page()
                self.text_entry.delete(1.0, tk.END)
                self.text_entry.place_forget()
                self.selected_text = None
                messagebox.showinfo("Success", "Text added to PDF successfully!")
                self.text_entry.unbind("<Control-Return>")
                self.text_entry.bind("<Control-Return>", self.update_text_content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add text: {e}")
        else:
            messagebox.showwarning("Warning", "No text entered.")

        return "break"

    def update_text_content(self, event=None):
        if not self.selected_text:
            messagebox.showwarning("Warning", "No text selected.")
            return

        new_text = self.text_entry.get(1.0, tk.END).strip()
        page = self.selected_text["page"]
        rect = self.selected_text["rect"]
        font_size = self.font_size
        font_family = self.font_family_var.get()

        # Erase original text
        try:
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to erase original text: {e}")
            return

        font_mapping = {
            "helvetica": "helv",
            "times": "times",
            "courier": "courier",
            "arial": "helv",
            "symbol": "symbol",
        }

        fitz_font_name = font_mapping.get(font_family.lower(), "helv")
        insertion_point = (rect.x0, rect.y0 + ((rect.y1 - rect.y0) / 2) + font_size / 2)

        try:
            page.insert_text(
                insertion_point,
                new_text,
                fontsize=font_size,
                fontname=fitz_font_name,
                color=self.font_color,
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert text: {e}")
            return

        self.text_entry.place_forget()
        self.render_page()
        messagebox.showinfo("Success", "Text updated successfully.")

    def update_form_field(self, event=None):
        if not self.selected_text or self.selected_text["type"] != "form_field":
            messagebox.showwarning("Warning", "No form field selected for updating.")
            return

        new_text = self.entry_widget.get().strip()
        if not new_text:
            messagebox.showwarning("Warning", "No text entered.")
            return

        self.extract_form_fields()
        page_widgets = self.form_fields.get(self.current_page_index, [])
        widget = None
        for fw in page_widgets:
            if fw["field_name"] == self.selected_text["field_name"]:
                widget = fw["widget"]
                self.selected_text["widget"] = widget
                self.selected_text["rect"] = fw["rect"]
                break

        if not widget:
            messagebox.showwarning("Warning", "Form field not found or invalid.")
            return

        try:
            widget.field_value = new_text
            widget.update()
            self.render_page()
            self.entry_widget.delete(0, tk.END)
            self.entry_widget.place_forget()
            self.selected_text = None
            messagebox.showinfo("Success", "Form field updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update form field: {e}")
            return

    def delete_selected_text_event(self, event=None):
        self.delete_selected_text()

    def delete_selected_text(self, event=None):
        if not self.selected_text:
            messagebox.showwarning("Warning", "No text or form field selected to delete.")
            return

        if self.selected_text["type"] == "stroke":
            # Delete a selected stroke
            stroke_data = self.selected_text.get("stroke_data")
            if stroke_data in self.drawings:
                self.drawings.remove(stroke_data)
                if stroke_data in self.undo_stack:
                    self.undo_stack.remove(stroke_data)
                self.selected_text = None
                self.render_page()
                messagebox.showinfo("Success", "Selected stroke deleted successfully.")
            return

        page = self.selected_text["page"]
        rect = self.selected_text["rect"]

        try:
            if self.selected_text["type"] == "text":
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
            elif self.selected_text["type"] == "form_field":
                self.extract_form_fields()
                fields = self.form_fields.get(self.current_page_index, [])
                widget = None
                for fw in fields:
                    if fw["field_name"] == self.selected_text["field_name"]:
                        widget = fw["widget"]
                        break
                if widget:
                    page.delete_widget(widget)
                else:
                    messagebox.showwarning("Warning", "Form field not found.")
                    return
            else:
                messagebox.showwarning("Warning", "Unknown selection type.")
                return

            self.render_page()
            self.selected_text = None
            messagebox.showinfo("Success", "Selected content deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete content: {e}")

    def update_font_size(self):
        try:
            self.font_size = int(self.font_size_dropdown.get())
            if self.text_entry.winfo_ismapped():
                current_font = (self.font_family_var.get(), self.font_size)
                self.text_entry.configure(font=current_font)
            if self.entry_widget.winfo_ismapped():
                current_font = (self.font_family_var.get(), self.font_size)
                self.entry_widget.configure(font=current_font)
        except ValueError:
            messagebox.showerror("Error", "Invalid font size entered.")

    def select_color(self):
        color = colorchooser.askcolor()[0]
        if color:
            self.font_color = tuple(int(c) for c in color)

    def next_page(self):
        if self.current_page_index < len(self.pdf_document) - 1:
            self.current_page_index += 1
            self.drawings = []
            self.undo_stack = []
            self.render_page()
            self.update_navigation_buttons()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.drawings = []
            self.undo_stack = []
            self.render_page()
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        if self.current_page_index == 0:
            self.prev_button.config(state=tk.DISABLED)
        else:
            self.prev_button.config(state=tk.NORMAL)

        if self.current_page_index == len(self.pdf_document) - 1:
            self.next_button.config(state=tk.DISABLED)
        else:
            self.next_button.config(state=tk.NORMAL)

    def save_pdf(self):
        if not self.pdf_document:
            messagebox.showwarning("Warning", "No PDF loaded to save.")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if not save_path:
            return
        if os.path.exists(save_path):
            if not messagebox.askyesno("Confirm Overwrite", "File already exists. Overwrite?"):
                return
        try:
            # Apply all drawings to PDF
            for drawing in self.drawings:
                if drawing["type"] == "stroke":
                    page = self.pdf_document[self.current_page_index]
                    pdf_width = page.mediabox.width
                    pdf_height = page.mediabox.height
                    differ_x = (self.canvas_width - pdf_width * self.scale_factor) / 2
                    differ_y = (self.canvas_height - pdf_height * self.scale_factor) / 2

                    points = drawing["points"]
                    pdf_points = []
                    for point in points:
                        pdf_x = (point["x"] - differ_x) / self.scale_factor
                        pdf_y = (point["y"] - differ_y) / self.scale_factor
                        pdf_points.append(fitz.Point(pdf_x, pdf_y))

                    if len(pdf_points) > 1:
                        page.draw_path(pdf_points, color=tuple(c/255 for c in self.font_color), width=drawing["width"])

            self.pdf_document.save(save_path)
            messagebox.showinfo("Success", "PDF saved successfully!")
        except fitz.FitzError as fe:
            messagebox.showerror("Error", f"Failed to save PDF: {fe}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def start_drag(self, event):
        if not self.selected_text:
            return
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        if self.selected_text["type"] == "stroke":
            stroke_data = self.selected_text["stroke_data"]
            self.moving_content = {
                "type": "stroke",
                "original_points": [p.copy() for p in stroke_data["points"]],
                "stroke_data": stroke_data
            }
        else:
            self.moving_content = self.selected_text.copy()
            rect = self.selected_text["rect"]
            self.content_start_x = rect.x0
            self.content_start_y = rect.y0

    def do_drag(self, event):
        if not self.dragging or not self.selected_text:
            return
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        self.drag_start_x = event.x
        self.drag_start_y = event.y

        if self.selected_text["type"] == "stroke":
            stroke = self.moving_content["stroke_data"]
            original_points = self.moving_content["original_points"]
            for i, op in enumerate(original_points):
                stroke["points"][i]["x"] = op["x"] + dx
                stroke["points"][i]["y"] = op["y"] + dy
            xs = [p["x"] for p in stroke["points"]]
            ys = [p["y"] for p in stroke["points"]]
            stroke["bbox"] = (min(xs), min(ys), max(xs), max(ys))
            self.selected_text["rect"] = fitz.Rect(*stroke["bbox"])
            self.render_page()
        else:
            rect = self.moving_content["rect"]
            new_rect = fitz.Rect(
                rect.x0 + dx / self.scale_factor,
                rect.y0 + dy / self.scale_factor,
                rect.x1 + dx / self.scale_factor,
                rect.y1 + dy / self.scale_factor
            )
            self.moving_content["rect"] = new_rect
            self.render_page()

    def end_drag(self, event):
        if not self.dragging or not self.selected_text:
            return
        self.dragging = False
        self.canvas.delete("dragging")

        self.selected_text["page"] = self.pdf_document[self.current_page_index]
        self.extract_form_fields()

        if self.selected_text["type"] == "stroke":
            pass
        elif self.selected_text["type"] == "text":
            final_rect = self.moving_content["rect"]
            new_x0 = final_rect.x0
            new_y0 = final_rect.y0
            new_x1 = final_rect.x1
            new_y1 = final_rect.y1

            old_rect = self.selected_text["rect"]
            try:
                self.selected_text["page"].add_redact_annot(old_rect, fill=(1, 1, 1))
                self.selected_text["page"].apply_redactions()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to erase original text: {e}")
                self.canvas.bind("<ButtonPress-1>", self.on_button_press)
                self.moving_content = None
                return

            new_text = self.selected_text["sentence"]
            font_family = self.selected_text["font_family"]
            font_mapping = {
                "helvetica": "helv",
                "times": "times",
                "courier": "courier",
                "arial": "helv",
                "symbol": "symbol",
            }
            fitz_font_name = font_mapping.get(font_family.lower(), "helv")
            font_color_normalized = tuple(c/255 for c in self.font_color)

            insertion_point = (new_x0, new_y0 + self.font_size)
            try:
                self.selected_text["page"].insert_text(
                    insertion_point,
                    new_text,
                    fontsize=self.font_size,
                    fontname=fitz_font_name,
                    color=font_color_normalized,
                )
                self.selected_text["rect"] = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
                self.render_page()
                messagebox.showinfo("Success", "Text moved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to insert text at new location: {e}")

        elif self.selected_text["type"] == "form_field":
            final_rect = self.moving_content["rect"]
            new_x0 = final_rect.x0
            new_y0 = final_rect.y0
            new_x1 = final_rect.x1
            new_y1 = final_rect.y1

            fields = self.form_fields.get(self.current_page_index, [])
            widget = None
            for fw in fields:
                if fw["field_name"] == self.selected_text["field_name"]:
                    widget = fw["widget"]
                    break

            if not widget:
                messagebox.showerror("Error", "Failed to move form field: Widget not found or invalid.")
                self.canvas.bind("<ButtonPress-1>", self.on_button_press)
                self.moving_content = None
                return

            try:
                widget.rect = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
                widget.update()
                self.selected_text["rect"] = widget.rect
                self.render_page()
                messagebox.showinfo("Success", "Form field moved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move form field: {e}")

        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)

        self.selected_text = None
        self.moving_content = None

    def on_canvas_click(self, event):
        if not self.pdf_document:
            messagebox.showwarning("Warning", "Please upload a PDF before editing.")
            return

        x_canvas = event.x
        y_canvas = event.y
        pdf_x = (x_canvas + self.crop_x) / self.scale_factor
        pdf_y = (y_canvas + self.crop_y) / self.scale_factor

        # Check form fields first
        form_fields = self.form_fields.get(self.current_page_index, [])
        selected_field = None
        for field in form_fields:
            rect = field["rect"]
            if rect.contains(fitz.Point(pdf_x, pdf_y)):
                selected_field = field
                break

        if selected_field:
            if selected_field["field_type"] == "checkbox":
                response = messagebox.askyesno("Confirm", f"Do you want to check the checkbox '{selected_field['field_name']}'?")
                if response:
                    self.check_checkbox(selected_field["field_name"])
                else:
                    messagebox.showinfo("Cancelled", f"Checkbox '{selected_field['field_name']}' remains unchanged.")
                return
            # Select form field
            self.selected_text = {
                "type": "form_field",
                "field_name": selected_field["field_name"],
                "rect": selected_field["rect"],
                "widget": selected_field["widget"],
                "page": self.pdf_document[self.current_page_index],
                "font_size": self.font_size,
                "font_family": self.font_family_var.get()
            }
            self.highlight_selected_field(selected_field["rect"])
            editor_x = (selected_field["rect"].x0 - self.crop_x) * self.scale_factor
            editor_y = (selected_field["rect"].y1 - self.crop_y) * self.scale_factor + 10
            if editor_x + 300 > self.canvas_width:
                editor_x = self.canvas_width - 300
            if editor_y + 50 > self.canvas_height:
                editor_y = self.canvas_height - 50

            self.entry_widget.config(font=(self.font_family_var.get(), self.font_size))
            current_value = selected_field["widget"].field_value or ""
            self.entry_widget.delete(0, tk.END)
            self.entry_widget.insert(0, current_value.strip())

            self.entry_widget.place(x=editor_x, y=editor_y)
            self.entry_widget.focus_set()

            self.entry_widget.unbind("<Return>")
            self.entry_widget.bind("<Return>", self.update_form_field)

            self.canvas.bind("<ButtonPress-1>", self.start_drag)
            self.canvas.bind("<B1-Motion>", self.do_drag)
            self.canvas.bind("<ButtonRelease-1>", self.end_drag)
            return

        # Check text
        selected_sentence = None
        for sentence in self.sentences:
            rect = sentence["rect"]
            if rect.contains(fitz.Point(pdf_x, pdf_y)):
                selected_sentence = sentence
                break

        if selected_sentence:
            self.selected_text = {
                "type": "text",
                "sentence": selected_sentence["text"],
                "rect": selected_sentence["rect"],
                "page": self.pdf_document[self.current_page_index],
                "font_size": self.font_size,
                "font_family": self.font_family_var.get()
            }
            self.highlight_selected_sentence(selected_sentence["rect"])
            editor_x = (selected_sentence["rect"].x0 - self.crop_x) * self.scale_factor
            editor_y = (selected_sentence["rect"].y1 - self.crop_y) * self.scale_factor + 10
            if editor_x + 300 > self.canvas_width:
                editor_x = self.canvas_width - 300
            if editor_y + 100 > self.canvas_height:
                editor_y = self.canvas_height - 100

            self.text_entry.config(font=(self.font_family_var.get(), self.font_size))
            self.text_entry.delete(1.0, tk.END)
            self.text_entry.insert(tk.END, selected_sentence["text"].strip())

            self.text_entry.place(x=editor_x, y=editor_y)
            self.text_entry.focus_set()

            self.text_entry.unbind("<Control-Return>")
            self.text_entry.bind("<Control-Return>", self.update_text_content)

            self.canvas.bind("<ButtonPress-1>", self.start_drag)
            self.canvas.bind("<B1-Motion>", self.do_drag)
            self.canvas.bind("<ButtonRelease-1>", self.end_drag)
            return

        # If no text or form field selected, check strokes
        clicked_stroke = None
        for d in reversed(self.drawings):
            if d["type"] == "stroke":
                x0, y0, x1, y1 = d["bbox"]
                if x0 <= x_canvas <= x1 and y0 <= y_canvas <= y1:
                    clicked_stroke = d
                    break

        if clicked_stroke:
            self.selected_text = {
                "type": "stroke",
                "stroke_data": clicked_stroke,
                "rect": fitz.Rect(*clicked_stroke["bbox"])
            }
            self.highlight_selected_stroke(clicked_stroke["bbox"])

            self.canvas.bind("<ButtonPress-1>", self.start_drag)
            self.canvas.bind("<B1-Motion>", self.do_drag)
            self.canvas.bind("<ButtonRelease-1>", self.end_drag)
            return

        messagebox.showinfo("Info", "No selectable text, form field, or stroke found at this location.")

    def check_checkbox(self, field_name):
        try:
            page = self.pdf_document[self.current_page_index]
            widgets = page.widgets()
            if widgets:
                for w in widgets:
                    if w.field_name == field_name:
                        if w.field_type == "Btn" and getattr(w, 'field_flag_checkbox', False):
                            export_value = w.export_value if w.export_value else "Yes"
                            w.field_value = export_value
                            w.update()
                            self.render_page()
                            messagebox.showinfo("Success", f"Checkbox '{field_name}' checked successfully!")
                            return
                messagebox.showwarning("Warning", f"Checkbox '{field_name}' not found on this page.")
            else:
                messagebox.showwarning("Warning", "No form fields found on this page.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check checkbox '{field_name}': {e}")

if __name__ == "__main__":
    root = tk.Tk()
    pdf_editor = PDFEditor(root)
    root.mainloop()