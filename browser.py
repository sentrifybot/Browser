import sys
import os
import socket
import json
import re
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTabWidget, QMenu, QAction, QFrame, QMessageBox, QInputDialog, 
                             QListWidget, QDockWidget, QToolBar, QProgressBar, QFileDialog, QShortcut, QLabel)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import Qt, QUrl, QDateTime, QPoint, QDir
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QLinearGradient, QKeySequence, QCursor
import urllib.parse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTabWidget, QMenu, QAction, QFrame, QMessageBox, QInputDialog, 
                             QListWidget, QDockWidget, QToolBar, QProgressBar, QFileDialog, QShortcut, QLabel, QCompleter)
from PyQt5.QtCore import Qt, QUrl, QDateTime, QPoint, QDir, QStringListModel
import urllib.parse

class DownloadWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.downloads = []

    def add_download(self, download):
        item = QWidget()
        item_layout = QHBoxLayout(item)
        item_layout.addWidget(QLabel(download.path()))
        progress = QProgressBar()
        item_layout.addWidget(progress)
        download.downloadProgress.connect(progress.setValue)
        self.layout.addWidget(item)
        self.downloads.append(download)

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.featurePermissionRequested.connect(self.onFeaturePermissionRequested)

    def onFeaturePermissionRequested(self, url, feature):
        if feature in (QWebEnginePage.Geolocation, QWebEnginePage.Notifications):
            self.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
        else:
            self.setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)

class SFYBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SFY Browser")
        self.setGeometry(100, 100, 1200, 800)

        self.dns_server = ('104.237.128.17', 6000)
        self.bookmarks = []
        self.history = []
        self.zoom_factor = 1.0
        self.is_private_mode = False

        # List of popular search terms for autocomplete
        self.popular_searches = [
            "weather", "news", "maps", "translate", "calculator",
            "youtube", "facebook", "amazon", "twitter", "instagram",
            "linkedin", "reddit", "netflix", "spotify", "wikipedia"
        ]

        self.setup_ui()
        self.setup_shortcuts()
        self.setWindowIcon(QIcon('assets/sfy_browser_logo.svg'))

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.setup_toolbar()
        self.setup_tabs()
        self.setup_bookmarks_dock()
        self.setup_history_dock()
        self.setup_downloads_dock()

        self.apply_styles()


    def setup_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.back_button = QPushButton("◀")
        self.back_button.clicked.connect(self.go_back)
        toolbar.addWidget(self.back_button)

        self.forward_button = QPushButton("▶")
        self.forward_button.clicked.connect(self.go_forward)
        toolbar.addWidget(self.forward_button)

        self.reload_button = QPushButton("↻")
        self.reload_button.clicked.connect(self.reload_page)
        toolbar.addWidget(self.reload_button)


        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.setup_autocomplete()
        toolbar.addWidget(self.url_bar)

        self.bookmark_button = QPushButton("★")
        self.bookmark_button.clicked.connect(self.toggle_bookmark)
        toolbar.addWidget(self.bookmark_button)

        self.toggle_bookmarks_button = QPushButton("📚")
        self.toggle_bookmarks_button.clicked.connect(self.toggle_bookmarks_dock)
        toolbar.addWidget(self.toggle_bookmarks_button)

        self.toggle_history_button = QPushButton("🕒")
        self.toggle_history_button.clicked.connect(self.toggle_history_dock)
        toolbar.addWidget(self.toggle_history_button)

        self.find_button = QPushButton("🔍")
        self.find_button.clicked.connect(self.show_find_dialog)
        toolbar.addWidget(self.find_button)

        self.zoom_in_button = QPushButton("🔍+")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        toolbar.addWidget(self.zoom_in_button)

        self.zoom_out_button = QPushButton("🔍-")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        toolbar.addWidget(self.zoom_out_button)

        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_button)

        self.private_mode_button = QPushButton("🕵️")
        self.private_mode_button.clicked.connect(self.toggle_private_mode)
        toolbar.addWidget(self.private_mode_button)

        self.settings_button = QPushButton("⚙️")
        self.settings_button.clicked.connect(self.show_settings_menu)
        toolbar.addWidget(self.settings_button)

    def setup_autocomplete(self):
        completer = QCompleter(self.popular_searches)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.url_bar.setCompleter(completer)


    def setup_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.layout.addWidget(self.tabs)

        new_tab_button = QPushButton("+")
        new_tab_button.clicked.connect(self.add_tab)
        self.tabs.setCornerWidget(new_tab_button, Qt.TopRightCorner)

        self.add_tab()

    def setup_bookmarks_dock(self):
        self.bookmarks_widget = QListWidget()
        self.bookmarks_widget.itemClicked.connect(self.load_bookmark)
        
        self.bookmarks_dock = QDockWidget("Bookmarks")
        self.bookmarks_dock.setWidget(self.bookmarks_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bookmarks_dock)
        self.bookmarks_dock.hide()

    def setup_history_dock(self):
        self.history_widget = QListWidget()
        self.history_widget.itemClicked.connect(self.load_history_item)
        
        self.history_dock = QDockWidget("History")
        self.history_dock.setWidget(self.history_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
        self.history_dock.hide()

    def setup_downloads_dock(self):
        self.download_widget = DownloadWidget()
        self.download_dock = QDockWidget("Downloads")
        self.download_dock.setWidget(self.download_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.download_dock)
        self.download_dock.hide()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #3e2723, stop:1 #1b0000);
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #4e342e;
                color: #e0e0e0;
                border: none;
                padding: 5px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #5d4037;
            }
            QLineEdit {
                background-color: #4e342e;
                color: #e0e0e0;
                border: 1px solid #5d4037;
                padding: 5px;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #3e2723;
                color: #e0e0e0;
                padding: 8px;
            }
            QTabBar::tab:selected {
                background-color: #4e342e;
            }
            QDockWidget {
                color: #e0e0e0;
            }
            QListWidget {
                background-color: #3e2723;
                color: #e0e0e0;
                border: none;
            }
        """)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reload_page)
        QShortcut(QKeySequence("Ctrl+L"), self, self.focus_url_bar)
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_find_dialog)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)

    def add_tab(self, url=None):
        web_view = QWebEngineView()
        custom_page = CustomWebEnginePage(web_view)
        web_view.setPage(custom_page)
        custom_page.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        custom_page.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        
        index = self.tabs.addTab(web_view, "New Tab")
        self.tabs.setCurrentIndex(index)

        web_view.urlChanged.connect(lambda qurl, view=web_view: self.update_url_bar(qurl, view))
        web_view.loadFinished.connect(lambda _, view=web_view: self.update_tab_title(view))
        custom_page.profile().downloadRequested.connect(self.on_download_requested)

        if url:
            self.load_url(web_view, url)
        else:
            self.load_home_page(web_view)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.load_home_page(self.tabs.widget(0))

    def close_current_tab(self):
        self.close_tab(self.tabs.currentIndex())

    def load_home_page(self, web_view):
        home_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SFY Browser</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    margin: 0; 
                    background: linear-gradient(to bottom, #3e2723, #1b0000);
                    color: #e0e0e0;
                }
                .container { text-align: center; }
                h1 { 
                    color: #ff8a65; 
                    font-size: 84px; 
                    margin-bottom: 20px; 
                    font-weight: normal;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                }
                p { 
                    color: #d7ccc8; 
                    font-size: 22px;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SFY</h1>
                <p>Welcome to the SFY Browser</p>
            </div>
        </body>
        </html>
        """
        web_view.setHtml(home_html)
        self.url_bar.setText("")

    def is_ip_address(self, host):
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        return re.match(ip_pattern, host) is not None

    def navigate_to_url(self):
        url = self.url_bar.text().strip()
        current_tab = self.tabs.currentWidget()
        if current_tab:
            self.load_url(current_tab, url)

    def load_url(self, web_view, url):
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme

        if scheme in ['http', 'https']:
            web_view.setUrl(QUrl(url))
        elif scheme == 'sfy':
            domain = parsed_url.netloc
            ip = self.resolve_domain(domain)
            if ip:
                load_url = f"http://{ip}{parsed_url.path}"
                if parsed_url.query:
                    load_url += f"?{parsed_url.query}"
                web_view.load(QUrl(load_url))
                self.url_bar.setText(url)
            else:
                QMessageBox.warning(self, "SFY DNS Resolution Error", f"Could not resolve domain: {domain}")
        elif not scheme:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(url)}"
            web_view.setUrl(QUrl(search_url))
        else:
            web_view.setUrl(QUrl(url))

        if not self.is_private_mode:
            self.add_to_history(url)
            self.update_autocomplete(url)

    def update_autocomplete(self, url):
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            # It's likely a search term
            search_term = url.lower()
            if search_term not in self.popular_searches:
                self.popular_searches.append(search_term)
                self.popular_searches = self.popular_searches[-50:]  # Keep only the last 50 searches
                self.setup_autocomplete()  # Refresh the autocomplete

    def resolve_domain(self, domain):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(self.dns_server)
                s.sendall(f"RESOLVE {domain}".encode('utf-8'))
                response = s.recv(1024).decode('utf-8')
                result = json.loads(response)
                return result.get('ip')
        except Exception as e:
            print(f"DNS resolution error: {e}")
            return None


    def update_url_bar(self, q, view=None):
        if view != self.tabs.currentWidget():
            return
        # Only update the URL bar if it's not an SFY URL
        if not self.url_bar.text().startswith('sfy://'):
            self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_tab_title(self, view):
            index = self.tabs.indexOf(view)
            if index != -1:
                self.tabs.setTabText(index, view.page().title()[:20])

    def go_back(self):
        self.tabs.currentWidget().back()

    def go_forward(self):
        self.tabs.currentWidget().forward()

    def reload_page(self):
        self.tabs.currentWidget().reload()

    def toggle_bookmark(self):
        current_url = self.tabs.currentWidget().url().toString()
        current_title = self.tabs.currentWidget().page().title()
        
        if current_url in [b['url'] for b in self.bookmarks]:
            self.bookmarks = [b for b in self.bookmarks if b['url'] != current_url]
            self.bookmark_button.setText("☆")
        else:
            self.bookmarks.append({'title': current_title, 'url': current_url})
            self.bookmark_button.setText("★")
        
        self.update_bookmarks_list()

    def update_bookmarks_list(self):
        self.bookmarks_widget.clear()
        for bookmark in self.bookmarks:
            self.bookmarks_widget.addItem(f"{bookmark['title']} ({bookmark['url']})")

    def load_bookmark(self, item):
        url = item.text().split('(')[-1][:-1]  # Extract URL from list item
        self.load_url(self.tabs.currentWidget(), url)

    def add_to_history(self, url):
        if not self.is_private_mode:
            self.history.append({'url': url, 'timestamp': QDateTime.currentDateTime()})
            self.update_history_list()

    def update_history_list(self):
        self.history_widget.clear()
        for item in reversed(self.history):
            self.history_widget.addItem(f"{item['timestamp'].toString()} - {item['url']}")

    def load_history_item(self, item):
        url = item.text().split(' - ')[-1]
        self.load_url(self.tabs.currentWidget(), url)

    def toggle_bookmarks_dock(self):
        if self.bookmarks_dock.isVisible():
            self.bookmarks_dock.hide()
        else:
            self.bookmarks_dock.show()

    def toggle_history_dock(self):
        if self.history_dock.isVisible():
            self.history_dock.hide()
        else:
            self.history_dock.show()

    def show_find_dialog(self):
        find_text, ok = QInputDialog.getText(self, 'Find in Page', 'Enter text to find:')
        if ok and find_text:
            self.tabs.currentWidget().findText(find_text)

    def zoom_in(self):
        self.zoom_factor += 0.1
        self.tabs.currentWidget().setZoomFactor(self.zoom_factor)

    def zoom_out(self):
        self.zoom_factor = max(0.1, self.zoom_factor - 0.1)
        self.tabs.currentWidget().setZoomFactor(self.zoom_factor)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_private_mode(self):
        self.is_private_mode = not self.is_private_mode
        if self.is_private_mode:
            self.private_mode_button.setStyleSheet("background-color: #8B0000;")
        else:
            self.private_mode_button.setStyleSheet("")
        QMessageBox.information(self, "Private Mode", f"Private Mode: {'On' if self.is_private_mode else 'Off'}")

    def show_settings_menu(self):
        settings_menu = QMenu(self)
        clear_history_action = QAction("Clear History", self)
        clear_history_action.triggered.connect(self.clear_history)
        settings_menu.addAction(clear_history_action)

        clear_cookies_action = QAction("Clear Cookies", self)
        clear_cookies_action.triggered.connect(self.clear_cookies)
        settings_menu.addAction(clear_cookies_action)

        about_action = QAction("About SFY Browser", self)
        about_action.triggered.connect(self.show_about)
        settings_menu.addAction(about_action)

        settings_menu.exec_(QCursor.pos())

    def clear_history(self):
        self.history.clear()
        self.update_history_list()
        QMessageBox.information(self, "History Cleared", "Your browsing history has been cleared.")

    def clear_cookies(self):
        self.tabs.currentWidget().page().profile().cookieStore().deleteAllCookies()
        QMessageBox.information(self, "Cookies Cleared", "All cookies have been cleared.")

    def show_about(self):
        QMessageBox.about(self, "About SFY Browser", "SFY Browser v1.0\nA custom web browser with advanced features.")

    def on_download_requested(self, download):
        default_path = os.path.join(QDir.homePath(), download.suggestedFileName())
        path, _ = QFileDialog.getSaveFileName(self, "Save File", default_path, "All Files (*.*)")
        
        if path:
            download.setPath(path)
            download.accept()
            self.download_widget.add_download(download)
            self.download_dock.show()

    def focus_url_bar(self):
        self.url_bar.setFocus()
        self.url_bar.selectAll()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    browser = SFYBrowser()
    browser.show()
    sys.exit(app.exec_())
