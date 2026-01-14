# Sokoban AI Solver

**Team Members:** Purva Jivani, Laxman Patel, Tanishq Gupta, Harshal Singh  

This project implements an **AI solver for Sokoban**, a puzzle game where the player pushes boxes to target locations. The solver finds **optimal sequences of moves** to push all boxes to goals without getting stuck. It also includes a **Tkinter-based GUI** for interactive gameplay and solution visualization.

---

## Features

### Backend
- Written in **Python** using `heapq` (priority queues) and `deque` (BFS).  
- Parses levels into:  
  - Walls: `#`  
  - Goals: `.`  
  - Boxes: `$`  
  - Player: `@`  
  - Combined states: `*` (box on goal), `+` (player on goal)  

### Deadlock Detection
- **Corner Deadlock:** Box stuck in a corner not on a goal.  
- **Linear Deadlock:** Box trapped along a wall without a goal in line.  
- **2x2 Deadlock (optional):** Multiple boxes trapped in a 2×2 square.  
- **Two-Box Freeze:** Two boxes blocking each other along walls without goals.  

### Heuristic & Pathfinding
- **Player Pathfinding:** BFS used to reach positions necessary for pushing boxes.  
- **Heuristic Function:**  
  - Hungarian Algorithm: Minimum total Manhattan distance between boxes and goals.  
  - Fallback: Sum of nearest Manhattan distances if Hungarian fails.  

### A* Search Algorithm
- **State Representation:** `(boxes_positions, player_position)`  
- **Cost:** `g(n)` = number of moves so far  
- **Heuristic:** `h(n)` = Hungarian distance  
- **Priority:** `f(n) = g(n) + h(n)`  
- Expands nodes while avoiding deadlocks  
- Caches BFS paths for efficiency  
- Tracks `came_from` to reconstruct move sequences  

### Frontend (Tkinter GUI)
- Interactive interface for playing Sokoban  
- Level selection, loading, and reset support  
- Manual moves via arrow keys/buttons, undo, step-by-step solver, and auto-play  
- PNG-based graphics: `PLAYER_PNG`, `BOX_PNG`, `BOX_GOAL_PNG`, `WALL_PNG`, `TARGET_PNG`  
- Smooth animations with move interpolation  
- Move tracking and completion pop-up  

---

## Results
- Solver outputs **number of expansions**, **total moves**, and **full move sequence**.  
- Efficiently handles moderately complex levels using optimized heuristics.  

---

## Conclusion
The Sokoban solver combines **A\* search**, **BFS**, and the **Hungarian heuristic** for optimal or near-optimal solutions. Deadlock detection (corner, linear, 2×2, two-box freeze) prunes unsolvable states, ensuring efficiency and accuracy. The GUI allows interactive play, step-by-step solving, and visualization of solutions.

---

## Tech Stack
- **Backend:** Python, heapq, deque  
- **Frontend:** Tkinter  
- **Algorithms:** A*, BFS, Hungarian heuristic, deadlock detection  

---


   git clone <repository_url>
