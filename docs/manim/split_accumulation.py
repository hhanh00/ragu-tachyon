"""Instances pass through the circuit while witnesses stay with the prover; pnpm docs:manim --page split-accumulation."""
from manim import *
from concept_diagrams import label, math, heading, box, arrow, INK, MUTED, BLUE, TEAL, ORANGE, PURPLE


class InstanceWitnessLanes(Scene):
    def construct(self):
        heading(self, 'Each accumulator travels in two parts',
                'The circuit reads the instance lane, and only the prover and the decider read the witness lane')
        xs = [-3.6, 0.75]
        inst_y, wit_y = 0.75, -1.65
        self.add(label('Instance', -6.95, inst_y + 0.82, 22, BLUE),
                 label('Witness', -6.95, wit_y - 0.82, 22, TEAL))
        self.add(box(-6.65, inst_y, 1.6, 1.0, BLUE), math(r'(\bar{P}_i, u_i, v_i)', -6.65, inst_y, 22, BLUE, 1.45),
                 box(-6.65, wit_y, 1.6, 1.0, TEAL), math(r'(\mathbf{p}_i, \gamma_i)', -6.65, wit_y, 24, TEAL, 1.45))
        previous = -5.85
        names = [('i+1', r'\pi_i'), ('i+2', r'\pi_{i+1}')]
        for x, (sub, pi) in zip(xs, names):
            self.add(box(x, inst_y, 2.3, 1.0, ORANGE),
                     label('Acc.V, in the circuit', x, inst_y + 0.2, 17, ORANGE, 2.1),
                     label('checks the update', x, inst_y - 0.2, 17, MUTED, 2.1),
                     box(x, wit_y, 2.3, 1.0, PURPLE),
                     label('Acc.P, outside', x, wit_y + 0.2, 17, PURPLE, 2.1),
                     label('combines polynomials', x, wit_y - 0.2, 17, MUTED, 2.1),
                     arrow((previous, inst_y), (x - 1.15, inst_y), BLUE),
                     arrow((previous, wit_y), (x - 1.15, wit_y), TEAL),
                     arrow((x, wit_y + 0.5), (x, inst_y - 0.5), MUTED),
                     label('new instance, pf', x + 1.0, (inst_y + wit_y) / 2, 17, MUTED))
            self.add(math(rf'{pi}.\mathrm{{inst}}', x - 0.0, inst_y + 1.2, 22, BLUE),
                     arrow((x, inst_y + 1.0), (x, inst_y + 0.52), BLUE),
                     math(rf'{pi}.\mathrm{{wit}}', x, wit_y - 1.2, 22, TEAL),
                     arrow((x, wit_y - 1.0), (x, wit_y - 0.52), TEAL))
            previous = x + 1.15
        self.add(box(5.75, (inst_y + wit_y) / 2, 2.5, 2.2, INK),
                 label('Decider', 5.75, (inst_y + wit_y) / 2 + 0.5, 25, INK),
                 label('one MSM and', 5.75, (inst_y + wit_y) / 2, 18, MUTED),
                 label('one evaluation', 5.75, (inst_y + wit_y) / 2 - 0.35, 18, MUTED),
                 arrow((previous, inst_y), (4.5, inst_y - 0.2), BLUE),
                 arrow((previous, wit_y), (4.5, wit_y + 0.2), TEAL))
