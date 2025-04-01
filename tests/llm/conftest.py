import pytest


@pytest.fixture
def mock_response():
    """Create a mock API response object."""
    return type('Response', (), {
        'content': [
            type('Content', (), {
                'text': 'Test response'
            })()
        ],
        'usage': type('Usage', (), {
            'input_tokens': 10,
            'output_tokens': 20
        })
    })()

@pytest.fixture
def config():
    """Create a standard config for testing."""
    return {
        "api_key": "test_key",
        "timeout": 1.0,
        "max_retries": 1
    }