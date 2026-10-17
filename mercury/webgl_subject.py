"""Turn a build prompt into the 3D subject the user actually asked for.

The WebGL forge used to classify "3d / webgl" and then always emit the same
core, dino, or torus. This module reads the named subject (chicken, cat,
spaceship, house, slime, …) and builds that mesh instead.
"""

from __future__ import annotations

import json
import re
from typing import Any

WEBGL_FILLER = frozenset(
    {
        "please",
        "build",
        "create",
        "make",
        "forge",
        "scaffold",
        "generate",
        "me",
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "with",
        "and",
        "or",
        "for",
        "to",
        "into",
        "from",
        "using",
        "my",
        "some",
        "really",
        "very",
        "nice",
        "beautiful",
        "sick",
        "cool",
        "awesome",
        "interactive",
        "live",
        "punk",
        "neon",
        "acid",
        "cyber",
        "cyberpunk",
        "style",
        "themed",
        "theme",
        "app",
        "application",
        "studio",
        "scene",
        "simulation",
        "visualizer",
        "shader",
        "shaders",
        "graphic",
        "graphics",
        "webgl",
        "web",
        "gl",
        "three",
        "threejs",
        "js",
        "javascript",
        "3d",
        "2d",
        "model",
        "models",
        "mesh",
        "geometry",
        "render",
        "rendering",
        "just",
        "want",
        "wanted",
        "like",
        "that",
        "this",
        "thing",
        "something",
        "called",
        "named",
        "look",
        "looking",
        "actual",
        "real",
        "cute",
        "giant",
        "tiny",
        "little",
        "big",
        "small",
        "large",
        "huge",
        "mini",
        "low",
        "poly",
        "lowpoly",
        "low-poly",
        "detailed",
        "simple",
        "cartoon",
        "toy",
        "figure",
        "show",
        "draw",
        "spawn",
    }
)

WEBGL_FEATURES = {
    "mohawk": "mohawk",
    "mohawks": "mohawk",
    "horn": "horns",
    "horns": "horns",
    "spike": "spikes",
    "spikes": "spikes",
    "wing": "wings",
    "wings": "wings",
    "tail": "tail",
    "crown": "crown",
    "armor": "armor",
    "wheel": "wheels",
    "wheels": "wheels",
    "laser": "laser",
    "sword": "sword",
    "hat": "hat",
    "beak": "beak",
    "comb": "comb",
    "fire": "fire",
    "thruster": "thruster",
    "tentacle": "tentacles",
    "tentacles": "tentacles",
}

WEBGL_COLOR_WORDS = {
    "red": 0xE10600,
    "blue": 0x2F6BFF,
    "green": 0x39FF14,
    "pink": 0xFF4DA6,
    "yellow": 0xF5D90A,
    "purple": 0x9B30FF,
    "orange": 0xFF7A18,
    "black": 0x222222,
    "white": 0xF4F4F4,
    "gold": 0xF2C14E,
}


def _palette(body: int, accent: int, detail: int, eye: int = 0x1A1A1A) -> dict[str, int]:
    return {"body": body, "accent": accent, "detail": detail, "eye": eye}


def _rule(
    keys: tuple[str, ...],
    family: str,
    features: tuple[str, ...],
    colors: dict[str, int],
    *,
    kind: str = "organic",
    name: str = "",
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "keys": list(keys),
        "family": family,
        "features": list(features),
        "kind": kind,
        "colors": colors,
    }
    if name:
        rule["name"] = name
    return rule


