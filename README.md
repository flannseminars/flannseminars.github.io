# FLaNN website

A static website built with HTML, CSS, and JavaScript. Run it locally with Python 3; no packages or build step are needed to view the checked-in pages.

## Run locally

Clone the Tasting Menu review branch, then start a server from the repository folder:

```sh
git clone --branch codex/tasting-menu https://github.com/flannseminars/flannseminars.github.io.git
cd flannseminars.github.io
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [the website](http://127.0.0.1:8000/) or [the Tasting Menu](http://127.0.0.1:8000/tasting-menu.html). Use the server URL so the nomination form can load its JSON data. Stop the server with **Ctrl+C**.

If you already have this branch checked out, just run the server command from the repository folder. If port 8000 is busy, choose another port and update the URL.

## Make changes

- Edit HTML and CSS, save, and refresh your browser.
- For menu entries and paper posts, edit `data/tasting-menu-editorial.json`, then rebuild:

  ```sh
  python3 scripts/build_tasting_menu.py
  ```

Generated pages in `tasting-menu/` and the marked menu/archive blocks in `tasting-menu.html` are replaced by the build.

The current branch uses local design data; public voting has not opened. See the [host guide](docs/TASTING_MENU.md) for the nomination pipeline and activation steps, and the [Discord announcement draft](docs/tasting-menu-discord.txt) for proposed launch copy.
