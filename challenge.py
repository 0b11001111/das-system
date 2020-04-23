# Standard library modules.
import os
import abc
import telegram
from collections import OrderedDict

# Third party modules.

# Local modules
from util import sandboxed_exec, tts

# Globals and constants variables.


class SubmissionError(Exception):
    pass


class ChallengeMeta(abc.ABCMeta):
    registry = OrderedDict()

    def __init__(cls, name, bases, namespace):
        if bases:
            cls.registry[namespace.get('_name') or name] = cls

        super().__init__(name, bases, namespace)


class Challenge(metaclass=ChallengeMeta):
    _name = None
    _requires = set()
    _help = 'Für diese Challenge wird keine Hilfe zur Verfügung gestellt ¯\\_(ツ)_/¯'

    def __init__(self, state):
        self.unlocked = all(r in state.solved for r in self.requires)
        self.solved = self.name in state.solved

    @classmethod
    def load(cls, state):
        return cls.registry[state.active](state)

    @classmethod
    def list(cls, state, unlocked=None, solved=None):
        challenges = (c(state) for c in cls.registry.values())

        if unlocked is not None:
            challenges = filter(lambda c: c.unlocked == unlocked, challenges)

        if solved is not None:
            challenges = filter(lambda c: c.solved == solved, challenges)

        return list(challenges)

    @property
    def name(self):
        return self._name or type(self).__name__

    @property
    def requires(self):
        return self._requires

    @property
    def help(self):
        return self._help

    @abc.abstractmethod
    def start(self, update, context):
        raise NotImplementedError

    @abc.abstractmethod
    def submit(self, update, context):
        raise NotImplementedError


def extract_and_exec(update, context, namespace=None):
    code = ''
    if update.message:
        if update.message.text:
            code = update.message.text

        elif update.message.document:
            code = update.message.document.get_file().download_as_bytearray().decode('utf-8')

    state = sandboxed_exec(code, 10, namespace)

    if state.get('__EXCEPTION__'):
        msg = state['__STDERR__']

        context.bot.send_message(
            text=f'Da ist was schief gegangen o.O\n\n```\n{msg}\n```',
            chat_id=update.effective_chat.id,
            parse_mode=telegram.ParseMode.MARKDOWN
        )

    return state


def strip(s):
    s = '\n'.join(map(str.strip, s.strip().splitlines()))
    return '\n\n'.join(' '.join(l for l in p.splitlines()) for p in s.split('\n\n'))


def strip_code(s):
    lines = list(filter(lambda l: len(l) != 0, s.splitlines()))
    prefix = os.path.commonprefix(lines)
    return '\n'.join(l[len(prefix):] for l in lines)


class HelloWorld(Challenge):
    def start(self, update, context):
        return strip("""
            Hey! Cool, dass du die deine erste Challenge angehen möchtest! Ich gehe davon
            aus, dass du _Python3_ bereits auf deinem Computer installiert hast!? Wenn nicht
            mach das bitte erst mal ;). Wenn du nur etwas herumstöbern willst, kann ich Dir
            auch diese Website empfehlen: https://repl.it/languages/python3
            
            Wenn das geklappt hat, schreibe ein Programm, dass "hello world" ausgibt und
            schicke mir das fertige Programm als Textnachricht oder Datei. Für die Ausgabe solltest
            du die Funktion `print` benutzen ;)
            
            Viel Spaß 🦦!
        """)

    def submit(self, update, context):
        state = extract_and_exec(update, context)

        if 'hello world' in str(state.get('__STDOUT__')).strip().lower():
            self.solved = True


class LongestString(Challenge):
    _requires = {'HelloWorld'}

    def start(self, update, context):
        return strip("""
        So, jetz wo du so grob weißt, wie das hier läuft, habe ich eine etwas schwerere Aufgabe
        für Dich!

        Schreibe eine Funktion `longest_string`, die eine Liste mit Strings als Eingabe bekommt und
        den längsten String zurück gibt. Gibt es mehrere längste Strings, gib den letzten zurück.

        Nutze den folgenden Codeschnipsel als Vorlage für dein Programm ;)
        """) + '\n\n' + strip_code("""
        ```
        from typing import List
        
        def longest_string(l: List[str]) -> str:
            raise NotImplementedError
        
        assert longest_string([]) == None
        assert longest_string(['a']) == 'a'
        assert longest_string(['a', 'b']) == 'b'
        assert longest_string(['a', 'bb', 'c']) == 'bb'
        ```
        """)

    def submit(self, update, context):
        longest_string = extract_and_exec(update, context).get('longest_string')

        if longest_string:
            try:
                assert longest_string([]) is None
                assert longest_string(['a']) == 'a'
                assert longest_string(['a', 'b']) == 'b'
                assert longest_string(['a', 'bb', 'c']) == 'bb'
                self.solved = True

            except AssertionError:
                pass


