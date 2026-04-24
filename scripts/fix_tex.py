#!/usr/bin/env python3
"""
Patch nbconvert latex output for Overleaf:

  1. % !TEX program = xelatex magic comment
  2. Unicode -> LaTeX mappings + emoji macros (cmark/xmark via pifont,
     wrapped in \\texorpdfstring so they survive PDF bookmarks)
  3. Strip combining-circumflex (U+0302), \\textdegree -> ^{\\circ},
     ° / ✅ / ❌ source replacements
  4. Figure path rewrites (figures/ and single-phase-inverter_files/),
     case fix for Power_Control_dq.pdf
  5. Real LaTeX \\title / \\author / \\date (replaces nbconvert's _tmp_for_pdf)
  6. Replace TOC image + manual markdown TOC with \\tableofcontents
  7. Paired \\hypertarget{X}{...\\label{X}} dedup for repeated heading slugs
     (numerical-example, pros, cons, ...)

Idempotent: safe to re-run on already-patched source.
"""
import re, os, sys, collections

path = sys.argv[1]
src = open(path).read()

# 1. Magic comment for Overleaf compiler
if not src.startswith("% !TEX"):
    src = "% !TEX program = xelatex\n" + src

# 2. Inject Unicode mappings + emoji macros after \documentclass (idempotent)
# Replace nbconvert's pdfTeX inputenc setup. The default has an
# `\IfFileExists{alphabeta.sty}` branch that loads alphabeta WITHOUT inputenc,
# which silently breaks raw unicode chars on TeX installs that ship alphabeta
# (notably Overleaf). The fallback uses [utf8x]{inputenc}, but utf8x conflicts
# with newunicodechar on TeX Live 2024+ (chars silently fail to decode).
# Solution: drop the conditional, always use plain [utf8]{inputenc} and rely
# on our explicit \newunicodechar mappings below for every non-ASCII char.
src = re.sub(
    r'\\ifPDFTeX\s*\n\s*\\usepackage\[T1\]\{fontenc\}\s*\n\s*\\IfFileExists\{alphabeta\.sty\}\{\s*\n'
    r'\s*\\usepackage\{alphabeta\}\s*\n'
    r'\s*\}\{\s*\n'
    r'\s*\\usepackage\[mathletters\]\{ucs\}\s*\n'
    r'\s*\\usepackage\[utf8x\]\{inputenc\}\s*\n'
    r'\s*\}',
    r'\\ifPDFTeX\n'
    r'        \\usepackage[T1]{fontenc}\n'
    r'        % Use plain [utf8]{inputenc}: utf8x conflicts with newunicodechar on\n'
    r'        % recent TeX Live (2024+), causing chars to silently not decode.\n'
    r'        \\usepackage[utf8]{inputenc}',
    src,
)

SENTINEL = "% --- Unicode -> LaTeX mappings"
inject = r"""
% --- Unicode -> LaTeX mappings + emoji macros ---
% Loaded AFTER inputenc; declares EVERY non-ASCII char that appears in the body
% so plain [utf8]{inputenc} can decode it.
\usepackage{newunicodechar}
\usepackage{pifont}
\providecommand{\cmark}{\texorpdfstring{{\color{green!60!black}\ding{51}}\,}{[+] }}
\providecommand{\xmark}{\texorpdfstring{{\color{red}\ding{55}}\,}{[-] }}
% (A few "Package newunicodechar Warning: Redefining Unicode character" lines
%  on the pdflatex path are harmless: T1 fontenc already maps a couple of
%  these to defaults and we override them with proper ensuremath versions.)
% Math symbols
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≠}{\ensuremath{\neq}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{↔}{\ensuremath{\leftrightarrow}}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{←}{\ensuremath{\leftarrow}}
\newunicodechar{²}{\ensuremath{^{2}}}
\newunicodechar{³}{\ensuremath{^{3}}}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{×}{\ensuremath{\times}}
% Greek letters that appear in body prose (not just math):
\newunicodechar{Δ}{\ensuremath{\Delta}}
\newunicodechar{α}{\ensuremath{\alpha}}
\newunicodechar{β}{\ensuremath{\beta}}
\newunicodechar{θ}{\ensuremath{\theta}}
\newunicodechar{ω}{\ensuremath{\omega}}
"""
# Inject AFTER the \ifPDFTeX/\fi block (newunicodechar needs inputenc loaded
# first). Anchor on `\usepackage{fancyvrb}` which is the next package after \fi.
if SENTINEL not in src:
    m = re.search(r'\n(\s*)\\usepackage\{fancyvrb\}', src)
    src = src[:m.start()] + "\n" + inject + src[m.start():]

# 3. Strip combining circumflex
src = src.replace("\u0302", "")
# 4. textdegree -> ^\circ (textdegree is invalid in math mode)
src = src.replace("\\textdegree", "^{\\circ}")
# 5. Replace emoji + degree symbol with macros (utf8x can't intercept these via newunicodechar)
src = src.replace("✅", r"\cmark{}")
src = src.replace("❌", r"\xmark{}")
src = src.replace("°", r"\ensuremath{{}^{\circ}}")
# Re-runs: collapse stale '\cmark\,' / '\xmark\,' artefacts (the trailing thinspace
# breaks PDF bookmarks; the new \cmark/\xmark macros embed their own spacing).
src = src.replace(r"\cmark\,", r"\cmark{}")
src = src.replace(r"\xmark\,", r"\xmark{}")

