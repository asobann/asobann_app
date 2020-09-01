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
class TestUploadComponent:
    @pytest.mark.skip
    def test_upload_empty_json(self, base_url):
        res = requests.post(base_url + '/components/new', data=b'{}')
        assert res.status_code == 400

    @pytest.mark.skip
    def test_create_component(self, base_url):
        assert False

    @pytest.mark.skip
    def test_update_component(self, base_url):
        assert False

    @pytest.mark.skip
    def test_download_component(self, base_url):
        assert False

    @pytest.mark.skip
    def test_delete_component(self, base_url):
        assert False

    @pytest.mark.skip
    def test_upload_component_without_images(self, base_url):
        assert False

    @pytest.mark.skip
    def test_upload_component_with_images(self, base_url):
        assert False

