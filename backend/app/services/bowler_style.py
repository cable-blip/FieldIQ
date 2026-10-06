"""
bowler_style.py
------------------
A hand-curated lookup of bowler name -> bowling style ("Pace" or "Spin"),
covering bowlers who bowled at least 15 deliveries (in the source dataset)
against FieldIQ's 9 bundled real batters.

Why hand-curated, not inferred
--------------------------------
There is no reliable way to derive "pace" vs "spin" from a bowler's name or
from the ball-by-ball data itself (the source dataset doesn't carry a
bowling-style column). This is real-world cricketing knowledge, checked
against public player records - the same category of judgment call as
BATTER_HANDEDNESS in real_data_loader.py.

Honesty over completeness
----------------------------
A handful of names are deliberately marked "Unknown" rather than guessed,
because the classification genuinely isn't a clean binary or I couldn't
confirm it confidently:

  - Regan West: confirmed (via public player records) to have bowled BOTH
    left-arm fast-medium AND slow left-arm orthodox during his career - a
    real dual-style bowler, not a data-entry ambiguity. Forcing a single
    label here would be a fabrication, not a simplification.
  - A few historically minor/associate-nation players (Greg Lamb, Andy
    McKay, Garey Mathurin, Mudassar Bukhari, Ahsan Malik) where I could not
    independently confirm bowling style with confidence.

Any bowler not in BOWLER_STYLE at all (330 total appear in the source data;
only the ~184 with >=15 deliveries against our 9 batters were reviewed)
also resolves to "Unknown" via bowler_style()'s default. Deliveries by an
"Unknown"-style bowler are excluded whenever the app filters by bowler
style - never silently folded into either bucket.
"""

from __future__ import annotations

