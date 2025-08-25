
# type1_app.py — Addition_type1 (Type-1: Direct Addition of Tens)
# Build (example):
#   pyinstaller --onefile --windowed --clean ^
#     --name Addition_type1 ^
#     --icon=logo.ico ^
#     --add-data "logo.ico;." ^
#     --add-data "logo.png;." ^
#     type1_app.py

import sys, os, time, random, zipfile, tempfile, shutil, webbrowser, subprocess, csv, io, json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog as fd
from datetime import datetime, timedelta

# -------------------- icon helpers --------------------
ICON_FILE_ICO = "logo.ico"   # for classic titlebar icon
ICON_FILE_PNG = "logo.png"   # for taskbar (wm_iconphoto)

def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, *parts)

def _set_windows_appid(app_id="om.addition_type1"):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

def safe_icon(window):
    _set_windows_appid()
    # 1) Titlebar icon (.ico)
    try:
        ico_path = resource_path(ICON_FILE_ICO)
        if os.path.isfile(ico_path):
            window.iconbitmap(ico_path)
    except Exception:
        pass
    # 2) Taskbar icon via PNG
    try:
        png_path = resource_path(ICON_FILE_PNG)
        if os.path.isfile(png_path):
            img = tk.PhotoImage(file=png_path)
            window.wm_iconphoto(True, img)
            if not hasattr(window, "_icon_imgs"):
                window._icon_imgs = []
            window._icon_imgs.append(img)
    except Exception:
        pass

# -------------------- SILENT subprocess helpers --------------------
def _run_silent(cmd, check=True):
    CREATE_NO_WINDOW = 0x08000000
    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except Exception:
        pass
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            startupinfo=si,
            creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e

# ---------- tiny online quotes (best-effort) ----------
def _try_fetch_quotes_online(cache_path):
    try:
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        req = urllib.request.Request("https://type.fit/api/quotes", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2, context=ctx) as r:
            body = r.read().decode("utf-8", "ignore")
        arr = json.loads(body)
        cleaned = []
        for q in arr:
            t = (q.get("text") or "").strip()
            if 8 <= len(t) <= 160:
                cleaned.append(t)
            if len(cleaned) >= 300: break
        if cleaned:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"quotes": cleaned, "ts": time.time()}, f)
    except Exception:
        pass

