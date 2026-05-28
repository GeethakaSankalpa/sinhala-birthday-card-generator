# Birthday Card Maker

Sinhala Birthday Card Generator built with Python and Tkinter.

## Features
- Sinhala Unicode support
- Custom birthday card generation
- Auto save to Downloads folder
- PNG template support

## Run

```bash
pip install -r requirements.txt
python card_app.py


## Build Exe

```bash
pyinstaller --onefile --windowed ^
--add-data "front.png;." ^
--add-data "back.png;." ^
--add-data "NotoSansSinhala-Regular.ttf;." ^
--add-data "NotoSansSinhala-Bold.ttf;." ^
card_app.py