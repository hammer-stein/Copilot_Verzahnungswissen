"""
gear_metrology.py
-----------------
Software-unabhängige Vermessung von Verzahnungsgeometrie direkt aus der B-Rep.

Kernidee
========
Statt sich auf die Flächen-Tessellierung der CAD-Software zu verlassen
(Zylinder-/Kegel-/Torus-Patches, die je nach Modellierer völlig unterschiedlich
ausfallen), wird das Bauteil in seinem EIGENEN Koordinatensystem vermessen:

  1. Rotationsachse  → Hauptträgheitsachse (die "andersartige" der drei Achsen).
  2. Planare Querschnitte senkrecht zur Achse liefern die exakte Zahnkontur r(θ).
  3. Der Zahnkranz wird über die WINKELPERIODIZITÄT der Kontur identifiziert:
     der längste zusammenhängende Achsbereich mit konstanter Zähnezahl.

Daraus folgen direkt und herstellerunabhängig:
  z (Zähnezahl), d_a (Kopfkreis), d_f (Fußkreis), m (Modul), d (Teilkreis),
  b (Zahnbreite), β (Schrägungswinkel), Bohrungsdurchmesser, Innen-/Außen-
  verzahnung sowie Kegelrad-Erkennung.

Die Funktion extract_metrology(shape) gibt ein Dict mit den gemessenen Größen
zurück (None wo nicht bestimmbar). geometry_analyzer.py nutzt diese als
hochkonfidente Primärquelle und fällt nur bei Misserfolg auf Heuristiken zurück.
"""

import logging
import math
import time
from typing import Optional, Tuple, List, Dict, Any

from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GCPnts import GCPnts_AbscissaPoint
from OCC.Core.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods
from OCC.Core.gp import gp_Pln, gp_Pnt, gp_Dir

_log = logging.getLogger("gear_metrology")

# Standard-Normmodule DIN 780 (für Modul-Rundung)
STANDARD_MODULES = [
    0.1, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8,
    1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0,
    10.0, 12.0, 16.0, 20.0, 25.0, 32.0, 40.0, 50.0,
]

# Zoll-Verzahnungen (US-Markt) sind über den Diametral Pitch (DP) genormt,
# NICHT metrisch: m = 25.4 / DP. Viele reale STEP-Dateien stammen aus US-CAD.
DIAMETRAL_PITCHES = [3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 72, 80, 96, 120]
INCH_MODULES = [round(25.4 / dp, 4) for dp in DIAMETRAL_PITCHES]

# Vereinigte, sortierte Kandidatenliste (metrisch + zöllig) für die Rundung
ALL_MODULES = sorted(set(STANDARD_MODULES) | set(INCH_MODULES))

# Schnittzahl-Grenzen. Untergrenze sichert die volle Abdeckung des Zahnkranz-
# bandes (bei Kegel-/Gehrungsrädern oft nur ~⅓ der Achslänge); Obergrenze deckelt
# die Rechenzeit bei sehr großen B-Reps.
MIN_SECTIONS = 28
MAX_SECTIONS = 72


# ─────────────────────────────────────────────────────────────
# Achsen- und Frame-Bestimmung
# ─────────────────────────────────────────────────────────────

def find_rotation_axis(shape) -> Tuple[Tuple[float, float, float],
                                       Tuple[float, float, float]]:
    """
    Bestimmt Massenschwerpunkt und Rotationsachse über die Hauptträgheitsachsen.

    Für ein (näherungsweise) rotationssymmetrisches Bauteil sind zwei der drei
    Hauptträgheitsmomente nahezu gleich (die Ebene senkrecht zur Achse); die
    verbleibende Achse ist die Rotationsachse — unabhängig davon, ob das Teil
    flach (Scheibe) oder lang (Ritzel/Schnecke) ist.
    """
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    com = props.CentreOfMass()
    pp = props.PrincipalProperties()
    axes = [pp.FirstAxisOfInertia(), pp.SecondAxisOfInertia(), pp.ThirdAxisOfInertia()]
    moments = list(pp.Moments())

    # Das Achsenpaar mit den ähnlichsten Momenten spannt die Querschnittsebene
    # auf → die dritte (übrige) Achse ist die Rotationsachse.
    pairs = sorted([
        (abs(moments[0] - moments[1]), 2),
        (abs(moments[0] - moments[2]), 1),
        (abs(moments[1] - moments[2]), 0),
    ])
    d = axes[pairs[0][1]]
    n = math.sqrt(d.X() ** 2 + d.Y() ** 2 + d.Z() ** 2) or 1.0
    return (com.X(), com.Y(), com.Z()), (d.X() / n, d.Y() / n, d.Z() / n)


def _orthonormal_frame(axis: Tuple[float, float, float]):
    """Zwei zur Achse senkrechte Einheitsvektoren (u, v)."""
    tmp = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = (axis[1] * tmp[2] - axis[2] * tmp[1],
         axis[2] * tmp[0] - axis[0] * tmp[2],
         axis[0] * tmp[1] - axis[1] * tmp[0])
    un = math.sqrt(sum(c * c for c in u)) or 1.0
    u = (u[0] / un, u[1] / un, u[2] / un)
    v = (axis[1] * u[2] - axis[2] * u[1],
         axis[2] * u[0] - axis[0] * u[2],
         axis[0] * u[1] - axis[1] * u[0])
    return u, v


