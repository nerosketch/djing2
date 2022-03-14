#!/usr/bin/env python3
#  from requests import get as httpget
from requests import put as httpput


def subscribe():
    r = httpput(url='http://localhost/api/hook/subscribe/', json={
        'notification_type': 3,
        'client_url': 'http://localhost:8083/',
        'content_type': {
            'app_label': 'customers',
            'model': 'customer'
        }
    }, headers={
        'Authorization': 'Token 0000000000000000000000000000000000000000',
        'Content-type': 'application/json'
    })
    print(r.status_code, r.json())
    return r.json()



def main():
    subscribe()


if __name__ == '__main__':
    main()

