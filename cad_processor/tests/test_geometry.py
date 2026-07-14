"""
tests/test_geometry.py
----------------------
Unit-Tests für das Geometrie-Modul (ohne STEP-Datei nötig).

Testet die reinen Berechnungsfunktionen in geometry_analyzer.py
und die JSON-Ausgabestruktur in output_schema.py.

Ausführen:
conda run -n gear-copilot python -m pytest tests/ -v
"""

import sys
import os
import math
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from geometry_analyzer import (
    calculate_module,
    calculate_tooth_profile,
    estimate_num_teeth,
    estimate_z_from_diameter,
    detect_gear_type,
    detect_helix_angle_v2,
    estimate_mass,
    assign_norm_reference,
    STANDARD_MODULES,
)
from output_schema import GearParameters, ParameterValue, C
from gear_hints import generate_gear_hints, GEAR_KNOWLEDGE


# ─────────────────────────────────────────────
# Modul-Berechnung
# ─────────────────────────────────────────────

class TestCalculateModule:

    def test_standard_modul_2(self):
        # Stirnrad: z=30, m=2 → d_a = 2*(30+2) = 64 mm
        result = calculate_module(64.0, 30)
        assert result == 2.0

    def test_standard_modul_2_5(self):
        # z=20, m=2.5 → d_a = 2.5*(20+2) = 55 mm
        result = calculate_module(55.0, 20)
        assert result == 2.5

    def test_standard_modul_3(self):
        # z=15, m=3 → d_a = 3*(15+2) = 51 mm
        result = calculate_module(51.0, 15)
        assert result == 3.0

    def test_small_deviation_rounds_to_norm(self):
        # Leichte Abweichung: sollte trotzdem auf Normmodul runden
        result = calculate_module(64.3, 30)   # leicht > 64.0
        assert result == 2.0

    def test_none_for_zero_teeth(self):
        assert calculate_module(80.0, 0) is None

    def test_none_for_none_teeth(self):
        assert calculate_module(80.0, None) is None

    def test_returns_raw_if_no_norm_match(self):
        # Sehr ungewöhnliche Kombination → Rohwert
        result = calculate_module(37.7, 17)
        assert result is not None


# ─────────────────────────────────────────────
# Zahnprofil-Parameter
# ─────────────────────────────────────────────

class TestToothProfile:

    def setup_method(self):
        # Referenz-Zahnrad: z=30, m=2, d_a=64, d_f=55
        self.z = 30
        self.m = 2.0
        self.d_a = 64.0
        self.profile = calculate_tooth_profile(self.z, self.m, self.d_a, None, False)

    def test_pitch_diameter(self):
        assert self.profile["pitch_diameter_mm"] == 60.0   # d = m*z = 2*30

    def test_root_diameter_standard(self):
        # d_f = m*(z-2.5) = 2*(30-2.5) = 55.0
        assert self.profile["root_diameter_mm"] == 55.0

    def test_addendum(self):
        assert self.profile["addendum_mm"] == 2.0   # h_a = m

    def test_dedendum(self):
        assert self.profile["dedendum_mm"] == 2.5   # h_f = 1.25*m

    def test_tooth_height(self):
        # h = (d_a - d_f) / 2 = (64 - 55) / 2 = 4.5
        assert self.profile["tooth_height_mm"] == 4.5

    def test_tooth_thickness(self):
        # s = π*m/2
        expected = round(math.pi * 2.0 / 2, 3)
        assert self.profile["tooth_thickness_mm"] == expected

    def test_profile_shift_zero_standard(self):
        assert self.profile["profile_shift_x"] == 0.0

    def test_root_diameter_direct_from_geometry(self):
        # Wenn d_f direkt aus Geometrie übergeben → wird bevorzugt
        profile = calculate_tooth_profile(30, 2.0, 64.0, 54.5, False)
        assert profile["root_diameter_mm"] == 54.5

    def test_internal_gear_root_diameter(self):
        profile = calculate_tooth_profile(30, 2.0, 64.0, None, True)
        # d_f = m*(z+2.5) = 2*(30+2.5) = 65.0
        assert profile["root_diameter_mm"] == 65.0


