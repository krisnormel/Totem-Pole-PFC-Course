# Single-Phase Totem-Pole PFC Course

LaTeX source for the Overleaf-connected course on control of a
single-phase totem-pole PFC.

## Build

```
make
```

Produces `totem-pole-pfc.pdf` via two passes of `xelatex`. pdflatex
also works (the preamble includes the iftex branch).

## Structure

1. Introduction
2. The Totem-Pole PFC (topology, simplified model, control structure)
3. PWM Strategy
4. Control in the abc frame
   - Current control
   - Power calculation methods
   - Pure active power control
   - DC-link voltage control
5. Comparison of control methods
