import json
from codecs import open
from pathlib import Path

import asobann, asobann.app


app = asobann.app.create_app()


def purge_all():
    for d in [asobann.store.tables, asobann.store.components, asobann.store.kits]:
        d.purge_all()


def purge_kits_and_components():
    for d in [asobann.store.components, asobann.store.kits]:
        d.purge_all()


def load_default():
    with open(Path(__file__).parent / "./initial_deploy_data.json", encoding='utf-8') as f:
        default_data = json.load(f)
    # purge_all()
    purge_kits_and_components()
    asobann.store.components.store_default(default_data["components"])
    asobann.store.kits.store_default(default_data["kits"])


if __name__ == '__main__':
    load_default()
