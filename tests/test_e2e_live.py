"""
test_e2e_live.py – Live-Abnahmetest gegen den LAUFENDEN Server (echtes LLM).

Spielt den Originalfall des Kernbugs durch: geladenes Sperrrad (ratchet, Konfidenz
0.92) + wörtliche "Kegelrad"-Frage. Geprüft wird die TATSÄCHLICH generierte Antwort:
  1. Bauteil-Abgleich-Hinweis (CAD-Typ + Konfidenz) vorangestellt,
  2. Terminologie-Dominanz: CAD-Typ (Sperrrad/Ratsche) dominiert den Fließtext,
     der Fragetyp (Kegelrad) taucht höchstens als Quellenkontext auf,
  3. Zitate: mindestens eine real genutzte Quelle, alle [Q..]-Verweise gültig,
  4. Fakten-Guardrail-Fußnote wird ausgegeben (manuell gegenzulesen, kein Assert –
     eine Markierung kann auch eine ECHTE Halluzination sein, das wäre korrekt).

Läuft nur, wenn der Server erreichbar ist (sonst skip):
  E2E_BASE_URL (Default http://localhost:8000; aus einem Compose-Container: http://app:8000)
Aufruf mit sichtbarer Antwort:  pytest tests/test_e2e_live.py -s
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000").rstrip("/")

_RATCHET_CAD = {
    "gear_type": {"value": "ratchet", "confidence": 0.92},
    "tooth_profile": {"num_teeth": {"value": 24}, "module_mm": {"value": 1.0583, "unit": "mm"}},
    "basic_geometry": {"pitch_diameter_mm": {"value": 25.399, "unit": "mm"},
                       "face_width_mm": {"value": 6.35, "unit": "mm"}},
}
_KEGELRAD_FRAGE = (
    "ich möchte das hochgeladene kegelrad herstellen. Was sagt die literatur in der "
    "wissensbasis dazu welches verfahren sich zur produktion hier am besten eignet"
)


def _server_reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/documents", timeout=5) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


@pytest.mark.skipif(not _server_reachable(), reason=f"Server {BASE_URL} nicht erreichbar (Live-E2E)")
def test_original_case_follow_cad_terminology_dominates():
    req = urllib.request.Request(
        f"{BASE_URL}/ask",
        data=json.dumps({
            "questions": [_KEGELRAD_FRAGE],
            "cad_metadata": _RATCHET_CAD,
            "format": "standard",
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        answer = json.load(r)["answers"][0]

    text = answer["answer_text"]
    print("\n" + "=" * 72 + "\nECHTE ANTWORT (Live-E2E, Originalfall):\n" + "=" * 72)
    print(text)
    print("=" * 72)
    print("citation_stats:", json.dumps(answer.get("citation_stats"), ensure_ascii=False))

    # 1) Bauteil-Abgleich-Hinweis mit CAD-Typ + Konfidenz vorangestellt.
    assert text.startswith("⚠️"), "Bauteil-Abgleich-Hinweis fehlt am Antwortanfang"
    note, _, body = text.partition("\n\n")
    assert "Sperrrad" in note and "92" in note

    # 2) Terminologie-Dominanz im Fließtext (robuste Zählung, kein Einzel-String):
    #    CAD-Typ-Begriffe müssen vorkommen und mindestens so häufig sein wie der
    #    (falsche) Fragetyp – der darf höchstens als Quellenkontext auftauchen.
    lower = body.lower()
    cad_mentions = len(re.findall(r"sperrrad|sperrrads|ratsche", lower))
    question_mentions = len(re.findall(r"kegelrad|kegelräd", lower))
    assert cad_mentions >= 1, "CAD-Typ (Sperrrad/Ratsche) kommt im Fließtext nicht vor"
    assert question_mentions <= cad_mentions, (
        f"Fragetyp dominiert: Kegelrad {question_mentions}x vs. Sperrrad/Ratsche {cad_mentions}x"
    )
    # Der erste Satz (die Empfehlung) darf nicht das Kegelrad zum Gegenstand haben.
    first_sentence = body.strip().split(".")[0].lower()
    assert "kegelrad" not in first_sentence or "sperrrad" in first_sentence

    # 3) Zitate: mindestens eine genutzte Quelle, alle [Q..]-Verweise existieren.
    stats = answer.get("citation_stats") or {}
    cited = stats.get("cited_qids") or []
    assert cited, "Antwort zitiert keine einzige Quelle"
    valid_qids = {str(s.get("qid")) for s in answer.get("sources", [])}
    assert set(cited) <= valid_qids, f"Erfundene Quellenverweise: {set(cited) - valid_qids}"

    # 4) Fakten-Guardrail: nur Ausgabe (Markierung kann eine echte Halluzination sein).
    if "Ohne Beleg" in text:
        print("HINWEIS: Fakten-Guardrail hat Angaben markiert – bitte manuell gegenlesen.")