WEBGL_SUBJECT_RULES: list[dict[str, Any]] = [
    _rule(("chicken", "rooster", "hen", "chick"), "bird", ("beak", "comb", "wings", "tail", "legs"), _palette(0xF2C14E, 0xFF7A18, 0xE10600)),
    _rule(("duck", "goose"), "bird", ("beak", "wings", "tail", "legs"), _palette(0xF4EFE2, 0xE8892C, 0xF4EFE2)),
    _rule(("penguin",), "bird", ("beak", "wings", "tail", "legs"), _palette(0x1B1B1B, 0xF4F4F4, 0xE10600)),
    _rule(("owl",), "bird", ("beak", "wings", "tail", "legs", "bigeyes"), _palette(0x8C6A43, 0xF0C14E, 0x5C3B22)),
    _rule(("eagle", "hawk", "parrot", "bird", "turkey", "pigeon", "flamingo", "phoenix"), "bird", ("beak", "wings", "tail", "legs"), _palette(0xC4552A, 0xF2C14E, 0x6B2A12)),
    _rule(
        ("dinobuddy", "dinosaur", "dino", "trex", "t-rex", "raptor", "rex"),
        "dino",
        ("tail", "mohawk"),
        _palette(0x39FF14, 0xF5FF00, 0xFF007F, 0xF5FF00),
        kind="metal",
        name="Dino",
    ),
    _rule(("cat", "kitten", "feline"), "quadruped", ("ears", "tail", "snout"), _palette(0xE39B3A, 0xF2D2A2, 0xC46A1A)),
    _rule(("fox",), "quadruped", ("ears", "tail", "snout"), _palette(0xE07020, 0xF4F4F4, 0x7A3B12)),
    _rule(("dog", "puppy", "wolf", "hound"), "quadruped", ("ears", "tail", "snout"), _palette(0xC4844A, 0xE7C7A1, 0x6B3E22)),
    _rule(("horse",), "quadruped", ("ears", "tail", "snout"), _palette(0x8B5A2B, 0x3B2414, 0x1A1A1A)),
    _rule(("cow",), "quadruped", ("ears", "tail", "snout"), _palette(0xF4F4F4, 0xF2C9A0, 0x2A2A2A)),
    _rule(("bull",), "quadruped", ("ears", "tail", "snout", "horns"), _palette(0x6B3E22, 0xF2C9A0, 0xE7E7E7)),
    _rule(("lion", "tiger"), "quadruped", ("ears", "tail", "snout"), _palette(0xE09A3A, 0xF2D2A2, 0xC4552A)),
    _rule(("bear",), "quadruped", ("ears", "tail", "snout"), _palette(0x6B4226, 0xC4A574, 0x2A1A10)),
    _rule(("pig",), "quadruped", ("ears", "tail", "snout"), _palette(0xF2A7B5, 0xE77A90, 0xC4556A)),
    _rule(("rabbit", "bunny"), "quadruped", ("ears", "tail", "snout"), _palette(0xE7E7E7, 0xF2C9A0, 0xD07090)),
    _rule(("deer",), "quadruped", ("ears", "tail", "snout", "horns"), _palette(0xC4844A, 0xE7C7A1, 0x6B3E22)),
    _rule(("frog",), "quadruped", ("eyes",), _palette(0x3FA34D, 0xF5FF66, 0x1F6B32)),
    _rule(("shark",), "fish", ("fins", "tail"), _palette(0x8AA0B2, 0xD7E2EA, 0x4C5C6B)),
    _rule(("whale", "dolphin"), "fish", ("fins", "tail"), _palette(0x4C6F8A, 0xD7E2EA, 0x1C3A4F)),
    _rule(("goldfish",), "fish", ("fins", "tail"), _palette(0xFF7A18, 0xF5D90A, 0xE10600)),
    _rule(("fish",), "fish", ("fins", "tail"), _palette(0x3AA0FF, 0xF25C8E, 0x1C4E8C)),
    _rule(("dragon",), "serpent", ("wings", "horns", "tail", "fire"), _palette(0x6B2FA0, 0xFF5A00, 0xF5D90A)),
    _rule(("snake", "serpent", "worm", "eel"), "serpent", ("tail",), _palette(0x3FA34D, 0xF5D90A, 0x1F6B32)),
    _rule(("spider",), "insect", ("legs",), _palette(0x2A2A2A, 0xC4552A, 0x6B1A1A)),
    _rule(("bee",), "insect", ("legs", "wings"), _palette(0xF5D90A, 0x1A1A1A, 0xF4F4F4)),
    _rule(("ant", "bug", "insect", "crab"), "insect", ("legs",), _palette(0x8C3A2F, 0x1A1A1A, 0xC4844A)),
    _rule(("octopus", "squid"), "cephalopod", ("tentacles",), _palette(0xC4556A, 0xE77A90, 0x6B1A3A)),
    _rule(("slimeball", "slime", "blob", "goo", "amoeba"), "blob", (), _palette(0x39FF14, 0xB8FF6A, 0x111111), kind="gel"),
    _rule(("heart",), "blob", ("heart",), _palette(0xE10600, 0xFF4D6A, 0x8C1028)),
    _rule(("planet", "earth", "moon", "globe"), "blob", ("planet",), _palette(0x2F6BFF, 0x3FA34D, 0xF4F4F4), kind="metal"),
    _rule(("robot", "android", "mech", "cyborg"), "biped", ("armor", "visor"), _palette(0x8E99A4, 0x39FF14, 0xFF007F, 0x39FF14), kind="metal"),
    _rule(("astronaut",), "biped", ("visor",), _palette(0xF4F4F4, 0x2F6BFF, 0xE10600), kind="metal"),
    _rule(("knight",), "biped", ("armor", "horns"), _palette(0xC5CCD3, 0x8E99A4, 0xF5D90A), kind="metal"),
    _rule(("skeleton", "skull"), "biped", ("skull",), _palette(0xE7E2D6, 0x1A1A1A, 0xF4F4F4)),
    _rule(("human", "person", "astronaut", "zombie", "goblin", "wizard", "ninja", "character"), "biped", (), _palette(0xE7B89A, 0x3D5A80, 0x1A1A1A)),
    _rule(("car", "truck", "buggy"), "vehicle", ("wheels",), _palette(0xFF007F, 0x1A1A1A, 0xF5FF00), kind="metal"),
    _rule(("spaceship", "starship", "rocket", "plane", "airplane", "jet"), "vehicle", ("wings", "thruster"), _palette(0xC8D0D8, 0x39FF14, 0xFF007F), kind="metal"),
    _rule(("boat", "ship"), "vehicle", ("thruster",), _palette(0x8C3A2F, 0xF4F4F4, 0x2F6BFF), kind="metal"),
    _rule(("tree", "pine"), "structure", ("canopy",), _palette(0x2E8B3A, 0x6B3F1D, 0x1F6B32)),
    _rule(("house", "home", "castle", "tower", "building"), "structure", ("roof",), _palette(0xD7C4A3, 0x8C3A2F, 0xC4552A), kind="matte"),
    _rule(("teapot", "kettle"), "prop", ("teapot",), _palette(0xD7C4A3, 0xF4F4F4, 0x8C3A2F), kind="matte"),
    _rule(("chair",), "prop", ("chair",), _palette(0x8C5A2B, 0xC4844A, 0x3B2414), kind="matte"),
    _rule(("sword",), "prop", ("sword",), _palette(0xC5CCD3, 0xF5D90A, 0x8E99A4), kind="metal"),
    _rule(("torus", "knot"), "torus", (), _palette(0x39FF14, 0xFF007F, 0xF5FF00), kind="metal", name="Torus"),
    _rule(("mercbot", "icosahedron", "orb"), "core", (), _palette(0x223829, 0x39FF14, 0xFF007F, 0xF5FF00), kind="metal", name="Core"),
]


def _pretty(token: str) -> str:
    if "-" in token:
        return "-".join(part.capitalize() for part in token.split("-"))
    return token[:1].upper() + token[1:]


def _singular_forms(token: str) -> list[str]:
    forms: list[str] = []
    if len(token) > 4 and token.endswith("ies"):
        forms.append(token[:-3] + "y")
    if len(token) > 4 and token.endswith("es"):
        forms.append(token[:-2])
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        forms.append(token[:-1])
    return forms


def _key_in_text(raw: str, content: list[str], key: str) -> bool:
    if key in content:
        return True
    for token in content:
        if key in _singular_forms(token):
            return True
    return re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", raw) is not None


