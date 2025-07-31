from urllib.request import urlopen
from urllib.parse import urljoin
from urllib.error import URLError
import subprocess
import os
from bs4 import BeautifulSoup
import yaml

with open("config.yaml", "r") as opened_file:
    config = yaml.safe_load(opened_file)


def send_message(config, body=""):
    """Send email using the local ``mail`` command."""

    receiver_email = config.get("receiver_email")
    sender_email = config.get("sender_email")
    subject = "You have a new post"
    message = f"{body}\n---\n\nCheers,\nYour team"

    try:
        subprocess.run(
            [
                "mail",
                "-s",
                subject,
                "-r",
                sender_email,
                receiver_email,
            ],
            input=message.encode("utf-8"),
            check=True,
        )
    except Exception as exc:
        print(f"Failed to send email: {exc}")
        return

    print("Message sent!")


def query_room_website(url):
    print(f'Scraping {url}')
    try:
        html = urlopen(url).read()
    except URLError as exc:
        print(f'Failed to read {url}: {exc}')
        return ""
    soup = BeautifulSoup(html, features="html.parser")

    body = ""
    # "tr" is table row
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 2:
            for cell in cells:
                info = cell.text.strip()
                body += info + '\n'
            body += '\n'

    body += f'Listing link\n{url}'

    return body


def query_main_website() -> list:
    """
    Find all listings on the main WOKO website
    :return: list of listings
    """
    url = config["url_woko"]
    try:
        html = urlopen(url).read()
    except URLError as exc:
        print(f'Failed to query main page: {exc}')
        return []
    soup = BeautifulSoup(html, features="html.parser")

    # return value if no listing section could be found
    listing_urls = []
    id = ''
    zurich_variations = ('zurich', 'zürich', 'zuerich')
    winterthur_variations = ('winterthur', 'wädenswil', 'waedenswil')
    for button in soup.find_all('button'):
        button_text = button.text.lower()
        # The button and div containing the listing are linked with a data-gruppeid number.
        if 'data-gruppeid' in str(button):
            # Looking for the button corresponding to a specific city.
            if (
                    config['city'].lower() in zurich_variations
                    and any(city in button_text for city in zurich_variations)
            ):
                id = button['data-gruppeid']
                break

            elif (
                    config['city'].lower() in winterthur_variations
                    and any(city in button_text for city in winterthur_variations)
            ):
                id = button['data-gruppeid']
                break

            elif 'free rooms' in button_text:
                id = button['data-gruppeid']
                break

    if id == "":
        print("Couldn't find the room buttons")
        return listing_urls

    # This is the div which the button reveals
    div = soup.find('div', attrs={'id': f'GruppeID_{id}'})
    if not div:
        print("Couldn't locate listing container")
        return listing_urls

    # Extract individual listing URLs
    for link in div.find_all('a'):
        relative_room_url = link['href']
        room_url = urljoin(url, relative_room_url)
        listing_urls.append(room_url)

    return listing_urls


def load_known_listings(path="known_listings.txt"):
    if os.path.exists(path):
        with open(path, "r") as fh:
            return [line.strip() for line in fh if line.strip()]
    return []


def save_known_listings(urls, path="known_listings.txt"):
    with open(path, "w") as fh:
        for url in urls:
            fh.write(f"{url}\n")


def main():
    listing_urls = query_main_website()

    if len(listing_urls) == 0:
        print('No listings found')
        if config['test_email']:
            print('Cannot test without any listings, exiting')
        return

    if config['test_email']:
        listing_urls.pop()

    known = load_known_listings()

    new_listing_urls = set(listing_urls) - set(known)

    if new_listing_urls:
        for new_listing_url in new_listing_urls:
            body = query_room_website(new_listing_url)
            if body:
                send_message(
                    body=body,
                    config=config,
                )
        print("Found new listings!")
    else:
        print(f"Still: {len(listing_urls)} rooms...")

    save_known_listings(listing_urls)


if __name__ == "__main__":
    main()
