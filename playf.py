import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import time
import os
import sys

# Determine correct base path for BOTH normal Python AND PyInstaller EXE
if getattr(sys, 'frozen', False):
    # Running as EXE (PyInstaller single-file)
    BASE_PATH = sys._MEIPASS
else:
    # Running as .py script
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Path to your data folder
DATA_PATH = os.path.join(BASE_PATH, "data")

# Import solver after BASE_PATH/DATA_PATH is defined (no dependency, but keep ordering predictable)
from sokoban_solverf import (
    parse_level,
    astar_push_move_optimal_improved,
    DIR_MAP,
)

# Asset filenames resolved using DATA_PATH
PLAYER_PNG = os.path.join(DATA_PATH, "retro_player.png")
BOX_PNG = os.path.join(DATA_PATH, "retro_box.png")
BOX_GOAL_PNG = os.path.join(DATA_PATH, "retro_box_on_goal.png")
WALL_PNG = os.path.join(DATA_PATH, "retro_wall.png")
TARGET_PNG = os.path.join(DATA_PATH, "retro_target.png")

CELL = 64

def animate_move(canvas, item, dx, dy, steps=8, delay=0.01):
    for _ in range(steps):
        canvas.move(item, dx / steps, dy / steps)
        canvas.update()
        time.sleep(delay)


