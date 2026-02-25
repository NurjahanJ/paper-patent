"""
Ferrofluid classification taxonomy.

Source: FEROFLUIDS_CLASS_DEFINITION.txt
24 class codes across 5 major categories.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassCode:
    code: int
    major_category: str
    description: str


# --- All 24 class codes ---

TAXONOMY: dict[int, ClassCode] = {
    11: ClassCode(11, "Material", "Chemistry"),
    12: ClassCode(12, "Material", "Formulation"),
    13: ClassCode(13, "Material", "Properties"),
    14: ClassCode(14, "Material", "Evaluation / Characterization"),
    15: ClassCode(15, "Material", "Manipulation, Droplets, other"),
    16: ClassCode(16, "Material", "Handling of"),
    21: ClassCode(21, "Computation", "FEA"),
    22: ClassCode(22, "Computation", "CFD"),
    23: ClassCode(23, "Computation", "MATLAB"),
    24: ClassCode(24, "Computation", "Modelling (ODE, Boundary value, Two-phase, Lifting force, Magneto-optical, Dipole, Strain Energy, Susceptibility)"),
    25: ClassCode(25, "Computation", "Flow"),
    26: ClassCode(26, "Computation", "Heat"),
    27: ClassCode(27, "Computation", "Modelling"),
    28: ClassCode(28, "Computation", "Stability and other"),
    29: ClassCode(29, "Computation", "Magnetic Droplets, Spin of droplet"),
    37: ClassCode(37, "Experimentation", "Other than evaluation indicated in class 14"),
    38: ClassCode(38, "Application", "Using principles of magnetic induction"),
    39: ClassCode(39, "Application", "Medical Robotic Surgery"),
    40: ClassCode(40, "Application", "Medical (Hyperthermia, Cancer, Drug Delivery)"),
    41: ClassCode(41, "Application", "Medical (Pharmaceutical)"),
    42: ClassCode(42, "Application", "Biomedical"),
    43: ClassCode(43, "Application", "Robotics - general"),
    44: ClassCode(44, "Application", "Geology, Oil-field recovery"),
    45: ClassCode(45, "Application", "Flow"),
    46: ClassCode(46, "Application", "Heat transfer"),
    47: ClassCode(47, "Application", "Bearing, Seal, Lubricant"),
    48: ClassCode(48, "Application", "Levitation, Spin of droplets"),
    49: ClassCode(49, "Application", "Digital Micro Fluids, Damping, Physics, Environmental, Engineering, Instruments to evaluate FF"),
    50: ClassCode(50, "Review / Book", "Review - Survey"),
    51: ClassCode(51, "Review / Book", "Book / Book chapter"),
}

VALID_CODES = set(TAXONOMY.keys())

MAJOR_CATEGORIES = {
    1: "Material",
    2: "Computation",
    3: "Experimentation",
    4: "Application",
    5: "Review / Book",
}


def get_class_description(code: int) -> str:
    """Return 'Major Category > Description' for a class code."""
    if code in TAXONOMY:
        c = TAXONOMY[code]
        return f"{c.major_category} > {c.description}"
    return f"Unknown class ({code})"


def get_major_category(code: int) -> str:
    """Return the major category for a class code."""
    if code in TAXONOMY:
        return TAXONOMY[code].major_category
    return "Unknown"


def format_taxonomy_for_prompt() -> str:
    """Format the full taxonomy as text for inclusion in AI prompts."""
    lines = ["FERROFLUID CLASSIFICATION CODES:", ""]
    current_major = ""
    for code in sorted(TAXONOMY.keys()):
        c = TAXONOMY[code]
        if c.major_category != current_major:
            current_major = c.major_category
            lines.append(f"--- {current_major.upper()} ---")
        lines.append(f"  {c.code}: {c.description}")
    return "\n".join(lines)