def _hash_colors(token: str) -> dict[str, int]:
    acc = 2166136261
    for ch in token:
        acc ^= ord(ch)
        acc = (acc * 16777619) & 0xFFFFFFFF
    red = 70 + (acc & 0x7F)
    green = 50 + ((acc >> 8) & 0x7F)
    blue = 40 + ((acc >> 16) & 0x5F)
    return _palette((red << 16) | (green << 8) | blue, 0xFF007F, 0xF5FF00)


def _core_subject() -> dict[str, Any]:
    return {
        "name": "Core",
        "token": "core",
        "family": "core",
        "kind": "metal",
        "features": [],
        "colors": _palette(0x223829, 0x39FF14, 0xFF007F, 0xF5FF00),
    }


def resolve_webgl_subject(text: str) -> dict[str, Any]:
    """Parse the thing the user asked to build out of a freeform prompt."""
    raw = (text or "").lower()
    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", raw)
    features: list[str] = []
    body_override: int | None = None
    content: list[str] = []
    for token in tokens:
        if token in WEBGL_FEATURES:
            feat = WEBGL_FEATURES[token]
            if feat not in features:
                features.append(feat)
            continue
        if token in WEBGL_COLOR_WORDS:
            body_override = WEBGL_COLOR_WORDS[token]
            continue
        if token in WEBGL_FILLER:
            continue
        content.append(token)

    best_rule: dict[str, Any] | None = None
    best_key = ""
    for rule in WEBGL_SUBJECT_RULES:
        for key in rule["keys"]:
            if _key_in_text(raw, content, key) and len(key) > len(best_key):
                best_rule = rule
                best_key = key

    if best_rule is None and not content:
        subject = _core_subject()
        if body_override is not None:
            subject["colors"] = {**subject["colors"], "body": body_override}
        return subject

    if best_rule is None:
        token = content[0]
        colors = _hash_colors(token)
        if body_override is not None:
            colors = {**colors, "body": body_override}
        return {
            "name": _pretty(token),
            "token": token,
            "family": "mascot",
            "kind": "organic",
            "features": features or ["limbs"],
            "colors": colors,
        }

    family = str(best_rule["family"])
    merged = list(best_rule.get("features") or [])
    for feat in features:
        if feat not in merged:
            merged.append(feat)
    name = str(best_rule.get("name") or _pretty(best_key))
    if family == "dino" and "mohawk" in merged:
        name = "Dino Mohawk"
    colors = dict(best_rule["colors"])
    if body_override is not None:
        colors["body"] = body_override
    return {
        "name": name,
        "token": best_key,
        "family": family,
        "kind": best_rule.get("kind", "organic"),
        "features": merged,
        "colors": colors,
    }


def mesh_mode_for_subject(subject: dict[str, Any]) -> str:
    """Which built-in viewport slot should open for this subject."""
    family = subject.get("family")
    if family in ("dino", "torus", "core"):
        return str(family)
    return "subject"


def subject_bootstrap_js(subject: dict[str, Any]) -> str:
    payload = {
        "rules": WEBGL_SUBJECT_RULES,
        "filler": sorted(WEBGL_FILLER),
        "features": WEBGL_FEATURES,
        "colors": WEBGL_COLOR_WORDS,
    }
    return (
        "let activeSubject = "
        + json.dumps(subject)
        + ";\nconst SUBJECT_FORGE = "
        + json.dumps(payload)
        + ";\n"
        + _RESOLVER_AND_FALLBACK_JS
    )


def subject_builder_js() -> str:
    return _SUBJECT_BUILDER_JS


