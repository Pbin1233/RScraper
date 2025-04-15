import webview
from override_api import OverrideAPI

if __name__ == '__main__':
    api = OverrideAPI()
    window = webview.create_window("Autocontrollo Override Editor", "autocontrollo.html", js_api=api, width=1200, height=900)
    webview.start()
