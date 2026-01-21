import time
import threading
import tkinter as tk
from tkinter import ttk
from pynput import mouse, keyboard
class MacroRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoFlow Macro Recorder")
        self.root.geometry("560x460")
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.events = []
        self.start_time = 0
        self.is_recording = False
        self.is_playing = False
        # Playback controls
        self.playback_speed = tk.DoubleVar(value=1.0)
        self.loop_enabled = tk.BooleanVar(value=False)
        self.loop_count = tk.IntVar(value=1)
        # Hotkeys
        self.record_hotkey = tk.StringVar(value="f8")
        self.play_hotkey = tk.StringVar(value="f9")
        self.stop_hotkey = tk.StringVar(value="f10")
        self.speed_up_hotkey = tk.StringVar(value="f11")
        self.speed_down_hotkey = tk.StringVar(value="f12")

        self.mouse_listener = None
        self.keyboard_listener = None
        self.hotkey_listener = None

        self.create_widgets()
        self.start_hotkey_listener()

    # ---------------- UI ---------------- #

    def create_widgets(self):
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, font=("Arial", 12)).pack(pady=10)

        # Main buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack()

        ttk.Button(btn_frame, text="Record", command=self.toggle_recording).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Play", command=self.start_playback).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Stop", command=self.stop_all).grid(row=0, column=2, padx=5)

        # Hotkeys
        hotkey_frame = ttk.LabelFrame(self.root, text="Hotkeys")
        hotkey_frame.pack(fill="x", padx=10, pady=10)

        labels = [
            ("Record", self.record_hotkey),
            ("Play  ", self.play_hotkey),
            ("Stop  ", self.stop_hotkey),
            ("Speed +", self.speed_up_hotkey),
            ("Speed -", self.speed_down_hotkey)
        ]

        for i, (text, var) in enumerate(labels):
            ttk.Label(hotkey_frame, text=text + ":").grid(row=i // 2, column=(i % 2) * 2, padx=5, sticky="e")
            ttk.Entry(hotkey_frame, textvariable=var, width=6).grid(row=i // 2, column=(i % 2) * 2 + 1, padx=5)

        ttk.Button(hotkey_frame, text="Apply Hotkeys", command=self.restart_hotkeys)\
            .grid(row=3, column=0, columnspan=4, pady=5)

        # Playback options
        playback_frame = ttk.LabelFrame(self.root, text="Playback Options")
        playback_frame.pack(fill="x", padx=10)

        ttk.Checkbutton(playback_frame, text="Loop", variable=self.loop_enabled)\
            .grid(row=0, column=0, padx=5)

        ttk.Label(playback_frame, text="Loops (0 = ∞):").grid(row=0, column=1)
        ttk.Spinbox(playback_frame, from_=0, to=999, textvariable=self.loop_count, width=5)\
            .grid(row=0, column=2)

        ttk.Label(playback_frame, text="Speed:").grid(row=1, column=0, pady=5)
        ttk.Scale(playback_frame, from_=0.5, to=2.0,
                  variable=self.playback_speed, orient="horizontal")\
            .grid(row=1, column=1, columnspan=2, sticky="we")

        # Event list
        self.tree = ttk.Treeview(self.root, columns=("Time", "Event"), show="headings", height=8)
        self.tree.heading("Time", text="Time")
        self.tree.heading("Event", text="Action")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------- Hotkeys ---------------- #

    def start_hotkey_listener(self):
        self.hotkey_listener = keyboard.GlobalHotKeys({
            f'<{self.record_hotkey.get()}>': self.toggle_recording,
            f'<{self.play_hotkey.get()}>': self.start_playback,
            f'<{self.stop_hotkey.get()}>': self.stop_all,
            f'<{self.speed_up_hotkey.get()}>': self.speed_up,
            f'<{self.speed_down_hotkey.get()}>': self.speed_down
        })
        self.hotkey_listener.start()

    def restart_hotkeys(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.start_hotkey_listener()
        self.status_var.set("Hotkeys updated")

    # ---------------- Recording ---------------- #

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_playing:
            return
        self.events.clear()
        self.tree.delete(*self.tree.get_children())
        self.is_recording = True
        self.start_time = time.time()
        self.status_var.set("Recording...")

        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll)
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)

        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_recording(self):
        self.is_recording = False
        self.status_var.set(f"Recorded {len(self.events)} events")
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    # ---------------- Event Capture ---------------- #

    def on_move(self, x, y):
        if self.is_recording:
            self.events.append({'type': 'move', 'time': time.time() - self.start_time, 'x': x, 'y': y})

    def on_click(self, x, y, button, pressed):
        if self.is_recording:
            dt = time.time() - self.start_time
            self.events.append({'type': 'click', 'time': dt, 'x': x, 'y': y,
                                'button': button, 'pressed': pressed})
            self.tree.insert("", "end", values=(f"{dt:.2f}", "Click"))

    def on_scroll(self, x, y, dx, dy):
        if self.is_recording:
            self.events.append({'type': 'scroll', 'time': time.time() - self.start_time,
                                'dx': dx, 'dy': dy})

    def on_press(self, key):
        if self.is_recording:
            self.events.append({'type': 'press', 'time': time.time() - self.start_time, 'key': key})

    def on_release(self, key):
        if self.is_recording:
            self.events.append({'type': 'release', 'time': time.time() - self.start_time, 'key': key})

    # ---------------- Playback ---------------- #

    def start_playback(self):
        if not self.events or self.is_playing:
            return
        self.is_playing = True
        threading.Thread(target=self.playback_loop, daemon=True).start()

    def playback_loop(self):
        loops = self.loop_count.get()
        speed = self.playback_speed.get()
        current_loop = 0

        while self.is_playing:
            start = time.time()
            for e in self.events:
                if not self.is_playing:
                    break

                target = start + (e['time'] / speed)
                time.sleep(max(0, target - time.time()))

                if e['type'] == 'move':
                    self.mouse_controller.position = (e['x'], e['y'])
                elif e['type'] == 'click':
                    self.mouse_controller.press(e['button']) if e['pressed'] else self.mouse_controller.release(e['button'])
                elif e['type'] == 'scroll':
                    self.mouse_controller.scroll(e['dx'], e['dy'])
                elif e['type'] == 'press':
                    self.keyboard_controller.press(e['key'])
                elif e['type'] == 'release':
                    self.keyboard_controller.release(e['key'])

            current_loop += 1
            if not self.loop_enabled.get():
                break
            if loops != 0 and current_loop >= loops:
                break

        self.is_playing = False
        self.status_var.set("Playback finished")

    # ---------------- Stop & Speed ---------------- #

    def stop_all(self):
        self.is_playing = False
        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.status_var.set("Stopped")

    def speed_up(self):
        self.playback_speed.set(min(2.0, self.playback_speed.get() + 0.1))
        self.status_var.set(f"Speed: {self.playback_speed.get():.1f}x")

    def speed_down(self):
        self.playback_speed.set(max(0.5, self.playback_speed.get() - 0.1))
        self.status_var.set(f"Speed: {self.playback_speed.get():.1f}x")

# ---------------- Run ---------------- #
if __name__ == "__main__":
    root = tk.Tk()
    app = MacroRecorder(root)
    root.mainloop()
