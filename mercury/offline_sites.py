"""Offline landing-page and dashboard generators for the MercBot Application Forge.

Used only when no live frontier model is reachable. The theme, subject, copy, and
data domain are all derived from the prompt so a "cyberpunk generative UI landing
page" and a "minimal coffee shop website" produce visibly different products.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

_FONT_LINKS = {
    "Orbitron": "Orbitron:wght@500;700;900",
    "Inter": "Inter:wght@400;500;700;800",
    "Playfair Display": "Playfair+Display:wght@500;700;800",
    "Righteous": "Righteous",
    "Fraunces": "Fraunces:wght@400;600;800",
    "Fredoka": "Fredoka:wght@400;600;700",
    "Space Grotesk": "Space+Grotesk:wght@400;500;700",
    "JetBrains Mono": "JetBrains+Mono:wght@400;700",
}

THEMES: dict[str, dict[str, Any]] = {
    "cyberpunk": {
        "label": "Cyberpunk",
        "vars": {
            "bg": "#07040f", "surface": "#120a24", "surface2": "#1b0f36", "text": "#eef0ff",
            "muted": "#9a93c9", "primary": "#ff2bd6", "secondary": "#00f0ff", "accent": "#f5ff00",
            "border": "rgba(0,240,255,0.28)", "on-primary": "#07040f",
        },
        "heading": "Orbitron", "body": "Space Grotesk", "radius": "4px", "dark": True, "glow": True, "grid": True,
    },
    "retro": {
        "label": "Synthwave",
        "vars": {
            "bg": "#1a0b2e", "surface": "#2a1150", "surface2": "#3a1968", "text": "#fff0fb",
            "muted": "#c9a6e8", "primary": "#ff6ec7", "secondary": "#7afcff", "accent": "#ffd319",
            "border": "rgba(255,110,199,0.35)", "on-primary": "#1a0b2e",
        },
        "heading": "Righteous", "body": "Space Grotesk", "radius": "10px", "dark": True, "glow": True, "grid": True,
    },
    "acid": {
        "label": "Acid Punk",
        "vars": {
            "bg": "#050c07", "surface": "#09150d", "surface2": "#0f2216", "text": "#ecfff0",
            "muted": "#8ab896", "primary": "#39ff14", "secondary": "#ff007f", "accent": "#f5ff00",
            "border": "rgba(57,255,20,0.35)", "on-primary": "#050c07",
        },
        "heading": "JetBrains Mono", "body": "JetBrains Mono", "radius": "0px", "dark": True, "glow": True, "grid": True,
    },
    "minimal": {
        "label": "Minimal",
        "vars": {
            "bg": "#fafafa", "surface": "#ffffff", "surface2": "#f1f1f3", "text": "#111114",
            "muted": "#62626b", "primary": "#111114", "secondary": "#4f46e5", "accent": "#10b981",
            "border": "rgba(17,17,20,0.10)", "on-primary": "#ffffff",
        },
        "heading": "Inter", "body": "Inter", "radius": "14px", "dark": False, "glow": False, "grid": False,
    },
    "luxury": {
        "label": "Luxury",
        "vars": {
            "bg": "#0b0b0c", "surface": "#151517", "surface2": "#1d1d20", "text": "#f3efe6",
            "muted": "#a39f94", "primary": "#c9a45c", "secondary": "#e8d5a3", "accent": "#ffffff",
            "border": "rgba(201,164,92,0.28)", "on-primary": "#0b0b0c",
        },
        "heading": "Playfair Display", "body": "Inter", "radius": "2px", "dark": True, "glow": False, "grid": False,
    },
    "nature": {
        "label": "Organic",
        "vars": {
            "bg": "#f4f1ea", "surface": "#fffdf8", "surface2": "#ebe6da", "text": "#1f2a1f",
            "muted": "#5f6b5a", "primary": "#2f6b3a", "secondary": "#c58b3c", "accent": "#8fb573",
            "border": "rgba(47,107,58,0.16)", "on-primary": "#fffdf8",
        },
        "heading": "Fraunces", "body": "Inter", "radius": "18px", "dark": False, "glow": False, "grid": False,
    },
    "playful": {
        "label": "Playful",
        "vars": {
            "bg": "#fff7ed", "surface": "#ffffff", "surface2": "#ffeedd", "text": "#1e1b4b",
            "muted": "#6b6b8a", "primary": "#ff5e5b", "secondary": "#00b4b0", "accent": "#ffc23d",
            "border": "rgba(30,27,75,0.12)", "on-primary": "#ffffff",
        },
        "heading": "Fredoka", "body": "Fredoka", "radius": "22px", "dark": False, "glow": False, "grid": False,
    },
    "corporate": {
        "label": "Corporate",
        "vars": {
            "bg": "#f5f7fb", "surface": "#ffffff", "surface2": "#eef2f8", "text": "#0f172a",
            "muted": "#475569", "primary": "#1d4ed8", "secondary": "#0ea5e9", "accent": "#f59e0b",
            "border": "rgba(15,23,42,0.10)", "on-primary": "#ffffff",
        },
        "heading": "Inter", "body": "Inter", "radius": "10px", "dark": False, "glow": False, "grid": False,
    },
    "dark": {
        "label": "Modern Dark",
        "vars": {
            "bg": "#0b0d12", "surface": "#141821", "surface2": "#1b2130", "text": "#e8ecf3",
            "muted": "#8b93a7", "primary": "#7c5cff", "secondary": "#22d3ee", "accent": "#f472b6",
            "border": "rgba(124,92,255,0.22)", "on-primary": "#ffffff",
        },
        "heading": "Space Grotesk", "body": "Inter", "radius": "14px", "dark": True, "glow": True, "grid": False,
    },
}

_THEME_RULES: list[tuple[str, str]] = [
    ("cyberpunk", r"cyber\s*punk|\bcyber\b|\bneon\b|blade\s*runner|\bhacker|\bmatrix\b|\bdystopi"),
    ("retro", r"synth\s*wave|vapor\s*wave|\bretro\b|\b80s\b|outrun|arcade"),
    ("acid", r"\bacid\b|\bpunk\b|grunge|\bzine\b|brutalis"),
    ("luxury", r"luxur|elegan|premium|high[- ]end|\bgold\b|boutique|jewel"),
    ("nature", r"\bnature\b|\beco\b|organic|garden|\bplant|forest|sustainab|\bfarm|botanic"),
    ("playful", r"playful|\bfun\b|\bkids?\b|\bcute\b|colou?rful|bubbly|cartoon"),
    ("corporate", r"corporate|enterprise|professional|\bb2b\b|fintech|\bbank|consult|\blaw\b|insurance"),
    ("minimal", r"minimal|\bclean\b|\bsimple\b|apple[- ]like|swiss|\bwhite\b"),
    ("dark", r"\bdark\b|\bsleek\b|\bmodern\b"),
]

_STYLE_WORDS = (
    r"cyber\s*punk|cyber|neon|synth\s*wave|vapor\s*wave|retro|80s|outrun|acid|punk|grunge|zine|brutalist|"
    r"luxury|luxurious|elegant|premium|high[- ]end|minimal|minimalist|minimalistic|clean|simple|sleek|modern|"
    r"dark|light|playful|fun|cute|colorful|colourful|bubbly|corporate|professional|enterprise|organic|eco|"
    r"cool|awesome|sick|beautiful|stunning|amazing|epic|gorgeous|slick|futuristic|bold|nice|pretty|"
    r"responsive|interactive|animated|polished|themed|style|styled|looking"
)
_PAGE_WORDS = (
    r"landing\s*pages?|websites?|web\s*sites?|web\s*pages?|home\s*pages?|homepages?|sites?|pages?|"
    r"one[- ]pager|splash\s*page|marketing\s*(?:site|page)|product\s*page|pricing\s*page|"
    r"dashboards?|admin\s*panel|analytics|panel|app|application|ui\s*kit"
)

_ACRONYMS = {"ui", "ux", "ai", "api", "saas", "crm", "vr", "ar", "3d", "2d", "nft", "seo", "llm", "gpt", "iot", "b2b", "dj", "hr"}


def detect_theme(text: str) -> str:
    lowered = (text or "").lower()
    for theme_id, pattern in _THEME_RULES:
        if re.search(pattern, lowered):
            return theme_id
    return "dark"


def _titleize(words: list[str]) -> str:
    out = []
    for w in words:
        lw = w.lower()
        out.append(lw.upper() if lw in _ACRONYMS else (w if w[:1].isupper() and len(w) > 1 and w[1:].islower() else w.capitalize()))
    return " ".join(out)


def extract_subject(display_name: str, brief: str) -> dict[str, str]:
    """Pull the product/brand the user is asking for out of the prompt."""
    text = (brief or display_name or "").strip()
    named = re.search(r"\b(?:called|named|for brand|brand(?:ed)? as)\s+[\"']?([A-Za-z0-9][\w&.' -]{1,40})", text, re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:please\s+)?(?:build|create|make|forge|generate|design|scaffold|code|write)\s+(?:me\s+|us\s+)?", "", text, flags=re.IGNORECASE)
    for_match = re.search(r"\b(?:for|about)\s+(?:a|an|the|my|our)?\s*([A-Za-z0-9][\w&' -]{1,50})", cleaned, re.IGNORECASE)
    cleaned = re.sub(rf"\b(?:{_PAGE_WORDS})\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(rf"\b(?:{_STYLE_WORDS})\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:a|an|the|my|our|with|and|for|about|that|which|is|of|in|to|some|really|very|super)\b", " ", cleaned, flags=re.IGNORECASE)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&'+-]*", cleaned)
    if for_match:
        tail = re.sub(rf"\b(?:{_PAGE_WORDS}|{_STYLE_WORDS})\b", " ", for_match.group(1), flags=re.IGNORECASE)
        tail_words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&'+-]*", tail)
        tail_words = [w for w in tail_words if w.lower() not in ("a", "an", "the", "my", "our", "with", "and")]
        if tail_words:
            words = tail_words
    subject = _titleize(words[:4]) if words else "Your Product"
    brand = named.group(1).strip().rstrip(".") if named else subject
    return {"subject": subject, "brand": brand}


def _sub(text: str, ctx: dict[str, str]) -> str:
    return text.replace("{subject}", ctx["subject"]).replace("{brand}", ctx["brand"]).replace("{subject_lower}", ctx["subject"].lower())


_DOMAINS: list[tuple[str, str]] = [
    ("generative", r"generative|\bgen\s*ai\b|\bai\b|\bllm|\bgpt|prompt|copilot|\bagents?\b|machine learning|neural"),
    ("portfolio", r"portfolio|photograph|\bdesigner\b|\bartist\b|resume|\bcv\b|freelanc|illustrat"),
    ("food", r"coffee|\bcafe\b|caf[eé]|restaurant|bakery|pizza|\bfood\b|\bbar\b|kitchen|brew|burger|sushi|tea\b"),
    ("fitness", r"fitness|\bgym\b|workout|yoga|health|wellness|training|\brun(?:ning)?\b|nutrition"),
    ("music", r"\bmusic|\bband\b|\bdj\b|festival|concert|album|\btour\b|podcast|\bevent\b|conference"),
    ("game", r"\bgames?\b|gaming|esports|\bplayers?\b|\bstudio\b"),
    ("crypto", r"crypto|web3|\bnft|blockchain|\bdefi\b|\btoken|wallet|trading|fintech|invest"),
    ("agency", r"agency|consult|marketing|branding|creative studio|\bseo\b"),
    ("software", r"\bapp\b|saas|platform|software|\btool\b|startup|\bproduct\b|\bapi\b|developer"),
]

_CONTENT: dict[str, dict[str, Any]] = {
    "generative": {
        "eyebrow": "Prompt in. Interface out.",
        "headline": "{brand} turns a sentence into a working interface",
        "sub": "Describe the screen you need. {brand} composes real components, wires the states, and hands you code you can ship the same afternoon.",
        "cta": "Generate a UI", "cta2": "See how it works",
        "features": [
            ("Prompt-to-component", "Type what you need in plain language and get layout, components, and copy generated live."),
            ("Design-token aware", "Every generated screen inherits your colors, type scale, spacing, and radius automatically."),
            ("Stateful by default", "Forms validate, toggles toggle, lists filter. Generated UI is interactive, not a screenshot."),
            ("Export real code", "Copy clean HTML, React, or Vue output with semantic markup and accessible labels."),
            ("Iterate by chatting", "\"Make the CTA louder\" or \"add a pricing toggle\" edits the screen in place."),
            ("Guardrails built in", "Contrast checks, keyboard focus order, and responsive breakpoints are verified on every render."),
        ],
        "steps": [("Describe", "Write the screen you want: \"pricing table for a coffee subscription\"."), ("Generate", "{brand} composes components and states from your design system."), ("Ship", "Refine by chat, then export production-ready code.")],
        "stats": [(12, "ms", "median component render"), (480, "+", "component patterns"), (99, "%", "AA contrast pass rate")],
        "offers_title": "Plans", "offers_kind": "pricing",
        "offers": [
            ("Hacker", 0, "For tinkering on side projects", ["50 generations / month", "HTML export", "Community themes"]),
            ("Studio", 29, "For product teams shipping weekly", ["Unlimited generations", "React + Vue export", "Custom design tokens", "Version history"]),
            ("Enterprise", 99, "For orgs with a design system", ["SSO & audit logs", "Private component registry", "On-prem model routing", "Priority support"]),
        ],
        "testimonials": [
            ("We prototyped an entire onboarding flow in one standup.", "Rhea Okafor", "Product Lead, Lumen"),
            ("It respects our tokens better than half our engineers do.", "Marco Viel", "Design Systems, Northwind"),
            ("The exported code passed review on the first try.", "Jin Park", "Staff Engineer, Patchwork"),
        ],
        "faq": [
            ("Is the generated UI real code?", "Yes. Every preview is rendered from the same markup you export, with working states and accessible labels."),
            ("Can it use my design system?", "Import your tokens or component library and every generation stays on-brand."),
            ("Which frameworks are supported?", "HTML/CSS, React, and Vue today, with Svelte in preview."),
            ("Do you train on my prompts?", "No. Prompts and outputs stay in your workspace and are never used for training."),
        ],
        "demo": "generative",
    },
    "portfolio": {
        "eyebrow": "Selected work",
        "headline": "{brand}: work that earns a second look",
        "sub": "A portfolio of projects, process, and results. Browse the case studies, then get in touch.",
        "cta": "View projects", "cta2": "Contact",
        "features": [
            ("Brand identity", "Logos, systems, and guidelines that scale from favicon to billboard."),
            ("Product design", "Flows and interfaces tested with real users before a single pixel ships."),
            ("Art direction", "Campaign visuals with a point of view and a consistent voice."),
            ("Motion", "Micro-interactions and launch films that make products feel alive."),
            ("Photography", "Editorial and product shoots, lit and graded in-house."),
            ("Workshops", "Discovery sprints that align teams before the expensive decisions."),
        ],
        "steps": [("Discover", "We map goals, audience, and constraints together."), ("Design", "Concepts, critique, and iteration in short loops."), ("Deliver", "Final assets, documentation, and handoff support.")],
        "stats": [(64, "", "projects shipped"), (11, "", "years of practice"), (23, "", "awards & features")],
        "offers_title": "Case studies", "offers_kind": "projects",
        "offers": [
            ("Northwind Rebrand", None, "Identity system for a logistics scale-up", ["Logo & type system", "Fleet livery", "+38% brand recall"]),
            ("Lumen App", None, "Habit app redesign from research to launch", ["12 user interviews", "New onboarding", "4.8 store rating"]),
            ("Field Notes", None, "Editorial photo series for a travel magazine", ["9 countries", "Print + web", "Cover feature"]),
        ],
        "testimonials": [
            ("Clear thinking, beautiful execution, zero drama.", "Ana Ruiz", "CMO, Northwind"),
            ("Our conversion jumped the week the redesign launched.", "Sam Lee", "Founder, Lumen"),
            ("The rare collaborator who makes everyone sharper.", "Priya Das", "Editor, Field Notes"),
        ],
        "faq": [
            ("Are you available for new projects?", "Booking projects starting next quarter. Short engagements can start sooner."),
            ("What does a typical project cost?", "Most engagements land between two and eight weeks. Fixed quotes after a discovery call."),
            ("Do you work remotely?", "Yes, with clients across time zones, plus on-site workshops when it helps."),
            ("Can you work with my in-house team?", "Absolutely. Embedding with existing teams is a favorite way to work."),
        ],
        "demo": "",
    },
    "food": {
        "eyebrow": "Fresh daily",
        "headline": "{brand}, made slowly and served warm",
        "sub": "Small-batch, seasonal, and made by people who care. Stop by, order ahead, or book a table tonight.",
        "cta": "Order ahead", "cta2": "See the menu",
        "features": [
            ("Seasonal menu", "Ingredients from growers within a day's drive, changing with what's at its best."),
            ("Made in-house", "Breads, sauces, and syrups made from scratch every morning."),
            ("Order ahead", "Skip the line. Your order is ready at the counter when you arrive."),
            ("Private events", "Book the back room for birthdays, launches, and long dinners."),
            ("Loyalty that's simple", "Every tenth visit is on us. No app required."),
            ("Neighborhood first", "Day-old goods go to the community pantry every evening."),
        ],
        "steps": [("Browse", "Check today's menu and specials."), ("Order", "Pick up, dine in, or reserve a table."), ("Enjoy", "Come hungry. Leave happy.")],
        "stats": [(1200, "+", "cups and plates a week"), (14, "", "local suppliers"), (4.9, "★", "average rating")],
        "offers_title": "Menu highlights", "offers_kind": "menu",
        "offers": [
            ("House Signature", 6.5, "The one regulars order without looking", ["Seasonal", "Best seller"]),
            ("Morning Plate", 12, "Eggs, sourdough, greens, and house jam", ["Vegetarian option", "Until 2pm"]),
            ("Sunset Special", 18, "Chef's rotating evening plate", ["Changes weekly", "Pairs with wine"]),
        ],
        "testimonials": [
            ("My whole week is planned around this place.", "Dana K.", "Regular since day one"),
            ("Friendly staff and the best thing I've eaten this year.", "Luis M.", "Local guide"),
            ("We booked the back room for our launch. Flawless.", "Tess W.", "Event host"),
        ],
        "faq": [
            ("Do you take reservations?", "Yes, for groups of any size. Walk-ins are always welcome too."),
            ("Are there vegan options?", "Every section of the menu has at least one vegan dish."),
            ("Do you cater?", "We cater events up to 120 guests. Ask us for a custom menu."),
            ("Where do you source ingredients?", "From farms and roasters within a 200-mile radius whenever possible."),
        ],
        "demo": "",
    },
    "fitness": {
        "eyebrow": "Train with intent",
        "headline": "{brand}: get stronger every single week",
        "sub": "Coaching, programming, and accountability that fit your schedule. Show up, we'll handle the plan.",
        "cta": "Start free week", "cta2": "View programs",
        "features": [
            ("Personal programming", "Workouts built around your goals, history, and the equipment you actually have."),
            ("Expert coaches", "Certified coaches review your form and adjust your plan every week."),
            ("Progress tracking", "Lifts, runs, and recovery in one timeline so you can see the trend."),
            ("Nutrition guidance", "Simple targets and real meals. No crash diets."),
            ("Community classes", "Small-group sessions that make showing up the easy part."),
            ("Recovery tools", "Mobility, sleep, and deload weeks planned in, not bolted on."),
        ],
        "steps": [("Assess", "A 20-minute intake to understand where you are."), ("Train", "Follow your plan, in person or anywhere."), ("Progress", "Weekly check-ins keep you moving forward.")],
        "stats": [(3400, "+", "members coached"), (27, "%", "average strength gain in 12 weeks"), (92, "%", "still training after 6 months")],
        "offers_title": "Memberships", "offers_kind": "pricing",
        "offers": [
            ("Open Gym", 39, "Train on your own schedule", ["24/7 access", "Program library", "App tracking"]),
            ("Coached", 129, "A coach in your corner", ["Custom program", "Weekly check-ins", "Form reviews", "Nutrition targets"]),
            ("1:1 Elite", 249, "Maximum results, fastest", ["Private sessions", "Daily messaging", "Recovery protocol", "Quarterly testing"]),
        ],
        "testimonials": [
            ("Deadlift up 60 pounds and my back finally stopped hurting.", "Chris A.", "Member, 1 year"),
            ("The coaches notice everything. In a good way.", "Mia T.", "Coached plan"),
            ("I actually look forward to Mondays now.", "Raj P.", "Community classes"),
        ],
        "faq": [
            ("I'm a total beginner. Is that okay?", "Most members started from zero. Your plan starts where you are."),
            ("Can I train from home?", "Yes. Programs adapt to home equipment or no equipment at all."),
            ("Is there a contract?", "No contracts. Cancel any time from your account."),
            ("What's in the free week?", "Full access to classes, the app, and one coach consultation."),
        ],
        "demo": "",
    },
    "music": {
        "eyebrow": "Live. Loud. Together.",
        "headline": "{brand}: the night you'll still be talking about",
        "sub": "New music, live dates, and moments you had to be there for. Grab tickets before they're gone.",
        "cta": "Get tickets", "cta2": "Listen now",
        "features": [
            ("Live shows", "Full production sets in venues big and small."),
            ("New releases", "Fresh tracks every season, first on our mailing list."),
            ("Behind the scenes", "Studio sessions, rehearsal clips, and tour diaries."),
            ("Merch drops", "Limited runs designed for each tour."),
            ("VIP experiences", "Soundcheck access, meet & greets, and early entry."),
            ("Community", "A crowd that sings every word back."),
        ],
        "steps": [("Pick a date", "Find the show closest to you."), ("Grab tickets", "Secure checkout, mobile tickets."), ("Show up loud", "Doors open early. Don't miss the opener.")],
        "stats": [(86, "", "shows this year"), (12, "M", "streams"), (31, "", "cities")],
        "offers_title": "Upcoming dates", "offers_kind": "tickets",
        "offers": [
            ("Brooklyn Steel", 45, "Sat, Nov 14 · Doors 7pm", ["General admission", "All ages"]),
            ("The Fillmore", 55, "Fri, Nov 20 · Doors 8pm", ["Balcony seating", "21+"]),
            ("Red Rocks", 79, "Sat, Dec 5 · Doors 6pm", ["Outdoor amphitheatre", "VIP available"]),
        ],
        "testimonials": [
            ("Best live show I've seen in a decade.", "Jordan R.", "Fan since the first EP"),
            ("The energy in that room was unreal.", "Sky M.", "Front row, Chicago"),
            ("Bought tickets for the next tour on the drive home.", "Alex P.", "Superfan"),
        ],
        "faq": [
            ("Are tickets refundable?", "Tickets are transferable, and refundable if a show is cancelled or rescheduled."),
            ("Is there an age limit?", "Varies by venue. Each date lists its age policy."),
            ("Can I bring a camera?", "Phones yes, professional cameras need a media pass."),
            ("How do VIP packages work?", "VIP includes early entry, soundcheck access, and exclusive merch."),
        ],
        "demo": "",
    },
    "game": {
        "eyebrow": "Now in early access",
        "headline": "{brand}: drop in, gear up, outplay everyone",
        "sub": "Fast matches, deep strategy, and a world that changes every season. Your squad is waiting.",
        "cta": "Play free", "cta2": "Watch trailer",
        "features": [
            ("Fast matches", "Fifteen-minute rounds that never overstay their welcome."),
            ("Deep loadouts", "Hundreds of builds with no pay-to-win shortcuts."),
            ("Living world", "Seasonal map changes and story events driven by the community."),
            ("Cross-play", "PC, console, and handheld in the same lobby."),
            ("Ranked ladder", "Skill-based matchmaking with transparent ratings."),
            ("Creator tools", "Build custom modes and share them in a tap."),
        ],
        "steps": [("Download", "Free on every major platform."), ("Squad up", "Party with friends or match with locals."), ("Climb", "Earn rewards every season.")],
        "stats": [(2, "M", "players"), (140, "+", "unique abilities"), (60, "fps", "on handhelds")],
        "offers_title": "Editions", "offers_kind": "pricing",
        "offers": [
            ("Free to Play", 0, "Everything you need to compete", ["All maps & modes", "Ranked play", "Seasonal events"]),
            ("Founder", 19, "Support development, look great", ["Founder skins", "Battle pass S1", "Name badge"]),
            ("Legend", 49, "The full collector experience", ["Everything in Founder", "Digital artbook", "Soundtrack", "Beta access"]),
        ],
        "testimonials": [
            ("Haven't had this much fun with friends in years.", "xNova", "Diamond rank"),
            ("Every patch makes it better. Devs actually listen.", "Kestrel", "Founding player"),
            ("The creator tools are absurdly good.", "PixelPunk", "Mode builder"),
        ],
        "faq": [
            ("Is it really free?", "Yes. Every gameplay item can be earned by playing."),
            ("What platforms are supported?", "PC, PlayStation, Xbox, Switch, and Steam Deck with full cross-play."),
            ("Is there a single-player mode?", "Bot matches and a story prologue are available offline."),
            ("When is full release?", "Full launch is planned after three early-access seasons."),
        ],
        "demo": "",
    },
    "crypto": {
        "eyebrow": "Built on-chain",
        "headline": "{brand}: move value at the speed of the internet",
        "sub": "Non-custodial, audited, and fast. Trade, stake, and track everything from one dashboard.",
        "cta": "Launch app", "cta2": "Read the docs",
        "features": [
            ("Self-custody", "Your keys, your assets. Connect any wallet in seconds."),
            ("Audited contracts", "Three independent audits and a live bug bounty."),
            ("Low fees", "Batched settlement keeps costs a fraction of a cent."),
            ("Real-time analytics", "Positions, yields, and risk updated every block."),
            ("Multi-chain", "Bridge across the major networks without leaving the app."),
            ("Governance", "Token holders vote on every protocol parameter."),
        ],
        "steps": [("Connect", "Link the wallet you already use."), ("Deposit", "Move assets in with one signature."), ("Earn", "Stake, trade, or provide liquidity.")],
        "stats": [(1.8, "B", "total volume"), (99.99, "%", "uptime"), (0.002, "$", "avg fee")],
        "offers_title": "Tiers", "offers_kind": "pricing",
        "offers": [
            ("Explorer", 0, "Everything to get started", ["Swap & stake", "Portfolio view", "Community support"]),
            ("Pro", 15, "For active traders", ["Advanced orders", "API access", "Fee rebates", "Tax exports"]),
            ("Institutional", 199, "For funds and treasuries", ["Multi-sig workflows", "Dedicated RPC", "Compliance reports", "24/7 desk"]),
        ],
        "testimonials": [
            ("Fastest settlement we've integrated with.", "Ivy Chen", "CTO, Ledgerline"),
            ("The analytics alone replaced three tools.", "Omar F.", "Trader"),
            ("Clean UX for something this powerful.", "Nadia B.", "DeFi researcher"),
        ],
        "faq": [
            ("Is my money custodied?", "Never. Assets stay in your wallet and contracts you can verify."),
            ("Which wallets work?", "Any WalletConnect wallet, plus browser and hardware wallets."),
            ("Has the protocol been audited?", "Yes, by three independent firms. Reports are public."),
            ("What chains are supported?", "Ethereum, the major L2s, and Solana, with more voted in by governance."),
        ],
        "demo": "",
    },
    "agency": {
        "eyebrow": "Strategy · Design · Growth",
        "headline": "{brand} builds brands people choose on purpose",
        "sub": "We partner with ambitious teams to sharpen positioning, design standout experiences, and grow faster.",
        "cta": "Start a project", "cta2": "Our work",
        "features": [
            ("Positioning", "Find the story only you can tell and make it the center of everything."),
            ("Identity", "Visual systems built to flex across every touchpoint."),
            ("Web experiences", "Fast, accessible sites that convert visitors into customers."),
            ("Content", "Campaigns, video, and copy that people actually share."),
            ("Performance", "Paid and organic growth measured against real revenue."),
            ("Enablement", "Guidelines and training so your team keeps the momentum."),
        ],
        "steps": [("Listen", "Workshops with your team and your customers."), ("Make", "Design and build in tight, visible sprints."), ("Grow", "Launch, measure, and improve together.")],
        "stats": [(140, "+", "brands launched"), (3.4, "x", "avg pipeline growth"), (18, "", "industry awards")],
        "offers_title": "Engagements", "offers_kind": "pricing",
        "offers": [
            ("Sprint", 8, "Two-week focused project (k)", ["Positioning workshop", "Messaging framework", "Launch plan"]),
            ("Brand", 35, "Full identity engagement (k)", ["Strategy & naming", "Identity system", "Website", "Guidelines"]),
            ("Partner", 15, "Ongoing growth partner (k/mo)", ["Dedicated pod", "Campaigns", "Performance marketing", "Monthly reporting"]),
        ],
        "testimonials": [
            ("They found the story we'd been circling for years.", "Elena G.", "CEO, Brightside"),
            ("Pipeline doubled within two quarters.", "Tom H.", "VP Growth, Arcline"),
            ("A true extension of our team.", "Grace O.", "CMO, Fieldwork"),
        ],
        "faq": [
            ("What size companies do you work with?", "From seed-stage startups to public companies, usually teams of 10 to 2,000."),
            ("How soon can we start?", "Sprints can start within two weeks. Larger engagements in four to six."),
            ("Do you work with in-house teams?", "Yes. Most projects are collaborative, with shared tools and rituals."),
            ("How do you measure success?", "We agree on business metrics up front and report against them."),
        ],
        "demo": "",
    },
    "software": {
        "eyebrow": "Now available",
        "headline": "{brand} does the busywork so your team can do the real work",
        "sub": "Everything you need to plan, ship, and measure in one fast, focused workspace. Set up in minutes, loved for years.",
        "cta": "Start free", "cta2": "Book a demo",
        "features": [
            ("Fast by design", "Every action is under 100ms. No spinners, no waiting."),
            ("Works with your stack", "Two-way sync with the tools your team already uses."),
            ("Automations", "Trigger workflows from events and stop doing repetitive tasks."),
            ("Real-time collaboration", "See changes as they happen, with presence and comments."),
            ("Insights", "Dashboards that answer questions before they're asked."),
            ("Secure", "SSO, granular permissions, and SOC 2 Type II compliance."),
        ],
        "steps": [("Sign up", "Create a workspace in under a minute."), ("Connect", "Import data and link your tools."), ("Ship", "Automate the routine and focus on what matters.")],
        "stats": [(10, "k+", "teams"), (40, "%", "less time in meetings"), (99.9, "%", "uptime SLA")],
        "offers_title": "Pricing", "offers_kind": "pricing",
        "offers": [
            ("Starter", 0, "For individuals and tiny teams", ["Up to 3 users", "Core features", "Community support"]),
            ("Team", 12, "For growing teams", ["Unlimited users", "Automations", "Integrations", "Priority support"]),
            ("Business", 32, "For organizations at scale", ["SSO & SCIM", "Audit logs", "Advanced analytics", "Dedicated manager"]),
        ],
        "testimonials": [
            ("We replaced four tools and nobody misses them.", "Lena M.", "Head of Ops, Kite"),
            ("Onboarding took an afternoon. Adoption took a week.", "Ben C.", "Engineering Manager, Tessel"),
            ("The automations pay for the whole subscription.", "Aisha N.", "COO, Brightloop"),
        ],
        "faq": [
            ("Is there a free plan?", "Yes. The Starter plan is free forever for up to three users."),
            ("Can I import my data?", "One-click imports from the most popular tools, plus CSV and API."),
            ("Is my data secure?", "Encrypted in transit and at rest, with SOC 2 Type II and GDPR compliance."),
            ("Can I cancel anytime?", "Yes. Monthly plans cancel instantly, annual plans pro-rate."),
        ],
        "demo": "",
    },
}


def detect_domain(text: str) -> str:
    lowered = (text or "").lower()
    for domain_id, pattern in _DOMAINS:
        if re.search(pattern, lowered):
            return domain_id
    return "software"


def _theme_css(theme: dict[str, Any]) -> str:
    vars_css = "\n".join(f"  --{k}: {v};" for k, v in theme["vars"].items())
    return (
        ":root {\n"
        f"{vars_css}\n"
        f"  --radius: {theme['radius']};\n"
        f"  --font-heading: '{theme['heading']}', 'Segoe UI', system-ui, sans-serif;\n"
        f"  --font-body: '{theme['body']}', 'Segoe UI', system-ui, sans-serif;\n"
        "}\n"
    )


def _font_link(theme: dict[str, Any]) -> str:
    families = []
    for name in {theme["heading"], theme["body"]}:
        if name in _FONT_LINKS:
            families.append(f"family={_FONT_LINKS[name]}")
    if not families:
        return ""
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com" />\n  '
        f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{"&amp;".join(sorted(families))}&amp;display=swap" />'
    )


_LANDING_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  line-height: 1.6;
  overflow-x: hidden;
}
a { color: inherit; text-decoration: none; }
img { max-width: 100%; display: block; }
.container { width: min(1160px, 92vw); margin: 0 auto; }
h1, h2, h3 { font-family: var(--font-heading); line-height: 1.12; letter-spacing: -0.01em; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--secondary);
}
.eyebrow::before { content: ""; width: 26px; height: 2px; background: currentColor; }
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 14px 24px; border-radius: var(--radius); font-weight: 700; font-size: 15px;
  border: 1px solid transparent; cursor: pointer; font-family: var(--font-body);
  transition: transform .18s ease, box-shadow .18s ease, background .18s ease, color .18s ease;
}
.btn:hover { transform: translateY(-2px); }
.btn-primary { background: var(--primary); color: var(--on-primary); }
.btn-ghost { background: transparent; color: var(--text); border-color: var(--border); }
.btn-ghost:hover { border-color: var(--secondary); color: var(--secondary); }
.theme-glow .btn-primary { box-shadow: 0 0 0 1px var(--primary), 0 0 28px color-mix(in srgb, var(--primary) 55%, transparent); }

/* Nav */
.nav {
  position: fixed; inset: 0 0 auto 0; z-index: 50;
  transition: background .25s ease, border-color .25s ease, backdrop-filter .25s ease;
  border-bottom: 1px solid transparent;
}
.nav.scrolled { background: color-mix(in srgb, var(--bg) 82%, transparent); backdrop-filter: blur(14px); border-color: var(--border); }
.nav-inner { display: flex; align-items: center; justify-content: space-between; height: 72px; }
.brand { font-family: var(--font-heading); font-weight: 800; font-size: 20px; display: flex; align-items: center; gap: 10px; }
.brand-mark {
  width: 30px; height: 30px; border-radius: calc(var(--radius) / 2 + 4px);
  background: linear-gradient(135deg, var(--primary), var(--secondary));
}
.nav-links { display: flex; gap: 30px; font-size: 15px; color: var(--muted); }
.nav-links a:hover { color: var(--text); }
.nav-actions { display: flex; gap: 10px; align-items: center; }
.menu-toggle { display: none; background: none; border: 1px solid var(--border); color: var(--text); border-radius: var(--radius); padding: 8px 10px; cursor: pointer; }

/* Hero */
.hero { position: relative; min-height: 100vh; display: flex; align-items: center; padding: 120px 0 80px; overflow: hidden; }
.hero-bg { position: absolute; inset: 0; z-index: 0; }
.hero-bg canvas { width: 100%; height: 100%; display: block; }
.hero-grid-overlay {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: radial-gradient(ellipse at 50% 40%, black 10%, transparent 70%);
  opacity: .45;
}
.hero-blob { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .45; z-index: 0; }
.hero-blob.a { width: 520px; height: 520px; background: var(--primary); top: -140px; right: -120px; }
.hero-blob.b { width: 420px; height: 420px; background: var(--secondary); bottom: -160px; left: -120px; }
.hero-inner { position: relative; z-index: 1; display: grid; grid-template-columns: 1.05fr 1fr; gap: 56px; align-items: center; }
.hero h1 { font-size: clamp(40px, 5.6vw, 72px); font-weight: 800; margin: 18px 0 20px; }
.hero h1 .hl { background: linear-gradient(90deg, var(--primary), var(--secondary)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero p.lead { font-size: 19px; color: var(--muted); max-width: 560px; }
.hero-ctas { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 34px; }
.hero-trust { margin-top: 34px; display: flex; gap: 12px; align-items: center; color: var(--muted); font-size: 14px; }
.avatars { display: flex; }
.avatars span { width: 34px; height: 34px; border-radius: 50%; border: 2px solid var(--bg); margin-left: -10px; background: linear-gradient(135deg, var(--secondary), var(--primary)); }
.avatars span:first-child { margin-left: 0; }

.hero-visual {
  position: relative; border: 1px solid var(--border); border-radius: calc(var(--radius) + 6px);
  background: color-mix(in srgb, var(--surface) 88%, transparent); backdrop-filter: blur(10px);
  padding: 22px; min-height: 360px;
}
.theme-glow .hero-visual { box-shadow: 0 30px 80px -30px color-mix(in srgb, var(--primary) 45%, transparent); }
.visual-bar { display: flex; gap: 7px; margin-bottom: 18px; }
.visual-bar i { width: 11px; height: 11px; border-radius: 50%; background: var(--surface2); }
.visual-bar i:nth-child(1) { background: var(--primary); }
.visual-bar i:nth-child(2) { background: var(--accent); }
.visual-bar i:nth-child(3) { background: var(--secondary); }
.visual-card { background: var(--surface2); border-radius: var(--radius); padding: 16px; margin-bottom: 12px; }
.visual-row { display: flex; gap: 12px; }
.visual-row .visual-card { flex: 1; }
.bar-line { height: 10px; border-radius: 6px; background: color-mix(in srgb, var(--text) 14%, transparent); margin: 8px 0; }
.bar-line.w60 { width: 60%; } .bar-line.w80 { width: 80%; } .bar-line.w40 { width: 40%; }
.bar-line.prim { background: var(--primary); }
.mini-chart { display: flex; align-items: flex-end; gap: 6px; height: 90px; }
.mini-chart b { flex: 1; border-radius: 4px 4px 0 0; background: linear-gradient(to top, var(--primary), var(--secondary)); animation: rise 2.4s ease-in-out infinite alternate; }
@keyframes rise { from { transform: scaleY(.55); } to { transform: scaleY(1); } }
.mini-chart b { transform-origin: bottom; }

/* Generative playground */
.playground { display: flex; flex-direction: column; gap: 14px; }
.playground-input { display: flex; gap: 10px; }
.playground-input input {
  flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--text);
  border-radius: var(--radius); padding: 12px 14px; font-family: var(--font-body); font-size: 15px; outline: none;
}
.playground-input input:focus { border-color: var(--secondary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--secondary) 25%, transparent); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  font-size: 12px; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--border);
  color: var(--muted); cursor: pointer; background: transparent; font-family: var(--font-body);
}
.chip:hover { color: var(--secondary); border-color: var(--secondary); }
.gen-tabs { display: flex; gap: 6px; }
.gen-tabs button { font-size: 12px; padding: 6px 12px; border-radius: var(--radius); border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; font-family: var(--font-body); }
.gen-tabs button.active { background: var(--surface2); color: var(--text); border-color: var(--secondary); }
.gen-output { min-height: 250px; border: 1px dashed var(--border); border-radius: var(--radius); padding: 16px; background: var(--bg); position: relative; }
.gen-output.loading::after {
  content: "composing components…"; position: absolute; inset: 0; display: grid; place-items: center;
  background: color-mix(in srgb, var(--bg) 82%, transparent); color: var(--secondary); font-size: 14px; letter-spacing: .08em;
}
.gen-code { display: none; white-space: pre-wrap; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 12px; color: var(--secondary); max-height: 300px; overflow: auto; }
.gen-status { font-size: 12px; color: var(--muted); }
.g-component { animation: pop .45s cubic-bezier(.2,.8,.2,1.2) both; }
@keyframes pop { from { opacity: 0; transform: translateY(10px) scale(.98); } to { opacity: 1; transform: none; } }
.g-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-bottom: 10px; }
.g-title { font-family: var(--font-heading); font-weight: 700; font-size: 16px; margin-bottom: 6px; }
.g-muted { color: var(--muted); font-size: 13px; }
.g-row { display: flex; gap: 10px; flex-wrap: wrap; }
.g-row > * { flex: 1; min-width: 120px; }
.g-price { font-size: 26px; font-weight: 800; font-family: var(--font-heading); }
.g-input { width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px; color: var(--text); margin: 6px 0; font-family: var(--font-body); }
.g-btn { background: var(--primary); color: var(--on-primary); border: none; border-radius: var(--radius); padding: 10px 14px; font-weight: 700; cursor: pointer; width: 100%; margin-top: 6px; font-family: var(--font-body); }
.g-toggle { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.g-switch { width: 38px; height: 22px; border-radius: 999px; background: var(--surface2); position: relative; cursor: pointer; border: 1px solid var(--border); }
.g-switch::after { content: ""; position: absolute; width: 16px; height: 16px; border-radius: 50%; top: 2px; left: 2px; background: var(--muted); transition: all .2s ease; }
.g-switch.on { background: var(--primary); }
.g-switch.on::after { left: 18px; background: var(--on-primary); }
.g-bars { display: flex; align-items: flex-end; gap: 6px; height: 80px; margin-top: 8px; }
.g-bars b { flex: 1; background: linear-gradient(to top, var(--primary), var(--secondary)); border-radius: 3px 3px 0 0; }
.g-list-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; cursor: pointer; }
.g-list-item.done span { text-decoration: line-through; color: var(--muted); }
.g-check { width: 18px; height: 18px; border-radius: 5px; border: 2px solid var(--secondary); flex-shrink: 0; }
.g-list-item.done .g-check { background: var(--secondary); }
.g-avatar { width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), var(--secondary)); flex: 0 0 48px; }
.g-bubble { padding: 9px 12px; border-radius: 14px; font-size: 14px; margin: 6px 0; max-width: 80%; }
.g-bubble.me { background: var(--primary); color: var(--on-primary); margin-left: auto; }
.g-bubble.them { background: var(--surface2); }
.g-tile { aspect-ratio: 1; border-radius: var(--radius); background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 70%, var(--bg)), color-mix(in srgb, var(--secondary) 70%, var(--bg))); }

/* Sections */
section.block { padding: 110px 0; position: relative; }
.section-head { text-align: center; max-width: 720px; margin: 0 auto 60px; }
.section-head h2 { font-size: clamp(30px, 4vw, 46px); margin: 14px 0; }
.section-head p { color: var(--muted); font-size: 18px; }
.logos { padding: 34px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.logos-row { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 26px; color: var(--muted); font-family: var(--font-heading); font-weight: 700; font-size: 18px; letter-spacing: .06em; opacity: .7; }
.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.feature {
  background: var(--surface); border: 1px solid var(--border); border-radius: calc(var(--radius) + 4px);
  padding: 28px; transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}
.feature:hover { transform: translateY(-4px); border-color: var(--secondary); }
.theme-glow .feature:hover { box-shadow: 0 0 34px -10px var(--secondary); }
.feature-icon {
  width: 46px; height: 46px; border-radius: var(--radius); display: grid; place-items: center; margin-bottom: 18px;
  background: color-mix(in srgb, var(--primary) 16%, transparent); color: var(--primary); font-weight: 800; font-family: var(--font-heading);
}
.feature h3 { font-size: 19px; margin-bottom: 10px; }
.feature p { color: var(--muted); font-size: 15px; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; counter-reset: step; }
.step { padding: 30px; border-radius: calc(var(--radius) + 4px); background: linear-gradient(160deg, var(--surface), var(--surface2)); border: 1px solid var(--border); position: relative; }
.step-num { font-family: var(--font-heading); font-size: 46px; font-weight: 900; color: var(--primary); opacity: .9; line-height: 1; }
.step h3 { margin: 14px 0 8px; font-size: 21px; }
.step p { color: var(--muted); }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; text-align: center; }
.stat-num { font-family: var(--font-heading); font-size: clamp(40px, 5vw, 60px); font-weight: 800; color: var(--text); }
.stat-num .unit { color: var(--primary); }
.stat-label { color: var(--muted); }
.offers-toggle { display: flex; justify-content: center; align-items: center; gap: 12px; margin: -30px 0 40px; color: var(--muted); font-size: 15px; }
.switch { width: 52px; height: 28px; border-radius: 999px; background: var(--surface2); border: 1px solid var(--border); position: relative; cursor: pointer; }
.switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: var(--primary); transition: left .2s ease; }
.switch.on::after { left: 27px; }
.save-badge { background: color-mix(in srgb, var(--accent) 22%, transparent); color: var(--text); padding: 3px 9px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.offers-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; align-items: stretch; }
.offer {
  background: var(--surface); border: 1px solid var(--border); border-radius: calc(var(--radius) + 6px);
  padding: 32px; display: flex; flex-direction: column; gap: 14px; position: relative;
}
.offer.featured { border-color: var(--primary); transform: scale(1.03); }
.theme-glow .offer.featured { box-shadow: 0 0 60px -18px var(--primary); }
.offer-tag { position: absolute; top: -13px; left: 50%; transform: translateX(-50%); background: var(--primary); color: var(--on-primary); padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 800; letter-spacing: .06em; }
.offer h3 { font-size: 22px; }
.offer .price { font-family: var(--font-heading); font-size: 44px; font-weight: 800; }
.offer .price small { font-size: 15px; color: var(--muted); font-weight: 500; }
.offer .desc { color: var(--muted); font-size: 15px; }
.offer ul { list-style: none; display: flex; flex-direction: column; gap: 10px; margin: 6px 0 14px; flex: 1; }
.offer li { display: flex; gap: 10px; font-size: 15px; }
.offer li::before { content: "✓"; color: var(--secondary); font-weight: 800; }
.offer .visual { height: 150px; border-radius: var(--radius); background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 55%, var(--surface)), color-mix(in srgb, var(--secondary) 55%, var(--surface))); }
.testimonial-wrap { max-width: 820px; margin: 0 auto; text-align: center; min-height: 230px; }
.testimonial { display: none; }
.testimonial.active { display: block; animation: fadeUp .6s ease both; }
.testimonial blockquote { font-family: var(--font-heading); font-size: clamp(22px, 3vw, 32px); line-height: 1.35; margin-bottom: 24px; }
.testimonial cite { font-style: normal; color: var(--muted); }
.testimonial cite strong { color: var(--text); display: block; }
.dots { display: flex; justify-content: center; gap: 10px; margin-top: 26px; }
.dots button { width: 10px; height: 10px; border-radius: 50%; border: none; background: var(--surface2); cursor: pointer; }
.dots button.active { background: var(--primary); width: 28px; border-radius: 6px; }
.faq { max-width: 820px; margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }
.faq-item { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.faq-q { width: 100%; text-align: left; background: none; border: none; color: var(--text); font-size: 17px; font-weight: 700; padding: 20px 22px; display: flex; justify-content: space-between; cursor: pointer; font-family: var(--font-body); }
.faq-q span { transition: transform .25s ease; color: var(--primary); }
.faq-item.open .faq-q span { transform: rotate(45deg); }
.faq-a { max-height: 0; overflow: hidden; transition: max-height .3s ease; color: var(--muted); padding: 0 22px; }
.faq-item.open .faq-a { max-height: 200px; padding-bottom: 20px; }
.cta-band {
  border-radius: calc(var(--radius) + 10px); padding: 70px 40px; text-align: center; position: relative; overflow: hidden;
  background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 85%, var(--bg)), color-mix(in srgb, var(--secondary) 75%, var(--bg)));
  color: var(--on-primary);
}
.cta-band h2 { font-size: clamp(30px, 4vw, 48px); margin-bottom: 14px; }
.cta-band p { opacity: .85; margin-bottom: 28px; font-size: 18px; }
.signup { display: flex; gap: 10px; max-width: 520px; margin: 0 auto; }
.signup input { flex: 1; padding: 14px 16px; border-radius: var(--radius); border: none; font-size: 15px; font-family: var(--font-body); }
.signup .btn { background: var(--bg); color: var(--text); }
.signup-msg { margin-top: 14px; font-weight: 700; min-height: 22px; }
footer { padding: 60px 0 40px; border-top: 1px solid var(--border); margin-top: 80px; color: var(--muted); }
.footer-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 30px; margin-bottom: 40px; }
.footer-grid h4 { color: var(--text); margin-bottom: 14px; font-family: var(--font-heading); }
.footer-grid a { display: block; padding: 4px 0; font-size: 15px; }
.footer-grid a:hover { color: var(--secondary); }
.footer-bottom { display: flex; justify-content: space-between; font-size: 14px; flex-wrap: wrap; gap: 10px; }
.to-top { position: fixed; right: 22px; bottom: 22px; width: 46px; height: 46px; border-radius: 50%; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; opacity: 0; pointer-events: none; transition: opacity .2s ease; z-index: 40; font-size: 18px; }
.to-top.show { opacity: 1; pointer-events: auto; }
.reveal { opacity: 0; transform: translateY(26px); transition: opacity .7s ease, transform .7s ease; }
.reveal.in { opacity: 1; transform: none; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

/* Glitch for neon themes */
.theme-glow .glitch { position: relative; }
.theme-glow .glitch::before, .theme-glow .glitch::after {
  content: attr(data-text); position: absolute; inset: 0; pointer-events: none; opacity: 0;
}
.theme-grid .glitch.glitching::before { opacity: .8; color: var(--secondary); transform: translate(3px, -2px); clip-path: inset(10% 0 55% 0); }
.theme-grid .glitch.glitching::after { opacity: .8; color: var(--primary); transform: translate(-3px, 2px); clip-path: inset(60% 0 8% 0); }

@media (max-width: 960px) {
  .hero-inner { grid-template-columns: 1fr; }
  .features-grid, .offers-grid, .steps, .stats { grid-template-columns: 1fr; }
  .offer.featured { transform: none; }
  .footer-grid { grid-template-columns: 1fr 1fr; }
  .nav-links { display: none; position: absolute; top: 72px; left: 0; right: 0; flex-direction: column; background: var(--surface); padding: 20px 4vw; border-bottom: 1px solid var(--border); }
  .nav-links.open { display: flex; }
  .menu-toggle { display: block; }
  .nav-actions .btn-ghost { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""


_LANDING_JS = r"""
const CFG = JSON.parse(document.getElementById("site-config").textContent);