# fmt: off
BOWLER_STYLE: dict[str, str] = {
    # Pace / seam
    "Morne Morkel": "Pace", "Jade Dernbach": "Pace", "Stuart Broad": "Pace",
    "Nuwan Kulasekara": "Pace", "Lasith Malinga": "Pace", "Mohammad Amir": "Pace",
    "Sohail Tanvir": "Pace", "Angelo Mathews": "Pace", "Steven Finn": "Pace",
    "Dale Steyn": "Pace", "Darren Sammy": "Pace", "Tim Bresnan": "Pace",
    "Kyle Mills": "Pace", "Zaheer Khan": "Pace", "Umar Gul": "Pace",
    "Wayne Parnell": "Pace", "Jacob Oram": "Pace", "Tim Southee": "Pace",
    "Lonwabo Tsotsobe": "Pace", "Brett Lee": "Pace", "Jerome Taylor": "Pace",
    "Dwayne Bravo": "Pace", "Mashrafe Mortaza": "Pace", "Kieron Pollard": "Pace",
    "Irfan Pathan": "Pace", "Fidel Edwards": "Pace", "Thisara Perera": "Pace",
    "Shane Watson": "Pace", "Ravi Rampaul": "Pace", "Shane Bond": "Pace",
    "Kyle Jarvis": "Pace", "Albie Morkel": "Pace", "Shaun Tait": "Pace",
    "Chris Woakes": "Pace", "Ishant Sharma": "Pace", "Ashish Nehra": "Pace",
    "Dirk Nannes": "Pace", "Elton Chigumbura": "Pace", "Ryan Sidebottom": "Pace",
    "Chris Mpofu": "Pace", "Nathan Bracken": "Pace", "Mitchell Starc": "Pace",
    "David Wiese": "Pace", "Mitchell Johnson": "Pace", "Kemar Roach": "Pace",
    "Abdul Razzaq": "Pace", "Kagiso Rabada": "Pace", "Isuru Udana": "Pace",
    "James Anderson": "Pace", "Mohammad Irfan": "Pace", "Kyle Abbott": "Pace",
    "Shaun Pollock": "Pace", "Wahab Riaz": "Pace", "Marchant de Lange": "Pace",
    "Trent Johnston": "Pace", "Ian Butler": "Pace", "Mohammad Sami": "Pace",
    "Mohammad Asif": "Pace", "Jacques Kallis": "Pace", "Alex Cusack": "Pace",
    "Doug Bracewell": "Pace", "Boyd Rankin": "Pace", "Rory Kleinveldt": "Pace",
    "Shoaib Akhtar": "Pace", "Peter Siddle": "Pace", "James Franklin": "Pace",
    "Dwayne Smith": "Pace", "Scott Styris": "Pace", "Bhuvneshwar Kumar": "Pace",
    "Clint McKay": "Pace", "James Faulkner": "Pace", "Ryan Harris": "Pace",
    "Rusty Theron": "Pace", "Shafiul Islam": "Pace", "Al-Amin Hossain": "Pace",
    "Ajmal Shahzad": "Pace", "Timm van der Gugten": "Pace", "Chris Morris": "Pace",
    "Mitchell McClenaghan": "Pace", "Rob Nicol": "Pace", "Mohit Sharma": "Pace",
    "Beuran Hendricks": "Pace", "RP Singh": "Pace", "Pat Cummins": "Pace",
    "Ben Laughlin": "Pace", "Ben Stokes": "Pace", "David Willey": "Pace",
    "Yasir Arafat": "Pace", "James Hopes": "Pace", "Makhaya Ntini": "Pace",
    "Michael Mason": "Pace", "Andre Russell": "Pace", "Nehemiah Odhiambo": "Pace",
    "Suranga Lakmal": "Pace", "Dilhara Fernando": "Pace", "Chris Jordan": "Pace",
    "Paul Collingwood": "Pace", "Andrew Tye": "Pace", "Iftikhar Anjum": "Pace",
    "Syed Rasel": "Pace", "Kevin O'Brien": "Pace", "Daniel Christian": "Pace",
    "Hardik Pandya": "Pace", "Jasprit Bumrah": "Pace", "Tino Best": "Pace",
    "Mark Gillespie": "Pace", "Taskin Ahmed": "Pace", "Vinay Kumar": "Pace",
    "Charl Langeveldt": "Pace", "Dushmantha Chameera": "Pace",
    "Ravi Bopara": "Pace", "Luke Wright": "Pace", "Virat Kohli": "Pace",

    # Spin (offspin, legspin, left-arm orthodox, chinaman, mystery)
    "Shahid Afridi": "Spin", "Mohammad Hafeez": "Spin", "Saeed Ajmal": "Spin",
    "Daniel Vettori": "Spin", "Imran Tahir": "Spin", "Sunil Narine": "Spin",
    "Ray Price": "Spin", "Ravichandran Ashwin": "Spin", "Harbhajan Singh": "Spin",
    "Graeme Swann": "Spin", "Nathan McCullum": "Spin", "Samuel Badree": "Spin",
    "James Tredwell": "Spin", "Prosper Utseya": "Spin", "Johan Botha": "Spin",
    "Shakib Al Hasan": "Spin", "Ajantha Mendis": "Spin", "Yusuf Pathan": "Spin",
    "Raza Hasan": "Spin", "Yuvraj Singh": "Spin", "Ravindra Jadeja": "Spin",
    "Robin Peterson": "Spin", "Sulieman Benn": "Spin", "Jean-Paul Duminy": "Spin",
    "Rangana Herath": "Spin", "Mahmudullah": "Spin", "Aaron Phangiso": "Spin",
    "David Hussey": "Spin", "Glenn Maxwell": "Spin", "Marlon Samuels": "Spin",
    "Xavier Doherty": "Spin", "Suresh Raina": "Spin", "Shoaib Malik": "Spin",
    "Abdur Razzak": "Spin", "Nikita Miller": "Spin", "Steven Smith": "Spin",
    "Samit Patel": "Spin", "Michael Yardy": "Spin", "Ronnie Hira": "Spin",
    "Graeme Cremer": "Spin", "Sohag Gazi": "Spin", "Steve O'Keefe": "Spin",
    "Muttiah Muralitharan": "Spin", "Abdur Rehman": "Spin", "Brad Hogg": "Spin",
    "Amit Mishra": "Spin", "Kyle McCallan": "Spin", "Sanath Jayasuriya": "Spin",
    "Tillakaratne Dilshan": "Spin", "Narsingh Deonarine": "Spin",
    "Cameron Boyce": "Spin", "Roelof van der Merwe": "Spin", "Rohit Sharma": "Spin",
    "Sachithra Senanayake": "Spin", "Nathan Hauritz": "Spin", "Nasir Hossain": "Spin",
    "Piyush Chawla": "Spin", "Danny Briggs": "Spin", "Imad Wasim": "Spin",
    "Michael Clarke": "Spin", "Chris Gayle": "Spin", "Malinga Bandara": "Spin",

    # Genuinely uncertain / dual-style - deliberately NOT guessed
    "Regan West": "Unknown",       # confirmed dual pace-and-spin bowler
    "Greg Lamb": "Unknown",
    "Andy McKay": "Unknown",
    "Garey Mathurin": "Unknown",
    "Mudassar Bukhari": "Unknown",
    "Ahsan Malik": "Unknown",
}
# fmt: on


