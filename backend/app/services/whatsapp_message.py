import requests

phone_number_id = "926159523906357"
access_token = "EAATJDPXxzGEBQAT8zVqipZCahHCaXHblug3bTbPZB232JFcdMfcNPXspfObbzA5NAmahYIkmHuMAIt4SXsoyZBOvCyYYWjvN3BYvNUsAJzqSiKExWqgLmzpChQdEUCyI3zDVev6uq8mNsQg3WkWbV5PMkSGjFteQbfXeibvH5dnATGtCHTMsRZAwhSgC8yQtIAZDZD"

def send_whatsapp_messages(message):
    recipients = [
        "923322590048",
        "923001112223",
        "923004445556"
    ]
    
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    for number in recipients:
        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "text",
            "text": {"body": message}
        }

        response = requests.post(url, json=payload, headers=headers)
        print(f"Sent to {number}: {response.json()}")