# ─────────────────────────────────────────────
# Zahnzahl-Schätzung
# ─────────────────────────────────────────────

class TestEstimateNumTeeth:

    def test_tori_method_preferred(self):
        # 60 Tori → z = 60//2 = 30
        tori = [0.4] * 60
        result = estimate_num_teeth(500, 0, tori)
        assert result == 30

    def test_fallback_edge_method(self):
        # 720 Kanten, keine Tori → 720/36 = 20
        result = estimate_num_teeth(720, 0, [])
        assert result == 20

    def test_returns_none_for_few_edges(self):
        result = estimate_num_teeth(10, 0, [])
        assert result is None

    def test_implausible_tori_count_uses_fallback(self):
        # 1 Torus → z=0 → außerhalb [5,200] → Kanten-Fallback (720/36 = 20)
        tori = [0.4] * 1
        result = estimate_num_teeth(720, 0, tori)
        assert result == 20


# ─────────────────────────────────────────────
# Zahnrad-Typ-Erkennung
# ─────────────────────────────────────────────

class TestDetectGearType:

    def test_spur_no_cones(self):
        cylinders = [(32.0, False)] * 5 + [(27.5, False)] * 30 + [(10.0, True)]
        gear_type, is_internal, cone_angle = detect_gear_type(cylinders, 20, [], [0.4]*30)
        assert gear_type == "spur"
        assert is_internal is False
        assert cone_angle is None

    def test_internal_gear(self):
        # Mehr innere als äußere Zylinder
        cylinders = [(32.0, True)] * 30 + [(10.0, False)] * 3
        gear_type, is_internal, _ = detect_gear_type(cylinders, 10, [], [])
        assert is_internal is True
        assert gear_type == "internal"

    def test_bevel_gear(self):
        # Viele konische Flächen
        cones = [(math.radians(20), False)] * 10
        gear_type, _, cone_angle = detect_gear_type([], 5, cones, [])
        assert gear_type == "bevel"
        assert cone_angle is not None
        assert abs(cone_angle - 20.0) < 1.0

    def test_rack_no_cylinders(self):
        gear_type, _, _ = detect_gear_type([], 50, [], [])
        assert gear_type == "rack"


# ─────────────────────────────────────────────
# Masse-Schätzung
# ─────────────────────────────────────────────

class TestEstimateMass:

    def test_steel_density(self):
        # Würfel 100x100x100 mm = 1e6 mm³, Stahl 7.85 g/cm³ → 7.85 kg
        mass = estimate_mass(1_000_000, "16MnCr5")
        assert abs(mass - 7.85) < 0.01

    def test_aluminium_lower_density(self):
        mass = estimate_mass(1_000_000, "Aluminium")
        assert mass < 3.0

    def test_unknown_material_uses_default(self):
        mass_known = estimate_mass(100_000, "C45")
        mass_unknown = estimate_mass(100_000, None)
        # Beide sollten nahe beieinander liegen (beide Stahl)
        assert abs(mass_known - mass_unknown) < 0.01

    def test_zero_volume_returns_none(self):
        assert estimate_mass(0, "C45") is None


# ─────────────────────────────────────────────
# Norm-Referenzen
# ─────────────────────────────────────────────

class TestNormReference:

    def test_spur_gear_has_din_867(self):
        norms = assign_norm_reference("spur")
        assert "DIN 867" in norms

    def test_bevel_gear_has_din_868(self):
        norms = assign_norm_reference("bevel")
        assert "DIN 868" in norms

    def test_worm_gear_specific_norm(self):
        norms = assign_norm_reference("worm")
        assert "DIN 3975" in norms

    def test_none_type_returns_empty(self):
        norms = assign_norm_reference(None)
        assert norms == []


# ─────────────────────────────────────────────
# Zahnzahl + Modul via Durchmesser-Enumeration
# ─────────────────────────────────────────────