def bowler_style(name: str) -> str:
    """'Pace', 'Spin', or 'Unknown' (bowler not reviewed, or genuinely
    ambiguous - see module docstring). Never guesses."""
    return BOWLER_STYLE.get(name, "Unknown")


BOWLER_DISCIPLINE: dict[str, str] = {
    # Left-Arm Fast / Seam (unambiguous public records)
    "Mitchell Starc": "LEFT_ARM_FAST",
    "Trent Boult": "LEFT_ARM_FAST",
    "Zaheer Khan": "LEFT_ARM_FAST",
    "Mohammad Amir": "LEFT_ARM_FAST",
    "Sohail Tanvir": "LEFT_ARM_FAST",
    "Wayne Parnell": "LEFT_ARM_FAST",
    "Dirk Nannes": "LEFT_ARM_FAST",
    "Mitchell McClenaghan": "LEFT_ARM_FAST",
    "Ryan Sidebottom": "LEFT_ARM_FAST",
    "Wahab Riaz": "LEFT_ARM_FAST",
    "Mohammad Irfan": "LEFT_ARM_FAST",
    "Lonwabo Tsotsobe": "LEFT_ARM_FAST",
    "Beuran Hendricks": "LEFT_ARM_FAST",
    "Syed Rasel": "LEFT_ARM_FAST",
    "David Willey": "LEFT_ARM_FAST",
    "James Faulkner": "LEFT_ARM_FAST",
    "RP Singh": "LEFT_ARM_FAST",
    "Ashish Nehra": "LEFT_ARM_FAST",
    "Isuru Udana": "LEFT_ARM_FAST",
    "Irfan Pathan": "LEFT_ARM_FAST",

    # Right-Arm Fast / Seam / Medium
    "Mohammad Asif": "RIGHT_ARM_FAST",
    "Dale Steyn": "RIGHT_ARM_FAST",
    "Morne Morkel": "RIGHT_ARM_FAST",
    "Lasith Malinga": "RIGHT_ARM_FAST",
    "Brett Lee": "RIGHT_ARM_FAST",
    "Jasprit Bumrah": "RIGHT_ARM_FAST",
    "Pat Cummins": "RIGHT_ARM_FAST",
    "Stuart Broad": "RIGHT_ARM_FAST",
    "Steven Finn": "RIGHT_ARM_FAST",
    "Tim Southee": "RIGHT_ARM_FAST",
    "Kagiso Rabada": "RIGHT_ARM_FAST",
    "Shaun Tait": "RIGHT_ARM_FAST",
    "Umar Gul": "RIGHT_ARM_FAST",
    "Kemar Roach": "RIGHT_ARM_FAST",
    "James Anderson": "RIGHT_ARM_FAST",
    "Nuwan Kulasekara": "RIGHT_ARM_FAST",
    "Bhuvneshwar Kumar": "RIGHT_ARM_FAST",
    "Chris Woakes": "RIGHT_ARM_FAST",
    "Kyle Mills": "RIGHT_ARM_FAST",
    "Tim Bresnan": "RIGHT_ARM_FAST",
    "Darren Sammy": "RIGHT_ARM_MEDIUM",
    "Angelo Mathews": "RIGHT_ARM_MEDIUM",
    "Dwayne Bravo": "RIGHT_ARM_MEDIUM",
    "Kieron Pollard": "RIGHT_ARM_MEDIUM",
    "Shane Watson": "RIGHT_ARM_FAST",
    "Jacques Kallis": "RIGHT_ARM_FAST",
    "Albie Morkel": "RIGHT_ARM_FAST",
    "Shoaib Akhtar": "RIGHT_ARM_FAST",
    "Peter Siddle": "RIGHT_ARM_FAST",
    "Doug Bracewell": "RIGHT_ARM_FAST",
    "Boyd Rankin": "RIGHT_ARM_FAST",
    "Shaun Pollock": "RIGHT_ARM_FAST",
    "Marchant de Lange": "RIGHT_ARM_FAST",
    "Ian Butler": "RIGHT_ARM_FAST",
    "Mohammad Sami": "RIGHT_ARM_FAST",
    "Clint McKay": "RIGHT_ARM_FAST",
    "Ryan Harris": "RIGHT_ARM_FAST",
    "Rusty Theron": "RIGHT_ARM_FAST",
    "Chris Morris": "RIGHT_ARM_FAST",
    "Mohit Sharma": "RIGHT_ARM_FAST",
    "Ben Stokes": "RIGHT_ARM_FAST",
    "Hardik Pandya": "RIGHT_ARM_FAST",
    "Andrew Tye": "RIGHT_ARM_MEDIUM",
    "Daniel Christian": "RIGHT_ARM_MEDIUM",
    "Paul Collingwood": "RIGHT_ARM_MEDIUM",
    "Jacob Oram": "RIGHT_ARM_MEDIUM",
    "Jerome Taylor": "RIGHT_ARM_FAST",
    "Mashrafe Mortaza": "RIGHT_ARM_FAST",
    "Fidel Edwards": "RIGHT_ARM_FAST",
    "Thisara Perera": "RIGHT_ARM_MEDIUM",

    # Leg-Spin / Wrist-Spin
    "Shahid Afridi": "LEG_SPIN",
    "Imran Tahir": "LEG_SPIN",
    "Amit Mishra": "LEG_SPIN",
    "Piyush Chawla": "LEG_SPIN",
    "Samuel Badree": "LEG_SPIN",
    "Cameron Boyce": "LEG_SPIN",
    "Brad Hogg": "LEFT_ARM_WRIST_SPIN",
    "Malinga Bandara": "LEG_SPIN",

    # Off-Spin
    "Ravichandran Ashwin": "OFF_SPIN",
    "Harbhajan Singh": "OFF_SPIN",
    "Graeme Swann": "OFF_SPIN",
    "Saeed Ajmal": "OFF_SPIN",
    "Muttiah Muralitharan": "OFF_SPIN",
    "Sunil Narine": "OFF_SPIN",
    "Mohammad Hafeez": "OFF_SPIN",
    "Nathan McCullum": "OFF_SPIN",
    "James Tredwell": "OFF_SPIN",
    "Prosper Utseya": "OFF_SPIN",
    "Johan Botha": "OFF_SPIN",
    "Tillakaratne Dilshan": "OFF_SPIN",

    # Left-Arm Orthodox
    "Daniel Vettori": "LEFT_ARM_ORTHODOX",
    "Ravindra Jadeja": "LEFT_ARM_ORTHODOX",
    "Shakib Al Hasan": "LEFT_ARM_ORTHODOX",
    "Rangana Herath": "LEFT_ARM_ORTHODOX",
    "Abdur Razzak": "LEFT_ARM_ORTHODOX",
    "Ray Price": "LEFT_ARM_ORTHODOX",
    "Robin Peterson": "LEFT_ARM_ORTHODOX",
    "Sulieman Benn": "LEFT_ARM_ORTHODOX",
    "Xavier Doherty": "LEFT_ARM_ORTHODOX",
    "Danny Briggs": "LEFT_ARM_ORTHODOX",
}


