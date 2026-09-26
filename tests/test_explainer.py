from __future__ import annotations

from pathlib import Path

import pytest

from wintersolve.modules.explainer import explain_file, npm_package_name
from wintersolve.project import MAX_TEXT_FILE_BYTES

from .conftest import write


class TestPythonFiles:
    def test_detects_symbols_imports_and_docstring(self, tmp_path: Path) -> None:
        target = write(
            tmp_path / "demo.py",
            '"""Demo module.\n\nMore detail.\n"""\n\nimport os\nfrom pathlib import Path\n\n\n'
            "class Demo:\n    def run(self):\n        pass\n\n    def stop(self):\n        pass\n"
            "\n\ndef helper():\n    pass\n\n\n"
            'if __name__ == "__main__":\n    helper()\n',
        )

        result = explain_file(target)

        assert result.language == "Python"
        assert result.symbols == [
            "class Demo (2 methods)",
            "function helper",
            "runnable as a script (__main__ guard)",
        ]
        assert result.imports == ["os", "pathlib"]
        assert "Its docstring says: Demo module." in result.summary
        assert result.errors == []

    def test_imports_are_sorted_into_standard_library_third_party_and_local(
        self, tmp_path: Path
    ) -> None:
        write(tmp_path / "pkg" / "__init__.py")
        target = write(
            tmp_path / "pkg" / "core.py",
            "import os\nimport click\nfrom rich.table import Table\n"
            "from . import helpers\nfrom .ctx import Context\nfrom pkg.models import Model\n",
        )

        result = explain_file(target)

        assert result.imports == [".ctx", ".helpers", "click", "os", "pkg.models", "rich.table"]
        assert (
            "It imports 6 modules: 1 from the standard library, "
            "2 from third-party packages (click, rich), 3 from this project."
        ) in result.summary

    def test_syntax_errors_are_surfaced_not_swallowed(self, tmp_path: Path) -> None:
        target = write(tmp_path / "broken.py", "def broken(:\n    pass\n")

        result = explain_file(target)

        assert result.errors and result.errors[0].startswith("Python syntax error near line 1")
        assert "The file does not parse; fix the reported syntax error first." in result.risks


class TestJavaScriptAndTypeScript:
    def test_symbols_imports_and_exports(self, tmp_path: Path) -> None:
        source = "\n".join(
            [
                "/**",
                " * Routes for the admin dashboard.",
                " * @module admin",
                " * @example const x = require('not-a-dependency')",
                " */",
                "import React from 'react'",
                "import {",
                "  useState,",
                "  useEffect,",
                "} from 'react'",
                "import './styles.css'",
                "const path = require('node:path')",
                "const helpers = require('./helpers')",
                "",
                "export function main() {}",
                "export default class App {}",
                "const handler = async (req, res) => {}",
                "export const VERSION = '1.0'",
                "function internal() {",
                "  function nested() {}",
                "}",
            ]
        )
        target = write(tmp_path / "app.js", source + "\n")

        result = explain_file(target)

        assert result.language == "JavaScript"
        assert result.symbols == [
            "export function main",
            "export class App",
            "function handler",
            "export constant VERSION",
            "function internal",
        ]
        assert result.imports == ["./helpers", "./styles.css", "node:path", "react"]
        assert "Its header comment says: Routes for the admin dashboard." in result.summary
        assert (
            "It imports 4 modules: 1 from the standard library, "
            "1 from third-party packages (react), 2 from this project."
        ) in result.summary

    def test_typescript_types(self, tmp_path: Path) -> None:
        source = (
            "export interface User { id: string }\n"
            "export type Id = string\n"
            "enum Color { Red }\n"
            "export const load = (id: Id): Promise<User> => fetch(id)\n"
        )

        result = explain_file(write(tmp_path / "user.ts", source))

        assert result.symbols == [
            "export interface User",
            "export type Id",
            "enum Color",
            "export function load",
        ]

    @pytest.mark.parametrize(
        ("specifier", "package"),
        [("lodash", "lodash"), ("lodash/fp", "lodash"), ("@scope/pkg/deep", "@scope/pkg")],
    )
    def test_npm_package_name(self, specifier: str, package: str) -> None:
        assert npm_package_name(specifier) == package


