"""Errores que reportan el lexer y el parser, siempre con fila y columna."""
from dataclasses import dataclass


@dataclass
class ErrorLexico:
    fila: int
    columna: int
    mensaje: str
    detalle: str   # la transición del AFD que falló, p. ej. "δ(q9, g) = sumidero"

    def __str__(self):
        return (f'Error léxico en fila {self.fila}, columna {self.columna}: '
                f'{self.mensaje}\n    AFD: {self.detalle}')


@dataclass
class ErrorSintactico:
    fila: int
    columna: int
    mensaje: str

    def __str__(self):
        return f'Error sintáctico en fila {self.fila}, columna {self.columna}: {self.mensaje}'


class ErrorDeGramatica(Exception):
    """La gramática del archivo .bnf está mal escrita o no es LL(1)."""