class TestEstimateZFromDiameter:

    def test_spur_m2_z20(self):
        z, m = estimate_z_from_diameter(44.0, 720)
        assert z == 20 and m == 2.0

    def test_spur_m2_z30(self):
        z, m = estimate_z_from_diameter(64.0, 1080)
        assert z == 30 and m == 2.0

    def test_spur_m3_z15(self):
        z, m = estimate_z_from_diameter(51.0, 540)
        assert z == 15 and m == 3.0

    def test_spur_m5_z10(self):
        z, m = estimate_z_from_diameter(60.0, 360)
        assert z == 10 and m == 5.0

    def test_helical_m2_z25(self):
        z, m = estimate_z_from_diameter(54.0, 900)
        assert z == 25 and m == 2.0

    def test_helical_m3_z20(self):
        z, m = estimate_z_from_diameter(66.0, 720)
        assert z == 20 and m == 3.0

    def test_returns_none_for_no_match(self):
        z, m = estimate_z_from_diameter(1.0, 0)
        assert z is None and m is None


# ─────────────────────────────────────────────
# JSON-Schema Ausgabe
# ─────────────────────────────────────────────

class TestOutputSchema:

    def test_to_dict_has_required_keys(self):
        params = GearParameters(source_file="test.stp")
        params.gear_type = "spur"
        params.num_teeth = 30
        params.module_mm = 2.0
        d = params.to_dict()
        assert "schema_version" in d
        assert "basic_geometry" in d
        assert "tooth_profile" in d
        assert "topology" in d
        assert "material_context" in d
        assert "metadata" in d
        assert "extraction_quality" in d

    def test_to_dict_nested_structure(self):
        params = GearParameters(source_file="test.stp")
        params.outer_diameter_mm = 64.0
        params.num_teeth = 30
        params.module_mm = 2.0
        d = params.to_dict()
        assert d["basic_geometry"]["outer_diameter_mm"] == 64.0
        assert d["tooth_profile"]["num_teeth"] == 30

    def test_to_json_creates_valid_file(self, tmp_path):
        params = GearParameters(source_file="test.stp")
        params.gear_type = ParameterValue.make("spur", "", 0.88)
        output_path = str(tmp_path / "result.json")
        params.to_json(output_path)
        assert os.path.exists(output_path)
        with open(output_path) as f:
            data = json.load(f)
        assert data["gear_type"]["value"] == "spur"
        assert data["schema_version"] == "2.0"

    def test_warnings_list_initially_empty(self):
        params = GearParameters(source_file="test.stp")
        assert params.warnings == []

    def test_confidence_default_is_1(self):
        params = GearParameters(source_file="test.stp")
        assert params.overall_confidence == 1.0

    def test_hints_field_in_to_dict(self):
        params = GearParameters(source_file="test.stp")
        params.gear_type = "spur"
        params.hints = {"norms": ["DIN 867"], "optimization": []}
        d = params.to_dict()
        assert "hints" in d
        assert "DIN 867" in d["hints"]["norms"]

    def test_parameter_value_serialization(self):
        pv = ParameterValue.make(44.0, "mm", 0.92)
        d = pv.to_dict()
        assert d == {"value": 44.0, "unit": "mm", "confidence": 0.92}

    def test_gear_parameters_have_per_field_confidence(self):
        params = GearParameters(source_file="test.stp")
        params.outer_diameter_mm = ParameterValue.make(64.0, "mm", 0.92)
        params.num_teeth = ParameterValue.make(30, "", 0.75)
        params.module_mm = ParameterValue.make(2.0, "mm", 0.82)
        d = params.to_dict()
        for field_name in ("outer_diameter_mm",):
            field_val = d["basic_geometry"][field_name]
            assert isinstance(field_val, dict), f"{field_name} should be a dict"
            assert "value" in field_val and "confidence" in field_val
        assert d["tooth_profile"]["num_teeth"]["value"] == 30
        assert d["tooth_profile"]["module_mm"]["confidence"] == 0.82


# ─────────────────────────────────────────────
# Schrägungswinkel v2 (3D-Kurven-Abtastung)
# ─────────────────────────────────────────────

