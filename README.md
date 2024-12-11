# Interactive PDF Text Editor - README

## Overview
The **Interactive PDF Text Editor** is a graphical application built using Python and Tkinter for editing PDF files. It supports a variety of features such as text editing, drawing, form field interaction, and more. This tool allows users to interact with the contents of a PDF in a simple and intuitive way.

---

## Features
- **Upload PDFs:** Load a PDF document to view and edit.
- **Text Editing:** Select, update, and add new text content to the PDF.
- **Form Field Interaction:** Interact with form fields, including checkboxes and text fields.
- **Drawing:** Enable freehand drawing on the PDF.
- **Undo Functionality:** Undo the last drawing or stroke using `Ctrl + Z`.
- **Save PDF:** Save the modified PDF to a new file.
- **Navigation:** Navigate through multi-page PDFs using `Previous Page` and `Next Page` buttons.
- **Customizable Text:** Choose font family, font size, and font color for new or updated text.

---

## Requirements
- Python 3.7 or later
- Libraries:
  - `tkinter`
  - `Pillow`
  - `PyMuPDF` (also known as `fitz`)
- Ensure these libraries are installed using `pip install Pillow pymupdf`.

---

## Installation
1. Clone or download this repository to your local machine.
2. Install the required Python packages:
   ```bash
   pip install Pillow pymupdf
   ```
3. Run the application:
   ```bash
   python pdf-editor.py
   ```

---

## Usage

### Interface Guide
1. **Top Menu:**
   - `Upload PDF`: Open a file dialog to select a PDF for editing.
   - `Save PDF`: Save the edited PDF to a new file.
   - `Add New Content`: Add new text content to the PDF by clicking on a location.
   - `Enable/Disable Drawing`: Toggle the drawing mode.
   - `Font Size`: Adjust the font size for new or updated text.
   - `Font Color`: Choose a color for text.
   - `Font Family`: Select a font family for text.

2. **Navigation Buttons:**
   - Navigate between pages of the PDF using `Previous Page` and `Next Page` buttons.

3. **Canvas:**
   - Displays the PDF page. Users can interact with text, form fields, and drawings directly on the canvas.

### Steps for Common Actions
#### Upload a PDF
1. Click the `Upload PDF` button.
2. Select a PDF file from your file system.

#### Edit Text
1. Click on existing text to select it.
2. Use the on-screen text editor to modify the text.
3. Press `Ctrl + Enter` to apply changes.

#### Add New Text
1. Click the `Add New Content` button.
2. Click on the desired location in the PDF.
3. Enter the text in the popup editor and press `Ctrl + Enter` to add it.

#### Interact with Form Fields
- **Check a Checkbox:** Click on a checkbox field to toggle its state.
- **Edit a Text Field:** Select a text field, update its value, and press `Enter` to save changes.

#### Draw on the PDF
1. Click `Enable Drawing` to activate drawing mode.
2. Use the mouse to draw freehand strokes on the canvas.
3. To undo the last stroke, press `Ctrl + Z`.

#### Save the Edited PDF
1. Click the `Save PDF` button.
2. Choose a location to save the updated file.

---

## Keyboard Shortcuts
- `Ctrl + Z`: Undo the last drawing action.
- `Ctrl + Enter`: Save changes to text when editing or adding new text.
- `Delete`: Delete selected text, form field, or drawing.

---

## Limitations
- Currently, supports only form field checkboxes and text fields.
- Drawing strokes are applied globally to the PDF upon saving; they cannot be moved or resized once drawn.
- Complex form elements (e.g., dropdowns or radio buttons) are not supported.

---

## Known Issues
- Some encrypted PDFs may not be editable.
- The accuracy of text selection may vary depending on the PDF's structure.
- Undo functionality is limited to drawing actions only.

---

## Contributing
Contributions are welcome! If you have ideas for improvements or want to fix bugs, feel free to fork this repository and submit a pull request.

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.


---

## Credits
- **Tkinter:** For the GUI components.
- **Pillow:** For image processing.
- **PyMuPDF (fitz):** For handling PDF files.

