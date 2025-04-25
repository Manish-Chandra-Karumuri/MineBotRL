import pyautogui
import keyboard
import win32gui
import win32con
import time

class MinecraftController:
    def __init__(self):
        self.key_mappings = {
            'forward': 'w',
            'backward': 's',
            'left': 'a',
            'right': 'd',
            'jump': 'space'
        }
        self.initial_mouse_pos = pyautogui.position()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def find_minecraft_window(self):
        def window_enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if any(name in title.lower() for name in ['minecraft', 'tlauncher']):
                    windows.append((hwnd, title))
            return True

        windows = []
        win32gui.EnumWindows(window_enum_callback, windows)
        return windows

    def focus_minecraft(self):
        try:
            windows = self.find_minecraft_window()
            if windows:
                hwnd, title = windows[0]
                print(f"Found Minecraft window: {title}")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            print(f"Error focusing Minecraft: {e}")
            return False

    def reset_controls(self):
        for key in self.key_mappings.values():
            keyboard.release(key)
        pyautogui.moveTo(self.initial_mouse_pos)

    def handle_movement(self, move_x, move_z):
        if move_x > 0.5:
            keyboard.press(self.key_mappings['forward'])
        elif move_x < -0.5:
            keyboard.press(self.key_mappings['backward'])
        else:
            keyboard.release(self.key_mappings['forward'])
            keyboard.release(self.key_mappings['backward'])

        if move_z > 0.5:
            keyboard.press(self.key_mappings['right'])
        elif move_z < -0.5:
            keyboard.press(self.key_mappings['left'])
        else:
            keyboard.release(self.key_mappings['left'])
            keyboard.release(self.key_mappings['right'])

    def handle_jump(self, jump):
        if jump > 0.5:
            keyboard.press(self.key_mappings['jump'])
        else:
            keyboard.release(self.key_mappings['jump'])

    def handle_looking(self, look_yaw, look_pitch):
        mouse_move_x = int(look_yaw * 2)
        mouse_move_y = int(look_pitch * 2)
        pyautogui.moveRel(mouse_move_x, mouse_move_y) 