# Python Snake Game (Browser)

A Snake game with Python game logic and a browser frontend.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python snake.py
```

Then open: http://127.0.0.1:5000

## Deploy on Render

1. Push this project to a GitHub repo.
2. In Render, create a new **Web Service** from that repo.
3. Render will use `render.yaml` automatically.
4. After deploy, open your Render URL to play.

If `render.yaml` is not picked up, set manually:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn snake:app`
