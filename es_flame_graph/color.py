"""
Color mapping module

Implements Brendan Gregg's color hashing algorithm for flame graphs.
"""

import re


def namehash(name: str) -> float:
    """
    Generate a vector hash for a name string, weighting early over later characters.
    This ensures the same function name gets the same color across different flame graphs.

    Ported from Brendan Gregg's flamegraph.pl

    Args:
        name: Function name

    Returns:
        Hash value between 0 and 1
    """
    vector = 0
    weight = 1
    max_val = 1
    mod = 10

    # Remove module name prefix if present (e.g., "java.")
    name = re.sub(r".*?`", "", name)

    for c in name:
        i = ord(c) % mod
        vector += (i / (mod - 1)) * weight
        max_val += 1 * weight
        weight *= 0.70
        if mod > 12:
            break
        mod += 1

    return 1 - vector / max_val


def sum_namehash(name: str) -> int:
    """
    Simple string hash for random_namehash.

    Ported from Brendan Gregg's flamegraph.pl

    Args:
        name: Function name

    Returns:
        Integer hash value
    """
    return hash(name) & 0xFFFFFFFF


def random_namehash(name: str) -> float:
    """
    Generate a random-looking hash for name string.
    This ensures functions with the same name have the same color.

    Ported from Brendan Gregg's flamegraph.pl

    Args:
        name: Function name

    Returns:
        Random-looking value between 0 and 1
    """
    h = sum_namehash(name)
    # Use the hash as a seed
    import random

    random.seed(h)
    return random.random()


def color_hot(hash_val1: float, hash_val2: float, hash_val3: float) -> str:
    """
    Generate hot color theme colors (orange/red/yellow spectrum).

    Ported from Brendan Gregg's flamegraph.pl --color=hot

    Args:
        hash_val1: First hash value
        hash_val2: Second hash value
        hash_val3: Third hash value

    Returns:
        RGB color string
    """
    r = 205 + int(50 * hash_val3)
    g = 0 + int(230 * hash_val1)
    b = 0 + int(55 * hash_val2)
    return f"rgb({r},{g},{b})"


def color_mem(hash_val1: float, hash_val2: float, hash_val3: float) -> str:
    """
    Generate memory color theme colors (green spectrum).

    Ported from Brendan Gregg's flamegraph.pl --color=mem

    Args:
        hash_val1: First hash value
        hash_val2: Second hash value
        hash_val3: Third hash value

    Returns:
        RGB color string
    """
    r = 0
    g = 190 + int(50 * hash_val2)
    b = 0 + int(210 * hash_val1)
    return f"rgb({r},{g},{b})"


def color_java(name: str) -> str:
    """
    Generate color for Java functions based on function type.

    Ported from Brendan Gregg's flamegraph.pl --color=java

    Args:
        name: Function name (may include annotations)

    Returns:
        RGB color string
    """
    # Check for annotations
    if "_[j]" in name:  # JIT compiled
        type_ = "green"
    elif "_[i]" in name:  # Inlined
        type_ = "aqua"
    elif "_[k]" in name:  # Kernel
        type_ = "orange"
    elif re.match(r"^(java|javax|jdk|net|org|com|io|sun)/", name):  # Java
        type_ = "green"
    elif ":::" in name:  # Java, typical perf-map-agent method separator
        type_ = "green"
    elif "::" in name:  # C++
        type_ = "yellow"
    else:  # System
        type_ = "red"

    # Fall through to color palettes
    return _get_color_by_type(type_, name)


def _get_color_by_type(type_: str, name: str) -> str:
    """
    Get color based on type.

    Args:
        type_: Color type (red, green, blue, yellow, purple, aqua, orange)
        name: Function name for hashing

    Returns:
        RGB color string
    """
    v1 = random_namehash(name)
    v2 = random_namehash(name)
    v3 = random_namehash(name)

    if type_ == "red":
        r = 200 + int(55 * v1)
        x = 50 + int(80 * v1)
        return f"rgb({r},{x},{x})"
    elif type_ == "green":
        g = 200 + int(55 * v1)
        x = 50 + int(60 * v1)
        return f"rgb({x},{g},{x})"
    elif type_ == "blue":
        b = 205 + int(50 * v1)
        x = 80 + int(60 * v1)
        return f"rgb({x},{x},{b})"
    elif type_ == "yellow":
        x = 175 + int(55 * v1)
        b = 50 + int(20 * v1)
        return f"rgb({x},{x},{b})"
    elif type_ == "purple":
        x = 190 + int(65 * v1)
        g = 80 + int(60 * v1)
        return f"rgb({x},{g},{x})"
    elif type_ == "aqua":
        r = 50 + int(60 * v1)
        g = 165 + int(55 * v1)
        b = 165 + int(55 * v1)
        return f"rgb({r},{g},{b})"
    elif type_ == "orange":
        r = 190 + int(65 * v1)
        g = 90 + int(65 * v1)
        return f"rgb({r},{g},0)"
    else:
        return "rgb(0,0,0)"


def get_color(name: str, theme: str = "hot") -> str:
    """
    Get color for a function name.

    This function implements Brendan Gregg's color hashing algorithm
    to ensure the same function name gets the same color across
    different flame graphs.

    Special cases:
    - "-" or "--" returns gray (for stack separators)
    - Functions with annotations use specific colors
    - Java functions use java theme colors

    Args:
        name: Function name (may include annotations)
        theme: Color theme (hot, java, mem, io, wakeup, chain,
                         red, green, blue, yellow, purple, aqua, orange)

    Returns:
        RGB color string (e.g., "rgb(255,100,50)")
    """
    # Handle special separators
    if name == "--":
        return "rgb(160, 160, 160)"
    if name == "-":
        return "rgb(200, 200, 200)"

    # Handle java theme
    if theme == "java":
        return color_java(name)

    # Handle other themes that use type detection
    if theme in [
        "hot",
        "mem",
        "io",
        "wakeup",
        "chain",
        "red",
        "green",
        "blue",
        "yellow",
        "purple",
        "aqua",
        "orange",
    ]:
        v1 = random_namehash(name)
        v2 = random_namehash(name)
        v3 = random_namehash(name)

        if theme == "hot":
            return color_hot(v1, v2, v3)
        elif theme == "mem":
            return color_mem(v1, v2, v3)
        elif theme == "io":
            r = 80 + int(60 * v1)
            g = r
            b = 190 + int(55 * v2)
            return f"rgb({r},{g},{b})"
        elif theme == "wakeup":
            return _get_color_by_type("aqua", name)
        elif theme == "chain":
            if "_[w]" in name:  # Waker
                return _get_color_by_type("aqua", name)
            else:  # Off-CPU
                return _get_color_by_type("blue", name)
        else:
            return _get_color_by_type(theme, name)

    # Default: use hot theme
    v1 = random_namehash(name)
    v2 = random_namehash(name)
    v3 = random_namehash(name)
    return color_hot(v1, v2, v3)
