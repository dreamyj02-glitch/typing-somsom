import tkinter as tk
from tkinter import ttk, simpledialog
from pynput import keyboard, mouse
from PIL import Image, ImageTk
import time
import asyncio
import websockets
import json
import threading

root = tk.Tk()

# 모드 선택
mode_window = tk.Toplevel()

mode_window.title("모드 선택")
mode_window.geometry("250x150")
mode_window.attributes("-topmost", True)

selected_mode = None
room_code = None


def select_single():
    global selected_mode

    selected_mode = "single"

    mode_window.destroy()


def select_multi():
    global selected_mode, room_code

    selected_mode = "multi"

    room_code = simpledialog.askstring(
        "방 코드",
        "방 코드를 입력하세요."
    )

    mode_window.destroy()


ttk.Label(
    mode_window,
    text="모드를 선택하세요."
).pack(pady=15)

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

root.withdraw()

mode_window.wait_window()

root.deiconify()

root.geometry("300x300+500+200")
root.attributes("-topmost", True)
root.overrideredirect(True)

root.configure(bg="black")
root.wm_attributes("-transparentcolor", "black")

# 설정값
icon_size = 200
icon_alpha = 1.0
icon_angle = 0

reset_timer = None
current_state = "idle"

# 마지막 활동 시간
last_activity_time = time.time()

drag_start_x = 0
drag_start_y = 0
other_users = {}
other_user_labels = {}
visible_users = {}

username = str(id(root))

idle_original = Image.open("idle.png").convert("RGBA")
typing_original = Image.open("typing.png").convert("RGBA")
sleep_original = Image.open("sleep.png").convert("RGBA")

idle_photo = None
typing_photo = None
sleep_photo = None

label = tk.Label(root, bg="black", borderwidth=0, highlightthickness=0)
label.pack(expand=True)


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

    resize_window()

    idle_photo = make_image(idle_original)
    typing_photo = make_image(typing_original)
    sleep_photo = make_image(sleep_original)

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

    other_label = tk.Label(
        root,
        image=idle_photo,
        bg="black",
        borderwidth=0,
        highlightthickness=0
    )

    other_label.place(
        x=30 + index * 60,
        y=30
    )

    other_user_labels[user_id] = other_label
    visible_users[user_id] = True


def update_other_user_icon(user_id, state):

    if user_id not in other_user_labels:
        create_other_user(user_id)

    other_label = other_user_labels[user_id]

    if state == "typing":
        other_label.config(image=typing_photo)

    elif state == "sleep":
        other_label.config(image=sleep_photo)

    else:
        other_label.config(image=idle_photo)

def open_settings(event=None):
    settings = tk.Toplevel(root)
    settings.title("설정")
    settings.geometry("300x420")
    settings.attributes("-topmost", True)

    size_var = tk.IntVar(value=icon_size)
    alpha_var = tk.DoubleVar(value=icon_alpha)
    angle_var = tk.IntVar(value=icon_angle)

    def apply_settings():
        global icon_size, icon_alpha, icon_angle

        icon_size = size_var.get()
        icon_alpha = alpha_var.get()
        icon_angle = angle_var.get()

        refresh_images()

    ttk.Label(settings, text="아이콘 크기").pack(pady=(10, 0))
    ttk.Scale(
        settings,
        from_=50,
        to=700,
        variable=size_var,
        command=lambda v: apply_settings()
    ).pack(fill="x", padx=20)

    ttk.Label(settings, text="아이콘 투명도").pack(pady=(10, 0))
    ttk.Scale(
        settings,
        from_=0.1,
        to=1.0,
        variable=alpha_var,
        command=lambda v: apply_settings()
    ).pack(fill="x", padx=20)

    ttk.Label(settings, text="아이콘 각도").pack(pady=(10, 0))

    for angle in [0, 90, 180, 270]:
        ttk.Radiobutton(
            settings,
            text=f"{angle}도",
            value=angle,
            variable=angle_var,
            command=apply_settings
        ).pack()

    ttk.Label(settings, text="접속 중인 사람").pack(pady=(15, 0))

    for user_id in other_user_labels:

        var = tk.BooleanVar(value=visible_users.get(user_id, True))

        ttk.Checkbutton(
            settings,
            text=user_id,
            variable=var,
            command=lambda user_id=user_id, var=var: toggle_other_user(
                user_id,
                var.get()
            )
        ).pack()

    ttk.Button(
        settings,
        text="프로그램 종료",
        command=root.destroy
    ).pack(pady=15)

def toggle_other_user(user_id, is_visible):

    visible_users[user_id] = is_visible

    if user_id not in other_user_labels:
        return

    label = other_user_labels[user_id]

    if is_visible:
        index = list(other_user_labels.keys()).index(user_id)

        label.place(
            x=30 + index * 60,
            y=30
        )

    else:
        label.place_forget()

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
check_sleep()
async def connect_to_server():

    try:
        global room_code

        uri = "ws://localhost:8765"

        async with websockets.connect(uri) as websocket:

            await websocket.send(room_code)

            print("서버 연결 성공")

            while True:

                data = {
                    "user": username,
                    "state": current_state
                }

                await websocket.send(json.dumps(data))

                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=0.1
                    )

                    received_data = json.loads(message)

                    user_id = received_data["user"]
                    state = received_data["state"]

                    print(user_id, state)

                    if user_id != username:

                        other_users[user_id] = state

                        root.after(
                            0,
                            lambda user_id=user_id, state=state: update_other_user_icon(user_id, state)
                        )

                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(0.1)

    except Exception as e:
        print("서버 오류:", e)

print("선택된 모드:", selected_mode)
print("방 코드:", room_code)

if selected_mode == "multi":

    threading.Thread(
        target=lambda: asyncio.run(connect_to_server()),
        daemon=True
    ).start()

root.mainloop()