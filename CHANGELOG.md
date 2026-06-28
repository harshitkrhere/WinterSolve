# Changelog

All notable changes to WinterSolve are documented in this file.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/) and uses semantic versioning once public releases begin.

## [Unreleased]

### Added

- Modern Typer/Rich CLI entry point with `python -m wintersolve` support.
- CI quality gates for Ruff, format checks, Mypy, tests, package builds, and Bandit scanning.
- PyPI-oriented release workflow for tagged releases.
- Optional AI provider extension examples for OpenAI and Anthropic.
- Project logging configuration that stays quiet by default.

### Changed

- Packaging metadata now uses modern SPDX license syntax.
- Test suite is pytest-compatible and runs under strict pytest configuration.

### Security

- Security scanner keeps reports redacted by default.
- Release and CI workflows include package validation.

## [0.2.0] - 2026-06-28

### Added

- Open-source readiness pass for packaging, CI, CLI reliability, provider extension points, and release automation.

## [0.1.0]

### Added

- Initial offline-first Repo Brain, scan, explain, debug, docs, review, and security workflows.
