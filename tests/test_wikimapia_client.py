import json
import unittest

import httpx

from infrastructure.wikimapia_client import WikimapiaClient


class WikimapiaClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_page_skips_details_when_option_is_disabled(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            body = {
                "folder": [
                    {
                        "id": 42,
                        "name": "Укрытие",
                        "location": {"lon": 37.6, "lat": 55.7},
                    }
                ]
            }
            return httpx.Response(200, content=json.dumps(body).encode())

        client = WikimapiaClient("key")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            places = await client.fetch_page(2390, 1, "37,55,38,56", 100)
        finally:
            await client.close()

        self.assertEqual(places[0].description, "")
        self.assertEqual(len(requests), 1)

    async def test_fetch_page_loads_description_from_place_details(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            function = request.url.params["function"]
            if function == "box":
                body = {
                    "folder": [
                        {
                            "id": 42,
                            "name": "Укрытие",
                            "location": {"lon": 37.6, "lat": 55.7},
                        }
                    ]
                }
            else:
                body = {
                    "id": 42,
                    "title": "Укрытие",
                    "description": "Подробное описание",
                }
            return httpx.Response(200, content=json.dumps(body).encode())

        client = WikimapiaClient(
            "key",
            detail_request_delay=0,
            include_detailed_description=True,
        )
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            places = await client.fetch_page(2390, 1, "37,55,38,56", 100)
        finally:
            await client.close()

        self.assertEqual(places[0].description, "Подробное описание")
        self.assertEqual((places[0].longitude, places[0].latitude), (37.6, 55.7))
        self.assertEqual([r.url.params["function"] for r in requests], [
            "box",
            "place.getbyid",
        ])


if __name__ == "__main__":
    unittest.main()
