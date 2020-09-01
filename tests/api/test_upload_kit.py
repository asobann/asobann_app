from pathlib import Path
import requests
import json
import pytest

PWD = Path(__file__).parent


def upload_image(base_url, image_image_path):
    files = {'image': open(image_image_path, 'rb')}
    res = requests.post(base_url + '/dummy', files=files)
    assert res.status_code == 200
    return json.loads(res.content)


def get_image(base_url, image_url):
    res = requests.get(base_url + image_url)
    assert res.status_code == 200
    return res.content


@pytest.mark.usefixtures("server")
class TestUploadImage:
    def test_upload_and_view(self, base_url):
        local_image_path = PWD / 'example.png'
        with open(local_image_path, 'rb') as f:
            local_image = f.read()
        resp = upload_image(base_url, local_image_path)
        data = get_image(base_url, resp['imageUrl'])
        assert local_image == data


@pytest.mark.usefixtures("server")
class TestUploadKits:
    class TestFailures:
        def test_upload_empty_json(self, base_url):
            files = {'data': b'{}'}
            res = requests.post(base_url + '/kits/create', files=files)
            assert res.status_code == 400

        def test_upload_malformed_input(self, base_url):
            files = {'data': b'hi! this is NOT JSON'}
            res = requests.post(base_url + '/kits/create', files=files)
            assert res.status_code == 400

        @pytest.mark.skip
        def test_kit_references_wrong_component(self, base_url):
            assert False

    def test_create(self, base_url):
        kit_data = {
            'kit': {
                'name': 'test kit 01',
                'label': 'test kit 01',
                'label_ja': 'test kit 01',
                'height': '64px',
                'width': '64px',
                'boxAndComponents': {
                    'test component 01': None,
                },
                'usedComponentNames': [
                    'test component 01',
                ]
            },
            'components': [
                {
                    "name": "test component 01",
                    "handArea": False,
                    "top": "0px",
                    "left": "0px",
                    "height": "64px",
                    "width": "64px",
                    "showImage": False,
                    "draggable": True,
                    "flippable": False,
                    "resizable": False,
                    "rollable": True,
                    "ownable": False,
                },
            ]
        }
        files = {'data': json.dumps(kit_data)}
        res = requests.post(base_url + '/kits/create', files=files)
        assert res.status_code == 200
        res_data = json.loads(res.text)
        kit_name = res_data['kitName']

        res = requests.get(f'{base_url}/kits/{kit_name}')
        assert res.status_code == 200
        kit_data2 = json.loads(res.text)
        assert 'test kit 01' == kit_data2['kit']['name']
        assert 1 == kit_data2['version']

        res = requests.get(f'{base_url}/components/?kit_name={kit_data2["kit"]["name"]}')
        assert res.status_code == 200
        components_data = json.loads(res.text)
        assert 'test component 01' == components_data[0]['component']['name']

    @pytest.mark.skip
    def test_update(self, base_url):
        assert False

    @pytest.mark.skip
    def test_download(self, base_url):
        assert False

    @pytest.mark.skip
    def test_delete(self, base_url):
        assert False

    @pytest.mark.skip
    def test_upload_without_images(self, base_url):
        assert False

    @pytest.mark.skip
    def test_upload_with_images(self, base_url):
        assert False
