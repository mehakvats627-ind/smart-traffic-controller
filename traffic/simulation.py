"""Seeded, discrete-time four-approach traffic simulation and controllers."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from .fuzzy import FuzzyTrafficController

APPROACHES = ("North", "East", "South", "West")
VEHICLES = ("Car", "Bus", "Truck", "Ambulance")
FIXED_DURATIONS = (25, 25, 25, 25)

@dataclass
class Vehicle:
    approach: str
    kind: str
    arrived: int
    remaining: int
    stopped: bool = False
    stops: int = 0

@dataclass
class SimState:
    seconds: int = 0
    phase: str = "North"
    phase_elapsed: int = 0
    transition: str = "green"
    transition_elapsed: int = 0
    vehicles: list[Vehicle] | None = None
    served: int = 0
    waits: list[int] | None = None
    travel: list[int] | None = None
    queues: list[int] | None = None
    stops: list[int] | None = None
    phase_green: int = 25
    arrivals: dict | None = None

    def __post_init__(self):
        self.vehicles = self.vehicles or []
        self.waits = self.waits or []
        self.travel = self.travel or []
        self.queues = self.queues or []
        self.stops = self.stops or []
        self.arrivals = self.arrivals or {a: [] for a in APPROACHES}

def make_schedule(scenario="Rush hour", seed=23, duration=600, custom=None):
    rates = {"Normal traffic": [0.10]*4, "Rush hour": [0.22]*4, "Unequal traffic": [0.38,0.08,0.16,0.06],
             "Low traffic": [0.035]*4, "Emergency vehicle": [0.12]*4}
    probs = rates.get(scenario, custom or [0.12]*4)
    rng = np.random.default_rng(seed)
    schedule = {a: [] for a in APPROACHES}
    for t in range(duration):
        for i, a in enumerate(APPROACHES):
            if rng.random() < probs[i]:
                kind = rng.choice(VEHICLES[:3], p=[.76,.12,.12]).item()
                schedule[a].append((t, kind))
    if scenario == "Emergency vehicle":
        schedule["North"].append((min(75, duration-1), "Ambulance"))
        schedule["North"].sort()
    return schedule

class TrafficSimulation:
    def __init__(self, controller="Fuzzy Logic", scenario="Rush hour", seed=23, duration=600, custom=None, fixed_durations=None):
        self.controller, self.scenario, self.seed = controller, scenario, seed
        self.fixed_durations=tuple(fixed_durations or FIXED_DURATIONS)
        self.state = SimState(phase_green=self.fixed_durations[0], arrivals=make_schedule(scenario,seed,duration,custom))
        self.fuzzy = FuzzyTrafficController()
        self.max_wait_fairness = 90

    def queue_counts(self):
        return {a: sum(v.approach == a for v in self.state.vehicles) for a in APPROACHES}

    def _next_phase(self):
        s=self.state
        if self.controller == "Fixed Time":
            next_index=(APPROACHES.index(s.phase)+1)%4
            return APPROACHES[next_index], self.fixed_durations[next_index]
        counts=self.queue_counts()
        avgwait={a: max((s.seconds-v.arrived for v in s.vehicles if v.approach==a), default=0) for a in APPROACHES}
        emergency=[v.approach for v in s.vehicles if v.kind == "Ambulance"]
        # Aged-wait fairness is an override to the fuzzy selection, not a replacement for inference.
        overdue=[a for a in APPROACHES if avgwait[a] >= self.max_wait_fairness]
        target=(emergency[0] if emergency else max(overdue,key=lambda a: avgwait[a])) if (emergency or overdue) else max(APPROACHES,key=lambda a: (counts[a],avgwait[a]))
        inf=self.fuzzy.infer(counts[target],avgwait[target])
        s.phase_green=inf["duration"]
        return target, inf["duration"]

    def step(self, seconds=1):
        s=self.state
        for _ in range(seconds):
            now=s.seconds
            for a, entries in s.arrivals.items():
                while entries and entries[0][0] <= now:
                    _,kind=entries.pop(0)
                    s.vehicles.append(Vehicle(a,kind,now,3 if kind=="Car" else 5 if kind=="Bus" else 4))
            green=s.transition=="green" and s.phase
            for v in list(s.vehicles):
                if green and v.approach==s.phase:
                    v.remaining-=1
                    v.stopped=False
                    if v.remaining<=0:
                        s.vehicles.remove(v); s.served+=1
                        s.waits.append(max(0,now-v.arrived-(3 if v.kind=="Car" else 5 if v.kind=="Bus" else 4)))
                        s.travel.append(now-v.arrived); s.stops.append(v.stops)
                else:
                    v.stops += int(not v.stopped)
                    v.stopped=True
            s.queues.append(len(s.vehicles))
            if s.transition=="green":
                s.phase_elapsed+=1
                if s.phase_elapsed>=s.phase_green:
                    s.transition="yellow"; s.transition_elapsed=0
            elif s.transition=="yellow":
                s.transition_elapsed+=1
                if s.transition_elapsed>=3: s.transition="all-red"; s.transition_elapsed=0
            else:
                s.transition_elapsed+=1
                if s.transition_elapsed>=1:
                    s.phase,s.phase_green=self._next_phase(); s.transition="green"; s.phase_elapsed=0; s.transition_elapsed=0
            s.seconds+=1
        return s

    def metrics(self):
        s=self.state
        waits=list(s.waits)+[max(0,s.seconds-v.arrived) for v in s.vehicles]
        return {"avg_wait":float(np.mean(waits)) if waits else 0., "max_wait":max(waits,default=0),
                "avg_queue":float(np.mean(s.queues)) if s.queues else 0., "max_queue":max(s.queues,default=0),
                "served":s.served,"throughput_per_min":s.served/(s.seconds/60) if s.seconds else 0,
                "avg_travel":float(np.mean(s.travel)) if s.travel else 0.,
                "stops_per_vehicle":float(np.mean(s.stops)) if s.stops else 0.}

    def snapshot(self):
        s=self.state
        return {"seconds":s.seconds,"phase":s.phase,"transition":s.transition,"phase_elapsed":s.phase_elapsed,
                "phase_green":s.phase_green,"queues":self.queue_counts(),"vehicles":[asdict(v) for v in s.vehicles],"metrics":self.metrics()}

def compare_controllers(scenario="Rush hour",seed=23,duration=600,custom=None,fixed_durations=None):
    results={}
    for name in ("Fixed Time","Fuzzy Logic"):
        sim=TrafficSimulation(name,scenario,seed,duration,custom,fixed_durations)
        while sim.state.seconds < duration: sim.step(min(10,duration-sim.state.seconds))
        results[name]={"metrics":sim.metrics(),"queue_series":sim.state.queues,"served":sim.state.served}
    return results
