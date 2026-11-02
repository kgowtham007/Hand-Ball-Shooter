import cv2
import math
import random
import time
import tkinter as tk
from PIL import Image, ImageTk
from cvzone.HandTrackingModule import HandDetector

class FruitShooterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hand Tracking Fruit Shooter")
        self.width = 800
        self.height = 600
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.resizable(False, False)

        # High Scores Storage (Capped at Top 5)
        self.high_scores = [("Gowtham", 230), ("Sandeep", 240), ("Charan", 220)]
        
        # Complete Match History Storage [(Name, Score, TimeStr), ...]
        self.game_history = []
        self.current_player = "Guest"

        # Game State Variables
        self.score = 0
        self.time_left = 60
        self.game_running = False
        self.fruits = []
        self.history_panel_open = False

        # Setup Camera & Vision Engine
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, self.width)
        self.cap.set(4, self.height)
        self.detector = HandDetector(detectionCon=0.8, maxHands=1)

        # Container frame for switching screens
        self.container = tk.Frame(self.root, width=self.width, height=self.height)
        self.container.pack(fill="both", expand=True)

        # Handle window close safely
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Start on Login/Home Screen
        self.show_login_screen()

    # ==================== 1. LOGIN / HOME SCREEN ====================
    def show_login_screen(self):
        self.clear_container()
        self.history_panel_open = False

        # Canvas for background image & UI elements
        self.login_canvas = tk.Canvas(self.container, width=self.width, height=self.height, bg="#1a1a1a", highlightthickness=0)
        self.login_canvas.pack(fill="both", expand=True)

        # -------------------------------------------------------------
        # IMAGE COMMENT 1: LOGIN PAGE BACKGROUND
        # Save your login image as "login_bg.png" in the same project folder,
        # then uncomment the 3 lines below:
        # -------------------------------------------------------------
        self.login_bg_raw = Image.open("login_bg.jpg").resize((self.width, self.height))
        self.login_bg_img = ImageTk.PhotoImage(self.login_bg_raw)
        self.login_canvas.create_image(0, 0, image=self.login_bg_img, anchor=tk.NW)

        # Title
        self.login_canvas.create_text(400, 50, text="BALL SHOOTER", fill="#122806", font=("Georgia", 32, "bold"))

        # High Score Board (Top 5 Max)
        self.login_canvas.create_text(400, 110, text="--- TOP 5 HIGH SCORES ---", fill="yellow", font=("Arial", 15, "bold"))
        sorted_scores = sorted(self.high_scores, key=lambda x: x[1], reverse=True)[:5]
        
        y_pos = 140
        for idx, (name, sc) in enumerate(sorted_scores, 1):
            self.login_canvas.create_text(400, y_pos, text=f"{idx}. {name} - {sc} pts", fill="white", font=("Arial", 13, "bold"))
            y_pos += 22

        # Guest / Name Input Entry
        self.login_canvas.create_text(400, 275, text="Enter Player Name:", fill="white", font=("Arial", 13, "bold"))
        self.name_entry = tk.Entry(self.root, font=("Arial", 13), justify="center")
        self.login_canvas.create_window(400, 305, window=self.name_entry, width=220, height=32)
        self.name_entry.insert(0, "")