class SokobanGUI:
    def __init__(self, root, levels):
        self.root = root
        self.levels = levels
        self.current_level_index = 0

        root.title("Sokoban — Retro Pixel Edition")
        root.configure(bg="#111111")
        root.bind("<Key>", self.on_key)

        # Load textures (ImageTk.PhotoImage) using the resolved paths
        try:
            self.tex_player = ImageTk.PhotoImage(Image.open(PLAYER_PNG).resize((CELL, CELL), Image.NEAREST))
            self.tex_box = ImageTk.PhotoImage(Image.open(BOX_PNG).resize((CELL, CELL), Image.NEAREST))
            self.tex_box_goal = ImageTk.PhotoImage(Image.open(BOX_GOAL_PNG).resize((CELL, CELL), Image.NEAREST))
            self.tex_wall = ImageTk.PhotoImage(Image.open(WALL_PNG).resize((CELL, CELL), Image.NEAREST))
            self.tex_target = ImageTk.PhotoImage(Image.open(TARGET_PNG).resize((CELL, CELL), Image.NEAREST))
        except Exception as e:
            messagebox.showerror("Asset Load Error", f"Failed to load one or more image assets.\n\n{e}")
            raise

        self.side = tk.Frame(root, bg="#fac800", padx=10, pady=10)
        self.side.grid(row=0, column=0, sticky="ns")

        self.main = tk.Frame(root, bg="white")
        self.main.grid(row=0, column=1, padx=30, pady=30)

        tk.Label(self.side, text="Levels", font=("Consolas", 14, "bold"), bg="#fac800").pack(pady=4)

        self.level_list = tk.Listbox(self.side, width=18, height=10, font=("Consolas", 12))
        self.level_list.pack(pady=4)
        for i in range(len(levels)):
            self.level_list.insert(tk.END, f"Level {i+1}")
        self.level_list.bind("<<ListboxSelect>>", self.on_level_select)

        ttk.Button(self.side, text="Load", command=self.load_selected_level).pack(pady=6)
        ttk.Button(self.side, text="Solve", command=self.solve).pack(pady=6)
        ttk.Button(self.side, text="Step", command=self.step).pack(pady=6)
        ttk.Button(self.side, text="Auto", command=self.auto_play).pack(pady=6)
        ttk.Button(self.side, text="Reset", command=self.reset_level).pack(pady=6)

        arrow_frame = tk.Frame(self.side, bg="#fac800")
        arrow_frame.pack(pady=8)
        ttk.Button(arrow_frame, text="↑", width=4, command=lambda: self.try_move("U")).grid(row=0, column=1)
        ttk.Button(arrow_frame, text="←", width=4, command=lambda: self.try_move("L")).grid(row=1, column=0)
        ttk.Button(arrow_frame, text="→", width=4, command=lambda: self.try_move("R")).grid(row=1, column=2)
        ttk.Button(arrow_frame, text="↓", width=4, command=lambda: self.try_move("D")).grid(row=2, column=1)

        ttk.Button(self.side, text="Undo", command=self.undo).pack(pady=6)

        self.move_label = tk.Label(self.side, text="Moves: 0/0", bg="#fac800", font=("Consolas", 12))
        self.move_label.pack(pady=8)

        self.canvas = None

        self.wall_items = {}
        self.target_items = {}
        self.box_items = {}
        self.player_item = None

        self.move_history = []
        self.moves = []
        self.move_index = 0

        self.load_level(0)

    def on_key(self, event):
        key = event.keysym.lower()
        km = {"up": "U", "w": "U", "down": "D", "s": "D", "left": "L", "a": "L", "right": "R", "d": "R"}
        if key in km:
            self.try_move(km[key])
        elif key == "z" and (event.state & 0x4):
            self.undo()

    def on_level_select(self, event):
        sel = self.level_list.curselection()
        if sel:
            self.load_level(sel[0])

    def load_selected_level(self):
        sel = self.level_list.curselection()
        if sel:
            self.load_level(sel[0])

    def load_level(self, index):
        self.current_level_index = index
        lines = self.levels[index]
        walls, goals, boxes, player = parse_level(lines)

        self.walls = set(walls)
        self.goals = set(goals)
        self.boxes = set(boxes)
        self.player = player

        self.rows = len(lines)
        self.cols = max(len(r) for r in lines)

        if self.canvas:
            self.canvas.destroy()

        self.canvas = tk.Canvas(self.main, width=self.cols * CELL, height=self.rows * CELL,
                                bg="#222222", highlightthickness=0)
        self.canvas.pack()

        self.wall_items.clear()
        self.target_items.clear()
        self.box_items.clear()

        self.move_history = []
        self.moves = []
        self.move_index = 0

        self.draw_level()
        self.update_moves_label()

    def draw_level(self):
        self.canvas.delete("all")
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c * CELL, r * CELL
                self.canvas.create_rectangle(x, y, x + CELL, y + CELL, fill="#eaeaea", outline="#bdbdbd")

        for (r, c) in self.walls:
            x, y = c * CELL, r * CELL
            self.wall_items[(r, c)] = self.canvas.create_image(x, y, anchor="nw", image=self.tex_wall)

        for (r, c) in self.goals:
            x, y = c * CELL, r * CELL
            self.target_items[(r, c)] = self.canvas.create_image(x, y, anchor="nw", image=self.tex_target)

        for (r, c) in self.boxes:
            x, y = c * CELL, r * CELL
            img = self.tex_box_goal if (r, c) in self.goals else self.tex_box
            self.box_items[(r, c)] = self.canvas.create_image(x, y, anchor="nw", image=img)

        pr, pc = self.player
        self.player_item = self.canvas.create_image(pc * CELL, pr * CELL, anchor="nw", image=self.tex_player)

        self.check_win()

    def try_move(self, mv):
        dr, dc = DIR_MAP[mv]
        pr, pc = self.player
        nr, nc = pr + dr, pc + dc
        dest = (nr, nc)

        if dest in self.walls:
            return

        pushing_box = dest in self.boxes
        self.move_history.append((self.player, set(self.boxes)))

        if pushing_box:
            br, bc = nr + dr, nc + dc
            box_dest = (br, bc)
            if box_dest in self.walls or box_dest in self.boxes:
                self.move_history.pop()
                return

            box_id = self.box_items.pop(dest)
            animate_move(self.canvas, box_id, dc * CELL, dr * CELL)
            self.boxes.remove(dest)
            self.boxes.add(box_dest)
            new_img = self.tex_box_goal if box_dest in self.goals else self.tex_box
            self.canvas.itemconfig(box_id, image=new_img)
            self.box_items[box_dest] = box_id

        animate_move(self.canvas, self.player_item, dc * CELL, dr * CELL)
        self.player = dest

        self.move_index += 1  # correct for manual play
        self.update_moves_label()
        self.check_win()

    def apply(self, mv):
        dr, dc = DIR_MAP[mv]
        pr, pc = self.player
        nr, nc = pr + dr, pc + dc
        dest = (nr, nc)

        self.move_history.append((self.player, set(self.boxes)))

        if dest in self.boxes:
            br, bc = nr + dr, nc + dc
            box_id = self.box_items.pop(dest)
            animate_move(self.canvas, box_id, dc * CELL, dr * CELL)
            self.boxes.remove(dest)
            self.boxes.add((br, bc))
            new_img = self.tex_box_goal if (br, bc) in self.goals else self.tex_box
            self.canvas.itemconfig(box_id, image=new_img)
            self.box_items[(br, bc)] = box_id

        animate_move(self.canvas, self.player_item, dc * CELL, dr * CELL)
        self.player = dest

        self.move_index += 1  # solver move count
        self.check_win()

    def undo(self):
        if not self.move_history:
            return

        prev_player, prev_boxes = self.move_history.pop()
        self.player = prev_player
        self.boxes = set(prev_boxes)

        self.draw_level()

        if self.move_index > 0:
            self.move_index -= 1

        self.update_moves_label()

    def solve(self):
        res = astar_push_move_optimal_improved(
            self.walls,
            self.goals,
            frozenset(self.boxes),
            self.player,
            max_expansions=2_000_000
        )

        if res is None:
            messagebox.showerror("Solver", "No solution found (or exceeded max expansions).")
            return

        self.moves = res["moves"]
        self.move_index = 0
        messagebox.showinfo("Solver", f"Solution loaded — {len(self.moves)} moves.")
        self.update_moves_label()

    def step(self):
        if not hasattr(self, "moves") or self.move_index >= len(self.moves):
            return

        mv = self.moves[self.move_index]
        self.apply(mv)
        self.update_moves_label()

    def auto_play(self):
        if not hasattr(self, "moves"):
            return
        if self.move_index < len(self.moves):
            self.step()
            self.canvas.after(120, self.auto_play)

    def check_win(self):
        if all(box in self.goals for box in self.boxes):
            messagebox.showinfo("Level Complete", f"Solved in {self.move_index} moves!")
            return True
        return False

    def update_moves_label(self):
        total = len(self.moves) if hasattr(self, "moves") else 0
        self.move_label.config(text=f"Moves: {self.move_index}/{total}")

    def reset_level(self):
        self.load_level(self.current_level_index)


