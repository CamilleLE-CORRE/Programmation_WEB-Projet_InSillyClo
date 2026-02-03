def parse_genbank(source):
    """
    Parse a GenBank file (or dict) into a dict ready for visualization.

    Returns:
    {
        "length": int,
        "features": [
            {
                "start": int,
                "end": int,
                "length": int,
                "label": str,
                "type": str,
                "strand": int,
                "color": str,
                "linked_plasmid": str or None
            },
            ...
        ]
    }
    """

    # Initialisation
    parsed = {
        "length": 1,
        "features": []
    }

    # Si source est un dict
    if isinstance(source, dict):
        parsed["length"] = source.get("length", 1)
        features = source.get("features", [])
        for f in features:
            # Assurer les clés essentielles
            f.setdefault("start", 0)
            f.setdefault("end", 1)
            f.setdefault("length", f["end"] - f["start"] + 1)
            f.setdefault("strand", 1)
            f.setdefault("label", "")
            f.setdefault("color", "#CCCCCC")
            f.setdefault("linked_plasmid", None)
            parsed["features"].append(f)
        # recalculer length si features existent
        if features:
            parsed["length"] = max(f.get("end", 1) for f in features)
        return parsed

    # Sinon, parser un fichier GenBank
    with open(source, "r") as f:
        lines = f.readlines()

    feature = None
    for line in lines:
        # détecter LOCUS
        if line.startswith("LOCUS") and parsed["length"] == 1:
            parts = line.split()
            try:
                parsed["length"] = int(parts[2])
            except (IndexError, ValueError):
                parsed["length"] = 1
        # features
        if line.startswith("     "):
            parts = line.split()
            if len(parts) < 2:
                continue
            ftype = parts[0].strip()
            loc = parts[1].strip()
            feature = {"type": ftype}

            # strand
            if "complement" in loc:
                loc = loc.replace("complement(", "").replace(")", "")
                feature["strand"] = -1
            else:
                feature["strand"] = 1

            # join
            if "join" in loc:
                loc = loc.replace("join(", "").replace(")", "")
                start = min(int(x.split("..")[0]) for x in loc.split(","))
                end = max(int(x.split("..")[1]) for x in loc.split(","))
            else:
                try:
                    start, end = map(int, loc.split(".."))
                except:
                    start, end = 0, 1

            feature["start"] = start
            feature["end"] = end
            feature["length"] = end - start + 1
            feature["label"] = ""
            feature["color"] = "#CCCCCC"
            feature["linked_plasmid"] = None
            parsed["features"].append(feature)
        elif line.strip().startswith("/label=") and feature is not None:
            feature["label"] = line.strip().split("=")[1].strip()

    return parsed