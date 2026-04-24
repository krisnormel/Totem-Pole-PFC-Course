# Inverter course — open TODOs

Items flagged during Kristian's 2026-04-23 review that need a second pass.
Kept out of the course text so the PDF stays clean; track and close here.

## Section 5.3 Phase-Locked Loop (PLL)
- Re-check the "three components" description of the PLL (current wording
  mapping `(vα, vβ)` → `(vd, vq)` → PI(vq) → `Δω̂` → integrator → `θ̂`).
  Verify the sign convention against a working implementation and the
  PLL numerical example below. If the description is still off, revise.

## Section 5.4 OSG
- Full review pass: the section now covers only Simple OSG (formerly
  mislabelled FAE in earlier drafts) and SOGI. Confirm the "Simple OSG"
  naming (alternative: "Recursive OSG") matches published terminology
  or pick a better name.
- Confirm that referring to Imperix's SOGI-PLL article + the SOGI figure
  is enough; if not, add a minimal block diagram made in-house.
- Any text that previously referred to "FAE" or "quarter-period delay"
  should now read correctly after the trim — check on a final read-through.
