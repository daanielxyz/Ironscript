"""Lectura de la gramática G (archivo .bnf) y cálculo de FIRST, FOLLOW, PREDICT
y la tabla LL(1).

El parser no tiene las reglas escritas en el código: las saca de aquí. Por eso,
si se modifica datos/gramatica.bnf, el parser acepta el lenguaje nuevo, y si la
modificación rompe la condición LL(1) el programa lo detecta y dice en qué
celda de la tabla está el conflicto.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from .errores import ErrorDeGramatica
from .tokens import SIMBOLO_FIN

ARCHIVO_GRAMATICA = Path(__file__).resolve().parent.parent / 'datos' / 'gramatica.bnf'
EPSILON = 'ε'

# Piezas de una regla BNF: "literal", <no_terminal>, CATEGORIA, ε o |
_PIEZA = re.compile(r'\s*(?:"([^"]+)"|(<[a-z_]+>)|([A-Z_]+)|(ε)|(\|))')


@dataclass(frozen=True)
class Produccion:
    numero: int            # número de la producción, en el orden del archivo (desde 1)
    izquierda: str         # el no terminal, p. ej. '<expr>'
    derecha: tuple         # símbolos del lado derecho; () es ε

    def __str__(self):
        cuerpo = ' '.join(mostrar(s) for s in self.derecha) if self.derecha else EPSILON
        return f'{self.izquierda} ::= {cuerpo}'


def es_no_terminal(simbolo):
    return simbolo.startswith('<') and simbolo.endswith('>') and len(simbolo) > 2


def mostrar(simbolo, literales=None):
    """Cómo se escribe un símbolo en la gramática: los literales van entre comillas."""
    if es_no_terminal(simbolo) or simbolo == SIMBOLO_FIN:
        return simbolo
    if simbolo.isupper() and simbolo.replace('_', '').isalpha():
        return simbolo           # categoría de token: ID, ENTERO ...
    return f'"{simbolo}"'


class Gramatica:
    def __init__(self, texto):
        self.producciones = []
        self.no_terminales = []          # en orden de aparición; el primero es el inicial
        self.reglas = {}                 # no terminal -> lista de producciones
        self._leer(texto)
        self.inicial = self.no_terminales[0]
        self.terminales = sorted({s for p in self.producciones for s in p.derecha
                                  if not es_no_terminal(s)})
        self._validar()
        self.anulables = self._calcular_anulables()
        self.first = self._calcular_first()
        self.follow = self._calcular_follow()
        self.predict = {p: self._calcular_predict(p) for p in self.producciones}
        self.tabla, self.conflictos = self._construir_tabla()

    # ---------- lectura del archivo .bnf ----------
    def _leer(self, texto):
        actual = None
        for n_linea, linea in enumerate(texto.splitlines(), start=1):
            linea = linea.split('#', 1)[0].strip()
            if not linea:
                continue
            if '::=' in linea:
                izquierda, linea = (x.strip() for x in linea.split('::=', 1))
                if not es_no_terminal(izquierda):
                    raise ErrorDeGramatica(f'línea {n_linea}: {izquierda!r} no es un no terminal <...>')
                if izquierda in self.reglas:
                    raise ErrorDeGramatica(f'línea {n_linea}: {izquierda} está definido dos veces')
                actual = izquierda
                self.no_terminales.append(actual)
                self.reglas[actual] = []
            elif linea.startswith('|') and actual:
                linea = linea[1:]        # la línea continúa la regla anterior
            else:
                raise ErrorDeGramatica(f'línea {n_linea}: se esperaba "<no_terminal> ::= ..." o "| ..."')
            self._leer_alternativas(linea, n_linea, actual)

    def _leer_alternativas(self, linea, n_linea, izquierda):
        """Agrega una producción por cada alternativa separada con |."""
        simbolos, vista, pos = [], False, 0
        linea = linea.rstrip()
        while pos < len(linea):
            m = _PIEZA.match(linea, pos)
            if not m or m.end() == pos:
                raise ErrorDeGramatica(f'línea {n_linea}: no se entiende {linea[pos:].strip()!r}')
            pos = m.end()
            literal, no_terminal, categoria, epsilon, barra = m.groups()
            if barra:
                if not vista:
                    raise ErrorDeGramatica(f'línea {n_linea}: alternativa vacía (escriba ε)')
                self._agregar(izquierda, simbolos)
                simbolos, vista = [], False
            elif epsilon:
                vista = True             # ε no agrega símbolos
            else:
                simbolos.append(literal or no_terminal or categoria)
                vista = True
        if not vista:
            raise ErrorDeGramatica(f'línea {n_linea}: alternativa vacía (escriba ε)')
        self._agregar(izquierda, simbolos)

    def _agregar(self, izquierda, simbolos):
        p = Produccion(len(self.producciones) + 1, izquierda, tuple(simbolos))
        self.producciones.append(p)
        self.reglas[izquierda].append(p)

    def _validar(self):
        for p in self.producciones:
            for s in p.derecha:
                if es_no_terminal(s) and s not in self.reglas:
                    raise ErrorDeGramatica(f'{s} se usa en "{p}" pero no tiene regla')
        for a in self.no_terminales:
            if not self.reglas[a]:
                raise ErrorDeGramatica(f'{a} no tiene producciones')

    # ---------- conjuntos ----------
    def _calcular_anulables(self):
        """No terminales que pueden derivar ε (punto fijo)."""
        anulables, cambio = set(), True
        while cambio:
            cambio = False
            for p in self.producciones:
                if p.izquierda not in anulables and all(s in anulables for s in p.derecha):
                    anulables.add(p.izquierda)
                    cambio = True
        return anulables

    def first_de(self, simbolos):
        """FIRST de una secuencia de símbolos (sin ε; usar anula() para saber si deriva ε)."""
        resultado = set()
        for s in simbolos:
            if not es_no_terminal(s):
                resultado.add(s)
                return resultado
            resultado |= self.first[s]
            if s not in self.anulables:
                return resultado
        return resultado

    def anula(self, simbolos):
        return all(es_no_terminal(s) and s in self.anulables for s in simbolos)

    def _calcular_first(self):
        self.first = {a: set() for a in self.no_terminales}
        cambio = True
        while cambio:
            cambio = False
            for p in self.producciones:
                nuevo = self.first_de(p.derecha) - self.first[p.izquierda]
                if nuevo:
                    self.first[p.izquierda] |= nuevo
                    cambio = True
        return self.first

    def _calcular_follow(self):
        follow = {a: set() for a in self.no_terminales}
        follow[self.inicial].add(SIMBOLO_FIN)
        cambio = True
        while cambio:
            cambio = False
            for p in self.producciones:
                for i, b in enumerate(p.derecha):
                    if not es_no_terminal(b):
                        continue
                    resto = p.derecha[i + 1:]
                    nuevo = set(self.first_de(resto))
                    if self.anula(resto):
                        nuevo |= follow[p.izquierda]
                    if not nuevo <= follow[b]:
                        follow[b] |= nuevo
                        cambio = True
        return follow

    def _calcular_predict(self, p):
        resultado = set(self.first_de(p.derecha))
        if self.anula(p.derecha):
            resultado |= self.follow[p.izquierda]
        return resultado

    def _construir_tabla(self):
        """tabla[(A, a)] = producción a usar. Un conflicto es una celda con dos producciones."""
        tabla, conflictos = {}, []
        for p in self.producciones:
            for a in sorted(self.predict[p]):
                celda = (p.izquierda, a)
                if celda in tabla:
                    conflictos.append((celda, tabla[celda], p))
                else:
                    tabla[celda] = p
        return tabla, conflictos

    def esperados(self, no_terminal):
        """Terminales con los que puede seguir el análisis al expandir este no terminal."""
        return sorted(a for (x, a) in self.tabla if x == no_terminal)

    def exigir_ll1(self):
        if self.conflictos:
            lineas = [f'  celda M[{a}, {mostrar(t)}]: "{p1}"  vs  "{p2}"'
                      for (a, t), p1, p2 in self.conflictos]
            raise ErrorDeGramatica('la gramática no es LL(1); conflictos:\n' + '\n'.join(lineas))

    def advertencias_lexicas(self, categorias_del_lexer, palabras_reservadas):
        """Diferencias entre lo que la gramática espera y lo que el lexer produce."""
        avisos = []
        for t in self.terminales:
            es_palabra = t.isalpha() and t.islower()
            if t.isupper() and t not in categorias_del_lexer:
                avisos.append(f'la categoría {t} no la produce ningún estado final del AFD')
            if es_palabra and t not in palabras_reservadas:
                avisos.append(f'"{t}" está en la gramática pero no en PALABRAS_RESERVADAS '
                              f'(el lexer lo leería como ID)')
        for palabra in sorted(palabras_reservadas):
            if palabra not in self.terminales:
                avisos.append(f'la palabra reservada "{palabra}" no aparece en la gramática')
        return avisos


def cargar_gramatica(ruta=ARCHIVO_GRAMATICA):
    with open(ruta, encoding='utf-8') as f:
        return Gramatica(f.read())
