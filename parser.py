"""Analizador sintáctico LL(1) predictivo (descendente, con pila).

Algoritmo (el de clase para LL(1)):
    pila = [$, símbolo inicial]
    repetir:
        X = cima de la pila, a = token actual
        si X es terminal:      si X == a, se saca X y se avanza; si no, error.
        si X es no terminal:   se busca la producción M[X, a] en la tabla LL(1);
                               se saca X y se apilan los símbolos del lado derecho
                               en orden inverso (el primero queda en la cima).
        si X es $:             si a también es $, la cadena se acepta.

Las producciones salen de datos/gramatica.bnf (módulo gramatica): aquí no hay
reglas de IronScript escritas a mano. Cada expansión crea los hijos del nodo en
el árbol de derivación, y el orden de expansión es la derivación más a la
izquierda.

Recuperación de errores, para listar varios errores en una sola pasada:
- Terminal esperado que no llega: si el token siguiente sí es el esperado, el
  actual sobra y se descarta; si no, se supone que el terminal falta y se saca
  de la pila.
- No terminal sin celda en la tabla: si deriva ε se aplica su producción vacía
  (el error saldrá más adelante, con un mensaje más preciso); si no, se reporta
  y, si el token está en FOLLOW del no terminal, se saca de la pila; si no, se
  descarta el token (modo pánico).
- Después de un error no se reportan más hasta que un terminal se lea bien, para
  no llenar la lista de errores en cascada.
"""
from dataclasses import dataclass, field

from .arbol import Nodo
from .errores import ErrorSintactico
from .gramatica import es_no_terminal, mostrar, EPSILON
from .tokens import SIMBOLO_FIN

# Solo para que los mensajes de error se lean mejor. Si un no terminal no está
# aquí, el mensaje lista los tokens que admite la tabla LL(1).
DESCRIPCION = {
    '<programa>': 'una rutina (rutina "nombre" { ... })',
    '<rutina>': 'una rutina (rutina "nombre" { ... })',
    '<bloque>': "un bloque que empiece con '{'",
    '<sentencia>': 'una sentencia (var, serie, descanso, si, repetir o una asignación)',
    '<expr>': 'una expresión',
    '<conj>': 'una expresión', '<neg>': 'una expresión', '<rel>': 'una expresión',
    '<arit>': 'una expresión', '<term>': 'una expresión', '<unario>': 'una expresión',
    '<prim>': 'un valor (número, peso, tiempo, porcentaje, variable o paréntesis)',
    '<oprel>': 'un operador de comparación', '<opsuma>': "'+' o '-'", '<opmul>': "'*' o '/'",
}


@dataclass
class ResultadoSintactico:
    arbol: Nodo
    errores: list = field(default_factory=list)
    derivacion: list = field(default_factory=list)   # producciones en orden (más a la izquierda)

    @property
    def valido(self):
        return not self.errores


