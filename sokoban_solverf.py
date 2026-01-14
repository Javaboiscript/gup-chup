import heapq
from collections import deque
import time
import os
import sys

DIRS = [(-1, 0, "U"), (1, 0, "D"), (0, -1, "L"), (0, 1, "R")]
DIR_MAP = {d[2]: (d[0], d[1]) for d in DIRS}
INF = 10**9

ENABLE_STRONG_DEADLOCK = False
ENABLE_FREEZE_PATTERNS = True

def parse_level(lines):
    walls = set()
    goals = set()
    boxes = set()
    player = None
    for r, row in enumerate(lines):
        for c, ch in enumerate(row):
            pos = (r, c)
            if ch == '#':
                walls.add(pos)
            elif ch == '.':
                goals.add(pos)
            elif ch == '$':
                boxes.add(pos)
            elif ch == '@':
                player = pos
            elif ch == '*':
                boxes.add(pos); goals.add(pos)
            elif ch == '+':
                player = pos; goals.add(pos)
    return walls, goals, frozenset(boxes), player

def print_map(lines, walls, goals, boxes, player):
    rows = len(lines)
    cols = max(len(r) for r in lines) if lines else 0
    for r in range(rows):
        s = ""
        for c in range(cols):
            p = (r, c)
            if p in walls:
                s += "#"
            elif p == player:
                s += "@"
            elif p in boxes and p in goals:
                s += "*"
            elif p in boxes:
                s += "$"
            elif p in goals:
                s += "."
            else:
                s += " "
        print(s)

def compute_goal_distance_map(walls, goals):
    dist = {}
    q = deque()
    for g in goals:
        dist[g] = 0
        q.append(g)
    while q:
        r, c = q.popleft()
        for dr, dc, _ in DIRS:
            np = (r + dr, c + dc)
            if np in walls or np in dist:
                continue
            dist[np] = dist[(r, c)] + 1
            q.append(np)
    return dist

def is_corner_deadlock(cell, walls, goals):
    if cell in goals:
        return False
    r, c = cell
    up = (r - 1, c); down = (r + 1, c); left = (r, c - 1); right = (r, c + 1)
    return (up in walls or down in walls) and (left in walls or right in walls)

def is_linear_deadlock(cell, walls, goals):
    if cell in goals:
        return False
    r, c = cell
    if (r-1, c) in walls and (r+1, c) in walls:
        left = c
        while (r, left-1) not in walls:
            left -= 1
        right = c
        while (r, right+1) not in walls:
            right += 1
        for cc in range(left, right+1):
            if (r, cc) in goals:
                return False
        return True
    if (r, c-1) in walls and (r, c+1) in walls:
        up = r
        while (up-1, c) not in walls:
            up -= 1
        down = r
        while (down+1, c) not in walls:
            down += 1
        for rr in range(up, down+1):
            if (rr, c) in goals:
                return False
        return True
    return False

def is_2x2_deadlock(cell, walls, goals):
    r, c = cell
    blocks = [
        [(r, c), (r, c+1), (r+1, c), (r+1, c+1)],
        [(r-1, c), (r-1, c+1), (r, c), (r, c+1)],
        [(r, c-1), (r, c), (r+1, c-1), (r+1, c)],
        [(r-1, c-1), (r-1, c), (r, c-1), (r, c)],
    ]
    for blk in blocks:
        any_goal = any(cellp in goals for cellp in blk)
        if any_goal:
            continue
        wall_count = sum(1 for cellp in blk if cellp in walls)
        if wall_count >= 2:
            return True
    return False

def is_two_box_freeze(box_pos, boxes, walls, goals):
    r, c = box_pos
    for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
        nb = (r+dr, c+dc)
        if nb not in boxes:
            continue
        if box_pos in goals or nb in goals:
            return False
        r1,c1 = box_pos; r2,c2 = nb
        if (r1-1,c1) in walls and (r2-1,c2) in walls:
            if all((r1, x) not in goals for x in range(min(c1,c2)-1, max(c1,c2)+2)):
                return True
        if (r1+1,c1) in walls and (r2+1,c2) in walls:
            if all((r1, x) not in goals for x in range(min(c1,c2)-1, max(c1,c2)+2)):
                return True
        if (r1, c1-1) in walls and (r2, c2-1) in walls:
            if all((y, c1) not in goals for y in range(min(r1,r2)-1, max(r1,r2)+2)):
                return True
        if (r1, c1+1) in walls and (r2, c2+1) in walls:
            if all((y, c1) not in goals for y in range(min(r1,r2)-1, max(r1,r2)+2)):
                return True
    return False

