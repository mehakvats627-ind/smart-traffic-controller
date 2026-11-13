import json
from pathlib import Path
from PIL import Image
from io import BytesIO
from traffic.fuzzy import FuzzyTrafficController
from traffic.simulation import TrafficSimulation, Vehicle, compare_controllers, make_schedule
from traffic.storage import save_run, history
from traffic.renderer import render

def test_fuzzy_rules_and_green_bounds():
    fuzzy=FuzzyTrafficController()
    assert len(fuzzy.rules)==9
    for q in range(0,51,5):
        for w in range(0,181,15):
            result=fuzzy.infer(q,w)
            assert 10 <= result["duration"] <= 60
            assert len(result["rules"])==9
    probes=[(0,0),(0,75),(0,180),(22,0),(22,75),(22,180),(50,0),(50,75),(50,180)]
    assert {fuzzy.infer(q,w)["selected_rule"] for q,w in probes}=={f"R{i}" for i in range(1,10)}

def test_phase_transition_safety():
    sim=TrafficSimulation("Fixed Time","Low traffic",3,120,fixed_durations=[12,15,18,21])
    seen=[]
    for _ in range(60):
        sim.step(); seen.append((sim.state.phase,sim.state.transition))
    assert any(t=="yellow" for _,t in seen)
    assert any(t=="all-red" for _,t in seen)
    assert sim.fixed_durations==(12,15,18,21)
    for i,(phase,transition) in enumerate(seen):
        if transition=="all-red":
            assert [seen[j][1] for j in range(i-3,i)]==["yellow"]*3
    # A new green only follows the full yellow and all-red clearance.
    for i,(phase,transition) in enumerate(seen):
        if transition=="green" and i:
            assert seen[i-1][1] in ("all-red","green")

def test_reproducible_schedule_and_paired_comparison():
    assert make_schedule("Rush hour",42,60)==make_schedule("Rush hour",42,60)
    result=compare_controllers("Rush hour",42,120)
    assert set(result)=={"Fixed Time","Fuzzy Logic"}
    assert all(d["metrics"]["served"]>=0 for d in result.values())

def test_vehicle_moves_and_serves():
    sim=TrafficSimulation("Fixed Time","Rush hour",1,180)
    sim.step(180)
    assert sim.state.served > 0
    assert sim.state.seconds==180

def test_headless_renderer_returns_valid_png():
    image=Image.open(BytesIO(render(TrafficSimulation().snapshot())))
    assert image.format=="PNG" and image.size==(1000,500)

def test_emergency_priority_and_wait_fairness():
    sim=TrafficSimulation("Fuzzy Logic","Low traffic",3,120)
    sim.state.seconds=100
    sim.state.vehicles=[Vehicle("West","Ambulance",99,4)]
    assert sim._next_phase()[0]=="West"
    sim.state.vehicles=[Vehicle("South","Car",0,3),Vehicle("North","Car",99,3),Vehicle("East","Car",99,3)]
    assert sim._next_phase()[0]=="South"

def test_database_round_trip():
    path=Path(__file__).parent/".test.db"
    payload={"Fixed Time":{"metrics":{"served":1},"queue_series":[1]},"Fuzzy Logic":{"metrics":{"served":2},"queue_series":[0]}}
    try:
        ident=save_run("Normal traffic",7,60,payload,path)
        rows=history(path)
        assert rows[0]["id"]==ident and rows[0]["results"]==payload
    finally:
        if path.exists(): path.unlink()