def _axial_extent(shape, com, axis) -> Tuple[float, float, float]:
    """(z_min, z_max, r_max) der Eckpunkte entlang der Achse (Achs-Koordinate)."""
    exp = TopExp_Explorer(shape, TopAbs_VERTEX)
    zmin, zmax, rmax = math.inf, -math.inf, 0.0
    u, v = _orthonormal_frame(axis)
    while exp.More():
        p = BRep_Tool.Pnt(topods.Vertex(exp.Current()))
        d = (p.X() - com[0], p.Y() - com[1], p.Z() - com[2])
        z = d[0] * axis[0] + d[1] * axis[1] + d[2] * axis[2]
        pu = d[0] * u[0] + d[1] * u[1] + d[2] * u[2]
        pv = d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
        r = math.sqrt(pu * pu + pv * pv)
        zmin, zmax, rmax = min(zmin, z), max(zmax, z), max(rmax, r)
        exp.Next()
    if zmin == math.inf:
        return 0.0, 0.0, 0.0
    return zmin, zmax, rmax


# ─────────────────────────────────────────────────────────────
# Querschnitt → Radialprofil
# ─────────────────────────────────────────────────────────────

def _section_points(shape, com, axis, u, v, z0, spacing) -> List[Tuple[float, float]]:
    """Planarer Schnitt bei Achs-Koordinate z0 → Liste von (r, θ) der Schnittkanten."""
    base = gp_Pnt(com[0] + z0 * axis[0], com[1] + z0 * axis[1], com[2] + z0 * axis[2])
    sec = BRepAlgoAPI_Section(shape, gp_Pln(base, gp_Dir(*axis)), False)
    sec.ComputePCurveOn1(False)
    sec.Approximation(False)
    sec.Build()
    pts: List[Tuple[float, float]] = []
    exp = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while exp.More():
        edge = topods.Edge(exp.Current())
        try:
            curve = BRepAdaptor_Curve(edge)
            length = GCPnts_AbscissaPoint.Length(curve)
            nsamp = max(6, int(length / spacing) + 1)
            t0, t1 = curve.FirstParameter(), curve.LastParameter()
            for i in range(nsamp):
                t = t0 + (t1 - t0) * i / (nsamp - 1)
                p = curve.Value(t)
                d = (p.X() - com[0], p.Y() - com[1], p.Z() - com[2])
                pu = d[0] * u[0] + d[1] * u[1] + d[2] * u[2]
                pv = d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
                pts.append((math.sqrt(pu * pu + pv * pv), math.atan2(pv, pu)))
        except Exception as exc:  # noqa: BLE001
            _log.debug("Section edge sampling failed @z=%.3f: %s", z0, exc)
        exp.Next()
    return pts


def _radial_split(pts: List[Tuple[float, float]]) -> Optional[float]:
    """
    Findet den Radius-Schwellwert, der die innere Materialgruppe (Bohrung, Nabe)
    von der äußeren (Zahnkranz/Felge) trennt — die größte radiale Lücke in der
    Punkteverteilung. Gibt None zurück, wenn keine signifikante Lücke existiert.

    Ohne diese Trennung "gewinnt" die Bohrung in Winkel-Bins, in denen die äußere
    Kontur keinen Abtastpunkt hat, und verfälscht das Außenprofil.
    """
    radii = sorted(r for r, _ in pts)
    if len(radii) < 8:
        return None
    rmax = radii[-1]
    best_gap, thr = 0.0, None
    for a, b in zip(radii, radii[1:]):
        if b < 0.15 * rmax or a > 0.85 * rmax:
            continue
        if b - a > best_gap:
            best_gap, thr = b - a, 0.5 * (a + b)
    if thr is not None and best_gap > 0.10 * rmax:
        return thr
    return None


def _radial_profile(pts: List[Tuple[float, float]], NA: int, outer: bool):
    """
    Baut das Radialprofil r(θ) über NA Winkel-Bins.

    outer=True  → äußere Hülle (max r je Bin)  — Außenverzahnung / Kopfkreis
    outer=False → innere Hülle (min r je Bin)  — Innenverzahnung / Bohrung

    Innere/äußere Materialgruppen werden vorab über die größte radiale Lücke
    getrennt, damit die Bohrung das Außenprofil nicht verfälscht.

    Gibt (profil, coverage) zurück; leere Bins werden zirkulär interpoliert.
    """
    thr = _radial_split(pts)
    if thr is not None:
        pts = [(r, th) for r, th in pts if (r >= thr if outer else r <= thr)]
    if not pts:
        return None, 0.0
    grid: List[Optional[float]] = [None] * NA
    for r, th in pts:
        ia = int((th + math.pi) / (2 * math.pi) * NA) % NA
        cur = grid[ia]
        if cur is None or (r > cur if outer else r < cur):
            grid[ia] = r
    filled = sum(1 for x in grid if x is not None)
    if filled == 0:
        return None, 0.0
    coverage = filled / NA
    for _ in range(3):
        for i in range(NA):
            if grid[i] is None:
                left = grid[(i - 1) % NA]
                grid[i] = left if left is not None else grid[(i + 1) % NA]
    if any(x is None for x in grid):
        return None, coverage
    return grid, coverage


def _count_periods(prof: List[float], rel_min: float = 0.02) -> Tuple[int, float]:
    """
    Zählt die Perioden (Zähne) im Radialprofil über Schwellwert-Übergänge mit
    Hysterese. Gibt (Periodenzahl, Amplitude) zurück.

    Ein glatter Kreis (Bohrung, Nabe, Felgenrand) hat eine verschwindend kleine
    relative Amplitude und liefert daher 0 Perioden — nur eine echte Verzahnung
    mit Amplitude ≥ rel_min·r_mittel wird gezählt.
    """
    lo, hi = min(prof), max(prof)
    amp = hi - lo
    mean = sum(prof) / len(prof)
    if mean <= 0 or amp < rel_min * mean:
        return 0, amp
    NA = len(prof)
    thr_hi, thr_lo = lo + 0.6 * amp, lo + 0.4 * amp
    state, count = "lo", 0
    for i in range(NA * 2):
        x = prof[i % NA]
        if state == "lo" and x > thr_hi:
            count += 1
            state = "hi"
        elif state == "hi" and x < thr_lo:
            state = "lo"
    return count // 2, amp


