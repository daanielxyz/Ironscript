"""Tokens de IronScript (Fase 1).

Un token es la unidad que el lexer le entrega al parser: su categoría, el texto
exacto que lo formó (lexema) y dónde empieza en el archivo (fila y columna,
contando desde 1).
"""
from dataclasses import dataclass

# Tabla de palabras reservadas. El AFD reconoce estas palabras como ID (estado
# q20) y después el lexer las busca aquí para reclasificarlas.
PALABRAS_RESERVADAS = frozenset({
    'rutina', 'var', 'serie', 'con', 'descanso',
    'si', 'sino', 'repetir', 'y', 'o', 'no',
})

# Categorías cuyo lexema siempre es uno de pocos textos fijos. En la gramática
# aparecen entre comillas ("si", "{", "==" ...), así que el parser las reconoce
# por su lexema. Las demás categorías (ID, ENTERO, PESO ...) aparecen en la
# gramática por su nombre.
CATEGORIAS_POR_LEXEMA = frozenset({
    'PALABRA_RESERVADA', 'OP_ARITMETICO', 'OP_RELACIONAL',
    'ASIGNACION', 'DELIMITADOR',
})

FIN_DE_ARCHIVO = 'EOF'
SIMBOLO_FIN = '$'   # nombre del fin de archivo en la gramática y en FOLLOW


@dataclass(frozen=True)
class Token:
    categoria: str
    lexema: str
    fila: int
    columna: int

    @property
    def terminal(self):
        """Nombre con el que este token aparece en la gramática."""
        if self.categoria == FIN_DE_ARCHIVO:
            return SIMBOLO_FIN
        if self.categoria in CATEGORIAS_POR_LEXEMA:
            return self.lexema
        return self.categoria

    def describir(self):
        """Texto corto para mensajes de error."""
        if self.categoria == FIN_DE_ARCHIVO:
            return 'el fin del archivo'
        return f"'{self.lexema}'"
