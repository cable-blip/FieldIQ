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