class TestGo:
    def test_types_group_their_methods(self, tmp_path: Path) -> None:
        source = "\n".join(
            [
                "// Copyright 2024 The Authors. Licensed under Apache 2.0.",
                "",
                "// Package demo runs small, well-behaved commands for you.",
                "package demo",
                "",
                "import (",
                '\t"fmt"',
                '\tflag "github.com/spf13/pflag"',
                ")",
                'import "os"',
                "",
                "type Command struct{}",
                "type Runner interface{}",
                "func (c *Command) Run() error { return nil }",
                "func (c *Command) Name() string { return fmt.Sprint(os.Args) }",
                "func (l List[T]) Len() int { return 0 }",
                "func New() *Command { return &Command{} }",
            ]
        )

        result = explain_file(write(tmp_path / "demo.go", source))

        assert result.symbols == [
            "struct Command (2 methods)",
            "interface Runner",
            "func New",
            "methods on List (1)",
        ]
        assert result.imports == ["fmt", "github.com/spf13/pflag", "os"]
        assert (
            "Its header comment says: Package demo runs small, well-behaved commands for you."
            in result.summary
        )
        assert (
            "It imports 3 modules: 2 from the standard library, "
            "1 from third-party packages (github.com/spf13/pflag)."
        ) in result.summary


class TestOtherLanguages:
    def test_swift_imports_and_top_level_definitions(self, tmp_path: Path) -> None:
        source = (
            "// import NotARealModule\n"
            "import Foundation\n"
            "@testable import AppCore\n"
            "public struct User {\n"
            "    func nested() {}\n"
            "}\n"
            "final class Store {}\n"
            "enum State {}\n"
            "protocol Persistable {}\n"
            "extension User {}\n"
            "func load<T>() {}\n"
        )

        result = explain_file(write(tmp_path / "User.swift", source))

        assert result.language == "Swift"
        assert result.imports == ["AppCore", "Foundation"]
        assert result.symbols == [
            "struct User",
            "class Store",
            "enum State",
            "protocol Persistable",
            "extension User",
            "func load",
        ]

    def test_rust(self, tmp_path: Path) -> None:
        source = (
            "//! Parses configuration files for the server.\n"
            "use std::{\n    fs,\n    io,\n};\n"
            "use serde::Deserialize;\n"
            "use crate::errors::Error;\n"
            "pub struct Config {}\n"
            "impl Config {\n    pub fn load() {}\n}\n"
            "pub(crate) async fn run() {}\n"
            "enum Mode { A }\n"
        )

        result = explain_file(write(tmp_path / "config.rs", source))

        assert result.symbols == ["struct Config", "impl Config", "fn run", "enum Mode"]
        assert result.imports == ["crate::errors::Error", "serde::Deserialize", "std::{fs, io}"]
        assert "Its header comment says: Parses configuration files for the server." in (
            result.summary
        )

    def test_java(self, tmp_path: Path) -> None:
        source = (
            "import java.util.List;\n"
            "import static org.junit.Assert.assertEquals;\n\n"
            "public final class Service {\n"
            "    public static void main(String[] args) {}\n"
            "    protected List<String> names() { return null; }\n"
            "    private void hidden() {}\n"
            "    public Service() {}\n"
            "}\n"
        )

        result = explain_file(write(tmp_path / "Service.java", source))

        assert result.symbols == ["class Service", "method main", "method names"]
        assert result.imports == ["java.util.List", "org.junit.Assert.assertEquals"]

    def test_kotlin_and_csharp(self, tmp_path: Path) -> None:
        kotlin = "import kotlinx.coroutines.launch\ndata class User(val id: Int)\nfun main() {}\n"
        csharp = (
            "using System.Text;\n"
            "namespace Demo.Api;\n"
            "public sealed class Handler\n{\n"
            "    public async Task<int> RunAsync(string input) { return 0; }\n}\n"
        )

        kotlin_result = explain_file(write(tmp_path / "Main.kt", kotlin))
        csharp_result = explain_file(write(tmp_path / "Handler.cs", csharp))

        assert kotlin_result.symbols == ["class User", "fun main"]
        assert kotlin_result.imports == ["kotlinx.coroutines.launch"]
        assert csharp_result.symbols == ["namespace Demo.Api", "class Handler", "method RunAsync"]
        assert csharp_result.imports == ["System.Text"]

    def test_c_and_cpp(self, tmp_path: Path) -> None:
        source = (
            "#include <stdio.h>\n"
            '#include "util.h"\n'
            "struct point;\n"
            "struct buffer {\n"
            "  int size;\n"
            "};\n"
            "static int parse(const char *text) {\n"
            "  return 0;\n"
            "}\n"
            "int main(int argc, char **argv)\n"
            "{\n"
            "  return parse(argv[0]);\n"
            "}\n"
        )

        result = explain_file(write(tmp_path / "main.c", source))

        assert result.symbols == ["struct buffer", "function parse", "function main"]
        assert result.imports == ["stdio.h", "util.h"]

    def test_ruby_php_and_shell(self, tmp_path: Path) -> None:
        ruby = (
            "require 'json'\nrequire_relative 'helpers'\nmodule Api\n  class Client\n  end\nend\n"
        )
        php = (
            "<?php\nnamespace App\\Http;\nuse Illuminate\\Support\\Str;\n"
            "final class Controller {\n    public function index() {}\n}\n"
        )
        shell = "#!/usr/bin/env bash\nsource ./env.sh\nbuild() {\n  make\n}\nfunction deploy {\n}\n"

        assert explain_file(write(tmp_path / "client.rb", ruby)).symbols == [
            "module Api",
            "class Client",
        ]
        assert explain_file(write(tmp_path / "client.rb", ruby)).imports == ["helpers", "json"]
        assert explain_file(write(tmp_path / "Controller.php", php)).symbols == [
            "namespace App\\Http",
            "class Controller",
            "function index",
        ]
        assert explain_file(write(tmp_path / "deploy.sh", shell)).symbols == [
            "function build",
            "function deploy",
        ]

    def test_languages_without_patterns_say_so(self, tmp_path: Path) -> None:
        result = explain_file(write(tmp_path / "App.dart", "import 'dart:core';\nclass App {}\n"))

        assert result.symbols == []
        assert "Definitions and imports are not detected for Dart files yet." in result.summary
        assert result.risks == ["No obvious file-level risks were detected."]


