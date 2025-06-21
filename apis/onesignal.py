import requests

def send_notification(title, message, segments=["All"]):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic os_v2_org_nhceqyl6krd63e32jf4xpqggmicemnbcjshehsfubka73mn6w5ssxqpwxbdv7cnsw42vpddie7uf4egy3rj6bi63u4gyy2n4pbxstlq"
    }

    payload = {
        "app_id": "69c44861-7e54-47ed-937a-497977c0c662",
        "included_segments": segments,  # يمكنك تخصيصها لاحقًا
        "headings": {
            "en": title,
            "ar": title
        },
        "contents": {
            "en": message,
            "ar": message
        }
    }

    try:
        response = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