class FizzBuzz(Challenge):
    _requires = {'HelloWorld'}
    _help = 'Der Modulo-Operator (%) kann bei dieser Aufgabe sehr nützlich sein.'

    def start(self, update, context):
        return strip("""
        Schreibe eine Funktion `fizzbuzz`, die eine Zahl als Eingabe bekommt und "Fizz" zurück 
        gibt, wenn die Zahl durch 3 teilbar ist. Ist die Zahl durch 5 teilbar, gibt sie "Buzz" 
        zurück, bzw. "FizzBuzz", wenn beides zutrifft. In allen anderen Fällen, wird einfach die 
        Zahl selbst zurück gegeben.
        
        Nutze den folgenden Codeschnipsel als Vorlage für dein Programm ;)
        """) + '\n\n' + strip_code("""
        ```
        def fizzbuzz(x: int) -> str:
            raise NotImplementedError
        
        assert fizzbuzz(2) == '2'
        assert fizzbuzz(3) == 'Fizz'
        assert fizzbuzz(5) == 'Buzz'
        assert fizzbuzz(15) == 'FizzBuzz'
        ```
        """)

    def submit(self, update, context):
        fizzbuzz = extract_and_exec(update, context).get('fizzbuzz')

        if fizzbuzz:
            try:
                assert str(fizzbuzz(2)) == '2'
                assert str(fizzbuzz(3)) == 'Fizz'
                assert str(fizzbuzz(5)) == 'Buzz'
                assert str(fizzbuzz(6)) == 'Fizz'
                assert str(fizzbuzz(15)) == 'FizzBuzz'
                assert str(fizzbuzz(1515)) == 'FizzBuzz'
                self.solved = True

            except AssertionError:
                pass


class Palindrome(Challenge):
    _requires = {'LongestString', 'FizzBuzz'}
    _help = 'Groß- und Kleinschreibung soll ignoriert werden ("Ö" == "ö" usw.)'

    def start(self, update, context):
        return strip("""
        Ein Palindrom ist ein Wort, das vorwärts und rückwärts gelesen werden kann wie z.B. 
        "Otto" oder "Regallager". Schreibe eine Funktion, die `True` zurück gibt, wenn das gegebene 
        Wort ein Palindrom ist.

        Nutze den folgenden Codeschnipsel als Vorlage für dein Programm ;)
        """) + '\n\n' + strip_code("""
        ```
        def palindrome(s: str) -> bool:
            raise NotImplementedError
        ```
        """)

    def submit(self, update, context):
        palindrome = extract_and_exec(update, context).get('palindrome')

        if palindrome:
            try:
                assert palindrome('') == True
                assert palindrome('Abba') == True
                assert palindrome('a'*100 + 'b' + 'a'*100) == True
                assert palindrome('a'*100 + 'b' + 'a'*101) == False
                self.solved = True

            except AssertionError:
                pass


class CaesarI(Challenge):
    _requires = {'Palindrome'}

    def start(self, update, context):
        return strip("""
        Schon die alten Römer kannten das Prinzip der Verschlüsselung. Verglichen mit heutigen
        Methoden war sie allerdings nicht besonders sicher und kann mit heutigen Mitteln leicht
        geknackt werden. Heute ist diese Verschlüsselung unter dem Namen _Caesar-Verschlüsselung_
        bekannt.
        
        Bei der _Caesar-Verschlüsselung_ wird zum Verschlüsseln jeder Buchstabe eines Textes um _x_,
        zum Entschlüsseln um _-x_ Stellen verschoben. Z.B.: `caesar('a', 2) -> 'c'`,
        `caesar('z', 2) -> 'b'` oder `caesar(caesar('abc', 9999), -9999) -> 'abc'`.
        
        Der folgende Satz wurde mit dem Schlüssel *1337* verschlüsselt. Schicke mir den 
        entschlüsselten Text zurück!
        
        *"Qlmpc pde dflp bftdbfp qzcefylp."*
        
        _Tipps_
        
        Alles zeichen, die keine Buchstaben des Englischen Alphabets sind, werden bei der 
        Verschlüsselung ignoriert.
        
        Der ASCII-Standart legt die Kodierung von Zeichen als Zahlen fest. Der Zahlenbereich 65-90
        enthält die Groß-, der Bereich 97-122 die Kleinbuchstaben (siehe https://www.ascii-code.com).
        Mit der Python-Funktion `ord` kannst du ein Zeichen in den Entsprechenden ASCII-Code
        umwandeln und mit `chr` einen ASCII-Code zu dem entsprechenden Zeichen.
        
        Der Modulo-Operator `%` wird benutzt, um den Rest einer Division zu berechnen, z.B. 
        `5 % 3 ->2` oder `10 % 2 -> 0`.
        """)

    def submit(self, update, context):
        if update.message:
            if update.message.text:
                try:
                    assert str(update.message.text).strip() == 'Faber est suae quisque fortunae.'
                    self.solved = True

                except AssertionError:
                    pass


