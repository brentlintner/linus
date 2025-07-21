import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Make sure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import chat, parser, database

@pytest.fixture
def temp_cwd_with_db(tmp_path):
    """
    A pytest fixture that creates a temporary working directory,
    initializes the database within it, and handles cleanup.
    """
    original_cwd = os.getcwd()
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    os.chdir(test_dir)

    db = database.initialize_database(str(test_dir))

    yield test_dir

    db.close()
    os.chdir(original_cwd)

@patch('src.chat.genai.Client')
def test_stream_parsing_and_file_writing(MockGenaiClient, temp_cwd_with_db):
    """
    Tests that the stream processing logic correctly parses file parts from a
    mocked API stream, assembles them, and writes the final file to disk.
    """
    cwd = temp_cwd_with_db
    state = chat.create_session_state(cwd=str(cwd), writeable=True, include_patterns=None)

    # 1. Define the file content and path for our test
    file_path = "src/new_file.py"
    file_content_part1 = "import os\n\n"
    file_content_part2 = "def main():\n    print('hello world')\n"
    expected_final_content = "import os\n\ndef main():\n    print('hello world')\n"

    # 2. Manually craft the multi-part file response as the "AI" would send it
    part1_block = f"""{parser.placeholder('START FILE METADATA')}
Path: {file_path}
Language: python
Version: 1
Part: 1
{parser.placeholder('END FILE METADATA')}
{file_content_part1}
{parser.placeholder('END OF FILE')}"""

    part2_block = f"""{parser.placeholder('START FILE METADATA')}
Path: {file_path}
Language: python
Version: 1
Part: 2
{parser.placeholder('END FILE METADATA')}
{file_content_part2}
{parser.placeholder('END OF FILE')}"""

    final_block = f"""{parser.placeholder('START FILE METADATA')}
Path: {file_path}
Language: python
Version: 1
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
{parser.placeholder('END OF FILE')}"""

    # 3. Simulate the chunked stream from the API
    fake_chunks_text = [
        "Sure, here is the file you requested:\n\n",
        part1_block,
        "\n",
        part2_block,
        "\n",
        final_block,
        "\nThat should do it.",
    ]
    fake_response_chunks = [MagicMock(text=t, usage_metadata=None) for t in fake_chunks_text]
    fake_response_chunks[-1].usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=100, total_token_count=110,
        cached_content_token_count=0, thoughts_token_count=0, tool_use_prompt_token_count=0
    )

    # 4. Configure the mocked client instance
    mock_client_instance = MockGenaiClient.return_value
    mock_client_instance.models.generate_content_stream.return_value = iter(fake_response_chunks)

    # 5. Run the function that contains the logic we want to test
    chat.send_request_to_ai(state, mock_client_instance)

    # 6. Assert the results
    created_file_path = cwd / file_path
    assert created_file_path.exists(), "The file should have been created on disk"

    with open(created_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert content == expected_final_content, "The file content should be correctly assembled"

    with database.db_proxy:
        last_chat = chat.Chat.select().order_by(chat.Chat.timestamp.desc()).get()
        assert "That should do it" in last_chat.message
        assert f"Path: {file_path}" in last_chat.message
        assert last_chat.user.name == 'linus', "The chat history should be saved under the 'linus' user"
