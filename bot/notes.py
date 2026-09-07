from bot.config import NOTES_PATH
import os


def guardar_nota(nota: str) -> str:
    """Agrega una nueva nota al archivo de notas e ideas persistente."""
    with open(NOTES_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n- {nota}")
    return f"Anotado: {nota}"


def cargar_notas() -> str:
    """Lee todas las notas guardadas y devuelve un string formateado."""
    if os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            contenido = f.read()
        # Extrae solo las líneas de notas (después del header)
        lineas = contenido.split("\n")
        notas = [l for l in lineas if l.strip().startswith("- ")]
        if notas:
            return "Tus notas e ideas:\n" + "\n".join(notas)
    return "No tienes notas anotadas aún."


def listar_notas_corto() -> str:
    """Devuelve solo el listado de notas (sin header)."""
    if os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            contenido = f.read()
        lineas = contenido.split("\n")
        notas = [l for l in lineas if l.strip().startswith("- ")]
        if notas:
            return "\n".join(notas)
    return "Sin notas aún."


def buscar_notas(query: str) -> list:
    """Devuelve las notas que contengan el término buscado (case-insensitive)."""
    if not os.path.exists(NOTES_PATH):
        return []
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        contenido = f.read()
    lineas = contenido.split("\n")
    notas = [l for l in lineas if l.strip().startswith("- ")]
    query_lower = query.strip().lower()
    return [n for n in notas if query_lower in n.lower()]
