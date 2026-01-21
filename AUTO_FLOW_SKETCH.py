import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import mouse, keyboard

class MacroRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Mouse Clone")
        self.root.geometry("400x300")
        
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        self.events = []
        self.start_time = 0
        self.is_recording = False
        self.is_playing = False
        
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # UI Setup
        self.create_widgets()
        
    def create_widgets(self):
        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.pack(pady=20)
        
        # Buttons Frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        self.record_btn = ttk.Button(btn_frame, text="Record (F8)", command=self.toggle_recording)
        self.record_btn.grid(row=0, column=0, padx=10)
        
        self.play_btn = ttk.Button(btn_frame, text="Play (F9)", command=self.start_playback)
        self.play_btn.grid(row=0, column=1, padx=10)
        
        # Event List (Preview)
        self.tree = ttk.Treeview(self.root, columns=("Time", "Event"), show="headings", height=8)
        self.tree.heading("Time", text="Time (s)")
        self.tree.heading("Event", text="Action")
        self.tree.column("Time", width=80)
        self.tree.column("Event", width=280)
        self.tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Global Hotkeys listener (non-blocking)
        # We need a separate listener for hotkeys that works even when app is focused/unfocused
        # But for simplicity in this clone, we might rely on the buttons or a background listener
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<f8>': self.toggle_recording,
            '<f9>': self.start_playback
        })
        self.hotkey_listener.start()

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_playing:
            return
            
        self.events = []
        self.tree.delete(*self.tree.get_children())
        self.is_recording = True
        self.status_var.set("Recording... (Press F8 to Stop)")
        self.record_btn.config(text="Stop (F8)")
        self.play_btn.config(state=tk.DISABLED)
        
        self.start_time = time.time()
        
        # Start Listeners
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
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.status_var.set(f"Recorded {len(self.events)} events")
        self.record_btn.config(text="Record (F8)")
        self.play_btn.config(state=tk.NORMAL)
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def on_move(self, x, y):
        if self.is_recording:
            dt = time.time() - self.start_time
            self.events.append({'type': 'move', 'time': dt, 'x': x, 'y': y})

    def on_click(self, x, y, button, pressed):
        if self.is_recording:
            dt = time.time() - self.start_time
            self.events.append({'type': 'click', 'time': dt, 'x': x, 'y': y, 'button': button, 'pressed': pressed})
            self.update_tree_view('Click', dt)

    def on_scroll(self, x, y, dx, dy):
        if self.is_recording:
            dt = time.time() - self.start_time
            self.events.append({'type': 'scroll', 'time': dt, 'x': x, 'y': y, 'dx': dx, 'dy': dy})

    def on_press(self, key):
        if self.is_recording:
            # Avoid recording the stop hotkey itself if possible, or handle it gracefully
            if key == keyboard.Key.f8:
                return
            dt = time.time() - self.start_time
            self.events.append({'type': 'press', 'time': dt, 'key': key})
            self.update_tree_view(f'Press {key}', dt)

    def on_release(self, key):
        if self.is_recording:
            if key == keyboard.Key.f8:
                return
            dt = time.time() - self.start_time
            self.events.append({'type': 'release', 'time': dt, 'key': key})

    def update_tree_view(self, action, dt):
        # Update UI in main thread safely
        self.root.after(0, lambda: self.tree.insert("", "end", values=(f"{dt:.2f}", action)))

    def start_playback(self):
        if self.is_recording or self.is_playing or not self.events:
            return
            
        self.is_playing = True
        self.status_var.set("Playing...")
        self.play_btn.config(state=tk.DISABLED)
        self.record_btn.config(state=tk.DISABLED)
        
        # Run playback in separate thread
        threading.Thread(target=self._playback_loop, daemon=True).start()

    def _playback_loop(self):
        start_playback_time = time.time()
        
        for event in self.events:
            if not self.is_playing:
                break
                
            # Wait until it's time for this event
            target_time = start_playback_time + event['time']
            current_time = time.time()
            if target_time > current_time:
                time.sleep(target_time - current_time)
            
            # Execute event
            try:
                if event['type'] == 'move':
                    self.mouse_controller.position = (event['x'], event['y'])
                elif event['type'] == 'click':
                    if event['pressed']:
                        self.mouse_controller.press(event['button'])
                    else:
                        self.mouse_controller.release(event['button'])
                elif event['type'] == 'scroll':
                    self.mouse_controller.scroll(event['dx'], event['dy'])
                elif event['type'] == 'press':
                    self.keyboard_controller.press(event['key'])
                elif event['type'] == 'release':
                    self.keyboard_controller.release(event['key'])
            except Exception as e:
                print(f"Error executing event: {e}")

        self.is_playing = False
        self.root.after(0, self.finish_playback)

    def finish_playback(self):
        self.status_var.set("Playback Finished")
        self.play_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)

    def on_close(self):
        self.is_recording = False
        self.is_playing = False
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroRecorder(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