def _get_cached_quotes():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    cache_dir = os.path.join(appdata, "Addition_type1")
    cache_file = os.path.join(cache_dir, "quotes_cache.json")
    builtin = [
        "Small steps every day beat big plans someday.",
        "Discipline is choosing what you want most over what you want now.",
        "You don’t have to be great to start; you have to start to be great.",
        "Focus: Follow One Course Until Successful.",
        "Consistency is harder when no one is watching — do it anyway.",
        "Win the morning, win the day.",
        "Practice makes progress — perfection is a trap.",
        "If it’s important, schedule it. Then show up.",
        "Your future is built in 30-minute blocks today.",
        "Done > Perfect. Keep moving.",
    ]
    try:
        if os.path.isfile(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            arr = data.get("quotes") or []
            if arr: return arr, cache_file
    except Exception:
        pass
    return builtin, cache_file

def _pick_quote():
    quotes, cache_file = _get_cached_quotes()
    _try_fetch_quotes_online(cache_file)  # non-blocking next time
    return random.choice(quotes)

# -------------- PDF bits --------------
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

W, H = A4
COLS = 4
APP_URL   = "https://ombha.netlify.app"
BASE_NAME = "Addition_type1"
MAX_PDFS, MIN_PDFS = 4000, 1

TASK_PREFIX_FOLDER = "Addition_type1_Reminder_"
TASK_PREFIX_ZIP    = "Addition_type1_Reminder_ZIP_"

def asc(font, size):  return pdfmetrics.getAscent(font)*size/1000.0
def desc(font, size): return abs(pdfmetrics.getDescent(font))*size/1000.0
def text_h(font, size): return asc(font,size)+desc(font,size)
def baseline_for_center(font,size,cy): return cy-text_h(font,size)/2.0
def rounded(c,x,y,w,h,r,stroke=1,fill=0): c.roundRect(x,y,w,h,r,stroke=stroke,fill=fill)

def hsl2hex(h, s, l):
    c=(1-abs(2*l-1))*s; x=c*(1-abs((h/60)%2-1)); m=l-c/2
    if   0<=h<60:  r,g,b=c,x,0
    elif 60<=h<120:r,g,b=x,c,0
    elif 120<=h<180:r,g,b=0,c,x
    elif 180<=h<240:r,g,b=0,x,c
    elif 240<=h<300:r,g,b=x,0,c
    else:           r,g,b=c,0,x
    R,G,B=[int((v+m)*255) for v in (r,g,b)]
    return f"#{R:02X}{G:02X}{B:02X}"

def mix_hex(h1, h2, t):
    h1=h1.lstrip('#'); h2=h2.lstrip('#')
    r1,g1,b1=int(h1[0:2],16),int(h1[2:4],16),int(h1[4:6],16)
    r2,g2,b2=int(h2[0:2],16),int(h2[2:4],16),int(h2[4:6],16)
    r=int(r1+(r2-r1)*t); g=int(g1+(g2-g1)*t); b=int(b1+(b2-b1)*t)
    return f"#{r:02X}{g:02X}{b:02X}"
def lighten(hexcol, t=0.2): return mix_hex(hexcol, '#FFFFFF', max(0,min(1,t)))
def darken (hexcol, t=0.2): return mix_hex(hexcol, '#000000', max(0,min(1,t)))

def draw_poly(c, pts, fill="#000000", stroke=None, sw=1):
    p=c.beginPath(); p.moveTo(pts[0], pts[1])
    for i in range(2, len(pts), 2): p.lineTo(pts[i], pts[i+1])
    p.close()
    if fill:   c.setFillColor(colors.HexColor(fill))
    if stroke: c.setStrokeColor(colors.HexColor(stroke)); c.setLineWidth(sw); c.drawPath(p, fill=1 if fill else 0, stroke=1)
    else:      c.drawPath(p, fill=1, stroke=0)

# -------------------- TYPE-1 QUESTION LOGIC --------------------
# Generate 100 pairs like 50 + 70, 30 + 90, 80 + 20 etc. (multiples of 10)
def gen_qs(seed):
    r = random.Random(seed)
    tens = [10,20,30,40,50,60,70,80,90]
    data = []
    # try to cover variety of sums; avoid identical pairs
    for _ in range(140):
        a = r.choice(tens)
        b = r.choice(tens)
        if a == b and r.random() < 0.6:
            # 40% allow same, otherwise pick a different one
            b = r.choice([t for t in tens if t != a])
        s = a + b
        data.append((a, b, s))
        if len(data) >= 100:
            break
    # ensure exactly 100
    data = data[:100]
    r.shuffle(data)
    return data

def palette(i):
    phi=137.507764
    h=(i*phi)%360; a=(h+18)%360; m=(h-20)%360; g=(h+34)%360
    return {
        "base":   hsl2hex(h, 0.16, 0.97),
        "soft":   hsl2hex(m, 0.20, 0.93),
        "accent": hsl2hex(a, 0.42, 0.70),
        "accent2":hsl2hex(g, 0.30, 0.62),
        "ink":"#111827",
        "badge_outer": hsl2hex(h, 0.14, 0.86),
        "badge_inner":"#FFFFFF",
        "badge_text":"#0F172A",
    }

def draw_bg_page(c, t, idx):
    c.setFillColor(colors.HexColor(t["base"])); c.rect(0,0,W,H,0,1)
    style = idx % 4
    c.setFillColor(colors.HexColor(t["soft"]))
    if style == 0: c.ellipse(-60, H-140, W+120, H-20, 0, 1)
    elif style == 1:
        c.ellipse(30, H-200, 300, H-80, 0, 1); c.ellipse(W-320, H-190, W-60, H-60, 0, 1)
    elif style == 2:
        for b in range(6): c.rect(40+b*100, 28, 60, H-56, 0, 1)
    else:
        for b in range(4): c.ellipse(60+b*140, -10, 360+b*140, 110, 0, 1)

def draw_bg_card(c, x, y, w, h, t, idx):
    line_col  = colors.HexColor(darken(t["soft"],0.10))
    fill1_col = colors.HexColor(lighten(t["soft"],0.08))
    fill2_col = colors.HexColor(lighten(t["soft"],0.16))
    c.saveState(); p=c.beginPath(); p.roundRect(x,y,w,h,16); c.clipPath(p,0,0)
    style = idx % 8
    if style == 0:
        for k in range(8):
            c.setFillColor(fill1_col if k%2==0 else fill2_col)
            c.ellipse(x-220+k*140, y+h-60-k*40, x+w+220, y+h+30-k*40, 0, 1)
    elif style == 1:
        c.setStrokeColor(line_col); c.setLineWidth(1)
        for rad in (280,240,200,160,120): c.circle(x+120, y+h-80, rad, 1, 0)
    elif style == 2:
        rr=random.Random(7000+idx); c.setStrokeColor(line_col); c.setLineWidth(1)
        for _ in range(120):
            xx=rr.uniform(x+20, x+w-20); yy=rr.uniform(y+20, y+h-20)
            if rr.random()<0.5: c.line(xx-6,yy,xx+6,yy); c.line(xx,yy-6,xx,yy+6)
            else: c.line(xx-6,yy+3,xx+6,yy+3); c.line(xx-6,yy-3,xx+6,yy-3)
    elif style == 3:
        for cx,cy in [(x+160,y+h-120),(x+320,y+h-140),(x+480,y+h-110)]:
            c.setFillColor(fill2_col); c.ellipse(cx,cy, cx+160,cy+60, 0, 1)
            c.setFillColor(fill1_col); c.ellipse(cx+60,cy+8, cx+220,cy+68, 0, 1)
    elif style == 4:
        rr=random.Random(9100+idx); c.setFillColor(fill1_col)
        for _ in range(140):
            xx=rr.uniform(x+20,x+w-20); yy=rr.uniform(y+20,y+h-20)
            s=rr.uniform(6,10); c.ellipse(xx,yy,xx+s,yy+s, 0, 1)
    elif style == 5:
        for k in range(6):
            draw_poly(c,[x-60+k*120,y+h-40-k*28, x+w+60,y+h-40-k*28, x+w+60,y+h-10-k*28, x-60+k*120,y+h-10-k*28],
                      fill=fill1_col.hexval() if hasattr(fill1_col,'hexval') else lighten(t["soft"],0.08))
    elif style == 6:
        c.setStrokeColor(line_col); c.setLineWidth(1)
        for yy in range(int(y+40), int(y+h-20), 40): c.arc(x+20, yy-20, x+w-20, yy+20, 0, 180)
    else:
        c.setFillColor(fill1_col)
        for k in range(9):
            y0 = y+40+k*40
            draw_poly(c,[x+30,y0, x+60,y0+22, x+90,y0, x+60,y0-22],
                      fill=fill1_col.hexval() if hasattr(fill1_col,'hexval') else lighten(t["soft"],0.08))
    c.restoreState()

def draw_header_var(c, t, idx):
    title = "Type-1 • Direct Addition (Tens)"; sub="100 Questions"
    rng = random.Random(200_000 + idx * 73)
    w = rng.randint(400, 540); h = rng.randint(46, 64); rad = rng.randint(8, 26)
    x = W/2 - w/2; y = H - 44 - h
    a_hex, b_hex = t["accent"], t["accent2"]; family = rng.randrange(12)
    c.setFillColor(colors.HexColor(a_hex))
    if family == 0:
        c.roundRect(x,y,w,h,rad,0,1); c.setFillColor(colors.HexColor(lighten(a_hex,0.35)))
        c.roundRect(x + w*0.04, y + h*0.70, w*0.92, h*0.22, h*0.18, 0, 1)
    else:
        c.roundRect(x,y,w,h,rad,0,1); c.setFillColor(colors.HexColor(b_hex))
        c.ellipse(x+60, y+h-18, x+w-60, y+h+10, 0, 1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",14); c.drawCentredString(W/2, y + h*0.58, title)
    c.setFont("Helvetica",9); c.drawCentredString(W/2, y + h*0.30, sub)
    return y, h

def draw_card(c,m=26):
    x,y=m,m; w,h=W-2*m,H-2*m
    c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor("#E5E7EB"))
    rounded(c,x,y,w,h,16,1,1); return x,y,w,h

def draw_answers(c,x,y,w):
    ay,ah=y+50,150; ax,aw=x+16,w-32
    c.setStrokeColor(colors.HexColor("#E5E7EB")); rounded(c,ax,ay,aw,ah,8,1,0)
    c.setFont("Helvetica-Bold",10); c.setFillColor(colors.black)
    c.drawString(ax+10,ay+ah-14,"Answers"); return ax,ay,aw,ah

def draw_answers_text(c,ax,ay,aw,ah,data):
    c.setFont("Helvetica",8.6); c.setFillColor(colors.black)
    cols=10; cw=(aw-16)/cols; ax0,ay0=ax+8,ay+ah-28
    for i in range(100):
        cx,rr=i%cols, i//cols
        c.drawString(ax0+cx*cw, ay0-rr*12, f"{i+1:>2}. {data[i][2]}")

def draw_badge(c,cx,cy,label,t):
    c.setFillColor(colors.HexColor("#E4E6EB")); rounded(c,cx-12,cy-7,24,14,6,0,1)
    c.setFillColor(colors.HexColor(t["badge_outer"])); rounded(c,cx-11,cy-8,22,14,6,0,1)
    c.setFillColor(colors.HexColor(t["badge_inner"])); rounded(c,cx-9,cy-6,18,10,5,0,1)
    c.setFont("Helvetica-Bold",9.0); c.setFillColor(colors.HexColor(t["badge_text"]))
    c.drawCentredString(cx, baseline_for_center("Helvetica-Bold", 9.0, cy), label)

def draw_questions(c,x,y,w,pill_y,pill_h,ans_ay,ans_ah,t,data):
    start_y=pill_y-30; cutoff=ans_ay+ans_ah+12
    col_w=(w-2*18)/COLS
    c.setFont("Helvetica",10); c.setFillColor(colors.HexColor(t["ink"]))
    c.drawString(x+18, start_y+12, "Example: 50 + 70 = 120 (Direct addition)")
    line_h=17.5
    for i in range(100):
        col,row=i%COLS,i//COLS
        base_y=start_y-22-row*line_h
        if base_y<cutoff: break
        cx=x+18+col*col_w+col_w/2
        draw_badge(c, cx-col_w/2+12, base_y+6, f"{i+1}", t)
        c.setFont("Helvetica",10.5); c.setFillColor(colors.HexColor(t["ink"]))
        a,b,_=data[i]; c.drawString(cx-col_w/2+32, base_y, f"{a} + {b} =")

def generate_pdfs(target, total, progress_cb=None):
    os.makedirs(target, exist_ok=True)
    for idx in range(total):
        if progress_cb: progress_cb(idx)
        t=palette(idx); data=gen_qs(7000+idx*53)
        path=os.path.join(target, f"Day {idx+1}.pdf")
        c=pdfcanvas.Canvas(path, pagesize=A4)
        draw_bg_page(c, t, idx)
        x,y,w,h=draw_card(c)
        draw_bg_card(c, x,y,w,h, t, idx)
        py,ph=draw_header_var(c, t, idx)
        ax,ay,aw,ah=draw_answers(c,x,y,w)
        draw_answers_text(c,ax,ay,aw,ah,data)
        draw_questions(c,x,y,w,py,ph,ay,ah,t,data)
        c.linkURL(APP_URL,(W/2-140,y+10,W/2+140,y+26))
        c.setFont("Helvetica",9); c.setFillColor(colors.HexColor("#6B7280"))
        c.drawCentredString(W/2,y+16,"Made by Om • ombha.netlify.app")
        c.save()
        if progress_cb: progress_cb(idx+1)

def zip_from_folder(folder_path, zip_path):
    try:
        if os.path.exists(zip_path): os.remove(zip_path)
    except PermissionError:
        base,ext=os.path.splitext(zip_path)
        zip_path=f"{base}_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(folder_path)):
            if name.lower().endswith(".pdf"):
                z.write(os.path.join(folder_path,name), arcname=name)
    return zip_path

# -------------------- Reminder system (same as Type-8) --------------------
def _is_bundled():
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

def _app_task_command(args_list):
    if _is_bundled():
        exe = os.path.abspath(sys.executable)
        full = ' '.join([f'"{exe}"'] + [f'"{a}"' for a in args_list])
    else:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw): pyw = sys.executable
        script = os.path.abspath(sys.argv[0])
        full = ' '.join([f'"{pyw}"', f'"{script}"'] + [f'"{a}"' for a in args_list])
    return full

