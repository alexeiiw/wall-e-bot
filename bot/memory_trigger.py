import re

# Variantes en español (con y sin tilde/voseo) para recordar
_PATRON_RECORDATORIO = re.compile(
    r"(?:recuerda|recordá|recuérdame|acordate|acuérdate|no olvides)\s+que\s+(.+)",
    re.IGNORECASE
)

# Variantes en español para anotar notas
_PATRON_ANOTAR = re.compile(
    r"(?:anota|anotá|anotame|anótame|apunta|apuntá|apúntame)\s+que\s+(.+)",
    re.IGNORECASE
)

# Variantes en español para listar/dime notas
_PATRON_DIME = re.compile(
    r"(?:dime|dimé|cuéntame|muéstrame|qué notas|mis anotaciones|mis notas|mis ideas)\b",
    re.IGNORECASE
)


def detectar_dato_a_recordar(texto: str):
    """Si el texto contiene una frase tipo 'recuerda que...', devuelve el dato a guardar. Si no, devuelve None."""
    match = _PATRON_RECORDATORIO.search(texto)
    if match:
        return match.group(1).strip()
    return None


def detectar_nota_a_anotar(texto: str):
    """Si el texto contiene una frase tipo 'anota que...', devuelve la nota a guardar. Si no, devuelve None."""
    match = _PATRON_ANOTAR.search(texto)
    if match:
        return match.group(1).strip()
    return None


def detectar_solicitud_listar_notas(texto: str):
    """Si el texto contiene una frase tipo 'dime mis notas...', devuelve True. Si no, devuelve False."""
    match = _PATRON_DIME.search(texto)
    return match is not None

