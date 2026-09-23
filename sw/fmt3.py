"""Round 7 (fix 5): one number format for every generated LaTeX macro and table cell.
sig(x, nd=3): None / non-finite -> the placeholder; integer-valued or >= 1000 -> integer with thousands separators;
otherwise nd significant digits WITH trailing zeros (3.00, 5.70, 1.10, 0.0720, 0.700, 0.580), so that tables print uniformly."""
import math
def sig(x, nd=3, none="--"):
    if x is None: return none
    try: x = float(x)
    except (TypeError, ValueError): return str(x)
    if not math.isfinite(x): return none
    if abs(x) >= 1000 or x == int(x): return f"{x:,.0f}"
    s = f"{x:#.{nd}g}"
    if "e" in s: return f"{x:,.0f}" if abs(x) >= 1 else f"{x:.{nd}g}"
    return s.rstrip(".")