class TestHelixAngleV2:

    def _make_helix_data(self, beta_deg: float, pitch_radius: float, n: int = 20):
        """Erzeugt synthetische (avg_r, d_theta_dz)-Daten für einen gegebenen β-Winkel."""
        tan_beta = math.tan(math.radians(beta_deg))
        # dθ/dz = tan(β) / r_pitch
        d_theta_dz = tan_beta / pitch_radius
        return [(pitch_radius, d_theta_dz)] * n

    def test_spur_zero_helix(self):
        # dθ/dz = 0 → β = 0°
        data = [(25.0, 0.0)] * 20
        result = detect_helix_angle_v2(data, pitch_radius=25.0)
        assert result == 0.0

    def test_helical_15_deg(self):
        data = self._make_helix_data(15.0, pitch_radius=27.0)
        result = detect_helix_angle_v2(data, pitch_radius=27.0)
        assert result is not None
        assert abs(result - 15.0) < 1.0

    def test_helical_20_deg(self):
        data = self._make_helix_data(20.0, pitch_radius=27.0)
        result = detect_helix_angle_v2(data, pitch_radius=27.0)
        assert result is not None
        assert abs(result - 20.0) < 1.0

    def test_helical_30_deg(self):
        data = self._make_helix_data(30.0, pitch_radius=33.0)
        result = detect_helix_angle_v2(data, pitch_radius=33.0)
        assert result is not None
        assert abs(result - 30.0) < 1.0

    def test_returns_none_for_empty_data(self):
        assert detect_helix_angle_v2([], pitch_radius=25.0) is None

    def test_returns_none_for_zero_pitch_radius(self):
        data = [(25.0, 0.01)] * 5
        assert detect_helix_angle_v2(data, pitch_radius=0.0) is None

    def test_median_filters_outliers(self):
        # 18 Kanten sagen β=20°, 2 Ausreißer (Fasen) sagen β=45°
        good = self._make_helix_data(20.0, pitch_radius=27.0, n=18)
        outliers = self._make_helix_data(45.0, pitch_radius=27.0, n=2)
        result = detect_helix_angle_v2(good + outliers, pitch_radius=27.0)
        assert result is not None
        assert abs(result - 20.0) < 2.0


# ─────────────────────────────────────────────
# Zahnrad-Typ v2 (neue Erkennungslogik)
# ─────────────────────────────────────────────

class TestDetectGearTypeV2:

    def test_worm_by_aspect_ratio_and_tori(self):
        # Schnecke: b/d_a = 3.0, viele Tori pro Zylinder
        cylinders = [(15.0, False)] * 3
        tori = [0.5] * 30   # 10 Tori pro Zylinder
        gear_type, _, _ = detect_gear_type(
            cylinders, 5, [], tori,
            outer_diameter_mm=30.0, face_width_mm=90.0, total_faces=50
        )
        assert gear_type == "worm"

    def test_worm_wheel_by_tori_fraction(self):
        # Schneckenrad: Tori-Anteil > 30% aller Faces, Aspektverhältnis < 1
        cylinders = [(30.0, False)] * 5 + [(10.0, True)] * 2
        tori = [0.4] * 25   # 25 von 80 Faces = 31%
        gear_type, _, _ = detect_gear_type(
            cylinders, 10, [], tori,
            outer_diameter_mm=60.0, face_width_mm=30.0, total_faces=80
        )
        assert gear_type == "worm_wheel"

    def test_bevel_with_fraction_check(self):
        # Kegelrad: 15 signifikante Kegel-Faces bei 60 Gesamt-Faces = 25%
        cones = [(math.radians(20), False)] * 15
        gear_type, _, cone_angle = detect_gear_type(
            [], 10, cones, [],
            outer_diameter_mm=50.0, face_width_mm=20.0, total_faces=60
        )
        assert gear_type == "bevel"
        assert abs(cone_angle - 20.0) < 1.0

    def test_spur_chamfers_not_bevel(self):
        # 4 kleine Fase-Kegel (45°) bei 200 Gesamt-Faces = 2% → KEIN Kegelrad
        cylinders = [(22.0, False)] * 30 + [(10.0, True)]
        cones = [(math.radians(45), False)] * 4   # typische Fase
        gear_type, _, _ = detect_gear_type(
            cylinders, 20, cones, [],
            outer_diameter_mm=44.0, face_width_mm=20.0, total_faces=200
        )
        assert gear_type == "spur"

    def test_internal_with_margin(self):
        # 30 innere, 3 äußere Zylinder
        cylinders = [(32.0, True)] * 30 + [(10.0, False)] * 3
        gear_type, is_internal, _ = detect_gear_type(
            cylinders, 10, [], [],
            outer_diameter_mm=70.0, face_width_mm=20.0, total_faces=80
        )
        assert gear_type == "internal"
        assert is_internal is True

    def test_rack_no_cylinders(self):
        gear_type, _, _ = detect_gear_type(
            [], 50, [], [],
            outer_diameter_mm=100.0, face_width_mm=20.0, total_faces=60
        )
        assert gear_type == "rack"