const nav = document.querySelector(".nav");
const toTop = document.querySelector(".to-top");
window.addEventListener("scroll", () => {
  nav.classList.toggle("scrolled", window.scrollY > 20);
  toTop.classList.toggle("show", window.scrollY > 700);
});
toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

const menuToggle = document.querySelector(".menu-toggle");
const navLinks = document.querySelector(".nav-links");
menuToggle.addEventListener("click", () => navLinks.classList.toggle("open"));
navLinks.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => navLinks.classList.remove("open")));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("in");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });
document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));

function formatStat(value, decimals) {
  return decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString();
}
const statObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    const el = entry.target;
    const target = parseFloat(el.dataset.value);
    const decimals = (el.dataset.value.split(".")[1] || "").length;
    const start = performance.now();
    const duration = 1600;
    function tick(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = formatStat(target * eased, decimals);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    statObserver.unobserve(el);
  });
}, { threshold: 0.4 });
document.querySelectorAll("[data-value]").forEach((el) => statObserver.observe(el));

const billingSwitch = document.getElementById("billingSwitch");
if (billingSwitch) {
  billingSwitch.addEventListener("click", () => {
    const yearly = billingSwitch.classList.toggle("on");
    billingSwitch.setAttribute("aria-checked", String(yearly));
    document.querySelectorAll("[data-monthly]").forEach((el) => {
      const monthly = parseFloat(el.dataset.monthly);
      const shown = yearly ? Math.round(monthly * 0.8) : monthly;
      el.querySelector(".amt").textContent = shown === 0 ? "Free" : CFG.currency + shown;
      el.querySelector("small").textContent = shown === 0 ? "" : (yearly ? " /mo, billed yearly" : " /mo");
    });
  });
}