class CaesarII(Challenge):
    _requires = {'CaesarI'}
    _help = 'Mit moderner Rechenpower ist es kein Problem, den Schlüssel zu erraten.'

    def start(self, update, context):
        import inspect
        from solutions import caesar

        msg = 'Ach du Scheiße, ich habe Teile meines eigenen Quellcodes verschlüsselt. ' \
              'Kriegst du das geknackt?'

        with tts(msg) as buffer:
            context.bot.send_voice(chat_id=update.effective_chat.id, voice=buffer)

        return f'```\n{caesar(inspect.getsource(OutsideTheBox), 13)}\n```'

    def submit(self, update, context):
        if 'OutsideTheBox' in extract_and_exec(update, context, namespace={'Challenge': type}):
            self.solved = True


class Classes(Challenge):
    _requires = {'CaesarII'}

    def start(self, update, context):
        return strip("""
        Hast du schon mal von Klassen in Python gehört? Klassen sind ein Konzept um Daten und die
        zugehörige Logik zu koppeln. Gleichzeitig helfen sie, bestehenden Code wieder zu verwenden.

        Du siehst hier teile meiner Geometrielogik. Kannst du den Code bitte fertig schreiben?
        """) + '\n\n' + strip_code("""
        ```
        class Shape:
            def __init__(self, x: float, y: float):
                self.x = x
                self.y = y
        
            def __str__(self):
                return f'{type(self).__name__}(pos={(self.x, self.y)}, area={self.area()})'
        
            def area(self):
                # compute area of shape, has to be overwritten by subclasses
                raise NotImplementedError
        
        
        class Rectangle(Shape):
            def __init__(self, x: float, y: float, h: float, w: float):
                raise NotImplementedError
        
            def area(self):
                raise NotImplementedError
        
        
        class Square(Rectangle):
            def __init__(self, x: float, y: float, l: float):
                super().__init__(x, y, l, l)
        
        
        class Circle(Shape):
            def __init__(self, x: float, y: float, r: float):
                raise NotImplementedError
        
            def area(self):
                raise NotImplementedError
            
        
        print(Rectangle(0, 0, 1, 5))
        print(Square(5, 10, 4))
        print(Circle(-3, 2.5, 1.0))
        ```
        """)

    def submit(self, update, context):
        state = extract_and_exec(update, context)

        Rectangle = state.get('Rectangle')
        Square = state.get('Square')
        Circle = state.get('Circle')

        if Rectangle and Square and Circle:
            try:
                r = Rectangle(0, 0, 13, 37)
                s = Square(5, 13, 666)
                c = Circle(-3, 2.5, 4.2)

                assert r.area() == 481
                assert s.area() == 443556
                assert abs(c.area() - 55.4178) < .001
                self.solved = True

            except AssertionError:
                pass


class OutsideTheBox(Challenge):
    _requires = {'CaesarII', 'Classes'}
    _help = 'CaesarII'

    def start(self, update, context):
        # TODO write challenge description
        raise NotImplementedError

    def submit(self, update, context):
        from random import randint

        # extract source code and execute it
        state = extract_and_exec(update, context)

        # extract target function
        blackbox = state.get('blackbox')

        # test target function
        if blackbox is not None:
            try:
                n = randint(10, 1000)

                assert blackbox('') == True
                assert blackbox('abc') == True
                assert blackbox('a' * n + 'b' * n) == True
                assert blackbox('a' * n + 'b' * n + 'c' * (n+10)) == False
                assert blackbox('system') == False
                assert blackbox('fish') == True

                self.solved = True

            except AssertionError:
                pass