def is_deadlock(cell, walls, goals, boxes=None):
    if is_corner_deadlock(cell, walls, goals):
        return True
    if is_linear_deadlock(cell, walls, goals):
        return True
    if ENABLE_STRONG_DEADLOCK and is_2x2_deadlock(cell, walls, goals):
        return True
    if ENABLE_FREEZE_PATTERNS and boxes is not None:
        if is_two_box_freeze(cell, set(boxes), walls, goals):
            return True
    return False

def bfs_player_path(start, goal, boxes, walls):
    if start == goal:
        return []
    blocked = set(walls) | set(boxes)
    q = deque([start])
    parent = {start: None}
    parent_move = {}
    while q:
        cur = q.popleft()
        for dr, dc, label in DIRS:
            np = (cur[0] + dr, cur[1] + dc)
            if np in blocked or np in parent:
                continue
            parent[np] = cur
            parent_move[np] = label
            if np == goal:
                path = []
                node = np
                while parent[node] is not None:
                    path.append(parent_move[node])
                    node = parent[node]
                path.reverse()
                return path
            q.append(np)
    return None

def hungarian_min_cost(boxes, goals, goal_dist_map):
    boxes = list(boxes)
    goals = list(goals)
    n = max(len(boxes), len(goals))
    if n == 0:
        return 0
    cost = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i < len(boxes) and j < len(goals):
                bx = boxes[i]; gx = goals[j]
                cost[i][j] = abs(bx[0]-gx[0]) + abs(bx[1]-gx[1])
            else:
                cost[i][j] = 0
    u = [0]*(n+1)
    v = [0]*(n+1)
    p = [0]*(n+1)
    way = [0]*(n+1)
    for i in range(1, n+1):
        p[0] = i
        j0 = 0
        minv = [INF]*(n+1)
        used = [False]*(n+1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = 0
            for j in range(1, n+1):
                if used[j]:
                    continue
                cur = cost[i0-1][j-1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(0, n+1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1]*n
    for j in range(1, n+1):
        if p[j] > 0 and p[j]-1 < len(boxes) and j-1 < len(goals):
            assignment[p[j]-1] = j-1
    total_cost = 0
    for i in range(len(boxes)):
        j = assignment[i]
        if j is None or j == -1:
            if goals:
                bx = boxes[i]
                best = min(abs(bx[0]-g[0]) + abs(bx[1]-g[1]) for g in goals)
                total_cost += best
        else:
            bx = boxes[i]; gx = goals[j]
            total_cost += abs(bx[0]-gx[0]) + abs(bx[1]-gx[1])
    return total_cost

def heuristic_hungarian(boxes, goals, goal_dist_map):
    if not boxes or not goals:
        return 0
    try:
        return hungarian_min_cost(boxes, goals, goal_dist_map)
    except Exception:
        s = 0
        for b in boxes:
            s += min((abs(b[0]-g[0]) + abs(b[1]-g[1])) for g in goals)
        return s

def reconstruct(came_from, end_key):
    parts = []
    cur = end_key
    while True:
        info = came_from.get(cur)
        if info is None:
            break
        parent, moves = info
        parts.append(moves)
        cur = parent
    parts.reverse()
    full_moves = []
    for p in parts:
        full_moves.extend(p)
    return full_moves

def astar_push_move_optimal_improved(walls, goals, start_boxes, start_player, max_expansions=2_000_000):
    start_key = (tuple(sorted(start_boxes)), start_player)
    goal_dist_map = compute_goal_distance_map(walls, goals)

    def is_goal_state(boxes):
        return all(b in goals for b in boxes)

    pq = []
    gscore = {start_key: 0}
    fscore = {start_key: heuristic_hungarian(start_boxes, goals, goal_dist_map)}
    heapq.heappush(pq, (fscore[start_key], gscore[start_key], start_key))

    came_from = {}
    expansions = 0
    bfs_cache = {}
    best_seen = {start_key: 0}

    while pq:
        f, g, key = heapq.heappop(pq)
        if g != gscore.get(key, INF):
            continue

        boxes_tup, player_pos = key
        boxes = set(boxes_tup)

        if is_goal_state(boxes):
            full_moves = reconstruct(came_from, key)
            return {"moves": full_moves, "expansions": expansions, "g": g}

        expansions += 1
        if expansions > max_expansions:
            return None

        parent_info = came_from.get(key)
        parent_boxes_tup = parent_info[0][0] if parent_info is not None else None

        push_candidates = []
        for b in boxes:
            for dr, dc, label in DIRS:
                target = (b[0] + dr, b[1] + dc)
                player_needed = (b[0] - dr, b[1] - dc)
                if target in walls or target in boxes:
                    continue
                if player_needed in walls or player_needed in boxes:
                    continue
                if is_deadlock(target, walls, goals, boxes):
                    continue

                bfs_key = (player_pos, boxes_tup, player_needed)
                if bfs_key in bfs_cache:
                    path_to_push = bfs_cache[bfs_key]
                else:
                    path_to_push = bfs_player_path(player_pos, player_needed, boxes, walls)
                    bfs_cache[bfs_key] = path_to_push

                if path_to_push is None:
                    continue

                cur_h = heuristic_hungarian(boxes, goals, goal_dist_map)
                new_boxes = set(boxes)
                new_boxes.remove(b)
                new_boxes.add(target)
                new_h = heuristic_hungarian(new_boxes, goals, goal_dist_map)
                score_delta = new_h - cur_h

                priority = (score_delta, len(path_to_push))
                push_candidates.append((priority, b, target, label, path_to_push))

        push_candidates.sort(key=lambda x: x[0])

        for _, b, target, label, path_to_push in push_candidates:
            new_boxes = set(boxes)
            new_boxes.remove(b)
            new_boxes.add(target)
            new_boxes_tup = tuple(sorted(new_boxes))
            new_player_pos = b

            moves_between = list(path_to_push) + [label]
            tentative_g = g + len(moves_between)

            new_key = (new_boxes_tup, new_player_pos)
            if parent_boxes_tup is not None and new_boxes_tup == parent_boxes_tup:
                continue

            if tentative_g >= best_seen.get(new_key, INF):
                continue

            best_seen[new_key] = tentative_g
            gscore[new_key] = tentative_g
            h = heuristic_hungarian(new_boxes, goals, goal_dist_map)
            f_new = tentative_g + h
            heapq.heappush(pq, (f_new, tentative_g, new_key))
            came_from[new_key] = (key, moves_between)

    return None

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def animate_solution(level_lines, walls, goals, boxes, player, moves, delay=0.2):
    cur_boxes = set(boxes)
    cur_player = player
    rows = len(level_lines)
    cols = max(len(r) for r in level_lines)
    step = 0
    for m in moves:
        dr, dc = DIR_MAP[m]
        next_pos = (cur_player[0] + dr, cur_player[1] + dc)
        if next_pos in cur_boxes:
            box_dest = (next_pos[0] + dr, next_pos[1] + dc)
            if box_dest in walls or box_dest in cur_boxes:
                print("Illegal push detected during animation; aborting.")
                return
            cur_boxes.remove(next_pos)
            cur_boxes.add(box_dest)
        cur_player = next_pos
        step += 1

        clear_console()
        print(f"Step {step}: Move {m} | Player {cur_player} | Boxes {sorted(cur_boxes)}")
        for r in range(rows):
            line = ""
            for c in range(cols):
                pos = (r, c)
                if pos in walls:
                    line += "#"
                elif pos == cur_player:
                    line += "@"
                elif pos in cur_boxes and pos in goals:
                    line += "*"
                elif pos in cur_boxes:
                    line += "$"
                elif pos in goals:
                    line += "."
                else:
                    line += " "
            print(line)
        try:
            time.sleep(delay)
        except Exception:
            pass
    print("solved.")

if __name__== "__main__":
    level = [
        "#########",
        "#   .   #",
        "# $ # $ #",
        "#   @ . #",
        "# $ # $ #",
        "#   . . #",
        "#########"
    ]

    walls, goals, boxes, player = parse_level(level)
    print("Parsed map:")
    print_map(level, walls, goals, boxes, player)
    print()

    t0 = time.time()
    result = astar_push_move_optimal_improved(walls, goals, boxes, player, max_expansions=2_000_000)
    t1 = time.time()

    if result is None:
        print("No solution found (or exceeded max expansions).")
        sys.exit(1)

    print("Solution found!")
    print("Expansions:", result["expansions"])
    print("Total moves (g):", result["g"])
    print("Move sequence (length):", len(result["moves"]))
    print("Move sequence (U/D/L/R):")
    print("".join(result["moves"]))
    print("\nsolving...")
    animate_solution(level, walls, goals, boxes, player, result["moves"], delay=0.2)