# Instructions Header (Black & Bold)
        self.login_canvas.create_text(
            400, 360, 
            text="--- HOW TO PLAY ---", 
            fill="#000000", 
            font=("Helvetica", 14, "bold"), 
            justify="center"
        )

        # Instructions Body (White & Normal)
        instructions_text = (
            "1. Move your index finger in front of webcam to position crosshair.\n"
            "2. Pinch Index + Thumb together to SHOOT falling targets.\n"
            "3. Green Ball (Large) = 10 Pts | Yellow (Medium) = 20 Pts | Red (Small) = 30 Pts\n"
            "4. Score as high as you can within 60 seconds!"
        )
        self.login_canvas.create_text(
            400, 415, 
            text=instructions_text, 
            fill="#FFFFFF", 
            font=("Helvetica", 13), 
            justify="center"
        )

        # Start Game Button
        btn_start = tk.Button(self.root, text="BEGIN GAME", font=("Arial", 13, "bold"), bg="#28a745", fg="white",
                              activebackground="#218838", cursor="hand2", command=self.prepare_game_start)
        self.login_canvas.create_window(400, 485, window=btn_start, width=170, height=42)

        # Side Menu Button: Game History Toggle
        btn_history = tk.Button(self.root, text="📋 Recent Plays", font=("Arial", 10, "bold"), bg="#17a2b8", fg="white",
                                cursor="hand2", command=self.toggle_history_panel)
        self.login_canvas.create_window(80, 30, window=btn_history, width=130, height=32)

        # Bind Enter Key to Start Game
        self.name_entry.bind("<Return>", lambda event: self.prepare_game_start())

    def toggle_history_panel(self):
        """Toggles the side drawer panel to display past games history."""
        if self.history_panel_open:
            # Close Panel
            self.login_canvas.delete("history_panel")
            self.history_panel_open = False
        else:
            # Open Side Panel
            self.history_panel_open = True
            
            # Draw Panel Background Box
            self.login_canvas.create_rectangle(10, 60, 260, 450, fill="#0d1117", outline="#17a2b8", width=2, tags="history_panel")
            self.login_canvas.create_text(135, 85, text="GAME HISTORY", fill="#17a2b8", font=("Arial", 13, "bold"), tags="history_panel")
            
            if not self.game_history:
                self.login_canvas.create_text(135, 130, text="No matches played yet!", fill="gray", font=("Arial", 10, "italic"), tags="history_panel")
            else:
                y_pos = 120
                # Show last 10 games played
                for name, sc, played_at in reversed(self.game_history[-10:]):
                    entry_str = f"• {name}: {sc} pts\n  ({played_at})"
                    self.login_canvas.create_text(25, y_pos, text=entry_str, fill="white", font=("Arial", 9), anchor="w", tags="history_panel")
                    y_pos += 32

    def prepare_game_start(self):
        player_name = self.name_entry.get().strip()
        self.current_player = player_name if player_name else "Guest"
        self.show_game_screen()

    # ==================== 2. GAMEPLAY SCREEN ====================
    def show_game_screen(self):
        self.clear_container()
        self.score = 0
        self.time_left = 60
        self.fruits = []
        self.game_running = False

        # Canvas for Game Engine
        self.game_canvas = tk.Canvas(self.container, width=self.width, height=self.height, bg="black", highlightthickness=0)
        self.game_canvas.pack(fill="both", expand=True)

        # -------------------------------------------------------------
        # IMAGE COMMENT 2: GAMEPLAY BACKGROUND
        # Save your gameplay background as "game_bg.png" in the project folder,
        # then uncomment the 3 lines below:
        # -------------------------------------------------------------
        self.game_bg_raw = Image.open("game_bg.png").resize((self.width, self.height))
        self.game_bg_img = ImageTk.PhotoImage(self.game_bg_raw)
        self.game_canvas.create_image(0, 0, image=self.game_bg_img, anchor=tk.NW)

        # UI Text Displays
        self.score_display = self.game_canvas.create_text(100, 35, text=f"Score: 0", fill="white", font=("Arial", 18, "bold"), anchor="w")
        self.player_display = self.game_canvas.create_text(400, 35, text=f"Player: {self.current_player}", fill="#00FFC8", font=("Arial", 16, "bold"))
        self.timer_display = self.game_canvas.create_text(700, 35, text=f"Time: 60s", fill="yellow", font=("Arial", 18, "bold"), anchor="e")

        # Exit to Home Button (Clickable via Mouse)
        btn_exit = tk.Button(self.root, text="Exit to Home", font=("Arial", 10, "bold"), bg="#dc3545", fg="white",
                             cursor="hand2", command=self.exit_to_home)
        self.game_canvas.create_window(720, 560, window=btn_exit, width=110, height=35)

        # Shooter Crosshair Reticle (Combining multiple lines & circle into a list of IDs)
        self.reticle_parts = {
            "circle": self.game_canvas.create_oval(0, 0, 0, 0, outline="#00FFC8", width=2),
            "dot": self.game_canvas.create_oval(0, 0, 0, 0, fill="#00FFC8", outline="#00FFC8"),
            "top": self.game_canvas.create_line(0, 0, 0, 0, fill="#00FFC8", width=2),
            "bottom": self.game_canvas.create_line(0, 0, 0, 0, fill="#00FFC8", width=2),
            "left": self.game_canvas.create_line(0, 0, 0, 0, fill="#00FFC8", width=2),
            "right": self.game_canvas.create_line(0, 0, 0, 0, fill="#00FFC8", width=2),
        }
        self.can_shoot = True

        # Countdown Text Overlay
        self.countdown_text = self.game_canvas.create_text(400, 300, text="", fill="gold", font=("Arial", 72, "bold"))

        # Start 3-Second Countdown sequence
        self.run_countdown(3)

    def run_countdown(self, count):
        if count > 0:
            self.game_canvas.itemconfig(self.countdown_text, text=str(count))
            self.root.after(1000, self.run_countdown, count - 1)
        else:
            self.game_canvas.itemconfig(self.countdown_text, text="GO!")
            self.root.after(600, lambda: self.game_canvas.itemconfig(self.countdown_text, text=""))
            
            # Start game loops
            self.game_running = True
            self.spawn_fruit()
            self.update_game_loop()
            self.update_timer_loop()

    def update_timer_loop(self):
        if not self.game_running:
            return
            
        if self.time_left > 0:
            self.time_left -= 1
            self.game_canvas.itemconfig(self.timer_display, text=f"Time: {self.time_left}s")
            self.root.after(1000, self.update_timer_loop)
        else:
            self.end_game()

    # ==================== 3. BALL SPAWNING & PHYSICS ====================
    def spawn_fruit(self):
        if not self.game_running:
            return

        x = random.randint(100, self.width - 100)
        y = self.height
        vx = random.choice([-3, -2, 2, 3])
        vy = random.randint(-22, -16)

        # Three distinct types: Green (10pt), Yellow (20pt), Red (30pt)
        ball_types = [
            {"color": "green", "radius": 40, "points": 10},
            {"color": "yellow", "radius": 28, "points": 20},
            {"color": "red", "radius": 18, "points": 30}
        ]
        
        chosen = random.choices(ball_types, weights=[50, 35, 15], k=1)[0]
        
        oval_id = self.game_canvas.create_oval(x - chosen["radius"], y - chosen["radius"],
                                               x + chosen["radius"], y + chosen["radius"],
                                               fill=chosen["color"], outline="white", width=2)

        self.fruits.append({
            "id": oval_id,
            "x": x, "y": y,
            "vx": vx, "vy": vy,
            "radius": chosen["radius"],
            "points": chosen["points"]
        })

        self.root.after(random.randint(1000, 2000), self.spawn_fruit)

    def update_game_loop(self):
        if not self.game_running:
            return

        success, img = self.cap.read()
        if success:
            img = cv2.flip(img, 1)
            hands, img = self.detector.findHands(img, draw=False)

            if hands:
                hand = hands[0]
                lmList = hand["lmList"]
                
                # Index Tip [8] coordinates mapped to camera
                ix, iy = lmList[8][0], lmList[8][1]
                
                # Crosshair Dimensions
                r = 18       # Radius of outer circle
                gap = 5      # Distance from center to start of crosshair ticks
                length = 10  # Length of crosshair ticks
                
                # Update outer target circle
                self.game_canvas.coords(self.reticle_parts["circle"], ix - r, iy - r, ix + r, iy + r)
                
                # Update center target dot (3px radius)
                self.game_canvas.coords(self.reticle_parts["dot"], ix - 2, iy - 2, ix + 2, iy + 2)
                
                # Update the crosshair lines (top, bottom, left, right)
                self.game_canvas.coords(self.reticle_parts["top"], ix, iy - gap - length, ix, iy - gap)
                self.game_canvas.coords(self.reticle_parts["bottom"], ix, iy + gap, ix, iy + gap + length)
                self.game_canvas.coords(self.reticle_parts["left"], ix - gap - length, iy, ix - gap, iy)
                self.game_canvas.coords(self.reticle_parts["right"], ix + gap, iy, ix + gap + length, iy)

                # Thumb Tip [4] for Pinch detection
                tx, ty = lmList[4][0], lmList[4][1]
                dist = math.hypot(ix - tx, iy - ty)

                if dist < 30 and self.can_shoot:
                    self.shoot(ix, iy)
                    self.can_shoot = False
                elif dist >= 30:
                    self.can_shoot = True

        # Update Target Positions & Physics
        gravity = 0.6
        for fruit in self.fruits[:]:
            fruit["x"] += fruit["vx"]
            fruit["y"] += fruit["vy"]
            fruit["vy"] += gravity

            r = fruit["radius"]
            self.game_canvas.coords(fruit["id"], fruit["x"] - r, fruit["y"] - r, fruit["x"] + r, fruit["y"] + r)

            if fruit["y"] > self.height + 60:
                self.game_canvas.delete(fruit["id"])
                self.fruits.remove(fruit)

        self.root.after(30, self.update_game_loop)

    def shoot(self, shot_x, shot_y):
        for fruit in self.fruits[:]:
            dist = math.hypot(shot_x - fruit["x"], shot_y - fruit["y"])
            if dist <= fruit["radius"]:
                self.game_canvas.delete(fruit["id"])
                self.fruits.remove(fruit)
                self.score += fruit["points"]
                self.game_canvas.itemconfig(self.score_display, text=f"Score: {self.score}")
                break

    # ==================== 4. GAME OVER & EXIT HANDLERS ====================
    def end_game(self):
        self.game_running = False
        
        # Save to High Scores & Match History
        self.high_scores.append((self.current_player, self.score))
        timestamp = time.strftime("%I:%M %p")
        self.game_history.append((self.current_player, self.score, timestamp))

        # Sort and maintain Top 5 High Scores
        self.high_scores = sorted(self.high_scores, key=lambda x: x[1], reverse=True)[:5]

        # Show Game Over Modal
        self.game_canvas.create_rectangle(150, 180, 650, 420, fill="#111111", outline="gold", width=3)
        self.game_canvas.create_text(400, 230, text="TIME'S UP!", fill="red", font=("Arial", 32, "bold"))
        self.game_canvas.create_text(400, 290, text=f"{self.current_player}, your Final Score: {self.score}", fill="white", font=("Arial", 18))

        btn_finish = tk.Button(self.root, text="Back to Main Menu", font=("Arial", 12, "bold"), bg="#007bff", fg="white",
                               cursor="hand2", command=self.show_login_screen)
        self.game_canvas.create_window(400, 360, window=btn_finish, width=180, height=40)

    def exit_to_home(self):
        self.game_running = False
        self.show_login_screen()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def quit_app(self):
        self.game_running = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FruitShooterApp(root)
    root.mainloop()