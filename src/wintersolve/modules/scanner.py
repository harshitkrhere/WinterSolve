"""Repository health scan: what is in this project and what is obviously missing.

The scan is deliberately cheap. It looks at file names, extensions, and a few
well-known marker files, and never opens source files. Deeper analysis is the
job of the other modules, which build on the ``ScanResult`` produced here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from wintersolve.logging_config import get_logger
from wintersolve.project import LANGUAGE_BY_EXTENSION, find_hygiene_files, walk_project

logger = get_logger("wintersolve.modules.scanner")

# Top-level file (or directory) → the stack it signals. Only the repository
# root is checked, which keeps monorepo sub-packages from being over-counted.
FRAMEWORK_MARKERS = {
    # JavaScript / TypeScript
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "bun.lock": "Bun",
    "bun.lockb": "Bun",
    "deno.json": "Deno",
    "deno.jsonc": "Deno",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "nuxt.config.ts": "Nuxt",
    "nuxt.config.js": "Nuxt",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "vite.config.mjs": "Vite",
    "astro.config.mjs": "Astro",
    "angular.json": "Angular",
    "svelte.config.js": "Svelte",
    "remix.config.js": "Remix",
    "tailwind.config.js": "Tailwind CSS",
    "tailwind.config.ts": "Tailwind CSS",
    # Python
    "pyproject.toml": "Python package",
    "setup.py": "Python package",
    "requirements.txt": "Python",
    "Pipfile": "Pipenv",
    "poetry.lock": "Poetry",
    "uv.lock": "uv",
    "manage.py": "Django",
    # Other languages
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "composer.json": "PHP Composer",
    "Gemfile": "Ruby",
    "mix.exs": "Elixir",
    "pubspec.yaml": "Dart / Flutter",
    "CMakeLists.txt": "CMake",
    "Makefile": "Make",
    # Infrastructure and tooling
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "compose.yaml": "Docker Compose",
    "compose.yml": "Docker Compose",
    "main.tf": "Terraform",
    "serverless.yml": "Serverless Framework",
    ".pre-commit-config.yaml": "pre-commit",
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
}

# Community files are matched by convention (README.rst, LICENSE.txt, Readme.md
# all count; see ``project.find_hygiene_files``); manifests by exact name.
HYGIENE_FILE_ORDER = [
    "README",
    "CONTRIBUTING",
    "LICENSE",
    "SECURITY",
    "CODE_OF_CONDUCT",
    "CHANGELOG",
]
IMPORTANT_MANIFESTS = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    ".env.example",
]

# Files whose absence is worth calling out for any project meant to be shared,
# as canonical name -> the filename we suggest creating.
RECOMMENDED_FILES = {
    "README": "README.md",
    "CONTRIBUTING": "CONTRIBUTING.md",
    "LICENSE": "LICENSE",
    "SECURITY": "SECURITY.md",
}

# Directory names that conventionally hold source code. Deeply nested packages
# are noise in an overview, so listing stops at ``src/<package>/<subpackage>``.
SOURCE_ROOT_NAMES = frozenset(
    {"src", "app", "lib", "packages", "services", "cmd", "internal", "pkg"}
)
MAX_SOURCE_PATH_DEPTH = 3

TESTABLE_EXTENSIONS = frozenset({".py", ".js", ".ts", ".tsx", ".go", ".rs", ".rb", ".java"})

# Reused by the Repo Brain recommendations so it can drop this line once
# commands have actually been detected.
RECOMMEND_DOCUMENT_COMMANDS = (
    "Document the main setup, test, and build commands for the detected stack."
)


@dataclass(frozen=True)
class ScanResult:
    path: Path
    exists: bool
    total_files: int
    total_directories: int
    languages: list[tuple[str, int]]
    frameworks: list[str]
    important_files: list[str]
    missing_recommended_files: list[str]
    likely_test_paths: list[str]
    likely_source_paths: list[str]
    risks: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = str(self.path)
        data["languages"] = [{"name": name, "files": count} for name, count in self.languages]
        return data


def scan_project(path: Path) -> ScanResult:
    """Scan a project directory and summarise its shape, stack, and hygiene."""
    logger.debug("Scanning project at %s", path)
    if not path.is_dir():
        logger.warning("Project path does not exist or is not a directory: %s", path)
        return _missing_project(path)

    tree = walk_project(path)
    relative_files = {file.relative_path for file in tree.files}
    relative_dirs = set(tree.directories)
    top_level_entries = relative_files | relative_dirs

    language_counts = Counter(
        LANGUAGE_BY_EXTENSION[file.path.suffix.lower()]
        for file in tree.files
        if file.path.suffix.lower() in LANGUAGE_BY_EXTENSION
    )
    frameworks = sorted(
        {stack for marker, stack in FRAMEWORK_MARKERS.items() if marker in top_level_entries}
    )
    hygiene = find_hygiene_files(name for name in relative_files if "/" not in name)
    important_files = [hygiene[key] for key in HYGIENE_FILE_ORDER if key in hygiene]
    important_files.extend(name for name in IMPORTANT_MANIFESTS if name in relative_files)
    missing_recommended_files = [
        suggested for key, suggested in RECOMMENDED_FILES.items() if key not in hygiene
    ]

    likely_test_paths = sorted(item for item in top_level_entries if _looks_like_test_path(item))
    likely_source_paths = sorted(item for item in relative_dirs if _looks_like_source_path(item))

    risks = _build_risks(
        total_files=len(tree.files),
        frameworks=frameworks,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths,
    )
    recommendations = _build_recommendations(
        frameworks=frameworks,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths,
    )

    logger.info(
        "Scan complete: %d files, %d directories, stack: %s",
        len(tree.files),
        len(tree.directories),
        ", ".join(frameworks) or "none",
    )
    return ScanResult(
        path=path,
        exists=True,
        total_files=len(tree.files),
        total_directories=len(tree.directories),
        languages=language_counts.most_common(),
        frameworks=frameworks,
        important_files=important_files,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths[:12],
        likely_source_paths=likely_source_paths[:12],
        risks=risks,
        recommendations=recommendations,
    )


def _missing_project(path: Path) -> ScanResult:
    return ScanResult(
        path=path,
        exists=False,
        total_files=0,
        total_directories=0,
        languages=[],
        frameworks=[],
        important_files=[],
        missing_recommended_files=list(RECOMMENDED_FILES.values()),
        likely_test_paths=[],
        likely_source_paths=[],
        risks=[f"Project path does not exist or is not a directory: {path}"],
        recommendations=["Run `wintersolve scan` with a valid project directory."],
    )


def _looks_like_test_path(relative_path: str) -> bool:
    normalized = relative_path.lower()
    name = Path(relative_path).name.lower()
    suffix = Path(relative_path).suffix.lower()
    return (
        normalized in {"test", "tests", "spec", "__tests__"}
        or normalized.startswith(("tests/", "test/", "spec/", "__tests__/"))
        or "/tests/" in normalized
        or "/__tests__/" in normalized
        or (name.startswith("test_") and suffix in TESTABLE_EXTENSIONS)
        or name.endswith(("_test.py", "_test.go", ".test.js", ".test.ts", ".test.tsx"))
        or name.endswith((".spec.js", ".spec.ts", ".spec.tsx", "_spec.rb"))
    )


def _looks_like_source_path(relative_dir: str) -> bool:
    parts = relative_dir.split("/")
    return parts[0] in SOURCE_ROOT_NAMES and len(parts) <= MAX_SOURCE_PATH_DEPTH


def _build_risks(
    total_files: int,
    frameworks: list[str],
    missing_recommended_files: list[str],
    likely_test_paths: list[str],
) -> list[str]:
    risks: list[str] = []
    if total_files == 0:
        risks.append("No files were found in the project directory.")
    if not frameworks:
        risks.append("No common project or framework markers were detected.")
    if "README.md" in missing_recommended_files:
        risks.append("No README was found, so onboarding may be difficult.")
    if "SECURITY.md" in missing_recommended_files:
        risks.append("No SECURITY.md was found for vulnerability reporting guidance.")
    if not likely_test_paths:
        risks.append("No obvious test files or test directories were detected.")
    return risks


def _build_recommendations(
    frameworks: list[str],
    missing_recommended_files: list[str],
    likely_test_paths: list[str],
) -> list[str]:
    recommendations = [
        f"Add {name} to improve project trust and maintainability."
        for name in missing_recommended_files
    ]
    if not likely_test_paths:
        recommendations.append("Add or document tests so contributors can verify changes.")
    if frameworks:
        recommendations.append(RECOMMEND_DOCUMENT_COMMANDS)
    else:
        recommendations.append(
            "Add clear setup metadata such as pyproject.toml, package.json, go.mod, or Cargo.toml."
        )
    return recommendations
