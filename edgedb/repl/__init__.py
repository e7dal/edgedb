##
# Copyright (c) 2016 MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import asyncio
import os
import sys

from prompt_toolkit import application as pt_app
from prompt_toolkit import buffer as pt_buffer
from prompt_toolkit import filters as pt_filters
from prompt_toolkit import history as pt_history
from prompt_toolkit import interface as pt_interface
from prompt_toolkit.key_binding import manager as pt_keymanager
from prompt_toolkit import shortcuts as pt_shortcuts
from prompt_toolkit import styles as pt_styles
from prompt_toolkit import token as pt_token

from edgedb import client
from edgedb.lang.common import lexer as core_lexer
from edgedb.lang.edgeql.parser.grammar import lexer as edgeql_lexer

from . import lex


class InputBuffer(pt_buffer.Buffer):

    def is_multiline_impl(self):
        text = self.document.text.strip()

        if text in Cli.exit_commands:
            return False

        if not text:
            return False

        if text.endswith(';'):
            lexer = edgeql_lexer.EdgeQLLexer()
            lexer.setinputstr(text)
            try:
                toks = list(lexer.lex())
            except core_lexer.UnknownTokenError as ex:
                return True

            if toks[-1].attrs['type'] == ';':
                return False

        return True

    def __init__(self, *args, **kwargs):
        is_multiline = pt_filters.Condition(self.is_multiline_impl)
        super().__init__(*args, is_multiline=is_multiline, **kwargs)


class Cli:

    style = pt_styles.style_from_dict({
        pt_token.Token.Prompt: '#aaa',
        pt_token.Token.PromptCont: '#888',

        # Syntax
        pt_token.Token.Keyword: '#e8364f',
        pt_token.Token.Operator: '#e8364f',
        pt_token.Token.String: '#d3c970',
        pt_token.Token.Number: '#9a79d7'
    })

    exit_commands = {'exit', 'quit', '\q', ':q'}

    def __init__(self):
        self.connection = None

        self.eventloop = pt_shortcuts.create_eventloop()
        self.aioloop = None
        self.cli = None

    def get_prompt_tokens(self, cli):
        return [
            (pt_token.Token.Prompt, '>>> '),
        ]

    def get_continuation_tokens(self, cli, width):
        return [
            (pt_token.Token.PromptCont, '...'),
        ]

    def build_cli(self):
        history = pt_history.FileHistory(
            os.path.expanduser('~/.edgedbhistory'))

        key_binding_manager = pt_keymanager.KeyBindingManager(
            enable_system_bindings=True,
            enable_search=True,
            enable_abort_and_exit_bindings=True)

        layout = pt_shortcuts.create_prompt_layout(
            lexer=lex.EdgeQLLexer(),
            reserve_space_for_menu=4,
            get_prompt_tokens=self.get_prompt_tokens,
            get_continuation_tokens=self.get_continuation_tokens,
            multiline=True
        )

        buf = InputBuffer(
            history=history,
            accept_action=pt_app.AcceptAction.RETURN_DOCUMENT)

        app = pt_app.Application(
            style=self.style,
            layout=layout,
            buffer=buf,
            ignore_case=True,
            key_bindings_registry=key_binding_manager.registry,
            on_exit=pt_app.AbortAction.RAISE_EXCEPTION,
            on_abort=pt_app.AbortAction.RETRY,
        )

        cli = pt_interface.CommandLineInterface(
            application=app,
            eventloop=self.eventloop)

        return cli

    def run_coroutine(self, coro):
        if self.aioloop is None:
            self.aioloop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.aioloop)

        try:
            return self.aioloop.run_until_complete(coro)
        except KeyboardInterrupt:
            self.aioloop.close()
            self.aioloop = None
            asyncio.set_event_loop(None)
            raise

    async def connect(self):
        try:
            return await client.connect()
        except:
            return None

    def ensure_connection(self):
        if self.connection is None:
            self.connection = self.run_coroutine(self.connect())

        if self.connection is not None and \
                self.connection._transport.is_closing():
            self.connection = self.run_coroutine(self.connect())

        if self.connection is None:
            print('Could not establish connection', file=sys.stderr)
            exit(1)

    def run(self):
        self.cli = self.build_cli()
        self.ensure_connection()

        try:
            while True:
                document = self.cli.run(True)
                command = document.text.strip()

                if not command:
                    continue

                if command in self.exit_commands:
                    raise EOFError

                self.ensure_connection()
                try:
                    result = self.run_coroutine(
                        self.connection.execute(command))
                except KeyboardInterrupt:
                    continue
                except Exception as ex:
                    print('{}: {}'.format(type(ex).__name__, ex.args[0]))
                    continue

                print(result)

        except EOFError:
            return


def main():
    Cli().run()