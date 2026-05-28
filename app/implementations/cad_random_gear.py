"""
cad_random_gear.py – Stub-Implementierung des CADAdapters.

Generiert zufällige, aber geometrisch konsistente Zahnrad-Metadaten nach DIN 3960.
Dient als Platzhalter bis ein echter CAD-Parser (z.B. PythonOCC für STEP-Dateien)
implementiert wird – ermöglicht sofortiges Testen des Systems ohne CAD-Daten.
"""

from __future__ import annotations

import random


class RandomGearGenerator:
    """Generiert zufällige Zahnrad-Metadaten. Kein Zustand, keine Parameter."""

    def extract(self, file_path=None) -> dict:
        """
        Erzeugt ein Dictionary mit geometrisch plausiblen Zahnrad-Parametern.
        file_path wird ignoriert (Stub-Interface). Die geometrischen Größen
        d, da, df werden nach DIN 3960 aus Modul, Zähnezahl und Profilverschiebung berechnet.
        """
        typ = random.choice(["Stirnrad", "Schrägverzahnung"])
        modul = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0])
        z = random.randint(15, 60)
        alpha = 20.0  # Standardeingriffswinkel nach DIN 867
        beta = 0.0 if typ == "Stirnrad" else float(random.choice([8, 10, 12, 15, 20]))
        x = round(random.uniform(-0.3, 0.5), 2)

        # Geometrie nach DIN 3960
        d = modul * z                         # Teilkreisdurchmesser
        da = d + 2 * modul * (1 + x)          # Kopfkreisdurchmesser
        df = d - 2 * modul * (1.25 - x)       # Fußkreisdurchmesser

        return {
            "verzahnungstyp": typ,
            "modul": modul,
            "zaehnezahl": z,
            "eingriffswinkel": alpha,
            "schraegungswinkel": beta,
            "profilverschiebung": x,
            "teilkreisdurchmesser": round(d, 2),
            "kopfkreisdurchmesser": round(da, 2),
            "fusskreisdurchmesser": round(df, 2),
            "zahnbreite": round(modul * random.uniform(8, 14), 1),
            "werkstoff": random.choice(["16MnCr5", "20MnCr5", "42CrMo4", "C45"]),
            "haerte": random.choice(["vergütet", "einsatzgehärtet", "nitriert"]),
            "verzahnungsqualitaet": random.choice([6, 7, 8]),
            "drehrichtung": "rechts" if beta > 0 else None,  # nur bei Schrägverzahnung relevant
        }