LEVELS = [
    [
        "#######",
        "#  .  #",
        "#   #$#",
        "# @ $ #",
        "#    .#",
        "#######"
    ],

    [
        "########",
        "# .   .#",
        "#   $$ #",
        "#  @   #",
        "#      #",
        "########"
    ],

    [
        "#########",
        "#   .   #",
        "# $ # $ #",
        "#   @ . #",
        "# $ # $ #",
        "#   . . #",
        "#########"
    ],

    [
        "###########",
        "#    .    #",
        "#  $ #  $ #",
        "#   ###   #",
        "#  @      #",
        "#    .    #",
        "###########"
    ],

    [
        "###########",
        "# .     . #",
        "#   ###   #",
        "# $  #    #",
        "### ## #  #",
        "# @  # $  #",
        "#         #",
        "###########"
    ],
]

if __name__ == "__main__":
    required_assets = [PLAYER_PNG, BOX_PNG, BOX_GOAL_PNG, WALL_PNG, TARGET_PNG]
    missing = [p for p in required_assets if not os.path.exists(p)]
    if missing:
        names = "\n".join(missing)
        raise FileNotFoundError(f"Required asset(s) not found. Expected at:\n{names}")

    root = tk.Tk()
    gui = SokobanGUI(root, LEVELS)

    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()
