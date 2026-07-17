"""
gear_hints.py
-------------
Wissensbasis für Zahnrad-Typen: Normen, Anwendungen, Fertigung, Qualität und
parametrische Optimierungsempfehlungen.

Wird von geometry_analyzer.py nach der Parameter-Extraktion aufgerufen:
    hints = generate_gear_hints(params)
    params.hints = hints

Optimierungsregeln sind callable: condition(params) → bool.
Schlägt eine Bedingung an, wird der zugehörige Hinweis in die JSON-Ausgabe
aufgenommen. Regeln dürfen nie Exceptions werfen (try/except im Aufrufer).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from output_schema import GearParameters


def _v(field_val: Any) -> Any:
    """Gibt den Rohwert zurück — entpackt ParameterValue oder gibt plain value direkt zurück."""
    return field_val.value if hasattr(field_val, "value") else field_val


# ─────────────────────────────────────────────
# Datenstrukturen
# ─────────────────────────────────────────────

@dataclass
class OptimizationRule:
    condition: Callable          # lambda params: bool
    hint: str
    severity: str = "info"       # "info" | "warning" | "cost"


@dataclass
class GearKnowledge:
    gear_type: str
    norms: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    manufacturing: List[str] = field(default_factory=list)
    quality_checks: List[str] = field(default_factory=list)
    optimization_rules: List[OptimizationRule] = field(default_factory=list)


# ─────────────────────────────────────────────
# Wissensbasis
# ─────────────────────────────────────────────

GEAR_KNOWLEDGE: dict[str, GearKnowledge] = {

    "spur": GearKnowledge(
        gear_type="spur",
        norms=["DIN 867", "DIN ISO 1328-1", "ISO 1122-1", "DIN 3960", "DIN 3961"],
        applications=[
            "Stirnradgetriebe mit parallelen Achsen",
            "Einsatz bis ca. 25 m/s Umfangsgeschwindigkeit (ölgeschmiert bis 50 m/s)",
            "Kraftfahrzeuggetriebe, Industriegetriebe, Werkzeugmaschinen",
            "Einfache Fertigung und Montage; kostengünstigster Verzahnungstyp",
        ],
        manufacturing=[
            "Wälzfräsen (Abwälzfräser / Hob) — Standardverfahren für Außenverzahnung",
            "Wälzstoßen (Stoßrad) — geeignet für Innenverzahnung und enge Räume",
            "Schleifen (Profilschleifen, Wälzschleifen) ab Qualitätsklasse DIN 6 und besser",
            "Räumen für Großserien (z. B. Planetenräder)",
            "Läppen als Feinbearbeitungsverfahren nach dem Härten",
        ],
        quality_checks=[
            "Flankenlinienabweichung Fβ (DIN ISO 1328-1)",
            "Einzelteilungsabweichung fp und Gesamtteilungsabweichung Fp",
            "Profilabweichung Fα (Evolventen-Formabweichung)",
            "Zahnlückenbreite Wnk (über k Zähne)",
            "Oberflächenrauheit der Zahnflanken Ra ≤ 0,8 µm für Qualität 6",
            "Härteeindringtiefe CHD nach Einsatzhärten prüfen",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: (_v(p.num_teeth) or 99) < 17,
                hint=(
                    "z < 17: Unterschnittgefahr bei Standardverzahnung. "
                    "Profilverschiebung x > 0 empfehlen (z. B. x ≈ 1 − z/17). "
                    "Erhöht Zahnfußtragfähigkeit ohne Mehrkosten."
                ),
                severity="warning",
            ),
            OptimizationRule(
                condition=lambda p: (
                    _v(p.face_width_mm) and _v(p.module_mm)
                    and _v(p.face_width_mm) > 0
                    and _v(p.module_mm) > 0
                    and (_v(p.face_width_mm) / _v(p.module_mm)) > 40
                ),
                hint=(
                    "b/m > 40: Zahnbreite sehr groß relativ zum Modul. "
                    "Schrägverzahnung (β = 15–20°) prüfen — reduziert Lärm und "
                    "erhöht Tragfähigkeit ohne signifikante Mehrkosten."
                ),
                severity="cost",
            ),
            OptimizationRule(
                condition=lambda p: (
                    _v(p.face_width_mm) and _v(p.pitch_diameter_mm)
                    and _v(p.pitch_diameter_mm) > 0
                    and _v(p.face_width_mm) > 2.5 * _v(p.pitch_diameter_mm)
                ),
                hint=(
                    "b > 2,5 × d: Sehr große Zahnbreite relativ zum Teilkreis. "
                    "Wellenbiegung kritisch — zweistufige Auslegung oder breitere "
                    "Lagerabstände prüfen."
                ),
                severity="warning",
            ),
            OptimizationRule(
                condition=lambda p: (_v(p.module_mm) or 0) > 8 and (_v(p.num_teeth) or 0) > 30,
                hint=(
                    "Großer Modul (m > 8) bei hoher Zähnezahl: "
                    "Modul reduzieren und z erhöhen spart Material (kleinere Kopfhöhe) "
                    "und verbessert den Eingriffswirkungsgrad."
                ),
                severity="cost",
            ),
        ],
    ),

    "helical": GearKnowledge(
        gear_type="helical",
        norms=["DIN 867", "DIN ISO 1328-1", "ISO 1122-1", "DIN 3960", "DIN 3961"],
        applications=[
            "Parallele Achsen — ruhigerer Lauf als Stirnrad durch gleitenden Eingriff",
            "Höhere Tragfähigkeit als Stirnrad bei gleichen Abmessungen",
            "Kraftfahrzeuggetriebe, Turbogetriebe, Verdichter",
            "Typischer Schrägungswinkel β = 8–20° (Kompromiss Axialkraft / Überdeckung)",
        ],
        manufacturing=[
            "Wälzfräsen mit schrägem Fräser (Schrägungswinkel im Fräserprogramm berücksichtigen)",
            "Wälzschleifen für hohe Qualitätsanforderungen",
            "Axialkraft beachten: Lagerauslegung muss Axialkraft aufnehmen",
        ],
        quality_checks=[
            "Schrägungswinkel β mit Zahnflankenmessgerät prüfen",
            "Flankenlinienabweichung Fβ besonders kritisch bei großem β",
            "Stirnschnittgrößen (Normalkräfte) für Lagerberechnung dokumentieren",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: (_v(p.helix_angle_deg) or 0) > 30,
                hint=(
                    "β > 30°: Hohe Axialkraft (F_ax = F_t × tan β). "
                    "Pfeilverzahnung (Doppelschrägverzahnung, β gespiegelt) erwägen — "
                    "hebt Axialkräfte auf, ermöglicht einfachere Lagerung."
                ),
                severity="warning",
            ),
            OptimizationRule(
                condition=lambda p: (_v(p.helix_angle_deg) or 0) > 0 and (_v(p.helix_angle_deg) or 0) < 8,
                hint=(
                    "β < 8°: Sehr kleiner Schrägungswinkel — Überdeckungsgewinn gering. "
                    "β ≥ 10° empfohlen für spürbaren Lärm- und Tragfähigkeitsvorteil."
                ),
                severity="info",
            ),
        ],
    ),

    "bevel": GearKnowledge(
        gear_type="bevel",
        norms=["DIN 868", "DIN ISO 17485", "ISO 23509", "DIN 3971"],
        applications=[
            "Achsversatz 90° (Standardfall) — auch andere Winkel möglich",
            "Kraftfahrzeug-Differential, Handgetriebe, Mischaggregate",
            "Geradverzahnt (einfach, laut), Schrägverzahnt, Bogenverzahnt (Gleason/Klingelnberg — ruhig)",
            "Bogenverzahnte Kegelräder für hohe Drehzahlen und Leistungen",
        ],
        manufacturing=[
            "Geradverzahnt: Kegelradfräsen (Teilverfahren)",
            "Bogenverzahnt: Gleason-Verfahren (USA) oder Klingelnberg-Verfahren (D/CH)",
            "Läppen als Feinbearbeitung — Laufpaarung wird immer zusammen geläppt",
            "Hochwertige CNC-5-Achs-Bearbeitungszentren für komplexe Geometrien",
        ],
        quality_checks=[
            "Tragbild prüfen (Kontaktfleckenverteilung auf der Zahnflanke)",
            "Kegelabstand Rv und Zahnspiel am montierten Getriebe messen",
            "Paarweise Kennzeichnung: Kegelräder immer als Paar ersetzen",
            "Achsabstandstoleranz im Getriebegehäuse kritisch für Tragbild",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Kegelräder immer als Paar austauschen — "
                    "Laufpaarung ist eingespielt und nicht austauschbar."
                ),
                severity="warning",
            ),
            OptimizationRule(
                condition=lambda p: abs((_v(p.cone_angle_deg) or 45) - 45) > 1.0,
                hint=(
                    "Teilkegelwinkel ≠ 45°: Achswinkel ist nicht 90° bzw. Übersetzung ≠ 1:1. "
                    "Prüfen, ob Getriebe-Gehäuse für diesen Achswinkel ausgelegt ist."
                ),
                severity="info",
            ),
        ],
    ),

    "miter": GearKnowledge(
        gear_type="miter",
        norms=["DIN 868", "DIN 3971", "DIN ISO 17485", "ISO 23509"],
        applications=[
            "Gehrungsrad = Kegelrad mit Übersetzung 1:1 (beide Räder gleiche Zähnezahl)",
            "Reine Achsumlenkung ohne Drehzahl-/Drehmomentwandlung (i = 1)",
            "Standard-Achswinkel 90° (Teilkegelwinkel γ = 45°); auch 60° und 45° lieferbar",
            "Stellantriebe, Handkurbeln, Messgeräte, Förder- und Antriebstechnik",
        ],
        manufacturing=[
            "Geradverzahnt: Kegelradhobeln/-fräsen im Teilverfahren",
            "Bogenverzahnt für ruhigeren Lauf: Gleason- oder Klingelnberg-Verfahren",
            "Läppen als Feinbearbeitung — Laufpaarung immer paarweise einlaufen lassen",
            "Beide Räder eines Gehrungspaars sind baugleich (1:1) und untereinander tauschbar",
        ],
        quality_checks=[
            "Tragbild beider Räder prüfen (Kontaktfleckenverteilung)",
            "Achswinkel und Montageabstand (mounting distance) am Getriebe kontrollieren",
            "Zahnspiel im montierten Zustand messen",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Gehrungsräder als baugleiches 1:1-Paar betreiben — "
                    "beide Räder besitzen identische Geometrie (z, m, γ)."
                ),
                severity="info",
            ),
            OptimizationRule(
                condition=lambda p: abs((_v(p.shaft_angle_deg) or 90) - 90) > 1.0,
                hint=(
                    "Achswinkel ≠ 90°: Sonderausführung (z. B. 60° oder 45°). "
                    "Gehäuse- und Lageranordnung müssen auf diesen Achswinkel ausgelegt sein."
                ),
                severity="info",
            ),
            OptimizationRule(
                condition=lambda p: (_v(p.num_teeth) or 99) < 14,
                hint=(
                    "Sehr kleine Zähnezahl (z < 14) bei Kegel-/Gehrungsrad: "
                    "Unterschnitt- und Spitzwerden-Gefahr — Profilverschiebung prüfen."
                ),
                severity="warning",
            ),
        ],
    ),

    "ratchet": GearKnowledge(
        gear_type="ratchet",
        norms=[],   # keine eigenständige Verzahnungsnorm — kein Wälzgetriebe
        applications=[
            "Ratschen-/Sperrrad: Sägezahnkranz, der mit einer Klinke nur eine "
            "Drehrichtung zulässt (Freilauf in der Gegenrichtung)",
            "Ratschen, Winden, Seilzüge, Rücklaufsperren, Spann- und Aufziehmechanismen",
            "KEIN Evolventen-Zahnrad — überträgt kein Drehmoment über Wälzeingriff",
            "Aussagekräftige Kenngrößen: Zähnezahl z, Außendurchmesser, Zahnteilung",
        ],
        manufacturing=[
            "Sägezahnkontur durch Fräsen, Drahterodieren, Laserschneiden oder Stanzen (Blech)",
            "Sintern für Großserien",
            "Steile Sperrflanke (nahezu radial) und flache Gleitflanke auslegen",
        ],
        quality_checks=[
            "Selbsthemmung der Klinke an der Sperrflanke prüfen (Druckwinkel)",
            "Zahnfußfestigkeit gegen stoßartige Klinken-Sperrlast",
            "Härte/Verschleißfestigkeit der Sperrflanke",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Sägezahn-Sperrrad: Modul, Eingriffswinkel und Teilkreis sind hier "
                    "ohne Bedeutung — Auslegung erfolgt über Sperrflankenwinkel und Klinke."
                ),
                severity="info",
            ),
        ],
    ),

    "worm": GearKnowledge(
        gear_type="worm",
        norms=["DIN 3975", "ISO 1122-2", "DIN 3974-1", "DIN 3974-2"],
        applications=[
            "Hohes Übersetzungsverhältnis in einer Stufe (i = 10 … 100)",
            "Selbsthemmung möglich (tan(γ) < μ) — kein Zurückdrehen ohne Antrieb",
            "Aufzüge, Hebezeuge, Fördertechnik, Lenkgetriebe",
            "Achsversatz 90°, gekreuzte Achsen",
        ],
        manufacturing=[
            "Schnecke: Drehen auf CNC-Drehmaschine + Schleifen der Flanken",
            "Schneckenrad: Wälzfräsen mit Schneckenfräser (Formfräser oder Abwälzfräser)",
            "Werkstoffpaarung: Stahl-Schnecke + Bronze-Schneckenrad (Gleitverschleiß reduzieren)",
        ],
        quality_checks=[
            "Zahnflankenspiel und Tragbild am montierten Getriebe prüfen",
            "Einlaufphase einplanen (Schneckenrad läuft sich ein — Tragbild verbessert sich)",
            "Thermische Auslegung: Wirkungsgrad η ≈ 0,7–0,9 → hohe Verlustleistung",
            "Schmierung: Druckumlaufschmierung bei hohen Leistungen",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Wirkungsgrad beachten: η ≈ 0,7–0,9. "
                    "Bei η-kritischen Anwendungen Hypoidverzahnung oder "
                    "mehrstufiges Getriebe mit höherem η prüfen."
                ),
                severity="info",
            ),
            OptimizationRule(
                condition=lambda p: (p.worm_starts or 1) == 1,
                hint=(
                    "Eingängige Schnecke (n = 1): Hohe Selbsthemmungswahrscheinlichkeit, "
                    "aber niedriger Wirkungsgrad. Mehrgängige Schnecke (n = 2–4) bei "
                    "η-kritischen Anwendungen erwägen."
                ),
                severity="cost",
            ),
        ],
    ),

    "worm_wheel": GearKnowledge(
        gear_type="worm_wheel",
        norms=["DIN 3975", "ISO 1122-2", "DIN 3974-1"],
        applications=[
            "Getriebepartner der Schnecke (Schneckenrad)",
            "Typisch: Bronze oder Grauguss für gute Gleiteigenschaften",
            "Hohes Übersetzungsverhältnis — wird langsam drehend ausgeführt",
        ],
        manufacturing=[
            "Wälzfräsen mit Schneckenfräser (Globalfräser) — erzeugt Kehlform",
            "Bei kleinen Serien: Formfräsen möglich",
            "Werkstoff: CuSn-Bronze (DIN 1705) für hohe Belastungen",
        ],
        quality_checks=[
            "Tragbild (Kontaktmuster) mit Tuschierfarbe prüfen",
            "Einlaufverschleiß durch Einfahrphase bei reduzierter Last berücksichtigen",
            "Zahnflankenspiel im eingebauten Zustand messen",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Schneckenrad immer zusammen mit der zugehörigen Schnecke "
                    "austauschen — Laufpaarung ist geometrisch aufeinander abgestimmt."
                ),
                severity="warning",
            ),
        ],
    ),

    "internal": GearKnowledge(
        gear_type="internal",
        norms=["DIN 867", "DIN ISO 1328-1", "ISO 1122-1"],
        applications=[
            "Planetengetriebe (Hohlrad) — kompakte Bauweise, koaxiale Anordnung",
            "Gleichläufige Drehrichtung zwischen Antrieb und Abtrieb",
            "Bohrungsmaschinen, Planetenachsen, automatische Getriebe",
            "Höherer Wirkungsgrad als Schneckengetriebe",
        ],
        manufacturing=[
            "Innenverzahnung: nur Stoßen (Wälzstoßen) möglich — kein Wälzfräsen",
            "Räumen für Großserien (z. B. Automatikgetriebe-Planetenräder)",
            "Innenschleifen für hohe Qualitätsklassen",
        ],
        quality_checks=[
            "Mindest-Zähnezahldifferenz zwischen Hohlrad und Planetenrad prüfen "
            "(Kopfkreisinterferenz vermeiden: z_Hohlrad − z_Planet ≥ 8)",
            "Koaxialität Innen-/Außenverzahnung messen",
            "Zahnspiel im montierten Planetensatz prüfen",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: (
                    _v(p.num_teeth) and _v(p.hub_bore_diameter_mm)
                    and _v(p.hub_bore_diameter_mm) > 0
                    and _v(p.outer_diameter_mm) > 0
                    and (_v(p.hub_bore_diameter_mm) / _v(p.outer_diameter_mm)) > 0.85
                ),
                hint=(
                    "Wanddicke sehr gering (d_N/d_a > 0,85). "
                    "Festigkeit des Hohlrades prüfen — ggf. Außendurchmesser vergrößern."
                ),
                severity="warning",
            ),
        ],
    ),

    "rack": GearKnowledge(
        gear_type="rack",
        norms=["DIN 867", "DIN 3960", "DIN ISO 1328-1"],
        applications=[
            "Zahnstangengetriebe: Drehbewegung → Linearbewegung",
            "CNC-Achsen, Druckmaschinen, Hebeanlagen, Zahnstangenlenkung",
            "Unbegrenzte Übersetzungslänge (stückweise Montage)",
            "Typischer Eingriffswinkel α = 20° (DIN 867)",
        ],
        manufacturing=[
            "Wälzfräsen (Abwälzverfahren auf Planfräsmaschine)",
            "Stoßen für kurze Zahnstangen",
            "Schleifen für hohe Genauigkeitsanforderungen",
            "Gehärtete und geschliffene Zahnstangen für CNC-Anwendungen",
        ],
        quality_checks=[
            "Teilungsabweichung fp über die gesamte Länge prüfen",
            "Geradheit der Zahnstange (Richtungsabweichung)",
            "Flankenrauheit Ra und Härteeindringtiefe nach Einsatzhärten",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: (_v(p.module_mm) or 0) < 2 and (_v(p.face_width_mm) or 0) > 100,
                hint=(
                    "Kleiner Modul (m < 2) bei langer Zahnstange: "
                    "Erhöhter Fertigungsaufwand. m ≥ 3 bei Länge > 100 mm prüfen."
                ),
                severity="cost",
            ),
        ],
    ),

    "crown": GearKnowledge(
        gear_type="crown",
        norms=["DIN 3960", "DIN 867"],   # keine eigene Planrad-Geometrienorm
        applications=[
            "Kronrad/Planrad: kämmt mit einem Stirnritzel unter ~90° Achsversatz",
            "Winkeltriebe mit geringer Empfindlichkeit gegen radialen Achsversatz des Ritzels",
            "Handwerkzeuge, Stellantriebe, Feinwerktechnik, Haushaltsgeräte",
            "Kostengünstige Alternative zum Kegelradsatz bei kleinen Übersetzungen",
        ],
        manufacturing=[
            "Wälzstoßen/Wälzfräsen mit stirnradartigem Werkzeug (Profil des Gegenritzels)",
            "Zahnflanken sind konjugiert zum Gegen-Stirnritzel — Werkzeug ≈ Bezugsritzel",
            "Sintern/Räumen für Großserien in der Feinwerktechnik",
        ],
        quality_checks=[
            "Tragbild-Prüfung mit dem Gegen-Stirnritzel (Kontaktmuster auf der Stirnfläche)",
            "Axiale Einbaulage des Ritzels prüfen (Kronräder sind gegen radialen Versatz "
            "tolerant, aber empfindlich gegen axiale Fehllage)",
            "Axiale Zahntiefe und radiale Zahnkranzbreite kontrollieren",
        ],
        optimization_rules=[
            OptimizationRule(
                condition=lambda p: (_v(p.num_teeth) or 99) < 17,
                hint=(
                    "z < 17 am Kronrad: erhöhte Unterschnitt-/Spitzenbildungsgefahr im "
                    "Zahnkranz. Größere Zähnezahl oder Profilverschiebung des Gegenritzels prüfen."
                ),
                severity="warning",
            ),
            OptimizationRule(
                condition=lambda p: True,
                hint=(
                    "Kronrad/Planrad: Eingriffswinkel und Fußkreis sind am Einzelrad nicht "
                    "messbar (α = 20° angenommen); das Modul ist am Bezugsradius (Zahnkranzmitte) "
                    "bestimmt und radiusabhängig — für die Paarung das Gegenritzel als Bezug nehmen."
                ),
                severity="info",
            ),
        ],
    ),
}


# ─────────────────────────────────────────────
# Hauptfunktion
# ─────────────────────────────────────────────

def generate_gear_hints(params) -> dict:
    """
    Erzeugt kontextbezogene Hinweise basierend auf Zahnrad-Typ und extrahierten Parametern.

    Gibt dict zurück mit: norms, applications, manufacturing, quality_checks, optimization.
    Gibt leeres dict zurück wenn Typ unbekannt.
    """
    knowledge = GEAR_KNOWLEDGE.get(_v(params.gear_type))
    if not knowledge:
        return {}

    hints: dict = {
        "norms":          knowledge.norms,
        "applications":   knowledge.applications,
        "manufacturing":  knowledge.manufacturing,
        "quality_checks": knowledge.quality_checks,
        "optimization":   [],
    }

    for rule in knowledge.optimization_rules:
        try:
            if rule.condition(params):
                hints["optimization"].append({
                    "severity": rule.severity,
                    "hint":     rule.hint,
                })
        except Exception:
            pass

    return hints