# ─────────────────────────────────────────────────────────────
# Zahnkranz-Band (längster Lauf konstanter Zähnezahl)
# ─────────────────────────────────────────────────────────────

def _median(xs: List[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _stdev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _percentile(xs: List[float], p: float) -> float:
    """p-Perzentil (0..1) einer Werteliste."""
    if not xs:
        return 0.0
    s = sorted(xs)
    k = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[k]


def _stratified_order(n: int) -> List[int]:
    """
    Bearbeitungsreihenfolge der Schnitt-Indizes [0..n-1], die bei JEDEM Präfix die
    gesamte Achslänge möglichst gleichmäßig abdeckt (rekursive Halbierung: erst die
    Enden/Mitte, dann progressiv feiner).

    Wichtig für die Robustheit unter Last: Bei achsparalleler Reihenfolge liegt der
    Zahnkranz oft in der zweiten Längenhälfte; ein zeitbedingter Abbruch verfehlt ihn
    dann komplett (→ kein Band → Heuristik-Müll). In stratifizierter Reihenfolge ist
    auch ein abgebrochener Lauf über die ganze Länge verteilt — der Zahnkranz wird
    (nur gröber) immer noch getroffen.
    """
    order: List[int] = []
    seen = set()
    step = n
    while step > 1:
        step = max(1, step // 2)
        for i in range(0, n, step):
            if i not in seen:
                order.append(i)
                seen.add(i)
    for i in range(n):                      # Rest auffüllen (Vollständigkeit)
        if i not in seen:
            order.append(i)
            seen.add(i)
    return order


def _profile_asymmetry(prof: List[float]) -> float:
    """
    Asymmetrie-Maß des Radialprofils r(θ): Verhältnis der mittleren Anstiegs-
    zur mittleren Abfall-Schrittweite (bzw. umgekehrt).

    Ein SÄGEZAHN (Ratschenrad) hat eine sanfte Rampe und eine steile Flanke →
    Verhältnis ≫ 1 (gemessen ~6). Ein symmetrisches Evolventenprofil (Stirn-/
    Kegelrad) hat ~gleiche Flanken → Verhältnis ≈ 1.
    """
    NA = len(prof)
    ups, downs = [], []
    for i in range(NA):
        d = prof[(i + 1) % NA] - prof[i]
        if d > 0:
            ups.append(d)
        elif d < 0:
            downs.append(-d)
    if not ups or not downs:
        return 1.0
    mu, md = sum(ups) / len(ups), sum(downs) / len(downs)
    hi, lo = max(mu, md), min(mu, md)
    return hi / lo if lo > 1e-9 else 1.0


def _longest_band(sections: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    """
    Findet den längsten zusammenhängenden Achsbereich mit konstanter Perioden-
    zahl (sections[i][key] = Periodenzahl). Toleriert einzelne Ausreißer-Sektionen.

    Gibt Dict mit z, i0, i1 oder None zurück.
    """
    n = len(sections)
    best = None
    i = 0
    while i < n:
        z = sections[i][key]
        if z < 4 or z > 400:
            i += 1
            continue
        j = i
        gap = 0
        last_good = i
        while j + 1 < n:
            nxt = sections[j + 1][key]
            if nxt == z:
                j += 1
                last_good = j
                gap = 0
            elif gap == 0 and abs(nxt - z) <= 1:
                # eine einzelne Ausreißer-Sektion überspringen
                j += 1
                gap = 1
            else:
                break
        run_len = last_good - i + 1
        if best is None or run_len > best["len"]:
            best = {"z": z, "i0": i, "i1": last_good, "len": run_len}
        i = last_good + 1
    return best


# ─────────────────────────────────────────────────────────────
# Schrägungswinkel
# ─────────────────────────────────────────────────────────────

def _helix_angle(shape, com, axis, u, v, z_count, r_pitch,
                 z_lo, z_hi, spacing, NA) -> Optional[float]:
    """
    Schrägungswinkel β über Kreuzkorrelation zweier Querschnittsprofile mit
    kleiner Achs-Basislinie. Der Suchbereich ist auf ±½ Zahnteilung begrenzt,
    um Aliasing (Verwechslung mit der Nachbarlücke) zu vermeiden.
    """
    if z_count <= 0 or r_pitch <= 0:
        return None
    # Basislinie klein genug für bis ~35° Schrägung ohne Aliasing
    span = z_hi - z_lo
    za = z_lo + 0.35 * span
    zb = z_lo + 0.65 * span
    dz = zb - za
    if dz < 1e-6:
        return None

    pa, _ = _radial_profile(_section_points(shape, com, axis, u, v, za, spacing), NA, True)
    pb, _ = _radial_profile(_section_points(shape, com, axis, u, v, zb, spacing), NA, True)
    if pa is None or pb is None:
        return None

    ma, mb = sum(pa) / NA, sum(pb) / NA
    na = [x - ma for x in pa]
    nb = [x - mb for x in pb]
    half_pitch = max(1, int(NA / (2 * z_count)))

    best_k, best_c = 0, -math.inf
    for k in range(-half_pitch, half_pitch + 1):
        c = sum(na[i] * nb[(i + k) % NA] for i in range(NA))
        if c > best_c:
            best_c, best_k = c, k
    d_theta = best_k * 2 * math.pi / NA
    beta = math.degrees(math.atan(r_pitch * abs(d_theta) / dz))
    return round(beta, 1)


# ─────────────────────────────────────────────────────────────
# Hauptfunktion
# ─────────────────────────────────────────────────────────────

def _round_module(m_raw: float) -> Tuple[float, bool]:
    """
    Rundet auf das nächste Normmodul — metrisch (DIN 780) ODER zöllig
    (Diametral Pitch, m = 25.4/DP). Gibt (modul, war_norm) zurück.
    """
    if m_raw <= 0:
        return 0.0, False
    m_norm = min(ALL_MODULES, key=lambda m: abs(m - m_raw))
    if abs(m_raw - m_norm) / m_norm <= 0.12:
        return m_norm, True
    return round(m_raw, 3), False


def extract_metrology(shape, n_sections: int = 48, NA: int = 720,
                      time_budget_s: float = 120.0) -> Dict[str, Any]:
    """
    Vermisst die Verzahnung über planare Querschnitte. Gibt ein Dict zurück:

        ok                : True, wenn ein Zahnkranz gefunden wurde
        num_teeth         : z (direkt gezählt)
        is_internal       : Innenverzahnung?
        tip_diameter_mm   : d_a
        root_diameter_mm  : d_f
        module_mm         : m (auf DIN 780 gerundet)
        module_is_norm    : True wenn m einem Normmodul entspricht
        pitch_diameter_mm : d = m·z
        face_width_mm     : b (axiale Ausdehnung des Zahnkranzes)
        helix_angle_deg   : β
        bore_diameter_mm  : kleinste durchgehende Innenbohrung
        is_bevel          : Kegelrad?
        cone_angle_deg    : Kopfkegelwinkel (nur Kegelrad)
        axis, com         : Rotationsachse / Schwerpunkt
    """
    result: Dict[str, Any] = {"ok": False}
    try:
        com, axis = find_rotation_axis(shape)
        u, v = _orthonormal_frame(axis)
        zmin, zmax, rmax = _axial_extent(shape, com, axis)
        length = zmax - zmin
        if length <= 1e-6 or rmax <= 1e-6:
            return result

        result["axis"] = axis
        result["com"] = com

        # Sampling-Abstand entlang der Schnittkanten ~ feine Winkelauflösung
        spacing = max(0.03, 2 * math.pi * rmax / 1000)

        # Performance-Schutz: Jeder exakte Schnitt (BRepAlgoAPI_Section) ist bei
        # großen/komplexen B-Reps teuer — und der TEUERSTE Bereich ist der Zahnkranz
        # (viele Schnittkanten je Schnitt), nicht die glatte Nabe. Daher die Kosten
        # an MEHREREN Positionen messen und das MAXIMUM verwenden. Eine einzelne
        # Probe in der Nabe unterschätzt die Kosten sonst grob: die Schnittzahl
        # bleibt zu hoch, der Lauf läuft ins Zeitlimit und bricht MITTEN im Zahnkranz
        # ab → zu kurzes Band → Vermessung schlägt fehl → schlechter Heuristik-Fallback.
        t_start = time.time()
        probe_costs = []
        for frac in (0.3, 0.5, 0.7):
            tp = time.time()
            _section_points(shape, com, axis, u, v, zmin + frac * length, spacing)
            probe_costs.append(time.time() - tp)
        sec_cost = max(1e-3, max(probe_costs))
        if sec_cost * n_sections > time_budget_s:
            n_sections = int(time_budget_s / sec_cost)
        # Unter-/Obergrenze: genug Schnitte für ein belastbares Band, aber gedeckelt.
        n_sections = max(MIN_SECTIONS, min(n_sections, MAX_SECTIONS))

        # Querschnitte über die Länge legen — in STRATIFIZIERTER Reihenfolge, damit
        # ein Sicherheits-Abbruch (Zeitlimit unter Last) die Achse trotzdem
        # gleichmäßig abdeckt und den Zahnkranz nicht verfehlt. Nach dem Sammeln
        # wieder nach Achs-Koordinate sortieren (die Bandbildung braucht z-Ordnung).
        sections: List[Dict[str, Any]] = []
        hard_deadline = time_budget_s * 2.5
        for i in _stratified_order(n_sections):
            if time.time() - t_start > hard_deadline:
                _log.warning("Sicherheits-Stopp der Vermessung nach %d Schnitten",
                             len(sections))
                break
            z0 = zmin + length * (i + 0.5) / n_sections
            pts = _section_points(shape, com, axis, u, v, z0, spacing)
            if not pts:
                continue
            outer_prof, cov_o = _radial_profile(pts, NA, outer=True)
            inner_prof, _ = _radial_profile(pts, NA, outer=False)
            entry: Dict[str, Any] = {"z": z0}
            # Sanity-Obergrenze: ein Zahn muss genug Winkel-Bins überspannen,
            # um zuverlässig gezählt zu werden (verhindert Hochfrequenz-Artefakte).
            max_z = NA // 6
            if outer_prof is not None:
                z_out, amp_out = _count_periods(outer_prof)
                entry["z_out"] = z_out if z_out <= max_z else 0
                entry["ra_out"] = max(outer_prof)
                entry["rf_out"] = min(outer_prof)
                entry["amp_out"] = amp_out
                entry["asym_out"] = _profile_asymmetry(outer_prof)
            else:
                entry["z_out"] = 0
            if inner_prof is not None:
                z_in, amp_in = _count_periods(inner_prof)
                entry["z_in"] = z_in if z_in <= max_z else 0
                entry["ra_in"] = min(inner_prof)   # Kopfkreis innen = kleinster r
                entry["rf_in"] = max(inner_prof)
                entry["amp_in"] = amp_in
            else:
                entry["z_in"] = 0
            # Innenradius (Bohrungskandidat): kleinster r überhaupt
            entry["r_inner"] = min(r for r, _ in pts)
            sections.append(entry)

        if not sections:
            return result

        # Nach Achs-Koordinate sortieren (stratifizierte Mess-Reihenfolge aufheben),
        # damit _longest_band zusammenhängende Achsbereiche korrekt erkennt.
        sections.sort(key=lambda s: s["z"])

        # Außenverzahnung hat Vorrang: Eine Außenverzahnung zeigt den Zahnkranz
        # als äußere Hülle. Nur wenn KEIN belastbares Außenband existiert (glatter
        # Felgenrand), wird auf Innenverzahnung geprüft.
        band_out = _longest_band(sections, "z_out")
        band_in = _longest_band(sections, "z_in")

        use_internal = (band_out is None or band_out["len"] < 3) and \
                       (band_in is not None and band_in["len"] >= 3)
        band = band_in if use_internal else band_out
        if band is None or band["len"] < 3:
            return result

        i0, i1 = band["i0"], band["i1"]
        z_count = band["z"]
        band_sec = sections[i0:i1 + 1]

        if use_internal:
            tip_radii  = [s["ra_in"] for s in band_sec if "ra_in" in s]
            root_radii = [s["rf_in"] for s in band_sec if "rf_in" in s]
        else:
            tip_radii  = [s["ra_out"] for s in band_sec if "ra_out" in s]
            root_radii = [s["rf_out"] for s in band_sec if "rf_out" in s]
        tip_r = _median(tip_radii)
        root_r = _median(root_radii)

        # Kegel-/Gehrungsrad-Erkennung über ZWEI Signale:
        #  1) Kopfradius ändert sich linear über die Breite (konische Flanke),
        #  2) ein echter Kopfkegel (koaxiale Kegelfläche) liefert γ.
        # Signal 2 fängt auch SPIRAL-Kegelräder, bei denen Signal 1 versagt.
        # Hinweis: _bevel_pitch_angle liefert den GRÖSSTEN koaxialen Kegel; bei
        # flachen Achswinkeln Σ<90° (Gehrungsrad, γ<45°) ist das der RÜCKENKEGEL
        # 90°−γ. Diese Mehrdeutigkeit löst geometry_analyzer für Gehrungsräder über
        # γ = min(γ_occ, 90°−γ_occ) auf (klassische Kegelräder mit γ>45° bleiben
        # unberührt — dort ist der größte Kegel der Kopfkegel).
        is_bevel, cone_angle = False, None     # cone_angle = Kopf-/Mantelkegel (für b)
        tip_r_outer = _percentile(tip_radii, 0.95)
        _bevel_cone = _bevel_pitch_angle(shape, com, axis, 2 * tip_r_outer)
        gamma = _bevel_cone[0] if _bevel_cone else None      # Teilkegelwinkel (≈)
        gamma_dr = _bevel_cone[1] if _bevel_cone else None   # radiale Kopfkegel-Spanne
        if len(tip_radii) >= 4:
            slope = _linfit_slope([s["z"] for s in band_sec], tip_radii)
            if abs(slope) > math.tan(math.radians(8)):
                is_bevel = True
                cone_angle = round(math.degrees(math.atan(abs(slope))), 2)
                snapped = _snap_cone_angle_to_occ(shape, com, axis, cone_angle)
                if snapped is not None:
                    cone_angle = snapped
        if gamma is not None:
            is_bevel = True   # Kopfkegel gefunden → sicher Kegelrad (auch Spiral)

        # Kopfkreisdurchmesser: beim Kegelrad zählt der GROSSE Rand am großen Ende
        # → oberes Perzentil; beim Zylinderrad der Median.
        if is_bevel:
            d_a = round(2 * tip_r_outer, 4)
        else:
            d_a = round(2 * tip_r, 4)
        d_f = round(2 * root_r, 4)

        # Modul:
        #  • Kegelrad mit Teilkegelwinkel γ: d_a = m·z + 2·m·cos γ
        #    → m = d_a/(z + 2·cos γ)  (herstellerunabhängig, beliebige Kegelwinkel)
        #  • sonst: Zahnhöhe + Kopfformel (Zylinderrad-Näherung)
        if is_bevel and gamma is not None:
            m_raw = d_a / (z_count + 2 * math.cos(math.radians(gamma)))
            module_mm, is_norm = _round_module(m_raw)
        else:
            m_from_height = abs(d_a - d_f) / 4.5        # h_gesamt = 2.25·m → Δd = 4.5·m
            m_from_tip = d_a / (z_count + 2) if not use_internal else d_a / (z_count - 2)
            m_raw = 0.5 * (m_from_height + m_from_tip)
            module_mm, is_norm = _round_module(m_raw)

        pitch_d = round(module_mm * z_count, 4)

        # Zahnbreite = axiale Ausdehnung der VOLL ausgeprägten Zahnlücken.
        # Bei Zahnauslauf (Hinterschnitt/Werkzeugauslauf) füllen sich die Lücken
        # allmählich; nur der volltiefe Bereich (rf nahe Fußkreis) zählt als Breite.
        rf_key = "rf_in" if use_internal else "rf_out"
        rfs = [s[rf_key] for s in band_sec if rf_key in s]
        dz_sec = length / n_sections
        face_width = round((band_sec[-1]["z"] - band_sec[0]["z"]) + dz_sec, 4)
        if rfs:
            rf_sorted = sorted(rfs)
            rf_base = rf_sorted[max(0, int(len(rf_sorted) * 0.05))]
            # volltief = Lückengrund ≥ 96 % der vollen Zahntiefe
            thr = rf_base + 0.04 * (tip_r - rf_base)
            # längster zusammenhängender volltiefer Lauf im Band
            best_lo, best_hi, cur_lo = None, None, None
            for k, s in enumerate(band_sec):
                if s.get(rf_key, 1e9) <= thr:
                    if cur_lo is None:
                        cur_lo = k
                    if best_lo is None or (k - cur_lo) > (best_hi - best_lo):
                        best_lo, best_hi = cur_lo, k
                else:
                    cur_lo = None
            if best_lo is not None and best_hi > best_lo:
                face_width = round(
                    (band_sec[best_hi]["z"] - band_sec[best_lo]["z"]) + dz_sec, 4
                )

        # Zylinder-Zahnrad: Die Zahnflanken-Flächen liefern die GESCHNITTENE
        # Zahnbreite exakter als das Querschnitt-Plateau (das den Werkzeugauslauf
        # mitzählt). Wenn genug Flankenflächen gefunden werden, hat das Vorrang.
        if not is_bevel:
            fw_flank = _face_width_from_flanks(shape, com, axis, root_r, tip_r, z_count)
            if fw_flank is not None:
                face_width = fw_flank

        # Kegelrad-Zahnbreite: Die Zähne laufen ENTLANG der Kegelmantellinie. Die
        # radiale Spanne des Kopfkegels (Ferse→Zehe) ist ΔR = b·sin γ, also
        # b = ΔR / sin γ — robust auch bei flachen Kegeln, wo das achsnormale
        # Querschnitt-Plateau kollabiert. Sonst Rückfall auf b_axial/cos(Mantelkegel).
        if is_bevel and gamma is not None and gamma_dr and gamma_dr > 0:
            sin_g = math.sin(math.radians(gamma))
            if sin_g > 1e-6:
                face_width = round(gamma_dr / sin_g, 4)
        elif is_bevel and cone_angle is not None:
            face_width = round(face_width / math.cos(math.radians(cone_angle)), 4)

        # Schrägungswinkel
        r_pitch = pitch_d / 2 if pitch_d else tip_r
        helix = _helix_angle(shape, com, axis, u, v, z_count, r_pitch,
                             band_sec[0]["z"], band_sec[-1]["z"], spacing, NA)

        # Bohrung: kleinster stabiler Innenradius außerhalb des Zahnkranzes
        bore_d = _detect_bore(sections, i0, i1, root_r)

        # Nabe (Naben-Ø + -Breite) — koaxialer Absatz zwischen Bohrung und Kranz
        hub_dia, hub_w = _detect_hub(shape, com, axis, d_a, d_f, bore_d)

        # Ratschenrad: stark ASYMMETRISCHE (Sägezahn-)Kontur — sanfte Rampe,
        # steile Flanke. Nur bei Außenverzahnung ohne Kegel prüfen.
        is_ratchet = False
        if not is_bevel and not use_internal:
            asyms = [s["asym_out"] for s in band_sec if "asym_out" in s]
            if asyms and _median(asyms) >= 2.5:
                is_ratchet = True

        result.update({
            "ok": True,
            "num_teeth": int(z_count),
            "is_internal": bool(use_internal),
            "tip_diameter_mm": d_a,
            "root_diameter_mm": d_f,
            "module_mm": module_mm,
            "module_is_norm": is_norm,
            "pitch_diameter_mm": pitch_d,
            "face_width_mm": face_width,
            "helix_angle_deg": helix,
            "bore_diameter_mm": bore_d,
            "hub_diameter_mm": hub_dia,
            "hub_width_mm": hub_w,
            "is_bevel": is_bevel,
            "is_ratchet": is_ratchet,
            "cone_angle_deg": gamma if gamma is not None else cone_angle,
            # Gesamtbreite = axiale Ausdehnung ENTLANG der gemessenen Achse
            # (robust gegen Bauteil-Orientierung; die globale Bounding-Box-Z
            # liefert bei gekippten/kegeligen Teilen den Durchmesser statt b).
            "overall_width_mm": round(length, 4),
            "band_sections": band["len"],
            "total_sections": len(sections),
        })
        return result

    except Exception as exc:  # noqa: BLE001
        _log.warning("Metrologie fehlgeschlagen: %s", exc)
        return result


def _linfit_slope(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0
    return (n * sxy - sx * sy) / denom


def _snap_cone_angle_to_occ(shape, com, axis, target_deg: float,
                            tol_deg: float = 10.0) -> Optional[float]:
    """
    Verfeinert einen grob geschätzten Kegelwinkel (aus der verrauschten
    Kopfradius-Bandsteigung) auf den EXAKTEN Halbwinkel der nächstgelegenen
    koaxialen OCC-Kegelfläche.

    Robustheit: Es werden nur Kegelflächen berücksichtigt, deren Achse parallel
    zur Radachse liegt UND deren Spitze auf der Achse sitzt (echte Kopf-/Fuß-/
    Mantelkegel, keine Zahnflanken-Facetten). Aus diesen wird der flächengrößte
    Kandidat gewählt, dessen Halbwinkel höchstens `tol_deg` vom Schätzwert
    abweicht — so kann kein völlig falscher Kegel gegriffen werden, der Wert
    stammt aber aus der exakten B-Rep statt aus einem verrauschten Fit.

    Gibt den exakten Halbwinkel (Grad) zurück oder None, wenn keine passende
    Kegelfläche existiert (dann bleibt der Bandschätzwert gültig).
    """
    try:
        best_angle, best_area = None, -1.0
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            face = topods.Face(exp.Current())
            try:
                surf = BRepAdaptor_Surface(face)
                if surf.GetType() == GeomAbs_Cone:
                    cone = surf.Cone()
                    axd = cone.Axis().Direction()
                    dot = abs(axd.X() * axis[0] + axd.Y() * axis[1] + axd.Z() * axis[2])
                    if dot >= 0.98:                         # koaxial zur Radachse
                        apex = cone.Apex()
                        d = (apex.X() - com[0], apex.Y() - com[1], apex.Z() - com[2])
                        zc = d[0] * axis[0] + d[1] * axis[1] + d[2] * axis[2]
                        apex_r = math.sqrt(max(0.0, d[0]**2 + d[1]**2 + d[2]**2 - zc**2))
                        semi = abs(math.degrees(cone.SemiAngle()))
                        if apex_r < 0.5 and abs(semi - target_deg) <= tol_deg:
                            gp = GProp_GProps()
                            brepgprop.SurfaceProperties(face, gp)
                            area = gp.Mass()
                            if area > best_area:
                                best_area, best_angle = area, semi
            except Exception:  # noqa: BLE001 — einzelne Fläche darf nicht abbrechen
                pass
            exp.Next()
        return round(best_angle, 2) if best_angle is not None else None
    except Exception as exc:  # noqa: BLE001
        _log.debug("Kegelwinkel-Snapping fehlgeschlagen: %s", exc)
        return None


def _bevel_pitch_angle(shape, com, axis, d_a: float) -> Optional[Tuple[float, float]]:
    """
    Teilkegelwinkel γ eines Kegelrads — direkt aus dem Kopfkegel (Stirnkegel).

    Die Zahnköpfe eines Kegelrads liegen auf dem Kopfkegel, dessen Halbwinkel
    (zur Achse) ≈ dem Teilkegelwinkel γ ist. Unter den koaxialen, achsspitzen-
    zentrierten Kegelflächen mit Bezugsradius ≈ d_a/2 (am großen Ende / Ferse)
    ist der Kopfkegel derjenige mit dem GRÖSSTEN Halbwinkel — der flache
    Außen-/Rohteilkegel hat einen kleinen, der Kopfkegel den großen.

    Damit wird das Modul herstellerunabhängig korrekt:
        d_a = m·z + 2·m·cos γ   →   m = d_a / (z + 2·cos γ)
    (die alte Spurrad-Näherung m=(d_a−d_f)/4.5 gilt am Kegel nicht).

    Gibt (γ in Grad, ΔR) zurück — ΔR = radiale Ausdehnung der Kopfkegelfläche
    (Ferse→Zehe), woraus die Zahnbreite b = ΔR / sin γ folgt. None, wenn kein
    Kopfkegel gefunden wird (dann greift die alte Heuristik).
    """
    if d_a <= 0:
        return None
    target_r = d_a / 2.0
    try:
        best_semi, best_dr = None, 0.0
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            face = topods.Face(exp.Current())
            try:
                surf = BRepAdaptor_Surface(face)
                if surf.GetType() == GeomAbs_Cone:
                    cone = surf.Cone()
                    axd = cone.Axis().Direction()
                    dot = abs(axd.X() * axis[0] + axd.Y() * axis[1] + axd.Z() * axis[2])
                    if dot >= 0.98:
                        apex = cone.Apex()
                        d = (apex.X() - com[0], apex.Y() - com[1], apex.Z() - com[2])
                        zc = d[0] * axis[0] + d[1] * axis[1] + d[2] * axis[2]
                        apex_r = math.sqrt(max(0.0, d[0]**2 + d[1]**2 + d[2]**2 - zc**2))
                        semi = abs(math.degrees(cone.SemiAngle()))
                        ref = cone.RefRadius()
                        if (apex_r < 0.5 and abs(ref - target_r) <= 0.06 * target_r
                                and 25.0 <= semi <= 88.0):
                            # Radiale Ausdehnung der Fläche aus den Eckpunkten: Ein
                            # echter Kopfkegel reicht von der Ferse (groß) zur Zehe
                            # (klein) → große Spanne. Eine Kopf-FASE eines Zylinder-
                            # rads ist nur ein dünner Ring → wird verworfen.
                            ve = TopExp_Explorer(face, TopAbs_VERTEX)
                            rmin, rmax = math.inf, -math.inf
                            while ve.More():
                                p = BRep_Tool.Pnt(topods.Vertex(ve.Current()))
                                dd = (p.X()-com[0], p.Y()-com[1], p.Z()-com[2])
                                zz = dd[0]*axis[0]+dd[1]*axis[1]+dd[2]*axis[2]
                                rr = math.sqrt(max(0.0, dd[0]**2+dd[1]**2+dd[2]**2 - zz*zz))
                                rmin, rmax = min(rmin, rr), max(rmax, rr)
                                ve.Next()
                            if rmax - rmin >= 0.15 * target_r:
                                if best_semi is None or semi > best_semi:
                                    best_semi = semi
                                    best_dr = rmax - rmin
            except Exception:  # noqa: BLE001
                pass
            exp.Next()
        return (round(best_semi, 2), round(best_dr, 4)) if best_semi is not None else None
    except Exception as exc:  # noqa: BLE001
        _log.debug("Teilkegelwinkel-Bestimmung fehlgeschlagen: %s", exc)
        return None


def _face_width_from_flanks(shape, com, axis, root_r: float, tip_r: float,
                            z_count: int) -> Optional[float]:
    """
    Zahnbreite aus der axialen Ausdehnung der Zahnflanken-Flächen.

    Die Flankenflächen eines Zylinder-Zahnrads erstrecken sich radial über die
    gesamte Zahnhöhe (Fuß→Kopf) und axial über die GESCHNITTENE Zahnbreite. Der
    Werkzeugauslauf (Hinterschnitt) liegt auf SEPARATEN, längeren Flächen.

    In der Praxis bilden die Flächen im Zahnhöhen-Band mehrere Längen-Cluster:
    die echten Flanken (= Schnitttiefe, ~2 Flächen je Zahn) und längere
    Auslauf-/Übergangsflächen. Die Schnitttiefe ist der NIEDRIGSTE dichte
    Cluster (Auslauf verlängert nur), der mindestens ~z Flächen enthält.

    Gibt diese Zahnbreite zurück oder None (dann gilt der Querschnitt-Schätzwert).
    """
    tooth_h = tip_r - root_r
    if tooth_h <= 1e-6:
        return None
    r_lo = root_r + 0.30 * tooth_h     # Flanke reicht von nahe Fußkreis …
    r_hi = tip_r - 0.30 * tooth_h      # … bis nahe Kopfkreis
    spans: List[float] = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods.Face(exp.Current())
        ve = TopExp_Explorer(face, TopAbs_VERTEX)
        rmin, rmax, zmn, zmx, seen = math.inf, -math.inf, math.inf, -math.inf, False
        while ve.More():
            p = BRep_Tool.Pnt(topods.Vertex(ve.Current()))
            d = (p.X() - com[0], p.Y() - com[1], p.Z() - com[2])
            z = d[0] * axis[0] + d[1] * axis[1] + d[2] * axis[2]
            rr = math.sqrt(max(0.0, d[0]**2 + d[1]**2 + d[2]**2 - z * z))
            rmin, rmax = min(rmin, rr), max(rmax, rr)
            zmn, zmx = min(zmn, z), max(zmx, z)
            seen = True
            ve.Next()
        # Flankenkriterium: überspannt die Zahnhöhe radial UND ist axial länger
        # als die Zahnhöhe (schließt Stirn-/Fasen-/kurze Flächen aus).
        if seen and rmin <= r_lo and rmax >= r_hi and (zmx - zmn) > tooth_h:
            spans.append(zmx - zmn)
        exp.Next()

    if len(spans) < max(4, z_count // 2):
        return None

    # Niedrigsten dichten Cluster suchen: kleinstes Fenster (Breite 0.3 mm), das
    # mindestens ~z/2 Flächen enthält → die echte Schnitttiefe (Flanken).
    spans.sort()
    win = 0.3
    need = max(4, z_count // 2)
    for i, lo in enumerate(spans):
        in_win = [s for s in spans[i:] if s <= lo + win]
        if len(in_win) >= need:
            return round(_median(in_win), 4)
    return None


def _detect_hub(shape, com, axis, d_a: float, d_f: float,
                bore_d: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """
    Nabe (Hub) = koaxiale Zylinderfläche zwischen Bohrung und Zahnkranz, die als
    Absatz/Buchse axial heraussteht. Sucht unter den koaxialen Zylindern den
    prominentesten Kandidaten:
      - Durchmesser zwischen Bohrung und ~0.92·d_a (nicht Kopf-/Außenzylinder),
      - NICHT nahe dem Fußkreis d_f (das wäre der Zahnfuß-Zylinder),
      - nennenswerte axiale Ausdehnung.
    Gibt (Nabendurchmesser, Nabenbreite) zurück, sonst (None, None).
    """
    lo = (bore_d * 1.3) if bore_d else 0.0
    hi = 0.92 * d_a
    # je Durchmesser die größte axiale Ausdehnung einer Zylinderfläche merken
    cyl: Dict[float, float] = {}
    try:
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            face = topods.Face(exp.Current())
            try:
                surf = BRepAdaptor_Surface(face)
                if surf.GetType() == GeomAbs_Cylinder:
                    c = surf.Cylinder()
                    axd = c.Axis().Direction()
                    if abs(axd.X()*axis[0] + axd.Y()*axis[1] + axd.Z()*axis[2]) >= 0.98:
                        dia = round(2 * c.Radius(), 2)
                        ve = TopExp_Explorer(face, TopAbs_VERTEX)
                        zs = []
                        while ve.More():
                            p = BRep_Tool.Pnt(topods.Vertex(ve.Current()))
                            d = (p.X()-com[0], p.Y()-com[1], p.Z()-com[2])
                            zs.append(d[0]*axis[0] + d[1]*axis[1] + d[2]*axis[2])
                            ve.Next()
                        if zs:
                            ext = max(zs) - min(zs)
                            cyl[dia] = max(cyl.get(dia, 0.0), ext)
            except Exception:  # noqa: BLE001
                pass
            exp.Next()
    except Exception as exc:  # noqa: BLE001
        _log.debug("Naben-Erkennung fehlgeschlagen: %s", exc)
        return None, None

    cands = [(dia, ext) for dia, ext in cyl.items()
             if lo < dia < hi and ext >= 2.0
             and (d_f <= 0 or abs(dia - d_f) > 0.06 * d_f)]
    if not cands:
        return None, None
    # prominenteste Nabe = größter Durchmesser
    hub_dia, hub_w = max(cands, key=lambda x: x[0])
    return round(hub_dia, 4), round(hub_w, 4)


def _detect_bore(sections, i0, i1, root_r) -> Optional[float]:
    """
    Bohrungsdurchmesser = Median des kleinsten Innenradius über die Sektionen,
    die deutlich kleiner als der Fußkreis sind (echte Durchgangsbohrung, nicht
    Madenschraube/Verrundung).
    """
    candidates = [s["r_inner"] for s in sections
                  if "r_inner" in s and s["r_inner"] < root_r * 0.9]
    if len(candidates) < 3:
        return None
    bore_r = _median(candidates)
    return round(2 * bore_r, 4)
