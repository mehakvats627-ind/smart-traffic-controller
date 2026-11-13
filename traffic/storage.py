"""SQLite persistence and export helpers."""
import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "traffic.db"

def connect(path=DB_PATH):
    con=sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, created_at TEXT, scenario TEXT, seed INTEGER, duration INTEGER, results_json TEXT)")
    con.commit()
    return con

def save_run(scenario,seed,duration,results,path=DB_PATH):
    con=connect(path)
    try:
        cur=con.execute("INSERT INTO runs(created_at,scenario,seed,duration,results_json) VALUES(?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(),scenario,int(seed),int(duration),json.dumps(results)))
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def history(path=DB_PATH):
    con=connect(path)
    try:
        rows=con.execute("SELECT id,created_at,scenario,seed,duration,results_json FROM runs ORDER BY id DESC").fetchall()
    finally:
        con.close()
    return [{"id":r[0],"created_at":r[1],"scenario":r[2],"seed":r[3],"duration":r[4],"results":json.loads(r[5])} for r in rows]

def history_frame(path=DB_PATH):
    rows=history(path)
    flat=[]
    for r in rows:
        for controller,data in r["results"].items(): flat.append({"run_id":r["id"],"created_at":r["created_at"],"scenario":r["scenario"],"seed":r["seed"],"duration":r["duration"],"controller":controller,**data["metrics"]})
    return pd.DataFrame(flat)