_RESOLVER_AND_FALLBACK_JS = r"""
function resolveSubject(text) {
  const raw = String(text || "").toLowerCase();
  const tokens = raw.match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) || [];
  const filler = new Set(SUBJECT_FORGE.filler);
  const features = [];
  let bodyOverride = null;
  const content = [];
  tokens.forEach((token) => {
    if (SUBJECT_FORGE.features[token]) {
      const feat = SUBJECT_FORGE.features[token];
      if (features.indexOf(feat) < 0) features.push(feat);
      return;
    }
    if (SUBJECT_FORGE.colors[token] != null) {
      bodyOverride = SUBJECT_FORGE.colors[token];
      return;
    }
    if (filler.has(token)) return;
    content.push(token);
  });
  function singulars(token) {
    const forms = [];
    if (token.length > 4 && token.endsWith("ies")) forms.push(token.slice(0, -3) + "y");
    if (token.length > 4 && token.endsWith("es")) forms.push(token.slice(0, -2));
    if (token.length > 3 && token.endsWith("s") && !token.endsWith("ss")) forms.push(token.slice(0, -1));
    return forms;
  }
  function keyInText(key) {
    if (content.indexOf(key) >= 0) return true;
    for (let i = 0; i < content.length; i++) {
      if (singulars(content[i]).indexOf(key) >= 0) return true;
    }
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp("(?<![a-z0-9])" + escaped + "(?![a-z0-9])").test(raw);
  }
  let best = null;
  let bestKey = "";
  SUBJECT_FORGE.rules.forEach((rule) => {
    rule.keys.forEach((key) => {
      if (keyInText(key) && key.length > bestKey.length) {
        best = rule;
        bestKey = key;
      }
    });
  });
  function pretty(token) {
    if (token.indexOf("-") >= 0) {
      return token.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("-");
    }
    return token.charAt(0).toUpperCase() + token.slice(1);
  }
  function applyBody(colors) {
    const next = Object.assign({}, colors);
    if (bodyOverride != null) next.body = bodyOverride;
    return next;
  }
  if (!best && content.length === 0) {
    return {
      name: "Core",
      token: "core",
      family: "core",
      kind: "metal",
      features: [],
      colors: applyBody({ body: 2242601, accent: 3778324, detail: 16711807, eye: 16187392 })
    };
  }
  if (!best) {
    const token = content[0];
    let acc = 2166136261;
    for (let i = 0; i < token.length; i++) {
      acc ^= token.charCodeAt(i);
      acc = Math.imul(acc, 16777619) >>> 0;
    }
    const red = 70 + (acc & 127);
    const green = 50 + ((acc >> 8) & 127);
    const blue = 40 + ((acc >> 16) & 95);
    return {
      name: pretty(token),
      token: token,
      family: "mascot",
      kind: "organic",
      features: features.length ? features : ["limbs"],
      colors: applyBody({ body: (red << 16) | (green << 8) | blue, accent: 16711807, detail: 16187392, eye: 1710618 })
    };
  }
  const merged = (best.features || []).slice();
  features.forEach((feat) => { if (merged.indexOf(feat) < 0) merged.push(feat); });
  let name = best.name || pretty(bestKey);
  if (best.family === "dino" && merged.indexOf("mohawk") >= 0) name = "Dino Mohawk";
  return {
    name: name,
    token: bestKey,
    family: best.family,
    kind: best.kind || "organic",
    features: merged,
    colors: applyBody(best.colors)
  };
}

function applySubjectCommand(text) {
  const next = resolveSubject(text);
  activeSubject = next;
  if (next.family === "dino") currentMeshIdx = meshModes.indexOf("dino");
  else if (next.family === "torus") currentMeshIdx = meshModes.indexOf("torus");
  else if (next.family === "core") currentMeshIdx = meshModes.indexOf("core");
  else currentMeshIdx = meshModes.indexOf("subject");
  if (currentMeshIdx < 0) currentMeshIdx = 0;
  userAdjustedZoom = false;
  if (typeof rebuildMeshFn === "function") rebuildMeshFn();
}

function drawSubjectFallback(ctx) {
  const w = canvas.width;
  const h = canvas.height;
  const s = activeSubject;
  ctx.fillStyle = "#030704";
  ctx.fillRect(0, 0, w, h);
  const hex = "#" + (Number(s.colors.body) >>> 0).toString(16).padStart(6, "0").slice(-6);
  ctx.fillStyle = hex;
  const cx = w / 2;
  const cy = h / 2;
  if (s.family === "bird") {
    ctx.beginPath(); ctx.ellipse(cx - 24, cy + 8, 74, 50, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + 68, cy - 34, 30, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ff7a18";
    ctx.beginPath(); ctx.moveTo(cx + 92, cy - 30); ctx.lineTo(cx + 136, cy - 18); ctx.lineTo(cx + 92, cy - 8); ctx.fill();
    ctx.fillStyle = "#e10600";
    ctx.beginPath(); ctx.ellipse(cx + 62, cy - 66, 8, 16, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx + 78, cy - 74, 8, 18, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx + 94, cy - 64, 8, 14, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "#ff7a18";
    ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(cx - 20, cy + 48); ctx.lineTo(cx - 20, cy + 92); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + 16, cy + 48); ctx.lineTo(cx + 16, cy + 92); ctx.stroke();
  } else if (s.family === "quadruped") {
    ctx.beginPath(); ctx.ellipse(cx - 10, cy + 6, 86, 38, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + 84, cy - 16, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillRect(cx - 48, cy + 28, 12, 42);
    ctx.fillRect(cx + 28, cy + 28, 12, 42);
  } else if (s.family === "fish") {
    ctx.beginPath(); ctx.ellipse(cx + 10, cy, 86, 34, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.moveTo(cx - 70, cy); ctx.lineTo(cx - 124, cy - 30); ctx.lineTo(cx - 124, cy + 30); ctx.fill();
  } else if (s.family === "blob") {
    ctx.beginPath(); ctx.arc(cx, cy, 72, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#111";
    ctx.beginPath(); ctx.arc(cx - 16, cy - 8, 8, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + 22, cy - 8, 8, 0, Math.PI * 2); ctx.fill();
  } else if (s.family === "vehicle") {
    ctx.fillRect(cx - 90, cy - 10, 180, 40);
    ctx.fillRect(cx - 24, cy - 48, 78, 40);
  } else if (s.family === "structure") {
    ctx.fillRect(cx - 54, cy - 10, 108, 78);
    ctx.beginPath(); ctx.moveTo(cx - 74, cy - 10); ctx.lineTo(cx, cy - 74); ctx.lineTo(cx + 74, cy - 10); ctx.fill();
  } else if (s.family !== "core" && s.family !== "torus") {
    ctx.beginPath(); ctx.arc(cx, cy + 16, 52, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx, cy - 52, 30, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = "#f5ff00";
  ctx.font = "700 16px Courier New";
  ctx.textAlign = "center";
  ctx.fillText(String(s.name || "SUBJECT").toUpperCase(), cx, h - 24);
}
"""


