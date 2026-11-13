"""El AFD de la Fase 1, M = (Q, Σ, δ, q0, F), cargado desde archivos de datos.

- datos/matriz_afd.csv : la matriz de transiciones δ (una fila por estado de
  trabajo q0..q19, una columna por clase de símbolos; "-" significa sumidero).
- datos/estados_afd.csv: los 34 estados, cuáles son finales, qué categoría de
  token aceptan y si retroceden (los marcados con * en el documento).

El código no tiene transiciones escritas a mano: si se cambia una celda del CSV,
cambia el comportamiento del lexer.
"""
import csv
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent.parent / 'datos'

# Clases de símbolos (las 24 columnas de la matriz). Cada carácter de entrada se
# convierte primero en su clase y la clase es la que se busca en la matriz.
LETRAS_CON_CLASE_PROPIA = 'xkglbsmin'   # letras que forman sufijos: 4x12, kg, lb, s, min
DIGITOS = '0123456789'
OPERADORES_ARITMETICOS = '+-*/'
DELIMITADORES = '(){};'
SIMBOLOS_CON_CLASE_PROPIA = '.%"#=!<>'
ESPACIOS = ' \t\r'

DESCRIPCION_CLASE = {
    'd': 'un dígito', '.': "'.'", 'L': 'una letra o _', '%': "'%'",
    '"': 'comillas', '#': "'#'", '=': "'='", '!': "'!'", '<': "'<'", '>': "'>'",
    'A': 'un operador + - * /', 'D': 'un delimitador ( ) { } ;',
    'W': 'un espacio', 'N': 'un salto de línea', 'O': 'otro carácter',
}
for _letra in LETRAS_CON_CLASE_PROPIA:
    DESCRIPCION_CLASE[_letra] = f"'{_letra}'"


def clase_de(caracter):
    """Devuelve la clase de símbolos (columna de la matriz) de un carácter."""
    if caracter in DIGITOS:
        return 'd'
    if caracter in LETRAS_CON_CLASE_PROPIA:
        return caracter
    if caracter == '_' or (caracter.isascii() and caracter.isalpha()):
        return 'L'
    if caracter in SIMBOLOS_CON_CLASE_PROPIA:
        return caracter
    if caracter in OPERADORES_ARITMETICOS:
        return 'A'
    if caracter in DELIMITADORES:
        return 'D'
    if caracter in ESPACIOS:
        return 'W'
    if caracter == '\n':
        return 'N'
    return 'O'


def _leer_csv(nombre):
    # QUOTE_NONE porque una de las columnas se llama literalmente "
    with open(CARPETA_DATOS / nombre, encoding='utf-8', newline='') as f:
        return [fila for fila in csv.reader(f, quoting=csv.QUOTE_NONE) if fila]


def _numero(estado):
    return int(estado[1:])   # "q14" -> 14


class Automata:
    """AFD cargado desde los CSV. Los estados se manejan como enteros (q14 -> 14)."""

    def __init__(self):
        estados = _leer_csv('estados_afd.csv')[1:]
        self.nombre = {}
        self.categoria_final = {}      # estado final -> categoría del token
        self.retrocede = set()         # finales marcados con * en el documento
        self.sumidero = None
        for estado, nombre, tipo, categoria, retrocede in estados:
            q = _numero(estado)
            self.nombre[q] = nombre
            if tipo == 'final':
                self.categoria_final[q] = categoria
                if retrocede == 'si':
                    self.retrocede.add(q)
            elif tipo == 'sumidero':
                self.sumidero = q

        filas = _leer_csv('matriz_afd.csv')
        self.clases = filas[0][1:]
        self.delta = {}
        for fila in filas[1:]:
            q = _numero(fila[0])
            self.delta[q] = {c: (self.sumidero if destino == '-' else _numero(destino))
                             for c, destino in zip(self.clases, fila[1:])}
        self.inicial = 0

    def transicion(self, estado, clase):
        """δ(estado, clase). Los finales y el sumidero no tienen transiciones."""
        return self.delta[estado][clase]

    def es_final(self, estado):
        return estado in self.categoria_final

    def esperado(self, estado):
        """Explica, a partir de la matriz, qué caracteres sí aceptaba un estado."""
        continua, termina = [], False
        for c in self.clases:
            destino = self.delta[estado][c]
            if destino == self.sumidero:
                continue
            if self.es_final(destino) and destino in self.retrocede:
                termina = True          # el carácter no es del token: solo lo cierra
            else:
                continua.append(c)      # el carácter sí forma parte del token
        letras = list(LETRAS_CON_CLASE_PROPIA) + ['L']
        if all(c in continua for c in letras):          # todas las letras -> "una letra"
            continua = [c for c in continua if c not in letras] + ['L']
        partes = [DESCRIPCION_CLASE[c] for c in continua]
        if termina:
            partes.append('un separador (espacio, operador, delimitador...) para cerrar el token')
        return ', '.join(partes) if partes else 'nada'


AUTOMATA = Automata()
