# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox
from PIL import Image
import numpy as np
import uharfbuzz as hb
import freetype
import ctypes
import sys
import os
import time

# ─────────────────────────────────────────────
# PYINSTALLER SAFE RESOURCE HANDLING
# ─────────────────────────────────────────────

def resource_path(filename):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)


FONT_PATH = resource_path("NotoSansSinhala-Regular.ttf")
BOLD_FONT_PATH = resource_path("NotoSansSinhala-Bold.ttf")
FRONT_IMG = resource_path("front.png")
BACK_IMG = resource_path("back.png")


# ── Auto delete old generated cards ─────────────────────

def cleanup_old_cards():

    ONE_WEEK_SECONDS = 7 * 24 * 60 * 60
    now = time.time()

    downloads_folder = os.path.join(
        os.path.expanduser("~"),
        "Downloads"
    )

    if not os.path.exists(downloads_folder):
        return

    for filename in os.listdir(downloads_folder):

        if filename.startswith("Birthday_Card_") and filename.lower().endswith(".jpg"):

            file_path = os.path.join(downloads_folder, filename)

            try:
                file_age = now - os.path.getmtime(file_path)

                if file_age > ONE_WEEK_SECONDS:
                    os.remove(file_path)
                    print(f"Deleted old file: {filename}")

            except Exception as e:
                print(f"Could not delete {filename}: {e}")


# ── Core rendering engine ───────────────────────────────

def _make_hb(path):
    with open(path, "rb") as f:
        data = f.read()

    face = hb.Face(data)
    font = hb.Font(face)
    font.scale = (face.upem, face.upem)

    return font, face.upem


def _shape(hb_font, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)

    return buf.glyph_infos, buf.glyph_positions


_resource_cache = {}


def _get(bold, size):

    key = (bold, size)

    if key not in _resource_cache:

        path = BOLD_FONT_PATH if bold else FONT_PATH

        hb_font, upem = _make_hb(path)
        scale = size / upem

        ft = freetype.Face(path)
        ft.set_pixel_sizes(0, size)

        lh = (ft.size.height >> 6) - 2
        asc = ft.size.ascender >> 6

        _resource_cache[key] = (hb_font, ft, scale, lh, asc)

    return _resource_cache[key]


# ── RENDER ENGINE (your ORIGINAL logic preserved) ───────

def render_lines(base_img, line_specs, margin_x=60, text_color=(20, 20, 20)):

    img_w, img_h = base_img.size
    margin_y = 10

    rows = []

    for spec in line_specs:
        rows.append(dict(spec))

        for _ in range(spec.get("spacer", 0)):
            rows.append({
                "text": "",
                "bold": False,
                "size": spec.get("size", 42)
            })

    def row_lh(r):
        return _get(r.get("bold", False), r.get("size", 42))[3]

    total_h = sum(row_lh(r) for r in rows)

    if total_h > img_h - 2 * margin_y:
        factor = (img_h - 2 * margin_y) / total_h
        for r in rows:
            r["size"] = max(10, int(r["size"] * factor))

    total_h = sum(row_lh(r) for r in rows)
    start_y = (img_h - total_h) // 2

    canvas = base_img.convert("RGBA")
    pix = np.array(canvas, dtype=np.int32)

    rc, gc, bc = text_color
    cur_y = start_y

    for row in rows:

        text = row.get("text", "")
        bold = row.get("bold", False)
        size = row.get("size", 42)

        hb_font, ft_face, scale, lh, asc = _get(bold, size)

        if text.strip():

            infos, positions = _shape(hb_font, text)

            line_w = sum(int(p.x_advance * scale) for p in positions)
            cursor_x = (img_w - line_w) // 2
            cursor_y = cur_y + asc

            for info, pos in zip(infos, positions):

                ft_face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
                bm = ft_face.glyph.bitmap

                gx = cursor_x + ft_face.glyph.bitmap_left + int(pos.x_offset * scale)
                gy = cursor_y - ft_face.glyph.bitmap_top - int(pos.y_offset * scale)

                if bm.width > 0 and bm.rows > 0:

                    alpha = np.array(bm.buffer, dtype=np.int32).reshape(bm.rows, bm.width)

                    x0, y0 = max(gx, 0), max(gy, 0)
                    x1, y1 = min(gx + bm.width, img_w), min(gy + bm.rows, img_h)

                    bx0, by0 = x0 - gx, y0 - gy

                    if x1 > x0 and y1 > y0:

                        sl = alpha[by0:by0 + (y1 - y0), bx0:bx0 + (x1 - x0)]
                        alpha_factor = sl / 255.0

                        for ci, cv in enumerate([rc, gc, bc]):
                            pix[y0:y1, x0:x1, ci] = (
                                pix[y0:y1, x0:x1, ci] * (1 - alpha_factor)
                                + cv * alpha_factor
                            ).astype(np.int32)

                        pix[y0:y1, x0:x1, 3] = np.clip(
                            pix[y0:y1, x0:x1, 3] + sl,
                            0,
                            255
                        )

                cursor_x += int(pos.x_advance * scale)
                cursor_y -= int(pos.y_advance * scale)

        cur_y += lh

    out = Image.fromarray(pix.astype(np.uint8), "RGBA")
    bg = base_img.convert("RGBA")
    bg.paste(out, (0, 0), out)

    return bg.convert("RGB")


