import os
import sys
import inspect
import pathlib
import tempfile
import unittest
import contextlib
import unittest.mock
import importlib.util

from dffml.util.asynctestcase import AsyncTestCase

from dffml.util.testing.consoletest.commands import *
from dffml.util.testing.consoletest.parser import parse_nodes, Node


# Root of DFFML source tree
ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

# Load files by path. We have to import literalinclude_diff for diff-files
for module_name in ["literalinclude_diff"]:
    spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(ROOT_DIR, "docs", "_ext", f"{module_name}.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    setattr(sys.modules[__name__], module_name, module)


class TestFunctions(AsyncTestCase):
    def test_parse_commands_multi_line(self):
        self.assertListEqual(
            parse_commands(
                [
                    "$ python3 -m \\",
                    "    venv \\",
                    "    .venv",
                    "some shit",
                    "",
                    "",
                    "$ . \\",
                    "    .venv/bin/activate",
                    "more asdflkj",
                    "",
                ]
            ),
            [["python3", "-m", "venv", ".venv"], [".", ".venv/bin/activate"],],
        )

    def test_parse_commands_substitution(self):
        for cmd in [
            ["$ python3 $(cat feedface)"],
            ["$ python3 `cat feedface`"],
            ['$ python3 "`cat feedface`"'],
        ]:
            with self.subTest(cmd=cmd):
                with self.assertRaises(NotImplementedError):
                    parse_commands(cmd)

        cmd = ["$ python3 '`cat feedface`'"]
        with self.subTest(cmd=cmd):
            parse_commands(cmd)

    def test_parse_commands_single_line_with_output(self):
        self.assertListEqual(
            parse_commands(
                [
                    "$ docker logs maintained_db 2>&1 | grep 'ready for'",
                    "2020-01-13 21:31:09 0 [Note] mysqld: ready for connections.",
                    "2020-01-13 21:32:16 0 [Note] mysqld: ready for connections.",
                ]
            ),
            [
                [
                    "docker",
                    "logs",
                    "maintained_db",
                    "2>&1",
                    "|",
                    "grep",
                    "ready for",
                ],
            ],
        )

    def test_build_command_venv_linux(self):
        self.assertEqual(
            build_command([".", ".venv/bin/activate"],),
            ActivateVirtualEnvCommand(".venv"),
        )

    def test_pipes(self):
        self.assertListEqual(
            pipes(
                [
                    "python3",
                    "-c",
                    r"print('Hello\nWorld')",
                    "|",
                    "grep",
                    "Hello",
                ]
            ),
            [["python3", "-c", r"print('Hello\nWorld')"], ["grep", "Hello"]],
        )

    async def test_run_commands(self):
        with tempfile.TemporaryFile() as stdout:
            await run_commands(
                [
                    ["python3", "-c", r"print('Hello\nWorld')"],
                    ["grep", "Hello", "2>&1"],
                ],
                {"cwd": os.getcwd()},
                stdout=stdout,
            )
            stdout.seek(0)
            stdout = stdout.read().decode().strip()
            self.assertEqual(stdout, "Hello")


class TestPipInstallCommand(unittest.TestCase):
    def test_fix_dffml_packages(self):
        command = PipInstallCommand(
            [
                "python",
                "-m",
                "pip",
                "install",
                "--use-feature=2020-resolver",
                "-U",
                "dffml",
                "-e",
                "dffml-model-scikit",
                "shouldi",
                "aiohttp",
            ]
        )
        command.fix_dffml_packages({"root": ROOT_DIR})
        self.assertListEqual(
            command.cmd,
            [
                "python",
                "-m",
                "pip",
                "install",
                "--use-feature=2020-resolver",
                "-U",
                "-e",
                os.path.abspath(ROOT_DIR),
                "-e",
                os.path.abspath(os.path.join(ROOT_DIR, "model", "scikit")),
                "-e",
                os.path.abspath(os.path.join(ROOT_DIR, "examples", "shouldi")),
                "aiohttp",
            ],
        )


class TestDockerRunCommand(unittest.TestCase):
    def test_find_name(self):
        self.assertEqual(
            DockerRunCommand.find_name(
                ["docker", "run", "--rm", "-d", "--name", "maintained_db",]
            ),
            (
                "maintained_db",
                False,
                ["docker", "run", "--rm", "-d", "--name", "maintained_db",],
            ),
        )


class TestParser(unittest.TestCase):
    def test_parse_nodes(self):
        self.maxDiff = None
        self.assertListEqual(
            list(
                filter(
                    lambda node: node.directive
                    in {"code-block", "literalinclude"},
                    parse_nodes(
                        inspect.cleandoc(
                            r"""
                .. code-block:: console
                    :test:

                    $ echo -e 'Hello\n\n\nWorld'
                    Hello


                    World

                .. literalinclude:: some/file.py
                    :filepath: myfile.py
                    :test:

                .. note::

                    .. note::

                        .. code-block:: console
                            :test:
                            :daemon: 8080

                            $ echo -e 'Hello\n\n\n    World\n\n\nTest'
                            Hello


                                World


                            Test

                    .. code-block:: console

                        $ echo -e 'Hello\n\n\n    World\n\n\n\n'
                        Hello


                            World



                        $ echo 'feedface'
                        feedface

                    .. note::

                        .. code-block:: console
                            :test:

                            $ echo feedface
                            feedface

                .. code-block:: console
                    :test:

                    $ echo feedface
                    feedface
                """
                        )
                    ),
                )
            ),
            [
                Node(
                    directive="code-block",
                    content=[
                        r"$ echo -e 'Hello\n\n\nWorld'",
                        "Hello",
                        "",
                        "",
                        "World",
                    ],
                    options={"test": True},
                    node={},
                ),
                Node(
                    directive="literalinclude",
                    content="",
                    options={"filepath": "myfile.py", "test": True},
                    node={"source": "some/file.py"},
                ),
                Node(
                    directive="code-block",
                    content=[
                        r"$ echo -e 'Hello\n\n\n    World\n\n\nTest'",
                        "Hello",
                        "",
                        "",
                        "    World",
                        "",
                        "",
                        "Test",
                    ],
                    options={"test": True, "daemon": "8080"},
                    node={},
                ),
                Node(
                    directive="code-block",
                    content=[
                        r"$ echo -e 'Hello\n\n\n    World\n\n\n\n'",
                        "Hello",
                        "",
                        "",
                        "    World",
                        "",
                        "",
                        "",
                        "$ echo 'feedface'",
                        "feedface",
                    ],
                    options={},
                    node={},
                ),
                Node(
                    directive="code-block",
                    content=["$ echo feedface", "feedface",],
                    options={"test": True},
                    node={},
                ),
                Node(
                    directive="code-block",
                    content=["$ echo feedface", "feedface",],
                    options={"test": True},
                    node={},
                ),
            ],
        )


ROOT_PATH = pathlib.Path(__file__).parent.parent.parent
DOCS_PATH = ROOT_PATH / "docs"


class TestDocs(unittest.TestCase):
    """
    A testcase for each doc will be added to this class
    """

    TESTABLE_DOCS = []

    def test__all_docs_being_tested(self):
        """
        Make sure that there is a jobs.tutorials.strategy.matrix.docs entry for
        each testable doc.
        """
        # Ensure that we identified some docs to test
        should_have = sorted(self.TESTABLE_DOCS)
        self.assertTrue(should_have)
        # Load the ci testing workflow avoid requiring the yaml module as that
        # has C dependencies
        docs = list(
            sorted(
                map(
                    lambda i: str(
                        pathlib.Path(ROOT_PATH, i.strip()[2:])
                        .relative_to(DOCS_PATH)
                        .with_suffix("")
                    ),
                    filter(
                        lambda line: line.strip().startswith("- docs/"),
                        pathlib.Path(
                            ROOT_PATH, ".github", "workflows", "testing.yml"
                        )
                        .read_text()
                        .split("\n"),
                    ),
                )
            )
        )
        # Make sure that we have an entry for all the docs we can test
        self.assertListEqual(should_have, docs)


def mktestcase(filepath: pathlib.Path, relative: pathlib.Path):
    # The test case itself, assigned to test_doctest of each class
    def testcase(self):
        from sphinx.cmd.build import (
            get_parser,
            Tee,
            color_terminal,
            patch_docutils,
            docutils_namespace,
            Sphinx,
        )
        from sphinx.environment import BuildEnvironment

        os.chdir(ROOT_DIR)

        filenames = [str(relative)]

        class SubSetBuildEnvironment(BuildEnvironment):
            def get_outdated_files(self, updated):
                added, changed, removed = super().get_outdated_files(updated)
                added.clear()
                changed.clear()
                removed.clear()
                added.add("index")
                for filename in filenames:
                    added.add(filename)
                return added, changed, removed

        class SubSetSphinx(Sphinx):
            def _init_env(self, freshenv: bool) -> None:
                self.env = SubSetBuildEnvironment()
                self.env.setup(self)
                self.env.find_files(self.config, self.builder)

        confdir = os.path.join(ROOT_DIR, "docs")

        pickled_objs = {}

        def pickle_dump(obj, fileobj, _protocol):
            pickled_objs[fileobj.name] = obj

        def pickle_load(fileobj):
            return pickled_objs[fileobj.name]

        with patch_docutils(
            confdir
        ), docutils_namespace(), unittest.mock.patch(
            "pickle.dump", new=pickle_dump
        ), unittest.mock.patch(
            "pickle.load", new=pickle_load
        ), tempfile.TemporaryDirectory() as tempdir:
            app = SubSetSphinx(
                os.path.join(ROOT_DIR, "docs"),
                confdir,
                os.path.join(tempdir, "consoletest"),
                os.path.join(tempdir, "consoletest", ".doctrees"),
                "consoletest",
                {},
                sys.stdout,
                sys.stderr,
                True,
                False,
                [],
                0,
                1,
                False,
            )
            app.build(False, [])
        self.assertFalse(app.statuscode)

    return testcase


SKIP_DOCS = ["plugins/dffml_model"]


for filepath in DOCS_PATH.rglob("*.rst"):
    if b":test:" not in pathlib.Path(filepath).read_bytes():
        continue
    relative = filepath.relative_to(DOCS_PATH).with_suffix("")
    if str(relative) in SKIP_DOCS:
        continue
    TestDocs.TESTABLE_DOCS.append(str(relative))
    name = "test_" + str(relative).replace(os.sep, "_")
    # Do not add the tests if we are running with GitHub Actions for the main
    # package. This is because there are seperate jobs for each tutorial test
    # and the TestDocs.test__all_docs_being_tested ensures that we are running a
    # job for each tutorial
    if (
        "GITHUB_ACTIONS" in os.environ
        and "PLUGIN" in os.environ
        and os.environ["PLUGIN"] == "."
    ):
        continue
    setattr(
        TestDocs,
        name,
        unittest.skipIf(
            "RUN_CONSOLETESTS" not in os.environ,
            "RUN_CONSOLETESTS environment variable not set",
        )(mktestcase(filepath, relative)),
    )
