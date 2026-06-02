import sys
import os
import tkinter as tk
from tkinter import ttk, simpledialog
from pynput import keyboard, mouse
from PIL import Image, ImageTk
import time
import asyncio
import websockets
import json
import threading

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def app_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))

def load_somsom_images(user_id):

    user_id = user_id.strip()

    print("frozen:", getattr(sys, "frozen", False))
    print("__file__:", __file__)
    print("sys.executable:", sys.executable)
    print("app_path:", app_path())

    somsom_folder = os.path.join(
        app_path(),
        "somsom",
        user_id
    )

    print("찾는 폴더:", somsom_folder)

    idle_path = os.path.join(somsom_folder, "idle.png")
    typing_path = os.path.join(somsom_folder, "typing.png")
    sleep_path = os.path.join(somsom_folder, "sleep.png")

    print("idle 경로:", idle_path)
    print("idle 존재:", os.path.exists(idle_path))
    print("typing 존재:", os.path.exists(typing_path))
    print("sleep 존재:", os.path.exists(sleep_path))

    try:
        idle = Image.open(idle_path).convert("RGBA")
        typing = Image.open(typing_path).convert("RGBA")
        sleep = Image.open(sleep_path).convert("RGBA")

        return idle, typing, sleep

    except Exception as e:
        print("somsom 이미지 로드 실패:", e)
        return None, None, None


def get_user_original_images(user_id):

    somsom_idle, somsom_typing, somsom_sleep = load_somsom_images(user_id)

    if somsom_idle is not None:
        return somsom_idle, somsom_typing, somsom_sleep

    return idle_original, typing_original, sleep_original

def settings_path():
    return os.path.join(app_path(), "settings.json")

