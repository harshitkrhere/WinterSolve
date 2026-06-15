from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from wintersolve.project import IGNORED_DIRECTORIES, is_ignored


LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".md": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

FRAMEWORK_MARKERS = {
    "package.json": "Node.js",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "angular.json": "Angular",
    "svelte.config.js": "Svelte",
    "pyproject.toml": "Python package",
    "requirements.txt": "Python",
    "manage.py": "Django",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "composer.json": "PHP Composer",
    "Gemfile": "Ruby",
    "Dockerfile": "Docker",
}

IMPORTANT_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    ".env.example",
]


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


def scan_project(path: Path) -> ScanResult:
    if not path.exists() or not path.is_dir():
        return ScanResult(
            path=path,
            exists=False,
            total_files=0,
            total_directories=0,
            languages=[],
            frameworks=[],
            important_files=[],
            missing_recommended_files=[],
            likely_test_paths=[],
            likely_source_paths=[],
            risks=[f"Project path does not exist or is not a directory: {path}"],
            recommendations=["Run `wintersolve scan` with a valid project directory."],
        )

    files: list[Path] = []
    directories: list[Path] = []
    for item in path.rglob("*"):
        if is_ignored(item, path):
            continue
        if item.is_dir():
            directories.append(item)
        elif item.is_file():
            files.append(item)

    relative_files = {_to_posix(file.relative_to(path)) for file in files}
    relative_dirs = {_to_posix(directory.relative_to(path)) for directory in directories}

    language_counts = Counter(
        LANGUAGE_BY_EXTENSION[file.suffix.lower()]
        for file in files
        if file.suffix.lower() in LANGUAGE_BY_EXTENSION
    )

    frameworks = sorted(
        {
            framework
            for marker, framework in FRAMEWORK_MARKERS.items()
            if marker in relative_files
        }
    )

    important_files = [file for file in IMPORTANT_FILES if file in relative_files]
    missing_recommended_files = [
        file
        for file in ["README.md", "CONTRIBUTING.md", "LICENSE", "SECURITY.md"]
        if file not in relative_files
    ]

    likely_test_paths = sorted(
        item
        for item in relative_dirs | relative_files
        if _looks_like_test_path(item)
    )[:12]
    likely_source_paths = sorted(
        item
        for item in relative_dirs
        if item in {"src", "app", "lib", "packages", "services", "cmd", "internal"}
        or item.startswith(("src/", "app/", "lib/"))
    )[:12]

    risks = _build_risks(
        total_files=len(files),
        frameworks=frameworks,
        important_files=important_files,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths,
    )
    recommendations = _build_recommendations(
        frameworks=frameworks,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths,
    )

    return ScanResult(
        path=path,
        exists=True,
        total_files=len(files),
        total_directories=len(directories),
        languages=language_counts.most_common(),
        frameworks=frameworks,
        important_files=important_files,
        missing_recommended_files=missing_recommended_files,
        likely_test_paths=likely_test_paths,
        likely_source_paths=likely_source_paths,
        risks=risks,
        recommendations=recommendations,
    )


def _looks_like_test_path(path: str) -> bool:
    normalized = path.lower()
    name = Path(path).name.lower()
    return (
        normalized == "tests"
        or normalized.startswith("tests/")
        or "/tests/" in normalized
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
    )


def _build_risks(
    total_files: int,
    frameworks: list[str],
    important_files: list[str],
    missing_recommended_files: list[str],
    likely_test_paths: list[str],
) -> list[str]:
    risks: list[str] = []

    if total_files == 0:
        risks.append("No files were found in the project directory.")
    if not frameworks:
        risks.append("No common project or framework markers were detected.")
    if "README.md" not in important_files:
        risks.append("No README.md was found, so onboarding may be difficult.")
    if "SECURITY.md" in missing_recommended_files:
        risks.append("No SECURITY.md was found for vulnerability reporting guidance.")
    if not likely_test_paths:
        risks.append("No obvious test files or test directories were detected.")

    return risks or ["No major repository health risks were detected by the basic scan."]


def _build_recommendations(
    frameworks: list[str],
    missing_recommended_files: list[str],
    likely_test_paths: list[str],
) -> list[str]:
    recommendations: list[str] = []

    for file in missing_recommended_files:
        recommendations.append(f"Add {file} to improve project trust and maintainability.")
    if not likely_test_paths:
        recommendations.append("Add or document tests so contributors can verify changes.")
    if not frameworks:
        recommendations.append("Add clear setup metadata such as pyproject.toml, package.json, go.mod, or Cargo.toml.")
    if frameworks:
        recommendations.append("Document the main setup, test, and build commands for the detected stack.")

    return recommendations or ["Keep documentation, tests, and project metadata current as the project grows."]


def _to_posix(path: Path) -> str:
    return path.as_posix()
