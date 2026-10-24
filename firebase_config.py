"""Parse private deployment credentials without leaking their contents."""
import json


def parse_credentials(raw, project_id):
    try:
        value = raw.strip()
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        data = json.loads(value)
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict) or data.get('type') != 'service_account':
            raise ValueError()
        if data.get('project_id') != project_id:
            raise ValueError()
        if not data.get('client_email') or not isinstance(data.get('private_key'), str):
            raise ValueError()
        data['private_key'] = data['private_key'].replace('\\n', '\n')
        return data
    except (ValueError, TypeError):
        raise ValueError('Invalid Firebase credential format or project.') from None
