import json

import pytest

from firebase_config import parse_credentials


@pytest.mark.parametrize('encoding', ['plain', 'quoted', 'double'])
def test_deployment_credential_formats(encoding):
    data = dict(type='service_account', project_id='test', client_email='test@example.invalid', private_key='BEGIN\\nFAKE\\nEND')
    raw = json.dumps(data)
    if encoding == 'quoted':
        raw = "'" + raw + "'"
    elif encoding == 'double':
        raw = json.dumps(raw)
    assert parse_credentials(raw, 'test')['private_key'] == 'BEGIN\nFAKE\nEND'


@pytest.mark.parametrize('raw', ['not-json-secret', '[]', '{"type":"service_account","project_id":"wrong"}'])
def test_invalid_credentials_do_not_expose_input(raw):
    with pytest.raises(ValueError) as error:
        parse_credentials(raw, 'test')
    assert str(error.value) == 'Invalid Firebase credential format or project.'