_SUBJECT_BUILDER_JS = r"""
  function buildRequestedSubject() {
    const s = activeSubject || {
      family: "mascot",
      kind: "organic",
      token: "subject",
      name: "Subject",
      features: [],
      colors: { body: 0x39ff14, accent: 0xff007f, detail: 0xf5ff00, eye: 0x111111 }
    };
    const kind = s.kind || "organic";
    const body = s.colors.body;
    const accent = s.colors.accent;
    const detail = s.colors.detail;
    const eyeC = s.colors.eye;
    const has = (feat) => (s.features || []).indexOf(feat) >= 0;

    function part(geo, color, x, y, z, rx, ry, rz, sx, sy, sz, partKind) {
      const mesh = new THREE.Mesh(geo, makeMat(color, false, 0x000000, partKind || kind));
      mesh.position.set(x || 0, y || 0, z || 0);
      mesh.rotation.set(rx || 0, ry || 0, rz || 0);
      mesh.scale.set(sx || 1, sy || 1, sz || 1);
      rootGroup.add(mesh);
      return mesh;
    }

    function eyeAt(x, y, z, scale) {
      const sc = scale || 1;
      const sign = z >= 0 ? 1 : -1;
      part(new THREE.SphereGeometry(0.09 * sc, 12, 10), 0xf7f7f7, x, y, z, 0, 0, 0, 1, 1, 1, "organic");
      part(new THREE.SphereGeometry(0.045 * sc, 10, 8), eyeC || 0x111111, x + 0.025 * sc, y, z + sign * 0.05 * sc, 0, 0, 0, 1, 1, 1, "organic");
    }

    function buildBird() {
      part(new THREE.SphereGeometry(1, 28, 20), body, -0.05, 0.2, 0, 0, 0, 0.15, 1.35, 1.02, 0.98);
      part(new THREE.SphereGeometry(0.34, 14, 12), body, 0.78, 0.78, 0);
      part(new THREE.SphereGeometry(0.5, 20, 16), body, 1.12, 1.28, 0);
      const beakLen = (s.token === "duck" || s.token === "goose") ? 1.05 : 0.78;
      const beakRad = (s.token === "duck" || s.token === "goose") ? 0.22 : 0.16;
      part(new THREE.ConeGeometry(beakRad, beakLen, 10), accent, 1.72, 1.22, 0, 0, 0, -Math.PI / 2, 1, 1, 0.78);
      part(new THREE.ConeGeometry(beakRad * 0.62, beakLen * 0.48, 8), accent, 1.62, 1.04, 0, 0, 0, -Math.PI / 2, 1, 1, 0.6);
      if (has("comb")) {
        for (let i = 0; i < 4; i++) {
          part(new THREE.SphereGeometry(0.13, 10, 8), detail, 0.92 + i * 0.14, 1.78 - Math.abs(i - 1.5) * 0.05, 0, 0, 0, 0, 0.62, 1.35, 0.42);
        }
        part(new THREE.SphereGeometry(0.12, 10, 8), detail, 1.48, 0.92, 0, 0, 0, 0, 0.65, 1.45, 0.45);
      }
      if (s.token === "penguin") {
        part(new THREE.SphereGeometry(0.62, 16, 12), accent, 0.18, 0.12, 0, 0, 0, 0, 0.72, 0.95, 0.48);
      }
      const eyeScale = has("bigeyes") ? 1.7 : 1;
      eyeAt(1.38, 1.4, 0.22, eyeScale);
      eyeAt(1.38, 1.4, -0.22, eyeScale);
      part(new THREE.SphereGeometry(0.58, 14, 10), body, 0.05, 0.28, 0.78, 0.15, 0.35, 0.9, 0.28, 0.95, 0.55);
      part(new THREE.SphereGeometry(0.58, 14, 10), body, 0.05, 0.28, -0.78, -0.15, -0.35, -0.9, 0.28, 0.95, 0.55);
      for (let i = -2; i <= 2; i++) {
        part(
          new THREE.ConeGeometry(0.14, 0.95, 6),
          i === 0 ? detail : body,
          -1.2,
          0.95,
          i * 0.2,
          -0.55,
          0,
          i * 0.22
        );
      }
      part(new THREE.CylinderGeometry(0.07, 0.06, 0.95, 8), accent, -0.08, -0.85, 0.22);
      part(new THREE.CylinderGeometry(0.07, 0.06, 0.95, 8), accent, -0.08, -0.85, -0.22);
      [-0.22, 0.22].forEach((z) => {
        part(new THREE.BoxGeometry(0.42, 0.05, 0.1), accent, 0.08, -1.32, z);
        part(new THREE.BoxGeometry(0.22, 0.05, 0.08), accent, -0.02, -1.32, z + (z > 0 ? 0.1 : -0.1));
      });
    }

    function buildQuadruped() {
      part(new THREE.SphereGeometry(0.82, 22, 16), body, 0, 0.32, 0, 0, 0, 0, 1.6, 0.82, 0.78);
      part(new THREE.SphereGeometry(0.42, 14, 12), body, 0.95, 0.55, 0);
      part(new THREE.SphereGeometry(0.4, 16, 14), body, 1.38, 0.82, 0);
      part(new THREE.SphereGeometry(0.2, 12, 10), accent, 1.74, 0.66, 0, 0, 0, 0, 1.35, 0.75, 0.9);
      part(new THREE.SphereGeometry(0.055, 8, 8), 0x222222, 1.96, 0.68, 0, 0, 0, 0, 1, 1, 1, "organic");
      const eyeScale = s.token === "frog" ? 1.8 : 1;
      eyeAt(1.5, 0.96, 0.16, eyeScale);
      eyeAt(1.5, 0.96, -0.16, eyeScale);
      const earH = (s.token === "rabbit" || s.token === "bunny") ? 0.9 : 0.4;
      part(new THREE.ConeGeometry(0.12, earH, 7), body, 1.28, 1.2, 0.16, 0.1, 0, 0.15);
      part(new THREE.ConeGeometry(0.12, earH, 7), body, 1.28, 1.2, -0.16, -0.1, 0, -0.15);
      [[0.55, 0.28], [0.55, -0.28], [-0.62, 0.28], [-0.62, -0.28]].forEach((p) => {
        part(new THREE.CylinderGeometry(0.11, 0.09, 0.82, 8), body, p[0], -0.42, p[1]);
      });
      if (s.token === "cat" || s.token === "kitten") {
        part(new THREE.CylinderGeometry(0.05, 0.08, 0.7, 6), body, -1.25, 0.85, 0, 0, 0, 0.9);
      } else if (s.token === "fox") {
        part(new THREE.ConeGeometry(0.16, 0.7, 6), accent, -1.35, 0.55, 0, 0, 0, Math.PI / 2);
      } else {
        part(new THREE.SphereGeometry(0.16, 10, 8), accent, -1.3, 0.5, 0, 0, 0, 0.4, 0.55, 1.2, 0.45);
      }
      if (s.token === "cow") {
        part(new THREE.SphereGeometry(0.16, 8, 8), detail, 0.2, 0.7, 0.32, 0, 0, 0, 1, 1, 1, "organic");
        part(new THREE.SphereGeometry(0.12, 8, 8), detail, -0.45, 0.55, -0.28, 0, 0, 0, 1, 1, 1, "organic");
      }
    }

    function buildBiped() {
      const metal = kind === "metal";
      if (metal) {
        part(new THREE.BoxGeometry(1.15, 1.35, 0.7), body, 0, 0.35, 0);
        part(new THREE.BoxGeometry(0.72, 0.55, 0.62), body, 0, 1.35, 0);
        if (has("visor") || has("skull")) {
          part(new THREE.BoxGeometry(0.64, 0.14, 0.66), accent, 0, 1.38, 0);
        } else {
          eyeAt(0.28, 1.42, 0.16);
          eyeAt(0.28, 1.42, -0.16);
        }
        part(new THREE.CylinderGeometry(0.035, 0.035, 0.38, 6), detail, 0.18, 1.78, 0);
      } else if (has("skull")) {
        part(new THREE.SphereGeometry(0.48, 16, 14), body, 0, 1.25, 0);
        part(new THREE.SphereGeometry(0.55, 14, 12), body, 0, 0.25, 0, 0, 0, 0, 0.7, 1.1, 0.45);
        eyeAt(0.28, 1.32, 0.16, 1.3);
        eyeAt(0.28, 1.32, -0.16, 1.3);
      } else {
        part(new THREE.SphereGeometry(0.58, 18, 14), body, 0, 0.3, 0, 0, 0, 0, 0.9, 1.2, 0.62);
        part(new THREE.SphereGeometry(0.4, 16, 14), accent, 0, 1.22, 0);
        eyeAt(0.22, 1.3, 0.15);
        eyeAt(0.22, 1.3, -0.15);
      }
      part(new THREE.CylinderGeometry(0.1, 0.08, 1.05, 8), body, 0, 0.25, 0.62, 0, 0, 0.25);
      part(new THREE.CylinderGeometry(0.1, 0.08, 1.05, 8), body, 0, 0.25, -0.62, 0, 0, -0.25);
      part(new THREE.CylinderGeometry(0.13, 0.11, 1.0, 8), body, -0.22, -0.72, 0);
      part(new THREE.CylinderGeometry(0.13, 0.11, 1.0, 8), body, 0.22, -0.72, 0);
    }

    function buildFish() {
      part(new THREE.SphereGeometry(0.72, 24, 16), body, 0.1, 0, 0, 0, 0, 0, 1.75, 0.72, 0.62);
      part(new THREE.ConeGeometry(0.36, 0.85, 8), accent, -1.25, 0.05, 0, 0, 0, Math.PI / 2);
      const finH = s.token === "shark" ? 0.7 : 0.45;
      part(new THREE.ConeGeometry(0.08, finH, 4), detail, -0.05, 0.55, 0);
      part(new THREE.SphereGeometry(0.16, 8, 8), accent, 0.25, -0.1, 0.42, 0, 0, 0.7, 0.35, 0.12, 0.55);
      part(new THREE.SphereGeometry(0.16, 8, 8), accent, 0.25, -0.1, -0.42, 0, 0, -0.7, 0.35, 0.12, 0.55);
      eyeAt(0.85, 0.12, 0.2);
      eyeAt(0.85, 0.12, -0.2);
    }

    function buildSerpent() {
      for (let i = 0; i < 9; i++) {
        const t = i / 8;
        const x = -1.7 + t * 3.1;
        const y = Math.sin(t * Math.PI) * 0.42;
        const rad = Math.max(0.12, 0.36 - t * 0.12);
        part(new THREE.SphereGeometry(rad, 14, 10), i % 2 ? accent : body, x, y, 0);
      }
      part(new THREE.SphereGeometry(0.42, 16, 12), body, 1.5, 0.5, 0);
      part(new THREE.ConeGeometry(0.12, 0.45, 8), accent, 1.92, 0.42, 0, 0, 0, -Math.PI / 2);
      eyeAt(1.62, 0.64, 0.16);
      eyeAt(1.62, 0.64, -0.16);
      if (has("wings")) {
        part(new THREE.SphereGeometry(0.72, 12, 8), detail, 0.25, 0.75, 0.95, 0.2, 0.4, 0.7, 0.12, 0.7, 1);
        part(new THREE.SphereGeometry(0.72, 12, 8), detail, 0.25, 0.75, -0.95, -0.2, -0.4, -0.7, 0.12, 0.7, 1);
      }
      if (has("horns")) {
        part(new THREE.ConeGeometry(0.08, 0.48, 6), detail, 1.4, 0.95, 0.12, 0.25, 0, 0.4);
        part(new THREE.ConeGeometry(0.08, 0.48, 6), detail, 1.4, 0.95, -0.12, -0.25, 0, -0.4);
      }
      if (has("fire")) {
        part(new THREE.ConeGeometry(0.16, 0.7, 8), 0xff5a00, 2.2, 0.42, 0, 0, 0, -Math.PI / 2, 1, 1, 1, "organic");
        part(new THREE.ConeGeometry(0.08, 0.4, 8), 0xf5ff00, 2.5, 0.42, 0, 0, 0, -Math.PI / 2, 1, 1, 1, "organic");
      }
    }

    function buildInsect() {
      const legs = (s.token === "spider" || s.token === "crab") ? 8 : 6;
      part(new THREE.SphereGeometry(0.55, 16, 12), body, -0.3, 0.15, 0, 0, 0, 0, s.token === "crab" ? 1.4 : 1.15, 0.8, 0.9);
      part(new THREE.SphereGeometry(0.32, 14, 12), accent, 0.5, 0.28, 0);
      eyeAt(0.7, 0.4, 0.12);
      eyeAt(0.7, 0.4, -0.12);
      if (has("wings")) {
        part(new THREE.SphereGeometry(0.4, 10, 8), 0xf4f4f4, 0.05, 0.45, 0.45, 0.4, 0.2, 0.4, 0.15, 0.7, 0.8, "organic");
        part(new THREE.SphereGeometry(0.4, 10, 8), 0xf4f4f4, 0.05, 0.45, -0.45, -0.4, -0.2, -0.4, 0.15, 0.7, 0.8, "organic");
      }
      for (let i = 0; i < legs; i++) {
        const side = i % 2 === 0 ? 1 : -1;
        const along = -0.5 + Math.floor(i / 2) * 0.28;
        part(new THREE.CylinderGeometry(0.03, 0.025, 0.85, 5), detail, along, -0.2, side * 0.62, side * 1.0, 0, 0);
      }
    }

    function buildCephalopod() {
      part(new THREE.SphereGeometry(0.85, 22, 16), body, 0, 0.75, 0, 0, 0, 0, 1, 0.9, 1);
      eyeAt(0.4, 0.8, 0.38, 1.3);
      eyeAt(0.4, 0.8, -0.38, 1.3);
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        for (let j = 0; j < 5; j++) {
          const radius = 0.32 + j * 0.24;
          const y = 0.2 - j * 0.28;
          part(
            new THREE.SphereGeometry(0.14 - j * 0.016, 8, 6),
            j % 2 ? accent : body,
            Math.cos(a) * radius,
            y,
            Math.sin(a) * radius
          );
        }
      }
    }

    function buildBlob() {
      if (has("planet") || s.token === "planet" || s.token === "earth" || s.token === "moon" || s.token === "globe") {
        part(new THREE.SphereGeometry(1.15, 28, 20), body, 0, 0, 0);
        part(new THREE.TorusGeometry(1.7, 0.08, 12, 40), accent, 0, 0, 0, Math.PI / 2.8, 0.2, 0);
        return;
      }
      if (has("heart") || s.token === "heart") {
        part(new THREE.SphereGeometry(0.55, 16, 12), detail, -0.32, 0.28, 0);
        part(new THREE.SphereGeometry(0.55, 16, 12), detail, 0.32, 0.28, 0);
        part(new THREE.ConeGeometry(0.78, 1.15, 4), detail, 0, -0.4, 0, Math.PI, 0, Math.PI / 4);
        return;
      }
      part(new THREE.SphereGeometry(1.15, 28, 20), body, 0, 0.15, 0, 0, 0, 0, 1.08, 0.9, 1);
      part(new THREE.SphereGeometry(0.42, 12, 10), accent, -0.75, -0.55, 0.15);
      part(new THREE.SphereGeometry(0.26, 10, 8), accent, 0.8, -0.7, -0.1);
      eyeAt(0.38, 0.28, 0.55, 1.4);
      eyeAt(0.38, 0.28, -0.55, 1.4);
    }

    function buildVehicle() {
      const flyer = has("wings") || has("thruster") || ["spaceship", "starship", "rocket", "plane", "airplane", "jet", "boat", "ship"].indexOf(s.token) >= 0;
      if (!flyer) {
        part(new THREE.BoxGeometry(2.5, 0.55, 1.2), body, 0, 0.15, 0);
        part(new THREE.BoxGeometry(1.15, 0.48, 1.02), accent, -0.15, 0.62, 0);
        [[0.78, 0.58], [0.78, -0.58], [-0.78, 0.58], [-0.78, -0.58]].forEach((p) => {
          part(new THREE.CylinderGeometry(0.28, 0.28, 0.18, 16), 0x222222, p[0], -0.28, p[1], Math.PI / 2, 0, 0, 1, 1, 1, "metal");
          part(new THREE.CylinderGeometry(0.12, 0.12, 0.2, 10), detail, p[0], -0.28, p[1], Math.PI / 2, 0, 0, 1, 1, 1, "metal");
        });
        part(new THREE.BoxGeometry(0.08, 0.16, 0.28), 0xf5ff66, 1.22, 0.18, 0.32, 0, 0, 0, 1, 1, 1, "organic");
        part(new THREE.BoxGeometry(0.08, 0.16, 0.28), 0xf5ff66, 1.22, 0.18, -0.32, 0, 0, 0, 1, 1, 1, "organic");
        return;
      }
      if (s.token === "boat" || s.token === "ship") {
        part(new THREE.BoxGeometry(2.2, 0.45, 0.9), body, 0, -0.1, 0);
        part(new THREE.ConeGeometry(0.55, 0.7, 4), body, 1.15, -0.05, 0, 0, Math.PI / 2, Math.PI / 2);
        part(new THREE.BoxGeometry(0.7, 0.45, 0.6), accent, -0.2, 0.32, 0);
        part(new THREE.CylinderGeometry(0.04, 0.04, 0.8, 6), detail, -0.2, 0.9, 0);
        return;
      }
      part(new THREE.CylinderGeometry(0.28, 0.42, 2.3, 14), body, 0, 0, 0, 0, 0, Math.PI / 2);
      part(new THREE.ConeGeometry(0.28, 0.7, 12), accent, 1.45, 0, 0, 0, 0, -Math.PI / 2);
      part(new THREE.BoxGeometry(0.55, 0.06, 1.7), detail, -0.1, 0, 0);
      part(new THREE.SphereGeometry(0.22, 12, 10), 0x9ad7ff, 0.4, 0.28, 0, 0, 0, 0, 1, 1, 1, "organic");
      part(new THREE.SphereGeometry(0.18, 10, 8), 0xff5a00, -1.2, 0, 0, 0, 0, 0, 1, 1, 1, "gel");
    }

    function buildStructure() {
      if (has("canopy") || s.token === "tree" || s.token === "pine") {
        part(new THREE.CylinderGeometry(0.16, 0.28, 1.35, 8), accent, 0, -0.25, 0);
        if (s.token === "pine") {
          part(new THREE.ConeGeometry(0.85, 1.1, 8), body, 0, 0.7, 0);
          part(new THREE.ConeGeometry(0.65, 0.9, 8), detail, 0, 1.35, 0);
        } else {
          part(new THREE.SphereGeometry(0.8, 16, 12), body, 0, 0.85, 0);
          part(new THREE.SphereGeometry(0.5, 12, 10), detail, 0.45, 1.15, 0.15);
          part(new THREE.SphereGeometry(0.42, 12, 10), body, -0.4, 1.2, -0.1);
        }
        return;
      }
      const tall = s.token === "tower" || s.token === "castle";
      const h = tall ? 2.3 : 1.3;
      part(new THREE.BoxGeometry(tall ? 1.25 : 1.8, h, tall ? 1.25 : 1.45), body, 0, h / 2 - 0.75, 0);
      part(new THREE.ConeGeometry(tall ? 0.95 : 1.35, tall ? 1.05 : 0.75, 4), detail, 0, h * 0.55 + 0.05, 0);
      const front = tall ? 0.64 : 0.74;
      part(new THREE.BoxGeometry(0.32, 0.55, 0.08), 0x4a2a16, 0, -0.5, front, 0, 0, 0, 1, 1, 1, "matte");
      part(new THREE.BoxGeometry(0.28, 0.28, 0.06), 0x9ad7ff, -0.42, 0.15, front, 0, 0, 0, 1, 1, 1, "organic");
      part(new THREE.BoxGeometry(0.28, 0.28, 0.06), 0x9ad7ff, 0.42, 0.15, front, 0, 0, 0, 1, 1, 1, "organic");
      if (tall) {
        part(new THREE.BoxGeometry(0.18, 0.55, 0.18), detail, 0.7, h * 0.35, 0);
      }
    }

    function buildProp() {
      if (has("teapot") || s.token === "teapot" || s.token === "kettle") {
        part(new THREE.SphereGeometry(0.75, 20, 16), body, 0, 0.05, 0, 0, 0, 0, 1.15, 0.85, 1);
        part(new THREE.CylinderGeometry(0.28, 0.34, 0.14, 12), accent, 0, 0.72, 0);
        part(new THREE.SphereGeometry(0.16, 10, 8), detail, 0, 0.9, 0);
        part(new THREE.CylinderGeometry(0.07, 0.1, 0.7, 8), body, 0.9, 0.18, 0, 0, 0, -1.15);
        part(new THREE.TorusGeometry(0.32, 0.06, 8, 18), accent, -0.72, 0.1, 0, 0, Math.PI / 2, 0);
        return;
      }
      if (has("sword") || s.token === "sword") {
        part(new THREE.BoxGeometry(0.12, 1.9, 0.04), accent, 0, 0.45, 0);
        part(new THREE.BoxGeometry(0.62, 0.1, 0.08), detail, 0, -0.55, 0);
        part(new THREE.CylinderGeometry(0.06, 0.05, 0.45, 8), body, 0, -0.85, 0);
        return;
      }
      if (has("chair") || s.token === "chair") {
        part(new THREE.BoxGeometry(0.9, 0.1, 0.9), body, 0, 0, 0);
        part(new THREE.BoxGeometry(0.9, 0.9, 0.1), accent, 0, 0.5, -0.4);
        [[0.35, 0.35], [0.35, -0.35], [-0.35, 0.35], [-0.35, -0.35]].forEach((p) => {
          part(new THREE.CylinderGeometry(0.05, 0.05, 0.55, 6), detail, p[0], -0.32, p[1]);
        });
        return;
      }
      buildMascot();
    }

    function buildMascot() {
      part(new THREE.SphereGeometry(0.78, 20, 16), body, 0, 0.1, 0);
      part(new THREE.SphereGeometry(0.46, 16, 14), accent, 0, 1.05, 0);
      eyeAt(0.18, 1.12, 0.18);
      eyeAt(0.18, 1.12, -0.18);
      part(new THREE.CylinderGeometry(0.09, 0.08, 0.7, 8), body, 0, -0.1, 0.55, 0.5, 0, 0);
      part(new THREE.CylinderGeometry(0.09, 0.08, 0.7, 8), body, 0, -0.1, -0.55, -0.5, 0, 0);
      part(new THREE.CylinderGeometry(0.12, 0.1, 0.7, 8), body, -0.22, -0.7, 0);
      part(new THREE.CylinderGeometry(0.12, 0.1, 0.7, 8), body, 0.22, -0.7, 0);
    }

    function addFeatureHats() {
      if (!has("mohawk") && !has("horns") && !has("crown")) return;
      const box = new THREE.Box3().setFromObject(rootGroup);
      if (box.isEmpty()) return;
      const top = box.max.y;
      const midX = (box.min.x + box.max.x) / 2;
      if (has("mohawk")) {
        for (let i = 0; i < 5; i++) {
          part(new THREE.ConeGeometry(0.09, 0.5, 5), detail, midX - 0.36 + i * 0.18, top + 0.08, 0, 0, 0, -0.15, 1, 1, 1, "organic");
        }
      }
      if (has("crown")) {
        part(new THREE.CylinderGeometry(0.28, 0.32, 0.22, 6), detail, midX, top + 0.05, 0, 0, 0, 0, 1, 1, 1, "metal");
      }
      if (has("horns") && s.family !== "serpent" && s.family !== "dino") {
        part(new THREE.ConeGeometry(0.09, 0.48, 6), detail, midX + 0.05, top, 0.18, 0.35, 0, 0.25);
        part(new THREE.ConeGeometry(0.09, 0.48, 6), detail, midX + 0.05, top, -0.18, -0.35, 0, -0.25);
      }
    }

    function frameSubject() {
      const box = new THREE.Box3().setFromObject(rootGroup);
      if (box.isEmpty()) return;
      const center = box.getCenter(new THREE.Vector3());
      rootGroup.children.forEach((child) => { child.position.sub(center); });
      const fitted = new THREE.Box3().setFromObject(rootGroup);
      const size = fitted.getSize(new THREE.Vector3());
      const groundY = fitted.min.y - 0.03;
      const radius = Math.max(size.x, size.z) * 0.5;
      const shadow = new THREE.Mesh(
        new THREE.CircleGeometry(Math.max(radius, 0.7), 28),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28, depthWrite: false })
      );
      shadow.rotation.x = -Math.PI / 2;
      shadow.position.y = groundY;
      rootGroup.add(shadow);
      if (!userAdjustedZoom) {
        const maxDim = Math.max(size.x, size.y, size.z, 0.8);
        zoom = Math.max(5.2, Math.min(14, maxDim * 1.6));
        fitZoom = zoom;
      }
    }

    const family = s.family;
    if (family === "bird") buildBird();
    else if (family === "quadruped") buildQuadruped();
    else if (family === "biped") buildBiped();
    else if (family === "fish") buildFish();
    else if (family === "serpent") buildSerpent();
    else if (family === "insect") buildInsect();
    else if (family === "cephalopod") buildCephalopod();
    else if (family === "blob") buildBlob();
    else if (family === "vehicle") buildVehicle();
    else if (family === "structure") buildStructure();
    else if (family === "prop") buildProp();
    else buildMascot();
    if (family !== "dino") addFeatureHats();
    frameSubject();
  }
"""