# ─────────────────────────────────────────────
# Hinweis-System (gear_hints.py)
# ─────────────────────────────────────────────

class TestGearHints:

    def test_all_types_have_knowledge(self):
        for gear_type in ("spur", "helical", "bevel", "worm", "worm_wheel", "internal", "rack"):
            assert gear_type in GEAR_KNOWLEDGE, f"{gear_type} fehlt in GEAR_KNOWLEDGE"

    def test_all_types_have_norms(self):
        for gear_type, knowledge in GEAR_KNOWLEDGE.items():
            if gear_type == "ratchet":
                # Sperrräder sind keine Wälzgetriebe und besitzen deshalb keine
                # eigenständige Verzahnungsnorm. Diese Ausnahme ist beabsichtigt.
                assert knowledge.norms == []
            else:
                assert len(knowledge.norms) > 0, f"{gear_type}: keine Normen definiert"

    def test_spur_has_din_867(self):
        assert "DIN 867" in GEAR_KNOWLEDGE["spur"].norms

    def test_bevel_has_din_868(self):
        assert "DIN 868" in GEAR_KNOWLEDGE["bevel"].norms

    def test_worm_has_din_3975(self):
        assert "DIN 3975" in GEAR_KNOWLEDGE["worm"].norms

    def test_generate_hints_spur(self):
        params = GearParameters(source_file="test.stp")
        params.gear_type = "spur"
        hints = generate_gear_hints(params)
        assert "norms" in hints
        assert "applications" in hints
        assert "manufacturing" in hints
        assert "quality_checks" in hints
        assert "optimization" in hints
        assert "DIN 867" in hints["norms"]

    def test_generate_hints_unknown_type(self):
        params = GearParameters(source_file="test.stp")
        params.gear_type = "unknown_xyz"
        hints = generate_gear_hints(params)
        assert hints == {}

    def test_optimization_undercut_warning(self):
        # z < 17 → Unterschnitt-Warnung
        params = GearParameters(source_file="test.stp")
        params.gear_type = "spur"
        params.num_teeth = 12
        hints = generate_gear_hints(params)
        opt_hints = [h["hint"] for h in hints["optimization"]]
        assert any("Unterschnitt" in h for h in opt_hints)

    def test_no_undercut_warning_for_large_z(self):
        # z = 25 → kein Unterschnitt
        params = GearParameters(source_file="test.stp")
        params.gear_type = "spur"
        params.num_teeth = 25
        hints = generate_gear_hints(params)
        opt_hints = [h["hint"] for h in hints["optimization"]]
        assert not any("Unterschnitt" in h for h in opt_hints)

    def test_helical_axialkraft_warning(self):
        # β > 30° → Axialkraft-Warnung
        params = GearParameters(source_file="test.stp")
        params.gear_type = "helical"
        params.helix_angle_deg = 35.0
        hints = generate_gear_hints(params)
        opt_hints = [h["hint"] for h in hints["optimization"]]
        assert any("Axialkraft" in h for h in opt_hints)