# 6. Path rewrites for figures and matplotlib outputs
fig_dir = os.path.join(os.path.dirname(path), "figures")
mpl_dir = os.path.join(os.path.dirname(path), "single-phase-inverter_files")
fig_files = set(os.listdir(fig_dir)) if os.path.isdir(fig_dir) else set()
mpl_files = set(os.listdir(mpl_dir)) if os.path.isdir(mpl_dir) else set()

def path_repl(m):
    inner = m.group(1)
    bn = inner.split("/")[-1]
    if bn in fig_files:
        return "{figures/" + bn + "}"
    if bn in mpl_files:
        return "{single-phase-inverter_files/" + bn + "}"
    return m.group(0)

src = re.sub(r'\{(single-phase-inverter_files/[^}]+|[A-Za-z0-9_\- ]+\.(?:pdf|png|jpg))\}', path_repl, src)
# Case fix for one figure that nbconvert emits with title-case but the file is lowercase
src = src.replace("{figures/Power_Control_dq.pdf}", "{figures/power_control_dq.pdf}")

# 7. Real document metadata (replace nbconvert's filename-derived title)
src = re.sub(
    r'\\title\{\\_tmp\\_for\\_pdf\}',
    r'\\title{Bidirectional Single-Phase Inverter\\\\\\large Control in abc and dq frames}'
    r'\n    \\author{Kristian Skorpen}'
    r'\n    \\date{\\today}',
    src,
)

# 8. Replace TOC image + manual markdown TOC with real \tableofcontents.
# The block runs from `\includegraphics{figures/TOC_Reduced.png}` through the
# `\end{enumerate}` of the manual TOC list (immediately after).
toc_re = re.compile(
    r'\\includegraphics\{figures/TOC_Reduced\.png\}\s*\n+'
    r'\s*\\hypertarget\{table-of-contents\}\{%\s*\n'
    r'\\subsubsection\{Table of contents\}\\label\{table-of-contents\}\}\s*\n+'
    r'\\begin\{enumerate\}.*?\\end\{enumerate\}',
    re.DOTALL,
)
src, n_toc = toc_re.subn(
    r'\\setcounter{tocdepth}{3}' '\n' r'\\tableofcontents' '\n' r'\\newpage',
    src,
)

# 8b. Recover display-math blocks that pandoc/nbconvert wrapped in verbatim.
# When the notebook source had ```matrix-latex``` (code fence) inside $$...$$,
# pandoc emitted \$\$\n\\begin{verbatim}...\\end{verbatim}\n\$\$ which prints
# the LaTeX as code instead of rendering math. Convert back to \[...\].
math_verbatim = re.compile(
    r'\\\$\\\$\s*\n+\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}\s*\n+\\\$\\\$',
    re.DOTALL,
)
src, n_math = math_verbatim.subn(lambda m: "\\[\n" + m.group(1).rstrip() + "\n\\]", src)

# 9. Paired-anchor dedup
# nbconvert pattern: \hypertarget{X}{...\label{X}}. Sometimes also orphan \label{X}.
# Strategy: pair each \hypertarget with the next nearby \label of the same name.
# Then count occurrences PER NAME across pair-units and rename 2nd, 3rd, ...
# consistently across both sides of each unit. Otherwise hyperref breaks.
anchor_re = re.compile(r'\\(hypertarget|label)\{([^}]+)\}')
anchors = list(anchor_re.finditer(src))

pair_partner = {}
for i, m in enumerate(anchors):
    if m.group(1) == "hypertarget":
        name = m.group(2)
        for j in range(i+1, min(i+5, len(anchors))):
            n2 = anchors[j]
            if n2.group(1) == "label" and n2.group(2) == name:
                pair_partner[i] = j
                pair_partner[j] = i
                break

visited = set()
units = []
for i, m in enumerate(anchors):
    if i in visited: continue
    name = m.group(2)
    if i in pair_partner:
        units.append((name, [i, pair_partner[i]]))
        visited.add(i); visited.add(pair_partner[i])
    else:
        units.append((name, [i]))
        visited.add(i)

name_counter = collections.Counter()
edits = []
for name, idxs in units:
    name_counter[name] += 1
    if name_counter[name] == 1:
        continue
    new_name = f"{name}-{name_counter[name]}"
    for idx in idxs:
        a = anchors[idx]
        kind = a.group(1)
        edits.append((a.start(), a.end(), f"\\{kind}{{{new_name}}}"))

edits.sort(reverse=True)
for s, e, repl in edits:
    src = src[:s] + repl + src[e:]

open(path, "w").write(src)

# Verify
ht_dups = [(k,v) for k,v in collections.Counter(re.findall(r'\\hypertarget\{([^}]+)\}', src)).items() if v > 1]
lb_dups = [(k,v) for k,v in collections.Counter(re.findall(r'\\label\{([^}]+)\}', src)).items() if v > 1]
print(f"toc-replacements: {n_toc}")
print(f"math-verbatim recovered: {n_math}")
print(f"dup hypertargets after dedup: {ht_dups}")
print(f"dup labels after dedup: {lb_dups}")
print(f"size: {len(src)} bytes")