const testimonials = Array.from(document.querySelectorAll(".testimonial"));
const dotsWrap = document.querySelector(".dots");
let tIndex = 0;
let tTimer = null;
function showTestimonial(i) {
  tIndex = (i + testimonials.length) % testimonials.length;
  testimonials.forEach((t, idx) => t.classList.toggle("active", idx === tIndex));
  dotsWrap.querySelectorAll("button").forEach((d, idx) => d.classList.toggle("active", idx === tIndex));
}
testimonials.forEach((_, i) => {
  const dot = document.createElement("button");
  dot.setAttribute("aria-label", "Show testimonial " + (i + 1));
  dot.addEventListener("click", () => { showTestimonial(i); restartTestimonials(); });
  dotsWrap.appendChild(dot);
});
function restartTestimonials() {
  clearInterval(tTimer);
  tTimer = setInterval(() => showTestimonial(tIndex + 1), 6000);
}
showTestimonial(0);
restartTestimonials();

document.querySelectorAll(".faq-item").forEach((item) => {
  item.querySelector(".faq-q").addEventListener("click", () => {
    const open = item.classList.contains("open");
    document.querySelectorAll(".faq-item").forEach((other) => other.classList.remove("open"));
    if (!open) item.classList.add("open");
  });
});

const signupForm = document.getElementById("signupForm");
const signupMsg = document.getElementById("signupMsg");
signupForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const email = signupForm.email.value.trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    signupMsg.textContent = "That email doesn't look right. Try again?";
    return;
  }
  const list = JSON.parse(localStorage.getItem("signups") || "[]");
  list.push({ email, at: new Date().toISOString() });
  localStorage.setItem("signups", JSON.stringify(list));
  signupForm.reset();
  signupMsg.textContent = "You're in. Check " + email + " for next steps.";
});

