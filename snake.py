from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template_string, request


BOARD_WIDTH = 20
BOARD_HEIGHT = 20


@dataclass
class SnakeGame:
    width: int = BOARD_WIDTH
    height: int = BOARD_HEIGHT
    snake: List[Tuple[int, int]] = field(default_factory=list)
    direction: str = "right"
    next_direction: str = "right"
    food: Tuple[int, int] = (0, 0)
    score: int = 0
    alive: bool = True
    wrap_walls: bool = True

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        cx, cy = self.width // 2, self.height // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = "right"
        self.next_direction = "right"
        self.score = 0
        self.alive = True
        self.food = self._spawn_food()

    def _spawn_food(self) -> Tuple[int, int]:
        occupied = set(self.snake)
        empty_cells = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in occupied
        ]
        if not empty_cells:
            return self.snake[0]
        return random.choice(empty_cells)

    def turn(self, direction: str) -> None:
        if direction not in {"up", "down", "left", "right"}:
            return

        opposite = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }
        if opposite[direction] == self.direction:
            return
        self.next_direction = direction

    def step(self) -> None:
        if not self.alive:
            return

        self.direction = self.next_direction
        x, y = self.snake[0]
        if self.direction == "up":
            y -= 1
        elif self.direction == "down":
            y += 1
        elif self.direction == "left":
            x -= 1
        elif self.direction == "right":
            x += 1

        if self.wrap_walls:
            x %= self.width
            y %= self.height

        new_head = (x, y)
        grows = new_head == self.food
        # Moving into the old tail position is valid when the snake is not growing.
        body_for_collision = self.snake if grows else self.snake[:-1]

        if (not self.wrap_walls and (x < 0 or x >= self.width or y < 0 or y >= self.height)) or (
            new_head in body_for_collision
        ):
            self.alive = False
            return

        self.snake.insert(0, new_head)

        if grows:
            self.score += 1
            self.food = self._spawn_food()
        else:
            self.snake.pop()

    def as_dict(self) -> Dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "snake": self.snake,
            "food": self.food,
            "score": self.score,
            "alive": self.alive,
            "direction": self.direction,
        }


app = Flask(__name__)
games: Dict[str, SnakeGame] = {}


