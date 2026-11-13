"""Analizador léxico de IronScript: ejecuta el AFD de la Fase 1 sobre el texto.

Reglas (las mismas del documento de la Fase 1):
1. Se lee carácter por carácter; cada carácter se convierte en su clase y se
   busca δ(estado, clase) en la matriz.
2. Volver a q0 significa que se leyó un espacio, un salto de línea o el final
   de un comentario: se descarta y empieza un token nuevo.
3. Al llegar a un estado final se emite un token. Si el final está marcado con
   retroceso (*), el último carácter leído no es parte del token y se vuelve a
   leer desde q0 (así se obtiene siempre el lexema más largo).
4. Un ID cuyo lexema está en la tabla de palabras reservadas se reclasifica.
5. Llegar al sumidero es un error léxico. Se reporta y el lexer se recupera
   (modo pánico) para seguir buscando más errores.
6. Si el archivo no termina en salto de línea se le agrega uno, para que el
   último token siempre tenga un carácter de frontera.
"""
from .afd import AUTOMATA, clase_de
from .errores import ErrorLexico
from .tokens import Token, PALABRAS_RESERVADAS, FIN_DE_ARCHIVO

SEPARADORES = ('W', 'N', 'D')   # clases donde termina la recuperación de un error


class Lexer:
    def __init__(self, texto, automata=AUTOMATA):
        self.original = texto
        self.texto = texto if texto.endswith('\n') else texto + '\n'
        self.afd = automata
        self.tokens = []
        self.errores = []
        self.traza = []    # (índice, estado_anterior, carácter, clase, estado_nuevo) por cada paso
        self._posiciones = self._calcular_posiciones()

    def _calcular_posiciones(self):
        """(fila, columna) de cada índice del texto, contando desde 1."""
        posiciones, fila, columna = [], 1, 1
        for c in self.texto:
            posiciones.append((fila, columna))
            if c == '\n':
                fila, columna = fila + 1, 1
            else:
                columna += 1
        return posiciones

    def analizar(self):
        """Recorre todo el texto. Devuelve (tokens, errores); tokens termina en EOF."""
        afd, texto = self.afd, self.texto
        i, estado, inicio = 0, afd.inicial, 0
        while i < len(texto):
            caracter = texto[i]
            clase = clase_de(caracter)
            anterior = estado
            estado = afd.transicion(estado, clase)
            self.traza.append((i, anterior, caracter, clase, estado))

            if estado == afd.sumidero:
                i, inicio = self._error(anterior, inicio, i, clase)
                estado = afd.inicial
            elif estado == afd.inicial:
                i += 1
                inicio = i
            elif afd.es_final(estado):
                fin = i if estado in afd.retrocede else i + 1
                self._emitir(estado, inicio, fin)
                i = inicio = fin
                estado = afd.inicial
            else:
                i += 1
        self.tokens.append(self._token_fin())
        return self.tokens, self.errores

    def _emitir(self, estado, inicio, fin):
        lexema = self.texto[inicio:fin]
        categoria = self.afd.categoria_final[estado]
        if categoria == 'ID' and lexema in PALABRAS_RESERVADAS:
            categoria = 'PALABRA_RESERVADA'
        fila, columna = self._posiciones[inicio]
        self.tokens.append(Token(categoria, lexema, fila, columna))

    def _error(self, estado, inicio, i, clase):
        """Reporta el error y devuelve (i, inicio) desde donde se sigue leyendo."""
        afd, texto = self.afd, self.texto
        caracter = texto[i]
        leido = texto[inicio:i]
        visible = repr(caracter) if caracter != '\n' else 'un salto de línea'

        if leido.startswith('"'):
            mensaje = 'cadena sin cerrar: falta la comilla de cierre antes del fin de la línea'
            posicion = self._posiciones[inicio]
        elif estado == afd.inicial and clase == 'O':
            mensaje = f'el carácter {visible} no pertenece al alfabeto de IronScript'
            posicion = self._posiciones[i]
        elif estado == afd.inicial:
            mensaje = f'el carácter {visible} no puede iniciar ningún token'
            posicion = self._posiciones[i]
        else:
            mensaje = (f"después de '{leido}' no puede venir {visible}; "
                       f'se esperaba {afd.esperado(estado)}')
            posicion = self._posiciones[i]
        detalle = (f'δ(q{estado}, {clase}) = sumidero q{afd.sumidero} '
                   f'(q{estado}: {afd.nombre[estado]}, carácter {visible})')
        self.errores.append(ErrorLexico(posicion[0], posicion[1], mensaje, detalle))

        # Modo pánico: se descarta el token a medio leer. Si el carácter que
        # causó el error es un separador, se vuelve a leer desde q0; si no, se
        # descarta junto con lo que le sigue hasta el próximo separador.
        if estado != afd.inicial and clase in SEPARADORES:
            return i, i
        i += 1
        while i < len(texto) and clase_de(texto[i]) not in SEPARADORES:
            i += 1
        return i, i

    def _token_fin(self):
        """EOF se ubica justo después del último carácter que no es espacio."""
        j = len(self.original.rstrip())
        if j == 0:
            return Token(FIN_DE_ARCHIVO, '', 1, 1)
        fila, columna = self._posiciones[j - 1]
        return Token(FIN_DE_ARCHIVO, '', fila, columna + 1)


def analizar_lexico(texto):
    """Atajo: devuelve (tokens, errores) del texto."""
    return Lexer(texto).analizar()
