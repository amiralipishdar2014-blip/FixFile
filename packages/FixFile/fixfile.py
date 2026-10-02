#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

VERSION = "1.0.0"
BACKUP_SUFFIX = ".fixfile.backup"

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sh": "bash",
    ".bash": "bash",
    ".php": "php",
    ".rb": "ruby",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
}


def run_command(command, timeout=20):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = "\n".join(
            x for x in [result.stdout, result.stderr] if x
        ).strip()

        return result.returncode, output

    except FileNotFoundError:
        return None, "COMMAND_NOT_FOUND"

    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def detect_language(filename):
    extension = os.path.splitext(filename)[1].lower()
    return EXTENSIONS.get(extension)


def check_file(filename, language):
    if language == "python":
        return run_command([sys.executable, filename])

    if language == "javascript":
        if not shutil.which("node"):
            return None, "Node.js نصب نیست."
        return run_command(["node", "--check", filename])

    if language == "typescript":
        if not shutil.which("tsc"):
            return None, "TypeScript compiler (tsc) نصب نیست."
        return run_command(["tsc", "--noEmit", filename])

    if language == "bash":
        return run_command(["bash", "-n", filename])

    if language == "php":
        if not shutil.which("php"):
            return None, "PHP نصب نیست."
        return run_command(["php", "-l", filename])

    if language == "ruby":
        if not shutil.which("ruby"):
            return None, "Ruby نصب نیست."
        return run_command(["ruby", "-c", filename])

    if language == "java":
        if not shutil.which("javac"):
            return None, "Java/Javac نصب نیست."
        return run_command(["javac", filename])

    if language == "c":
        if not shutil.which("clang"):
            return None, "Clang نصب نیست."
        return run_command(["clang", "-fsyntax-only", filename])

    if language == "cpp":
        if not shutil.which("clang++"):
            return None, "Clang++ نصب نیست."
        return run_command(["clang++", "-fsyntax-only", filename])

    if language == "go":
        if not shutil.which("go"):
            return None, "Go نصب نیست."
        return run_command(["go", "fmt", "-d", filename])

    if language == "rust":
        if not shutil.which("rustc"):
            return None, "Rustc نصب نیست."
        return run_command(
            ["rustc", "--emit", "metadata", filename]
        )

    if language == "json":
        try:
            with open(filename, "r", encoding="utf-8") as file:
                json.load(file)

            return 0, "JSON معتبر است."

        except Exception as error:
            return 1, str(error)

    if language == "html":
        return 0, "HTML بررسی پایه شد."

    if language == "css":
        return 0, "CSS بررسی پایه شد."

    return None, "این زبان پشتیبانی نمی‌شود."


def read_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def clean_ai_response(code):
    code = code.strip()

    if code.startswith("```"):
        lines = code.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines).strip()

    return code + "\n"


def ask_openrouter(code, error):
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        print()
        print("❌ OPENROUTER_API_KEY تنظیم نشده است.")
        print()
        print("ابتدا کلید API خود را در متغیر محیطی قرار دهید.")
        print('مثال: export OPENROUTER_API_KEY="YOUR_API_KEY"')
        return None

    prompt = f"""
You are FixFile, an automatic code repair assistant.

Repair the source code below.

Rules:
1. Fix the reported error.
2. Preserve the original functionality.
3. Do not remove working features.
4. Return ONLY the complete corrected source code.
5. Do not use Markdown code fences.
6. Do not explain the answer.

SOURCE CODE:
{code}

ERROR:
{error}
"""

    payload = {
        "model": "openrouter/auto",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": (
                "https://github.com/"
                "amiralipishdar2014-blip/FixFile"
            ),
            "X-Title": "FixFile",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=90,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        return result["choices"][0]["message"]["content"]

    except Exception as error:
        print()
        print("❌ خطا در ارتباط با OpenRouter:")
        print(error)
        return None


def test_code(code, filename, language):
    extension = os.path.splitext(filename)[1]

    temporary_file = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=extension,
            delete=False,
        ) as file:
            file.write(code)
            temporary_file = file.name

        return check_file(
            temporary_file,
            language,
        )

    finally:
        if temporary_file:
            try:
                os.remove(temporary_file)
            except OSError:
                pass


def repair(filename):
    language = detect_language(filename)

    if not language:
        print(
            "❌ پسوند این فایل توسط FixFile پشتیبانی نمی‌شود."
        )
        return False

    print(f"🔍 زبان: {language}")

    try:
        original_code = read_file(filename)
    except Exception as error:
        print(f"❌ خطا در خواندن فایل: {error}")
        return False

    current_code = original_code

    for attempt in range(1, 5):
        print()
        print(f"🔧 تلاش {attempt}/4")

        return_code, error = test_code(
            current_code,
            filename,
            language,
        )

        if return_code == 0:
            print("✅ کد بدون خطا است.")

            if current_code != original_code:
                backup = filename + BACKUP_SUFFIX

                shutil.copy2(
                    filename,
                    backup,
                )

                with open(
                    filename,
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(current_code)

                print(f"💾 Backup ساخته شد: {backup}")
                print("✅ فایل اصلاح شد.")

            return True

        if return_code is None:
            print(f"❌ {error}")
            return False

        print("❌ خطا:")
        print(error)

        print()
        print("🤖 ارسال کد برای تعمیر توسط هوش مصنوعی...")

        repaired_code = ask_openrouter(
            current_code,
            error,
        )

        if not repaired_code:
            return False

        current_code = clean_ai_response(
            repaired_code
        )

        print("🔄 نسخه اصلاح‌شده دریافت شد.")

    print()
    print("❌ بعد از ۴ تلاش، فایل قابل اصلاح نبود.")

    return False


def show_help():
    print()
    print("FixFile - AI Code Repair Tool")
    print(f"Version: {VERSION}")
    print()
    print("استفاده:")
    print("  fixfile <file>")
    print()
    print("مثال:")
    print("  fixfile test.py")
    print("  fixfile app.cpp")
    print("  fixfile script.js")
    print()
    print("زبان‌های پشتیبانی‌شده:")
    print("  Python")
    print("  JavaScript")
    print("  TypeScript")
    print("  Bash")
    print("  PHP")
    print("  Ruby")
    print("  Java")
    print("  C")
    print("  C++")
    print("  Go")
    print("  Rust")
    print("  JSON")
    print("  HTML")
    print("  CSS")
    print()


def main():
    print()
    print("╔══════════════════════════════════╗")
    print("║            FixFile               ║")
    print("║       AI Code Repair Tool        ║")
    print(f"║            v{VERSION}             ║")
    print("╚══════════════════════════════════╝")

    if len(sys.argv) != 2:
        show_help()
        return 1

    filename = sys.argv[1]

    if not os.path.isfile(filename):
        print()
        print(f"❌ فایل پیدا نشد: {filename}")
        return 1

    print()
    print(f"📄 فایل: {filename}")

    success = repair(filename)

    print()

    if success:
        print("🎉 FixFile با موفقیت تمام شد.")
        return 0

    print("❌ FixFile نتوانست فایل را تعمیر کند.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
