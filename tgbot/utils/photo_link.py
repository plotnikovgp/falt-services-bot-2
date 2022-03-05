import aiohttp


async def photo_link(path) -> str:
    with open(path, "rb") as file:
        form = aiohttp.FormData()
        form.add_field(name='file', value=file)

        async with aiohttp.ClientSession() as session:
            async with session.post('https://telegra.ph/upload', data=form) as response:
                resp = await response.json()

    link = 'http://telegra.ph/' + resp[0]["src"]
    return link

