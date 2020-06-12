import json
from codecs import open
from pathlib import Path

import asobann


app = asobann.create_app()


if __name__ == '__main__':
    with open(Path(__file__).parent / "./initial_deploy_data.json", encoding='utf-8') as f:
        default_data = json.load(f)
    for d in [asobann.tables, asobann.components, asobann.kits]:
        d.purge_all()
    asobann.components.store_default(default_data["components"])
    asobann.kits.store_default(default_data["kits"])
