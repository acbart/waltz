import requests
import time
from json.decoder import JSONDecodeError


def download_file(url, destination):
    r = requests.get(url)
    f = open(destination, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    f.close()


class CanvasAPI:
    course: str
    token: str
    base: str

    def __init__(self, base, token, course):
        self.base = base
        self.token = token
        self.course = course

    def get(self, command, data=None, retrieve_all=False, params=None, json=None, skip_course=False):
        return self._canvas_request(requests.get, command, data, params, json, retrieve_all, skip_course)

    def post(self, command, data=None, retrieve_all=False, params=None, json=None, skip_course=False):
        return self._canvas_request(requests.post, command, data, params, json, retrieve_all, skip_course)

    def put(self, command, data=None, retrieve_all=False, params=None, json=None, skip_course=False):
        return self._canvas_request(requests.put, command, data, params, json, retrieve_all, skip_course)

    def delete(self, command, data=None, retrieve_all=False, params=None, json=None, skip_course=False):
        return self._canvas_request(requests.delete, command, data, params, json, retrieve_all, skip_course)

    def _canvas_request(self, verb, command, data, params, json, retrieve_all, skip_course):
        if data is None:
            data = {}
        if params is None:
            params = {}
        headers = {}
        if json is not None:
            data = None
            headers['Authorization'] = "Bearer "+self.token
        else:
            data['access_token'] = self.token
        next_url = self.base+"api/v1/"
        if not skip_course:
            next_url += "courses/{course_id}/".format(course_id=self.course)
        next_url += command
        if retrieve_all:
            data['per_page'] = 100
            final_result = []
            while True:
                response = verb(next_url, data=data, params=params, json=json, headers=headers)
                try:
                    final_result += response.json()
                except JSONDecodeError:
                    raise Exception("{}\n{}".format(response, next_url))
                if 'next' in response.links:
                    next_url = response.links['next']['url']
                else:
                    return final_result
        else:
            response = verb(next_url, data=data, params=params, json=json, headers=headers)
            if response.status_code == 204:
                return response
            try:
                return response.json()
            except JSONDecodeError:
                raise Exception("{}\n{}".format(response, next_url))

    def progress_loop(self, progress_id, seconds_delay=3):
        attempt = 0
        while True:
            result = self._canvas_request(requests.get, 'progress/{}'.format(progress_id),
                                          {'_dummy_counter': attempt}, None, None, False, True)[0]
            if result['workflow_state'] == 'completed':
                return True
            elif result['workflow_state'] == 'failed':
                return False
            else:
                print("In progress:", result['workflow_state'], result['message'],
                      str(int(round(result['completion']*10))/10)+"%")
                if not hasattr(result, 'from_cache') or not result.from_cache:
                    time.sleep(seconds_delay)
                attempt += 1
