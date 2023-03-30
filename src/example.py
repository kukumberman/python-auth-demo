import aiohttp
import asyncio
import platform
import uuid
import webbrowser
import json
import os

SERVER_URL = "http://localhost:3000"
EXTERNAL_LOGIN_WAIT_IN_SECONDS = 3
TOKEN_FILE = "./save/token.json"

session = ""
token_data = None
profile_data = None


class UnauthorizedError(Exception):
    pass


def open_url(url: str):
    webbrowser.open(url)


def create_session_id():
    return str(uuid.uuid4()).split("-")[0]


async def do_request(method: str, endpoint: str, headers=None):
    async with aiohttp.ClientSession(SERVER_URL) as session:
        async with session.request(method, endpoint, headers=headers) as response:
            # todo - wrap response to custom object
            if response.status == 200:
                data = await response.json()
                return data
            if response.status == 401:
                raise UnauthorizedError
            return None


async def get_request(endpoint: str, headers=None):
    return await do_request("GET", endpoint, headers)


async def external_login_request(session: str):
    data = await get_request("/login/external?session={0}".format(session))
    return data


async def social_platforms_request(session: str):
    return await get_request("/login/all?session={0}".format(session))


async def authorized_request(url: str):
    headers = {
        "Authorization": "Bearer {0}".format(token_data["accessToken"])
    }
    try:
        data = await get_request(url, headers)
        return data
    except UnauthorizedError:
        print("todo - try refresh token")
        pass


async def profile_request():
    return await authorized_request("/api/profile/me")


def ensure_token_directory_exists():
    directory = os.path.dirname(TOKEN_FILE)
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)


def save_token_locally():
    ensure_token_directory_exists()

    json_str = json.dumps(token_data, indent=2)
    with open(TOKEN_FILE, "w") as f:
        f.write(json_str)


def read_local_token():
    global token_data
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            return True
    except FileNotFoundError:
        pass
    except json.decoder.JSONDecodeError:
        pass
    return False


def show_profile():
    id = profile_data["id"]
    nickname = profile_data["app"]["nickname"]["value"]
    print(id, nickname)


async def handle_login_via_platform():
    global session
    session = create_session_id()
    platforms = await social_platforms_request(session)

    platform_names = list(map(lambda x: x["name"], platforms))
    print(platform_names)

    auth_url = platforms[0]["authorizationUri"]
    open_url(auth_url)

    while True:
        print("Waiting for user...")
        await asyncio.sleep(EXTERNAL_LOGIN_WAIT_IN_SECONDS)
        data = await external_login_request(session)
        if data != None:
            global token_data
            token_data = data
            save_token_locally()
            break

    profile = await profile_request()
    if profile != None:
        global profile_data
        profile_data = profile


async def handle_login_via_local_token():
    if read_local_token():
        profile = await profile_request()
        if profile != None:
            global profile_data
            profile_data = profile
            return True
    return False


async def main():
    if await handle_login_via_local_token():
        show_profile()
    else:
        await handle_login_via_platform()
        show_profile()

if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
