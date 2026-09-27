"""Register the languages that ship with the platform.

Languages are data, so this command is idempotent and safe to re-run: it
updates the command templates and limits of existing rows and inserts the ones
that are missing.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.execution.models import Language

#: The five languages the platform supports out of the box.
DEFAULTS = [
    {
        "name": "Python",
        "slug": "python",
        "file_extension": ".py",
        "order": 10,
        "runner": "python",
        "execution_command": "{python} {file_name}",
        "monaco_language": "python",
        "time_limit": 5.0,
        "memory_limit_mb": 512,
        "enforce_address_space_limit": True,
        "docker_image": "python:3.12-slim",
        "notes": "Runs with python -I -B (isolated, no bytecode files).",
    },
    {
        "name": "C++",
        "slug": "cpp",
        "file_extension": ".cpp",
        "order": 20,
        "runner": "cpp",
        "compile_command": "g++ {file} -O2 -std=c++17 -o {out}",
        "execution_command": "{out}",
        "monaco_language": "cpp",
        "time_limit": 5.0,
        "memory_limit_mb": 512,
        "enforce_address_space_limit": True,
        "notes": "Compiled with g++ -O2 -std=c++17. Set DSA_CXX to use another compiler.",
    },
    {
        "name": "Java",
        "slug": "java",
        "file_extension": ".java",
        "order": 30,
        "runner": "java",
        "compile_command": "javac {file}",
        "execution_command": "java Main",
        "monaco_language": "java",
        "time_limit": 8.0,
        "memory_limit_mb": 1024,
        "enforce_address_space_limit": False,
        "run_env": {"JAVA_TOOL_OPTIONS": "-XX:+UseSerialGC"},
        "notes": "JVM start-up is ~100 ms, so the default limit is higher. Heap is capped with -Xmx.",
    },
    {
        "name": "JavaScript",
        "slug": "javascript",
        "file_extension": ".js",
        "order": 40,
        "runner": "javascript",
        "execution_command": "node {file_name}",
        "monaco_language": "javascript",
        "time_limit": 5.0,
        "memory_limit_mb": 512,
        "enforce_address_space_limit": False,
        "notes": "Runs on Node.js. console.log is redirected to stderr so it cannot corrupt the answer.",
    },
    {
        "name": "C",
        "slug": "c",
        "file_extension": ".c",
        "order": 50,
        "runner": "c",
        "compile_command": "gcc {file} -O2 -std=c11 -o {out}",
        "execution_command": "{out}",
        "monaco_language": "c",
        "time_limit": 5.0,
        "memory_limit_mb": 512,
        "enforce_address_space_limit": True,
        "notes": "Arrays are passed as pointers plus a length; set <fn>_len for array results.",
    },
]


class Command(BaseCommand):
    help = "Create or update the built-in language rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Only insert languages that do not exist yet.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0
        for payload in DEFAULTS:
            existing = Language.objects.filter(slug=payload["slug"]).first()
            if existing and options["only_missing"]:
                continue
            if existing:
                for key, value in payload.items():
                    if getattr(existing, key) != value:
                        setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                Language.objects.create(**payload)
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f"Languages ready: {created} created, {updated} updated.")
        )