def get_game(game_id: str) -> SnakeGame | None:
    return games.get(game_id)


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Snake (Python Backend)</title>
  <style>
    :root {
      --bg: #101522;
      --panel: #1a2336;
      --snake: #31d07f;
      --food: #ff7043;
      --grid: #27334c;
      --text: #eaf0ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 20%, #223150 0%, transparent 35%),
        radial-gradient(circle at 80% 80%, #22203e 0%, transparent 40%),
        var(--bg);
      padding: 16px;
    }
    .card {
      background: linear-gradient(180deg, #1b2438 0%, #141d2f 100%);
      border: 1px solid #2c3c5d;
      border-radius: 14px;
      width: min(92vw, 560px);
      padding: 14px;
      box-shadow: 0 10px 35px rgba(0, 0, 0, 0.35);
    }
    .top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    h1 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .score {
      font-weight: 700;
      padding: 5px 10px;
      border-radius: 999px;
      background: #101a2b;
      border: 1px solid #2a3a59;
    }
    canvas {
      width: 100%;
      aspect-ratio: 1 / 1;
      image-rendering: pixelated;
      border-radius: 8px;
      border: 1px solid #2a3958;
      background: #0d1423;
      display: block;
    }
    .controls {
      margin-top: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    button {
      border: 1px solid #365286;
      color: var(--text);
      background: #1f3356;
      border-radius: 10px;
      padding: 8px 12px;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { filter: brightness(1.08); }
    .hint {
      opacity: 0.85;
      font-size: 0.9rem;
    }
    .state {
      font-weight: 700;
      color: #ffcf5d;
    }
    .dpad {
      margin-top: 10px;
      display: grid;
      place-items: center;
      gap: 8px;
    }
    .dpad-row {
      display: flex;
      gap: 8px;
    }
    .dpad-btn {
      min-width: 74px;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="top">
      <h1>Snake</h1>
      <div class="score">Score: <span id="score">0</span></div>
    </div>
    <canvas id="game" width="600" height="600"></canvas>
    <div class="controls">
      <button id="newGameBtn">New Game</button>
      <span class="hint">Arrow keys / WASD / touch controls</span>
      <span class="state" id="stateLabel"></span>
    </div>
    <div class="dpad">
      <button data-dir="up" class="dpad-btn">Up</button>
      <div class="dpad-row">
        <button data-dir="left" class="dpad-btn">Left</button>
        <button data-dir="down" class="dpad-btn">Down</button>
        <button data-dir="right" class="dpad-btn">Right</button>
      </div>
    </div>
  </div>

  <script>
    const canvas = document.getElementById("game");
    const ctx = canvas.getContext("2d");
    const scoreEl = document.getElementById("score");
    const stateLabel = document.getElementById("stateLabel");
    const newGameBtn = document.getElementById("newGameBtn");
    let gameId = null;
    let state = null;
    let tickMs = 165;

    const keyMap = {
      ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
      w: "up", a: "left", s: "down", d: "right",
      W: "up", A: "left", S: "down", D: "right",
    };

    function drawGrid(state) {
      const w = canvas.width;
      const h = canvas.height;
      const cellW = w / state.width;
      const cellH = h / state.height;

      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0d1423";
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "#27334c";
      ctx.lineWidth = 1;
      for (let x = 0; x <= state.width; x++) {
        ctx.beginPath();
        ctx.moveTo(x * cellW, 0);
        ctx.lineTo(x * cellW, h);
        ctx.stroke();
      }
      for (let y = 0; y <= state.height; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * cellH);
        ctx.lineTo(w, y * cellH);
        ctx.stroke();
      }

      ctx.fillStyle = "#ff7043";
      ctx.fillRect(state.food[0] * cellW, state.food[1] * cellH, cellW, cellH);

      ctx.fillStyle = "#31d07f";
      state.snake.forEach((part, i) => {
        const inset = i === 0 ? 1 : 2;
        ctx.fillRect(part[0] * cellW + inset, part[1] * cellH + inset, cellW - inset * 2, cellH - inset * 2);
      });
    }

    async function postJSON(url, body = {}) {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    }

    async function newGame() {
      const data = await postJSON("/api/new");
      gameId = data.game_id;
      state = data.state;
      render();
    }

    function render() {
      if (!state) return;
      scoreEl.textContent = state.score;
      stateLabel.textContent = state.alive ? "" : "Game Over";
      drawGrid(state);
    }

    async function tick() {
      if (!gameId || !state) return;
      if (!state.alive) return;
      const data = await postJSON("/api/tick", { game_id: gameId });
      state = data.state;
      render();
    }

    async function turn(direction) {
      if (!gameId || !state || !state.alive) return;
      const data = await postJSON("/api/turn", { game_id: gameId, direction });
      state = data.state;
      render();
    }

    window.addEventListener("keydown", async (e) => {
      const direction = keyMap[e.key];
      if (!direction) return;
      e.preventDefault();
      turn(direction).catch(console.error);
    });

    newGameBtn.addEventListener("click", () => {
      newGame().catch(console.error);
    });

    document.querySelectorAll(".dpad-btn").forEach((btn) => {
      const handler = (e) => {
        e.preventDefault();
        const dir = btn.dataset.dir;
        turn(dir).catch(console.error);
      };
      btn.addEventListener("click", handler);
      btn.addEventListener("touchstart", handler, { passive: false });
    });

    setInterval(() => tick().catch(console.error), tickMs);
    newGame().catch(console.error);
  </script>
</body>
</html>
"""


@app.get("/")
def index() -> str:
    return render_template_string(INDEX_HTML)


@app.post("/api/new")
def new_game():
    game_id = uuid.uuid4().hex
    game = SnakeGame()
    games[game_id] = game
    return jsonify({"game_id": game_id, "state": game.as_dict()})


@app.post("/api/turn")
def turn():
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    direction = payload.get("direction")
    if not game_id or not direction:
        return jsonify({"error": "game_id and direction are required"}), 400

    game = get_game(game_id)
    if not game:
        return jsonify({"error": "game not found"}), 404

    game.turn(direction)
    return jsonify({"state": game.as_dict()})


@app.post("/api/tick")
def tick():
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    if not game_id:
        return jsonify({"error": "game_id is required"}), 400

    game = get_game(game_id)
    if not game:
        return jsonify({"error": "game not found"}), 404

    game.step()
    return jsonify({"state": game.as_dict()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
