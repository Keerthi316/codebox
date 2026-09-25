"""Language registry: which sandbox image to use and how to build/run code.

To add a language: create executor/Dockerfiles/<name>/Dockerfile (see README)
and register a Language here.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class Language:
    key: str
    display_name: str
    image: str
    monaco_id: str
    # Returns (source filename, run command) for the given source code.
    layout: Callable[[str], "Layout"]
    # Syntax/compile step. With `separate_compile`, it runs in its own container
    # with compile limits and its outputs (`artifacts`) are shipped to the run
    # container; otherwise it runs in the run container before the program.
    compile_cmd: Optional[Callable[[str], List[str]]] = None
    separate_compile: bool = False
    artifacts: List[str] = field(default_factory=list)
    # Multiplier applied to EXECUTION_TIMEOUT (e.g. JVM start-up is slow).
    time_factor: float = 1.0


@dataclass(frozen=True)
class Layout:
    filename: str
    run_cmd: List[str]


_JAVA_CLASS = re.compile(r"public\s+(?:final\s+|abstract\s+)*class\s+([A-Za-z_$][\w$]*)")


def _java_layout(source: str) -> Layout:
    match = _JAVA_CLASS.search(source)
    name = match.group(1) if match else "Main"
    return Layout(
        f"{name}.java",
        ["java", "-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1", "-XX:-UsePerfData",
         "-Xshare:auto", "-XX:MaxRAMPercentage=70", "-Xss64m", "-cp", ".", name],
    )


LANGUAGES: Dict[str, Language] = {
    lang.key: lang
    for lang in [
        Language(
            key="python",
            display_name="Python 3.12",
            image="codebox-sandbox-python:latest",
            monaco_id="python",
            layout=lambda src: Layout("main.py", ["python3", "main.py"]),
            compile_cmd=lambda fn: ["python3", "-m", "py_compile", fn],
        ),
        Language(
            key="javascript",
            display_name="JavaScript (Node.js 22)",
            image="codebox-sandbox-javascript:latest",
            monaco_id="javascript",
            layout=lambda src: Layout("main.js", ["node", "main.js"]),
            compile_cmd=lambda fn: ["node", "--check", fn],
        ),
        Language(
            key="java",
            display_name="Java 21",
            image="codebox-sandbox-java:latest",
            monaco_id="java",
            layout=_java_layout,
            compile_cmd=lambda fn: ["javac", "-J-XX:+UseSerialGC", "-J-XX:TieredStopAtLevel=1",
                                    "-J-XX:-UsePerfData", "-encoding", "UTF-8", fn],
            separate_compile=True,
            artifacts=["*.class"],
            time_factor=2.0,
        ),
        Language(
            key="cpp",
            display_name="C++17 (GCC)",
            image="codebox-sandbox-cpp:latest",
            monaco_id="cpp",
            layout=lambda src: Layout("main.cpp", ["./main"]),
            compile_cmd=lambda fn: ["g++", "-std=c++17", "-O2", "-pipe", "-s", "-o", "main", fn],
            separate_compile=True,
            artifacts=["main"],
        ),
    ]
}


def get_language(key: str) -> Optional[Language]:
    return LANGUAGES.get((key or "").lower())
