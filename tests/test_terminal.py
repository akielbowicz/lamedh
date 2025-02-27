from copy import deepcopy
from io import StringIO
import tempfile
from unittest.mock import patch, MagicMock
import unittest

from lamedh.terminal import Terminal, HELP


class BaseTestTerminal(unittest.TestCase):
    def setUp(self):
        self.terminal = Terminal()
        self.terminal.memory['FORMAT'] = 'normal'

    @patch('sys.stdout', new_callable = StringIO)
    def call_main(self, inputs, stdout):
        if 'exit' not in inputs:
            # prevent never ending loop
            inputs = inputs + ['exit']  # avoiding modify received inputs
        with patch('builtins.input', side_effect=inputs):
            self.terminal.main()
        return stdout

    def last_OUT(self, stdout):
        if self.terminal.OUT not in stdout.getvalue():
            print('>>>', stdout.getvalue(), '<<<')
            return None
        return stdout.getvalue().split(self.terminal.OUT)[-1]

    def last_line(self, stdout, omit_bye=True):
        lines = list(filter(bool, stdout.getvalue().split('\n')))
        last = lines.pop()
        if omit_bye and last.strip() == 'Bye!':
            last = lines.pop()
        return last


class TestTerminalParsing(BaseTestTerminal):
    def test_parse_expression_simplest(self):
        inputs = ['A']
        stdout = self.call_main(inputs)
        last = self.last_line(stdout)
        self.assertIn('A', last)
        self.assertIn('new expression parsed:', last)

    def test_parse_expression_uses_from_string(self):
        expr = 'A'
        inputs = [expr]
        with patch('lamedh.expr.Expr.from_string') as mock:
            stdout = self.call_main(inputs)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0][0], expr)


class TestTerminalHelp(BaseTestTerminal):

    def test_help(self):
        inputs = ['?']
        stdout = self.call_main(inputs)
        self.assertIn(HELP, stdout.getvalue())


class TestTerminalMemory(BaseTestTerminal):

    def test_define_new_expr_in_memory(self):
        name = 'some_fancy_name'
        expr = 'λx.x'
        inputs = ['%s = %s' % (name, expr)]
        stdout = self.call_main(inputs)
        self.assertIn(name, self.terminal.memory)

    def test_define_new_expr_with_empty_name_fails(self):
        expr = 'λx.x'
        inputs = [' = %s' % (expr)]
        memory_before = deepcopy(self.terminal.memory)
        stdout = self.call_main(inputs)
        self.assertEqual(memory_before, self.terminal.memory)
        last = self.last_line(stdout)
        self.assertIn('Error', last)  # wont be very meticulous in detailed error message

    def test_several_equal_sings_fails(self):
        name = 'some_fancy_name'
        expr = 'λx.x'
        inputs = ['%s = %s =' % (name, expr)]
        memory_before = deepcopy(self.terminal.memory)
        stdout = self.call_main(inputs)
        self.assertEqual(memory_before, self.terminal.memory)
        self.assertNotIn(name, self.terminal.memory)
        self.assertIn('Error', stdout.getvalue())  # wont be very meticulous in detailed error message

    def test_parsing_expressions_with_no_definition_is_stored_as_default_name(self):
        expr = '(λx.x)'
        inputs = [expr]
        stdout = self.call_main(inputs)
        last = self.last_line(stdout)
        self.assertIn('new expression parsed:', last)
        default_name = self.terminal.DEFAULT_NAME
        self.assertIn(default_name, self.terminal.memory)
        self.assertEqual(str(self.terminal.memory[default_name]), expr)

    def test_dump_memory(self):
        name = 'some_fancy_name'
        expr = '(λx.x)'
        self.call_main(['%s = %s' % (name, expr)])
        # two main calls, to make sure the output is only from the dump
        stdout = self.call_main(['dump'])
        output = stdout.getvalue()
        self.assertIn('Dumping expressions saved in memory:', output)
        self.assertIn(name, output)
        self.assertIn(expr, output)

    def test_load_memory(self):
        name = 'some_fancy_name'
        expr = '(λx.x)'
        with tempfile.TemporaryDirectory() as temp_dir:
            fname = temp_dir + '/prelude'
            with open(fname, 'w') as f:
                f.write('%s = %s' % (name, expr))
            inputs = ['load %s' % fname]
            stdout = self.call_main(inputs)
        output = stdout.getvalue()
        self.assertIn('new expression parsed:', output)
        self.assertIn(name, self.terminal.memory)
        self.assertEqual(str(self.terminal.memory[name]), expr)

    def test_load_memory_unexistent_file_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fname = temp_dir + '/prelude'  # temp_dir just created. File doesn't exist
            inputs = ['load %s' % fname]
            stdout = self.call_main(inputs)
        output = stdout.getvalue()
        self.assertIn('Error:', output)
        self.assertNotIn('new expression parsed:', output)


class TestReservedNames(BaseTestTerminal):

    def test_reserved_names(self):
        # remember that any string xyz will be parsed as Var('xyz')
        for name in self.terminal.RESERVED_NAMES:
            inputs = ['%s = λx.x' % name]
            memory_before = deepcopy(self.terminal.memory)
            stdout = self.call_main(inputs)
            output = stdout.getvalue()
            self.assertIn('Error:', output)
            self.assertIn('reserved', output)


if __name__ == '__main__':
    unittest.main()