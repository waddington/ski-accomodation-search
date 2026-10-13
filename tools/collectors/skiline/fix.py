#!/usr/bin/env python3
"""fix.py in.jsonl out.jsonl : map Ski Line API resort -> resorts_raw village + ski_area."""
import sys, json
V = {
 "Les Menuires": ("Les Menuires", "Les 3 Vallées"), "Reberty 2000": ("Les Menuires: Reberty 2000", "Les 3 Vallées"),
 "St-Martin-de-Belleville": ("St-Martin-de-Belleville", "Les 3 Vallées"), "Mottaret": ("Méribel-Mottaret", "Les 3 Vallées"),
 "Val Thorens": ("Val Thorens", "Les 3 Vallées"), "La Tania": ("La Tania", "Les 3 Vallées"),
 "Courchevel": ("Courchevel", "Les 3 Vallées"), "Meribel": ("Méribel", "Les 3 Vallées"),
 "Brides les Bains": ("Brides-les-Bains", "Les 3 Vallées"),
 "Tignes": ("Tignes", "Espace Killy (Tignes – Val d'Isère)"), "Val d'Isere": ("Val d'Isère", "Espace Killy (Tignes – Val d'Isère)"),
 "La Plagne": ("La Plagne", "Paradiski"), "Les Arcs": ("Les Arcs", "Paradiski"), "Bourg Saint Maurice": ("Bourg-St-Maurice", "Paradiski"),
 "Avoriaz": ("Avoriaz", "Portes du Soleil"), "Morzine": ("Morzine", "Portes du Soleil"), "Les Gets": ("Les Gets", "Portes du Soleil"),
 "Chatel": ("Châtel", "Portes du Soleil"), "Les Crosets": ("Les Crosets", "Portes du Soleil"),
 "Alpe d'Huez": ("Alpe d'Huez", "Alpe d'Huez Grand Domaine"), "Auris-en-Oisans": ("Auris-en-Oisans", "Alpe d'Huez Grand Domaine"),
 "Vaujany": ("Vaujany", "Alpe d'Huez Grand Domaine"), "Les Deux-Alpes": ("Les 2 Alpes", "Les 2 Alpes"),
 "Montgenevre": ("Montgenèvre", "Via Lattea / Milky Way"), "La Toussuire": ("La Toussuire", "Les Sybelles"),
 "Le Corbier": ("Le Corbier", "Les Sybelles"), "St Sorlin d'Arves": ("St-Sorlin-d'Arves", "Les Sybelles"),
 "Flaine": ("Flaine", "Grand Massif"), "Les Carroz": ("Les Carroz", "Grand Massif"), "Samoens": ("Samoëns", "Grand Massif"),
 "Serre-Chevalier": ("Serre Chevalier", "Serre Chevalier"), "Megeve": ("Megève", "Évasion Mont-Blanc"),
 "Saint-Gervais": ("St-Gervais-les-Bains", "Évasion Mont-Blanc"), "Risoul": ("Risoul 1850", "La Forêt Blanche"),
 "Vars": ("Vars", "La Forêt Blanche"), "Valmorel": ("Valmorel", "Le Grand Domaine"), "La Rosiere": ("La Rosière", "Espace San Bernardo"),
 "Les Saisies": ("Les Saisies", "Espace Diamant"), "Pra Loup": ("Pra-Loup", "Espace Lumière"),
 "Valloire": ("Valloire", "Galibier-Thabor"), "Valmeinier": ("Valmeinier 1800", "Galibier-Thabor"),
 "St Anton": ("St Anton am Arlberg", "Ski Arlberg"), "St Christoph": ("St Christoph", "Ski Arlberg"), "Lech": ("Lech", "Ski Arlberg"),
 "Zurs": ("Zürs", "Ski Arlberg"), "Ischgl": ("Ischgl", "Silvretta Arena"), "Solden": ("Sölden", "Sölden (Ötztal)"),
 "Hochsolden": ("Hochsölden", "Sölden (Ötztal)"), "Saalbach": ("Saalbach", "Skicircus Saalbach Hinterglemm Leogang Fieberbrunn"),
 "Hinterglemm & Fieberbrunn": ("Hinterglemm", "Skicircus Saalbach Hinterglemm Leogang Fieberbrunn"),
 "Leogang": ("Leogang", "Skicircus Saalbach Hinterglemm Leogang Fieberbrunn"), "Kitzbuhel": ("Kitzbühel", "KitzSki"),
 "Serfaus": ("Serfaus", "Serfaus-Fiss-Ladis"), "Konigsleiten": ("Königsleiten", "Zillertal Arena"), "Gerlos": ("Gerlos", "Zillertal Arena"),
 "Mayrhofen": ("Mayrhofen", "Mayrhofen"), "Finkenberg": ("Finkenberg", "Mayrhofen"), "Soll": ("Söll", "SkiWelt Wilder Kaiser–Brixental"),
 "Westendorf": ("Westendorf", "SkiWelt Wilder Kaiser–Brixental"), "Ellmau": ("Ellmau", "SkiWelt Wilder Kaiser–Brixental"),
 "Montafon": ("Montafon", "Silvretta Montafon"), "Verbier": ("Verbier", "4 Vallées"), "Zermatt": ("Zermatt", "Matterhorn Ski Paradise"),
 "Laax": ("Laax (Murschetg)", "Flims Laax Falera"), "St Moritz": ("St Moritz", "St Moritz – Corviglia"),
 "Selva": ("Selva / Wolkenstein", "Sella Ronda – Dolomiti Superski"), "Arabba": ("Arabba", "Sella Ronda – Dolomiti Superski"),
 "Corvara": ("Corvara", "Sella Ronda – Dolomiti Superski"), "Colfosco": ("Colfosco", "Sella Ronda – Dolomiti Superski"),
 "Canazei": ("Canazei", "Sella Ronda – Dolomiti Superski"), "St Cristina": ("Santa Cristina", "Sella Ronda – Dolomiti Superski"),
 "La Villa (Sella Ronda)": ("La Villa", "Sella Ronda – Dolomiti Superski"), "San Cassiano": ("San Cassiano", "Sella Ronda – Dolomiti Superski"),
 "Ortisei": ("Ortisei", "Sella Ronda – Dolomiti Superski"), "Sestriere": ("Sestriere", "Via Lattea / Milky Way"),
 "Sauze d'Oulx": ("Sauze d'Oulx", "Via Lattea / Milky Way"), "Pragelato": ("Pragelato", "Via Lattea / Milky Way"),
 "Cervinia": ("Breuil-Cervinia", "Matterhorn Ski Paradise"), "Madonna Di Campiglio": ("Madonna di Campiglio", "Madonna di Campiglio – Pinzolo – Folgarida-Marilleva"),
 "Folgarida": ("Folgarida", "Madonna di Campiglio – Pinzolo – Folgarida-Marilleva"), "Pinzolo": ("Pinzolo", "Madonna di Campiglio – Pinzolo – Folgarida-Marilleva"),
 "La Thuile": ("La Thuile", "Espace San Bernardo"), "Champoluc": ("Champoluc", "Monterosa Ski"), "Gressoney": ("Gressoney-La-Trinité", "Monterosa Ski"),
}
n = 0
with open(sys.argv[2], "w") as out:
    for l in open(sys.argv[1]):
        if not l.strip().startswith("{"): continue
        r = json.loads(l)
        api = r.get("village", "")
        if api in V:
            v, a = V[api]
            if v != api:
                r["notes"] = (r.get("notes") or "") + f"; Ski Line resort '{api}'"
            r["village"] = v
            r["ski_area"] = r.get("ski_area") or a
        if r.get("property_type") in ("apartment", "hotel"):
            if r.get("hot_tub") == "yes-type-unknown":
                r["notes"] = (r.get("notes") or "") + "; Ski Line hot-tub flag on a residence/hotel: probably shared spa (pass2: hot tub type)"
            if r.get("bedrooms"):
                r["bedrooms"] = ""  # residence descriptions list several unit types
        out.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
print("fixed", n, file=sys.stderr)