class Parser:
    def __init__(self, gramatica, tokens, registrar_pasos=False):
        gramatica.exigir_ll1()
        self.g = gramatica
        self.tokens = tokens          # el último es EOF
        self.i = 0
        self.errores = []
        self.derivacion = []
        self.silencio = False
        # Si se pide, se guarda cada paso del algoritmo (para la interfaz visual).
        self.pasos = [] if registrar_pasos else None

    @property
    def actual(self):
        return self.tokens[self.i]

    def analizar(self):
        raiz = Nodo(self.g.inicial)
        pila = [(SIMBOLO_FIN, None), (self.g.inicial, raiz)]
        while pila:
            simbolo, nodo = pila[-1]
            a = self.actual.terminal
            if simbolo == SIMBOLO_FIN:
                if a != SIMBOLO_FIN:
                    self._anotar(pila, 'error', f'sobra {self.actual.describir()} después del final')
                    self._error(self.actual, f'sobra {self.actual.describir()}: '
                                             f'el programa ya terminó en la rutina anterior')
                else:
                    self._anotar(pila, 'aceptar', 'la pila y la entrada llegaron a $: se acepta')
                pila.pop()
            elif not es_no_terminal(simbolo):
                self._terminal(pila, simbolo, nodo, a)
            else:
                self._no_terminal(pila, simbolo, nodo, a)
        return ResultadoSintactico(raiz, self.errores, self.derivacion)

    def _terminal(self, pila, simbolo, nodo, a):
        if simbolo == a:
            self._anotar(pila, 'emparejar', f'{mostrar(simbolo)} coincide con el token: se saca y se avanza')
            nodo.token = self.actual
            pila.pop()
            self.i += 1
            self.silencio = False
            return
        siguiente = self.tokens[min(self.i + 1, len(self.tokens) - 1)]
        if a != SIMBOLO_FIN and siguiente.terminal == simbolo:
            self._anotar(pila, 'error', f'sobra {self.actual.describir()}: se descarta')
            self._error(self.actual, f'sobra {self.actual.describir()} '
                                     f'(se esperaba {mostrar(simbolo)})')
            self.i += 1                      # se descarta el token sobrante
            return
        self._anotar(pila, 'error', f'falta {mostrar(simbolo)}: se saca de la pila')
        self._faltante(simbolo)
        pila.pop()                           # se supone que el terminal estaba

    def _no_terminal(self, pila, simbolo, nodo, a):
        produccion = self.g.tabla.get((simbolo, a))
        if produccion is not None:
            self._anotar(pila, 'expandir', f'M[{simbolo}, {mostrar(a)}] = ({produccion.numero}) {produccion}',
                         produccion.numero)
        elif simbolo in self.g.anulables:
            produccion = next(p for p in self.g.reglas[simbolo] if self.g.anula(p.derecha))
            self._anotar(pila, 'expandir', f'M[{simbolo}, {mostrar(a)}] está vacía; {simbolo} deriva ε: '
                                           f'({produccion.numero}) {produccion}', produccion.numero)
        if produccion is not None:
            pila.pop()
            nodo.produccion = produccion
            self.derivacion.append(produccion)
            if not produccion.derecha:
                nodo.hijos = [Nodo(EPSILON)]
            else:
                nodo.hijos = [Nodo(s) for s in produccion.derecha]
                for hijo in reversed(nodo.hijos):
                    pila.append((hijo.simbolo, hijo))
            return
        esperado = DESCRIPCION.get(simbolo) or 'uno de: ' + ', '.join(
            mostrar(t) for t in self.g.esperados(simbolo))
        abandona = a == SIMBOLO_FIN or a in self.g.follow[simbolo]
        self._anotar(pila, 'error', f'M[{simbolo}, {mostrar(a)}] está vacía: ' +
                     ('se abandona ' + simbolo if abandona else 'se descarta el token'))
        self._error(self.actual, f'se esperaba {esperado} pero se encontró {self.actual.describir()}')
        if abandona:
            nodo.falta = True
            pila.pop()                       # se abandona este no terminal
        else:
            self.i += 1                      # modo pánico: se descarta el token

    def _anotar(self, pila, tipo, accion, produccion=None):
        if self.pasos is not None:
            self.pasos.append({'pila': [mostrar(s) for s, _ in pila], 'token': self.i, 'tipo': tipo,
                               'accion': accion, 'produccion': produccion})

    def _faltante(self, simbolo):
        """Error de terminal faltante. Si el token actual ya está en otra línea, el
        error se ubica justo después del token anterior (p. ej. falta ';')."""
        actual = self.actual
        anterior = self.tokens[self.i - 1] if self.i > 0 else None
        if anterior is not None and anterior.fila < actual.fila:
            if self.silencio:
                return
            self.errores.append(ErrorSintactico(
                anterior.fila, anterior.columna + len(anterior.lexema),
                f"falta {mostrar(simbolo)} después de '{anterior.lexema}'"))
            self.silencio = True
        else:
            self._error(actual, f'se esperaba {mostrar(simbolo)} pero se encontró {actual.describir()}')

    def _error(self, token, mensaje):
        if self.silencio:
            return
        self.errores.append(ErrorSintactico(token.fila, token.columna, mensaje))
        self.silencio = True


def analizar_sintaxis(gramatica, tokens):
    return Parser(gramatica, tokens).analizar()
