"""Mamdani fuzzy controller for selecting an approach and green duration."""
from __future__ import annotations

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyTrafficController:
    def __init__(self) -> None:
        self.queue = ctrl.Antecedent(np.arange(0, 51, 1), "queue")
        self.wait = ctrl.Antecedent(np.arange(0, 181, 1), "wait")
        self.green = ctrl.Consequent(np.arange(10, 61, 1), "green")
        self.queue["low"] = fuzz.trapmf(self.queue.universe, [0, 0, 5, 15])
        self.queue["medium"] = fuzz.trimf(self.queue.universe, [8, 22, 36])
        self.queue["high"] = fuzz.trapmf(self.queue.universe, [28, 40, 50, 50])
        self.wait["short"] = fuzz.trapmf(self.wait.universe, [0, 0, 15, 50])
        self.wait["moderate"] = fuzz.trimf(self.wait.universe, [30, 75, 120])
        self.wait["long"] = fuzz.trapmf(self.wait.universe, [95, 140, 180, 180])
        self.green["short"] = fuzz.trimf(self.green.universe, [10, 10, 28])
        self.green["medium"] = fuzz.trimf(self.green.universe, [18, 35, 50])
        self.green["long"] = fuzz.trimf(self.green.universe, [40, 60, 60])
        rules = [
            ctrl.Rule(self.queue["low"] & self.wait["short"], self.green["short"], label="R1"),
            ctrl.Rule(self.queue["low"] & self.wait["moderate"], self.green["short"], label="R2"),
            ctrl.Rule(self.queue["low"] & self.wait["long"], self.green["medium"], label="R3"),
            ctrl.Rule(self.queue["medium"] & self.wait["short"], self.green["short"], label="R4"),
            ctrl.Rule(self.queue["medium"] & self.wait["moderate"], self.green["medium"], label="R5"),
            ctrl.Rule(self.queue["medium"] & self.wait["long"], self.green["long"], label="R6"),
            ctrl.Rule(self.queue["high"] & self.wait["short"], self.green["medium"], label="R7"),
            ctrl.Rule(self.queue["high"] & self.wait["moderate"], self.green["long"], label="R8"),
            ctrl.Rule(self.queue["high"] & self.wait["long"], self.green["long"], label="R9"),
        ]
        self.rules = rules
        self.system = ctrl.ControlSystem(rules)

    def infer(self, queue: float, wait: float) -> dict:
        q, w = float(np.clip(queue, 0, 50)), float(np.clip(wait, 0, 180))
        sim = ctrl.ControlSystemSimulation(self.system, clip_to_bounds=True)
        sim.input["queue"], sim.input["wait"] = q, w
        sim.compute()
        qd = {name: float(fuzz.interp_membership(self.queue.universe, self.queue[name].mf, q)) for name in self.queue.terms}
        wd = {name: float(fuzz.interp_membership(self.wait.universe, self.wait[name].mf, w)) for name in self.wait.terms}
        strengths = []
        for rule in self.rules:
            try:
                value = float(rule.aggregate_firing[sim])
            except (KeyError, TypeError):
                value = 0.0
            strengths.append((rule.label, value))
        return {"duration": float(np.clip(sim.output["green"], 10, 60)), "queue_membership": qd,
                "wait_membership": wd, "rules": strengths,
                "selected_rule": max(strengths, key=lambda x: x[1])[0]}