class TestDocumentsAndData:
    def test_markdown_outline(self, tmp_path: Path) -> None:
        markdown = "# Title\n\n## Install\n\n```bash\n# not a heading\n```\n\n#### Too deep\n"

        result = explain_file(write(tmp_path / "GUIDE.md", markdown))

        assert result.symbols == ["# Title", "## Install"]
        assert "It has 2 sections." in result.summary

    def test_json_keys_and_parse_errors(self, tmp_path: Path) -> None:
        valid = explain_file(write(tmp_path / "package.json", '{"name": "x", "scripts": {}}'))
        broken = explain_file(write(tmp_path / "broken.json", '{"name": }'))

        assert valid.symbols == ["key name", "key scripts"]
        assert broken.errors[0].startswith("JSON does not parse")
        assert "The file does not parse; fix the reported syntax error first." in broken.risks

    def test_json_with_comments_is_not_an_error(self, tmp_path: Path) -> None:
        tsconfig = '{\n  // strict mode\n  "compilerOptions": {\n    "strict": true\n  }\n}\n'

        result = explain_file(write(tmp_path / "tsconfig.json", tsconfig))

        assert result.errors == []
        assert result.symbols == ["key compilerOptions"]

    def test_toml_and_yaml(self, tmp_path: Path) -> None:
        toml = 'title = "x"\n[project]\nname = "demo"\n[[tool.mypy.overrides]]\nmodule = "a"\n'
        yaml = "name: CI\non:\n  push:\njobs:\n  test:\n    steps:\n      - run: pytest\n"

        assert explain_file(write(tmp_path / "pyproject.toml", toml)).symbols == [
            "key title",
            "[project]",
            "[[tool.mypy.overrides]]",
        ]
        assert explain_file(write(tmp_path / "ci.yml", yaml)).symbols == [
            "key name",
            "key on",
            "key jobs",
        ]

    def test_data_formats_get_a_label(self, tmp_path: Path) -> None:
        assert explain_file(write(tmp_path / "config.toml", "a = 1\n")).language == "TOML"
        assert explain_file(write(tmp_path / "notes.txt", "hello\n")).language == "Text"


class TestLimitsAndRisks:
    def test_long_symbol_lists_are_capped_and_say_so(self, tmp_path: Path) -> None:
        source = "".join(f"export function f{index}() {{}}\n" for index in range(25))

        result = explain_file(write(tmp_path / "many.js", source))

        assert len(result.symbols) == 20
        assert "It has 25 definitions; the first 20 are listed." in result.summary

    def test_unknown_extensions_are_not_analyzed(self, tmp_path: Path) -> None:
        result = explain_file(write(tmp_path / "notes", "hello\n"))

        assert result.language == "Binary or large file"
        assert result.risks == ["File is too large or not recognized as text."]

    def test_large_file_is_skipped(self, tmp_path: Path) -> None:
        target = write(tmp_path / "bundle.js", "x" * (MAX_TEXT_FILE_BYTES + 1))

        result = explain_file(target)

        assert result.language == "Binary or large file"
        assert result.line_count == 0

    def test_missing_file(self, tmp_path: Path) -> None:
        result = explain_file(tmp_path / "nope.py")

        assert not result.exists
        assert result.risks == [f"File does not exist: {tmp_path / 'nope.py'}"]

    def test_long_file_without_structure_is_a_risk(self, tmp_path: Path) -> None:
        target = write(tmp_path / "script.js", "doSomething();\n" * 200)

        assert (
            "Long file with no obvious definitions or sections detected."
            in explain_file(target).risks
        )