def resolve_bowler_discipline(name: str) -> tuple[str, str]:
    """
    Resolves canonical BowlerType enum member name and provenance metadata.
    Returns (enum_name, provenance):
      - ('LEFT_ARM_FAST', 'curated_categorical') if specifically verified in BOWLER_DISCIPLINE
      - ('RIGHT_ARM_FAST', 'unspecified_fallback') if general Pace, but arm/discipline unreviewed
      - ('OFF_SPIN', 'unspecified_fallback') if general Spin, but sub-discipline unreviewed
      - ('RIGHT_ARM_FAST', 'insufficient_data') if Unknown style
    Never guesses arm or discipline for unreviewed players.
    """
    clean_name = str(name).strip()
    for b_name, b_type in BOWLER_DISCIPLINE.items():
        if b_name.lower() == clean_name.lower():
            return b_type, "curated_categorical"

    style = bowler_style(clean_name)
    if style == "Pace":
        return "RIGHT_ARM_FAST", "unspecified_fallback"
    elif style == "Spin":
        return "OFF_SPIN", "unspecified_fallback"
    else:
        return "RIGHT_ARM_FAST", "insufficient_data"


BOWLER_TYPE_MAP: dict[str, str] = {
    # Enum member names from BowlerType
    "RIGHT_ARM_FAST": "Pace",
    "LEFT_ARM_FAST": "Pace",
    "RIGHT_ARM_MEDIUM": "Pace",
    "OFF_SPIN": "Spin",
    "LEG_SPIN": "Spin",
    "LEFT_ARM_ORTHODOX": "Spin",
    "LEFT_ARM_WRIST_SPIN": "Spin",
    # Common alternate forms / aliases
    "PACE": "Pace",
    "SPIN": "Spin",
    "FAST": "Pace",
    "MEDIUM": "Pace",
    "FAST_MEDIUM": "Pace",
    "SLOW_LEFT_ARM": "Spin",
    "WRIST_SPIN": "Spin",
}



def normalize_bowler_type(val: any) -> str:
    """
    Normalizes any BowlerType enum instance, enum name string, bowling style string,
    or bowler name to canonical 'Pace', 'Spin', or 'Unknown'.
    """
    if val is None:
        return "Unknown"

    # If it's an Enum with a name attribute
    if hasattr(val, "name"):
        val_str = str(val.name).strip()
    else:
        val_str = str(val).strip()

    # Exact check in BOWLER_TYPE_MAP (case-insensitive)
    upper_val = val_str.upper()
    if upper_val in BOWLER_TYPE_MAP:
        return BOWLER_TYPE_MAP[upper_val]

    # Check title case directly
    if val_str in ("Pace", "Spin", "Unknown"):
        return val_str

    # Check if it's a known bowler name in BOWLER_STYLE
    if val_str in BOWLER_STYLE:
        return BOWLER_STYLE[val_str]

    # Check case-insensitive bowler name
    for b_name, style in BOWLER_STYLE.items():
        if b_name.lower() == val_str.lower():
            return style

    return "Unknown"