document.getElementById("year").textContent = new Date().getFullYear();

const glitchEl = document.querySelector(".glitch");
if (glitchEl && document.body.classList.contains("theme-grid")) {
  setInterval(() => {
    glitchEl.classList.add("glitching");
    setTimeout(() => glitchEl.classList.remove("glitching"), 180);
  }, 3800);
}

/* Animated hero background */
(function heroCanvas() {
  const canvas = document.getElementById("heroCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const styles = getComputedStyle(document.documentElement);
  const colors = [styles.getPropertyValue("--primary").trim(), styles.getPropertyValue("--secondary").trim(), styles.getPropertyValue("--accent").trim()];
  const bg = styles.getPropertyValue("--bg").trim();
  let w = 0, h = 0, particles = [];
  const mouse = { x: -9999, y: -9999 };
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(900, Math.floor((w * h) / 2600));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h, life: Math.random() * 200,
      c: colors[Math.floor(Math.random() * colors.length)]
    }));
    ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
  }
  function field(x, y, t) {
    return Math.sin(x * 0.0021 + t * 0.00025) * 2.1 + Math.cos(y * 0.0024 - t * 0.0002) * 2.1 + Math.sin((x + y) * 0.0009);
  }
  window.addEventListener("resize", resize);
  canvas.parentElement.addEventListener("mousemove", (e) => {
    const r = canvas.getBoundingClientRect();
    mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top;
  });
  resize();
  function frame(t) {
    ctx.globalAlpha = 0.08;
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 0.9;
    for (const p of particles) {
      const a = field(p.x, p.y, t);
      let vx = Math.cos(a) * 1.3, vy = Math.sin(a) * 1.3;
      const dx = p.x - mouse.x, dy = p.y - mouse.y, d2 = dx * dx + dy * dy;
      if (d2 < 14000) { vx += dx / 40; vy += dy / 40; }
      ctx.fillStyle = p.c;
      ctx.fillRect(p.x, p.y, 1.6, 1.6);
      p.x += vx; p.y += vy; p.life -= 1;
      if (p.life < 0 || p.x < 0 || p.x > w || p.y < 0 || p.y > h) {
        p.x = Math.random() * w; p.y = Math.random() * h; p.life = 120 + Math.random() * 180;
      }
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

/* Generative UI playground */
(function playground() {
  const form = document.getElementById("genForm");
  if (!form) return;
  const input = document.getElementById("genPrompt");
  const out = document.getElementById("genOutput");
  const code = document.getElementById("genCode");
  const status = document.getElementById("genStatus");
  const tabs = document.querySelectorAll(".gen-tabs button");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const STOP = new Set("a an the for with and or to of in on my our me make build create generate show give i want need please some that this".split(" "));

  function nouns(prompt) {
    return prompt.toLowerCase().replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w));
  }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function topic(prompt, skip) {
    const words = nouns(prompt).filter((w) => !skip.includes(w));
    return words.length ? words.slice(0, 2).map(cap).join(" ") : "Your Product";
  }

  const COMPONENTS = [
    { id: "pricing", keys: ["pricing", "price", "plan", "plans", "subscription", "tier", "tiers", "checkout"], render(t) {
      const plans = [["Basic", 9], ["Pro", 24], ["Team", 59]];
      return `<div class="g-row">${plans.map(([n, p], i) => `<div class="g-card"><div class="g-title">${n}</div><div class="g-muted">${esc(t)} ${i === 1 ? "· most popular" : ""}</div><div class="g-price">$${p}<span class="g-muted">/mo</span></div><button class="g-btn" data-act="toast" data-msg="${n} plan selected">Choose ${n}</button></div>`).join("")}</div>`;
    } },
    { id: "login", keys: ["login", "signin", "sign", "signup", "register", "auth", "account", "password"], render(t) {
      return `<div class="g-card" style="max-width:340px;margin:0 auto"><div class="g-title">Welcome to ${esc(t)}</div><div class="g-muted">Sign in to continue</div><input class="g-input" placeholder="Email" type="email"><input class="g-input" placeholder="Password" type="password"><button class="g-btn" data-act="validate">Sign in</button><div class="g-muted g-msg" style="margin-top:8px"></div></div>`;
    } },
    { id: "form", keys: ["form", "contact", "survey", "feedback", "booking", "reservation", "rsvp", "newsletter"], render(t) {
      return `<div class="g-card"><div class="g-title">${esc(t)}</div><div class="g-row"><input class="g-input" placeholder="Full name"><input class="g-input" placeholder="Email"></div><textarea class="g-input" rows="3" placeholder="Tell us more"></textarea><button class="g-btn" data-act="validate">Submit</button><div class="g-muted g-msg" style="margin-top:8px"></div></div>`;
    } },
    { id: "stats", keys: ["dashboard", "analytics", "stats", "metrics", "chart", "kpi", "revenue", "sales", "report", "graph"], render(t) {
      const kpis = [["Revenue", "$48.2k", "+12%"], ["Users", "9,481", "+8%"], ["Churn", "1.9%", "-0.4%"]];
      const bars = Array.from({ length: 14 }, () => 25 + Math.round(Math.random() * 75));
      return `<div class="g-row">${kpis.map(([k, v, d]) => `<div class="g-card"><div class="g-muted">${k}</div><div class="g-price">${v}</div><div class="g-muted">${d} vs last week</div></div>`).join("")}</div><div class="g-card"><div class="g-title">${esc(t)} · last 14 days</div><div class="g-bars">${bars.map((b) => `<b style="height:${b}%"></b>`).join("")}</div></div>`;
    } },
    { id: "profile", keys: ["profile", "user", "team", "member", "card", "contact", "author", "bio"], render(t) {
      return `<div class="g-card"><div style="display:flex;gap:14px;align-items:center"><div class="g-avatar"></div><div><div class="g-title">Avery Quinn</div><div class="g-muted">${esc(t)} · Lead Designer</div></div></div><div class="g-row" style="margin-top:12px"><button class="g-btn" data-act="toast" data-msg="Following Avery">Follow</button><button class="g-btn" style="background:var(--surface2);color:var(--text)" data-act="toast" data-msg="Message sent">Message</button></div></div>`;
    } },
    { id: "todo", keys: ["todo", "task", "tasks", "checklist", "list", "kanban", "planner"], render(t) {
      const items = ["Draft " + t.toLowerCase() + " brief", "Review with the team", "Ship the first version", "Collect feedback"];
      return `<div class="g-card"><div class="g-title">${esc(t)} checklist</div>${items.map((it, i) => `<div class="g-list-item ${i === 0 ? "done" : ""}" data-act="check"><div class="g-check"></div><span>${esc(it)}</span></div>`).join("")}</div>`;
    } },
    { id: "settings", keys: ["settings", "preferences", "toggle", "notifications", "privacy", "options"], render(t) {
      const opts = ["Email notifications", "Dark mode", "Weekly digest", "Two-factor auth"];
      return `<div class="g-card"><div class="g-title">${esc(t)} settings</div>${opts.map((o, i) => `<div class="g-toggle"><span>${o}</span><div class="g-switch ${i % 2 === 0 ? "on" : ""}" data-act="switch"></div></div>`).join("")}</div>`;
    } },
    { id: "chat", keys: ["chat", "message", "messages", "messenger", "support", "assistant", "bot"], render(t) {
      return `<div class="g-card"><div class="g-title">${esc(t)} chat</div><div class="g-bubble them">Hi! How can I help with ${esc(t.toLowerCase())} today?</div><div class="g-bubble me">Show me what's new.</div><div class="g-bubble them">Three new features shipped this week. Want a tour?</div><div class="g-row"><input class="g-input g-chat-in" placeholder="Type a message"><button class="g-btn" style="flex:0 0 90px" data-act="send">Send</button></div></div>`;
    } },
    { id: "gallery", keys: ["gallery", "photos", "images", "portfolio", "grid", "showcase", "products", "shop", "store"], render(t) {
      return `<div class="g-card"><div class="g-title">${esc(t)}</div><div class="g-row">${Array.from({ length: 4 }, (_, i) => `<div><div class="g-tile" style="filter:hue-rotate(${i * 35}deg)"></div><div class="g-muted" style="margin-top:6px">${esc(t)} ${i + 1}</div></div>`).join("")}</div></div>`;
    } },
    { id: "hero", keys: ["hero", "landing", "banner", "header", "homepage", "website"], render(t) {
      return `<div class="g-card" style="text-align:center;padding:26px"><div class="g-muted">Introducing</div><div class="g-title" style="font-size:24px">${esc(t)}</div><div class="g-muted">The fastest way to get from idea to launch.</div><div class="g-row" style="max-width:320px;margin:12px auto 0"><button class="g-btn" data-act="toast" data-msg="Welcome aboard">Get started</button></div></div>`;
    } },
  ];

  function compose(prompt) {
    const words = nouns(prompt);
    const picked = COMPONENTS.filter((c) => c.keys.some((k) => words.includes(k)));
    const used = picked.length ? picked.slice(0, 3) : [COMPONENTS.find((c) => c.id === "hero"), COMPONENTS.find((c) => c.id === "stats")];
    const skip = used.flatMap((c) => c.keys);
    const t = topic(prompt, skip);
    return { t, html: used.map((c) => `<div class="g-component" data-component="${c.id}">${c.render(t)}</div>`).join(""), used: used.map((c) => c.id) };
  }

  function generate(prompt) {
    if (!prompt.trim()) { input.focus(); return; }
    out.classList.add("loading");
    status.textContent = "Parsing intent…";
    setTimeout(() => { status.textContent = "Selecting components…"; }, 250);
    setTimeout(() => {
      const res = compose(prompt);
      out.innerHTML = res.html;
      code.textContent = res.html.replace(/></g, ">\n<");
      out.classList.remove("loading");
      status.textContent = `Generated ${res.used.length} component${res.used.length > 1 ? "s" : ""} (${res.used.join(", ")}) for "${res.t}"`;
    }, 650);
  }

  out.addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const act = el.dataset.act;
    if (act === "switch") el.classList.toggle("on");
    if (act === "check") el.classList.toggle("done");
    if (act === "toast") { status.textContent = el.dataset.msg; }
    if (act === "validate") {
      const card = el.closest(".g-card");
      const empty = Array.from(card.querySelectorAll(".g-input")).filter((i) => !i.value.trim());
      card.querySelector(".g-msg").textContent = empty.length ? `Please fill ${empty.length} more field${empty.length > 1 ? "s" : ""}.` : "Submitted. Thanks!";
    }
    if (act === "send") {
      const card = el.closest(".g-card");
      const inp = card.querySelector(".g-chat-in");
      if (!inp.value.trim()) return;
      const bubble = document.createElement("div");
      bubble.className = "g-bubble me";
      bubble.textContent = inp.value;
      inp.parentElement.before(bubble);
      inp.value = "";
      setTimeout(() => {
        const reply = document.createElement("div");
        reply.className = "g-bubble them";
        reply.textContent = "Got it. Generating that now.";
        card.querySelector(".g-row").before(reply);
      }, 500);
    }
  });

  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    const showCode = tab.dataset.view === "code";
    code.style.display = showCode ? "block" : "none";
    out.style.display = showCode ? "none" : "block";
  }));
  document.querySelectorAll(".chip").forEach((chip) => chip.addEventListener("click", () => {
    input.value = chip.textContent;
    generate(chip.textContent);
  }));
  form.addEventListener("submit", (e) => { e.preventDefault(); generate(input.value); });
  generate(CFG.demoSeed);
})();
"""


def _offer_card(item: tuple, idx: int, kind: str, currency: str) -> str:
    name, price, desc, bullets = item
    featured = idx == 1
    tag = '<span class="offer-tag">MOST POPULAR</span>' if featured and kind == "pricing" else ""
    bullets_html = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
    if kind == "pricing":
        amt = "Free" if price == 0 else f"{currency}{price:g}"
        suffix = "" if price == 0 else " /mo"
        price_html = f'<div class="price" data-monthly="{price}"><span class="amt">{amt}</span><small>{suffix}</small></div>'
        cta = f'<a class="btn {"btn-primary" if featured else "btn-ghost"}" href="#signup">Choose {html.escape(name)}</a>'
    elif kind in ("menu", "tickets"):
        price_html = f'<div class="price">{currency}{price:g}</div>'
        label = "Buy tickets" if kind == "tickets" else "Add to order"
        cta = f'<a class="btn {"btn-primary" if featured else "btn-ghost"}" href="#signup">{label}</a>'
    else:
        price_html = '<div class="visual"></div>'
        cta = '<a class="btn btn-ghost" href="#signup">Read case study</a>'
    return (
        f'<article class="offer reveal{" featured" if featured else ""}">{tag}'
        f"<h3>{html.escape(name)}</h3>{price_html}"
        f'<p class="desc">{html.escape(desc)}</p><ul>{bullets_html}</ul>{cta}</article>'
    )


def build_landing_page_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    prompt = f"{display_name} {brief}"
    theme_id = detect_theme(prompt)
    theme = THEMES[theme_id]
    domain_id = detect_domain(prompt)
    content = _CONTENT[domain_id]
    ctx = extract_subject(display_name, brief)
    wants_generative_canvas = bool(re.search(r"generative|particle|flow|animated|motion|3d|immersive", prompt, re.IGNORECASE)) or theme["glow"]
    show_playground = content["demo"] == "generative"
    currency = "$"
    esc = html.escape

    headline = _sub(content["headline"], ctx)
    brand = ctx["brand"]
    if brand in headline:
        head_html = esc(headline).replace(esc(brand), f'<span class="hl">{esc(brand)}</span>', 1)
    else:
        head_html = esc(headline)

    nav_items = [("Features", "#features"), ("How it works", "#how"), (content["offers_title"], "#offers"), ("FAQ", "#faq")]
    nav_links = "".join(f'<a href="{href}">{esc(label)}</a>' for label, href in nav_items)

    feature_cards = "".join(
        f'<article class="feature reveal"><div class="feature-icon">{i + 1:02d}</div>'
        f"<h3>{esc(_sub(t, ctx))}</h3><p>{esc(_sub(b, ctx))}</p></article>"
        for i, (t, b) in enumerate(content["features"])
    )
    steps = "".join(
        f'<div class="step reveal"><div class="step-num">{i + 1:02d}</div><h3>{esc(_sub(t, ctx))}</h3><p>{esc(_sub(b, ctx))}</p></div>'
        for i, (t, b) in enumerate(content["steps"])
    )
    stats = "".join(
        f'<div class="reveal"><div class="stat-num"><span data-value="{v}">0</span><span class="unit">{esc(u)}</span></div>'
        f'<div class="stat-label">{esc(_sub(l, ctx))}</div></div>'
        for v, u, l in content["stats"]
    )
    offers = "".join(_offer_card(item, i, content["offers_kind"], currency) for i, item in enumerate(content["offers"]))
    billing_toggle = (
        '<div class="offers-toggle"><span>Monthly</span>'
        '<div class="switch" id="billingSwitch" role="switch" aria-checked="false" tabindex="0"></div>'
        '<span>Yearly</span><span class="save-badge">Save 20%</span></div>'
        if content["offers_kind"] == "pricing"
        else ""
    )
    testimonials = "".join(
        f'<div class="testimonial"><blockquote>&ldquo;{esc(q)}&rdquo;</blockquote>'
        f"<cite><strong>{esc(n)}</strong>{esc(r)}</cite></div>"
        for q, n, r in content["testimonials"]
    )
    faq = "".join(
        f'<div class="faq-item reveal"><button class="faq-q" type="button">{esc(q)}<span>+</span></button>'
        f'<div class="faq-a"><p>{esc(a)}</p></div></div>'
        for q, a in content["faq"]
    )
    logos = "".join(f"<span>{n}</span>" for n in ("NORTHWIND", "LUMEN", "PATCHWORK", "ARCLINE", "KITE", "TESSEL"))

    if show_playground:
        hero_visual = f"""<div class="hero-visual reveal">
          <div class="visual-bar"><i></i><i></i><i></i></div>
          <div class="playground">
            <form class="playground-input" id="genForm">
              <input id="genPrompt" placeholder="Describe a UI… e.g. pricing table for a coffee app" aria-label="Describe a UI" />
              <button class="btn btn-primary" type="submit">Generate</button>
            </form>
            <div class="chips">
              <button class="chip" type="button">pricing plans for {esc(ctx['subject'].lower())}</button>
              <button class="chip" type="button">login form for a music app</button>
              <button class="chip" type="button">analytics dashboard with revenue stats</button>
              <button class="chip" type="button">settings panel with notifications</button>
            </div>
            <div class="gen-tabs"><button class="active" data-view="preview" type="button">Preview</button><button data-view="code" type="button">Code</button></div>
            <div class="gen-output" id="genOutput"></div>
            <pre class="gen-code" id="genCode"></pre>
            <div class="gen-status" id="genStatus">Ready.</div>
          </div>
        </div>"""
    else:
        hero_visual = """<div class="hero-visual reveal" aria-hidden="true">
          <div class="visual-bar"><i></i><i></i><i></i></div>
          <div class="visual-row">
            <div class="visual-card"><div class="bar-line w60"></div><div class="bar-line prim w40"></div><div class="bar-line w80"></div></div>
            <div class="visual-card"><div class="bar-line w80"></div><div class="bar-line w40"></div><div class="bar-line prim w60"></div></div>
          </div>
          <div class="visual-card"><div class="mini-chart">""" + "".join(
            f'<b style="height:{h}%;animation-delay:{i * 0.12:.2f}s"></b>' for i, h in enumerate((40, 65, 50, 80, 58, 92, 70, 100, 76, 88))
        ) + """</div></div>
          <div class="visual-row">
            <div class="visual-card"><div class="bar-line prim w80"></div><div class="bar-line w60"></div></div>
            <div class="visual-card"><div class="bar-line w40"></div><div class="bar-line w80"></div></div>
          </div>
        </div>"""

    hero_bg = (
        '<div class="hero-bg"><canvas id="heroCanvas"></canvas></div>'
        if wants_generative_canvas
        else '<div class="hero-blob a"></div><div class="hero-blob b"></div>'
    )
    grid_overlay = '<div class="hero-grid-overlay"></div>' if theme["grid"] else ""
    body_classes = " ".join(c for c in ("theme-glow" if theme["glow"] else "", "theme-grid" if theme["grid"] else "") if c)
    config = {"currency": currency, "demoSeed": f"pricing plans and signup form for {ctx['subject'].lower()}", "theme": theme_id, "domain": domain_id}

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(brand)} — {esc(_sub(content['eyebrow'], ctx))}</title>
  <meta name="description" content="{esc(_sub(content['sub'], ctx))}" />
  {_font_link(theme)}
  <link rel="stylesheet" href="style.css" />
</head>
<body class="{body_classes}">
  <header class="nav">
    <div class="container nav-inner">
      <a class="brand" href="#top"><span class="brand-mark"></span>{esc(brand)}</a>
      <nav class="nav-links">{nav_links}</nav>
      <div class="nav-actions">
        <a class="btn btn-ghost" href="#signup">Sign in</a>
        <a class="btn btn-primary" href="#signup">{esc(content['cta'])}</a>
        <button class="menu-toggle" type="button" aria-label="Open menu">☰</button>
      </div>
    </div>
  </header>

  <main id="top">
    <section class="hero">
      {hero_bg}
      {grid_overlay}
      <div class="container hero-inner">
        <div class="reveal">
          <span class="eyebrow">{esc(_sub(content['eyebrow'], ctx))}</span>
          <h1 class="glitch" data-text="{esc(headline)}">{head_html}</h1>
          <p class="lead">{esc(_sub(content['sub'], ctx))}</p>
          <div class="hero-ctas">
            <a class="btn btn-primary" href="{'#top' if show_playground else '#signup'}" id="heroCta">{esc(content['cta'])} →</a>
            <a class="btn btn-ghost" href="#how">{esc(content['cta2'])}</a>
          </div>
          <div class="hero-trust"><div class="avatars"><span></span><span></span><span></span><span></span></div>Trusted by teams who ship.</div>
        </div>
        {hero_visual}
      </div>
    </section>

    <div class="logos"><div class="container logos-row">{logos}</div></div>

    <section class="block" id="features">
      <div class="container">
        <div class="section-head reveal">
          <span class="eyebrow">Why {esc(brand)}</span>
          <h2>Everything {esc(ctx['subject'])} needs, nothing it doesn't</h2>
          <p>{esc(_sub(content['sub'], ctx))}</p>
        </div>
        <div class="features-grid">{feature_cards}</div>
      </div>
    </section>

    <section class="block" id="how">
      <div class="container">
        <div class="section-head reveal">
          <span class="eyebrow">How it works</span>
          <h2>Three steps. That's it.</h2>
        </div>
        <div class="steps">{steps}</div>
      </div>
    </section>

    <section class="block">
      <div class="container stats">{stats}</div>
    </section>

    <section class="block" id="offers">
      <div class="container">
        <div class="section-head reveal">
          <span class="eyebrow">{esc(content['offers_title'])}</span>
          <h2>{esc(content['offers_title'])} for {esc(brand)}</h2>
        </div>
        {billing_toggle}
        <div class="offers-grid">{offers}</div>
      </div>
    </section>

    <section class="block">
      <div class="container">
        <div class="testimonial-wrap">{testimonials}</div>
        <div class="dots"></div>
      </div>
    </section>

    <section class="block" id="faq">
      <div class="container">
        <div class="section-head reveal">
          <span class="eyebrow">FAQ</span>
          <h2>Questions, answered</h2>
        </div>
        <div class="faq">{faq}</div>
      </div>
    </section>

    <section class="block" id="signup">
      <div class="container">
        <div class="cta-band reveal">
          <h2>Ready for {esc(brand)}?</h2>
          <p>Join the list and be first in line.</p>
          <form class="signup" id="signupForm" novalidate>
            <input name="email" type="email" placeholder="you@company.com" aria-label="Email address" />
            <button class="btn" type="submit">{esc(content['cta'])}</button>
          </form>
          <div class="signup-msg" id="signupMsg" role="status"></div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="container">
      <div class="footer-grid">
        <div><a class="brand" href="#top"><span class="brand-mark"></span>{esc(brand)}</a><p style="margin-top:14px;max-width:320px">{esc(_sub(content['eyebrow'], ctx))}</p></div>
        <div><h4>Product</h4><a href="#features">Features</a><a href="#offers">{esc(content['offers_title'])}</a><a href="#faq">FAQ</a></div>
        <div><h4>Company</h4><a href="#how">About</a><a href="#signup">Careers</a><a href="#signup">Contact</a></div>
        <div><h4>Legal</h4><a href="#top">Privacy</a><a href="#top">Terms</a></div>
      </div>
      <div class="footer-bottom"><span>© <span id="year"></span> {esc(brand)}. All rights reserved.</span><span>{esc(theme['label'])} theme</span></div>
    </div>
  </footer>
  <button class="to-top" type="button" aria-label="Back to top">↑</button>
  <script id="site-config" type="application/json">{json.dumps(config)}</script>
  <script src="app.js" defer></script>
</body>
</html>
"""

    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