# ── CARD GENERATION (UNCHANGED LOGIC) ───────────────────

def generate_card():

    name = name_entry.get().strip()
    title = title_var.get().strip()

    if not name:
        messagebox.showerror("Error", "කරුණාකර නම ඇතුලත් කරන්න")
        return

    if title == "අදාළ පදවි නාමය":
        messagebox.showerror("Error", "කරුණාකර පදවි නාමය තෝරන්න")
        return

    line_specs = [

        {"text": "අද දින උපන් දිනය සමරන පින්වත්", "bold": False, "size": 22, "spacer": 1},
        {"text": name, "bold": True, "size": 30, "spacer": 1},
        {"text": f"{title}ට", "bold": True, "size": 30, "spacer": 1},

        {"text": "අනන්ත වූ බුදු ගුණ බලයෙන්", "bold": False, "size": 22},
        {"text": "නිදුක් නිරෝගී සැප සම්පත්තිය පිරි", "bold": False, "size": 22},
        {"text": "සුභ උපන් දිනයක් වේවා යි", "bold": False, "size": 22},
        {"text": "මෙත් සිතින් පතමි.", "bold": False, "size": 22, "spacer": 1},

        {"text": "මෙදින සවස 6.30ට", "bold": True, "size": 22},
        {"text": '"බෝසෙවන" විහාරස්ථානයේදී', "bold": True, "size": 22},

        {"text": "ඔබ වෙනුවෙන් විශේෂ", "bold": False, "size": 22},
        {"text": "සෙත් පැතීමක් සිදු කෙරේ.", "bold": False, "size": 22},
        {"text": "එයට සහභාගී වන මෙන්", "bold": False, "size": 22},
        {"text": "කරුණාවෙන් සිහිපත් කරමි.", "bold": False, "size": 22, "spacer": 1},

        {"text": "තෙරුවන් සරණයි!", "bold": True, "size": 36, "spacer": 1},

        {"text": "මෙයට,", "bold": False, "size": 24},
        {"text": "ශාසන දයාවෙන්", "bold": False, "size": 24, "spacer": 1},

        {"text": "විහාරාධිපති", "bold": False, "size": 24},
        {"text": "ගෞරව ශාස්ත්‍රවේදී", "bold": False, "size": 24},
        {"text": "පූජ්‍ය ගොඩපිටියේ ඉන්දානන්ද හිමි", "bold": True, "size": 30},

        {"text": "බෝසෙවන විහාරය", "bold": False, "size": 24},
        {"text": "මාළිගාවත්ත පාර, කොළඹ 10.", "bold": False, "size": 24},
        {"text": "දුරකථනය 2541612", "bold": False, "size": 24},
    ]

    try:
        front = Image.open(FRONT_IMG).convert("RGB")
        back = Image.open(BACK_IMG).convert("RGB")
    except:
        messagebox.showerror("Error", "front.png / back.png not found!")
        return

    back_rendered = render_lines(back, line_specs, margin_x=80)

    final = Image.new(
        "RGB",
        (front.width + back_rendered.width, max(front.height, back_rendered.height))
    )

    final.paste(front, (0, 0))
    final.paste(back_rendered, (front.width, 0))

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    filename = f"Birthday_Card_{name}.jpg"
    save_path = os.path.join(downloads, filename)

    final.save(save_path)

    messagebox.showinfo("Success", f"{filename} Downloads folder එකට save වුණා!")


# ── UI (YOUR ORIGINAL UI RESTORED) ───────────────

ctypes.windll.gdi32.AddFontResourceExW(FONT_PATH, 0x10, 0)

cleanup_old_cards()

root = tk.Tk()
root.title("Birthday Card Maker")
root.geometry("520x500")
root.configure(bg="#f3f8f4")
root.resizable(False, False)

main_frame = tk.Frame(root, bg="#ffffff")
main_frame.place(relx=0.5, rely=0.5, anchor="center", width=460, height=430)

tk.Label(main_frame, text="Birthday Card Maker",
         font=("Arial", 18, "bold"), fg="#1b5e20", bg="#ffffff").pack(pady=20)

tk.Label(main_frame, text="නම ඇතුලත් කරන්න", bg="#ffffff").pack(anchor="w", padx=40)

name_entry = tk.Entry(main_frame, width=30)
name_entry.pack(padx=40, pady=10)

tk.Label(main_frame, text="පදවි නාමය තෝරන්න", bg="#ffffff").pack(anchor="w", padx=40)

title_var = tk.StringVar(value="අදාළ පදවි නාමය")
titles = ["මැතිතුමා","මැතිණිය","දරුවා","දැරිවිය","ආචාර්‍ය්වරයා","ගරු ස්වාමින් වහන්සේ"]

tk.OptionMenu(main_frame, title_var, *titles).pack(pady=10)

tk.Button(main_frame, text="කාඩ් එක සාදන්න",
          bg="#1b5e20", fg="white",
          command=generate_card).pack(pady=20)

tk.Button(main_frame, text="Exit", command=root.destroy).pack()

root.mainloop()