def _create_daily_task(task_name, full_tr_command, time_hhmm_24):
    cmd = ["schtasks","/Create","/SC","DAILY","/TN",task_name,"/TR",full_tr_command,"/ST",time_hhmm_24,"/F"]
    try:
        _run_silent(cmd, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, (e.stderr or "").strip()

def _list_our_task_rows():
    try:
        out = _run_silent(["schtasks","/Query","/FO","CSV","/V"], check=True).stdout
    except Exception:
        return []
    try:
        reader = csv.DictReader(io.StringIO(out))
    except Exception:
        return []
    rows=[]
    for row in reader:
        tn = (row.get("TaskName","") or "").strip().lstrip("\\")
        run = (row.get("Task To Run","") or "").lower()
        if (tn.startswith(TASK_PREFIX_FOLDER) or tn.startswith(TASK_PREFIX_ZIP)
            or tn.startswith("Type1_Reminder_") or tn.startswith("Type1_Zip_Reminder_")
            or "--open-folder" in run or "--open-zip" in run):
            row["_TaskNameClean"]=tn
            rows.append(row)
    return rows

def _parse_dt(s):
    s=(s or "").strip()
    if not s or s.upper()=="N/A": return None
    fmts=[
        "%m/%d/%Y %I:%M:%S %p","%d/%m/%Y %I:%M:%S %p","%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S","%d/%m/%Y %H:%M:%S","%d-%m-%Y %I:%M:%S %p"
    ]
    for f in fmts:
        try: return datetime.strptime(s,f)
        except: pass
    try: return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except: return None

def get_next_run_time_from_system():
    rows=_list_our_task_rows()
    best_dt,best_name=None,""
    now=datetime.now()
    for r in rows:
        nxt=_parse_dt(r.get("Next Run Time","") or r.get("Next Run Time "))
        if nxt and nxt>now and (best_dt is None or nxt<best_dt):
            best_dt,best_name=nxt,r["_TaskNameClean"]
    return best_dt,best_name

def _list_our_task_names():
    return [r["_TaskNameClean"] for r in _list_our_task_rows()]

def remove_all_reminders():
    for tn in _list_our_task_names():
        try:
            _run_silent(["schtasks","/Delete","/TN",tn,"/F"], check=True)
        except subprocess.CalledProcessError:
            pass
    for i in range(1,10):
        for base in (TASK_PREFIX_FOLDER,TASK_PREFIX_ZIP,"Type1_Reminder_","Type1_Zip_Reminder_"):
            try:
                _run_silent(["schtasks","/Delete","/TN",f"{base}{i}","/F"], check=True)
            except subprocess.CalledProcessError:
                pass

# -------------------- Custom Reminder Popup --------------------
class ReminderPopup(tk.Toplevel):
    def __init__(self, parent, title, main_text, quote_text, ok_text="OK", cancel_text="Cancel"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        safe_icon(self)

        frm = ttk.Frame(self, padding=14)
        frm.grid()

        hdr = ttk.Label(frm, text=main_text, font=("Segoe UI", 12, "bold"))
        hdr.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))

        card = tk.Frame(frm, bg="#0B1220", highlightthickness=0)
        card.grid(row=1, column=0, columnspan=2, sticky="we")
        q = tk.Label(card, text="“" + quote_text + "”", wraplength=420,
                     fg="#D1FAE5", bg="#0B1220", justify="left", font=("Segoe UI", 10))
        q.pack(padx=10, pady=10)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, pady=(12,4))
        self.ok = ttk.Button(btns, text=ok_text); self.ok.grid(row=0, column=0, padx=6)
        self.cancel = ttk.Button(btns, text=cancel_text, command=self.destroy)
        self.cancel.grid(row=0, column=1, padx=6)

        link = tk.Label(frm, text="Made by Om • ombha.netlify.app",
                        fg="#2563EB", cursor="hand2", font=("Segoe UI", 9, "italic"))
        link.grid(row=3, column=0, columnspan=2, pady=(2,0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://ombha.netlify.app"))

        self.update_idletasks()
        w = 480; h = 230
        sx = self.winfo_screenwidth()//2 - w//2
        sy = self.winfo_screenheight()//2 - h//2
        self.geometry(f"{w}x{h}+{sx}+{sy}")
        self.grab_set()

# -------------------- Actions on reminder fire --------------------
def _open_folder_interactive(path):
    root=tk.Tk(); root.withdraw()
    quote = _pick_quote()
    dlg = ReminderPopup(root, "Addition_type1 Reminder",
                        "Reminder: You set for study.\nOpen folder now?",
                        quote, ok_text="Open Folder")
    def _do():
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            newdir = fd.askdirectory(title="Pick your Addition_type1 PDFs folder")
            if newdir: os.startfile(newdir)
        dlg.destroy(); root.destroy()
    dlg.ok.configure(command=_do)
    dlg.wait_window(dlg)

def _open_zip_interactive(zipf):
    root=tk.Tk(); root.withdraw()
    quote = _pick_quote()
    dlg = ReminderPopup(root, "Addition_type1 Reminder (ZIP)",
                        "Reminder: You set for study.\nOpen ZIP location now?",
                        quote, ok_text="Show ZIP")
    def _do():
        if zipf and os.path.isfile(zipf):
            subprocess.Popen(["explorer", f"/select,{zipf}"])
        else:
            folder = fd.askdirectory(title="Pick folder that contains your Addition_type1 ZIP")
            if folder: os.startfile(folder)
        dlg.destroy(); root.destroy()
    dlg.ok.configure(command=_do)
    dlg.wait_window(dlg)

# -------------------- Digital Clock Picker --------------------
class ClockPicker(ttk.Frame):
    def __init__(self, parent, initial=None, big=True):
        super().__init__(parent)
        now = datetime.now()
        if initial:
            hh, mm = map(int, initial.split(":"))
        else:
            hh, mm = now.hour, now.minute
        self.hr12 = ((hh-1) % 12) + 1
        self.min  = mm
        self.ampm = tk.StringVar(value=("PM" if hh>=12 else "AM"))

        w = 220 if big else 170
        h = 60  if big else 40
        self.canvas = tk.Canvas(self, width=w, height=h, bg="#0F172A", highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=2, padx=(0,10))
        self._draw_bg(w,h)
        self.text_id = self.canvas.create_text(w//2, h//2, text="",
                                               font=("Consolas", 24 if big else 18, "bold"),
                                               fill="#22D3EE")

        btn_hr_up   = ttk.Button(self, width=3, text="▲", command=self._hr_up)
        btn_hr_down = ttk.Button(self, width=3, text="▼", command=self._hr_down)
        btn_hr_up.grid(row=0, column=1, padx=2); btn_hr_down.grid(row=1, column=1, padx=2)

        btn_mn_up   = ttk.Button(self, width=3, text="▲", command=self._mn_up)
        btn_mn_down = ttk.Button(self, width=3, text="▼", command=self._mn_down)
        btn_mn_up.grid(row=0, column=2, padx=2); btn_mn_down.grid(row=1, column=2, padx=2)

        self.dd = ttk.Combobox(self, width=4, values=["AM","PM"], textvariable=self.ampm, state="readonly")
        self.dd.grid(row=0, column=3, rowspan=2, padx=(6,0))

        self.after(100, self._tick)

    def _draw_bg(self, w, h):
        c=self.canvas
        def rr(x1,y1,x2,y2,r,fill,outline):
            c.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style="pieslice", fill=fill, outline=fill)
            c.create_arc(x2-2*r, y1, x2, y1+2*r, start=0,  extent=90, style="pieslice", fill=fill, outline=fill)
            c.create_arc(x1, y2-2*r, x1+2*r, y2, start=180,extent=90, style="pieslice", fill=fill, outline=fill)
            c.create_arc(x2-2*r, y2-2*r, x2, y2, start=270,extent=90, style="pieslice", fill=fill, outline=fill)
            c.create_rectangle(x1+10, y1, x2-10, y2, fill=fill, outline=fill)
            c.create_rectangle(x1, y1+10, x2, y2-10, fill=fill, outline=fill)
            c.create_rectangle(x1+1, y1+1, x2-1, y2-1, outline="#1F2937")
        rr(2,2,w-2,h-2,14,"#111827","#1F2937")

    def _tick(self):
        now = datetime.now()
        secs = now.second
        disp = f"{self.hr12:02d}:{self.min:02d}:{secs:02d}"
        color = "#22D3EE" if secs>10 else "#F59E0B"
        self.canvas.itemconfig(self.text_id, text=disp, fill=color)
        self.after(200, self._tick)

    def _hr_up(self):   self.hr12 = 1 if self.hr12==12 else self.hr12+1
    def _hr_down(self): self.hr12 = 12 if self.hr12==1  else self.hr12-1
    def _mn_up(self):   self.min  = 0 if self.min==59    else self.min+1
    def _mn_down(self): self.min  = 59 if self.min==0     else self.min-1

    def as_24h(self):
        h = self.hr12 % 12
        if self.ampm.get()=="PM": h += 12
        return f"{h:02d}:{self.min:02d}"

# -------------------- Reminder dialog --------------------
class ReminderDialog(tk.Toplevel):
    def __init__(self, parent, open_target, is_zip=False):
        super().__init__(parent); self.title("Set Daily Reminder"); self.resizable(False, False)
        safe_icon(self)
        self.result=None; self.open_target=open_target; self.is_zip=is_zip
        frm=ttk.Frame(self, padding=14); frm.grid()

        row=0
        ttk.Label(frm,text="How many reminders per day? (1–5)").grid(row=row,column=0,sticky="w")
        self.count=tk.IntVar(value=1)
        spin=ttk.Spinbox(frm,from_=1,to=5,width=5,textvariable=self.count,wrap=True,command=self._refresh,state="readonly")
        spin.grid(row=row,column=1,padx=(8,0),sticky="w"); row+=1

        ttk.Label(frm,text="Pick times (tap arrows to adjust)").grid(row=row,column=0,columnspan=2,sticky="w",pady=(8,4)); row+=1

        self.big_clock = ClockPicker(frm, big=True)
        self.big_clock.grid(row=row,column=0,columnspan=2,sticky="w",pady=(0,8)); row+=1

        qline = ttk.Label(frm, text="“" + _pick_quote() + "”", wraplength=420, foreground="#2563EB", justify="left")
        qline.grid(row=row, column=0, columnspan=2, sticky="we", pady=(0,10)); row+=1

        self.rows_frame=ttk.Frame(frm); self.rows_frame.grid(row=row,column=0,columnspan=2,sticky="w"); row+=1
        self.pickers=[]
        for i in range(4):
            rowf=ttk.Frame(self.rows_frame); rowf.grid(row=i,column=0, pady=3, sticky="w")
            ttk.Label(rowf, text=f"#{i+2}").grid(row=0,column=0,padx=(0,6))
            cp=ClockPicker(rowf, big=False); cp.grid(row=0,column=1)
            self.pickers.append((rowf,cp))

        btns=ttk.Frame(frm); btns.grid(row=row,column=0,columnspan=2,pady=(12,0)); row+=1
        ttk.Button(btns,text="Create Reminders",command=self.on_ok).grid(row=0,column=0,padx=6)
        ttk.Button(btns,text="Cancel",command=self.destroy).grid(row=0,column=1,padx=6)

        self._refresh(); self.grab_set(); self.wait_window(self)

    def _refresh(self, *_):
        n=self.count.get()
        for i,(rowf,_) in enumerate(self.pickers):
            (rowf.grid() if i<(n-1) else rowf.grid_remove())

    def on_ok(self):
        n=self.count.get()
        out=[ self.big_clock.as_24h() ]
        for i in range(n-1):
            _, cp = self.pickers[i]
            out.append(cp.as_24h())
        self.result=out; self.destroy()

# -------------------- Main UI --------------------
class AppUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Addition_type1 Generator (Type-1)"); self.resizable(False, False)
        safe_icon(self)
        self.total = tk.IntVar(value=100); self.mode=None; self.path=None

        frm = ttk.Frame(self, padding=14); frm.grid()
        ttk.Label(frm, text="Number of PDFs (1–4000):").grid(row=0, column=0, sticky="w")
        self.entry = ttk.Entry(frm, textvariable=self.total, width=10); self.entry.grid(row=0, column=1, sticky="w"); self.entry.focus()

        btns = ttk.Frame(frm); btns.grid(row=1, column=0, columnspan=3, pady=(10,8))
        ttk.Button(btns, text="Create PDFs (Folder…)", command=self.choose_folder).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Create ZIP…",         command=self.choose_zip).grid(row=0, column=1, padx=4)
        ttk.Button(btns, text="Cancel",              command=self.finish_exit).grid(row=0, column=2, padx=4)

        rbtns = ttk.Frame(frm); rbtns.grid(row=2, column=0, columnspan=3, pady=(4,2))
        ttk.Button(rbtns, text="Set Reminder for Folder…", command=self.manual_reminder_folder).grid(row=0, column=0, padx=4)
        ttk.Button(rbtns, text="Set Reminder for ZIP…",    command=self.manual_reminder_zip).grid(row=0, column=1, padx=4)
        ttk.Button(rbtns, text="Remove All Reminders",     command=self.remove_reminders).grid(row=0, column=2, padx=4)

        credit = ttk.Label(frm, text="Made exe by Omdevsinh Gohil • ombha.netlify.app", foreground="#2563EB", cursor="hand2")
        credit.grid(row=3, column=0, columnspan=3, pady=(8,0))
        credit.bind("<Button-1>", lambda e: webbrowser.open(APP_URL))

        self.countdown = ttk.Label(frm, text="", foreground="#2563EB", anchor="center", justify="center")
        self.countdown.grid(row=4, column=0, columnspan=3, pady=(6,0))
        self.countdown.grid_remove()

        self._next_run = None
        self._poll_ms = 30000  # every 30s
        self.after(200, self.refresh_next_run_from_system)
        self.after(100, self._tick_countdown)

    def _format_delta(self, delta: timedelta):
        if delta.total_seconds() < 0: delta = timedelta(0)
        hrs = int(delta.total_seconds() // 3600)
        mins = int((delta.total_seconds() % 3600) // 60)
        secs = int(delta.total_seconds() % 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def refresh_next_run_from_system(self):
        nxt, _ = get_next_run_time_from_system()
        if nxt:
            self._next_run = nxt
            self.countdown.grid()
        else:
            self._next_run = None
            self.countdown.grid_remove()
        self._render_countdown_label()
        self.after(self._poll_ms, self.refresh_next_run_from_system)

    def _tick_countdown(self):
        self._render_countdown_label()
        self.after(250, self._tick_countdown)

    def _render_countdown_label(self):
        if not self._next_run:
            self.countdown.grid_remove()
            return
        now = datetime.now()
        delta = self._next_run - now
        if delta.total_seconds() <= 0:
            self.countdown.configure(text=f"Reminder due now (at {self._next_run.strftime('%I:%M %p')}).")
            return
        at_str = self._next_run.strftime("%I:%M %p")
        self.countdown.configure(text=f"Next reminder in {self._format_delta(delta)} (at {at_str}).")

    def _set_next_run_from_times(self, times_24h):
        now = datetime.now()
        cands=[]
        for t in times_24h:
            try:
                hh,mm = map(int, t.split(":"))
                dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if dt <= now: dt += timedelta(days=1)
                cands.append(dt)
            except: pass
        if cands:
            self._next_run = min(cands)
            self.countdown.grid()
            self._render_countdown_label()

    # ----- PDF -----
    def validate_total(self):
        try: n = int(str(self.total.get()))
        except: messagebox.showerror("Invalid", "Please enter a number."); return None
        if not (MIN_PDFS <= n <= MAX_PDFS):
            messagebox.showerror("Invalid", f"Number must be between {MIN_PDFS} and {MAX_PDFS}."); return None
        return n

    def choose_folder(self):
        n = self.validate_total()
        if n is None: return
        parent = fd.askdirectory(title="Choose parent folder for PDFs",
                                 initialdir=os.path.expanduser("~\\Desktop"))
        if not parent: return
        folder = os.path.join(parent, BASE_NAME)
        if os.path.exists(folder):
            folder = f"{folder}_{time.strftime('%Y%m%d_%H%M%S')}"
        self.mode="folder"; self.path=folder
        self.start_generation(n)

    def choose_zip(self):
        n = self.validate_total()
        if n is None: return
        zpath = fd.asksaveasfilename(title="Save ZIP as",
                                     initialfile=f"{BASE_NAME}.zip",
                                     defaultextension=".zip",
                                     filetypes=[("ZIP archive","*.zip")],
                                     initialdir=os.path.expanduser("~\\Desktop"))
        if not zpath: return
        if not zpath.lower().endswith(".zip"): zpath += ".zip"
        self.mode="zip"; self.path=zpath
        self.start_generation(n)

    def start_generation(self, n):
        self.status = ttk.Label(self, text="Preparing…"); self.status.grid()
        self.progress = ttk.Progressbar(self, orient="horizontal", length=360, mode="determinate", maximum=n)
        self.progress.grid(pady=(2,8))
        self.update_idletasks()
        self.after(100, lambda: self.run_generation(n))

    def run_generation(self, n):
        try:
            if self.mode=="folder":
                generate_pdfs(self.path, n, progress_cb=self.on_prog)
                self.show_done(folder=self.path)
            else:
                tmp=tempfile.mkdtemp()
                generate_pdfs(tmp, n, progress_cb=self.on_prog)
                zip_from_folder(tmp, self.path)
                shutil.rmtree(tmp)
                self.show_done(zipf=self.path)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_prog(self, k):
        self.progress["value"]=k
        self.status.configure(text=f"Generating… {min(k+1,int(self.progress['maximum']))}/{int(self.progress['maximum'])}")
        self.update_idletasks()

    def show_done(self, folder=None, zipf=None):
        self.status.configure(text="✅ Completed!")
        self.done = ttk.Frame(self); self.done.grid(pady=(4,0))
        row=0
        if folder:
            ttk.Label(self.done, text=f"Saved Folder:\n{folder}", justify="left").grid(row=row,column=0,sticky="w"); row+=1
            ttk.Button(self.done, text="Open Folder", command=lambda: os.startfile(folder)).grid(row=row,column=0,pady=(6,0)); row+=1
            ttk.Button(self.done, text="Set Daily Reminder…", command=lambda: self.ask_reminder_folder(folder)).grid(row=row,column=0,pady=(6,0)); row+=1
        if zipf:
            ttk.Label(self.done, text=f"Saved ZIP:\n{zipf}", justify="left").grid(row=row,column=0,sticky="w"); row+=1
            ttk.Button(self.done, text="Open ZIP", command=lambda: os.startfile(zipf)).grid(row=row,column=0,pady=(6,0)); row+=1
            ttk.Button(self.done, text="Set Daily Reminder…", command=lambda: self.ask_reminder_zip(zipf)).grid(row=row,column=0,pady=(6,0)); row+=1
        ttk.Button(self.done, text="Close", command=self.finish_exit).grid(row=row,column=0,pady=(8,0))

    # ----- Reminders -----
    def ask_reminder_folder(self, folder):
        dlg = ReminderDialog(self, folder, is_zip=False)
        if not dlg.result: return
        errors=[]
        for idx, tstr in enumerate(dlg.result, start=1):
            args = ["--open-folder", folder]
            full_tr = _app_task_command(args)
            ok, err = _create_daily_task(f"{TASK_PREFIX_FOLDER}{idx}", full_tr, tstr)
            if not ok: errors.append(f"{tstr} → {err}")
        if errors:
            messagebox.showwarning("Reminder", "Some reminders failed:\n\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Reminder", f"Daily reminders set at: {', '.join(dlg.result)}")
        self._set_next_run_from_times(dlg.result)
        self.after(500, self.refresh_next_run_from_system)

    def ask_reminder_zip(self, zipf):
        dlg = ReminderDialog(self, zipf, is_zip=True)
        if not dlg.result: return
        errors=[]
        for idx, tstr in enumerate(dlg.result, start=1):
            args = ["--open-zip", zipf]
            full_tr = _app_task_command(args)
            ok, err = _create_daily_task(f"{TASK_PREFIX_ZIP}{idx}", full_tr, tstr)
            if not ok: errors.append(f"{tstr} → {err}")
        if errors:
            messagebox.showwarning("Reminder", "Some reminders failed:\n\n" + "\n".join(errors))
        else:
            messagebox.showinfo("Reminder", f"Daily reminders set at: {', '.join(dlg.result)}")
        self._set_next_run_from_times(dlg.result)
        self.after(500, self.refresh_next_run_from_system)

    def manual_reminder_folder(self):
        folder = fd.askdirectory(title="Pick PDFs folder for reminder")
        if not folder: return
        self.ask_reminder_folder(folder)

    def manual_reminder_zip(self):
        zipf = fd.askopenfilename(title="Pick ZIP for reminder", filetypes=[("ZIP archive","*.zip")])
        if not zipf: return
        self.ask_reminder_zip(zipf)

    def remove_reminders(self):
        remove_all_reminders()
        messagebox.showinfo("Reminders", "All Addition_type1 reminders removed.")
        self._next_run=None
        self.countdown.grid_remove()
        self.after(100, self.refresh_next_run_from_system)

    def finish_exit(self):
        try: self.destroy()
        except: pass
        sys.exit(0)

# -------------------- CLI entry --------------------

# -------------------- Custom Reminder Popup --------------------
class ReminderPopup(tk.Toplevel):
    def __init__(self, parent, title, main_text, quote_text, ok_text="OK", cancel_text="Cancel"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        safe_icon(self)

        frm = ttk.Frame(self, padding=14); frm.grid()
        hdr = ttk.Label(frm, text=main_text, font=("Segoe UI", 12, "bold"))
        hdr.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))

        card = tk.Frame(frm, bg="#0B1220", highlightthickness=0); card.grid(row=1, column=0, columnspan=2, sticky="we")
        q = tk.Label(card, text="“" + _pick_quote() + "”", wraplength=420,
                     fg="#D1FAE5", bg="#0B1220", justify="left", font=("Segoe UI", 10))
        q.pack(padx=10, pady=10)

        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, pady=(12,4))
        self.ok = ttk.Button(btns, text=ok_text); self.ok.grid(row=0, column=0, padx=6)
        self.cancel = ttk.Button(btns, text="Cancel", command=self.destroy); self.cancel.grid(row=0, column=1, padx=6)

        link = tk.Label(frm, text="Made by Om • ombha.netlify.app",
                        fg="#2563EB", cursor="hand2", font=("Segoe UI", 9, "italic"))
        link.grid(row=3, column=0, columnspan=2, pady=(2,0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://ombha.netlify.app"))

        self.update_idletasks()
        w, h = 480, 230
        sx = self.winfo_screenwidth()//2 - w//2
        sy = self.winfo_screenheight()//2 - h//2
        self.geometry(f"{w}x{h}+{sx}+{sy}")
        self.grab_set()

# -------------------- Actions when a scheduled reminder fires --------------------
def _open_folder_interactive(path):
    root = tk.Tk(); root.withdraw()
    quote = _pick_quote()
    dlg = ReminderPopup(root, "Reminder", "Reminder: You set for study.\nOpen folder now?", quote, ok_text="Open Folder")
    def _do():
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            newdir = fd.askdirectory(title="Pick your PDFs folder")
            if newdir: os.startfile(newdir)
        dlg.destroy(); root.destroy()
    dlg.ok.configure(command=_do)
    dlg.wait_window(dlg)

def _open_zip_interactive(zipf):
    root = tk.Tk(); root.withdraw()
    quote = _pick_quote()
    dlg = ReminderPopup(root, "Reminder (ZIP)", "Reminder: You set for study.\nOpen ZIP location now?", quote, ok_text="Show ZIP")
    def _do():
        if zipf and os.path.isfile(zipf):
            subprocess.Popen(["explorer", f"/select,{zipf}"])
        else:
            folder = fd.askdirectory(title="Pick folder that contains your ZIP")
            if folder: os.startfile(folder)
        dlg.destroy(); root.destroy()
    dlg.ok.configure(command=_do)
    dlg.wait_window(dlg)

def _handle_scheduled_invocation(argv):
    if "--open-folder" in argv:
        i = argv.index("--open-folder")
        path = argv[i+1] if i+1 < len(argv) else ""
        _open_folder_interactive(path)
        return True
    if "--open-zip" in argv:
        i = argv.index("--open-zip")
        path = argv[i+1] if i+1 < len(argv) else ""
        _open_zip_interactive(path)
        return True
    return False

# -------------------- launcher --------------------
if __name__=="__main__":
    if _handle_scheduled_invocation(sys.argv[1:]):
        sys.exit(0)
    AppUI().mainloop()