js = Path("app.js").read_text(encoding="utf-8")
for anchor in ("id=\\"features\\"", "id=\\"offers\\"", "id=\\"faq\\"", "id=\\"signupForm\\"", "site-config"):
    assert anchor in html, f"Landing page missing {anchor}"
assert "IntersectionObserver" in js and "signupForm" in js
print("PASS: landing page bundle verified (hero, features, offers, FAQ, signup)")
"""
    return [
        {"path": "index.html", "description": f"{brand} landing page ({theme['label']} theme)", "content": index_html},
        {"path": "style.css", "description": f"{theme['label']} landing page design system", "content": _theme_css(theme) + _LANDING_CSS},
        {"path": "app.js", "description": "Nav, reveal, counters, pricing toggle, testimonials, FAQ, signup, hero canvas"
         + (", generative UI playground" if show_playground else ""), "content": _LANDING_JS},
        {"path": "verify_custom.py", "description": "Smoke test verifying the landing page bundle", "content": verify_py},
    ]


_DASH_DOMAINS: dict[str, dict[str, Any]] = {
    "sales": {
        "pattern": r"sales|e-?commerce|store|shop|revenue|orders|retail|marketplace",
        "title": "Sales",
        "kpis": [("Revenue", "$", 48200, 0.12, 0), ("Orders", "", 1284, 0.10, 0), ("Avg order", "$", 37.6, 0.05, 2), ("Conversion", "%", 3.4, 0.08, 2)],
        "series": "Revenue", "breakdown": ["Online", "Retail", "Wholesale", "Marketplace"],
        "table": ["Order", "Customer", "Channel", "Amount", "Status"], "statuses": ["Paid", "Shipped", "Refunded", "Pending"],
        "names": ["Ava Chen", "Noah Patel", "Mia Rossi", "Liam Novak", "Zoe Adams", "Kai Morgan", "Eli Stone", "Isla Brooks"],
    },
    "fitness": {
        "pattern": r"fitness|health|workout|steps|calorie|gym|training|sleep|run",
        "title": "Training",
        "kpis": [("Steps", "", 9420, 0.18, 0), ("Active kcal", "", 612, 0.15, 0), ("Resting HR", " bpm", 58, 0.04, 0), ("Sleep", " h", 7.4, 0.08, 1)],
        "series": "Active minutes", "breakdown": ["Strength", "Cardio", "Mobility", "Rest"],
        "table": ["Session", "Type", "Coach", "Duration", "Status"], "statuses": ["Completed", "Scheduled", "Skipped", "Completed"],
        "names": ["Lower body", "Intervals", "Yoga flow", "Upper body", "Long run", "Core", "Tempo", "Recovery"],
    },
    "crypto": {
        "pattern": r"crypto|bitcoin|btc|eth|stock|trading|portfolio|finance|invest|market",
        "title": "Portfolio",
        "kpis": [("Portfolio", "$", 128450, 0.06, 0), ("24h P&L", "$", 2310, 0.6, 0), ("Positions", "", 14, 0.1, 0), ("Volatility", "%", 2.8, 0.2, 2)],
        "series": "Portfolio value", "breakdown": ["BTC", "ETH", "SOL", "Stablecoins"],
        "table": ["Trade", "Asset", "Side", "Value", "Status"], "statuses": ["Filled", "Open", "Cancelled", "Filled"],
        "names": ["BTC", "ETH", "SOL", "AVAX", "LINK", "ARB", "OP", "DOT"],
    },
    "devops": {
        "pattern": r"server|devops|infrastructure|uptime|latency|api|system|cluster|cloud|monitor|network",
        "title": "Infrastructure",
        "kpis": [("Uptime", "%", 99.98, 0.0004, 2), ("p95 latency", " ms", 182, 0.15, 0), ("Requests/s", "", 4210, 0.2, 0), ("Error rate", "%", 0.21, 0.4, 2)],
        "series": "Requests / s", "breakdown": ["us-east", "eu-west", "ap-south", "us-west"],
        "table": ["Deploy", "Service", "Region", "Duration", "Status"], "statuses": ["Healthy", "Degraded", "Rolled back", "Healthy"],
        "names": ["api-gateway", "auth", "billing", "search", "ingest", "notifier", "media", "web"],
    },
    "marketing": {
        "pattern": r"marketing|traffic|seo|social|campaign|audience|visitors|ads|growth|web analytics",
        "title": "Growth",
        "kpis": [("Visitors", "", 58210, 0.14, 0), ("Signups", "", 1840, 0.12, 0), ("CAC", "$", 42.3, 0.06, 2), ("Bounce", "%", 38.2, 0.05, 1)],
        "series": "Visitors", "breakdown": ["Organic", "Paid", "Social", "Referral"],
        "table": ["Campaign", "Channel", "Owner", "Spend", "Status"], "statuses": ["Live", "Paused", "Ended", "Draft"],
        "names": ["Spring launch", "Retargeting", "Creator collab", "Newsletter", "Webinar", "Brand search", "Podcast", "Referral push"],
    },
}
_DASH_DEFAULT = {
    "title": "Operations",
    "kpis": [("Throughput", "", 3420, 0.12, 0), ("Active", "", 812, 0.1, 0), ("Avg time", " min", 14.2, 0.06, 1), ("Satisfaction", "%", 94.1, 0.02, 1)],
    "series": "Throughput", "breakdown": ["Team A", "Team B", "Team C", "Team D"],
    "table": ["Item", "Owner", "Category", "Value", "Status"], "statuses": ["Done", "In progress", "Blocked", "Done"],
    "names": ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"],
}


def build_dashboard_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    prompt = f"{display_name} {brief}"
    theme = THEMES[detect_theme(prompt)]
    ctx = extract_subject(display_name, brief)
    domain = next((d for d in _DASH_DOMAINS.values() if re.search(d["pattern"], prompt, re.IGNORECASE)), _DASH_DEFAULT)
    title = ctx["subject"] if ctx["subject"] != "Your Product" else f"{domain['title']} Dashboard"
    esc = html.escape
    config = {
        "title": title,
        "kpis": [{"label": k, "unit": u, "base": b, "vol": v, "decimals": d} for k, u, b, v, d in domain["kpis"]],
        "series": domain["series"],
        "breakdown": domain["breakdown"],
        "table": domain["table"],
        "statuses": domain["statuses"],
        "names": domain["names"],
    }
    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  {_font_link(theme)}
  <link rel="stylesheet" href="style.css" />
</head>
<body class="{'theme-glow' if theme['glow'] else ''}">
  <div class="layout">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark"></span>{esc(title)}</div>
      <nav>
        <a href="#overview" class="active">Overview</a>
        <a href="#trends">Trends</a>
        <a href="#breakdown">Breakdown</a>
        <a href="#records">Records</a>
      </nav>
      <div class="live-box">
        <label class="live-toggle"><input type="checkbox" id="liveToggle" checked /> Live updates</label>
        <div class="muted" id="lastUpdated">Updated just now</div>
      </div>
    </aside>
    <main class="main">
      <header class="topbar" id="overview">
        <div>
          <h1>{esc(title)}</h1>
          <p class="muted">{esc(brief)}</p>
        </div>
        <div class="range" role="tablist">
          <button data-range="24" type="button">24h</button>
          <button data-range="7" class="active" type="button">7d</button>
          <button data-range="30" type="button">30d</button>
          <button data-range="90" type="button">90d</button>
        </div>
      </header>
      <section class="kpis" id="kpis"></section>
      <section class="grid">
        <div class="panel wide" id="trends">
          <div class="panel-head"><h2 id="seriesTitle"></h2><span class="muted" id="seriesSummary"></span></div>
          <canvas id="lineChart" height="260"></canvas>
          <div class="tooltip" id="tooltip"></div>
        </div>
        <div class="panel" id="breakdown">
          <div class="panel-head"><h2>Breakdown</h2></div>
          <canvas id="donutChart" height="220"></canvas>
          <div class="legend" id="legend"></div>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>By weekday</h2></div>
          <canvas id="barChart" height="220"></canvas>
        </div>
      </section>
      <section class="panel" id="records">
        <div class="panel-head">
          <h2>Recent records</h2>
          <div class="table-tools">
            <input id="tableSearch" placeholder="Search records…" />
            <button id="exportCsv" type="button">Export CSV</button>
          </div>
        </div>
        <div class="table-wrap"><table><thead id="tableHead"></thead><tbody id="tableBody"></tbody></table></div>
      </section>
    </main>
  </div>
  <script id="dash-config" type="application/json">{json.dumps(config)}</script>
  <script src="app.js" defer></script>
</body>
</html>
"""
    css = _theme_css(theme) + """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--font-body); }
h1, h2 { font-family: var(--font-heading); }
.muted { color: var(--muted); font-size: 13px; }
.layout { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.sidebar { background: var(--surface); border-right: 1px solid var(--border); padding: 24px 18px; display: flex; flex-direction: column; gap: 28px; position: sticky; top: 0; height: 100vh; }
.brand { font-family: var(--font-heading); font-weight: 800; display: flex; align-items: center; gap: 10px; font-size: 17px; }
.brand-mark { width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, var(--primary), var(--secondary)); flex: 0 0 26px; }
.sidebar nav { display: flex; flex-direction: column; gap: 4px; }
.sidebar nav a { color: var(--muted); text-decoration: none; padding: 10px 12px; border-radius: var(--radius); font-size: 15px; }
.sidebar nav a.active, .sidebar nav a:hover { background: var(--surface2); color: var(--text); }
.live-box { margin-top: auto; display: flex; flex-direction: column; gap: 6px; }
.live-toggle { display: flex; gap: 8px; align-items: center; font-size: 14px; cursor: pointer; }
.main { padding: 28px 32px 60px; display: flex; flex-direction: column; gap: 22px; min-width: 0; }
.topbar { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; }
.topbar h1 { font-size: 28px; }
.range { display: flex; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 4px; }
.range button { background: none; border: none; color: var(--muted); padding: 8px 14px; border-radius: var(--radius); cursor: pointer; font-weight: 700; font-family: var(--font-body); }
.range button.active { background: var(--primary); color: var(--on-primary); }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: calc(var(--radius) + 4px); padding: 18px; }
.theme-glow .kpi { box-shadow: 0 10px 40px -24px var(--primary); }
.kpi-label { color: var(--muted); font-size: 13px; }
.kpi-value { font-family: var(--font-heading); font-size: 28px; font-weight: 800; margin: 6px 0; }
.delta { font-size: 13px; font-weight: 700; }
.delta.up { color: #22c55e; } .delta.down { color: #ef4444; }
.spark { width: 100%; height: 36px; display: block; margin-top: 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: calc(var(--radius) + 4px); padding: 20px; position: relative; min-width: 0; }
.panel.wide { grid-column: 1 / -1; }
.panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; gap: 12px; flex-wrap: wrap; }
.panel-head h2 { font-size: 17px; }
canvas { width: 100%; display: block; }
.tooltip { position: absolute; pointer-events: none; background: var(--surface2); border: 1px solid var(--border); padding: 6px 10px; border-radius: var(--radius); font-size: 13px; opacity: 0; transition: opacity .12s ease; white-space: nowrap; }
.legend { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; font-size: 13px; }
.legend span { display: flex; align-items: center; gap: 8px; }
.legend i { width: 10px; height: 10px; border-radius: 3px; }
.table-tools { display: flex; gap: 8px; }
.table-tools input { background: var(--bg); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius); padding: 8px 12px; font-family: var(--font-body); }
.table-tools button { background: var(--primary); color: var(--on-primary); border: none; border-radius: var(--radius); padding: 8px 14px; font-weight: 700; cursor: pointer; font-family: var(--font-body); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; color: var(--muted); font-weight: 600; padding: 10px 12px; border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; white-space: nowrap; }
th.sorted::after { content: " ▾"; } th.sorted.asc::after { content: " ▴"; }
td { padding: 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }
tr:hover td { background: var(--surface2); }
.pill { padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; background: var(--surface2); }
.pill.s0 { color: #22c55e; } .pill.s1 { color: var(--secondary); } .pill.s2 { color: #ef4444; } .pill.s3 { color: var(--accent); }
@media (max-width: 1000px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: static; height: auto; flex-direction: row; flex-wrap: wrap; align-items: center; }
  .sidebar nav { flex-direction: row; }
  .live-box { margin-top: 0; }
  .kpis { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr; }
}
"""
    js = r"""
const CFG = JSON.parse(document.getElementById("dash-config").textContent);
const css = getComputedStyle(document.documentElement);
const C = {
  primary: css.getPropertyValue("--primary").trim(),
  secondary: css.getPropertyValue("--secondary").trim(),
  accent: css.getPropertyValue("--accent").trim(),
  text: css.getPropertyValue("--text").trim(),
  muted: css.getPropertyValue("--muted").trim(),
  border: css.getPropertyValue("--border").trim(),
};
const PALETTE = [C.primary, C.secondary, C.accent, C.muted];
let range = 7;
let seed = 1;
let sortCol = 0;
let sortAsc = false;

function rng() {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
}
function fmt(v, unit, decimals) {
  const n = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toLocaleString();
  if (unit === "$") return "$" + n;
  return n + unit;
}
function series(base, vol, n) {
  const out = [];
  let v = base;
  for (let i = 0; i < n; i++) {
    v = Math.max(base * 0.3, v * (1 + (rng() - 0.48) * vol) + Math.sin(i / 3) * base * vol * 0.2);
    out.push(v);
  }
  return out;
}

const state = { kpis: [], line: [], donut: [], bars: [], rows: [] };

function regenerate() {
  seed = range * 7919 + 13;
  const points = range === 24 ? 24 : range;
  state.kpis = CFG.kpis.map((k) => {
    const s = series(k.base, k.vol, Math.max(points, 12));
    const prev = s[0], cur = s[s.length - 1];
    return { ...k, value: cur, delta: ((cur - prev) / prev) * 100, spark: s };
  });
  state.line = series(CFG.kpis[0].base, CFG.kpis[0].vol, Math.max(points, 12));
  state.donut = CFG.breakdown.map(() => 10 + rng() * 40);
  state.bars = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => ({ d, v: 20 + rng() * 80 }));
  state.rows = Array.from({ length: 18 }, (_, i) => {
    const name = CFG.names[i % CFG.names.length];
    const status = CFG.statuses[Math.floor(rng() * CFG.statuses.length)];
    return [
      "#" + (4200 + i * 7 + range),
      name,
      CFG.breakdown[Math.floor(rng() * CFG.breakdown.length)],
      Math.round(40 + rng() * 960),
      status,
    ];
  });
  render();
}

function renderKpis() {
  const wrap = document.getElementById("kpis");
  wrap.innerHTML = "";
  state.kpis.forEach((k, idx) => {
    const el = document.createElement("div");
    el.className = "kpi";
    const up = k.delta >= 0;
    el.innerHTML = `<div class="kpi-label">${k.label}</div><div class="kpi-value">${fmt(k.value, k.unit, k.decimals)}</div>
      <div class="delta ${up ? "up" : "down"}">${up ? "▲" : "▼"} ${Math.abs(k.delta).toFixed(1)}% vs start of range</div>
      <canvas class="spark" id="spark${idx}"></canvas>`;
    wrap.appendChild(el);
    drawSpark(el.querySelector("canvas"), k.spark, up ? C.primary : C.secondary);
  });
}

function setupCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.clientWidth;
  const h = canvas.clientHeight || parseInt(canvas.getAttribute("height"), 10);
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

function drawSpark(canvas, data, color) {
  const { ctx, w, h } = setupCanvas(canvas);
  const min = Math.min(...data), max = Math.max(...data);
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * (h - 4) - 2;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

let linePoints = [];
function drawLine() {
  const canvas = document.getElementById("lineChart");
  const { ctx, w, h } = setupCanvas(canvas);
  const pad = { l: 56, r: 16, t: 12, b: 28 };
  const data = state.line;
  const min = Math.min(...data) * 0.95, max = Math.max(...data) * 1.05;
  ctx.font = "12px sans-serif";
  ctx.fillStyle = C.muted;
  ctx.strokeStyle = C.border;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + ((h - pad.t - pad.b) * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    const val = max - ((max - min) * i) / 4;
    ctx.fillText(fmt(val, CFG.kpis[0].unit === "$" ? "$" : "", 0), 6, y + 4);
  }
  linePoints = data.map((v, i) => ({
    x: pad.l + (i / (data.length - 1)) * (w - pad.l - pad.r),
    y: pad.t + (1 - (v - min) / (max - min || 1)) * (h - pad.t - pad.b),
    v,
    label: range === 24 ? `${i}:00` : `Day ${i + 1}`,
  }));
  const grad = ctx.createLinearGradient(0, pad.t, 0, h - pad.b);
  grad.addColorStop(0, C.primary + "55");
  grad.addColorStop(1, C.primary + "00");
  ctx.beginPath();
  linePoints.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  ctx.lineTo(linePoints[linePoints.length - 1].x, h - pad.b);
  ctx.lineTo(linePoints[0].x, h - pad.b);
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.beginPath();
  linePoints.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  ctx.strokeStyle = C.primary;
  ctx.lineWidth = 2.5;
  ctx.stroke();
  const step = Math.ceil(linePoints.length / 8);
  ctx.fillStyle = C.muted;
  linePoints.forEach((p, i) => { if (i % step === 0) ctx.fillText(p.label, p.x - 14, h - 8); });
  const total = data.reduce((a, b) => a + b, 0);
  document.getElementById("seriesTitle").textContent = CFG.series;
  document.getElementById("seriesSummary").textContent = `Avg ${fmt(total / data.length, CFG.kpis[0].unit, 0)} over ${range === 24 ? "24 hours" : range + " days"}`;
}

function drawDonut() {
  const canvas = document.getElementById("donutChart");
  const { ctx, w, h } = setupCanvas(canvas);
  const total = state.donut.reduce((a, b) => a + b, 0);
  const r = Math.min(w, h) / 2 - 10;
  const cx = w / 2, cy = h / 2;
  let a = -Math.PI / 2;
  state.donut.forEach((v, i) => {
    const slice = (v / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, a, a + slice);
    ctx.arc(cx, cy, r * 0.62, a + slice, a, true);
    ctx.closePath();
    ctx.fillStyle = PALETTE[i % PALETTE.length];
    ctx.fill();
    a += slice;
  });
  ctx.fillStyle = C.text;
  ctx.font = "700 20px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(Math.round((state.donut[0] / total) * 100) + "%", cx, cy + 4);
  ctx.font = "12px sans-serif";
  ctx.fillStyle = C.muted;
  ctx.fillText(CFG.breakdown[0], cx, cy + 22);
  ctx.textAlign = "left";
  document.getElementById("legend").innerHTML = CFG.breakdown
    .map((b, i) => `<span><i style="background:${PALETTE[i % PALETTE.length]}"></i>${b} · ${Math.round((state.donut[i] / total) * 100)}%</span>`)
    .join("");
}

function drawBars() {
  const canvas = document.getElementById("barChart");
  const { ctx, w, h } = setupCanvas(canvas);
  const pad = 26;
  const bw = (w - pad * 2) / state.bars.length;
  const max = Math.max(...state.bars.map((b) => b.v));
  state.bars.forEach((b, i) => {
    const bh = (b.v / max) * (h - pad * 2);
    const x = pad + i * bw + bw * 0.18;
    const y = h - pad - bh;
    const grad = ctx.createLinearGradient(0, y, 0, h - pad);
    grad.addColorStop(0, C.secondary);
    grad.addColorStop(1, C.primary);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, y, bw * 0.64, bh, 6) : ctx.rect(x, y, bw * 0.64, bh);
    ctx.fill();
    ctx.fillStyle = C.muted;
    ctx.font = "12px sans-serif";
    ctx.fillText(b.d, x, h - 8);
  });
}

function renderTable() {
  const head = document.getElementById("tableHead");
  head.innerHTML = "<tr>" + CFG.table.map((c, i) => `<th data-col="${i}" class="${i === sortCol ? "sorted" + (sortAsc ? " asc" : "") : ""}">${c}</th>`).join("") + "</tr>";
  head.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
    const col = Number(th.dataset.col);
    sortAsc = col === sortCol ? !sortAsc : true;
    sortCol = col;
    renderTable();
  }));
  const q = document.getElementById("tableSearch").value.toLowerCase().trim();
  const rows = state.rows
    .filter((r) => !q || r.join(" ").toLowerCase().includes(q))
    .sort((a, b) => {
      const x = a[sortCol], y = b[sortCol];
      const cmp = typeof x === "number" ? x - y : String(x).localeCompare(String(y));
      return sortAsc ? cmp : -cmp;
    });
  const unit = CFG.kpis[0].unit === "$" ? "$" : "";
  document.getElementById("tableBody").innerHTML = rows.length
    ? rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${unit}${r[3].toLocaleString()}</td><td><span class="pill s${CFG.statuses.indexOf(r[4])}">${r[4]}</span></td></tr>`).join("")
    : `<tr><td colspan="${CFG.table.length}" class="muted">No records match "${q}".</td></tr>`;
}

function render() {
  renderKpis();
  drawLine();
  drawDonut();
  drawBars();
  renderTable();
  document.getElementById("lastUpdated").textContent = "Updated " + new Date().toLocaleTimeString();
}

document.querySelectorAll(".range button").forEach((btn) => btn.addEventListener("click", () => {
  document.querySelectorAll(".range button").forEach((b) => b.classList.toggle("active", b === btn));
  range = Number(btn.dataset.range);
  regenerate();
}));
document.getElementById("tableSearch").addEventListener("input", renderTable);
document.getElementById("exportCsv").addEventListener("click", () => {
  const lines = [CFG.table.join(",")].concat(state.rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")));
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = CFG.title.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-records.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});
document.querySelectorAll(".sidebar nav a").forEach((a) => a.addEventListener("click", () => {
  document.querySelectorAll(".sidebar nav a").forEach((x) => x.classList.toggle("active", x === a));
}));

const tooltip = document.getElementById("tooltip");
const lineCanvas = document.getElementById("lineChart");
lineCanvas.addEventListener("mousemove", (e) => {
  const rect = lineCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  let best = null;
  linePoints.forEach((p) => { if (!best || Math.abs(p.x - mx) < Math.abs(best.x - mx)) best = p; });
  if (!best) return;
  tooltip.style.opacity = 1;
  tooltip.style.left = best.x + 24 + "px";
  tooltip.style.top = best.y + 40 + "px";
  tooltip.textContent = `${best.label}: ${fmt(best.v, CFG.kpis[0].unit, CFG.kpis[0].decimals)}`;
});
lineCanvas.addEventListener("mouseleave", () => { tooltip.style.opacity = 0; });

setInterval(() => {
  if (!document.getElementById("liveToggle").checked) return;
  const last = state.line[state.line.length - 1];
  state.line.push(Math.max(last * 0.5, last * (1 + (Math.random() - 0.48) * CFG.kpis[0].vol * 0.5)));
  state.line.shift();
  state.kpis.forEach((k) => {
    k.value = Math.max(0, k.value * (1 + (Math.random() - 0.5) * k.vol * 0.08));
    k.spark.push(k.value);
    k.spark.shift();
  });
  renderKpis();
  drawLine();
  document.getElementById("lastUpdated").textContent = "Updated " + new Date().toLocaleTimeString();
}, 2500);

window.addEventListener("resize", render);
regenerate();
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
js = Path("app.js").read_text(encoding="utf-8")
for anchor in ("lineChart", "donutChart", "barChart", "tableBody", "dash-config"):
    assert anchor in html, f"Dashboard missing {anchor}"
assert "regenerate" in js and "exportCsv" in js
print("PASS: dashboard bundle verified (KPIs, line/donut/bar charts, sortable table, CSV export)")
"""
    return [
        {"path": "index.html", "description": f"{title} dashboard ({theme['label']} theme)", "content": index_html},
        {"path": "style.css", "description": f"{theme['label']} dashboard styling", "content": css},
        {"path": "app.js", "description": "KPIs, canvas charts, range switching, live updates, sortable table, CSV export", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying the dashboard bundle", "content": verify_py},
    ]