def load_settings():
    if not os.path.exists(settings_path()):
        return {}

    try:
        with open(settings_path(), "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return {}


def save_settings():
    data = {
        "username": username,
        "icon_size": icon_size,
        "icon_alpha": icon_alpha,
        "icon_angle": icon_angle,
        "show_names": show_names,
        "selected_mode": selected_mode,
        "room_code": room_code
    }

    with open(settings_path(), "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

settings_data = load_settings()


root = tk.Tk()
root.withdraw()

username = settings_data.get("username", "익명")

username_window = tk.Toplevel(root)
username_window.title("사용자 이름")
username_window.geometry("300x120")
username_window.attributes("-topmost", True)

name_var = tk.StringVar(value=username)

def confirm_username():
    global username

    entered_name = name_var.get().strip()

    if entered_name:
        username = entered_name

    username_window.destroy()

ttk.Label(
    username_window,
    text="이름을 확인하거나 변경하세요."
).pack(pady=(15, 5))

name_entry = ttk.Entry(
    username_window,
    textvariable=name_var
)
name_entry.pack(padx=20, fill="x")
name_entry.focus()

ttk.Button(
    username_window,
    text="확인",
    command=confirm_username
).pack(pady=10)

username_window.bind(
    "<Return>",
    lambda event: confirm_username()
)

username_window.wait_window()


selected_mode = settings_data.get("selected_mode", None)
room_code = settings_data.get("room_code", None)


root.withdraw()

# 모드 선택
mode_window = tk.Toplevel(root)

mode_window.title("모드 선택")
mode_window.geometry("250x320")
mode_window.attributes("-topmost", True)

preview_idle, _, _ = load_somsom_images(username)
character_exists = preview_idle is not None

if preview_idle is None:
    preview_idle = Image.open(
        resource_path("idle.png")
    ).convert("RGBA")

preview_idle = preview_idle.resize((100, 100))
preview_photo = ImageTk.PhotoImage(preview_idle)

preview_label = tk.Label(
    mode_window,
    image=preview_photo
)
preview_label.image = preview_photo
preview_label.pack(pady=(10, 5))

if not character_exists:
    warning_label = tk.Label(
        mode_window,
        text="이미지가 저장되어 있지 않습니다!",
        fg="#b1000d",
        font=("맑은 고딕", 8, "bold")
    )
    warning_label.pack(pady=(0, 5))

ttk.Label(
    mode_window,
    text="모드를 선택하세요."
).pack(pady=(10, 8))


def select_single():
    global selected_mode

    selected_mode = "single"
    mode_window.destroy()


def select_multi():
    global selected_mode, room_code

    selected_mode = "multi"

    room_code = simpledialog.askstring(
        "방 코드",
        "방 코드를 입력하세요.",
        parent=mode_window
    )

    mode_window.destroy()


ttk.Button(
    mode_window,
    text="개인모드",
    command=select_single
).pack(pady=5)

ttk.Button(
    mode_window,
    text="다인모드",
    command=select_multi
).pack(pady=5)

mode_window.wait_window()

print("모드 선택창 종료됨")
print("선택된 모드:", selected_mode)
print("방 코드:", room_code)

for widget in root.winfo_children():
    widget.destroy()

print("기존 위젯 삭제 완료")

root.deiconify()

print("root 다시 표시 완료")

for widget in root.winfo_children():
    widget.destroy()

root.deiconify()

root.geometry("300x300+500+200")
root.attributes("-topmost", True)
root.overrideredirect(True)

root.configure(bg="black")
root.wm_attributes("-transparentcolor", "black")

# 설정값
icon_size = settings_data.get("icon_size", 200)
icon_alpha = settings_data.get("icon_alpha", 1.0)
icon_angle = settings_data.get("icon_angle", 0)
show_names = settings_data.get("show_names", True)

reset_timer = None
current_state = "idle"

# 마지막 활동 시간
last_activity_time = time.time()

drag_start_x = 0
drag_start_y = 0
other_users = {}
other_user_labels = {}
visible_users = {}
other_user_names = {}
other_user_images = {}


idle_original = Image.open(resource_path("idle.png")).convert("RGBA")
typing_original = Image.open(resource_path("typing.png")).convert("RGBA")
sleep_original = Image.open(resource_path("sleep.png")).convert("RGBA")
my_idle_original, my_typing_original, my_sleep_original = get_user_original_images(username)

print("내 이미지 로드 완료")

idle_photo = None
typing_photo = None
sleep_photo = None
default_idle_photo = None
default_typing_photo = None
default_sleep_photo = None

label = tk.Label(root, bg="black", borderwidth=0, highlightthickness=0)
label.pack(expand=True)

print("내 이미지 로드 완료")

name_label = tk.Label(
    root,
    text=username,
    fg="white",
    bg="black",
    font=("맑은 고딕", 10, "bold")
)

name_label.pack(side="bottom")


def resize_window():
    x = root.winfo_x()
    y = root.winfo_y()

    padding = 40
    window_size = icon_size + padding

    root.geometry(f"{window_size}x{window_size}+{x}+{y}")


def make_image(original):
    img = original.copy()

    img = img.rotate(icon_angle, expand=True)
    img = img.resize((icon_size, icon_size))

    if icon_alpha < 1.0:
        alpha = img.getchannel("A")
        alpha = alpha.point(lambda p: int(p * icon_alpha))
        img.putalpha(alpha)

    return ImageTk.PhotoImage(img)


def refresh_images():
    global idle_photo, typing_photo, sleep_photo
    global default_idle_photo, default_typing_photo, default_sleep_photo

    default_idle_photo = make_image(idle_original)
    default_typing_photo = make_image(typing_original)
    default_sleep_photo = make_image(sleep_original)

    resize_window()

    idle_photo = make_image(my_idle_original)
    typing_photo = make_image(my_typing_original)
    sleep_photo = make_image(my_sleep_original)

    if current_state == "typing":
        label.config(image=typing_photo)
    elif current_state == "sleep":
        label.config(image=sleep_photo)
    else:
        label.config(image=idle_photo)


def show_idle():

    global current_state

    inactive_seconds = time.time() - last_activity_time

    if inactive_seconds >= 60:
        current_state = "sleep"
        label.config(image=sleep_photo)
    else:
        current_state = "idle"
        label.config(image=idle_photo)


def show_typing():
    global reset_timer, current_state, last_activity_time

    last_activity_time = time.time()
    current_state = "typing"

    label.config(image=typing_photo)

    if reset_timer is not None:
        root.after_cancel(reset_timer)

    reset_timer = root.after(500, show_idle)


def check_sleep():
    global current_state

    inactive_seconds = time.time() - last_activity_time

    if inactive_seconds >= 60 and current_state != "sleep":
        current_state = "sleep"
        label.config(image=sleep_photo)

    root.after(1000, check_sleep)


def start_drag(event):
    global drag_start_x, drag_start_y

    drag_start_x = event.x
    drag_start_y = event.y


def drag_window(event):
    new_x = root.winfo_x() + event.x - drag_start_x
    new_y = root.winfo_y() + event.y - drag_start_y

    root.geometry(f"+{new_x}+{new_y}")

def create_other_user(user_id):

    index = len(other_user_labels)

    somsom_idle, somsom_typing, somsom_sleep = load_somsom_images(user_id)

    user_window = tk.Toplevel(root)
    user_window.geometry(f"+{root.winfo_x() + 80 + index * 80}+{root.winfo_y() + 80}")
    user_window.attributes("-topmost", True)
    user_window.overrideredirect(True)
    user_window.configure(bg="black")
    user_window.wm_attributes("-transparentcolor", "black")

    frame = tk.Frame(user_window, bg="black")

    other_label = tk.Label(
        frame,
        image=default_idle_photo,
        bg="black",
        borderwidth=0,
        highlightthickness=0
    )
    other_label.pack()

    other_name = tk.Label(
        frame,
        text=user_id,
        fg="white",
        bg="black",
        font=("맑은 고딕", 9)
    )

    if show_names:
        other_name.pack()

    frame.pack()

    drag_data = {"x": 0, "y": 0}

    def start_other_drag(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y

    def drag_other_window(event):
        new_x = user_window.winfo_x() + event.x - drag_data["x"]
        new_y = user_window.winfo_y() + event.y - drag_data["y"]
        user_window.geometry(f"+{new_x}+{new_y}")

    frame.bind("<Button-1>", start_other_drag)
    frame.bind("<B1-Motion>", drag_other_window)
    other_label.bind("<Button-1>", start_other_drag)
    other_label.bind("<B1-Motion>", drag_other_window)
    other_name.bind("<Button-1>", start_other_drag)
    other_name.bind("<B1-Motion>", drag_other_window)

    other_user_labels[user_id] = {
        "window": user_window,
        "frame": frame,
        "icon": other_label
    }

    other_user_images[user_id] = {
        "idle": somsom_idle,
        "typing": somsom_typing,
        "sleep": somsom_sleep
}

    other_user_names[user_id] = other_name
    visible_users[user_id] = True


def update_other_user_icon(user_id, state):

    if user_id not in other_user_labels:
        create_other_user(user_id)

    other_label = other_user_labels[user_id]["icon"]

    images = other_user_images.get(user_id)

    if images and images["idle"] is not None:

        if state == "typing":
            photo = ImageTk.PhotoImage(
                images["typing"].resize(
                    (icon_size, icon_size)
                )
            )

        elif state == "sleep":
            photo = ImageTk.PhotoImage(
                images["sleep"].resize(
                    (icon_size, icon_size)
                )
            )

        else:
            photo = ImageTk.PhotoImage(
                images["idle"].resize(
                    (icon_size, icon_size)
                )
            )

        other_label.image = photo
        other_label.config(image=photo)

    else:   

        if state == "typing":
            other_label.config(image=default_typing_photo)

        elif state == "sleep":
            other_label.config(image=default_sleep_photo)

        else:
           other_label.config(image=default_idle_photo)

def open_settings(event=None):
    settings = tk.Toplevel(root)
    settings.title("설정")
    settings.attributes("-topmost", True)
    settings.geometry("320x500")

    canvas = tk.Canvas(settings)

    scrollbar = ttk.Scrollbar(
        settings,
        orient="vertical",
        command=canvas.yview
    )

    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window(
        (0, 0),
        window=scrollable_frame,
        anchor="nw"
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    canvas.pack(
        side="left",
        fill="both",
        expand=True
    )

    scrollbar.pack(
        side="right",
        fill="y"
    )

    size_var = tk.IntVar(value=icon_size)
    alpha_var = tk.DoubleVar(value=icon_alpha)
    angle_var = tk.IntVar(value=icon_angle)
    name_var = tk.BooleanVar(value=show_names)

    def apply_settings():
        global icon_size, icon_alpha, icon_angle, show_names

        icon_size = size_var.get()
        icon_alpha = alpha_var.get()
        icon_angle = angle_var.get()
        show_names = name_var.get()

        refresh_images()
        refresh_name_visibility()
        save_settings()

    ttk.Label(scrollable_frame, text="아이콘 크기").pack(pady=(10, 0))

    ttk.Scale(
        scrollable_frame,
        from_=50,
        to=700,
        variable=size_var,
        command=lambda v: apply_settings()
    ).pack(fill="x", padx=20)

    ttk.Label(scrollable_frame, text="아이콘 투명도").pack(pady=(10, 0))

    ttk.Scale(
        scrollable_frame,
        from_=0.1,
        to=1.0,
        variable=alpha_var,
        command=lambda v: apply_settings()
    ).pack(fill="x", padx=20)

    ttk.Label(scrollable_frame, text="아이콘 각도").pack(pady=(10, 0))

    for angle in [0, 90, 180, 270]:
        ttk.Radiobutton(
            scrollable_frame,
            text=f"{angle}도",
            value=angle,
            variable=angle_var,
            command=apply_settings
        ).pack()

    ttk.Checkbutton(
        scrollable_frame,
        text="이름 표시",
        variable=name_var,
        command=apply_settings
    ).pack(pady=10)

    ttk.Label(scrollable_frame, text="접속 중인 사람").pack(pady=(15, 0))

    for user_id in other_user_labels:

        var = tk.BooleanVar(value=visible_users.get(user_id, True))

        ttk.Checkbutton(
            scrollable_frame,
            text=user_id,
            variable=var,
            command=lambda user_id=user_id, var=var: toggle_other_user(
                user_id,
                var.get()
            )
        ).pack()

    ttk.Button(
        scrollable_frame,
        text="프로그램 종료",
        command=lambda: (save_settings(), root.destroy())
    ).pack(pady=15)

def toggle_other_user(user_id, is_visible):

    visible_users[user_id] = is_visible

    if user_id not in other_user_labels:
        return

    window = other_user_labels[user_id]["window"]

    if is_visible:
        window.deiconify()
    else:
        window.withdraw()


def remove_other_user(user_id):

    if user_id in other_user_labels:
        other_user_labels[user_id]["window"].destroy()
        del other_user_labels[user_id]

    if user_id in other_users:
        del other_users[user_id]

    if user_id in visible_users:
        del visible_users[user_id]

    if user_id in other_user_names:
        del other_user_names[user_id]

    if user_id in other_user_images:
        del other_user_images[user_id]

def refresh_name_visibility():

    if show_names:
        name_label.pack(side="bottom")
    else:
        name_label.pack_forget()

    for user_id in other_user_names:

        other_name = other_user_names[user_id]

        if show_names:
            other_name.pack()
        else:
            other_name.pack_forget()

def on_key_press(key):
    root.after(0, show_typing)


def on_mouse_click(x, y, button, pressed):
    if pressed and button == mouse.Button.left:
        root.after(0, show_typing)


label.bind("<Button-1>", start_drag)
label.bind("<B1-Motion>", drag_window)
label.bind("<Button-3>", open_settings)

keyboard_listener = keyboard.Listener(on_press=on_key_press)
mouse_listener = mouse.Listener(on_click=on_mouse_click)

keyboard_listener.start()
mouse_listener.start()

refresh_images()
refresh_name_visibility()
check_sleep()
async def send_loop(websocket):

    while True:
        data = {
            "user": username,
            "state": current_state
        }

        await websocket.send(json.dumps(data))
        await asyncio.sleep(0.5)

async def receive_loop(websocket):

    while True:
        message = await websocket.recv()
        received_data = json.loads(message)

        if received_data.get("type") == "disconnect":
            user_id = received_data["user"]

            root.after(
                0,
                lambda user_id=user_id: remove_other_user(user_id)
            )

            continue

        user_id = received_data["user"]
        state = received_data["state"]

        if user_id != username:
            other_users[user_id] = state

            root.after(
                0,
                lambda user_id=user_id, state=state: update_other_user_icon(user_id, state)
            )


root.mainloop()
async def connect_to_server():

    global room_code

    uri = "wss://typing-somsom.onrender.com"

    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=20,
                open_timeout=60
            ) as websocket:

                await websocket.send(json.dumps({
                    "type": "join",
                    "room": room_code,
                    "user": username
                }))

                print("서버 연결 성공")

                await asyncio.gather(
                    send_loop(websocket),
                    receive_loop(websocket)
                )

        except Exception as e:
            print("서버 연결 끊김, 재시도:", e)
            await asyncio.sleep(3)

