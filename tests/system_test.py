import subprocess
import pytest
import re
import os

AI_SCRIPT_PATH = "pipenv"
cwd = os.getcwd() + "/tests"

# Test cases, yo!
test_cases = [
    (
        "conversation_no_files.txt",  # Fixture file
        ['--quiet', 'run', 'python', '-m', 'src.cli', '-d', cwd, '-q', '-n']  # Args, no -f
    ),
    (
        "conversation_with_files.txt",
        ['--quiet', 'run', 'python', '-m', 'src.cli', '-d', cwd, '-f', 'fixtures/test_file.txt', '-q', '-n']
    ),
    (
        "conversation_with_all_files.txt",
        ['--quiet', 'run', 'python', '-m', 'src.cli', '-d', cwd, '-f', '.', '-q', '-n']
    ),
]

def parse_conversation(fixture_content):
    """Parses the conversation fixture file.

    Args:
        fixture_content: The string content of the fixture file.

    Returns:
        A list of tuples, where each tuple is (speaker, message).
    """
    matches = re.findall(r"(^|\n)(Brent|Linus):\n(.*?)(?=\n(?:Brent|Linus)|$)", fixture_content, re.DOTALL)
    return [(speaker, message.strip()) for _, speaker, message in matches]

def run_test(conversation, ai_args):
    """Runs the system test.

    Args:
        conversation: List of tuples, (speaker, message).  Assumes Brent speaks first.
        ai_args: Arguments to pass to the AI subprocess.

    Returns:
      Bool, if test passed or failed
    """

    print("Starting process...")
    process = subprocess.Popen(
        [AI_SCRIPT_PATH, *ai_args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line-buffered
        universal_newlines=True,
        cwd=cwd # Set working directory here, for simpler file paths
    )

    all_output = []

    try:
        for i in range(0, len(conversation), 2):
            brent_message = conversation[i][1] # Always Brent
            expected_linus_response = conversation[i+1][1] # Always Linus

            # Send Brent's message to the process.  Include newline.
            process.stdin.write(brent_message + "\n")
            process.stdin.flush()

            # Read the output until we see expected Linus.
            output_buffer = ""

            while True:
                line = process.stdout.readline()
                if not line:
                    # Check for error/timeout
                    if process.poll() is not None:
                        all_output.append(output_buffer)
                        print(f"Process exited prematurely with code: {process.returncode}")
                        print(f"stderr: {process.stderr.read()}")
                        return False
                    else:
                        continue

                output_buffer += line

                if "TESTING: RESPONSE COMPLETE" in line:
                    break

            all_output.append(output_buffer)

            cleaned_output = output_buffer.replace("TESTING: RESPONSE COMPLETE", "").rstrip()
            if cleaned_output.strip() != expected_linus_response.strip():
                print(f"Output mismatch!\n\nExpected:\n---\n{expected_linus_response.strip()}\n---\n\nGot:\n---\n{cleaned_output.strip()}\n---\n")
                return False

        if process.stderr.read():
            print(f"Error in subprocess: {process.stderr.read()}")
            return False

        return True

    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

@pytest.mark.parametrize("fixture_file, ai_args", test_cases)
def test_conversation(fixture_file, ai_args):
    fixture_path = os.path.join("fixtures", fixture_file)
    with open(fixture_path, "r") as f:
        fixture_content = f.read()

    conversation = parse_conversation(fixture_content)
    assert run_test(conversation, ai_args)# Create empty fixture files.
open(os.path.join(cwd, "fixtures/conversation_no_files.txt"), "w").close()
open(os.path.join(cwd, "fixtures/conversation_with_files.txt"), "w").close()
open(os.path.join(cwd, "fixtures/conversation_with_all_files.txt"), "w").close()

# Create a test file
with open(os.path.join(cwd, "fixtures/test_file.txt"), "w") as f:
    f.write("This is a test file, for testing purposes.\n")